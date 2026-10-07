package com.electronicbrain.androidexecutor

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.IBinder
import java.io.File
import java.io.FileInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import org.json.JSONObject

class ExecutorService : Service() {
    companion object {
        const val ACTION_START = "START"
        private const val CHANNEL = "electronic_brain_executor"
        private const val DEFAULT_BASE_URL = "http://127.0.0.1:8012"
        private const val POLL_MS = 2000L
        private const val MAX_BACKOFF_MS = 30000L
        private val ALLOWED = setOf("status","device_info","platform","list_files","mkdir","read_file","write_text","run_toybox","ffmpeg_probe","ffmpeg_run","verify_file","verify_media","termux_probe","queue_status","queue_enqueue","film_create","chatgpt_ui_send","internet_download","open_url","open_app","create_app_project",)
    }

    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var queueWorker: QueueWorker
    @Volatile private var running = false

    override fun onCreate() {
        super.onCreate()
        queueWorker = QueueWorker(this)
        createChannel()
        startForeground(7, notification("Electronic Brain Executor: starting"))
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!running) {
            running = true
            executor.submit { loop() }
        }
        return START_STICKY
    }

    private fun loop() {
        val prefs = getSharedPreferences("executor", MODE_PRIVATE)
        val agentId = prefs.getString("agent_id", "android-executor-redmi3-01") ?: "android-executor-redmi3-01"
        val key = prefs.getString("agent_key", "") ?: ""
        val baseUrl = prefs.getString("brain_base_url", DEFAULT_BASE_URL)?.trimEnd('/') ?: DEFAULT_BASE_URL
        if (key.isBlank()) {
            updateNotification("ERROR: agent key missing")
            running = false
            return
        }

        updateNotification("READY: $agentId")
        var backoffMs = POLL_MS
        while (running) {
            try {
                // Keep Brain's device registry fresh even when no task is queued.
                heartbeat(baseUrl, agentId, key)
                // Resume one persisted production task on every executor cycle.
                queueWorker.resumeOnce()

                val task = poll(baseUrl, agentId, key)
                if (task != null) {
                    val result = execute(task)
                    report(baseUrl, agentId, key, task.optString("task_id"), result)
                    updateNotification(
                        if (result.optBoolean("ok")) "EXECUTED: " + task.optString("task")
                        else "FAILED: " + task.optString("task")
                    )
                } else {
                    backoffMs = POLL_MS
                    updateNotification("CONNECTED: $agentId • IDLE")
                    Thread.sleep(POLL_MS)
                }
            } catch (e: Exception) {
                updateNotification("RECONNECTING: " + (e.message ?: "unknown").take(70))
                Thread.sleep(backoffMs)
                backoffMs = (backoffMs * 2).coerceAtMost(MAX_BACKOFF_MS)
            }
        }
    }


    private fun heartbeat(baseUrl: String, agentId: String, key: String) {
        val c = URL(baseUrl + "/api/device/heartbeat").openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.doOutput = true
        c.connectTimeout = 10000
        c.readTimeout = 10000
        c.setRequestProperty("X-V12-Agent-Key", key)
        c.setRequestProperty("X-V12-Agent-Id", agentId)
        c.setRequestProperty("Content-Type", "application/json")
        val metadata = JSONObject().put("client", "ElectronicBrain-AndroidExecutor").put("model", Build.MODEL).put("sdk", Build.VERSION.SDK_INT).put("executor_agent_id", agentId)
        c.outputStream.use { it.write(JSONObject().put("agent_id", agentId).put("metadata", metadata).toString().toByteArray(StandardCharsets.UTF_8)) }
        val code = c.responseCode
        if (code !in 200..299) throw IllegalStateException("HEARTBEAT_HTTP_$code")
        c.inputStream.close()
        c.disconnect()
    }
    private fun poll(baseUrl: String, agentId: String, key: String): JSONObject? {
        val url = URL(baseUrl + "/api/device/poll?agent_id=" + URLEncoder.encode(agentId, "UTF-8"))
        val c = url.openConnection() as HttpURLConnection
        c.requestMethod = "GET"
        c.setRequestProperty("X-V12-Agent-Key", key)
        c.connectTimeout = 15000
        c.readTimeout = 20000
        val body = c.inputStream.bufferedReader().use { it.readText() }
        c.disconnect()
        val root = JSONObject(body)
        return if (root.has("task") && !root.isNull("task")) root.getJSONObject("task") else null
    }

    private fun report(baseUrl: String, agentId: String, key: String, taskId: String, result: JSONObject) {
        val payload = JSONObject()
            .put("task_id", taskId)
            .put("agent_id", agentId)
            .put("ok", result.optBoolean("ok"))
            .put("result", result.optJSONObject("result") ?: JSONObject())
            .put("error", result.optString("error", ""))

        val c = URL(baseUrl + "/api/device/report").openConnection() as HttpURLConnection
        c.requestMethod = "POST"
        c.doOutput = true
        c.setRequestProperty("X-V12-Agent-Key", key)
        c.setRequestProperty("Content-Type", "application/json")
        c.outputStream.use { it.write(payload.toString().toByteArray(StandardCharsets.UTF_8)) }
        c.inputStream.close()
        c.disconnect()
    }

    private fun execute(task: JSONObject): JSONObject {
        val name = task.optString("task")
        val params = task.optJSONObject("params") ?: JSONObject()
        if (!ALLOWED.contains(name)) return fail("TASK_NOT_ALLOWED")

        return try {
            when (name) {
                "internet_download" -> {
                    val urlText = params.optString("url", "").trim()
                    require(urlText.startsWith("https://") || urlText.startsWith("http://")) { "URL_SCHEME_NOT_ALLOWED" }
                    val name = params.optString("filename", "download.bin").replace(Regex("[^A-Za-z0-9._-]"), "_")
                    val target = safePath("Downloads/" + name)
                    val maxBytes = params.optLong("max_bytes", 50L * 1024L * 1024L).coerceIn(1L, 100L * 1024L * 1024L)
                    val conn = URL(urlText).openConnection() as HttpURLConnection
                    conn.connectTimeout = 15000
                    conn.readTimeout = 30000
                    conn.requestMethod = "GET"
                    conn.connect()
                    if (conn.responseCode !in 200..299) return fail("DOWNLOAD_HTTP_" + conn.responseCode)
                    val length = conn.contentLengthLong
                    if (length > maxBytes) return fail("DOWNLOAD_TOO_LARGE")
                    target.parentFile?.mkdirs()
                    var total = 0L
                    conn.inputStream.use { input ->
                        target.outputStream().use { output ->
                            val buf = ByteArray(8192)
                            while (true) {
                                val n = input.read(buf)
                                if (n <= 0) break
                                total += n
                                if (total > maxBytes) return fail("DOWNLOAD_TOO_LARGE")
                                output.write(buf, 0, n)
                            }
                        }
                    }
                    conn.disconnect()
                    ok(JSONObject().put("url", urlText).put("path", target.absolutePath).put("bytes", total))
                }
                "open_url" -> {
                    val urlText = params.optString("url", "").trim()
                    require(urlText.startsWith("https://") || urlText.startsWith("http://")) { "URL_SCHEME_NOT_ALLOWED" }
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(urlText)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(intent)
                    ok(JSONObject().put("url", urlText).put("opened", true))
                }
                "open_app" -> {
                    val packageName = params.optString("package", "").trim()
                    if (packageName.isBlank()) return fail("PACKAGE_REQUIRED")
                    val launch = packageManager.getLaunchIntentForPackage(packageName) ?: return fail("APP_NOT_INSTALLED")
                    launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(launch)
                    ok(JSONObject().put("package", packageName).put("opened", true))
                }
                "create_app_project" -> {
                    val projectName = params.optString("name", "BrainApp").replace(Regex("[^A-Za-z0-9_-]"), "_")
                    val files = params.optJSONObject("files") ?: return fail("FILES_REQUIRED")
                    val root = safePath("Apps/" + projectName)
                    if (!root.exists()) root.mkdirs()
                    val keys = files.keys()
                    var count = 0
                    while (keys.hasNext()) {
                        val rel = keys.next()
                        val body = files.optString(rel, "")
                        if (rel.contains("..") || rel.startsWith("/")) return fail("PATH_OUTSIDE_PROJECT")
                        if (body.toByteArray(StandardCharsets.UTF_8).size > 2 * 1024 * 1024) return fail("FILE_TOO_LARGE")
                        val out = File(root, rel).canonicalFile
                        require(out.path == root.canonicalPath || out.path.startsWith(root.canonicalPath + File.separator)) { "PATH_OUTSIDE_PROJECT" }
                        out.parentFile?.mkdirs()
                        out.writeText(body, StandardCharsets.UTF_8)
                        count++
                    }
                    ok(JSONObject().put("project", projectName).put("path", root.absolutePath).put("files", count).put("status", "CREATED"))
                }
                "chatgpt_ui_send" -> {
                    if (!params.optBoolean("approved", false)) return fail("EXPLICIT_APPROVAL_REQUIRED")
                    val message = params.optString("message", "").trim()
                    if (message.isBlank()) return fail("MESSAGE_REQUIRED")
                    val service = ChatGPTAccessibilityService.instance
                        ?: return fail("ACCESSIBILITY_SERVICE_NOT_CONNECTED")
                    ok(service.execute(message, params.optLong("timeout_ms", 120000L).coerceIn(5000L, 180000L)))
                }
                "queue_status" -> {
                    val items = QueueStore(this).load()
                    ok(JSONObject()
                        .put("count", items.size)
                        .put("states", JSONObject(items.groupingBy { it.state.name }.eachCount())))
                }
                "film_create" -> {
                    val dir = FilmFactory(this).createProduction(
                        params.optString("title", "Untitled Film"),
                        params.optInt("duration_sec", 60),
                        params.optInt("scene_count", 4)
                    )
                    ok(JSONObject().put("project_dir", dir.absolutePath).put("status", "QUEUED"))
                }
                "queue_enqueue" -> {
                    val taskName = params.optString("task")
                    if (taskName.isBlank()) return fail("TASK_REQUIRED")
                    val q = QueueStore(this).enqueue(
                        taskName,
                        params.optJSONObject("args") ?: JSONObject()
                    )
                    ok(JSONObject().put("queue_id", q.id).put("state", q.state.name))
                }
                "ffmpeg_probe" -> ok(JSONObject(FFmpegEngine(this).probe()))
                "ffmpeg_run" -> {
                    val a = params.optJSONArray("argv") ?: return fail("ARGV_REQUIRED")
                    val args = Array(a.length()) { i -> a.getString(i) }
                    ok(JSONObject(FFmpegEngine(this).run(args.toList())))
                }
                "verify_file" -> {
                    val file = safePath(params.optString("path", ""))
                    ok(JSONObject(VerificationEngine.file(file, params.optLong("min_bytes", 1L))))
                }
                "verify_media" -> {
                    val file = safePath(params.optString("path", ""))
                    ok(JSONObject(FFmpegEngine(this).probeMedia(file)))
                }
                "termux_probe" -> {
                    val installed = TermuxBridge.isInstalled(this)
                    if (!installed) {
                        ok(JSONObject().put("installed", false).put("ready", false).put("error", "TERMUX_NOT_INSTALLED"))
                    } else {
                        val result = TermuxBridge.run(
                            this,
                            "/data/data/com.termux/files/usr/bin/ffmpeg",
                            listOf("-version"),
                            timeoutMs = 20_000L
                        )
                        ok(JSONObject()
                            .put("installed", true)
                            .put("ready", result.exitCode == 0 && result.errorCode == 0)
                            .put("exit_code", result.exitCode)
                            .put("stdout", result.stdout.take(4000))
                            .put("stderr", result.stderr.take(2000))
                            .put("error", result.errorMessage))
                    }
                }
                "status" -> ok(JSONObject()
                    .put("device", "Android")
                    .put("model", Build.MODEL)
                    .put("manufacturer", Build.MANUFACTURER)
                    .put("sdk", Build.VERSION.SDK_INT)
                    .put("executor", "ElectronicBrain-AndroidExecutor")
                    .put("status", "READY"))
                "device_info" -> ok(JSONObject()
                    .put("model", Build.MODEL)
                    .put("manufacturer", Build.MANUFACTURER)
                    .put("sdk", Build.VERSION.SDK_INT)
                    .put("release", Build.VERSION.RELEASE)
                    .put("storage_root", baseDir().absolutePath))
                "platform" -> ok(JSONObject()
                    .put("system", "Android")
                    .put("release", Build.VERSION.RELEASE)
                    .put("sdk", Build.VERSION.SDK_INT)
                    .put("machine", Build.SUPPORTED_ABIS.firstOrNull() ?: "unknown"))
                "list_files" -> {
                    val dir = safePath(params.optString("path", ""))
                    ok(JSONObject()
                        .put("path", dir.absolutePath)
                        .put("files", (dir.listFiles()?.map { it.name } ?: emptyList()).joinToString("\n")))
                }
                "mkdir" -> {
                    val dir = safePath(params.optString("path", ""))
                    if (!dir.exists() && !dir.mkdirs()) fail("MKDIR_FAILED")
                    else ok(JSONObject().put("path", dir.absolutePath))
                }
                "read_file" -> {
                    val file = safePath(params.optString("path", ""))
                    if (!file.isFile) fail("FILE_NOT_FOUND")
                    else {
                        val max = params.optInt("max_bytes", 262144).coerceIn(1, 1048576)
                        val bytes = readAtMost(file, max)
                        ok(JSONObject()
                            .put("path", file.absolutePath)
                            .put("content", String(bytes, StandardCharsets.UTF_8)))
                    }
                }
                "write_text" -> {
                    val file = safePath(params.optString("path", ""))
                    file.parentFile?.mkdirs()
                    file.writeText(params.optString("content", ""), StandardCharsets.UTF_8)
                    ok(JSONObject().put("path", file.absolutePath).put("bytes", file.length()))
                }
                "run_toybox" -> {
                    val arr = params.optJSONArray("argv") ?: return fail("ARGV_REQUIRED")
                    val argv = mutableListOf<String>()
                    for (i in 0 until arr.length()) argv.add(arr.getString(i))
                    val command = argv.firstOrNull() ?: return fail("ARGV_EMPTY")
                    val allowed = setOf("id","uname","getprop","pwd","ls","df","du","mkdir","cp","mv","rm","cat")
                    if (command !in allowed) return fail("COMMAND_NOT_ALLOWED")
                    val p = ProcessBuilder("toybox", *argv.toTypedArray()).start()
                    val out = p.inputStream.bufferedReader().readText()
                    val err = p.errorStream.bufferedReader().readText()
                    val code = p.waitFor()
                    ok(JSONObject()
                        .put("exit_code", code)
                        .put("stdout", out.take(65536))
                        .put("stderr", err.take(65536)))
                }
                else -> fail("UNHANDLED_TASK")
            }
        } catch (e: Exception) {
            fail(e.javaClass.simpleName + ": " + (e.message ?: "unknown"))
        }
    }

    private fun readAtMost(file: File, maxBytes: Int): ByteArray {
        FileInputStream(file).use { input ->
            val out = ByteArray(maxBytes)
            var offset = 0
            while (offset < maxBytes) {
                val read = input.read(out, offset, maxBytes - offset)
                if (read <= 0) break
                offset += read
            }
            return if (offset == maxBytes) out else out.copyOf(offset)
        }
    }

    private fun baseDir() =
        File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_MOVIES), "ElectronicBrain")

    private fun safePath(relative: String): File {
        val root = baseDir().canonicalFile
        if (!root.exists()) root.mkdirs()
        val requested = if (relative.isBlank()) root else File(root, relative)
        val canonical = requested.canonicalFile
        require(canonical.path == root.path || canonical.path.startsWith(root.path + File.separator)) {
            "PATH_OUTSIDE_EXECUTOR_ROOT"
        }
        return canonical
    }

    private fun ok(result: JSONObject) = JSONObject().put("ok", true).put("result", result)
    private fun fail(error: String) =
        JSONObject().put("ok", false).put("result", JSONObject()).put("error", error)

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            getSystemService(NotificationManager::class.java)
                .createNotificationChannel(
                    NotificationChannel(
                        CHANNEL,
                        "Electronic Brain Executor",
                        NotificationManager.IMPORTANCE_LOW
                    )
                )
        }
    }

    private fun notification(text: String): Notification {
        val b = if (Build.VERSION.SDK_INT >= 26) Notification.Builder(this, CHANNEL)
        else Notification.Builder(this)
        return b.setContentTitle("Electronic Brain Executor")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java).notify(7, notification(text))
    }

    override fun onTimeout(startId: Int) {
        running = false
        executor.shutdownNow()
        stopSelf(startId)
    }

    override fun onDestroy() {
        running = false
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

package com.electronicbrain.androidexecutor

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
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
        private val ALLOWED = setOf("status","device_info","platform","list_files","mkdir","read_file","write_text","run_toybox","ffmpeg_probe","ffmpeg_run","verify_file","queue_status","queue_enqueue","film_create","termux_vps_preflight","termux_vps_deploy","termux_vps_health")
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
        val agentId = prefs.getString("agent_id", "android-executor-01") ?: "android-executor-01"
        val key = prefs.getString("agent_key", "") ?: ""
        val baseUrl = prefs.getString("brain_base_url", DEFAULT_BASE_URL)?.trimEnd('/') ?: DEFAULT_BASE_URL
        if (key.isBlank()) {
            updateNotification("ERROR: agent key missing")
            running = false
            return
        }

        updateNotification("READY: $agentId")
        while (running) {
            try {
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
                    Thread.sleep(POLL_MS)
                }
            } catch (e: Exception) {
                updateNotification("CONNECTION ERROR: " + (e.message ?: "unknown").take(80))
                Thread.sleep(5000)
            }
        }
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
                "termux_vps_preflight", "termux_vps_deploy", "termux_vps_health" -> {
                    ok(JSONObject(runEmbeddedTerminal(name.removePrefix("termux_vps_"))))
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
                    val args = List(a.length()) { i -> a.getString(i) }
                    ok(JSONObject(FFmpegEngine(this).run(args)))
                }
                "verify_file" -> {
                    val file = safePath(params.optString("path", ""))
                    ok(JSONObject(VerificationEngine.file(file, params.optLong("min_bytes", 1L))))
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
                    val p = ProcessBuilder("toybox", *argv).start()
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

    private fun runEmbeddedTerminal(operation: String): Map<String, Any> {
        val prefs = getSharedPreferences("executor", MODE_PRIVATE)
        val bash = prefs.getString("termux_bash", "")?.trim().orEmpty()
        val host = prefs.getString("vps_host", "")?.trim().orEmpty()
        if (bash.isBlank()) throw IllegalStateException("EMBEDDED_TERMUX_BASH_NOT_CONFIGURED")
        if (host.isBlank()) throw IllegalStateException("VPS_HOST_NOT_CONFIGURED")
        val script = File(filesDir, "brain-termux-autodeploy.sh")
        if (!script.exists()) {
            assets.open("brain-termux-autodeploy.sh").use { input ->
                script.outputStream().use { output -> input.copyTo(output) }
            }
            script.setExecutable(true)
        }
        val pb = ProcessBuilder(bash, script.absolutePath, operation)
        val env = pb.environment()
        env["BRAIN_VPS_HOST"] = host
        env["BRAIN_VPS_USER"] = prefs.getString("vps_user", "root")?.trim() ?: "root"
        env["BRAIN_SSH_PORT"] = prefs.getString("vps_port", "22")?.trim() ?: "22"
        prefs.getString("ssh_key_path", "")?.trim()?.takeIf { it.isNotBlank() }?.let { env["BRAIN_SSH_KEY"] = it }
        env["BRAIN_REPO"] = "https://github.com/omarenserat1980/MySimpleProject.git"
        val result = LocalTools.runProcess(pb, 20 * 60 * 1000L)
        return mapOf("operation" to operation, "exit_code" to result.first,
            "stdout" to result.second.takeLast(12000), "stderr" to result.third.takeLast(12000),
            "verified" to (result.first == 0))
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

    override fun onDestroy() {
        running = false
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

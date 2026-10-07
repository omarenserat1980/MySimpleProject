package com.electronicbrain.androidexecutor

import android.app.Activity
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

data class TermuxResult(
    val exitCode: Int,
    val stdout: String,
    val stderr: String,
    val errorCode: Int,
    val errorMessage: String
)

object TermuxBridge {
    const val EXTRA_EXECUTION_ID = "electronic_brain_execution_id"
    const val EXTRA_RESULT_BUNDLE = "com.termux.service.extra.plugin_result_bundle"

    private const val TERMUX_PACKAGE = "com.termux"
    private const val RUN_COMMAND_SERVICE = "com.termux.app.RunCommandService"
    private const val ACTION_RUN_COMMAND = "com.termux.RUN_COMMAND"
    private const val EXTRA_COMMAND_PATH = "com.termux.RUN_COMMAND_PATH"
    private const val EXTRA_ARGUMENTS = "com.termux.RUN_COMMAND_ARGUMENTS"
    private const val EXTRA_WORKDIR = "com.termux.RUN_COMMAND_WORKDIR"
    private const val EXTRA_BACKGROUND = "com.termux.RUN_COMMAND_BACKGROUND"
    private const val EXTRA_PENDING_INTENT = "com.termux.RUN_COMMAND_PENDING_INTENT"
    private const val RESULT_STDOUT = "com.termux.service.extra.plugin_result_bundle_stdout"
    private const val RESULT_STDERR = "com.termux.service.extra.plugin_result_bundle_stderr"
    private const val RESULT_EXIT = "com.termux.service.extra.plugin_result_bundle_exit_code"
    private const val RESULT_ERR = "com.termux.service.extra.plugin_result_bundle_err"
    private const val RESULT_ERRMSG = "com.termux.service.extra.plugin_result_bundle_errmsg"

    private data class Pending(val latch: CountDownLatch, @Volatile var result: TermuxResult? = null)

    private val nextId = AtomicInteger(1000)
    private val pending = ConcurrentHashMap<Int, Pending>()

    fun isInstalled(context: Context): Boolean =
        try {
            context.packageManager.getPackageInfo(TERMUX_PACKAGE, PackageManager.GET_ACTIVITIES)
            true
        } catch (_: Exception) {
            false
        }

    fun runBrainRuntimeLauncher(context: Context): TermuxResult {
        if (!isInstalled(context)) return TermuxResult(-1, "", "", -1, "TERMUX_NOT_INSTALLED")
        return runFixedCommand(context, "/data/data/com.termux/files/usr/bin/bash", listOf("/data/data/com.termux/files/home/MySimpleProject/brain_v12/tools/brain_runtime_launcher.sh"), timeoutMs = 120000L)
    }

    private fun runFixedCommand(context: Context, executable: String, arguments: List<String>, workDir: String = "/data/data/com.termux/files/home", timeoutMs: Long = 30 * 60 * 1000L): TermuxResult {
        require(executable == "/data/data/com.termux/files/usr/bin/bash") { "TERMUX_EXECUTABLE_NOT_ALLOWED" }
        require(arguments.size == 1 && arguments[0] == "/data/data/com.termux/files/home/MySimpleProject/brain_v12/tools/brain_runtime_launcher.sh") { "TERMUX_ARGUMENTS_NOT_ALLOWED" }
        return runInternal(context, executable, arguments, workDir, timeoutMs)
    }

    fun run(
        context: Context,
        executable: String,
        arguments: List<String>,
        workDir: String = "/data/data/com.termux/files/home",
        timeoutMs: Long = 30 * 60 * 1000L
    ): TermuxResult {
        require(executable == "/data/data/com.termux/files/usr/bin/ffmpeg" ||
                executable == "/data/data/com.termux/files/usr/bin/ffprobe") {
            "TERMUX_EXECUTABLE_NOT_ALLOWED"
        }
        return runInternal(context, executable, arguments, workDir, timeoutMs)
    }

    private fun runInternal(context: Context, executable: String, arguments: List<String>, workDir: String, timeoutMs: Long): TermuxResult {
        require(arguments.size <= 512) { "TERMUX_ARGUMENT_LIMIT" }
        if (!isInstalled(context)) {
            return TermuxResult(-1, "", "", -1, "TERMUX_NOT_INSTALLED")
        }

        val id = nextId.incrementAndGet()
        val p = Pending(CountDownLatch(1))
        pending[id] = p

        try {
            val callback = Intent(context, TermuxResultReceiver::class.java)
                .setPackage(context.packageName)
                .putExtra(EXTRA_EXECUTION_ID, id)

            var flags = PendingIntent.FLAG_ONE_SHOT
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                flags = flags or PendingIntent.FLAG_MUTABLE
            }

            val pendingIntent = PendingIntent.getBroadcast(context, id, callback, flags)

            val intent = Intent(ACTION_RUN_COMMAND).apply {
                setClassName(TERMUX_PACKAGE, RUN_COMMAND_SERVICE)
                putExtra(EXTRA_COMMAND_PATH, executable)
                putExtra(EXTRA_ARGUMENTS, arguments.toTypedArray())
                putExtra(EXTRA_WORKDIR, workDir)
                putExtra(EXTRA_BACKGROUND, true)
                putExtra(EXTRA_PENDING_INTENT, pendingIntent)
                putExtra("com.termux.RUN_COMMAND_COMMAND_LABEL", "Electronic Brain FFmpeg")
                putExtra("com.termux.RUN_COMMAND_COMMAND_DESCRIPTION", "Electronic Brain media execution requested by the authorized Brain Executor.")
            }

            context.startService(intent)

            if (!p.latch.await(timeoutMs, TimeUnit.MILLISECONDS)) {
                return TermuxResult(-1, "", "", -1, "TERMUX_COMMAND_TIMEOUT")
            }
            return p.result ?: TermuxResult(-1, "", "", -1, "TERMUX_RESULT_MISSING")
        } catch (e: SecurityException) {
            return TermuxResult(-1, "", "", -1, "TERMUX_PERMISSION_DENIED: ${e.message ?: "RUN_COMMAND permission required"}")
        } catch (e: Exception) {
            return TermuxResult(-1, "", "", -1, e.javaClass.simpleName + ": " + (e.message ?: "unknown"))
        } finally {
            pending.remove(id)
        }
    }

    fun complete(id: Int, bundle: Bundle) {
        val p = pending[id] ?: return
        p.result = TermuxResult(
            exitCode = bundle.getInt(RESULT_EXIT, -1),
            stdout = bundle.getString(RESULT_STDOUT, "") ?: "",
            stderr = bundle.getString(RESULT_STDERR, "") ?: "",
            errorCode = bundle.getInt(RESULT_ERR, Activity.RESULT_OK),
            errorMessage = bundle.getString(RESULT_ERRMSG, "") ?: ""
        )
        p.latch.countDown()
    }
}

package com.electronicbrain.androidexecutor

import android.content.Context
import java.io.File

class FFmpegEngine(private val context: Context) {
    private val factoryRoot = File("/storage/emulated/0/Movies/ElectronicBrain").apply { mkdirs() }
    private val appBin = File(context.filesDir, "bin/ffmpeg")
    private val appProbe = File(context.filesDir, "bin/ffprobe")

    fun available(): Boolean =
        appBin.canExecute() ||
        LocalTools.findBinary("ffmpeg") != null ||
        TermuxBridge.isInstalled(context)

    fun probe(): Map<String, Any> {
        val bin = binary()
        if (bin != null) {
            val r = LocalTools.run(listOf(bin.absolutePath, "-version"), 10_000L)
            return mapOf(
                "available" to (r.first == 0),
                "backend" to "local",
                "exit_code" to r.first,
                "stdout" to r.second.take(4000),
                "stderr" to r.third.take(2000)
            )
        }

        val r = TermuxBridge.run(
            context,
            "/data/data/com.termux/files/usr/bin/ffmpeg",
            listOf("-version"),
            timeoutMs = 20_000L
        )
        return mapOf(
            "available" to (r.exitCode == 0 && r.errorCode == 0),
            "backend" to "termux",
            "exit_code" to r.exitCode,
            "stdout" to r.stdout.take(4000),
            "stderr" to r.stderr.take(2000),
            "termux_error" to r.errorMessage
        )
    }

    fun run(args: List<String>, timeoutMs: Long = 30 * 60 * 1000L): Map<String, Any> {
        require(args.isNotEmpty()) { "FFmpeg args required" }
        args.forEach { require(!it.contains("..")) { "unsafe FFmpeg argument" } }

        val safeArgs = args.map {
            if (it.startsWith("/")) {
                val f = File(it).canonicalFile
                require(f.path.startsWith(factoryRoot.canonicalPath + File.separator)) {
                    "path outside factory root"
                }
                f.path
            } else it
        }

        val bin = binary()
        if (bin != null) {
            val r = LocalTools.run(listOf(bin.absolutePath) + safeArgs, timeoutMs)
            return mapOf(
                "ok" to (r.first == 0),
                "backend" to "local",
                "exit_code" to r.first,
                "stdout" to r.second.takeLast(8000),
                "stderr" to r.third.takeLast(8000)
            )
        }

        val r = TermuxBridge.run(
            context,
            "/data/data/com.termux/files/usr/bin/ffmpeg",
            safeArgs,
            workDir = "/storage/emulated/0/Movies/ElectronicBrain",
            timeoutMs = timeoutMs
        )
        return mapOf(
            "ok" to (r.exitCode == 0 && r.errorCode == 0),
            "backend" to "termux",
            "exit_code" to r.exitCode,
            "stdout" to r.stdout.takeLast(8000),
            "stderr" to r.stderr.takeLast(8000),
            "termux_error" to r.errorMessage
        )
    }

    fun probeMedia(path: File): Map<String, Any> {
        val f = path.canonicalFile
        require(f.path.startsWith(factoryRoot.canonicalPath + File.separator)) {
            "path outside factory root"
        }
        require(f.isFile) { "MEDIA_FILE_NOT_FOUND" }

        val args = listOf(
            "-v", "error",
            "-show_entries", "format=duration,size",
            "-show_entries", "stream=codec_type,codec_name,width,height",
            "-of", "json",
            f.path
        )

        val bin = if (appProbe.canExecute()) appProbe else LocalTools.findBinary("ffprobe")
        val r = if (bin != null) {
            val x = LocalTools.run(listOf(bin.absolutePath) + args, 60_000L)
            mapOf(
                "ok" to (x.first == 0),
                "backend" to "local",
                "exit_code" to x.first,
                "stdout" to x.second.takeLast(12000),
                "stderr" to x.third.takeLast(4000)
            )
        } else {
            val x = TermuxBridge.run(
                context,
                "/data/data/com.termux/files/usr/bin/ffprobe",
                args,
                workDir = "/storage/emulated/0/Movies/ElectronicBrain",
                timeoutMs = 60_000L
            )
            mapOf(
                "ok" to (x.exitCode == 0 && x.errorCode == 0),
                "backend" to "termux",
                "exit_code" to x.exitCode,
                "stdout" to x.stdout.takeLast(12000),
                "stderr" to x.stderr.takeLast(4000),
                "termux_error" to x.errorMessage
            )
        }

        return r + VerificationEngine.file(f, 1L)
    }

    private fun binary(): File? = when {
        appBin.canExecute() -> appBin
        else -> LocalTools.findBinary("ffmpeg")
    }
}

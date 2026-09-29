package com.electronicbrain.androidexecutor

import android.content.Context
import java.io.File

class FFmpegEngine(private val context: Context) {
    private val factoryRoot = File("/storage/emulated/0/Movies/ElectronicBrain").apply { mkdirs() }
    private val appBin = File(context.filesDir, "bin/ffmpeg")

    fun available(): Boolean = appBin.canExecute() || LocalTools.findBinary("ffmpeg") != null

    fun probe(): Map<String,Any> {
        val bin = binary() ?: return mapOf("available" to false, "error" to "FFmpeg binary not installed")
        val r=LocalTools.run(listOf(bin.absolutePath,"-version"),10_000L)
        return mapOf("available" to (r.first==0),"exit_code" to r.first,"stdout" to r.second.take(4000),"stderr" to r.third.take(2000))
    }

    fun run(args: List<String>, timeoutMs: Long=30*60*1000L): Map<String,Any> {
        require(args.isNotEmpty()) { "FFmpeg args required" }
        args.forEach { require(!it.contains("..")) { "unsafe FFmpeg argument" } }
        val bin=binary() ?: return mapOf("ok" to false,"error" to "FFmpeg binary not installed")
        val safeArgs=args.map {
            if(it.startsWith("/")) {
                val f=File(it).canonicalFile
                require(f.path.startsWith(factoryRoot.canonicalPath + File.separator)) { "path outside factory root" }
                f.path
            } else it
        }
        val r=LocalTools.run(listOf(bin.absolutePath)+safeArgs,timeoutMs)
        return mapOf("ok" to (r.first==0),"exit_code" to r.first,"stdout" to r.second.takeLast(8000),"stderr" to r.third.takeLast(8000))
    }

    private fun binary(): File? = when {
        appBin.canExecute() -> appBin
        else -> LocalTools.findBinary("ffmpeg")
    }
}

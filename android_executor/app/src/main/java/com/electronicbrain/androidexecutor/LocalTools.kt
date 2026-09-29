package com.electronicbrain.androidexecutor

import java.io.File

object LocalTools {
    fun runProcess(pb: ProcessBuilder, timeoutMs: Long = 120_000): Triple<Int,String,String> {
        val p = pb.redirectErrorStream(false).start()
        val stdout = StringBuilder()
        val stderr = StringBuilder()
        val outThread = Thread { p.inputStream.bufferedReader().useLines { it.forEach { stdout.append(it).append('\n') } } }
        val errThread = Thread { p.errorStream.bufferedReader().useLines { it.forEach { stderr.append(it).append('\n') } } }
        outThread.start(); errThread.start()
        val deadline = System.currentTimeMillis() + timeoutMs
        while (p.isAlive && System.currentTimeMillis() < deadline) Thread.sleep(50)
        if (p.isAlive) { p.destroyForcibly(); return Triple(-1, stdout.toString(), stderr.toString() + "TIMEOUT") }
        outThread.join(1000); errThread.join(1000)
        return Triple(p.exitValue(), stdout.toString(), stderr.toString())
    }

    fun findBinary(name: String): File? {
        val candidates = listOf(
            "/data/data/com.electronicbrain.androidexecutor/files/bin/$name",
            "/system/bin/$name",
            "/system/xbin/$name"
        )
        return candidates.map(::File).firstOrNull { it.canExecute() }
    }

    fun run(argv: List<String>, timeoutMs: Long = 120_000): Triple<Int,String,String> {
        require(argv.isNotEmpty())
        val p = ProcessBuilder(argv).redirectErrorStream(false).start()
        val stdout = StringBuilder()
        val stderr = StringBuilder()
        val outThread = Thread { p.inputStream.bufferedReader().useLines { it.forEach { stdout.append(it).append('\n') } } }
        val errThread = Thread { p.errorStream.bufferedReader().useLines { it.forEach { stderr.append(it).append('\n') } } }
        outThread.start(); errThread.start()
        val deadline = System.currentTimeMillis() + timeoutMs
        while (p.isAlive && System.currentTimeMillis() < deadline) Thread.sleep(50)
        if (p.isAlive) { p.destroyForcibly(); return -1 to stdout.toString() to (stderr.toString()+"TIMEOUT") }
        outThread.join(1000); errThread.join(1000)
        return Triple(p.exitValue(), stdout.toString(), stderr.toString())
    }
}

package com.electronicbrain.androidexecutor

import java.io.File
import java.security.MessageDigest

object VerificationEngine {
    fun file(path: File, minBytes: Long = 1): Map<String, Any> {
        val exists = path.exists() && path.isFile
        val size = if (exists) path.length() else 0L
        return mapOf(
            "exists" to exists,
            "size_bytes" to size,
            "size_ok" to (exists && size >= minBytes),
            "sha256" to if (exists) sha256(path) else ""
        )
    }

    private fun sha256(file: File): String {
        val md = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buf = ByteArray(8192)
            while (true) {
                val n = input.read(buf)
                if (n < 0) break
                md.update(buf, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
}

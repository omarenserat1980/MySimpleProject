package com.electronicbrain.androidexecutor

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.SecretKeyFactory

/**
 * Device-bound backup encryption backed by Android Keystore.
 *
 * The AES key is non-exportable and is never written beside the backup.
 * Backups can only be decrypted while this app installation retains its
 * Android Keystore alias. Uninstalling/clearing this app's data or resetting
 * the device can make existing backups permanently unrecoverable.
 */
object AndroidKeystoreBackup {
    private const val KEYSTORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "electronic_brain_backup_master_v1"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val TAG_BITS = 128
    private const val IV_BYTES = 12
    private const val BUFFER_BYTES = 1024 * 1024
    private val MAGIC = byteArrayOf(0x45, 0x42, 0x4b, 0x53, 0x54, 0x30, 0x31, 0x00) // EBKST01\0

    data class HardwareInfo(
        val providerAvailable: Boolean,
        val insideSecureHardware: Boolean?,
        val securityLevel: String,
        val keyAliasPresent: Boolean
    )

    @Synchronized
    private fun getOrCreateKey(): SecretKey {
        val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        val spec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .setUserAuthenticationRequired(false)
            .build()
        generator.init(spec)
        return generator.generateKey()
    }

    fun initialize(): HardwareInfo {
        getOrCreateKey()
        return inspect()
    }

    fun inspect(): HardwareInfo {
        val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        val present = store.containsAlias(KEY_ALIAS)
        val key = if (present) store.getKey(KEY_ALIAS, null) as? SecretKey else null
        val keyInfo = key?.let {
            SecretKeyFactory.getInstance(it.algorithm, KEYSTORE).getKeySpec(it, KeyInfo::class.java) as KeyInfo
        }
        val secure = keyInfo?.isInsideSecureHardware
        val level = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && keyInfo != null) {
            when (keyInfo.securityLevel) {
                KeyProperties.SECURITY_LEVEL_STRONGBOX -> "STRONGBOX"
                KeyProperties.SECURITY_LEVEL_TRUSTED_ENVIRONMENT -> "TRUSTED_ENVIRONMENT"
                KeyProperties.SECURITY_LEVEL_SOFTWARE -> "SOFTWARE"
                else -> "UNKNOWN"
            }
        } else if (secure == true) "SECURE_HARDWARE" else "UNKNOWN"
        return HardwareInfo(true, secure, level, present)
    }

    /**
     * Encrypts directly from a caller-owned stream into a private temporary
     * file. Plaintext is never staged as a second cache file.
     */
    fun encryptStream(source: InputStream, destination: File) {
        require(!destination.exists()) { "Refusing to overwrite an existing backup" }
        destination.parentFile?.mkdirs()
        val temp = File(destination.parentFile, destination.name + ".partial")
        require(!temp.exists()) { "Temporary output already exists; inspect it before retrying" }
        try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
            val iv = cipher.iv
            require(iv.size == IV_BYTES) { "Unexpected GCM IV length" }
            FileOutputStream(temp).use { rawOut ->
                BufferedOutputStream(rawOut).use { output ->
                    output.write(MAGIC)
                    output.write(1)
                    output.write(iv.size)
                    output.write(iv)
                    pumpEncrypt(BufferedInputStream(source), output, cipher)
                    output.flush()
                    rawOut.fd.sync()
                }
            }
            if (!temp.renameTo(destination)) throw IllegalStateException("Atomic backup finalization failed")
        } catch (t: Throwable) {
            temp.delete()
            throw t
        }
    }

    fun encryptFile(source: File, destination: File) {
        require(source.isFile && source.canRead()) { "Backup source is not readable" }
        require(!destination.exists()) { "Refusing to overwrite an existing backup" }
        destination.parentFile?.mkdirs()
        val temp = File(destination.parentFile, destination.name + ".partial")
        require(!temp.exists()) { "Temporary output already exists; inspect it before retrying" }
        try {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
            val iv = cipher.iv
            require(iv.size == IV_BYTES) { "Unexpected GCM IV length" }
            FileInputStream(source).use { rawIn ->
                BufferedInputStream(rawIn).use { input ->
                    FileOutputStream(temp).use { rawOut ->
                        BufferedOutputStream(rawOut).use { output ->
                            output.write(MAGIC)
                            output.write(1) // format version
                            output.write(iv.size)
                            output.write(iv)
                            pumpEncrypt(input, output, cipher)
                            output.flush()
                            rawOut.fd.sync()
                        }
                    }
                }
            }
            if (!temp.renameTo(destination)) throw IllegalStateException("Atomic backup finalization failed")
        } catch (t: Throwable) {
            temp.delete()
            throw t
        }
    }

    fun decryptFile(source: File, destination: File) {
        require(source.isFile && source.canRead()) { "Encrypted backup is not readable" }
        require(!destination.exists()) { "Refusing to overwrite an existing restore target" }
        destination.parentFile?.mkdirs()
        val temp = File(destination.parentFile, destination.name + ".partial")
        require(!temp.exists()) { "Temporary restore exists; inspect it before retrying" }
        try {
            FileInputStream(source).use { rawIn ->
                BufferedInputStream(rawIn).use { input ->
                    val magic = ByteArray(MAGIC.size)
                    readFully(input, magic)
                    require(magic.contentEquals(MAGIC)) { "Unrecognized backup format" }
                    require(input.read() == 1) { "Unsupported backup format version" }
                    val ivLength = input.read()
                    require(ivLength == IV_BYTES) { "Invalid GCM IV length" }
                    val iv = ByteArray(ivLength)
                    readFully(input, iv)

                    val cipher = Cipher.getInstance(TRANSFORMATION)
                    cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), GCMParameterSpec(TAG_BITS, iv))
                    FileOutputStream(temp).use { rawOut ->
                        BufferedOutputStream(rawOut).use { output ->
                            pumpDecrypt(input, output, cipher)
                            output.flush()
                            rawOut.fd.sync()
                        }
                    }
                }
            }
            if (!temp.renameTo(destination)) throw IllegalStateException("Atomic restore finalization failed")
        } catch (t: Throwable) {
            temp.delete()
            throw t
        }
    }

    private fun pumpEncrypt(input: InputStream, output: OutputStream, cipher: Cipher) {
        val buffer = ByteArray(BUFFER_BYTES)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            cipher.update(buffer, 0, count)?.let { output.write(it) }
        }
        output.write(cipher.doFinal())
    }

    private fun pumpDecrypt(input: InputStream, output: OutputStream, cipher: Cipher) {
        val buffer = ByteArray(BUFFER_BYTES)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            cipher.update(buffer, 0, count)?.let { output.write(it) }
        }
        // GCM authentication is verified here. A failure deletes the .partial file.
        output.write(cipher.doFinal())
    }

    private fun readFully(input: InputStream, target: ByteArray) {
        var offset = 0
        while (offset < target.size) {
            val count = input.read(target, offset, target.size - offset)
            require(count >= 0) { "Truncated encrypted backup" }
            offset += count
        }
    }
}

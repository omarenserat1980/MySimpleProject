package com.electronicbrain.androidexecutor

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import java.io.File
import java.util.UUID

class MainActivity : ComponentActivity() {
    private var backupOperation: String = ""
    private var backupStatus: TextView? = null

    private val backupInput = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val outputName = if (backupOperation == "encrypt") "ElectronicBrain-Backup.ebkst" else "ElectronicBrain-Restored.tar"
            backupOutput.launch(outputName)
            selectedBackupUri = uri
        }
    }

    private var selectedBackupUri: Uri? = null

    private val backupOutput = registerForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { outputUri ->
        val inputUri = selectedBackupUri
        selectedBackupUri = null
        if (outputUri == null || inputUri == null) {
            backupStatus?.text = "Backup operation cancelled"
            return@registerForActivityResult
        }
        runBackupOperation(inputUri, outputUri, backupOperation)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("executor", MODE_PRIVATE)
        val agentId = EditText(this).apply {
            hint = "V12_AGENT_ID"
            setText(prefs.getString("agent_id", "realme-rmx3710"))
        }
        val brainUrl = EditText(this).apply {
            hint = "BRAIN_BASE_URL"
            setText(prefs.getString("brain_base_url", "http://127.0.0.1:8012"))
        }
        val agentKey = EditText(this).apply {
            hint = "V12_AGENT_KEY"
            setText(prefs.getString("agent_key", ""))
        }
        val status = TextView(this).apply {
            text = "STOPPED"
            textSize = 16f
            setPadding(0, 24, 0, 24)
        }
        val start = Button(this).apply {
            text = "START EXECUTOR"
            setOnClickListener {
                prefs.edit().putString("agent_id", agentId.text.toString().trim())
                    .putString("agent_key", agentKey.text.toString().trim())
                    .putString("brain_base_url", brainUrl.text.toString().trim())
                    .apply()
                if (Build.VERSION.SDK_INT >= 33)
                    ActivityCompat.requestPermissions(this@MainActivity, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 100)
                val i = Intent(this@MainActivity, ExecutorService::class.java)
                    .setAction(ExecutorService.ACTION_START)
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
                status.text = "STARTING…"
            }
        }
        val stop = Button(this).apply {
            text = "STOP EXECUTOR"
            setOnClickListener {
                stopService(Intent(this@MainActivity, ExecutorService::class.java))
                status.text = "STOPPED"
            }
        }
        val accessibility = Button(this).apply {
            text = "ENABLE CHATGPT MEDIATOR"
            setOnClickListener { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        }
        val storage = Button(this).apply {
            text = "ALLOW ALL FILES"
            setOnClickListener {
                if (Build.VERSION.SDK_INT >= 30) startActivity(
                    Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                )
            }
        }

        val keyStatus = TextView(this).apply {
            text = "Backup key: not checked"
            textSize = 14f
            setPadding(0, 16, 0, 8)
        }
        backupStatus = keyStatus
        val inspectKey = Button(this).apply {
            text = "INITIALIZE / CHECK SECURE BACKUP KEY"
            setOnClickListener {
                keyStatus.text = "Checking Android Keystore…"
                Thread {
                    try {
                        val info = AndroidKeystoreBackup.initialize()
                        runOnUiThread {
                            keyStatus.text = "Keystore: AVAILABLE | Level: ${info.securityLevel} | Hardware-backed: ${info.insideSecureHardware} | Alias present: ${info.keyAliasPresent}"
                        }
                    } catch (t: Throwable) {
                        runOnUiThread { keyStatus.text = "Keystore error: ${t.javaClass.simpleName}: ${t.message}" }
                    }
                }.start()
            }
        }
        val encryptBackup = Button(this).apply {
            text = "ENCRYPT BACKUP WITH ANDROID KEYSTORE"
            setOnClickListener {
                backupOperation = "encrypt"
                backupInput.launch(arrayOf("*/*"))
            }
        }
        val decryptBackup = Button(this).apply {
            text = "RESTORE / DECRYPT BACKUP"
            setOnClickListener {
                backupOperation = "decrypt"
                backupInput.launch(arrayOf("*/*"))
            }
        }

        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 48, 32, 32)
            addView(TextView(this@MainActivity).apply {
                text = "ELECTRONIC BRAIN\nANDROID EXECUTOR & SECURE BACKUP"
                textSize = 22f
            })
            addView(agentId); addView(agentKey); addView(brainUrl)
            addView(start); addView(stop); addView(accessibility); addView(storage); addView(status)
            addView(TextView(this@MainActivity).apply {
                text = "DEVICE-BOUND BACKUP — KEEP THIS APP INSTALLED AND ITS DATA INTACT"
                textSize = 13f
                setPadding(0, 20, 0, 8)
            })
            addView(inspectKey); addView(encryptBackup); addView(decryptBackup); addView(keyStatus)
            addView(TextView(this@MainActivity).apply {
                text = "Brain Cloud is the primary runtime. Android Keystore backup keys are non-exportable and this backup cannot be restored on another installation unless a separate recovery key is configured."
                textSize = 12f
            })
        })
    }

    private fun runBackupOperation(inputUri: Uri, outputUri: Uri, operation: String) {
        backupStatus?.text = "Preparing secure file operation…"
        Thread {
            val token = UUID.randomUUID().toString()
            val inputFile = File(cacheDir, "eb-input-$token.tmp")
            val outputFile = File(cacheDir, "eb-output-$token.tmp")
            try {
                if (operation == "encrypt") {
                    // Stream source directly into encryption; do not stage plaintext in cache.
                    contentResolver.openInputStream(inputUri).use { source ->
                        requireNotNull(source) { "Cannot read selected source" }
                        AndroidKeystoreBackup.encryptStream(source, outputFile)
                    }
                } else {
                    // Ciphertext may be staged privately; plaintext is produced only after GCM authentication.
                    contentResolver.openInputStream(inputUri).use { source ->
                        requireNotNull(source) { "Cannot read selected encrypted backup" }
                        inputFile.outputStream().use { target -> source.copyTo(target) }
                    }
                    AndroidKeystoreBackup.decryptFile(inputFile, outputFile)
                }
                contentResolver.openOutputStream(outputUri, "w").use { target ->
                    requireNotNull(target) { "Cannot open selected destination" }
                    outputFile.inputStream().use { source -> source.copyTo(target) }
                    target.flush()
                }
                runOnUiThread { backupStatus?.text = if (operation == "encrypt") "ENCRYPTION COMPLETE — verify the .ebkst file before deleting any source" else "AUTHENTICATED DECRYPTION COMPLETE — restore archive is ready" }
            } catch (t: Throwable) {
                runOnUiThread { backupStatus?.text = "Backup failed: ${t.javaClass.simpleName}: ${t.message}" }
            } finally {
                inputFile.delete()
                outputFile.delete()
            }
        }.start()
    }
}

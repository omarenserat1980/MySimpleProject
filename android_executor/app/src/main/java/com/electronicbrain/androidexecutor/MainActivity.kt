package com.electronicbrain.androidexecutor

import android.Manifest
import android.content.Intent
import android.app.AlertDialog
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import org.json.JSONArray
import org.json.JSONObject
import java.util.Base64

class MainActivity : ComponentActivity() {
    private lateinit var statusView: TextView
    private var pendingAttestationChallenge: ByteArray? = null

    private val createAttestationDocument = registerForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        val challenge = pendingAttestationChallenge
        pendingAttestationChallenge = null
        if (uri == null) {
            statusView.text = "ATTESTATION_EXPORT_CANCELLED; no key was created"
            return@registerForActivityResult
        }
        val output = runCatching { contentResolver.openOutputStream(uri) }.getOrNull()
        if (output == null) {
            statusView.text = "ATTESTATION_EXPORT_FAILED; output stream unavailable; no key was created"
            return@registerForActivityResult
        }
        if (challenge == null) {
            output.close()
            statusView.text = "ATTESTATION_EXPORT_FAILED; challenge missing; no key was created"
            return@registerForActivityResult
        }
        runCatching {
            output.bufferedWriter(Charsets.UTF_8).use { writer ->
                // Key creation is deliberately after the user chooses an export destination.
                val material = PhoneIdentityKeyStore.createEnrollmentKey(challenge)
                val chain = JSONArray()
                material.attestationChainPem.forEach { chain.put(it) }
                val evidence = JSONObject()
                    .put("schema", "brain-phone-base.android-attestation-export.v1")
                    .put("captured_at_device_action", true)
                    .put("application_id", packageName)
                    .put("key_id_sha256", material.keyId)
                    .put("public_key_pem", material.publicKeyPem)
                    .put("attestation_chain_pem", chain)
                    .put("attestation_challenge_sha256", material.attestationChallengeSha256)
                    .put("attestation_verification", "NOT_PERFORMED")
                    .put("evidence_classification", "LOCAL_ATTESTATION_CHAIN_UNVERIFIED")
                    .put("device_identity_verified", false)
                    .put("trusted", false)
                    .put("active", false)
                    .put("manual_approval", "NOT_GRANTED")
                    .put("mining", "DISABLED")
                    .put("network_upload", false)
                    .put("node_registration", false)
                writer.write(evidence.toString(2))
                writer.write("\n")
            }
        }.onSuccess {
            statusView.text = "ATTESTATION_CHAIN_EXPORTED_LOCALLY\nVerification NOT performed. Device remains untrusted/inactive; mining disabled.\n$uri"
        }.onFailure { error ->
            statusView.text = "ATTESTATION_EXPORT_FAILED\n${error.message ?: error.javaClass.simpleName}\nIf the key was created, do not retry: the alias is intentionally non-overwritable. No trust or activation was granted."
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("executor", MODE_PRIVATE)
        val agentId = EditText(this).apply {
            hint = "V12_AGENT_ID"
            setText(prefs.getString("agent_id", "android-executor-redmi3-01"))
        }
        val brainUrl = EditText(this).apply {
            hint = "BRAIN_BASE_URL"
            setText(prefs.getString("brain_base_url", "http://127.0.0.1:8012"))
        }
        val agentKey = EditText(this).apply {
            hint = "V12_AGENT_KEY"
            setText(prefs.getString("agent_key", ""))
        }
        statusView = TextView(this).apply {
            text = "STOPPED"
            textSize = 16f
            setPadding(0, 24, 0, 24)
        }
        val identityProbe = Button(this).apply {
            text = "CHECK PHONE IDENTITY SUPPORT"
            setOnClickListener {
                val result = PhoneIdentityKeyStore.probeCapabilities(this@MainActivity)
                statusView.text = JSONObject(result).toString(2)
            }
        }
        val attestationChallenge = EditText(this).apply {
            hint = "Base64 challenge from independently verified enrollment authority (32+ bytes)"
        }
        val exportAttestation = Button(this).apply {
            text = "CREATE & EXPORT ATTESTATION CHAIN"
            setOnClickListener {
                val challenge = runCatching {
                    Base64.getDecoder().decode(attestationChallenge.text.toString().trim())
                }.getOrNull()
                if (challenge == null || challenge.size < 32) {
                    statusView.text = "INVALID_CHALLENGE; enter valid Base64 for an independently issued challenge of at least 32 bytes"
                    return@setOnClickListener
                }
                AlertDialog.Builder(this@MainActivity)
                    .setTitle("Create local identity key?")
                    .setMessage("This creates a non-exportable Android Keystore key and exports its public certificate chain to a file you choose. The key alias cannot be overwritten automatically. No network upload, node registration, trust, activation, or mining occurs. Use only a challenge whose origin/signature you independently verified.")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Choose export file") { _, _ ->
                        pendingAttestationChallenge = challenge.copyOf()
                        createAttestationDocument.launch("brain-phone-attestation-${System.currentTimeMillis()}.json")
                    }
                    .show()
            }
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
                statusView.text = "STARTING…"
            }
        }
        val stop = Button(this).apply {
            text = "STOP EXECUTOR"
            setOnClickListener {
                stopService(Intent(this@MainActivity, ExecutorService::class.java))
                statusView.text = "STOPPED"
            }
        }
        val accessibility = Button(this).apply {
            text = "ENABLE CHATGPT MEDIATOR"
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
        }
        val storage = Button(this).apply {
            text = "ALLOW ALL FILES"
            setOnClickListener {
                if (Build.VERSION.SDK_INT >= 30) startActivity(
                    Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                )
            }
        }
        setContentView(ScrollView(this).apply {
            isFillViewport = true
            addView(LinearLayout(this@MainActivity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 48, 32, 32)
            addView(TextView(this@MainActivity).apply {
                text = "ELECTRONIC BRAIN\nOPTIONAL ANDROID CLIENT"
                textSize = 22f
            })
            addView(agentId); addView(agentKey); addView(brainUrl)
            addView(identityProbe); addView(attestationChallenge); addView(exportAttestation)
            addView(start); addView(stop)
            addView(accessibility); addView(storage); addView(statusView)
            addView(TextView(this@MainActivity).apply {
                text = "Brain Cloud is the primary runtime.\nThis Android client is optional and never required for cloud operation."
                textSize = 13f
            })
            })
        })
    }
}

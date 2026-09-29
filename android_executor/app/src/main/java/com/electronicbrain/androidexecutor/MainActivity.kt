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
import androidx.core.app.ActivityCompat

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getPreferences(MODE_PRIVATE)
        val agentId = EditText(this).apply {
            hint = "V12_AGENT_ID"
            setText(prefs.getString("agent_id", "android-executor-01"))
        }
        val brainUrl = EditText(this).apply {
            hint = "BRAIN_BASE_URL"
            setText(prefs.getString("brain_base_url", "http://127.0.0.1:8012"))
        }
        val termuxBash = EditText(this).apply {
            hint = "EMBEDDED_TERMUX_BASH"
            setText(prefs.getString("termux_bash", ""))
        }
        val vpsHost = EditText(this).apply {
            hint = "VPS_HOST"
            setText(prefs.getString("vps_host", ""))
        }
        val vpsUser = EditText(this).apply {
            hint = "VPS_USER"
            setText(prefs.getString("vps_user", "root"))
        }
        val vpsPort = EditText(this).apply {
            hint = "VPS_SSH_PORT"
            setText(prefs.getString("vps_port", "22"))
        }
        val sshKey = EditText(this).apply {
            hint = "SSH_KEY_PATH (local only)"
            setText(prefs.getString("ssh_key_path", ""))
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
                    .putString("termux_bash", termuxBash.text.toString().trim())
                    .putString("vps_host", vpsHost.text.toString().trim())
                    .putString("vps_user", vpsUser.text.toString().trim())
                    .putString("vps_port", vpsPort.text.toString().trim())
                    .putString("ssh_key_path", sshKey.text.toString().trim()).apply()
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
        val storage = Button(this).apply {
            text = "ALLOW ALL FILES"
            setOnClickListener {
                if (Build.VERSION.SDK_INT >= 30) startActivity(
                    Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
                )
            }
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 48, 32, 32)
            addView(TextView(this@MainActivity).apply {
                text = "ELECTRONIC BRAIN\nPHONE-ONLY ANDROID EXECUTOR"
                textSize = 22f
            })
            addView(agentId); addView(agentKey); addView(brainUrl); addView(termuxBash); addView(vpsHost); addView(vpsUser); addView(vpsPort); addView(sshKey); addView(start); addView(stop); addView(storage); addView(status)
            addView(TextView(this@MainActivity).apply {
                text = "Brain URL: configurable\nEmbedded Termux → VPS deployment\nOutput: /storage/emulated/0/Movies/ElectronicBrain/"
                textSize = 13f
            })
        })
    }
}

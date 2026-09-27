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
                    .putString("agent_key", agentKey.text.toString().trim()).apply()
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
            addView(agentId); addView(agentKey); addView(start); addView(stop); addView(storage); addView(status)
            addView(TextView(this@MainActivity).apply {
                text = "Brain: https://electronic-brain-v12-gwwg.onrender.com\nOutput: /storage/emulated/0/Movies/ElectronicBrain/"
                textSize = 13f
            })
        })
    }
}

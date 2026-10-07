package com.electronicbrain.androidexecutor

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.graphics.Typeface
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat

class MainActivity : ComponentActivity() {
    private val cortex = BrainCortex()

    private fun label(text: String, size: Float = 15f, bold: Boolean = false): TextView =
        TextView(this).apply {
            this.text = text
            textSize = size
            if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(0, 8, 0, 8)
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = getSharedPreferences("executor", MODE_PRIVATE)

        val agentId = EditText(this).apply {
            hint = "V12_AGENT_ID"
            setText(prefs.getString("agent_id", "redmi3-01"))
        }
        val brainUrl = EditText(this).apply {
            hint = "BRAIN_BASE_URL"
            setText(prefs.getString("brain_base_url", "http://127.0.0.1:8012"))
        }
        val agentKey = EditText(this).apply {
            hint = "V12_AGENT_KEY"
            setText(prefs.getString("agent_key", ""))
        }

        val status = label("CORTEX: READY", 17f, true)
        val capabilities = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        cortex.snapshot().forEach { capability ->
            capabilities.addView(label(capability.name + ": " + capability.state))
        }

        val start = Button(this).apply {
            text = "START BRAIN EXECUTOR"
            setOnClickListener {
                prefs.edit()
                    .putString("agent_id", agentId.text.toString().trim())
                    .putString("agent_key", agentKey.text.toString().trim())
                    .putString("brain_base_url", brainUrl.text.toString().trim())
                    .apply()
                if (Build.VERSION.SDK_INT >= 33) {
                    ActivityCompat.requestPermissions(
                        this@MainActivity,
                        arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                        100
                    )
                }
                val i = Intent(this@MainActivity, ExecutorService::class.java)
                    .setAction(ExecutorService.ACTION_START)
                if (Build.VERSION.SDK_INT >= 26) startForegroundService(i) else startService(i)
                status.text = "CORTEX: EXECUTOR START REQUESTED"
            }
        }

        val stop = Button(this).apply {
            text = "STOP EXECUTOR"
            setOnClickListener {
                stopService(Intent(this@MainActivity, ExecutorService::class.java))
                status.text = "CORTEX: EXECUTOR STOPPED"
            }
        }

        val accessibility = Button(this).apply {
            text = "OPEN ACCESSIBILITY GATE"
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
            }
        }

        val storage = Button(this).apply {
            text = "OPEN STORAGE PERMISSION"
            setOnClickListener {
                if (Build.VERSION.SDK_INT >= 30) startActivity(
                    Intent(
                        Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                        Uri.parse("package:" + packageName)
                    )
                )
            }
        }

        val constitution = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            cortex.constitution().forEachIndexed { index, rule ->
                addView(label((index + 1).toString() + ". " + rule, 13f))
            }
        }

        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 36, 32, 32)
            addView(label("BRAIN CORTEX", 28f, true))
            addView(label("Android Habitat v1", 15f))
            addView(label("One Brain -> one orchestrated execution path", 13f))
            addView(status)
            addView(label("LOCAL CAPABILITIES", 18f, true))
            addView(capabilities)
            addView(label("AGENT CONFIGURATION", 18f, true))
            addView(agentId)
            addView(agentKey)
            addView(brainUrl)
            addView(start)
            addView(stop)
            addView(accessibility)
            addView(storage)
            addView(label("BRAIN CONSTITUTION", 18f, true))
            addView(constitution)
            addView(label("Sensitive actions remain behind explicit Android permission gates.", 12f))
        })
    }
}

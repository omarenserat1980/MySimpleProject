package com.brain.hondaconnect;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.graphics.Color;
import android.widget.*;

public class BrainCloudActivity extends Activity {
    TextView serverStatus;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28,28,28,28);
        root.setBackgroundColor(Color.rgb(12,12,16));

        TextView title = new TextView(this);
        title.setText("BRAIN PHONE SERVER\nCINEMATIC V3 PRO");
        title.setTextSize(25);
        title.setTextColor(Color.WHITE);
        root.addView(title);

        TextView info = new TextView(this);
        info.setText("الهاتف = عقدة BRAIN Cloud Hub محلية. السيرفر يعمل في الخلفية على المنفذ 8787.");
        info.setTextColor(Color.LTGRAY);
        info.setPadding(0,20,0,20);
        root.addView(info);

        Button start = new Button(this);
        start.setText("▶ تشغيل BRAIN Phone Server");
        root.addView(start);

        Button stop = new Button(this);
        stop.setText("■ إيقاف السيرفر");
        root.addView(stop);

        Button browser = new Button(this);\n        browser.setText("🌐 فتح BRAIN Browser");\n        root.addView(browser);\n\n        Button terminal = new Button(this);
        terminal.setText("⌘ فتح BRAIN Termux Emulator");
        root.addView(terminal);

        Button termux = new Button(this);
        termux.setText("⚙ تشغيل Full Cloud Hub عبر Termux الحقيقي");
        root.addView(termux);

        serverStatus = new TextView(this);
        serverStatus.setTextColor(Color.WHITE);
        serverStatus.setPadding(0,24,0,12);
        root.addView(serverStatus);

        TextView api = new TextView(this);
        api.setTextColor(Color.LTGRAY);
        api.setText("API: /healthz   /v1/status   |   Emulator: virtual shell   |   Factory: Python + FFmpeg");
        root.addView(api);

        setContentView(root);
        refreshStatus();

        start.setOnClickListener(v -> startServer());
        stop.setOnClickListener(v -> stopServer());
        browser.setOnClickListener(v -> startActivity(new Intent(this, BrainBrowserActivity.class)));\n        terminal.setOnClickListener(v -> startActivity(new Intent(this, BrainTermuxActivity.class)));
        termux.setOnClickListener(v -> openTermux());
    }

    private void startServer() {
        try {
            Intent i = new Intent(this, BrainServerService.class);
            if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(i);
            else startService(i);
            serverStatus.setText("🟢 BRAIN Phone Server يعمل على 0.0.0.0:8787");
        } catch (Exception e) {
            serverStatus.setText("فشل التشغيل: " + e.getMessage());
        }
    }

    private void stopServer() {
        stopService(new Intent(this, BrainServerService.class));
        serverStatus.setText("🔴 متوقف");
    }

    private void openTermux() {
        // Port 8787 is owned by the Android Phone Server. Stop it before
        // launching the real Termux Cloud Hub so both runtimes never compete
        // for the same listening socket.
        stopService(new Intent(this, BrainServerService.class));
        serverStatus.setText("🟡 Phone Server stopped — opening real Termux Cloud Hub...");
        try {
            Intent i = new Intent();
            i.setClassName("com.termux", "com.termux.app.TermuxActivity");
            startActivity(i);
            serverStatus.setText("تم فتح Termux الحقيقي. شغّل termux/setup_brain_phone_server.sh لتشغيل Full Cloud Hub على 8787.");
        } catch (Exception e) {
            serverStatus.setText("Termux الحقيقي غير مثبت. استخدم BRAIN Termux Emulator.");
        }
    }

    private void refreshStatus() {
        serverStatus.setText("جاهز — شغّل السيرفر أو افتح المحاكي.");
    }
}
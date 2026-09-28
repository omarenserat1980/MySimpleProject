package com.brain.hondaconnect;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.view.View;
import android.widget.*;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

public class BrainCloudActivity extends Activity {
    EditText portInput;
    TextView serverStatus;
    ServerSocket serverSocket;
    ExecutorService pool;
    volatile boolean running = false;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        buildUi();
    }

    private void buildUi() {
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
        info.setTextColor(Color.LTGRAY);
        info.setText("حوّل الهاتف إلى عقدة BRAIN محلية عبر Wi‑Fi.");
        info.setPadding(0,20,0,20);
        root.addView(info);

        portInput = new EditText(this);
        portInput.setHint("Port");
        portInput.setText("8787");
        portInput.setSingleLine(true);
        root.addView(portInput);

        Button start = new Button(this);
        start.setText("▶ تشغيل السيرفر");
        root.addView(start);

        Button stop = new Button(this);
        stop.setText("■ إيقاف السيرفر");
        root.addView(stop);

        serverStatus = new TextView(this);
        serverStatus.setTextColor(Color.WHITE);
        serverStatus.setPadding(0,24,0,12);
        root.addView(serverStatus);

        TextView api = new TextView(this);
        api.setTextColor(Color.LTGRAY);
        api.setText("API: /healthz   /v1/status   /");
        root.addView(api);

        setContentView(root);
        refreshStatus();

        start.setOnClickListener(v -> startServer());
        stop.setOnClickListener(v -> stopServer());
    }

    private void startServer() {
        if (running) return;
        final int port;
        try { port = Integer.parseInt(portInput.getText().toString().trim()); }
        catch (Exception e) { serverStatus.setText("منفذ غير صالح"); return; }
        if (port < 1024 || port > 65535) {
            serverStatus.setText("اختر منفذًا بين 1024 و65535");
            return;
        }
        try {
            serverSocket = new ServerSocket(port);
            pool = Executors.newCachedThreadPool();
            running = true;
            pool.execute(() -> acceptLoop());
            refreshStatus();
        } catch (Exception e) {
            serverStatus.setText("فشل التشغيل: " + e.getMessage());
        }
    }

    private void acceptLoop() {
        while (running) {
            try {
                Socket socket = serverSocket.accept();
                pool.execute(() -> handle(socket));
            } catch (IOException e) {
                if (running) runOnUiThread(() ->
                    serverStatus.setText("خطأ السيرفر: " + e.getMessage()));
            }
        }
    }

    private void handle(Socket socket) {
        try (Socket s = socket;
             BufferedReader in = new BufferedReader(new InputStreamReader(s.getInputStream(), "UTF-8"));
             OutputStream out = s.getOutputStream()) {

            String first = in.readLine();
            if (first == null) return;
            String[] parts = first.split(" ");
            String path = parts.length > 1 ? parts[1] : "/";
            while (true) {
                String line = in.readLine();
                if (line == null || line.isEmpty()) break;
            }

            String body;
            if (path.equals("/healthz")) {
                body = "{\"status\":\"ok\",\"server\":\"BRAIN Phone Server\"}";
            } else if (path.equals("/v1/status")) {
                body = "{\"service\":\"BRAIN Phone Server\",\"role\":\"phone_server\",\"port\":" +
                        serverSocket.getLocalPort() + ",\"running\":true,\"next\":\"Termux can run the full BRAIN Cloud Hub\"}";
            } else {
                body = "{\"service\":\"BRAIN Phone Server\",\"status\":\"online\",\"endpoints\":[\"/healthz\",\"/v1/status\"]}";
            }

            byte[] data = body.getBytes("UTF-8");
            String headers = "HTTP/1.1 200 OK\r\n" +
                    "Content-Type: application/json; charset=utf-8\r\n" +
                    "Content-Length: " + data.length + "\r\n" +
                    "Connection: close\r\n\r\n";
            out.write(headers.getBytes("UTF-8"));
            out.write(data);
            out.flush();
        } catch (Exception ignored) {}
    }

    private void stopServer() {
        running = false;
        try { if (serverSocket != null) serverSocket.close(); } catch (Exception ignored) {}
        if (pool != null) pool.shutdownNow();
        refreshStatus();
    }

    private void refreshStatus() {
        if (serverStatus == null) return;
        if (!running) {
            serverStatus.setText("🔴 متوقف");
            return;
        }
        serverStatus.setText("🟢 يعمل\n" + localUrls());
    }

    private String localUrls() {
        StringBuilder s = new StringBuilder();
        try {
            Enumeration<NetworkInterface> nets = NetworkInterface.getNetworkInterfaces();
            while (nets.hasMoreElements()) {
                NetworkInterface ni = nets.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                Enumeration<InetAddress> addrs = ni.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress a = addrs.nextElement();
                    if (a instanceof Inet4Address && !a.isLoopbackAddress()) {
                        s.append("http://").append(a.getHostAddress())
                         .append(":").append(serverSocket.getLocalPort()).append("\n");
                    }
                }
            }
        } catch (Exception ignored) {}
        return s.toString().trim();
    }

    @Override protected void onDestroy() {
        stopServer();
        super.onDestroy();
    }
}

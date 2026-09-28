package com.brain.hondaconnect;

import android.app.*;
import android.content.*;
import android.os.*;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

public class BrainServerService extends Service {
    private ServerSocket serverSocket;
    private ExecutorService pool;
    private volatile boolean running;

    @Override public void onCreate() {
        super.onCreate();
        startForeground(1001, notification());
        startServer(8787);
    }

    private Notification notification() {
        String channelId = "brain_server";
        NotificationManager nm = (NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(
                channelId, "BRAIN Phone Server", NotificationManager.IMPORTANCE_LOW));
        }
        return new Notification.Builder(this, channelId)
            .setContentTitle("BRAIN Phone Server")
            .setContentText("BRAIN Cloud Hub node is running")
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setOngoing(true)
            .build();
    }

    private void startServer(int port) {
        try {
            serverSocket = new ServerSocket(port);
            pool = Executors.newCachedThreadPool();
            running = true;
            pool.execute(() -> {
                while (running) {
                    try { pool.execute(() -> handle(serverSocketAccept())); }
                    catch (Exception e) { if (running) break; }
                }
            });
        } catch (Exception e) {
            stopSelf();
        }
    }

    private Socket serverSocketAccept() throws IOException {
        return serverSocket.accept();
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
            if ("/healthz".equals(path)) {
                body = "{\"status\":\"ok\",\"server\":\"BRAIN Phone Server\",\"role\":\"phone_server\"}";
            } else if ("/v1/status".equals(path)) {
                body = "{\"service\":\"BRAIN Phone Server\",\"role\":\"phone_server\",\"running\":true,\"port\":8787}";
            } else {
                body = "{\"service\":\"BRAIN Phone Server\",\"status\":\"online\",\"endpoints\":[\"/healthz\",\"/v1/status\"]}";
            }
            byte[] data = body.getBytes("UTF-8");
            String headers = "HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\nContent-Length: "
                + data.length + "\r\nConnection: close\r\n\r\n";
            out.write(headers.getBytes("UTF-8"));
            out.write(data);
            out.flush();
        } catch (Exception ignored) {}
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override public void onDestroy() {
        running = false;
        try { if (serverSocket != null) serverSocket.close(); } catch (Exception ignored) {}
        if (pool != null) pool.shutdownNow();
        super.onDestroy();
    }

    @Override public android.os.IBinder onBind(Intent intent) { return null; }
}

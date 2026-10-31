package com.brain.hondaconnect;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class BrainServerService extends Service {
    private static final int PORT = 8787;
    private static final int MAX_THREADS = 4;
    private static final String LOOPBACK = "127.0.0.1";

    private ServerSocket serverSocket;
    private ExecutorService pool;
    private volatile boolean running;

    @Override
    public void onCreate() {
        super.onCreate();
        startForeground(1001, notification());
        startServer();
    }

    private Notification notification() {
        String channelId = "brain_server";
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(new NotificationChannel(
                channelId, "BRAIN Phone Server", NotificationManager.IMPORTANCE_LOW));
        }
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? new Notification.Builder(this, channelId)
            : new Notification.Builder(this);
        return builder
            .setContentTitle("BRAIN Phone Server")
            .setContentText("Local-only BRAIN endpoint is running")
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setOngoing(true)
            .build();
    }

    private void startServer() {
        try {
            serverSocket = new ServerSocket();
            serverSocket.setReuseAddress(true);
            serverSocket.bind(new InetSocketAddress(InetAddress.getByName(LOOPBACK), PORT), 16);
            pool = Executors.newFixedThreadPool(MAX_THREADS);
            running = true;
            pool.execute(() -> {
                while (running) {
                    try {
                        Socket client = serverSocket.accept();
                        pool.execute(() -> handle(client));
                    } catch (Exception error) {
                        if (running) {
                            stopSelf();
                        }
                        break;
                    }
                }
            });
        } catch (Exception error) {
            running = false;
            stopSelf();
        }
    }

    private void handle(Socket socket) {
        try (Socket client = socket;
             BufferedReader input = new BufferedReader(
                 new InputStreamReader(client.getInputStream(), StandardCharsets.UTF_8));
             OutputStream output = client.getOutputStream()) {
            client.setSoTimeout(5000);
            String requestLine = input.readLine();
            if (requestLine == null || requestLine.length() > 2048) {
                writeResponse(output, 400, "Bad Request", "{\"error\":\"bad_request\"}");
                return;
            }

            String[] parts = requestLine.split(" ");
            if (parts.length < 2) {
                writeResponse(output, 400, "Bad Request", "{\"error\":\"bad_request\"}");
                return;
            }

            String method = parts[0];
            String path = parts[1];
            int queryIndex = path.indexOf('?');
            if (queryIndex >= 0) {
                path = path.substring(0, queryIndex);
            }

            int headerCount = 0;
            String line;
            while ((line = input.readLine()) != null && !line.isEmpty() && headerCount++ < 64) {
                // Consume bounded request headers; no request body is accepted.
            }

            if (!"GET".equals(method)) {
                writeResponse(output, 405, "Method Not Allowed", "{\"error\":\"method_not_allowed\"}");
            } else if ("/healthz".equals(path)) {
                writeResponse(output, 200, "OK",
                    "{\"status\":\"ok\",\"server\":\"BRAIN Phone Server\",\"role\":\"phone_server\"}");
            } else if ("/v1/status".equals(path)) {
                writeResponse(output, 200, "OK",
                    "{\"service\":\"BRAIN Phone Server\",\"role\":\"phone_server\",\"running\":true,\"host\":\"127.0.0.1\",\"port\":8787}");
            } else {
                writeResponse(output, 404, "Not Found", "{\"error\":\"not_found\"}");
            }
        } catch (Exception ignored) {
            // A malformed or disconnected local client must not terminate the service.
        }
    }

    private void writeResponse(OutputStream output, int code, String reason, String body) throws Exception {
        byte[] data = body.getBytes(StandardCharsets.UTF_8);
        String headers = "HTTP/1.1 " + code + " " + reason + "\r\n"
            + "Content-Type: application/json; charset=utf-8\r\n"
            + "Content-Length: " + data.length + "\r\n"
            + "Cache-Control: no-store\r\n"
            + "X-Content-Type-Options: nosniff\r\n"
            + "Connection: close\r\n\r\n";
        output.write(headers.getBytes(StandardCharsets.UTF_8));
        output.write(data);
        output.flush();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        running = false;
        try {
            if (serverSocket != null) serverSocket.close();
        } catch (Exception ignored) {
        }
        if (pool != null) pool.shutdownNow();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}

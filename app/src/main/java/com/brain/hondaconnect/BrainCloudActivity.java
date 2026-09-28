package com.brain.hondaconnect;

import android.app.*;
import android.os.*;
import android.graphics.Color;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.net.*;
import org.json.*;

public class BrainCloudActivity extends Activity {
    EditText url, token;
    TextView status, pipeline;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28,28,28,28);
        TextView title = new TextView(this);
        title.setText("BRAIN CLOUD HUB\nCINEMATIC V3 PRO");
        title.setTextSize(25);
        title.setTextColor(Color.WHITE);
        root.setBackgroundColor(Color.rgb(12,12,16));
        root.addView(title);

        url = new EditText(this);
        url.setHint("https://your-brain-cloud.example");
        url.setSingleLine(true);
        root.addView(url);

        token = new EditText(this);
        token.setHint("BRAIN_CONTROL_TOKEN");
        token.setSingleLine(true);
        token.setInputType(0x00000081);
        root.addView(token);

        Button connect = new Button(this);
        connect.setText("اتصال بـ BRAIN Cloud");
        root.addView(connect);

        Button film = new Button(this);
        film.setText("🎬 إنشاء فيلم");
        root.addView(film);

        pipeline = new TextView(this);
        pipeline.setText("Script → Scenes → Images → Motion → Audio → Render → QC");
        pipeline.setTextColor(Color.LTGRAY);
        pipeline.setPadding(0,24,0,12);
        root.addView(pipeline);

        status = new TextView(this);
        status.setText("غير متصل");
        status.setTextColor(Color.WHITE);
        root.addView(status);
        setContentView(root);

        connect.setOnClickListener(v -> request("/v1/status"));
        film.setOnClickListener(v -> request("/v1/films"));
    }

    private void request(String path) {
        final String base = url.getText().toString().trim().replaceAll("/+$","");
        final String auth = token.getText().toString().trim();
        if (base.isEmpty()) { status.setText("أدخل عنوان BRAIN Cloud"); return; }
        status.setText("جاري الاتصال...");
        new Thread(() -> {
            try {
                HttpURLConnection c=(HttpURLConnection)new URL(base+path).openConnection();
                c.setRequestMethod(path.equals("/v1/films") ? "POST" : "GET");
                c.setConnectTimeout(10000); c.setReadTimeout(15000);
                if(!auth.isEmpty()) c.setRequestProperty("Authorization","Bearer "+auth);
                if(path.equals("/v1/films")) {
                    c.setDoOutput(true);
                    c.setRequestProperty("Content-Type","application/json");
                    String body="{\"profile\":\"CINEMATIC V3 PRO\",\"source\":\"mobile\",\"mode\":\"cloud\"}";
                    try(OutputStream o=c.getOutputStream()){o.write(body.getBytes("UTF-8"));}
                }
                int code=c.getResponseCode();
                InputStream stream=code>=400?c.getErrorStream():c.getInputStream();
                StringBuilder s=new StringBuilder();
                if(stream!=null){byte[] buf=new byte[2048]; int n; while((n=stream.read(buf))!=-1)s.append(new String(buf,0,n,"UTF-8"));}
                final String result=s.toString();
                runOnUiThread(() -> status.setText("HTTP "+code+"\n"+result));
            } catch(Exception e) {
                runOnUiThread(() -> status.setText("خطأ اتصال: "+e.getMessage()));
            }
        }).start();
    }
}

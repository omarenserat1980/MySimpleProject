package com.brain.hondaconnect;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.widget.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.Scanner;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class BrainTermuxActivity extends Activity {
    private TextView terminal;
    private EditText input;
    private final Map<String,String> env = new HashMap<>();
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private File brainHome;
    private String lastJobId = "";

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        brainHome = new File(getFilesDir(), "brain_home");
        new File(brainHome, "bin").mkdirs();
        new File(brainHome, "brain").mkdirs();
        new File(brainHome, "cinematic_output").mkdirs();
        new File(brainHome, ".brain_state").mkdirs();
        env.put("HOME", brainHome.getAbsolutePath());
        env.put("PREFIX", new File(getFilesDir(), "usr").getAbsolutePath());
        env.put("BRAIN_MODE", "phone");
        env.put("BRAIN_PORT", "8787");
        buildUi();
        print("BRAIN TERMUX EMULATOR v3.0\\nLocal Cloud Hub bridge enabled.\\nSystem shell execution remains blocked.\\nType 'help'.\\n$ ");
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(16,16,16,16);
        root.setBackgroundColor(Color.rgb(8,10,8));

        TextView header = new TextView(this);
        header.setText("BRAIN • PHONE TERMINAL v3");
        header.setTextColor(Color.WHITE);
        header.setTextSize(18);
        header.setTypeface(Typeface.MONOSPACE, Typeface.BOLD);
        root.addView(header);

        terminal = new TextView(this);
        terminal.setTextColor(Color.rgb(190,255,190));
        terminal.setTextSize(14);
        terminal.setTypeface(Typeface.MONOSPACE);
        terminal.setGravity(Gravity.TOP);
        terminal.setPadding(8,12,8,12);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(terminal);
        root.addView(scroll, new LinearLayout.LayoutParams(-1,0,1));

        LinearLayout row = new LinearLayout(this);
        input = new EditText(this);
        input.setSingleLine(true);
        input.setHint("command");
        input.setTextColor(Color.WHITE);
        input.setHintTextColor(Color.GRAY);
        input.setTypeface(Typeface.MONOSPACE);
        row.addView(input, new LinearLayout.LayoutParams(0,-2,1));
        Button run = new Button(this);
        run.setText("RUN");
        row.addView(run);
        root.addView(row);

        run.setOnClickListener(v -> executeInput());
        input.setOnEditorActionListener((v,a,e) -> { executeInput(); return true; });
        setContentView(root);
    }

    private void executeInput() {
        String cmd = input.getText().toString().trim();
        input.setText("");
        if (!cmd.isEmpty()) print("\n$ " + cmd + "\n" + execute(cmd) + "\n$ ");
    }

    private String execute(String cmd) {
        if (cmd.equals("help")) return
            "BRAIN commands:\n" +
            "  pwd | ls | cd DIR\n" +
            "  mkdir NAME | touch NAME | rm NAME\n" +
            "  cat NAME | echo TEXT | env\n" +
            "  status | health | brain | processes\n" +
            "  factory TITLE | job ID | ffmpeg | qc ID\n" +
            "  clear | exit";
        if (cmd.equals("pwd")) return brainHome.getAbsolutePath();
        if (cmd.equals("ls")) {
            File[] files = brainHome.listFiles();
            if (files == null) return "";
            StringBuilder s = new StringBuilder();
            for (File f : files) s.append(f.getName()).append(f.isDirectory()?"/  ":"  ");
            return s.toString();
        }
        if (cmd.startsWith("cd ")) { try { return "cwd -> " + resolve(cmd.substring(3)).getAbsolutePath(); } catch(Exception e) { return "error: " + e.getMessage(); } }
        if (cmd.startsWith("mkdir ")) { try { File f=resolve(cmd.substring(6)); return f.mkdirs() ? "created "+f.getName() : "exists/failed"; } catch(Exception e){return "error: "+e.getMessage();} }
        if (cmd.startsWith("touch ")) {
            try { File f=resolve(cmd.substring(6)); if(f.exists()||f.createNewFile()) return "created "+f.getName(); }
            catch(Exception e){ return "error: "+e.getMessage(); }
            return "failed";
        }
        if (cmd.startsWith("rm ")) { try { File f=resolve(cmd.substring(3)); return f.delete() ? "removed "+f.getName() : "not removed"; } catch(Exception e){return "error: "+e.getMessage();} }
        if (cmd.startsWith("cat ")) {
            try { Scanner sc=new Scanner(resolve(cmd.substring(4))); StringBuilder s=new StringBuilder(); while(sc.hasNextLine())s.append(sc.nextLine()).append("\n"); sc.close(); return s.toString(); }
            catch(Exception e){ return "error: "+e.getMessage(); }
        }
        if (cmd.equals("env")) return "HOME="+env.get("HOME")+"\nPREFIX="+env.get("PREFIX")+"\nBRAIN_MODE=phone\nBRAIN_PORT=8787";
        if (cmd.equals("status")) { request("GET","/v1/status",null,"STATUS"); return "STATUS: querying local Cloud Hub..."; }
        if (cmd.equals("health")) { request("GET","/healthz",null,"HEALTH"); return "HEALTH: querying 127.0.0.1:8787..."; }
        if (cmd.equals("brain")) return "API | Movie Factory | CinematicLocalRenderer | FFmpeg | QC";
        if (cmd.equals("factory")) return "usage: factory TITLE";
        if (cmd.startsWith("factory ")) {
            String title=cmd.substring(8).trim();
            if(title.isEmpty()) return "usage: factory TITLE";
            String body="{\"title\":\""+jsonEscape(title)+"\",\"target_minutes\":1,\"language\":\"ar\"}";
            request("POST","/v1/films",body,"FACTORY");
            return "FACTORY: submitting real local film job...";
        }
        if (cmd.startsWith("job ")) { String id=cmd.substring(4).trim(); try { if(id.isEmpty())return "usage: job ID"; request("GET","/v1/films/"+safeId(id),null,"JOB"); return "JOB: querying "+id; } catch(Exception e) { return "error: "+e.getMessage(); } }
        if (cmd.equals("ffmpeg")) { request("GET","/v1/platform",null,"FFMPEG"); return "FFMPEG: querying factory capabilities..."; }
        if (cmd.equals("qc")) return lastJobId.isEmpty() ? "usage: qc JOB_ID" : "QC: query "+lastJobId+" with 'qc "+lastJobId+"'";
        if (cmd.startsWith("qc ")) { String id=cmd.substring(3).trim(); try { if(id.isEmpty())return "usage: qc JOB_ID"; request("GET","/v1/films/"+safeId(id),null,"QC"); return "QC: querying verified state for "+id; } catch(Exception e) { return "error: "+e.getMessage(); } }
        if (cmd.equals("processes")) return "brain-phone-server [Android]\nbrain-termux-emulator [UI]\ncloud-hub-bridge [HTTP localhost]";
        if (cmd.equals("clear")) { terminal.setText(""); return ""; }
        if (cmd.equals("exit")) { finish(); return ""; }
        if (cmd.startsWith("echo ")) return cmd.substring(5);
        return "command not found: "+cmd+"\nType 'help'.";
    }

    private String safeId(String id) {
        if (!id.matches("[A-Za-z0-9_-]{1,64}")) throw new IllegalArgumentException("invalid job id");
        return id;
    }

    private String jsonEscape(String s) {
        return s.replace("\\\\","\\\\\\\\").replace("\"","\\\\\"");
    }

    private File resolve(String path) throws IOException {
        if(path == null || path.trim().isEmpty() || path.startsWith("/")) throw new SecurityException("absolute paths are blocked");
        File base=brainHome.getCanonicalFile();
        File f=new File(base,path).getCanonicalFile();
        String prefix=base.getPath()+File.separator;
        if(!f.getPath().equals(base.getPath()) && !f.getPath().startsWith(prefix)) throw new SecurityException("path escapes BRAIN HOME");
        return f;
    }

    private void request(String method,String path,String body,String label) {
        network.submit(() -> {
            HttpURLConnection c=null;
            try {
                c=(HttpURLConnection)new URL("http://127.0.0.1:8787"+path).openConnection();
                c.setRequestMethod(method);
                c.setConnectTimeout(1500);
                c.setReadTimeout(10000);
                c.setRequestProperty("Content-Type","application/json");
                c.setRequestProperty("X-BRAIN-Local-App","1");
                if(body!=null) {
                    c.setDoOutput(true);
                    try(OutputStream out=c.getOutputStream()){out.write(body.getBytes(StandardCharsets.UTF_8));}
                }
                int code=c.getResponseCode();
                InputStream stream=code>=400?c.getErrorStream():c.getInputStream();
                StringBuilder b=new StringBuilder();
                if(stream!=null){BufferedReader r=new BufferedReader(new InputStreamReader(stream,StandardCharsets.UTF_8));String line;while((line=r.readLine())!=null)b.append(line);}
                String result=label+" HTTP "+code+"\\n"+b;
                if(label.equals("FACTORY")){
                    String marker="\"id\":\"";
                    int p=b.indexOf(marker);
                    if(p>=0){int s=p+marker.length(),e=b.indexOf("\"",s);if(e>s)lastJobId=b.substring(s,e);}
                }
                final String out=result;
                runOnUiThread(() -> print("\n"+out+"\n$ "));
            } catch(Exception e) {
                runOnUiThread(() -> print("\n"+label+" ERROR: "+e.getMessage()+"\n$ "));
            } finally { if(c!=null)c.disconnect(); }
        });
    }

    @Override protected void onDestroy() {
        network.shutdownNow();
        super.onDestroy();
    }

    private void print(String s) {
        terminal.append(s);
        terminal.post(() -> { View p=terminal.getParent(); if(p instanceof ScrollView)((ScrollView)p).fullScroll(View.FOCUS_DOWN); });
    }
}

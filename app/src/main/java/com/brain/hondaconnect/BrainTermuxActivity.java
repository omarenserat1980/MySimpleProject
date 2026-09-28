package com.brain.hondaconnect;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.widget.*;
import java.io.File;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;

public class BrainTermuxActivity extends Activity {
    private TextView terminal;
    private EditText input;
    private final Map<String,String> env = new HashMap<>();
    private File brainHome;
    private final ExecutorService network = Executors.newSingleThreadExecutor();
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
        print("BRAIN TERMUX EMULATOR v2.0\nPersistent virtual filesystem enabled.\nType 'help'.\n$ ");
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(16,16,16,16);
        root.setBackgroundColor(Color.rgb(8,10,8));

        TextView header = new TextView(this);
        header.setText("BRAIN • PHONE TERMINAL v2");
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
            "  cat NAME | echo TEXT\n" +
            "  env | status | health | brain\n" +
            "  factory | ffmpeg | qc | processes\n" +
            "  clear | exit";
        if (cmd.equals("pwd")) return brainHome.getAbsolutePath();
        if (cmd.equals("ls")) {
            File[] files = brainHome.listFiles();
            if (files == null) return "";
            StringBuilder s = new StringBuilder();
            for (File f : files) s.append(f.getName()).append(f.isDirectory()?"/  ":"  ");
            return s.toString();
        }
        if (cmd.startsWith("cd ")) return "cwd -> " + resolve(cmd.substring(3)).getAbsolutePath();
        if (cmd.startsWith("mkdir ")) {
            File f=resolve(cmd.substring(6)); return f.mkdirs() ? "created "+f.getName() : "exists/failed";
        }
        if (cmd.startsWith("touch ")) {
            try { File f=resolve(cmd.substring(6)); if(f.exists()||f.createNewFile()) return "created "+f.getName(); }
            catch(Exception e){ return "error: "+e.getMessage(); }
            return "failed";
        }
        if (cmd.startsWith("rm ")) {
            File f=resolve(cmd.substring(3)); return f.delete() ? "removed "+f.getName() : "not removed";
        }
        if (cmd.startsWith("cat ")) {
            try { java.util.Scanner sc=new java.util.Scanner(resolve(cmd.substring(4))); StringBuilder s=new StringBuilder(); while(sc.hasNextLine())s.append(sc.nextLine()).append("\n"); sc.close(); return s.toString(); }
            catch(Exception e){ return "error: "+e.getMessage(); }
        }
        if (cmd.equals("env")) return "HOME="+env.get("HOME")+"\nPREFIX="+env.get("PREFIX")+"\nBRAIN_MODE=phone\nBRAIN_PORT=8787";
        if (cmd.equals("status")) return "Phone Server: Android Foreground Service\nHTTP: 8787\nFactory route: local_ffmpeg_cinematic";
        if (cmd.equals("health")) return "BRAIN Phone Server /healthz -> local endpoint on :8787";
        if (cmd.equals("brain")) return "API | Movie Factory | CinematicLocalRenderer | FFmpeg | QC";
        if (cmd.equals("factory")) return "FACTORY: READY\nUse real Termux for Python production execution.";
        if (cmd.equals("ffmpeg")) return "FFmpeg: configured in real Termux path.";
        if (cmd.equals("qc")) return "QC gate: video + audio + duration + resolution + file-size checks.";
        if (cmd.equals("processes")) return "brain-phone-server [Android]\nbrain-termux-emulator [UI]";
        if (cmd.equals("clear")) { terminal.setText(""); return ""; }
        if (cmd.equals("exit")) { finish(); return ""; }
        if (cmd.startsWith("echo ")) return cmd.substring(5);
        return "command not found: "+cmd+"\nType 'help'.";
    }

    private File resolve(String path) {
        File f = path.startsWith("/") ? new File(path) : new File(brainHome, path);
        try { return f.getCanonicalFile(); } catch(Exception e) { return f; }
    }

    private void print(String s) {
        terminal.append(s);
        terminal.post(() -> { View p=terminal.getParent(); if(p instanceof ScrollView)((ScrollView)p).fullScroll(View.FOCUS_DOWN); });
    }
}
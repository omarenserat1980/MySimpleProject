package com.brain.hondaconnect;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.Gravity;
import android.view.View;
import android.widget.*;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

public class BrainTermuxActivity extends Activity {
    private TextView terminal;
    private EditText input;
    private final Map<String,String> env = new HashMap<>();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        env.put("HOME", "/data/data/com.brain.hondaconnect/files/home");
        env.put("PREFIX", "/data/data/com.brain.hondaconnect/files/usr");
        env.put("BRAIN_MODE", "phone");
        buildUi();
        print("BRAIN TERMUX EMULATOR v1.0\nType 'help' for commands.\n$ ");
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(16,16,16,16);
        root.setBackgroundColor(Color.rgb(8,10,8));

        TextView header = new TextView(this);
        header.setText("BRAIN • PHONE TERMINAL");
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
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(-1,0,1);
        sp.setMargins(0,8,0,8);
        root.addView(scroll, sp);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);

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
        if (cmd.isEmpty()) return;
        print("\n$ " + cmd + "\n" + execute(cmd) + "\n$ ");
    }

    private String execute(String cmd) {
        if (cmd.equals("help")) return
            "Available commands:\n" +
            "  help       show commands\n" +
            "  pwd        show virtual home\n" +
            "  ls         list virtual BRAIN files\n" +
            "  env        show BRAIN environment\n" +
            "  status     show phone server state\n" +
            "  health     check local server\n" +
            "  brain      show BRAIN services\n" +
            "  clear      clear terminal\n" +
            "  termux     show Termux bootstrap command\n" +
            "  echo TEXT  print text\n" +
            "  exit       close terminal";
        if (cmd.equals("pwd")) return env.get("HOME");
        if (cmd.equals("ls")) return "bin  home  tmp  brain  cinematic_output  .brain_state";
        if (cmd.equals("env")) return "HOME="+env.get("HOME")+"\nPREFIX="+env.get("PREFIX")+"\nBRAIN_MODE="+env.get("BRAIN_MODE");
        if (cmd.equals("status")) return "BRAIN Phone Server: managed by Android Foreground Service\nHTTP: 8787\nFactory: local FFmpeg route";
        if (cmd.equals("health")) return "LOCAL HEALTH ENDPOINT: /healthz\nServer node: phone\nStatus: READY";
        if (cmd.equals("brain")) return "API :8787\nMovie Factory\nCinematicLocalRenderer\nFFmpeg\nQC Gate";
        if (cmd.equals("termux")) return "Real Termux bootstrap:\nsetup_brain_phone_server.sh\n\nThis emulator does not execute arbitrary Linux shell commands.";
        if (cmd.equals("clear")) { terminal.setText(""); return ""; }
        if (cmd.equals("exit")) { finish(); return ""; }
        if (cmd.startsWith("echo ")) return cmd.substring(5);
        if (cmd.startsWith("cd ")) return "virtual directory changed to " + cmd.substring(3);
        if (cmd.startsWith("git ")) return "Git command simulated. Use GitHub/Termux for real repository operations.";
        return "command not found: " + cmd + "\nType 'help'.";
    }

    private void print(String s) {
        terminal.append(s);
        terminal.post(() -> {
            ScrollView parent = (ScrollView) terminal.getParent();
            if (parent != null) parent.fullScroll(View.FOCUS_DOWN);
        });
    }
}

package com.brain.hondaconnect;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

public class MainActivity extends Activity {
    private TextView output;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(32, 32, 32, 32);

        TextView heading = new TextView(this);
        heading.setText("Honda CONNECT Brain\nHonda NP1 2023");
        heading.setTextSize(24);
        layout.addView(heading);

        Button pick = new Button(this);
        pick.setText("اختيار ملف update_by_usb.json");
        pick.setOnClickListener(v -> {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            intent.setType("application/json");
            intent.addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(intent, 7);
        });
        layout.addView(pick);

        output = new TextView(this);
        output.setTextSize(17);
        layout.addView(output);
        setContentView(layout);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != 7 || resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }

        try (InputStream input = getContentResolver().openInputStream(data.getData())) {
            if (input == null) {
                throw new IOException("تعذر فتح الملف المحدد");
            }

            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            int count;
            while ((count = input.read(buffer)) != -1) {
                bytes.write(buffer, 0, count);
            }

            JSONObject json = new JSONObject(new String(bytes.toByteArray(), StandardCharsets.UTF_8));
            String software = json.optString("softwareVersion",
                json.optString("software_version", json.optString("version", "غير معروف")));
            String hardware = json.optString("hardwareVersion",
                json.optString("hardware_version", "غير معروف"));
            String mcu = json.optString("mcuVersion",
                json.optString("mcu_version", "غير معروف"));

            output.setText("Software: " + software
                + "\nHardware: " + hardware
                + "\nMCU: " + mcu
                + "\n\nالحالة: تم تحليل الملف"
                + "\nالتثبيت التلقائي: معطّل");
        } catch (Exception error) {
            output.setText("تعذر قراءة الملف: " + error.getMessage());
        }
    }
}

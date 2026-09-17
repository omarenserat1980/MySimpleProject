package com.foras.ads;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Button;
import android.view.ViewGroup;

public class MainActivity extends Activity {
    private static final String DEFAULT_URL = "http://127.0.0.1:8080/";
    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        EditText url = new EditText(this);
        url.setHint("عنوان خادم Foras Ads");
        url.setText(DEFAULT_URL);
        Button open = new Button(this);
        open.setText("فتح البرنامج");
        WebView web = new WebView(this);
        web.setWebViewClient(new WebViewClient());
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        open.setOnClickListener(v -> {
            String value = url.getText().toString().trim();
            if (!value.startsWith("http://") && !value.startsWith("https://")) value = "http://" + value;
            web.loadUrl(value.endsWith("/") ? value : value + "/");
        });
        root.addView(url, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(open, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(web, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(root);
    }
}

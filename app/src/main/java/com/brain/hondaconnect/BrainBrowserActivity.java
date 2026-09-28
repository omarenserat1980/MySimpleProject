package com.brain.hondaconnect;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.app.DownloadManager;
import android.os.Environment;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.*;
import android.webkit.URLUtil;
import android.widget.*;

import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Set;

public class BrainBrowserActivity extends Activity {
    private WebView web;
    private EditText address;
    private TextView title;
    private SharedPreferences prefs;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("brain_browser", MODE_PRIVATE);
        buildUi();
        loadHome();
    }

    private void buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(5,11,20));

        LinearLayout bar = new LinearLayout(this);
        bar.setPadding(10,10,10,6);
        bar.setBackgroundColor(Color.rgb(8,20,34));

        Button back = button("‹");
        Button forward = button("›");
        Button reload = button("↻");
        address = new EditText(this);
        address.setSingleLine(true);
        address.setHint("ابحث أو اكتب عنوانًا");
        address.setTextColor(Color.WHITE);
        address.setHintTextColor(Color.rgb(145,165,188));
        address.setBackgroundColor(Color.rgb(12,28,45));
        address.setPadding(18,0,18,0);
        address.setImeOptions(EditorInfo.IME_ACTION_GO);
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(0,54,1);
        ap.setMargins(6,0,6,0);

        Button home = button("⌂");
        Button bookmark = button("☆");
        bookmark.setOnLongClickListener(v -> { showBookmarks(); return true; });
        Button share = button("↗");

        bar.addView(back); bar.addView(forward); bar.addView(reload);
        bar.addView(address, ap);
        bar.addView(home); bar.addView(bookmark); bar.addView(share);
        root.addView(bar);

        title = new TextView(this);
        title.setTextColor(Color.rgb(145,165,188));
        title.setTextSize(11);
        title.setPadding(16,2,16,6);
        root.addView(title);

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setSupportZoom(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);
        s.setUserAgentString(s.getUserAgentString() + " BRAINBrowser/1.0");
        web.setBackgroundColor(Color.BLACK);
        web.setWebViewClient(new BrowserClient());
        web.setWebChromeClient(new WebChromeClient());
        web.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            try {
                DownloadManager.Request req = new DownloadManager.Request(Uri.parse(url));
                req.setMimeType(mimeType);
                req.addRequestHeader("User-Agent", userAgent);
                req.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                String name = URLUtil.guessFileName(url, contentDisposition, mimeType);
                req.setTitle(name);
                req.setDestinationInExternalFilesDir(this, Environment.DIRECTORY_DOWNLOADS, name);
                ((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(req);
                Toast.makeText(this, "بدأ تنزيل: " + name, Toast.LENGTH_SHORT).show();
            } catch (Exception e) {
                Toast.makeText(this, "تعذر بدء التنزيل", Toast.LENGTH_SHORT).show();
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(-1,0,1));

        back.setOnClickListener(v -> { if(web.canGoBack()) web.goBack(); });
        forward.setOnClickListener(v -> { if(web.canGoForward()) web.goForward(); });
        reload.setOnClickListener(v -> web.reload());
        home.setOnClickListener(v -> loadHome());
        bookmark.setOnClickListener(v -> saveBookmark());
        share.setOnClickListener(v -> sharePage());
        address.setOnEditorActionListener((v,id,e) -> {
            if (id == EditorInfo.IME_ACTION_GO || (e != null && e.getKeyCode()==KeyEvent.KEYCODE_ENTER)) {
                navigate(address.getText().toString());
                return true;
            }
            return false;
        });

        setContentView(root);
    }

    private Button button(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextColor(Color.WHITE);
        b.setTextSize(18);
        b.setMinWidth(48);
        b.setPadding(0,0,0,0);
        return b;
    }

    private void loadHome() {
        String home = "<!doctype html><html dir='rtl'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            + "<style>body{background:#050b14;color:#edf6ff;font-family:system-ui;text-align:center;padding:32px}"
            + ".orb{font-size:72px;margin:20px}.card{max-width:650px;margin:auto;background:#0c1726;border:1px solid #20334a;border-radius:22px;padding:24px}"
            + "input,button{font:inherit;padding:13px;border-radius:12px;border:1px solid #29435d;background:#14263b;color:white;margin:4px}"
            + "button{cursor:pointer}</style><div class='card'><div class='orb'>🧠</div>"
            + "<h1>BRAIN Browser</h1><p>متصفح BRAIN المدمج داخل Electronic Brain</p>"
            + "<input id='q' placeholder='ابحث أو اكتب عنوانًا' style='width:80%'><button onclick='go()'>فتح</button>"
            + "<p>الوصول السريع</p><button onclick="location.href='http://127.0.0.1:8787/'">BRAIN Cloud Hub</button>"
            + "<button onclick="location.href='https://github.com/omarenserat1980/MySimpleProject'">GitHub</button>"
            + "<script>function go(){let q=document.getElementById('q').value.trim();if(q)location.href='brain-search:'+encodeURIComponent(q)}</script>"
            + "</div></html>";
        web.loadDataWithBaseURL("https://brain.local/", home, "text/html", "UTF-8", null);
        address.setText("brain://home");
        title.setText("BRAIN Browser • الصفحة الرئيسية");
    }

    private void navigate(String raw) {
        String q = raw == null ? "" : raw.trim();
        if (q.isEmpty()) return;
        if (q.startsWith("brain-search:")) q = Uri.decode(q.substring(13));
        if (q.equalsIgnoreCase("brain://home") || q.equalsIgnoreCase("brain://")) { loadHome(); return; }
        String url;
        if (q.matches("(?i)^https?://.*")) url = q;
        else if (q.matches("(?i)^[a-z0-9.-]+\.[a-z]{2,}(/.*)?$")) url = "https://" + q;
        else {
            try { url = "https://www.google.com/search?q=" + URLEncoder.encode(q, "UTF-8"); }
            catch(Exception e) { url = "https://www.google.com/search?q=" + Uri.encode(q); }
        }
        web.loadUrl(url);
    }

    private void saveBookmark() {
        String u = web.getUrl();
        if (u == null || !(u.startsWith("http://") || u.startsWith("https://"))) return;
        Set<String> set = new HashSet<>(prefs.getStringSet("bookmarks", new HashSet<>()));
        set.add(u);
        prefs.edit().putStringSet("bookmarks", set).apply();
        Toast.makeText(this, "تم حفظ الصفحة في إشارات BRAIN", Toast.LENGTH_SHORT).show();
    }

    private void showBookmarks() {
        Set<String> set = prefs.getStringSet("bookmarks", new HashSet<>());
        if (set.isEmpty()) {
            Toast.makeText(this, "لا توجد إشارات محفوظة", Toast.LENGTH_SHORT).show();
            return;
        }
        String[] items = set.toArray(new String[0]);
        new android.app.AlertDialog.Builder(this)
            .setTitle("إشارات BRAIN")
            .setItems(items, (d, which) -> web.loadUrl(items[which]))
            .setNegativeButton("إغلاق", null)
            .show();
    }

    private void sharePage() {
        String u = web.getUrl();
        if (u == null) return;
        Intent i = new Intent(Intent.ACTION_SEND);
        i.setType("text/plain");
        i.putExtra(Intent.EXTRA_TEXT, u);
        startActivity(Intent.createChooser(i, "مشاركة من BRAIN Browser"));
    }

    @Override public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack(); else super.onBackPressed();
    }

    private class BrowserClient extends WebViewClient {
        @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
            Uri u = req.getUrl();
            String scheme = u.getScheme() == null ? "" : u.getScheme().toLowerCase();
            if ("brain-search".equals(scheme)) {
                navigate(u.toString());
                return true;
            }
            if ("http".equals(scheme) || "https".equals(scheme)) return false;
            try { startActivity(new Intent(Intent.ACTION_VIEW, u)); } catch(Exception ignored) {}
            return true;
        }

        @Override public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
            address.setText(url);
            title.setText("BRAIN Browser • جاري التحميل…");
        }

        @Override public void onPageFinished(WebView view, String url) {
            address.setText(url);
            String t = view.getTitle();
            title.setText("BRAIN Browser • " + (t == null || t.isEmpty() ? url : t));
        }
    }
}

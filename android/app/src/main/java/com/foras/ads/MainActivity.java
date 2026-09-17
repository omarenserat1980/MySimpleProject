package com.foras.ads;
import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Button;
public class MainActivity extends Activity {
    private static final String DEFAULT_URL="http://127.0.0.1:8080/";
    public void onCreate(Bundle b){super.onCreate(b); LinearLayout root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); EditText url=new EditText(this); url.setText(DEFAULT_URL); url.setHint("عنوان خادم Foras Ads"); Button open=new Button(this); open.setText("فتح البرنامج"); WebView web=new WebView(this); web.setWebViewClient(new WebViewClient()); WebSettings s=web.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true); s.setMediaPlaybackRequiresUserGesture(false); open.setOnClickListener(v->{String u=url.getText().toString().trim(); if(!u.startsWith("http://")&&!u.startsWith("https://"))u="http://"+u; web.loadUrl(u.endsWith("/")?u:u+"/");}); root.addView(url,new LinearLayout.LayoutParams(-1,-2)); root.addView(open,new LinearLayout.LayoutParams(-1,-2)); root.addView(web,new LinearLayout.LayoutParams(-1,0,1)); setContentView(root); }
}

package com.anyoarena.local;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.util.regex.Pattern;

public class MainActivity extends Activity {
    private static final int PICK_IMAGE = 27;
    private static final Pattern PRIVATE_IP = Pattern.compile(
        "^(127\\.0\\.0\\.1|10\\.(?:\\d{1,3}\\.){2}\\d{1,3}|192\\.168\\.\\d{1,3}\\.\\d{1,3}|172\\.(?:1[6-9]|2[0-9]|3[01])\\.\\d{1,3}\\.\\d{1,3}):8080$");
    private WebView web;
    private ValueCallback<Uri[]> imageCallback;
    private String origin;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        showConnect();
    }

    private void showConnect() {
        if (web != null) { web.destroy(); web = null; }
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(42, 40, 42, 20);
        layout.setGravity(Gravity.CENTER_VERTICAL);
        layout.setBackgroundColor(0xff111b2c);
        TextView title = new TextView(this);
        title.setText("ANYO ARENA"); title.setTextSize(30); title.setTextColor(0xffffcc6b);
        layout.addView(title);
        TextView help = new TextView(this);
        help.setText("Connect to the game host on the same Wi-Fi. Enter the host's local address (example: 192.168.1.5). The host must run server.py.");
        help.setTextColor(0xffd5deed); help.setTextSize(16);
        layout.addView(help);
        EditText address = new EditText(this);
        address.setSingleLine(); address.setHint("192.168.1.5"); address.setTextColor(0xffffffff);
        address.setHintTextColor(0xff8796aa);
        address.setText(getPreferences(MODE_PRIVATE).getString("host", ""));
        layout.addView(address);
        android.widget.Button connect = new android.widget.Button(this);
        connect.setText("CONNECT TO GAME"); layout.addView(connect);
        TextView error = new TextView(this); error.setTextColor(0xffff8c85); layout.addView(error);
        connect.setOnClickListener(v -> {
            String host = address.getText().toString().trim().replaceFirst("^https?://", "").replaceFirst("/.*$", "");
            if (!host.contains(":")) host += ":8080";
            if (!PRIVATE_IP.matcher(host).matches()) {
                error.setText("Enter a private Wi-Fi IP address from the host, such as 192.168.1.5"); return;
            }
            getPreferences(MODE_PRIVATE).edit().putString("host", host.replace(":8080", "")).apply();
            origin = "http://" + host;
            openGame();
        });
        setContentView(layout);
    }

    private void openGame() {
        web = new WebView(this);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(true);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return !url.startsWith(origin + "/") && !url.equals(origin);
            }
            @Override public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                if (failingUrl.startsWith(origin)) new AlertDialog.Builder(MainActivity.this)
                    .setMessage("Cannot reach the host. Check the Wi-Fi and host address.\n\n" + description)
                    .setPositiveButton("CHANGE ADDRESS", (dialog, which) -> showConnect()).show();
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (imageCallback != null) imageCallback.onReceiveValue(null);
                imageCallback = callback;
                Intent pick = new Intent(Intent.ACTION_GET_CONTENT);
                pick.setType("image/*"); pick.addCategory(Intent.CATEGORY_OPENABLE);
                startActivityForResult(Intent.createChooser(pick, "Choose fighter photo"), PICK_IMAGE);
                return true;
            }
        });
        setContentView(web);
        web.loadUrl(origin + "/");
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request == PICK_IMAGE && imageCallback != null) {
            Uri uri = result == RESULT_OK && data != null ? data.getData() : null;
            imageCallback.onReceiveValue(uri == null ? null : new Uri[]{uri});
            imageCallback = null;
        }
    }

    @Override public void onBackPressed() {
        if (web != null) new AlertDialog.Builder(this).setMessage("Disconnect from the game?")
            .setNegativeButton("CANCEL", null)
            .setPositiveButton("DISCONNECT", (d, w) -> showConnect()).show();
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        if (imageCallback != null) imageCallback.onReceiveValue(null);
        if (web != null) web.destroy();
        super.onDestroy();
    }
}

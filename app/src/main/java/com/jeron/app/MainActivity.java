package com.jeron.app;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentResolver;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.ServiceWorkerClient;
import android.webkit.ServiceWorkerController;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.webkit.WebViewAssetLoader;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;

public class MainActivity extends Activity {
    private static final String HOME = "https://appassets.androidplatform.net/assets/index.html";
    private static final int REQ_FILE = 7;
    private static final int REQ_IMG = 8;
    private WebView web;
    private ValueCallback<Uri[]> fileCb;
    private static int crashes = 0;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        setContentView(web);

        final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW); // للوصول لسيرفر Qwen-Image على الشبكة المحلية (http)
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

        ServiceWorkerController.getInstance().setServiceWorkerClient(new ServiceWorkerClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebResourceRequest r) {
                return loader.shouldInterceptRequest(r.getUrl());
            }
        });
        web.addJavascriptInterface(new Bridge(), "AndroidBridge");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                return loader.shouldInterceptRequest(r.getUrl());
            }

            @Override
            public boolean onRenderProcessGone(WebView v, RenderProcessGoneDetail d) {
                // الذاكرة خلصت: بدل ما يطلع التطبيق، نعيد تشغيل الواجهة (النموذج المحمّل ينحفظ بالكاش)
                if (++crashes > 3) { finish(); return true; }
                runOnUiThread(() -> recreate());
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb, FileChooserParams p) {
                if (fileCb != null) fileCb.onReceiveValue(null);
                fileCb = cb;
                try {
                    startActivityForResult(p.createIntent(), REQ_FILE);
                } catch (Exception e) {
                    fileCb = null;
                    return false;
                }
                return true;
            }
        });
        web.loadUrl(HOME);
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        if (req == REQ_IMG) {
            if (res != RESULT_OK || data == null) return;
            final ArrayList<Uri> uris = new ArrayList<>();
            if (data.getClipData() != null) {
                for (int i = 0; i < data.getClipData().getItemCount(); i++) uris.add(data.getClipData().getItemAt(i).getUri());
            } else if (data.getData() != null) uris.add(data.getData());
            new Thread(() -> {
                for (Uri u : uris) {
                    final String d = toDataUrl(u);
                    if (d == null) continue;
                    runOnUiThread(() -> web.evaluateJavascript("window.onPickedImage&&window.onPickedImage('" + d + "')", null));
                }
            }).start();
            return;
        }
        if (req == REQ_FILE && fileCb != null) {
            fileCb.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(res, data));
            fileCb = null;
            return;
        }
        super.onActivityResult(req, res, data);
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        web.evaluateJavascript("(window.jeronBack&&window.jeronBack())===true", v -> {
            if (!"true".equals(v)) finish();
        });
    }

    private String toDataUrl(Uri u) {
        try {
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inJustDecodeBounds = true;
            try (InputStream in = getContentResolver().openInputStream(u)) { BitmapFactory.decodeStream(in, null, o); }
            int mx = Math.max(o.outWidth, o.outHeight), ss = 1;
            while (mx / ss > 3200) ss *= 2;
            o = new BitmapFactory.Options();
            o.inSampleSize = ss;
            Bitmap b;
            try (InputStream in = getContentResolver().openInputStream(u)) { b = BitmapFactory.decodeStream(in, null, o); }
            if (b == null) return null;
            int rot = 0;
            try (InputStream in = getContentResolver().openInputStream(u)) {
                int ori = new ExifInterface(in).getAttributeInt(ExifInterface.TAG_ORIENTATION, 1);
                if (ori == 6) rot = 90; else if (ori == 3) rot = 180; else if (ori == 8) rot = 270;
            } catch (Exception ignored) {}
            int m = Math.max(b.getWidth(), b.getHeight());
            float k = m > 1568 ? 1568f / m : 1f;
            if (k != 1f || rot != 0) {
                Matrix mt = new Matrix();
                mt.postScale(k, k);
                mt.postRotate(rot);
                Bitmap n = Bitmap.createBitmap(b, 0, 0, b.getWidth(), b.getHeight(), mt, true);
                if (n != b) b.recycle();
                b = n;
            }
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            b.compress(Bitmap.CompressFormat.JPEG, 88, bo);
            b.recycle();
            return "data:image/jpeg;base64," + Base64.encodeToString(bo.toByteArray(), Base64.NO_WRAP);
        } catch (Throwable e) {
            return null;
        }
    }

    class Bridge {
        @JavascriptInterface
        public void pickImage() {
            runOnUiThread(() -> {
                Intent i = new Intent(Intent.ACTION_GET_CONTENT);
                i.setType("image/*");
                i.addCategory(Intent.CATEGORY_OPENABLE);
                i.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                try { startActivityForResult(Intent.createChooser(i, "اختر صورة"), REQ_IMG); } catch (Exception ignored) {}
            });
        }

        @JavascriptInterface
        public void keepAwake(final boolean on) {
            runOnUiThread(() -> {
                if (on) getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                else getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            });
        }

        @JavascriptInterface
        public void copy(String t) {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            if (cm != null) cm.setPrimaryClip(ClipData.newPlainText("jeron", t));
        }

        @JavascriptInterface
        public boolean save(String name, String mime, String b64) {
            try {
                byte[] data = Base64.decode(b64, Base64.DEFAULT);
                boolean img = mime != null && mime.startsWith("image/");
                ContentResolver cr = getContentResolver();
                ContentValues v = new ContentValues();
                v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                v.put(MediaStore.MediaColumns.MIME_TYPE, (mime == null || mime.isEmpty()) ? "application/octet-stream" : mime);
                v.put(MediaStore.MediaColumns.RELATIVE_PATH, img ? Environment.DIRECTORY_PICTURES + "/Jeron" : Environment.DIRECTORY_DOWNLOADS);
                Uri base = img ? MediaStore.Images.Media.EXTERNAL_CONTENT_URI : MediaStore.Downloads.EXTERNAL_CONTENT_URI;
                Uri u = cr.insert(base, v);
                if (u == null) return false;
                try (OutputStream o = cr.openOutputStream(u)) {
                    if (o == null) return false;
                    o.write(data);
                }
                return true;
            } catch (Exception e) {
                return false;
            }
        }
    }
}

# جيرون — مشروع الـ APK

المجلد هذا مشروع أندرويد جاهز (WebView) بداخله تطبيقك `index.html` + `sw.js`. ما تحتاج Netlify.

## الطريقة 1: بدون Android Studio (GitHub)
1. سوّي مستودع جديد على GitHub وارفع **محتويات** هذا المجلد كلها (مو المجلد نفسه).
2. افتح تبويب **Actions** ← **Build APK** ← **Run workflow** (يشتغل تلقائي أول ما ترفع).
3. بعد ~5 دقايق نزّل **jeron-apk** من أسفل صفحة التشغيل، فك الضغط، وثبّت `app-debug.apk`.

## الطريقة 2: Android Studio
افتح المجلد بـ Android Studio ← انتظر Gradle Sync ← Build ← Build APK(s).

## تشغيل التطبيق
- **الدردشة (Qwen3):** من الإعدادات اختر الحجم واضغط «تحميل النموذج الآن» (يحتاج نت مرة وحدة)، وبعدها يشتغل بدون نت. يحتاج WebGPU: Android 12+ وWebView حديث (حدّث Android System WebView وChrome).
- **الصور (Qwen-Image):** شغّل `qwen_image_server.py` على الكمبيوتر بالأمر:
  `HOST=0.0.0.0 python qwen_image_server.py`
  وبالتطبيق ضع رابط السيرفر بالإعدادات: `http://IP-الكمبيوتر:8000` (الجوال والكمبيوتر على نفس الواي فاي).

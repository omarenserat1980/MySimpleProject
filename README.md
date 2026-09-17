# Foras Ads

تطبيق لإنشاء إعلانات فيديو عمودية للمنتجات من الهاتف، مع تجهيز النشر إلى Facebook وYouTube.

## Android APK

تمت إضافة مشروع Android داخل `android/` مع واجهة تطبيق تفتح خادم Foras Ads المحلي. ملف GitHub Actions في `.github/workflows/android-apk.yml` يبني نسخة Debug APK ويرفعها كـ Artifact باسم `ForasAds-debug-apk`.

### مهم

نسخة APK الحالية هي واجهة Android للخادم. محرك إنشاء الفيديو Python/MoviePy يعمل على الجهاز الذي يشغّل الخادم؛ لذلك لكي يعمل الإنشاء محلياً على الهاتف، شغّل `run_mobile.py` في بيئة Python/Termux على الهاتف، ثم افتح التطبيق.

## تشغيل محرك الفيديو

```bash
pip install -r requirements-publishing.txt
python run_mobile.py
```

الصورة ترفع من الهاتف، والفيديو الناتج يكون عمودياً 1080×1920 ومناسباً للفيديوهات القصيرة.

لا تضع OAuth tokens أو مفاتيح API داخل GitHub. إعداد Facebook وYouTube يتم لاحقاً عبر متغيرات البيئة/تسجيل الدخول الرسمي.

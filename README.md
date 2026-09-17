# Foras Ads

إنشاء إعلانات فيديو عمودية للمنتجات من الهاتف، مع تجهيز النشر إلى Facebook وYouTube.

## Android APK

مشروع Android موجود داخل `android/`. التطبيق يفتح واجهة Foras Ads ويتصل بخادم الفيديو المحلي `http://127.0.0.1:8080/` أو بعنوان خادم تكتبه داخل التطبيق.

GitHub Actions موجود في `.github/workflows/android-apk.yml` لبناء Debug APK ورفعه كـ Artifact باسم `ForasAds-debug-apk`.

## تشغيل المحرك على الهاتف

ثبّت Python/Termux ثم:

```bash
pip install -r requirements-publishing.txt
python run_mobile.py
```

بعد ذلك افتح تطبيق Foras Ads واترك عنوان الخادم الافتراضي.

الفيديو الناتج عمودي 1080×1920. ربط Facebook وYouTube يحتاج OAuth/Graph API رسمي، ولا تحفظ المفاتيح أو Tokens داخل GitHub.

**ملاحظة:** الـAPK الحالي هو واجهة Android للمحرك، وليس محرك Python مضمناً داخل APK. هذه البنية تسمح ببناء APK الآن، بينما نكمل لاحقاً دمج محرك الفيديو داخل التطبيق أو تشغيله على خادم.

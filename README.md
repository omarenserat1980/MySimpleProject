# Foras Ads

تطبيق لإنشاء إعلانات فيديو عمودية للمنتجات من الهاتف، مع تجهيز النشر إلى Facebook وYouTube.

## Android APK

يوجد مشروع Android داخل `android/`. التطبيق يفتح واجهة Foras Ads ويمكنه الاتصال بخادم Foras Ads المحلي أو بعنوان خادم آخر تكتبه داخل التطبيق.

ملف GitHub Actions في `.github/workflows/android-apk.yml` يبني نسخة Debug APK ويرفعها كـ Artifact باسم `ForasAds-debug-apk`.

## مهم قبل الاستخدام

هذا الـAPK هو واجهة Android للمشروع، أما محرك إنشاء الفيديو Python/MoviePy فهو خادم منفصل. لذلك لا أعتبر التطبيق "مولد فيديو مستقل بالكامل" بعد. لتوليد الفيديو محلياً على الهاتف، شغّل `run_mobile.py` في Python/Termux على الهاتف ثم افتح التطبيق واترك العنوان `http://127.0.0.1:8080/`.

```bash
pip install -r requirements-publishing.txt
python run_mobile.py
```

الفيديو الناتج عمودي 1080×1920. نشر Facebook وYouTube يحتاج إعداد OAuth/Graph API رسمي ولا يتم تخزين الأسرار داخل GitHub.

# Brain Chat v1

واجهة محادثة شبيهة بتجربة ChatGPT فوق Electronic Brain.

## المسار
`/brain-chat.html`

## تستخدم واجهات Brain الموجودة
- `POST /api/chat` للمحادثة
- `GET /api/ai/status` لحالة مزود الذكاء
- `POST /api/image-factory/generate` لتوليد الصور
- ذاكرة المحادثات المحلية في المتصفح، مع بقاء محرك Brain وذاكرته على الخادم.

## ملاحظات الأمان
لا يحتوي هذا الملف على أي API key. المفاتيح تبقى في بيئة الخادم.

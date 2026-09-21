# Electronic Brain Agent

يشغّل هذا الوكيل على الجهاز الذي تريد أن ينفذ عليه العقل.

## التشغيل
ضع AGENT_TOKEN في البيئة ثم:
python agent.py

افتراضيًا التنفيذ محصور داخل agent_sandbox، والأوامر مسموحة فقط من قائمة AGENT_COMMANDS.

## الاتصال
POST /execute
POST /write
GET /read
GET /status

لا تضع مفتاحًا سريًا داخل GitHub. استخدم متغيرات البيئة أو Secret Manager.

## توسيع الصلاحيات
يمكن توسيع قائمة الأوامر على الجهاز نفسه عبر AGENT_COMMANDS بعد مراجعة المخاطر. لا تجعلها مفتوحة تلقائيًا لأوامر النظام.

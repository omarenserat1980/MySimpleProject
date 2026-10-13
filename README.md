# Electronic Brain V12

هذا المستودع مخصص لـ **العقل الإلكتروني V12**.

## البنية
- `brain_v12/` — النواة والخدمات والواجهة.
- `brain_v12/web/index.html` — واجهة V12 العربية RTL.
- `brain_v12/start_brain.sh` — تشغيل خدمة MCP محليًا.
- `.github/workflows/brain-v12-pages.yml` — نشر واجهة V12 على GitHub Pages.

## المسار التشغيلي القانوني

النواة الحالية هي `brain_v12`. نقطة تشغيل API الأساسية هي:

```bash
python3 -m brain_v12.app
```

مسارات Brain 6 القديمة لا تُعد مسارات تشغيل بديلة. مشغّل `scripts/brain6_168h.sh` معطّل عمدًا، وحالة حملة `production/BRAIN6_168H.json` متوقفة، ومثبت الخدمة القديم يزيل خدمة المستخدم القديمة بدلًا من تشغيلها. تفاصيل الترحيل: [BRAIN Runtime Cutover](docs/BRAIN_RUNTIME_CUTOVER.md).

## الحلقة المعرفية
Perceive → Understand → Memory → Goal → Plan → Decide → Act → Observe → Learn

## Brain Cloud runtime

المسار التشغيلي المعتمد هو **Brain Cloud / software-only**. لا يعتمد التشغيل الافتراضي على هاتف أو حاسوب شخصي أو Termux أو Hyper-V أو Runner ذاتي الاستضافة.

- موارد المحاكاة البرمجية هي المسار الأول؛ أي موارد فعلية أو خارجية لا تُعامل كشرط أساسي.
- تسجيل عامل مبرمجي لا يثبت تنفيذ المهمة؛ النجاح يتطلب نتيجة فعلية وبوابات تحقق وأدلة.
- DeviceBridge قد يبقى للتوافق البرمجي/القراءة، لكن تسجيل أجهزة Android وTermux والأجهزة الفيزيائية في WorkerRegistry مرفوض.
- لا يُعتبر الفيلم ناجحًا إلا بعد إنشاء MP4 واجتياز FFprobe/QC مستقل للصوت والصورة.
- FFmpeg وFFprobe يمران عبر عقد Brain-native toolchain (`BRAIN_FFMPEG_BIN` و`BRAIN_FFPROBE_BIN`).

## Mining Economics
طبقة Mining Economics للتحليل الحسابي فقط، دون تشغيل تعدين أو شراء أجهزة أو ربط محافظ. النتائج ليست بيانات سوق حية ولا دخلًا محققًا؛ الإيراد الفعلي يتطلب دليل دفع قابلًا للمطابقة.

## GitHub Cloud verification
المسار: **Supervisor → Reusable Brain Cloud → Tests → VerificationGate → Evidence**.
نجاح التنفيذ لا يساوي إكمال الهدف؛ لا يُعلن الإكمال دون دليل غير فارغ وشرط تحقق صريح.

## Software-only execution nodes

Brain يعمل بوضع **software-only**. معاملات التوافق القديمة لا تعيد تفعيل الأجهزة؛ تسجيل worker من نوع device/physical/termux/android/hardware يُرفض صراحة.

- السياسة والقيود: [Software-only nodes](brain_v12/docs/SOFTWARE_ONLY_NODES.md)
- فحوص CI: [Brain Software-Only Node Verification](.github/workflows/brain-software-only-nodes.yml)
- هذا يزيل اعتماد الأجهزة من سجل التنفيذ، لكنه لا يعني أن موارد المحاكاة غير محدودة أو أن كل تكامل خارجي قد اجتاز التحقق.

# Brain Termux Auto Deploy

هذا المشغّل يجعل هاتف Android + Termux نقطة تشغيل واحدة لنشر Brain Cloud على Ubuntu VPS عبر SSH.

## الاستخدام

داخل Termux:

```bash
pkg update -y
pkg install openssh curl -y
chmod +x cloud/vps/brain-termux-autodeploy.sh
./cloud/vps/brain-termux-autodeploy.sh
```

يمكن أيضًا ضبط المتغيرات:

```bash
export BRAIN_VPS_HOST="YOUR_SERVER_IP"
export BRAIN_VPS_USER="root"
export BRAIN_SSH_KEY="$HOME/.ssh/id_ed25519"
./cloud/vps/brain-termux-autodeploy.sh
```

المشغّل:
1. يفحص SSH.
2. يثبت Docker وCompose وGit وOpenSSL على Ubuntu.
3. يجلب `main` من المستودع.
4. ينشئ `BRAIN_CONTROL_TOKEN` تلقائيًا إذا كان مفقودًا، ولا يطبعه.
5. يسحب صورة GHCR أو يبنيها محليًا إذا تعذر السحب.
6. يشغّل Brain Cloud.
7. يفحص `/healthz` و`/readyz`.
8. يعيد المحاولة تلقائيًا عند فشل النشر.

لا يضع أي مفتاح API في الهاتف أو داخل المستودع. مفاتيح OpenAI/FAL/YouTube تبقى إعدادات خادم اختيارية في `cloud/.env`.

> ملاحظة: Termux يستطيع تنفيذ العملية بالكامل بعد توفر وصول SSH إلى VPS. لا يستطيع وحده إنشاء حساب سحابي مدفوع أو حجز VPS دون حساب/تفويض لدى مزود الخدمة.

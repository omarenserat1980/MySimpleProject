# Brain AI Platform Roadmap

## الهدف
تحويل Electronic Brain تدريجياً إلى منصة ذكاء اصطناعي مستقلة شبيهة بتجربة ChatGPT، مع بقاء ChatGPT/OpenAI والنماذج الأخرى مزودات اختيارية وليست مصدر الحقيقة الوحيد.

## الأولوية الحالية
**ChatGPT-like Brain Platform** هي المرحلة الأولى ذات الأولوية. لا ننتقل إلى Security/Backup/Wallet كمرحلة تنفيذ رئيسية إلا بعد إغلاق أساس المنصة الحوارية وتشغيله بأدلة فعلية.

## الطبقات
1. Brain UI — محادثات، جلسات، ملفات، أدوات، حالة التنفيذ.
2. AI Gateway — توحيد مزودي النماذج.
3. Orchestrator — تخطيط، أدوات، Agents، إعادة المحاولة.
4. Memory — ذاكرة وجلسات وتفضيلات ومتطلبات ومخرجات.
5. Tool Plane — Web, Files, Code, GitHub, Media, Automation.
6. Verification — Evidence، تدقيق، صلاحيات، Fail-Closed.
7. Runtime — Cloud/Browser execution بدون اعتماد على Render.
8. Model Layer — ChatGPT/OpenAI وغيرها كموارد قابلة للتبديل.

## مراحل التنفيذ ذات الأولوية
- [x] Brain AI tool loop
- [x] GitHub capability surface
- [x] ChatGPT capability registry
- [x] ChatGPT bridge + host gateway contract
- [x] CI evidence for host gateway
- [x] Browser-first Chat UI implementation
- [x] Persistent conversation/session implementation
- [ ] CI verification for persistent Chat UI/API
- [ ] Conversation context and memory per session
- [ ] Unified file workspace
- [ ] Attachments and multimodal message pipeline
- [ ] Agent/workspace management
- [ ] Unified model routing and provider fallback
- [ ] Streaming responses
- [ ] Tool approval UX and live execution evidence
- [ ] Production host-tool registration
- [ ] Independent Brain model/runtime options
- [ ] Cloud/browser deployment without device installation

## Definition of Done للمنصة الحوارية
لا تعتبر المنصة ChatGPT-like مكتملة حتى تثبت:
1. إنشاء جلسة وحفظها.
2. استمرار الرسائل بعد إعادة تشغيل التطبيق.
3. سياق محادثة صحيح لكل جلسة.
4. تشغيل الأدوات مع Evidence حقيقي.
5. ملفات ومرفقات ضمن مساحة العمل.
6. تعامل واضح مع الصلاحيات والموافقات.
7. نموذج/مزود قابل للتبديل.
8. واجهة Browser-first قابلة للاستخدام.
9. اختبارات API/UI/backend ناجحة.
10. تشغيل فعلي موثق من CI أو بيئة تشغيل حقيقية.

## المرحلة التالية بعد المنصة
بعد إغلاق Definition of Done للمنصة الحوارية، نفعّل تدريجياً:
**Security Foundation → Backup/Recovery → Wallet Security → Continuous Security Intelligence → Security Supervisor**

## معيار الانتقال
لا نعلن اكتمال أي مرحلة إلا بعد اختبار فعلي ودليل قابل للتحقق. الأدوات المضيفة لا تُعتبر منفذة إلا إذا عاد رد حقيقي من Host Gateway.

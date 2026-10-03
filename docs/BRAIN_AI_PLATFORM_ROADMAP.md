# Brain AI Platform Roadmap

## هدف
تحويل Electronic Brain تدريجياً إلى منصة ذكاء اصطناعي مستقلة شبيهة بتجربة ChatGPT، مع بقاء ChatGPT/النماذج الخارجية مزودات اختيارية وليست مصدر الحقيقة الوحيد.

## الطبقات
1. Brain UI — محادثات، جلسات، ملفات، أدوات، حالة التنفيذ.
2. AI Gateway — توحيد مزودي النماذج.
3. Orchestrator — تخطيط، أدوات، Agents، إعادة المحاولة.
4. Memory — ذاكرة وجلسات وتفضيلات ومتطلبات ومخرجات.
5. Tool Plane — Web, Files, Code, GitHub, Media, Automation.
6. Verification — Evidence، تدقيق، صلاحيات، Fail-Closed.
7. Runtime — Cloud/Browser execution بدون اعتماد على Render.
8. Model Layer — ChatGPT/OpenAI وغيرها كموارد قابلة للتبديل.

## مراحل التنفيذ
- [x] Brain AI tool loop
- [x] GitHub capability surface
- [x] ChatGPT capability registry
- [x] ChatGPT bridge + host gateway contract
- [x] CI evidence for host gateway
- [ ] Browser-first Chat UI
- [ ] Persistent conversation/session API
- [ ] Unified file workspace
- [ ] Agent/workspace management
- [ ] Unified model routing
- [ ] Production host-tool registration
- [ ] Independent Brain model/runtime options

## معيار الانتقال
لا نعلن اكتمال أي مرحلة إلا بعد اختبار فعلي ودليل قابل للتحقق. الأدوات المضيفة لا تُعتبر منفذة إلا إذا عاد رد حقيقي من Host Gateway.

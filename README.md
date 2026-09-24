# Electronic Brain V12

هذا المستودع أصبح مخصصًا لـ **العقل الإلكتروني V12**.

## البنية
- `brain_v12/` — النواة والخدمات والواجهة.
- `brain_v12/web/index.html` — واجهة V12 العربية RTL.
- `brain_v12/start_brain.sh` — تشغيل الخدمة محليًا.
- `.github/workflows/brain-v12-pages.yml` — نشر واجهة V12 على GitHub Pages.

## الحلقة المعرفية
Perceive → Understand → Memory → Goal → Plan → Decide → Act → Observe → Learn

تمت إزالة ملفات مشروع المضخة من جذر المشروع حتى لا تبقى واجهة أو تشغيلات خاصة بالمضخات ضمن المشروع الحالي.

## Brain V12 ↔ Termux Agent Gateway

The gateway uses HTTPS polling with an allowlist and shared secret. The initial smoke test is `python_version`.

### Termux
```bash
cd ~/MySimpleProject
export BRAIN_URL="https://electronic-brain-v12-gwwg.onrender.com"
export TERMUX_AGENT_KEY='YOUR_SECRET'
export TERMUX_AGENT_ID="android-termux-v12"
bash termux_agent/run_agent.sh
```

Keep `TERMUX_AGENT_KEY` out of source control and chat messages.

### Smoke test
After the agent is running, the Brain control endpoint can enqueue `python_version`. The Agent claims it, executes `python --version`, reports the result, and Brain verifies the stored result.

Allowed initial tasks: `status`, `python_version`, `termux_path`, `platform`.

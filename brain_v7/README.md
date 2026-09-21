# Electronic Brain V7

Backend مستقل لواجهة العقل الإلكتروني.

## التشغيل
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# ضع مفتاح مزود نموذج اللغة في LLM_API_KEY
python main.py

ثم افتح:
http://127.0.0.1:8000/docs

## API
GET /health
POST /api/chat
GET/POST /api/memory
GET/POST /api/goals
POST /api/cycle
GET /api/state
GET /api/events
GET /api/llm/status

هذا المشروع لا ينفذ أوامر نظام التشغيل ولا يصل إلى أسرار الجهاز تلقائياً. التشغيل الذاتي معطل افتراضياً.

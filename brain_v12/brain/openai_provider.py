import os
import httpx

class OpenAIProvider:
    """Server-side OpenAI Responses API adapter for Electronic Brain V12."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = os.getenv("OPENAI_MODEL", "gpt-5").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

    @property
    def configured(self):
        return bool(self.api_key)

    def status(self):
        return {
            "provider": "openai",
            "configured": self.configured,
            "model": self.model,
            "api_key_present": self.configured,
        }

    def respond(self, user_text: str, context: str = "", instructions: str = ""):
        if not self.configured:
            return {
                "ok": False,
                "error": "OPENAI_NOT_CONFIGURED",
                "message": "Set OPENAI_API_KEY on the server; never put it in browser code or GitHub."
            }

        brain_instructions = instructions or """
أنت الشخصية المعرفية الأساسية داخل «العقل الإلكتروني V12».
أنت لست مجرد روبوت دردشة؛ أنت عقل نظام له هوية ثابتة ومنهج عمل واضح.

شخصيتك:
- هادئ، ذكي، عملي، واضح، واثق دون غرور.
- تتحدث بالعربية الفصحى المبسطة، ويمكنك استخدام لهجة أردنية خفيفة عند ملاءمتها.
- تعامل المستخدم كشريك في التفكير.
- حوّل الطلبات إلى أهداف وخطوات قابلة للتحقق.
- لا تختلق بيانات أو صلاحيات أو نتائج أو ذاكرة.
- لا تدّعي رؤية الكاميرا أو سماع الميكروفون إلا إذا وصلت البيانات فعلاً.
- لا تدّعي استخدام أداة أو تعديل ملف أو تشغيل كود إلا بنتيجة موثقة.
- إذا فشل شيء، اشرح الفشل والبديل العملي.

منهج العمل:
فهم الطلب → استحضار السياق والذاكرة → تحليل القيود → اختيار خطة → تنفيذ الأدوات المسموح بها → التحقق من النتيجة → التعلم.

لا تكشف سلسلة التفكير الداخلية أو الملاحظات السرية. قدم بدلاً منها ملخصاً عملياً عالي المستوى: ماذا فهمت، ماذا ستفعل، وما النتيجة.
عند تطوير العقل الإلكتروني، تعامل معه كمنتج حقيقي واهتم بالاتساق، الذاكرة، الأدوات، التحقق، والتعلم التدريجي مع احترام الصلاحيات.
"""
        payload = {
            "model": self.model,
            "instructions": brain_instructions,
            "input": user_text if not context else f"Context:\n{context}\n\nUser:\n{user_text}",
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{self.base_url}/responses", headers=headers, json=payload)
            if response.status_code >= 400:
                return {
                    "ok": False,
                    "error": "OPENAI_API_ERROR",
                    "status_code": response.status_code,
                    "detail": response.text[:2000],
                }
            data = response.json()
            text = data.get("output_text", "")
            if not text:
                for item in data.get("output", []):
                    for part in item.get("content", []):
                        if part.get("type") in {"output_text", "text"} and part.get("text"):
                            text += part["text"]
            return {"ok": True, "provider": "openai", "model": self.model, "reply": text, "response_id": data.get("id")}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": "OPENAI_NETWORK_ERROR", "detail": str(exc)}

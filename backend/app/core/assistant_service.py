from __future__ import annotations

from typing import Any


class AssistantService:
    """Offline, read-only assistant for diagnostics and report explanations."""

    def diagnose(self, error: Exception | str) -> dict[str, Any]:
        message = str(error).strip() or "خطأ غير معروف"
        lowered = message.casefold()
        if "permission" in lowered or "صلاح" in message:
            advice = "تحقق من الدور والنطاق وفصل المهام قبل إعادة المحاولة."
        elif "duplicate" in lowered or "مكرر" in message:
            advice = "تحقق من مفتاح idempotency ورقم المستند قبل إعادة الإرسال."
        elif "stock" in lowered or "مخزون" in message:
            advice = "راجع الرصيد والحركات المفتوحة للمخزن والصنف."
        else:
            advice = "راجع تفاصيل العملية وسجل التدقيق، ثم أعد المحاولة بعد معالجة السبب."
        return {"title": "تشخيص العملية", "error": message, "advice": advice, "read_only": True}

    def explain_summary(self, summary: Any) -> dict[str, Any]:
        return {
            "title": "شرح الملخص",
            "text": (
                f"إجمالي المبيعات {summary.sales_total:,.2f}، "
                f"إجمالي المشتريات {summary.purchases_total:,.2f}، "
                f"وصافي الربح الإجمالي {summary.gross_profit:,.2f}."
            ),
            "read_only": True,
        }

    def execute_change(self, *_args, **_kwargs):
        raise PermissionError("المساعد الذكي للنسخة المحلية للقراءة والتشخيص فقط.")

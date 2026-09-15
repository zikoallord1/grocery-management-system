from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle

from backend.app.core.database import initialize_database
from frontend.app.branding import BRANDING
from frontend.app.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build_docs"
SCREEN_DIR = OUT / "screens"
DOCS_DIR = ROOT / "docs" / "client"


def _register_font() -> str:
    candidates = [
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            pdfmetrics.registerFont(TTFont("ArabicDoc", str(path)))
            return "ArabicDoc"
    return "Helvetica"


def capture_screenshots() -> list[tuple[str, Path]]:
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    initialize_database()
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.resize(1180, 760)
    window.show()
    app.processEvents()
    targets = [("01-الرئيسية", window.dashboard)]
    for name, page in window._pages.items():
        targets.append((f"02-{name}", page))
    result = []
    for filename, widget in targets:
        window.stack.setCurrentWidget(widget)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception:
                pass
        app.processEvents()
        path = SCREEN_DIR / f"{filename}.png"
        window.grab().save(str(path))
        result.append((filename, path))
    window.close()
    app.quit()
    return result


def build_pdf(path: Path, title: str, screenshots: list[tuple[str, Path]], detailed: bool) -> None:
    font = _register_font()
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName=font, fontSize=10.5, leading=16, alignment=TA_RIGHT, spaceAfter=7)
    heading = ParagraphStyle("heading", parent=styles["Heading2"], fontName=font, fontSize=16, leading=21, alignment=TA_RIGHT, spaceBefore=8, spaceAfter=10)
    center = ParagraphStyle("center", parent=body, alignment=TA_CENTER)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = [Paragraph(title, ParagraphStyle("title", parent=heading, fontSize=22, alignment=TA_CENTER)), Spacer(1, 5*mm)]
    story.append(Paragraph(f"{BRANDING.program_name} — إصدار توثيقي بتاريخ {date.today().isoformat()}", center))
    story.append(Spacer(1, 7*mm))
    if detailed:
        story += [
            Paragraph("طريقة الاستخدام الأساسية", heading),
            Paragraph("يُدخل المستخدم العملية مرة واحدة، ثم يربط النظام أثرها التشغيلي والمالي والمخزني والتقارير ذات الصلة حسب الوظيفة المتاحة.", body),
            Paragraph("المبيعات والمشتريات", heading),
            Paragraph("أنشئ الفاتورة، اختر العميل أو المورد عند الحاجة، اختر الصنف والوحدة والكمية والسعر، ثم احفظ العملية. الكميات المخزنية تعتمد على الوحدة الأساسية ومعامل التحويل الخاص بالصنف.", body),
            Paragraph("الوحدات والعبوات", heading),
            Paragraph("يمكن تعريف أكثر من وحدة للصنف نفسه: مثال 1 كرتون = 20 حبة لصنف، بينما يمكن أن يكون كرتون صنف آخر = 24 حبة. تحفظ العملية الوحدة ومعامل التحويل المستخدم وقت الإدخال.", body),
            Paragraph("الباركود", heading),
            Paragraph("يمكن استخدام قارئ الباركود بالكاميرا في شاشة المبيعات لإضافة الصنف بسرعة، مع دعم تكرار المسح.", body),
            Paragraph("المالية والذمم", heading),
            Paragraph("الدفع النقدي والمحفظة والتحويل البنكي مرتبطة بالحساب النقدي المناسب، بينما الائتمان يظهر كذمة على العميل أو المورد حسب العملية.", body),
            Paragraph("المرتجعات", heading),
            Paragraph("المرتجع يعكس أثر المخزون والحركة المالية مع المحافظة على مرجع الفاتورة الأصلية، ولا يعتمد على حذف العملية المالية.", body),
            Paragraph("الإغلاق والنسخ الاحتياطي", heading),
            Paragraph("يوفر النظام صيانة يومية تلقائية تتضمن إغلاق اليوم ونسخة احتياطية عند نجاح الإجراء، مع تسجيل حالة العملية.", body),
            Paragraph("التراخيص", heading),
            Paragraph("يستخدم النظام ترخيصًا موقّعًا رقميًا ومربوطًا بمعرّف التثبيت. برنامج مدير التراخيص يحتفظ بمفتاح الإصدار الخاص، بينما النسخة العميلة تستخدم مفتاح التحقق العام فقط.", body),
            PageBreak(),
        ]
    story.append(Paragraph("الواجهات المصورة", heading))
    for name, image_path in screenshots:
        story.append(Paragraph(name, heading))
        if image_path.exists():
            story.append(Image(str(image_path), width=175*mm, height=113*mm, kind="proportional"))
        story.append(Spacer(1, 5*mm))
        story.append(Paragraph("هذه لقطة حقيقية مولدة من واجهة البرنامج الحالية أثناء بناء التوثيق.", center))
        story.append(PageBreak())
    story.append(Paragraph(BRANDING.designer_credit, center))
    story.append(Paragraph(BRANDING.contact_text, center))
    doc.build(story)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    screenshots = capture_screenshots()
    build_pdf(OUT / "دليل استخدام البرنامج.pdf", "دليل استخدام نظام إدارة البقالات", screenshots, True)
    build_pdf(OUT / "تقرير البرنامج.pdf", "التقرير المصور لنظام إدارة البقالات", screenshots, False)
    (OUT / "معلومات الإصدار.txt").write_text(
        f"{BRANDING.program_name}\n\nتاريخ البناء: {date.today().isoformat()}\n\n{BRANDING.designer_credit}\n{BRANDING.contact_text}\n",
        encoding="utf-8",
    )
    print(f"Documentation generated: {len(screenshots)} screenshots")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QPageSize, QTextDocument, QTextOption
from PySide6.QtPrintSupport import QPrintPreviewDialog, QPrinter


def show_invoice_preview(parent, *, title, document_no, business_date, party_label, party_name, rows, total, paid, credit, kind):
    printer = QPrinter(QPrinter.HighResolution)
    printer.setPageSize(QPageSize(QPageSize.A4))
    preview = QPrintPreviewDialog(printer, parent)
    preview.setWindowTitle(f"معاينة {kind} {document_no}")

    def render(target_printer):
        document = QTextDocument()
        document.setDefaultTextOption(QTextOption(Qt.AlignRight))
        item_rows = "".join(
            f"<tr><td>{escape(str(name))}</td><td>{escape(str(quantity))}</td><td>{DecimalLike(price):,.2f}</td><td>{DecimalLike(line_total):,.2f}</td></tr>"
            for name, quantity, price, line_total in rows
        )
        html = f"""
        <html><head><meta charset='utf-8'><style>
        body {{ font-family: Arial; direction: rtl; }} h1 {{ text-align:center; }}
        table {{ width:100%; border-collapse:collapse; margin-top:16px; }}
        th,td {{ border:1px solid #777; padding:7px; text-align:right; }}
        .totals {{ width:45%; margin-right:55%; }}
        .brand {{ text-align:center; margin-top:28px; font-size:11px; }}
        </style></head><body>
        <h1>{escape(str(title))}</h1>
        <p><b>رقم الفاتورة:</b> {escape(str(document_no))}<br>
        <b>التاريخ:</b> {escape(str(business_date))}<br>
        <b>{escape(str(party_label))}:</b> {escape(str(party_name))}</p>
        <table><thead><tr><th>الصنف</th><th>الكمية</th><th>السعر</th><th>الإجمالي</th></tr></thead>
        <tbody>{item_rows}</tbody></table>
        <table class='totals'><tr><th>الإجمالي</th><td>{DecimalLike(total):,.2f}</td></tr>
        <tr><th>المدفوع</th><td>{DecimalLike(paid):,.2f}</td></tr>
        <tr><th>المتبقي</th><td>{DecimalLike(credit):,.2f}</td></tr></table>
        <div class='brand'>نظام الماركت المحاسبي<br>تصميم وتنفيذ المهندس : زكريا الحاج<br>لطلب البرنامج أو تصميم برامج أخرى التواصل على الرقم 772233564</div>
        </body></html>"""
        document.setHtml(html)
        document.print_(target_printer)

    preview.paintRequested.connect(render)
    preview.resize(900, 700)
    preview.exec()


def DecimalLike(value):
    return float(value or 0)

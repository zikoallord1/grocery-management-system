import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QFrame, QLineEdit, QPushButton, QVBoxLayout, QLabel, QMessageBox, QHBoxLayout

from backend.app.core.database import DATA_DIR
from backend.app.core.demo_data import seed_demo_data, prepare_for_delivery


SETTINGS_FILE = DATA_DIR / "settings.json"


class SettingsPage(QFrame):
    back_requested = Signal()
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("إعدادات النظام")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("إدارة بيانات البقالة والإعدادات العامة واختبار النظام قبل التسليم.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(desc)
        form = QFormLayout()
        form.setSpacing(12)
        self.store_name = QLineEdit()
        self.store_name.setPlaceholderText("اسم البقالة")
        self.currency = QComboBox()
        self.currency.addItems(["الريال اليمني", "الدولار الأمريكي", "الريال السعودي"])
        self.phone = QLineEdit()
        self.phone.setPlaceholderText("رقم الهاتف")
        self.invoice_footer = QLineEdit()
        self.invoice_footer.setPlaceholderText("عبارة أسفل الفاتورة")
        form.addRow("اسم البقالة", self.store_name)
        form.addRow("العملة الأساسية", self.currency)
        form.addRow("رقم الهاتف", self.phone)
        form.addRow("عبارة الفاتورة", self.invoice_footer)
        layout.addLayout(form)

        save = QPushButton("حفظ الإعدادات")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        layout.addWidget(save, alignment=Qt.AlignRight)

        test_box = QFrame()
        test_layout = QVBoxLayout(test_box)
        test_title = QLabel("اختبار وتهيئة النظام")
        test_title.setStyleSheet("font-size:18px;font-weight:700;")
        test_layout.addWidget(test_title)
        test_note = QLabel("يمكنك تعبئة النظام ببيانات واقعية تجريبية لاختبار المبيعات والمشتريات والمخزون والعملاء والموردين والمصروفات والإيرادات. قبل تسليم البرنامج للعميل استخدم زر التهيئة لحذف بيانات العمل مع الإبقاء على المستخدمين والترخيص.")
        test_note.setWordWrap(True)
        test_layout.addWidget(test_note)
        buttons = QHBoxLayout()
        demo = QPushButton("🧪 تعبئة بيانات تجريبية")
        demo.setObjectName("secondaryButton")
        demo.clicked.connect(self._seed_demo)
        buttons.addWidget(demo)
        reset = QPushButton("🧹 تهيئة النظام قبل التسليم")
        reset.setObjectName("dangerButton")
        reset.clicked.connect(self._prepare_delivery)
        buttons.addWidget(reset)
        test_layout.addLayout(buttons)
        layout.addWidget(test_box)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)
        self._load()

    def _load(self):
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.store_name.setText(str(data.get("store_name", "")))
                    self.phone.setText(str(data.get("phone", "")))
                    self.invoice_footer.setText(str(data.get("invoice_footer", "")))
                    currency = str(data.get("currency", ""))
                    index = self.currency.findText(currency)
                    if index >= 0:
                        self.currency.setCurrentIndex(index)
        except (OSError, ValueError):
            pass

    def _save(self):
        data = {
            "store_name": self.store_name.text().strip(),
            "currency": self.currency.currentText(),
            "phone": self.phone.text().strip(),
            "invoice_footer": self.invoice_footer.text().strip(),
        }
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self.status.setText(f"تعذر حفظ الإعدادات: {exc}")
            return
        self.status.setText("تم حفظ الإعدادات بنجاح على الجهاز.")
        self.settings_changed.emit()

    def _seed_demo(self):
        try:
            counts = seed_demo_data()
            self.status.setText("تمت تعبئة البيانات التجريبية: " + "، ".join(f"{k}={v}" for k, v in counts.items()))
            self.settings_changed.emit()
        except Exception as exc:
            self.status.setText(f"تعذر تعبئة البيانات التجريبية: {exc}")

    def _prepare_delivery(self):
        answer = QMessageBox.question(
            self,
            "تأكيد تهيئة النظام",
            "سيتم حذف بيانات العمل والتجارب من قاعدة البيانات مع الإبقاء على المستخدمين والترخيص وهيكل النظام. هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            prepare_for_delivery()
            self.status.setText("تمت تهيئة النظام للتسليم. البيانات التجريبية وبيانات العمل حُذفت مع إبقاء المستخدمين والترخيص.")
            self.settings_changed.emit()
        except Exception as exc:
            self.status.setText(f"تعذر تهيئة النظام: {exc}")

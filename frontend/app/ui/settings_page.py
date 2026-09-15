from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QFrame, QLineEdit, QComboBox, QPushButton, QVBoxLayout, QLabel


class SettingsPage(QFrame):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("إعدادات النظام")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("إدارة بيانات البقالة والإعدادات العامة وطريقة التعامل مع الفواتير والدفع والطباعة.")
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
        layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)

    def _save(self):
        self.status = getattr(self, "status", QLabel())
        self.status.setText("تم حفظ الإعدادات الحالية للجلسة")
        if self.status.parent() is None:
            self.layout().addWidget(self.status)

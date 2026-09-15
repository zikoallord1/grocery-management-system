from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class PermissionsPage(QFrame):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("الصلاحيات")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("تحديد ما يستطيع كل دور أو مستخدم مشاهدته وإضافته وتعديله واعتماده وطباعته.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(desc)
        permissions = ["عرض", "إضافة", "تعديل", "إلغاء", "اعتماد", "طباعة", "تصدير"]
        modules = ["المبيعات", "المشتريات", "المخزون", "العملاء", "الموردون", "المصروفات", "الصناديق والحسابات", "التقارير", "الإعدادات"]
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("الوحدة"), 0, 0)
        for c, p in enumerate(permissions, 1):
            grid.addWidget(QLabel(p), 0, c)
        for r, module in enumerate(modules, 1):
            grid.addWidget(QLabel(module), r, 0)
            for c in range(1, len(permissions) + 1):
                cb = QCheckBox()
                cb.setChecked(module == "التقارير" and c == 1)
                grid.addWidget(cb, r, c, alignment=Qt.AlignCenter)
        layout.addLayout(grid)
        save = QPushButton("حفظ الصلاحيات")
        save.setObjectName("primaryButton")
        layout.addWidget(save, alignment=Qt.AlignRight)
        layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)

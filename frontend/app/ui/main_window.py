from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SummaryCard(QFrame):
    def __init__(self, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام إدارة البقالات")
        self.resize(1180, 760)
        self.setMinimumSize(980, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(22, 18, 22, 12)
        root_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(22, 16, 22, 16)

        identity = QVBoxLayout()
        title = QLabel("نظام إدارة البقالات")
        title.setObjectName("appTitle")
        subtitle = QLabel("إدارة المبيعات والمشتريات والمخزون والحسابات من مكان واحد")
        subtitle.setObjectName("appSubtitle")
        identity.addWidget(title)
        identity.addWidget(subtitle)

        header_layout.addLayout(identity)
        header_layout.addStretch()
        search_button = QPushButton("بحث شامل")
        search_button.setObjectName("primaryButton")
        header_layout.addWidget(search_button)
        root_layout.addWidget(header)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        for label in ["الرئيسية", "المبيعات", "المشتريات", "المخزون", "العملاء", "الموردون", "المصروفات", "التقارير"]:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            nav.addWidget(button)
        root_layout.addLayout(nav)

        cards = QGridLayout()
        cards.setSpacing(12)
        card_data = [
            ("مبيعات اليوم", "0.00"),
            ("مشتريات اليوم", "0.00"),
            ("المصروفات اليوم", "0.00"),
            ("صافي الربح", "0.00"),
            ("ذمم العملاء", "0.00"),
            ("ذمم الموردين", "0.00"),
            ("رصيد الصندوق", "0.00"),
            ("أصناف منخفضة", "0"),
        ]
        for index, (label, value) in enumerate(card_data):
            cards.addWidget(SummaryCard(label, value), index // 4, index % 4)
        root_layout.addLayout(cards)

        content = QHBoxLayout()
        content.setSpacing(12)

        quick = QFrame()
        quick.setObjectName("panel")
        quick_layout = QVBoxLayout(quick)
        quick_layout.addWidget(QLabel("عمليات سريعة"))
        for label in ["فاتورة بيع جديدة", "فاتورة شراء جديدة", "إضافة صنف", "قبض من عميل", "سداد مورد", "تسجيل مصروف"]:
            button = QPushButton(label)
            button.setObjectName("actionButton")
            quick_layout.addWidget(button)
        quick_layout.addStretch()

        activity = QFrame()
        activity.setObjectName("panel")
        activity_layout = QVBoxLayout(activity)
        activity_layout.addWidget(QLabel("آخر العمليات"))
        empty = QLabel("لا توجد عمليات مسجلة بعد")
        empty.setAlignment(Qt.AlignCenter)
        empty.setObjectName("emptyState")
        activity_layout.addWidget(empty, 1)

        content.addWidget(quick, 1)
        content.addWidget(activity, 2)
        root_layout.addLayout(content, 1)

        footer = QLabel(
            "تصميم وتنفيذ المهندس / زكريا الحاج    |    "
            "لطلب البرنامج او تقديم المساعدة او طلب برامج اخرى التواصل على الرقم 772233564    "
            "☎  |  WhatsApp"
        )
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(footer)

        self.setCentralWidget(root)
        self.setStyleSheet(self._stylesheet())

    @staticmethod
    def _stylesheet() -> str:
        return """
        QWidget { font-family: 'Segoe UI'; font-size: 14px; }
        QMainWindow, QWidget { background: #f4f6f8; color: #1f2933; }
        #header { background: white; border: 1px solid #e1e6eb; border-radius: 12px; }
        #appTitle { font-size: 25px; font-weight: 700; }
        #appSubtitle { color: #667085; margin-top: 3px; }
        #primaryButton { background: #1769aa; color: white; border: 0; border-radius: 8px; padding: 10px 18px; font-weight: 600; }
        #navButton { background: white; border: 1px solid #d9e0e7; border-radius: 8px; padding: 9px 8px; }
        #navButton:hover, #actionButton:hover { background: #eef5fb; }
        #summaryCard, #panel { background: white; border: 1px solid #e1e6eb; border-radius: 12px; }
        #cardTitle { color: #667085; }
        #cardValue { font-size: 22px; font-weight: 700; margin-top: 6px; }
        #actionButton { text-align: right; background: #f8fafc; border: 1px solid #d9e0e7; border-radius: 8px; padding: 10px; }
        #emptyState { color: #98a2b3; }
        #footer { color: #667085; font-size: 12px; padding: 5px; }
        """

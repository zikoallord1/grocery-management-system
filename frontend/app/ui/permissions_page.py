import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from backend.app.core.database import DATA_DIR


PERMISSIONS_FILE = DATA_DIR / "permissions.json"
PERMISSIONS = ["عرض", "إضافة", "تعديل", "إلغاء", "اعتماد", "طباعة", "تصدير"]
MODULES = ["المبيعات", "المشتريات", "المخزون", "العملاء", "الموردون", "المصروفات", "الصناديق والحسابات", "التقارير", "الإعدادات"]


class PermissionsPage(QFrame):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._checks = {}
        self._master_checks = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("الصلاحيات")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("لكل نوع يمكنك الآن تحديد كل الصلاحيات أو إلغاؤها بالكامل من علامة واحدة، أو التحكم في كل صلاحية منفردة.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(desc)

        toolbar = QHBoxLayout()
        select_all = QPushButton("✓ تحديد جميع الصلاحيات")
        select_all.clicked.connect(lambda: self._set_all(True))
        clear_all = QPushButton("✕ إلغاء جميع الصلاحيات")
        clear_all.clicked.connect(lambda: self._set_all(False))
        toolbar.addWidget(select_all)
        toolbar.addWidget(clear_all)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("الوحدة / النوع"), 0, 0)
        for c, permission in enumerate(PERMISSIONS, 1):
            grid.addWidget(QLabel(permission), 0, c)
        grid.addWidget(QLabel("اختيار كامل"), 0, len(PERMISSIONS) + 1)
        grid.addWidget(QLabel("تحكم"), 0, len(PERMISSIONS) + 2)

        saved = self._load()
        for r, module in enumerate(MODULES, 1):
            label = QLabel(module)
            label.setMinimumWidth(150)
            grid.addWidget(label, r, 0)
            self._checks[module] = []
            for c, permission in enumerate(PERMISSIONS, 1):
                cb = QCheckBox()
                cb.setChecked(saved.get(module, {}).get(permission, False))
                self._checks[module].append(cb)
                grid.addWidget(cb, r, c, alignment=Qt.AlignCenter)
                cb.stateChanged.connect(lambda _state, m=module: self._sync_master(m))

            master = QCheckBox("全ها")
            master.setToolTip(f"تحديد أو إلغاء جميع صلاحيات {module}")
            master.stateChanged.connect(lambda state, m=module: self._master_changed(m, state))
            self._master_checks[module] = master
            grid.addWidget(master, r, len(PERMISSIONS) + 1, alignment=Qt.AlignCenter)

            controls = QHBoxLayout()
            choose = QPushButton("تحديد الكل")
            choose.clicked.connect(lambda checked=False, m=module: self._set_module(m, True))
            clear = QPushButton("إلغاء الكل")
            clear.clicked.connect(lambda checked=False, m=module: self._set_module(m, False))
            controls.addWidget(choose)
            controls.addWidget(clear)
            holder = QWidget()
            holder.setLayout(controls)
            grid.addWidget(holder, r, len(PERMISSIONS) + 2)

        layout.addLayout(grid)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        save = QPushButton("حفظ الصلاحيات")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        layout.addWidget(save, alignment=Qt.AlignRight)
        layout.addStretch()
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)

        for module in MODULES:
            self._sync_master(module)

    def _set_module(self, module, checked):
        master = self._master_checks[module]
        master.blockSignals(True)
        master.setChecked(checked)
        master.blockSignals(False)
        for cb in self._checks[module]:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)

    def _master_changed(self, module, state):
        if state == Qt.PartiallyChecked:
            return
        self._set_module(module, state == Qt.Checked)

    def _sync_master(self, module):
        checks = self._checks[module]
        if not checks:
            return
        checked_count = sum(cb.isChecked() for cb in checks)
        master = self._master_checks[module]
        master.blockSignals(True)
        if checked_count == 0:
            master.setCheckState(Qt.Unchecked)
        elif checked_count == len(checks):
            master.setCheckState(Qt.Checked)
        else:
            master.setCheckState(Qt.PartiallyChecked)
        master.blockSignals(False)

    def _set_all(self, checked):
        for module in MODULES:
            self._set_module(module, checked)

    def _load(self):
        try:
            if PERMISSIONS_FILE.exists():
                data = json.loads(PERMISSIONS_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            pass
        return {}

    def _save(self):
        data = {
            module: {permission: cb.isChecked() for permission, cb in zip(PERMISSIONS, checks)}
            for module, checks in self._checks.items()
        }
        try:
            PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            PERMISSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            self.status.setText(f"تعذر حفظ الصلاحيات: {exc}")
            return
        self.status.setText("تم حفظ الصلاحيات بنجاح.")

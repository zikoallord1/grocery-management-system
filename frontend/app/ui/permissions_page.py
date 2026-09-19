import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from backend.app.core.database import DATA_DIR
from backend.app.core.identity import audit_current_actor
from backend.app.core.database import get_session
from uuid import uuid4


PERMISSIONS_FILE = DATA_DIR / "permissions.json"
PERMISSIONS = ["عرض", "إضافة", "تعديل", "إلغاء", "اعتماد", "طباعة", "تصدير"]
MODULES = ["المبيعات", "المشتريات", "الأصناف", "المخزون", "العملاء", "الموردون", "المصروفات", "الصناديق والحسابات", "التقارير", "الإعدادات", "المستخدمون", "الصلاحيات"]
ROLES = ["مدير النظام", "مدير", "محاسب", "بائع", "مخزن", "مستخدم مخصص"]


class PermissionsPage(QFrame):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")
        self._checks = {}
        self._master_checks = {}
        self._all_master = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        title = QLabel("الصلاحيات")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        desc = QLabel("اختر نوع المستخدم أولًا. يمكنك تحديد كل صلاحيات الوحدة أو إلغاؤها بالكامل بعلامة واحدة، أو ضبط كل صلاحية منفردة.")
        desc.setWordWrap(True)
        desc.setObjectName("pageDescription")
        layout.addWidget(desc)

        role_row = QHBoxLayout()
        role_row.addWidget(QLabel("نوع المستخدم:"))
        self.role = QComboBox()
        self.role.addItems(ROLES)
        self.role.currentIndexChanged.connect(self._load_role)
        role_row.addWidget(self.role, 1)
        self.all_master = QCheckBox("تحديد/إلغاء الكل لهذا النوع")
        self.all_master.stateChanged.connect(self._all_master_changed)
        role_row.addWidget(self.all_master)
        layout.addLayout(role_row)

        toolbar = QHBoxLayout()
        select_all = QPushButton("✓ تحديد جميع الصلاحيات")
        select_all.clicked.connect(lambda: self._set_all(True))
        clear_all = QPushButton("✕ إلغاء جميع الصلاحيات")
        clear_all.clicked.connect(lambda: self._set_all(False))
        toolbar.addWidget(select_all)
        toolbar.addWidget(clear_all)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        headers = ["الوحدة / النوع", *PERMISSIONS, "اختيار كامل"]
        for col, text in enumerate(headers):
            grid.addWidget(QLabel(text), 0, col)

        for row, module in enumerate(MODULES, 1):
            grid.addWidget(QLabel(module), row, 0)
            self._checks[module] = []
            for col, permission in enumerate(PERMISSIONS, 1):
                cb = QCheckBox()
                cb.stateChanged.connect(lambda _state, m=module: self._sync_master(m))
                self._checks[module].append(cb)
                grid.addWidget(cb, row, col, alignment=Qt.AlignCenter)
            master = QCheckBox("الكل")
            master.stateChanged.connect(lambda state, m=module: self._master_changed(m, state))
            self._master_checks[module] = master
            grid.addWidget(master, row, len(PERMISSIONS) + 1, alignment=Qt.AlignCenter)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        save = QPushButton("حفظ الصلاحيات")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        layout.addWidget(save, alignment=Qt.AlignRight)
        back = QPushButton("العودة إلى الرئيسية")
        back.setObjectName("secondaryButton")
        back.clicked.connect(self.back_requested.emit)
        layout.addWidget(back, alignment=Qt.AlignLeft)
        self._load_role()

    def _read(self):
        try:
            if PERMISSIONS_FILE.exists():
                data = json.loads(PERMISSIONS_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            pass
        return {}

    def _role_data(self):
        data = self._read()
        role_data = data.get(self.role.currentText(), {})
        if isinstance(role_data, dict):
            return role_data
        return {}

    def _load_role(self):
        saved = self._role_data()
        for module, checks in self._checks.items():
            module_data = saved.get(module, {}) if isinstance(saved.get(module, {}), dict) else {}
            for permission, cb in zip(PERMISSIONS, checks):
                cb.blockSignals(True)
                cb.setChecked(bool(module_data.get(permission, False)))
                cb.blockSignals(False)
            self._sync_master(module)
        self._sync_all_master()
        self.status.setText(f"الصلاحيات المعروضة تخص: {self.role.currentText()}")

    def _set_module(self, module, checked):
        master = self._master_checks[module]
        master.blockSignals(True)
        master.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        master.blockSignals(False)
        for cb in self._checks[module]:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._sync_all_master()

    def _master_changed(self, module, state):
        if state == Qt.PartiallyChecked:
            return
        self._set_module(module, state == Qt.Checked)

    def _sync_master(self, module):
        checks = self._checks[module]
        count = sum(cb.isChecked() for cb in checks)
        master = self._master_checks[module]
        master.blockSignals(True)
        master.setCheckState(Qt.Unchecked if count == 0 else Qt.Checked if count == len(checks) else Qt.PartiallyChecked)
        master.blockSignals(False)
        self._sync_all_master()

    def _set_all(self, checked):
        for module in MODULES:
            self._set_module(module, checked)
        self._sync_all_master()

    def _all_master_changed(self, state):
        if state == Qt.PartiallyChecked:
            return
        self._set_all(state == Qt.Checked)

    def _sync_all_master(self):
        if not hasattr(self, "all_master"):
            return
        states = [cb.checkState() for cb in self._master_checks.values()]
        self.all_master.blockSignals(True)
        if states and all(state == Qt.Checked for state in states):
            self.all_master.setCheckState(Qt.Checked)
        elif states and all(state == Qt.Unchecked for state in states):
            self.all_master.setCheckState(Qt.Unchecked)
        else:
            self.all_master.setCheckState(Qt.PartiallyChecked)
        self.all_master.blockSignals(False)

    def _save(self):
        data = self._read()
        data[self.role.currentText()] = {
            module: {permission: cb.isChecked() for permission, cb in zip(PERMISSIONS, checks)}
            for module, checks in self._checks.items()
        }
        try:
            PERMISSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
            PERMISSIONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            session = get_session()
            try:
                audit_current_actor(
                    session,
                    operation_id=f"PERMISSIONS:{uuid4()}",
                    action="PERMISSIONS_UPDATED",
                    entity_type="ROLE_PERMISSIONS",
                    details={"role": self.role.currentText()},
                )
                session.commit()
            finally:
                session.close()
        except OSError as exc:
            self.status.setText(f"تعذر حفظ الصلاحيات: {exc}")
            return
        self.status.setText(f"تم حفظ صلاحيات نوع «{self.role.currentText()}» بنجاح.")

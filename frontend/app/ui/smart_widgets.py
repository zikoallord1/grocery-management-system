from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QLineEdit


class SmartComboBox(QComboBox):
    """Editable selector with fast substring completion for keyboard/barcode input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMinimumContentsLength(18)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._completer = QCompleter(self.model(), self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self.setCompleter(self._completer)
        self.lineEdit().setClearButtonEnabled(True)

    def configure_smart_input(self, placeholder="ابحث بالاسم أو الرمز أو الباركود..."):
        self.lineEdit().setPlaceholderText(placeholder)
        self._completer.setModel(self.model())
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)

    def set_smart_items(self, items, keep_data=None):
        current = self.currentData() if keep_data is None else keep_data
        self.blockSignals(True)
        self.clear()
        for text, data in items:
            self.addItem(text, data)
        self.blockSignals(False)
        self._completer.setModel(self.model())
        if current is not None:
            index = self.findData(current)
            if index >= 0:
                self.setCurrentIndex(index)
        self.configure_smart_input()


class SmartSearchLineEdit(QLineEdit):
    """Common search field contract used by list pages."""

    def __init__(self, parent=None, placeholder="بحث..."):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setClearButtonEnabled(True)
        self.setProperty("smartSearch", True)

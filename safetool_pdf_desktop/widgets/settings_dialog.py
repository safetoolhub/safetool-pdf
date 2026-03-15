# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Settings Dialog — Application preferences."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_desktop.settings import THEME, load_setting, save_setting
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager

class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 300)
        self.resize(500, 350)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_16)

        # Header
        header = QLabel("Settings")
        header.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XL}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
        )
        layout.addWidget(header)

        # Theme section
        theme_card = QFrame()
        theme_card.setStyleSheet(DesignSystem.get_card_style())
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setSpacing(DesignSystem.SPACE_8)

        theme_title = QLabel("Appearance")
        theme_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        theme_layout.addWidget(theme_title)

        theme_row = QHBoxLayout()
        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        theme_row.addWidget(theme_label)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Light", "System"])
        self._theme_combo.setStyleSheet(DesignSystem.get_combobox_style())

        current_theme = str(load_setting(THEME, "system"))
        idx = {"light": 0, "system": 1}.get(current_theme, 1)
        self._theme_combo.setCurrentIndex(idx)
        theme_row.addWidget(self._theme_combo)
        theme_row.addStretch()

        theme_layout.addLayout(theme_row)

        theme_note = QLabel(
            "Note: SafeTool PDF uses a light Material Design theme by default. "
            "Changes take effect on restart."
        )
        theme_note.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )
        theme_note.setWordWrap(True)
        theme_layout.addWidget(theme_note)

        layout.addWidget(theme_card)

        # Ghostscript info
        gs_card = QFrame()
        gs_card.setStyleSheet(DesignSystem.get_card_style())
        gs_layout = QVBoxLayout(gs_card)
        gs_layout.setSpacing(DesignSystem.SPACE_8)

        gs_title = QLabel("Ghostscript")
        gs_title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_MD}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        gs_layout.addWidget(gs_title)

        from safetool_pdf_core.gs_detect import gs_available

        gs_status = "Installed ✓" if gs_available() else "Not found ✗"
        gs_color = DesignSystem.COLOR_SUCCESS if gs_available() else DesignSystem.COLOR_DANGER

        gs_row = QHBoxLayout()
        gs_label = QLabel("Status:")
        gs_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        gs_row.addWidget(gs_label)

        gs_status_label = QLabel(gs_status)
        gs_status_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {gs_color};"
            f"border: none; background: transparent;"
        )
        gs_row.addWidget(gs_status_label)
        gs_row.addStretch()
        gs_layout.addLayout(gs_row)

        gs_note = QLabel(
            "Ghostscript is needed for Moderate and Aggressive presets "
            "(font subsetting, full PDF rewrite). Without it, these features are skipped."
        )
        gs_note.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )
        gs_note.setWordWrap(True)
        gs_layout.addWidget(gs_note)

        layout.addWidget(gs_card)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _save(self) -> None:
        themes = {0: "light", 1: "system"}
        theme = themes.get(self._theme_combo.currentIndex(), "system")
        save_setting(THEME, theme)
        self.accept()

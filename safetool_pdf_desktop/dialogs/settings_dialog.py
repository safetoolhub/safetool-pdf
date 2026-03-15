# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Settings Dialog — Application preferences with suffix configuration."""

from __future__ import annotations

import re
import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QTabWidget,
    QScrollArea,
    QGroupBox,
)

from safetool_pdf_core.constants import OUTPUT_SUFFIX
from safetool_pdf_desktop.dialogs.base_dialog import BaseDialog
from safetool_pdf_desktop.settings import (
    OUTPUT_SUFFIX as OUTPUT_SUFFIX_KEY,
    ENABLE_LOGGING,
    load_setting,
    save_setting,
    get_language,
    set_language as save_language,
)
from safetool_pdf_desktop.styles.design_system import DesignSystem
from i18n import tr, SUPPORTED_LANGUAGES, set_language as set_i18n_language


# Characters forbidden in filenames on Windows and most filesystems
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


class SettingsDialog(BaseDialog):
    """Application settings dialog with SafeTool Pix premium style."""

    settings_saved = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings.window_title"))
        self.setMinimumSize(600, 500)
        self.resize(720, 580)
        
        # Original values for change detection
        self._original_values = {}
        self._loading = True
        
        self._build_ui()
        self._load_current_settings()
        
        self._loading = False
        self._validate_changes()

    def _build_ui(self) -> None:
        """Construct the UI using QTabWidget and QGroupBox."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(DesignSystem.get_tab_widget_style())

        # === TAB 1: GENERAL ===
        general_tab = self._create_general_tab()
        self.tabs.addTab(self._wrap_in_scroll_area(general_tab), tr("settings.header"))

        main_layout.addWidget(self.tabs)

        # Footer Buttons
        footer = self._create_footer()
        main_layout.addWidget(footer)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("generalTab")
        widget.setStyleSheet(f"#generalTab {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_20, DesignSystem.SPACE_20, DesignSystem.SPACE_20)
        layout.setSpacing(DesignSystem.SPACE_20)

        # ── 1. Language Section ─────────────────────────────────────────
        lang_group = self._create_groupbox(tr("settings.language"))
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(DesignSystem.SPACE_12)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(DesignSystem.SPACE_12)
        
        lang_label = QLabel(tr("settings.language_label"))
        lang_label.setStyleSheet(DesignSystem.get_settings_label_style())
        lang_row.addWidget(lang_label)

        self._lang_combo = QComboBox()
        self._lang_combo.setStyleSheet(DesignSystem.get_combobox_style())
        current_lang = get_language()
        self._lang_codes = list(SUPPORTED_LANGUAGES.keys())
        for code in self._lang_codes:
            self._lang_combo.addItem(SUPPORTED_LANGUAGES[code], code)
        lang_idx = self._lang_codes.index(current_lang) if current_lang in self._lang_codes else 0
        self._lang_combo.setCurrentIndex(lang_idx)
        self._lang_combo.currentIndexChanged.connect(self._validate_changes)
        
        lang_row.addWidget(self._lang_combo, 1)
        lang_layout.addLayout(lang_row)
        
        lang_note = self._create_info_label(tr("settings.language_note"))
        lang_layout.addWidget(lang_note)
        
        layout.addWidget(lang_group)

        # ── 2. Output Suffix Section ────────────────────────────────────
        suffix_group = self._create_groupbox(tr("settings.output"))
        suffix_layout = QVBoxLayout(suffix_group)
        suffix_layout.setSpacing(DesignSystem.SPACE_12)

        suffix_row = QHBoxLayout()
        suffix_row.setSpacing(DesignSystem.SPACE_12)
        
        suffix_label = QLabel(tr("settings.suffix_label"))
        suffix_label.setStyleSheet(DesignSystem.get_settings_label_style())
        suffix_row.addWidget(suffix_label)

        self._suffix_edit = QLineEdit()
        current_suffix = str(load_setting(OUTPUT_SUFFIX_KEY, OUTPUT_SUFFIX))
        self._suffix_edit.setText(current_suffix)
        self._suffix_edit.setPlaceholderText("_safetoolpdf")
        self._suffix_edit.setStyleSheet(DesignSystem.get_line_edit_style())
        self._suffix_edit.textChanged.connect(self._update_preview)
        suffix_row.addWidget(self._suffix_edit, 1)
        suffix_layout.addLayout(suffix_row)

        self._suffix_preview = QLabel()
        self._suffix_preview.setStyleSheet(DesignSystem.get_settings_preview_style())
        suffix_layout.addWidget(self._suffix_preview)

        self._suffix_error = QLabel()
        self._suffix_error.setStyleSheet(DesignSystem.get_settings_error_style())
        self._suffix_error.hide()
        suffix_layout.addWidget(self._suffix_error)

        suffix_note = self._create_info_label(tr("settings.suffix_note"))
        suffix_layout.addWidget(suffix_note)

        layout.addWidget(suffix_group)

        # ── 3. Debugging Section ────────────────────────────────────────
        debug_group = self._create_groupbox(tr("settings.debugging"))
        debug_layout = QVBoxLayout(debug_group)
        debug_layout.setSpacing(DesignSystem.SPACE_12)
        
        self._logging_checkbox = QCheckBox(tr("settings.enable_logging"))
        self._logging_checkbox.setStyleSheet(DesignSystem.get_checkbox_style())
        current_logging = bool(load_setting(ENABLE_LOGGING, False))
        self._logging_checkbox.setChecked(current_logging)
        self._logging_checkbox.stateChanged.connect(self._validate_changes)
        debug_layout.addWidget(self._logging_checkbox)

        from pathlib import Path
        log_file_path = Path.home() / "logs" / "safetool-pdf.log"
        logging_note = self._create_info_label(tr("settings.logging_note", path=str(log_file_path)))
        logging_note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        debug_layout.addWidget(logging_note)

        layout.addWidget(debug_group)

        # ── 4. Ghostscript Section ──────────────────────────────────────
        gs_group = self._create_groupbox(tr("settings.ghostscript"))
        gs_layout = QVBoxLayout(gs_group)
        gs_layout.setSpacing(DesignSystem.SPACE_12)
        
        from safetool_pdf_core.gs_detect import find_gs
        gs_path = find_gs()
        gs_ok = gs_path is not None
        gs_status = tr("settings.gs_installed") if gs_ok else tr("settings.gs_not_found")
        gs_style = DesignSystem.get_settings_success_style() if gs_ok else DesignSystem.get_settings_danger_style()

        gs_status_row = QHBoxLayout()
        gs_status_row.setSpacing(DesignSystem.SPACE_12)
        
        gs_label = QLabel(tr("settings.gs_status_label"))
        gs_label.setStyleSheet(DesignSystem.get_settings_label_style())
        gs_status_row.addWidget(gs_label)
        
        gs_status_val = QLabel(gs_status)
        gs_status_val.setStyleSheet(gs_style)
        gs_status_row.addWidget(gs_status_val)
        gs_status_row.addStretch()
        gs_layout.addLayout(gs_status_row)

        gs_note = self._create_info_label(tr("settings.gs_note"))
        gs_layout.addWidget(gs_note)

        if not gs_ok:
            gs_install = QLabel(tr("about.welcome.system_tools.install_instructions"))
            gs_install.setWordWrap(True)
            gs_install.setOpenExternalLinks(True)
            gs_install.setStyleSheet(DesignSystem.get_settings_note_style())
            gs_layout.addWidget(gs_install)

        layout.addWidget(gs_group)

        layout.addStretch()
        self._update_preview()
        return widget

    def _create_footer(self) -> QFrame:
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(DesignSystem.SPACE_20, DesignSystem.SPACE_16, DesignSystem.SPACE_20, DesignSystem.SPACE_16)
        footer_layout.setSpacing(DesignSystem.SPACE_12)
        
        footer_layout.addStretch()

        cancel_btn = QPushButton(tr("settings.cancel"))
        cancel_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        self._save_btn = QPushButton(tr("settings.save"))
        self._save_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.clicked.connect(self._save)
        self._save_btn.setEnabled(False)  # Disabled until changes detected
        footer_layout.addWidget(self._save_btn)

        return footer

    def _wrap_in_scroll_area(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(widget)
        scroll.setStyleSheet("background-color: transparent;")
        return scroll

    def _create_groupbox(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_LG}px;
                margin-top: {DesignSystem.SPACE_12}px;
                padding-top: {DesignSystem.SPACE_24}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: {DesignSystem.SPACE_16}px;
                padding: 0 {DesignSystem.SPACE_4}px;
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
        """)
        return group

    def _create_info_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(f"""
            QLabel {{
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-style: italic;
                padding: {DesignSystem.SPACE_4}px 0;
            }}
        """)
        return label

    def _load_current_settings(self) -> None:
        """Capture original values for change detection."""
        self._original_values = {
            "suffix": self._suffix_edit.text(),
            "lang": self._lang_combo.currentData(),
            "logging": self._logging_checkbox.isChecked()
        }

    def _update_preview(self) -> None:
        suffix = self._suffix_edit.text().strip()
        if suffix:
            self._suffix_preview.setText(tr("settings.suffix_preview", suffix=suffix))
        else:
            self._suffix_preview.setText(tr("settings.suffix_preview", suffix=""))

        error = self._validate_suffix(suffix)
        if error:
            self._suffix_error.setText(error)
            self._suffix_error.show()
        else:
            self._suffix_error.hide()
            
        self._validate_changes()

    def _validate_changes(self) -> None:
        """Enable save button only if changes are valid and different from original."""
        if self._loading:
            return

        suffix = self._suffix_edit.text().strip()
        has_error = bool(self._validate_suffix(suffix))
        
        changed = (
            suffix != self._original_values["suffix"] or
            self._lang_combo.currentData() != self._original_values["lang"] or
            self._logging_checkbox.isChecked() != self._original_values["logging"]
        )
        
        self._save_btn.setEnabled(changed and not has_error)

    @staticmethod
    def _validate_suffix(suffix: str) -> str:
        if not suffix:
            return tr("settings.suffix_error_empty")
        if _INVALID_CHARS.search(suffix):
            return tr("settings.suffix_error_invalid")
        if len(suffix) > 60:
            return tr("settings.suffix_error_long")
        return ""

    def _save(self) -> None:
        suffix = self._suffix_edit.text().strip()
        if suffix and not self._validate_suffix(suffix):
            save_setting(OUTPUT_SUFFIX_KEY, suffix)

        lang_code = self._lang_combo.currentData()
        if lang_code:
            save_language(lang_code)
            set_i18n_language(lang_code)

        # Save logging preference
        save_setting(ENABLE_LOGGING, self._logging_checkbox.isChecked())

        self.accept()

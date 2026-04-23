# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""About dialog showing application information and license — Design System styling."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_core.constants import (
    APP_NAME,
    AUTHOR,
    LICENSE_TEXT,
    VERSION,
    WEBSITE,
)
from config import APP_DESCRIPTION, APP_REPO
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager

class AboutDialog(QDialog):
    """Modal About dialog with app info, branding, and license text."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(480)
        self.resize(520, 480)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(DesignSystem.SPACE_16)

        # App icon + title card
        header_card = QFrame()
        header_card.setStyleSheet(DesignSystem.get_card_style())
        header_layout = QVBoxLayout(header_card)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(DesignSystem.SPACE_8)

        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, 'file-pdf',
            color=DesignSystem.COLOR_PRIMARY, size=48,
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)

        title = QLabel(APP_NAME)
        title.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_2XL}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)

        version_label = QLabel(f"Version {VERSION}")
        version_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(version_label)

        layout.addWidget(header_card)

        # Info card
        info_card = QFrame()
        info_card.setStyleSheet(DesignSystem.get_card_style())
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(DesignSystem.SPACE_8)

        desc = QLabel(APP_DESCRIPTION)
        desc.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(desc)

        # Author
        author_label = QLabel(f"Developed by {AUTHOR}")
        author_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(author_label)

        # Website
        website_label = QLabel(
            f'<a href="{WEBSITE}" style="color:{DesignSystem.COLOR_PRIMARY};">{WEBSITE}</a>'
        )
        website_label.setOpenExternalLinks(True)
        website_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        website_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"border: none; background: transparent;"
        )
        info_layout.addWidget(website_label)

        layout.addWidget(info_card)

        # License text
        license_edit = QTextEdit()
        license_edit.setReadOnly(True)
        license_edit.setPlainText(LICENSE_TEXT)
        license_edit.setMaximumHeight(160)
        license_edit.setStyleSheet(
            f"QTextEdit {{"
            f"  font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"  font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"  color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"  background-color: {DesignSystem.COLOR_BACKGROUND};"
            f"  border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f"  border-radius: {DesignSystem.RADIUS_SM}px;"
            f"  padding: {DesignSystem.SPACE_8}px;"
            f"}}"
        )
        layout.addWidget(license_edit)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

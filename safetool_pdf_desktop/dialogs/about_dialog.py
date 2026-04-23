# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""About dialog with tutorial, tools overview, and technical info.

Implements a professional informative dialog serving as:
- Application information (version, credits)
- Workflow tutorial (step-by-step usage guide)
- Tools reference (current and future)
- Technical and licensing information

Uses lateral tab navigation with cards and consistent DesignSystem styles.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import (
    APP_AUTHOR,
    APP_CONTACT,
    APP_NAME,
    APP_VERSION,
    APP_VERSION_SUFFIX,
    APP_WEBSITE,
)
from safetool_pdf_core.gs_detect import find_gs
from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr


# Category colors for the tools tab
_CATEGORY_COLORS = {
    "available": {
        "bg": "rgba(25, 135, 84, 0.04)",
        "border": "rgba(25, 135, 84, 0.12)",
        "accent": "#198754",
        "icon": "#198754",
    },
    "upcoming": {
        "bg": "rgba(13, 110, 253, 0.04)",
        "border": "rgba(13, 110, 253, 0.12)",
        "accent": "#0D6EFD",
        "icon": "#0D6EFD",
    },
}


def _get_full_version() -> str:
    """Return version string with optional suffix."""
    if APP_VERSION_SUFFIX:
        return f"{APP_VERSION}-{APP_VERSION_SUFFIX}"
    return APP_VERSION


class AboutDialog(QDialog):
    """About dialog with tutorial, tools, and info tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.parent_window = parent
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle(tr("about.title", name=APP_NAME))
        self.setModal(True)
        self.setMinimumSize(1100, 920)
        self.resize(1100, 920)

        self.setStyleSheet(DesignSystem.get_stylesheet())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === HEADER ===
        main_layout.addWidget(self._create_header())

        # === CONTENT WITH TABS ===
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.West)
        self.tab_widget.setStyleSheet(
            DesignSystem.get_tutorial_tab_widget_style()
        )

        self.tab_widget.addTab(
            self._create_welcome_tab(), tr("about.tab.welcome")
        )
        self.tab_widget.addTab(
            self._create_tools_tab(), tr("about.tab.tools")
        )
        self.tab_widget.addTab(
            self._create_tech_tab(), tr("about.tab.info")
        )

        content_layout.addWidget(self.tab_widget)
        main_layout.addWidget(content_widget, 1)

        # === FOOTER ===
        main_layout.addWidget(self._create_footer())

    # ==================== HEADER / FOOTER ====================

    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {DesignSystem.COLOR_PRIMARY},
                    stop:1 {DesignSystem.COLOR_PRIMARY_HOVER});
            }}
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 12, 24, 12)

        # Left: title + version
        left_layout = QVBoxLayout()
        left_layout.setSpacing(2)

        title = QLabel(APP_NAME)
        title.setStyleSheet(f"""
            color: white;
            font-size: {DesignSystem.FONT_SIZE_XL}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        title.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        left_layout.addWidget(title)

        version = QLabel(
            tr("about.header.version", version=_get_full_version())
        )
        version.setStyleSheet(f"""
            color: rgba(255, 255, 255, 0.9);
            font-size: {DesignSystem.FONT_SIZE_SM}px;
        """)
        version.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        left_layout.addWidget(version)

        header_layout.addLayout(left_layout)
        header_layout.addStretch()

        # Right: privacy badge
        privacy_badge = QLabel(tr("about.header.privacy_badge"))
        privacy_badge.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
                padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                border-radius: {DesignSystem.RADIUS_FULL}px;
            }}
        """)
        privacy_badge.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        header_layout.addWidget(privacy_badge)

        return header

    def _create_footer(self) -> QFrame:
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border-top: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 10, 24, 10)
        footer_layout.addStretch()

        close_btn = QPushButton(tr("common.close"))
        close_btn.setStyleSheet(DesignSystem.get_primary_button_style())
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        footer_layout.addWidget(close_btn)

        return footer

    def _create_scroll_content(self, content_widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setStyleSheet(DesignSystem.get_tutorial_scroll_area_style())
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(content_widget)
        return scroll

    # ==================== WELCOME TAB ====================

    def _create_welcome_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
        )
        layout.setSpacing(DesignSystem.SPACE_10)

        # Title + description
        welcome_title = QLabel(tr("about.welcome.title"))
        welcome_title.setStyleSheet(
            DesignSystem.get_tutorial_section_header_style()
        )
        welcome_title.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(welcome_title)

        description = QLabel(tr("about.welcome.description"))
        description.setWordWrap(True)
        description.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_BASE}px;"
        )
        description.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(description)

        # Workflow section
        workflow_title = QLabel(tr("about.welcome.workflow_title"))
        workflow_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_MD}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_PRIMARY};
            margin-top: {DesignSystem.SPACE_8}px;
        """)
        workflow_title.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(workflow_title)

        workflow_desc = QLabel(tr("about.welcome.workflow_description"))
        workflow_desc.setWordWrap(True)
        workflow_desc.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" margin-bottom: {DesignSystem.SPACE_4}px;"
        )
        workflow_desc.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(workflow_desc)

        # Steps
        steps_container = QVBoxLayout()
        steps_container.setSpacing(DesignSystem.SPACE_8)

        steps = [
            (
                "1",
                tr("about.welcome.steps.1.title"),
                tr("about.welcome.steps.1.description"),
            ),
            (
                "2",
                tr("about.welcome.steps.2.title"),
                tr("about.welcome.steps.2.description"),
            ),
            (
                "3",
                tr("about.welcome.steps.3.title"),
                tr("about.welcome.steps.3.description"),
            ),
            (
                "4",
                tr("about.welcome.steps.4.title"),
                tr("about.welcome.steps.4.description"),
            ),
        ]

        for num, step_title, step_desc in steps:
            step_widget = self._create_step_widget_compact(
                num, step_title, step_desc
            )
            steps_container.addWidget(step_widget)

        layout.addLayout(steps_container)

        # Tips row
        tips_layout = QHBoxLayout()
        tips_layout.setSpacing(DesignSystem.SPACE_8)

        tip1 = self._create_mini_tip(
            tr("about.welcome.tips.privacy.title"),
            tr("about.welcome.tips.privacy.description"),
        )
        tip2 = self._create_mini_tip(
            tr("about.welcome.tips.presets.title"),
            tr("about.welcome.tips.presets.description"),
        )
        tip3 = self._create_mini_tip(
            tr("about.welcome.tips.ghostscript.title"),
            tr("about.welcome.tips.ghostscript.description"),
        )

        tips_layout.addWidget(tip1)
        tips_layout.addWidget(tip2)
        tips_layout.addWidget(tip3)
        layout.addLayout(tips_layout)

        # System tools section (Ghostscript check)
        tools_section = self._create_system_tools_section()
        layout.addWidget(tools_section)

        # Navigation
        nav_widget = self._create_tab_navigation(
            next_tab=1, next_label=tr("about.nav.view_tools")
        )
        layout.addWidget(nav_widget)

        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== SYSTEM TOOLS SECTION ====================

    def _create_system_tools_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
                margin-top: {DesignSystem.SPACE_2}px;
            }}
        """)

        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(
            0, DesignSystem.SPACE_4, 0, DesignSystem.SPACE_4
        )
        main_layout.setSpacing(DesignSystem.SPACE_2)

        # Section title
        title_layout = QHBoxLayout()
        title_layout.setSpacing(DesignSystem.SPACE_8)

        tools_icon = QLabel()
        icon_manager.set_label_icon(
            tools_icon, "settings",
            color=DesignSystem.COLOR_PRIMARY, size=18,
        )
        title_layout.addWidget(tools_icon)

        title_label = QLabel(tr("about.welcome.system_tools.title"))
        title_label.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
            background: transparent;
            border: none;
        """)
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # Info text
        info_label = QLabel(tr("about.welcome.system_tools.info"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-style: italic;
            background: transparent;
            border: none;
        """)
        info_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        main_layout.addWidget(info_label)

        # Status + check button row
        tools_row = QWidget()
        tools_row_layout = QHBoxLayout(tools_row)
        tools_row_layout.setContentsMargins(0, 0, 0, 0)
        tools_row_layout.setSpacing(DesignSystem.SPACE_12)

        self.gs_status_frame = QFrame()
        self.gs_status_frame.setStyleSheet(
            "background-color: transparent; border: none;"
        )

        gs_status_layout = QVBoxLayout(self.gs_status_frame)
        gs_status_layout.setContentsMargins(0, 0, 0, 0)
        gs_status_layout.setSpacing(DesignSystem.SPACE_4)

        self.gs_status_label = QLabel(
            tr("about.welcome.system_tools.gs_checking")
        )
        self.gs_status_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" background: transparent; border: none;"
        )
        gs_status_layout.addWidget(self.gs_status_label)

        tools_row_layout.addWidget(self.gs_status_frame, 1)

        check_btn = QPushButton(
            tr("about.welcome.system_tools.check_button")
        )
        check_btn.setFixedWidth(120)
        check_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
        check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        check_btn.setToolTip(
            tr("about.welcome.system_tools.check_button_tooltip")
        )
        check_btn.clicked.connect(self._check_system_tools)
        tools_row_layout.addWidget(
            check_btn, 0, Qt.AlignmentFlag.AlignTop
        )

        main_layout.addWidget(tools_row)

        # Install info (collapsible)
        self.install_info_btn = QPushButton(
            tr("about.welcome.system_tools.install_how")
        )
        self.install_info_btn.setFlat(True)
        self.install_info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_info_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_PRIMARY};
                text-align: left;
                padding: {DesignSystem.SPACE_4}px 0;
                border: none;
            }}
            QPushButton:hover {{
                color: {DesignSystem.COLOR_PRIMARY_HOVER};
                text-decoration: underline;
            }}
        """)
        self.install_info_btn.clicked.connect(self._toggle_install_info)
        main_layout.addWidget(self.install_info_btn)

        self.install_info_panel = QLabel(
            tr("about.welcome.system_tools.install_instructions")
        )
        self.install_info_panel.setWordWrap(True)
        self.install_info_panel.setOpenExternalLinks(True)
        self.install_info_panel.setStyleSheet(f"""
            QLabel {{
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                background-color: {DesignSystem.COLOR_WARNING_BG};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_6}px;
                margin-left: {DesignSystem.SPACE_8}px;
            }}
        """)
        self.install_info_panel.hide()
        main_layout.addWidget(self.install_info_panel)

        # Auto-check on creation
        QTimer.singleShot(10, self._check_system_tools)

        return frame

    def _check_system_tools(self) -> None:
        gs_path = find_gs()
        if gs_path:
            self.gs_status_label.setText(
                tr("about.welcome.system_tools.gs_installed")
            )
            self.gs_status_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_SUCCESS};"
                f" background: transparent; border: none;"
            )
            status_color = DesignSystem.COLOR_SUCCESS
        else:
            self.gs_status_label.setText(
                tr("about.welcome.system_tools.gs_not_installed")
            )
            self.gs_status_label.setStyleSheet(
                f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" color: {DesignSystem.COLOR_DANGER};"
                f" background: transparent; border: none;"
            )
            status_color = DesignSystem.COLOR_DANGER

        self.gs_status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
                border-left: 3px solid {status_color};
                padding-left: {DesignSystem.SPACE_8}px;
            }}
        """)

    def _toggle_install_info(self) -> None:
        if self.install_info_panel.isVisible():
            self.install_info_panel.hide()
            self.install_info_btn.setText(
                tr("about.welcome.system_tools.install_how")
            )
        else:
            self.install_info_panel.show()
            self.install_info_btn.setText(
                tr("about.welcome.system_tools.install_hide")
            )

    # ==================== TOOLS TAB ====================

    def _create_tools_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_16, DesignSystem.SPACE_8,
            DesignSystem.SPACE_16, DesignSystem.SPACE_8,
        )
        layout.setSpacing(DesignSystem.SPACE_6)

        title = QLabel(tr("about.tools_section.title"))
        title.setStyleSheet(
            DesignSystem.get_tutorial_section_header_style()
        )
        title.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(title)

        # === AVAILABLE TOOLS ===
        colors_avail = _CATEGORY_COLORS["available"]
        header_avail = self._create_category_header(
            tr("about.tools_section.available.title"),
            tr("about.tools_section.available.subtitle"),
            colors_avail["accent"],
        )
        layout.addWidget(header_avail)

        grid_avail = QGridLayout()
        grid_avail.setSpacing(DesignSystem.SPACE_8)
        grid_avail.setColumnStretch(0, 1)
        grid_avail.setColumnStretch(1, 1)

        available_tools = [
            (
                "compress",
                tr("about.tools_section.tools.optimizer.title"),
                tr("about.tools_section.tools.optimizer.description"),
            ),
            (
                "merge",
                tr("about.tools_section.tools.merge.title"),
                tr("about.tools_section.tools.merge.description"),
            ),
            (
                "tag",
                tr("tool_card.metadata.title"),
                tr("tool_card.metadata.description"),
            ),
            (
                "unlock",
                tr("tool_card.unlock.title"),
                tr("tool_card.unlock.description"),
            ),
        ]

        for i, (icon_name, tool_title, tool_desc) in enumerate(
            available_tools
        ):
            card = self._create_tool_mini_card(
                icon_name,
                tool_title,
                tool_desc,
                colors_avail["bg"],
                colors_avail["border"],
                colors_avail["icon"],
            )
            grid_avail.addWidget(card, i // 2, i % 2)

        if len(available_tools) % 2 != 0:
            spacer = QWidget()
            spacer.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            grid_avail.addWidget(spacer, len(available_tools) // 2, 1)

        layout.addLayout(grid_avail)

        # === UPCOMING TOOLS ===
        colors_upcoming = _CATEGORY_COLORS["upcoming"]
        header_upcoming = self._create_category_header(
            tr("about.tools_section.upcoming.title"),
            tr("about.tools_section.upcoming.subtitle"),
            colors_upcoming["accent"],
        )
        layout.addWidget(header_upcoming)

        grid_upcoming = QGridLayout()
        grid_upcoming.setSpacing(DesignSystem.SPACE_8)
        grid_upcoming.setColumnStretch(0, 1)
        grid_upcoming.setColumnStretch(1, 1)

        upcoming_tools = [
            (
                "scissors",
                tr("about.tools_section.tools.split.title"),
                tr("about.tools_section.tools.split.description"),
            ),
            (
                "counter",
                tr("about.tools_section.tools.numberer.title"),
                tr("about.tools_section.tools.numberer.description"),
            ),
        ]

        for i, (icon_name, tool_title, tool_desc) in enumerate(
            upcoming_tools
        ):
            card = self._create_tool_mini_card(
                icon_name,
                tool_title,
                tool_desc,
                colors_upcoming["bg"],
                colors_upcoming["border"],
                colors_upcoming["icon"],
            )
            grid_upcoming.addWidget(card, i // 2, i % 2)

        if len(upcoming_tools) % 2 != 0:
            spacer = QWidget()
            spacer.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            grid_upcoming.addWidget(spacer, len(upcoming_tools) // 2, 1)

        layout.addLayout(grid_upcoming)

        # Navigation
        nav_widget = self._create_tab_navigation(
            prev_tab=0,
            prev_label=tr("about.nav.home"),
            next_tab=2,
            next_label=tr("about.nav.view_info"),
        )
        layout.addWidget(nav_widget)

        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== INFO / TECH TAB ====================

    def _create_tech_tab(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
            DesignSystem.SPACE_24, DesignSystem.SPACE_16,
        )
        layout.setSpacing(DesignSystem.SPACE_16)

        # Title
        title = QLabel(tr("about.info.title"))
        title.setStyleSheet(
            DesignSystem.get_tutorial_section_header_style()
        )
        title.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(title)

        # Developer hero
        dev_hero = self._create_developer_hero()
        layout.addWidget(dev_hero)

        # Info row: App Info + Formats
        info_row = QWidget()
        info_row_layout = QHBoxLayout(info_row)
        info_row_layout.setContentsMargins(0, 0, 0, 0)
        info_row_layout.setSpacing(DesignSystem.SPACE_12)

        app_card = self._create_info_card(
            tr("about.info.app_card.title"),
            [
                (tr("about.info.app_card.name"), APP_NAME),
                (
                    tr("about.info.app_card.version"),
                    _get_full_version(),
                ),
                (
                    tr("about.info.app_card.platforms"),
                    tr("about.info.app_card.platforms_value"),
                ),
            ],
        )
        info_row_layout.addWidget(app_card, 1)

        formats_card = self._create_formats_card()
        info_row_layout.addWidget(formats_card, 1)

        layout.addWidget(info_row)

        # Values footer
        values_footer = self._create_values_footer()
        layout.addWidget(values_footer)

        # Trust footer
        trust_footer = QLabel(tr("about.dev.trust_footer"))
        trust_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        trust_footer.setStyleSheet(f"""
            color: {DesignSystem.COLOR_SUCCESS};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
            margin-bottom: {DesignSystem.SPACE_8}px;
        """)
        trust_footer.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(trust_footer)

        # License section
        license_container = QWidget()
        license_layout = QVBoxLayout(license_container)
        license_layout.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        license_layout.setSpacing(DesignSystem.SPACE_6)

        license_title = QLabel(tr("about.info.license.title"))
        license_title.setStyleSheet(f"""
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            text-transform: uppercase;
        """)
        license_layout.addWidget(license_title)

        try:
            license_path = (
                Path(__file__).resolve().parent.parent.parent / "LICENSE"
            )
            with open(license_path, "r", encoding="utf-8") as f:
                license_text = f.read()
        except Exception:
            license_text = tr("common.unknown")

        license_edit = QTextEdit()
        license_edit.setReadOnly(True)
        license_edit.setPlainText(license_text)
        license_edit.setMaximumHeight(120)
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
        license_layout.addWidget(license_edit)
        layout.addWidget(license_container)

        # Navigation
        nav_widget = self._create_tab_navigation(
            prev_tab=1, prev_label=tr("about.nav.view_tools")
        )
        layout.addWidget(nav_widget)

        layout.addStretch()
        return self._create_scroll_content(container)

    # ==================== DEVELOPER HERO ====================

    def _create_developer_hero(self) -> QFrame:
        outer_frame = QFrame()
        outer_frame.setStyleSheet(
            "background: transparent; border: none;"
        )

        outer_layout = QHBoxLayout(outer_frame)
        outer_layout.setSpacing(DesignSystem.SPACE_24)
        outer_layout.setContentsMargins(
            DesignSystem.SPACE_4, DesignSystem.SPACE_12,
            DesignSystem.SPACE_4, DesignSystem.SPACE_12,
        )

        # Left side: developed by
        dev_info_layout = QVBoxLayout()
        dev_info_layout.setSpacing(DesignSystem.SPACE_2)

        developed_by_label = QLabel(
            tr("about.info.app_card.developed_by")
        )
        developed_by_label.setStyleSheet(f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        dev_info_layout.addWidget(developed_by_label)

        org_link_name = QLabel(
            f'<a href="{APP_WEBSITE}" style="text-decoration: none;'
            f' color: {DesignSystem.COLOR_PRIMARY};">safetoolhub.org</a>'
        )
        org_link_name.setStyleSheet(f"""
            font-size: 36px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        org_link_name.setOpenExternalLinks(True)
        org_link_name.setCursor(Qt.CursorShape.PointingHandCursor)
        dev_info_layout.addWidget(org_link_name)

        tagline = QLabel(tr("about.dev.tagline"))
        tagline.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT};"
            f" font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
        )
        dev_info_layout.addWidget(tagline)

        outer_layout.addLayout(dev_info_layout)
        outer_layout.addStretch()

        # Right side: contact
        contact_card = QWidget()
        contact_card.setStyleSheet(
            "background: transparent; border: none;"
        )
        contact_layout = QVBoxLayout(contact_card)
        contact_layout.setContentsMargins(0, 0, 0, 0)
        contact_layout.setSpacing(0)

        contact_title = QLabel(tr("about.info.contact.title"))
        contact_title.setStyleSheet(
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f" color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" text-transform: uppercase; margin-bottom: -2px;"
        )
        contact_layout.addWidget(
            contact_title,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )

        email_link = (
            f'<a href="mailto:{APP_CONTACT}"'
            f' style="color: {DesignSystem.COLOR_PRIMARY};'
            f' text-decoration: none;">{APP_CONTACT}</a>'
        )
        email_label = QLabel(email_link)
        email_label.setOpenExternalLinks(True)
        email_label.setStyleSheet(
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
        )
        email_label.setCursor(Qt.CursorShape.PointingHandCursor)
        contact_layout.addWidget(
            email_label,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
        )

        outer_layout.addWidget(
            contact_card, 0, Qt.AlignmentFlag.AlignVCenter
        )

        return outer_frame

    # ==================== VALUES FOOTER ====================

    def _create_values_footer(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")

        layout = QHBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_24)
        layout.setContentsMargins(
            0, DesignSystem.SPACE_16, 0, DesignSystem.SPACE_8
        )
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_items = [
            (
                "wifi-off",
                tr("about.dev.values.offline.title"),
                tr("about.dev.values.offline.description"),
            ),
            (
                "eye-off",
                tr("about.dev.values.no_tracking.title"),
                tr("about.dev.values.no_tracking.description"),
            ),
            (
                "shield",
                tr("about.dev.values.open_source.title"),
                tr("about.dev.values.open_source.description"),
            ),
        ]

        for icon_name, val_title, val_desc in value_items:
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(DesignSystem.SPACE_12)

            icon_label = QLabel()
            icon_manager.set_label_icon(
                icon_label, icon_name,
                color=DesignSystem.COLOR_PRIMARY, size=24,
            )
            item_layout.addWidget(
                icon_label, 0, Qt.AlignmentFlag.AlignVCenter
            )

            text_layout = QVBoxLayout()
            text_layout.setSpacing(0)
            text_layout.setContentsMargins(0, 0, 0, 0)

            title_label = QLabel(val_title)
            title_label.setStyleSheet(
                f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
                f" color: {DesignSystem.COLOR_TEXT};"
                f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
                f" line-height: 100%;"
            )
            text_layout.addWidget(title_label)

            desc_label = QLabel(val_desc)
            desc_label.setStyleSheet(
                f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
                f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
                f" line-height: 100%;"
            )
            text_layout.addWidget(desc_label)

            item_layout.addLayout(text_layout)
            layout.addWidget(item_widget)

        return frame

    # ==================== NAVIGATION WIDGET ====================

    def _create_tab_navigation(
        self,
        prev_tab: int | None = None,
        prev_label: str | None = None,
        next_tab: int | None = None,
        next_label: str | None = None,
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: none;
                margin-top: {DesignSystem.SPACE_16}px;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, DesignSystem.SPACE_12, 0, 0)
        layout.setSpacing(DesignSystem.SPACE_8)

        if prev_tab is not None and prev_label:
            prev_btn = QPushButton(f"< {prev_label}")
            prev_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {DesignSystem.COLOR_PRIMARY};
                    border: 1px solid {DesignSystem.COLOR_BORDER};
                    border-radius: {DesignSystem.RADIUS_MD}px;
                    padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                    border-color: {DesignSystem.COLOR_PRIMARY};
                }}
            """)
            prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            prev_btn.clicked.connect(
                lambda checked=False, t=prev_tab: self.tab_widget.setCurrentIndex(t)
            )
            layout.addWidget(prev_btn)

        layout.addStretch()

        if next_tab is not None and next_label:
            next_btn = QPushButton(f"{next_label} >")
            next_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {DesignSystem.COLOR_PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {DesignSystem.RADIUS_MD}px;
                    padding: {DesignSystem.SPACE_6}px {DesignSystem.SPACE_16}px;
                    font-size: {DesignSystem.FONT_SIZE_SM}px;
                    font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {DesignSystem.COLOR_PRIMARY_HOVER};
                }}
            """)
            next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            next_btn.clicked.connect(
                lambda checked=False, t=next_tab: self.tab_widget.setCurrentIndex(t)
            )
            layout.addWidget(next_btn)

        return frame

    # ==================== AUXILIARY WIDGETS ====================

    def _create_category_header(
        self, title: str, subtitle: str, accent_color: str
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            DesignSystem.get_about_category_header_style(accent_color)
        )

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, DesignSystem.SPACE_2)
        layout.setSpacing(DesignSystem.SPACE_8)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {accent_color};
            font-size: {DesignSystem.FONT_SIZE_BASE}px;
            font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
        """)
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(title_label)

        subtitle_label = QLabel(f"\u2014 {subtitle}")
        subtitle_label.setStyleSheet(
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f" font-size: {DesignSystem.FONT_SIZE_SM}px;"
        )
        subtitle_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(subtitle_label)
        layout.addStretch()

        return frame

    def _create_tool_mini_card(
        self,
        icon_name: str,
        title: str,
        description: str,
        bg_color: str,
        border_color: str,
        icon_color: str,
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            DesignSystem.get_about_tool_card_category_style(
                bg_color, border_color
            )
        )
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout = QHBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_10)
        layout.setContentsMargins(
            DesignSystem.SPACE_12, DesignSystem.SPACE_8,
            DesignSystem.SPACE_12, DesignSystem.SPACE_8,
        )

        icon_label = QLabel()
        icon_manager.set_label_icon(
            icon_label, icon_name, color=icon_color, size=20
        )
        icon_label.setFixedSize(24, 24)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        content = QVBoxLayout()
        content.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            DesignSystem.get_tutorial_card_title_style()
        )
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        content.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(
            DesignSystem.get_tutorial_card_desc_style()
        )
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        content.addWidget(desc_label)

        layout.addLayout(content, 1)
        return frame

    def _create_step_widget_compact(
        self, number: str, title: str, description: str
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_step_card_style())

        layout = QHBoxLayout(frame)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 10, 12, 10)

        num_label = QLabel(number)
        num_label.setFixedSize(24, 24)
        num_label.setStyleSheet(
            DesignSystem.get_tutorial_step_number_style()
        )
        num_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(num_label)

        content = QVBoxLayout()
        content.setSpacing(DesignSystem.SPACE_2)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            DesignSystem.get_tutorial_card_title_style()
        )
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        content.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(
            DesignSystem.get_tutorial_card_desc_style()
        )
        desc_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        content.addWidget(desc_label)

        layout.addLayout(content, 1)
        return frame

    def _create_mini_tip(self, title: str, desc: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_tutorial_tip_card_style())

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        header = QLabel(title)
        header.setStyleSheet(DesignSystem.get_tutorial_card_title_style())
        header.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(header)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(
            DesignSystem.get_tutorial_card_desc_style()
        )
        desc_label.setWordWrap(True)
        desc_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(desc_label)

        return frame

    def _create_info_card(
        self, title: str, items: list[tuple[str, str]]
    ) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_info_card_style())

        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_2)
        layout.setContentsMargins(
            DesignSystem.SPACE_10, DesignSystem.SPACE_8,
            DesignSystem.SPACE_10, DesignSystem.SPACE_8,
        )

        title_label = QLabel(title)
        title_label.setStyleSheet(
            DesignSystem.get_tutorial_card_title_style()
        )
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(title_label)

        for label, value in items:
            row = QHBoxLayout()
            row.setSpacing(6)

            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(DesignSystem.get_about_info_label_style())
            lbl.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
            row.addWidget(lbl)

            val = QLabel(value)
            val.setStyleSheet(DesignSystem.get_about_info_value_style())
            val.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
            row.addWidget(val)
            row.addStretch()

            layout.addLayout(row)

        return frame

    def _create_formats_card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(DesignSystem.get_about_info_card_style())

        layout = QVBoxLayout(frame)
        layout.setSpacing(DesignSystem.SPACE_2)
        layout.setContentsMargins(
            DesignSystem.SPACE_10, DesignSystem.SPACE_8,
            DesignSystem.SPACE_10, DesignSystem.SPACE_8,
        )

        title_label = QLabel(tr("about.info.formats.title"))
        title_label.setStyleSheet(
            DesignSystem.get_tutorial_card_title_style()
        )
        title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        layout.addWidget(title_label)

        formats = [
            (
                "file-pdf",
                tr("about.info.formats.input"),
                "PDF",
            ),
            (
                "file-export",
                tr("about.info.formats.output"),
                tr("about.info.formats.output_value"),
            ),
        ]

        for icon_name, fmt_title, fmt_list in formats:
            row = QHBoxLayout()
            row.setSpacing(6)

            icon_label = QLabel()
            icon_manager.set_label_icon(
                icon_label, icon_name,
                color=DesignSystem.COLOR_PRIMARY, size=14,
            )
            row.addWidget(icon_label)

            text = QLabel(f"<b>{fmt_title}:</b> {fmt_list}")
            text.setStyleSheet(
                DesignSystem.get_about_formats_text_style()
            )
            text.setWordWrap(True)
            text.setTextInteractionFlags(
                Qt.TextInteractionFlag.NoTextInteraction
            )
            row.addWidget(text, 1)

            layout.addLayout(row)

        return frame

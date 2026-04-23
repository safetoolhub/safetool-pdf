# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Tool cards for the file selection screen (Optimize, Combine, etc.).

Completely redesigned to be elegant, professional, and visually appealing.
Includes icon containers, refined typography, and smooth interaction states.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from safetool_pdf_desktop.styles.design_system import DesignSystem
from safetool_pdf_desktop.styles.icons import icon_manager
from i18n import tr
import config


class BaseToolCard(QFrame):
    """Modern, premium tool card with icon box, title, description, and CTA."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        description: str,
        action_text: str,
        badge_text: str = "",
        enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_text = title
        self._desc_text = description
        self._action_text = action_text
        self._is_enabled = enabled
        self._badge_text = badge_text
        self._config_enabled = enabled  # Store the config-level enabled state

        # Container styling
        self.setObjectName("toolCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setLineWidth(0)
        self.setMaximumWidth(400)
        self.setMinimumHeight(240)
        
        # Main Layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Inner Content Frame (for better border/hover handling)
        self._inner = QFrame()
        self._inner.setObjectName("toolCardInner")
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(
            DesignSystem.SPACE_24, DesignSystem.SPACE_24,
            DesignSystem.SPACE_24, DesignSystem.SPACE_24,
        )
        self._inner_layout.setSpacing(DesignSystem.SPACE_16)
        
        self._main_layout.addWidget(self._inner)

        # Setup Shadow
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(6)
        self._shadow.setColor(QColor(0, 0, 0, 0)) # Start transparent
        self.setGraphicsEffect(self._shadow)

        # Shadow Animation
        self._shadow_anim = QPropertyAnimation(self._shadow, b"color")
        self._shadow_anim.setDuration(250)
        self._shadow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._build_ui()
        self.set_enabled(enabled)

    def _build_ui(self) -> None:
        # ── Header Area (Badge only) ──
        if self._badge_text:
            header_row = QHBoxLayout()
            header_row.setContentsMargins(0, 0, 0, 0)
            header_row.addStretch()
            
            self._badge_label = QLabel(self._badge_text)
            self._badge_label.setStyleSheet(DesignSystem.get_tool_card_badge_style())
            header_row.addWidget(self._badge_label, 0, Qt.AlignmentFlag.AlignTop)
            self._inner_layout.addLayout(header_row)
        else:
            # Add some top spacing if no badge is present to balance the layout
            self._inner_layout.addSpacing(DesignSystem.SPACE_8)

        # ── Title & Description ──
        text_container = QVBoxLayout()
        text_container.setSpacing(DesignSystem.SPACE_4)
        
        self._title_label = QLabel(self._title_text)
        self._title_label.setStyleSheet(DesignSystem.get_tool_card_title_style(self._is_enabled))
        text_container.addWidget(self._title_label)

        self._desc_label = QLabel(self._desc_text)
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(DesignSystem.get_tool_card_desc_style(self._is_enabled))
        text_container.addWidget(self._desc_label)
        
        self._inner_layout.addLayout(text_container)
        
        self._inner_layout.addStretch()

        # ── Action Area ──
        self._action_btn = QPushButton(f"  {self._action_text}")
        self._action_btn.setMinimumHeight(42)
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Connect the button click to the card's clicked signal
        self._action_btn.clicked.connect(self.clicked.emit)
        self._inner_layout.addWidget(self._action_btn)

    # ── Interaction & Hover ──

    def enterEvent(self, event) -> None:  # noqa: N802
        if not self._is_enabled:
            return
        
        # Animate shadow color
        self._shadow_anim.stop()
        self._shadow_anim.setEndValue(QColor(0, 0, 0, 30))
        self._shadow_anim.start()
        
        # Manual state update for stylesheet (handled by :hover on toolCardInner)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if not self._is_enabled:
            return
            
        self._shadow_anim.stop()
        self._shadow_anim.setEndValue(QColor(0, 0, 0, 0))
        self._shadow_anim.start()
        
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._is_enabled and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    # ── Public API ──

    def set_enabled(self, enabled: bool) -> None:
        """Update card state and visual styles.
        
        Note: This respects the config-level enabled state. If the card is
        disabled in config, it will remain disabled regardless of this call.
        """
        # Only enable if BOTH config allows it AND the parameter is True
        actual_enabled = self._config_enabled and enabled
        self._is_enabled = actual_enabled
        
        # Update tooltip for disabled cards
        if not self._config_enabled:
            self.setToolTip(tr("tool_card.disabled_tooltip"))
        else:
            self.setToolTip("")
        
        # Update Container Style
        self.setStyleSheet(DesignSystem.get_tool_card_style(enabled=actual_enabled))
        
        # Update Text Styles
        self._title_label.setStyleSheet(DesignSystem.get_tool_card_title_style(actual_enabled))
        self._desc_label.setStyleSheet(DesignSystem.get_tool_card_desc_style(actual_enabled))
        
        # Update Button
        self._action_btn.setEnabled(actual_enabled)
        if actual_enabled:
            self._action_btn.setStyleSheet(DesignSystem.get_primary_button_style())
            icon_manager.set_button_icon(self._action_btn, "arrow-right", color="white", size=18)
        else:
            self._action_btn.setStyleSheet(DesignSystem.get_secondary_button_style())
            icon_manager.set_button_icon(self._action_btn, "lock", color=DesignSystem.COLOR_TEXT_SECONDARY, size=18)

        # Update Cursor
        self.setCursor(QCursor(
            Qt.CursorShape.PointingHandCursor if actual_enabled 
            else Qt.CursorShape.ArrowCursor
        ))


class OptimizeToolCard(BaseToolCard):
    """Tool card for the Optimize function."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title=tr("tool_card.optimize.title"),
            description=tr("tool_card.optimize.description"),
            action_text=tr("tool_card.optimize.action"),
            enabled=config.TOOL_OPTIMIZE_ENABLED,
            parent=parent,
        )


class CombineToolCard(BaseToolCard):
    """Tool card for the Combine / Merge function."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title=tr("tool_card.combine.title"),
            description=tr("tool_card.combine.description"),
            action_text=tr("tool_card.combine.action"),
            enabled=config.TOOL_COMBINE_ENABLED,
            parent=parent,
        )


class NumberingToolCard(BaseToolCard):
    """Tool card for the Numbering function."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title=tr("tool_card.number.title"),
            description=tr("tool_card.number.description"),
            action_text=tr("tool_card.number.action"),
            enabled=config.TOOL_NUMBERING_ENABLED,
            parent=parent,
        )


class MetadataToolCard(BaseToolCard):
    """Tool card for the Remove Metadata function."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title=tr("tool_card.metadata.title"),
            description=tr("tool_card.metadata.description"),
            action_text=tr("tool_card.metadata.action"),
            enabled=config.TOOL_METADATA_ENABLED,
            parent=parent,
        )


class UnlockToolCard(BaseToolCard):
    """Tool card for the Remove Password function."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title=tr("tool_card.unlock.title"),
            description=tr("tool_card.unlock.description"),
            action_text=tr("tool_card.unlock.action"),
            enabled=config.TOOL_UNLOCK_ENABLED,
            parent=parent,
        )

# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Icon Manager — Centralized icon management with QtAwesome.

Provides a unified interface for Material Design icons in SafeTool PDF Desktop.

Usage:
    from safetool_pdf_desktop.styles.icons import icon_manager

    icon_manager.set_button_icon(button, 'cog', color='#2563eb', size=20)
    icon_manager.set_label_icon(label, 'file-pdf', size=16)
    icon = icon_manager.get_icon('folder', color='#2563eb')
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import qtawesome as qta
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QToolButton

class IconManager:
    """Centralized icon manager using QtAwesome MDI6 icons."""

    # Mapping of semantic names to qtawesome icon names (mdi6 = Material Design Icons)
    ICON_MAP = {
        # Core
        "file-pdf": "mdi6.file-pdf-box",
        "file-document": "mdi6.file-document-outline",
        "folder-open": "mdi6.folder-open-outline",
        "cog": "mdi6.cog-outline",
        "information": "mdi6.information-outline",
        "information-outline": "mdi6.information-outline",
        "ghost": "mdi6.ghost",
        "arrow-left": "mdi6.arrow-left",
        "arrow-right": "mdi6.arrow-right",
        "close-circle": "mdi6.close-circle-outline",
        "check-circle": "mdi6.check-circle-outline",

        # Strategy / Optimization
        "shield-check": "mdi6.shield-check-outline",
        "scale-balance": "mdi6.scale-balance",
        "rocket-launch": "mdi6.rocket-launch-outline",
        "tune": "mdi6.tune",
        "magnify": "mdi6.magnify",
        "compress": "mdi6.file-find-outline",  # used as "Optimize" card icon

        # Strategy Panel Elements
        "image": "mdi6.image-outline",
        "broom": "mdi6.broom",
        "eye": "mdi6.eye-outline",
        "eye-off": "mdi6.eye-off-outline",
        "check-bold": "mdi6.check-bold",
        "chevron-down": "mdi6.chevron-down",
        "chevron-up": "mdi6.chevron-up",
        "select-all": "mdi6.select-all",
        "grip-vertical": "mdi6.drag-vertical",

        # Actions
        "restart": "mdi6.restart",
        "file-export": "mdi6.file-export-outline",
        "file-multiple": "mdi6.file-multiple-outline",
        "file-edit": "mdi6.file-edit-outline",

        # Security
        "lock": "mdi6.lock",
        "shield-lock": "mdi6.shield-lock-outline",
        "shield-lock-outline": "mdi6.shield-lock-outline",
        "unlock": "mdi6.lock-open-variant-outline",
        "plus": "mdi6.plus",

        # About / Tutorial
        "settings": "mdi6.cog-outline",
        "wifi-off": "mdi6.wifi-off",
        "shield": "mdi6.shield-outline",
        "merge": "mdi6.file-document-multiple-outline",
        "counter": "mdi6.counter",
        "scissors": "mdi6.content-cut",
        "tag": "mdi6.tag-outline",
        "video": "mdi6.video-outline",

        # Multi-tool extras
        "tools": "mdi6.tools",
        "numeric": "mdi6.numeric",
        "shield-remove": "mdi6.shield-remove-outline",
        "lock-open-variant": "mdi6.lock-open-variant-outline",
        "progress-clock": "mdi6.progress-clock",
        "translate": "mdi6.translate",
        "bug": "mdi6.bug-outline",
        
        # Permissions
        "printer": "mdi6.printer-outline",
        "printer-check": "mdi6.printer-check",
        "printer-check-outline": "mdi6.printer-check-outline",
        "human": "mdi6.human",
        "comment-edit": "mdi6.comment-edit",
        "form-textbox": "mdi6.form-textbox",
    }

    def __init__(self) -> None:
        self._cache: Dict[str, QIcon] = {}

    def get_icon(
        self,
        name: str,
        color: Optional[str] = None,
        size: Optional[int] = None,
        scale_factor: float = 1.0,
    ) -> QIcon:
        """Get a Material Design icon by logical name."""
        if name not in self.ICON_MAP:
            raise ValueError(
                f"Icon '{name}' not found. "
                f"Available: {', '.join(sorted(self.ICON_MAP.keys()))}"
            )

        cache_key = f"{name}_{color}_{size}_{scale_factor}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        icon_name = self.ICON_MAP[name]
        options: Dict[str, Any] = {}
        if color:
            options['color'] = color
        if scale_factor != 1.0:
            options['scale_factor'] = scale_factor

        icon = qta.icon(icon_name, **options)
        self._cache[cache_key] = icon
        return icon

    def set_button_icon(
        self,
        button: QPushButton | QToolButton,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16,
    ) -> None:
        """Apply icon to a QPushButton or QToolButton."""
        icon = self.get_icon(icon_name, color=color)
        button.setIcon(icon)
        button.setIconSize(QSize(size, size))

    def set_label_icon(
        self,
        label: QLabel,
        icon_name: str,
        color: Optional[str] = None,
        size: int = 16,
    ) -> None:
        """Apply icon to a QLabel via pixmap."""
        icon = self.get_icon(icon_name, color=color)

        try:
            screen = label.screen() if hasattr(label, 'screen') else QGuiApplication.primaryScreen()
            dpr = float(screen.devicePixelRatio()) if screen is not None else 1.0
        except Exception:
            dpr = 1.0

        physical_size = QSize(max(1, int(size * dpr)), max(1, int(size * dpr)))
        pixmap = icon.pixmap(physical_size)

        if pixmap.isNull():
            pixmap = icon.pixmap(QSize(size, size))

        if not pixmap.isNull():
            try:
                logical_pixmap = pixmap.scaled(
                    QSize(size, size),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logical_pixmap.setDevicePixelRatio(1.0)
                label.setPixmap(logical_pixmap)
            except Exception:
                label.setPixmap(pixmap)
        else:
            # Fallback for null pixmap
            fallback = QPixmap(QSize(size, size))
            fallback.fill(QColor(0, 0, 0, 0))
            label.setPixmap(fallback)

# Global instance
icon_manager = IconManager()

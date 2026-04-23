# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Design System for SafeTool PDF Desktop.

Centralized design system providing consistent CSS tokens and reusable
style methods. Adapted from innerpix-lab design system for PySide6.
"""

from __future__ import annotations

class DesignSystem:
    """Centralized design system with reusable tokens and styles."""

    # ==================== COLORS ====================

    COLOR_BACKGROUND = "#F8F9FA"
    COLOR_SURFACE = "#FFFFFF"
    COLOR_TEXT = "#212529"
    COLOR_TEXT_SECONDARY = "#6C757D"
    COLOR_PRIMARY = "#0D6EFD"
    COLOR_PRIMARY_HOVER = "#0B5ED7"
    COLOR_PRIMARY_ACTIVE = "#0A58CA"
    COLOR_PRIMARY_LIGHT = "#E7F1FF"
    COLOR_PRIMARY_SUBTLE = "rgba(13, 110, 253, 0.04)"
    COLOR_PRIMARY_LIGHTER = "rgba(13, 110, 253, 0.08)"
    COLOR_TRANS_SURFACE = "rgba(255, 255, 255, 0.85)"
    COLOR_SHADOW = "rgba(0, 0, 0, 0.1)"
    COLOR_PRIMARY_TEXT = "#FFFFFF"
    COLOR_SECONDARY = "#6C757D"
    COLOR_SECONDARY_HOVER = "#5C636A"
    COLOR_SECONDARY_LIGHT = "#E9ECEF"
    COLOR_SUCCESS = "#198754"
    COLOR_SUCCESS_BG = "#D1E7DD"
    COLOR_SUCCESS_SOFT_BG = "#E6F4EA"
    COLOR_WARNING = "#FFC107"
    COLOR_WARNING_BG = "#FFF3CD"
    COLOR_WARNING_TEXT = "#664D03"
    COLOR_DANGER = "#DC3545"
    COLOR_DANGER_HOVER = "#BB2D3B"
    COLOR_DANGER_BG = "#F8D7DA"
    COLOR_INFO = "#0DCAF0"
    COLOR_INFO_BG = "#CFF4FC"
    COLOR_INFO_TEXT = "#055160"
    COLOR_BORDER = "#DEE2E6"
    COLOR_BORDER_LIGHT = "#E9ECEF"
    COLOR_CARD_BORDER = "#DEE2E6"

    # ==================== TYPOGRAPHY ====================

    FONT_FAMILY_BASE = "'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif"
    FONT_FAMILY_MONO = "'Consolas', 'Monaco', monospace"
    FONT_SIZE_XS = 11
    FONT_SIZE_SM = 13
    FONT_SIZE_BASE = 14
    FONT_SIZE_MD = 16
    FONT_SIZE_LG = 18
    FONT_SIZE_XL = 24
    FONT_SIZE_2XL = 32
    FONT_WEIGHT_NORMAL = 400
    FONT_WEIGHT_MEDIUM = 500
    FONT_WEIGHT_SEMIBOLD = 600
    FONT_WEIGHT_BOLD = 700

    # ==================== SPACING ====================

    SPACE_2 = 2
    SPACE_4 = 4
    SPACE_6 = 6
    SPACE_8 = 8
    SPACE_10 = 10
    SPACE_12 = 12
    SPACE_16 = 16
    SPACE_20 = 20
    SPACE_24 = 24
    SPACE_32 = 32
    SPACE_40 = 40
    SPACE_48 = 48

    # ==================== BORDER RADIUS ====================

    RADIUS_SM = 4
    RADIUS_BASE = 6
    RADIUS_MD = 8
    RADIUS_LG = 12
    RADIUS_XL = 16
    RADIUS_FULL = 9999

    # ==================== DIMENSIONS ====================

    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    HEADER_HEIGHT = 50

    # ==================== HELPERS ====================

    @staticmethod
    def _get_button_disabled_style() -> str:
        return f"""
            QPushButton:disabled {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: 1px solid {DesignSystem.COLOR_BORDER};
            }}
        """

    # ==================== GLOBAL STYLESHEET ====================

    @staticmethod
    def get_stylesheet() -> str:
        return f"""
            * {{ font-family: {DesignSystem.FONT_FAMILY_BASE}; }}
            QMainWindow {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}
            QWidget {{ color: {DesignSystem.COLOR_TEXT}; }}
            QToolTip {{
                background-color: #2D3436; color: #F5F6FA; border: none;
                border-radius: {DesignSystem.RADIUS_SM}px; padding: 4px 8px;
            }}
        """

    # ==================== HEADER ====================

    @staticmethod
    def get_header_style() -> str:
        return f"""
            QFrame#headerCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {DesignSystem.COLOR_SURFACE},
                    stop:1 {DesignSystem.COLOR_BACKGROUND});
                border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
                border-radius: {DesignSystem.RADIUS_LG}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
            }}
        """

    @staticmethod
    def get_header_title_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_XL}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT};"

    @staticmethod
    def get_header_icon_container_style() -> str:
        return f"background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; border-radius: {DesignSystem.RADIUS_MD}px; border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"

    @staticmethod
    def get_header_brand_label_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_XS}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_PRIMARY}; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent;"

    @staticmethod
    def get_card_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE}; border: 1px solid {DesignSystem.COLOR_CARD_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; padding: 16px; }}"

    # ==================== MAIN BUTTONS ====================

    @staticmethod
    def get_primary_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_PRIMARY}; color: {DesignSystem.COLOR_PRIMARY_TEXT};
                border: none; border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_HOVER}; }}
            QPushButton:pressed {{ background-color: {DesignSystem.COLOR_PRIMARY_ACTIVE}; }}
        """ + DesignSystem._get_button_disabled_style()

    @staticmethod
    def get_secondary_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {DesignSystem.COLOR_SURFACE}; color: {DesignSystem.COLOR_TEXT};
                border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_BASE}px;
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_24}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-height: 36px;
            }}
            QPushButton:hover {{ background-color: {DesignSystem.COLOR_SECONDARY_LIGHT}; border-color: {DesignSystem.COLOR_TEXT_SECONDARY}; }}
        """ + DesignSystem._get_button_disabled_style()

    # ==================== DROPZONE (Screen 1) ====================

    @staticmethod
    def get_dropzone_style(dragging: bool = False) -> str:
        if dragging:
            return f"QFrame {{ background-color: rgba(37, 99, 235, 0.15); border: 2px solid {DesignSystem.COLOR_PRIMARY}; border-radius: {DesignSystem.RADIUS_LG}px; }}"
        return f"QFrame {{ background-color: rgba(245, 245, 245, 0.8); border: 2px dashed {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; }} QFrame:hover {{ border: 2px dashed {DesignSystem.COLOR_PRIMARY}; background-color: rgba(37, 99, 235, 0.05); }}"

    @staticmethod
    def get_dropzone_text_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_LG}px; font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT}; background: transparent; border: none;"

    @staticmethod
    def get_dropzone_hint_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; background: transparent; border: none;"

    # ==================== TOOL CARDS (Screen 1) ====================

    @staticmethod
    def get_tool_card_style(enabled: bool = True, selected: bool = False) -> str:
        if not enabled:
            return f"""
                QFrame {{
                    background-color: {DesignSystem.COLOR_BACKGROUND};
                    border: 2px solid {DesignSystem.COLOR_BORDER_LIGHT};
                    border-radius: {DesignSystem.RADIUS_XL}px;
                }}
            """
        if selected:
            return f"""
                QFrame {{
                    background-color: {DesignSystem.COLOR_SURFACE};
                    border: 2px solid {DesignSystem.COLOR_PRIMARY};
                    border-radius: {DesignSystem.RADIUS_XL}px;
                }}
            """
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_SURFACE};
                border: 2px solid {DesignSystem.COLOR_BORDER};
                border-radius: {DesignSystem.RADIUS_XL}px;
            }}
            QFrame#toolCardInner:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY};
                background-color: {DesignSystem.COLOR_PRIMARY_SUBTLE};
            }}
        """

    @staticmethod
    def get_tool_card_title_style(enabled: bool = True) -> str:
        color = DesignSystem.COLOR_TEXT if enabled else DesignSystem.COLOR_TEXT_SECONDARY
        return f"font-size: {DesignSystem.FONT_SIZE_LG}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {color}; background: transparent; border: none;"

    @staticmethod
    def get_tool_card_desc_style(enabled: bool = True) -> str:
        color = DesignSystem.COLOR_TEXT_SECONDARY if enabled else "#A0AEC0"
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {color}; background: transparent; border: none;"

    # ==================== FILE LIST (Screen 1) ====================

    @staticmethod
    def get_file_list_container_style() -> str:
        return f"QScrollArea {{ border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_BASE}px; background-color: {DesignSystem.COLOR_SURFACE}; }}"

    @staticmethod
    def get_file_list_row_style(even: bool = True) -> str:
        bg = DesignSystem.COLOR_SURFACE if even else DesignSystem.COLOR_BACKGROUND
        return f"QFrame {{ background-color: {bg}; border: none; border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; padding: 6px 12px; }} QFrame:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; }}"

    @staticmethod
    def get_icon_button_style() -> str:
        return f"QToolButton {{ background: transparent; border: none; border-radius: {DesignSystem.RADIUS_BASE}px; padding: 4px; }} QToolButton:hover {{ background-color: rgba(0, 0, 0, 0.05); }} QToolButton:pressed {{ background-color: rgba(0, 0, 0, 0.1); }}"

    @staticmethod
    def get_tool_card_badge_style() -> str:
        return f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                border: none;
                border-radius: 10px;
                padding: 2px 10px;
                font-size: {DesignSystem.FONT_SIZE_XS}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
                text-transform: uppercase;
            }}
        """

    @staticmethod
    def get_tool_card_icon_box_style(enabled: bool = True) -> str:
        bg = DesignSystem.COLOR_PRIMARY_LIGHT if enabled else DesignSystem.COLOR_BORDER_LIGHT
        border = DesignSystem.COLOR_PRIMARY_LIGHTER if enabled else DesignSystem.COLOR_BORDER
        return f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {DesignSystem.RADIUS_MD}px;
                min-width: 48px;
                min-height: 48px;
                max-width: 48px;
                max-height: 48px;
            }}
        """

    @staticmethod
    def get_file_list_remove_button_style() -> str:
        return f"QToolButton {{ background: transparent; border: none; border-radius: {DesignSystem.RADIUS_SM}px; padding: 4px; }} QToolButton:hover {{ background-color: {DesignSystem.COLOR_DANGER_BG}; }}"

    @staticmethod
    def get_context_menu_style() -> str:
        return f"QMenu {{ background-color: {DesignSystem.COLOR_SURFACE}; border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_BASE}px; padding: 4px; font-size: {DesignSystem.FONT_SIZE_BASE}px; }} QMenu::item {{ background-color: transparent; color: {DesignSystem.COLOR_TEXT}; padding: 8px 16px; border-radius: {DesignSystem.RADIUS_SM}px; margin: 2px; }} QMenu::item:selected {{ background-color: {DesignSystem.COLOR_SECONDARY_LIGHT}; color: {DesignSystem.COLOR_TEXT}; }} QMenu::separator {{ height: 1px; background-color: {DesignSystem.COLOR_BORDER}; margin: 4px 8px; }}"

    @staticmethod
    def get_formats_hint_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none; background: transparent;"

    @staticmethod
    def get_separator_line_style() -> str:
        return f"color: {DesignSystem.COLOR_BORDER};"

    @staticmethod
    def get_table_summary_panel_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; border-top: 2px solid {DesignSystem.COLOR_PRIMARY}; border-bottom-left-radius: {DesignSystem.RADIUS_LG}px; border-bottom-right-radius: {DesignSystem.RADIUS_LG}px; }}"

    # ==================== STRATEGY SELECTION (Screen 2) ====================

    @staticmethod
    def get_strategy_selector_card_style(selected: bool = False) -> str:
        if selected:
            return f"QPushButton {{ background-color: {DesignSystem.COLOR_PRIMARY}; color: {DesignSystem.COLOR_PRIMARY_TEXT}; border: 1px solid {DesignSystem.COLOR_PRIMARY}; border-radius: {DesignSystem.RADIUS_MD}px; padding: 12px 20px; font-size: {DesignSystem.FONT_SIZE_BASE}px; font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; text-align: center; }} QPushButton:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_HOVER}; }}"
        return f"QPushButton {{ background-color: {DesignSystem.COLOR_SURFACE}; color: {DesignSystem.COLOR_TEXT}; border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_MD}px; padding: 12px 20px; font-size: {DesignSystem.FONT_SIZE_BASE}px; font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM}; text-align: center; }} QPushButton:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; border-color: {DesignSystem.COLOR_PRIMARY}; color: {DesignSystem.COLOR_PRIMARY}; }}"

    @staticmethod
    def get_strategy_header_text_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_LG}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"

    @staticmethod
    def get_strategy_info_text_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none; background: transparent;"

    @staticmethod
    def get_recommended_badge_style() -> str:
        return f"QLabel {{ background-color: {DesignSystem.COLOR_SUCCESS}; color: white; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; text-transform: uppercase; }}"

    # ==================== ESTIMATION TABLE (Screen 2) ====================

    @staticmethod
    def get_estimation_table_container_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE}; border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; }}"

    @staticmethod
    def get_file_table_header_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_BACKGROUND}; border-bottom: 2px solid {DesignSystem.COLOR_BORDER}; border-top-left-radius: {DesignSystem.RADIUS_LG}px; border-top-right-radius: {DesignSystem.RADIUS_LG}px; }}"

    @staticmethod
    def get_table_header_cell_style(is_active: bool = False) -> str:
        color = DesignSystem.COLOR_PRIMARY if is_active else DesignSystem.COLOR_TEXT_SECONDARY
        weight = DesignSystem.FONT_WEIGHT_BOLD if is_active else DesignSystem.FONT_WEIGHT_SEMIBOLD
        return f"font-size: {DesignSystem.FONT_SIZE_XS}px; font-weight: {weight}; color: {color}; text-transform: uppercase; letter-spacing: 0.5px; border: none; background: transparent;"

    @staticmethod
    def get_file_table_row_style(even: bool = True) -> str:
        bg = DesignSystem.COLOR_SURFACE if even else DesignSystem.COLOR_BACKGROUND
        return f"QFrame {{ background-color: {bg}; border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; }}"

    @staticmethod
    def get_file_table_row_optimized_style(even: bool = True) -> str:
        bg = "#f0fdf4" if even else "#ecfdf5"
        return f"QFrame {{ background-color: {bg}; border-bottom: 1px solid {DesignSystem.COLOR_SUCCESS}; }}"

    @staticmethod
    def get_table_row_text_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"

    @staticmethod
    def get_table_cell_btn_style(selected: bool = False, color: str = None, bold: bool = False) -> str:
        c = color or DesignSystem.COLOR_TEXT
        weight = DesignSystem.FONT_WEIGHT_BOLD if bold else DesignSystem.FONT_WEIGHT_MEDIUM
        if selected:
            return f"QPushButton {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; color: {c}; border: 1px solid {DesignSystem.COLOR_PRIMARY}; border-radius: {DesignSystem.RADIUS_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; padding: 4px; }} "
        return f"QPushButton {{ background-color: transparent; color: {c}; border: 1px transparent; border-radius: {DesignSystem.RADIUS_SM}px; font-weight: {weight}; padding: 4px; }} QPushButton:hover {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; }}"

    @staticmethod
    def get_summary_row_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; border-top: 2px solid {DesignSystem.COLOR_PRIMARY}; border-bottom-left-radius: {DesignSystem.RADIUS_LG}px; border-bottom-right-radius: {DesignSystem.RADIUS_LG}px; }}"

    @staticmethod
    def get_table_summary_label_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"

    @staticmethod
    def get_table_summary_value_style(color: str, is_active: bool) -> str:
        bg = f"background-color: {DesignSystem.COLOR_PRIMARY_LIGHT}; padding: 2px 4px; border-radius: 3px;" if is_active else ""
        return f"font-family: {DesignSystem.FONT_FAMILY_MONO}; font-size: {DesignSystem.FONT_SIZE_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {color}; border: none; {bg}"

    # ==================== CUSTOM PANEL (Screen 2) ====================

    @staticmethod
    def get_custom_panel_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE}; border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; margin: 8px 0px; }}"

    @staticmethod
    def get_custom_section_card_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_BACKGROUND}; border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; border-radius: {DesignSystem.RADIUS_MD}px; padding: 12px; }}"

    @staticmethod
    def get_custom_section_header_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_XS}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 0.8px; border: none; background: transparent;"

    @staticmethod
    def get_custom_panel_inner_style() -> str:
        """Style for the inner rows of the custom panel."""
        return f"background-color: {DesignSystem.COLOR_BACKGROUND}; border-radius: {DesignSystem.RADIUS_MD}px; padding: 10px; border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"

    # ==================== INFO ALERT ====================

    @staticmethod
    def get_info_alert_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_INFO_BG}; color: {DesignSystem.COLOR_INFO_TEXT}; border: 1px solid {DesignSystem.COLOR_INFO}; border-radius: {DesignSystem.RADIUS_MD}px; }} QLabel {{ font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_INFO_TEXT}; border: none; background: transparent; }}"

    @staticmethod
    def get_warning_alert_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_WARNING_BG}; color: {DesignSystem.COLOR_WARNING_TEXT}; border: 1px solid {DesignSystem.COLOR_WARNING}; border-radius: {DesignSystem.RADIUS_MD}px; }} QLabel {{ font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_WARNING_TEXT}; border: none; background: transparent; }}"

    @staticmethod
    def get_preview_icon_btn_style() -> str:
        """Subtle icon button for the preview magnifying glass."""
        return f"""
            QToolButton {{
                background: transparent; border: none;
                border-radius: {DesignSystem.RADIUS_SM}px; padding: 2px;
            }}
            QToolButton:hover {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
            QToolButton:pressed {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
            }}
        """

    @staticmethod
    def get_subtle_icon_label_style(color: str) -> str:
        """Small subtle icon container for settings rows."""
        return f"background-color: {color}15; border-radius: {DesignSystem.RADIUS_SM}px; border: 1px solid {color}30; padding: 2px;"

    @staticmethod
    def get_strategy_legend_card_style() -> str:
        """Card style for the always-visible strategy legend section."""
        return f"QFrame {{ background-color: {DesignSystem.COLOR_BACKGROUND}; border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT}; border-radius: {DesignSystem.RADIUS_MD}px; }}"

    @staticmethod
    def get_strategy_legend_item_style(color: str) -> str:
        """Individual strategy item inside the legend."""
        return f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE}; border: none; border-radius: {DesignSystem.RADIUS_LG}px; }}"

    @staticmethod
    def get_slider_style() -> str:
        return f"""
            QSlider::groove:horizontal {{
                border: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};
                height: 4px;
                background: {DesignSystem.COLOR_BORDER_LIGHT};
                margin: 2px 0;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {DesignSystem.COLOR_SURFACE};
                border: 2px solid {DesignSystem.COLOR_PRIMARY};
                width: 14px;
                height: 14px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                border-color: {DesignSystem.COLOR_PRIMARY_HOVER};
                background: {DesignSystem.COLOR_PRIMARY_LIGHT};
            }}
            QSlider::sub-page:horizontal {{
                background: {DesignSystem.COLOR_PRIMARY};
                border-radius: 2px;
            }}
        """

    @staticmethod
    def get_apply_all_combo_style() -> str:
        """ComboBox used as 'Apply to all' in table header."""
        return f"""
            QComboBox {{
                border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_SM}px;
                padding: 3px 8px; background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_XS}px;
                min-height: 24px; max-width: 150px;
            }}
            QComboBox:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{
                image: none; border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {DesignSystem.COLOR_TEXT_SECONDARY}; margin-right: 6px;
            }}
        """

    # ==================== TAB WIDGET ====================
    
    @staticmethod
    def get_tab_widget_style() -> str:
        return f"""
            QTabWidget::pane {{
                border: 1px solid {DesignSystem.COLOR_CARD_BORDER};
                border-radius: {DesignSystem.RADIUS_BASE}px;
                background-color: {DesignSystem.COLOR_SURFACE};
                padding: {DesignSystem.SPACE_16}px;
            }}

            QTabBar::tab {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_12}px {DesignSystem.SPACE_20}px;
                border: 1px solid {DesignSystem.COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: {DesignSystem.RADIUS_BASE}px;
                border-top-right-radius: {DesignSystem.RADIUS_BASE}px;
                margin-right: {DesignSystem.SPACE_4}px;
                font-size: {DesignSystem.FONT_SIZE_BASE}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-width: 100px;
                text-align: center;
            }}

            QTabBar::tab:selected {{
                background-color: {DesignSystem.COLOR_SURFACE};
                color: {DesignSystem.COLOR_PRIMARY};
                border-color: {DesignSystem.COLOR_CARD_BORDER};
                border-bottom-color: {DesignSystem.COLOR_SURFACE};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}

            QTabBar::tab:hover {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                color: {DesignSystem.COLOR_TEXT};
            }}

            QTabBar::tab:selected:hover {{
                background-color: {DesignSystem.COLOR_SURFACE};
            }}
        """

    # ==================== SETTINGS DIALOG ====================

    @staticmethod
    def get_settings_section_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE}; border: 1px solid {DesignSystem.COLOR_CARD_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; padding: 16px; }}"

    @staticmethod
    def get_settings_title_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_MD}px; font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"

    @staticmethod
    def get_settings_label_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_BASE}px; color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"

    @staticmethod
    def get_line_edit_style() -> str:
        return f"QLineEdit {{ border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_BASE}px; padding: 8px; font-size: {DesignSystem.FONT_SIZE_BASE}px; color: {DesignSystem.COLOR_TEXT}; background-color: {DesignSystem.COLOR_SURFACE}; }} QLineEdit:focus {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}"

    @staticmethod
    def get_combobox_style() -> str:
        return f"QComboBox {{ border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_BASE}px; padding: 6px 10px; background-color: {DesignSystem.COLOR_SURFACE}; color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px; min-height: 36px; }} QComboBox:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }} QComboBox::drop-down {{ border: none; width: 30px; }} QComboBox::down-arrow {{ image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 5px solid {DesignSystem.COLOR_TEXT_SECONDARY}; margin-right: 10px; }}"

    @staticmethod
    def get_spinbox_style() -> str:
        return f"QSpinBox {{ border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_BASE}px; padding: 6px 8px; background-color: {DesignSystem.COLOR_SURFACE}; color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_BASE}px; min-height: 36px; }} QSpinBox:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}"

    @staticmethod
    def get_checkbox_style() -> str:
        return f"QCheckBox {{ font-size: {DesignSystem.FONT_SIZE_BASE}px; color: {DesignSystem.COLOR_TEXT}; spacing: 8px; }} QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {DesignSystem.COLOR_BORDER}; border-radius: 4px; background-color: {DesignSystem.COLOR_SURFACE}; }} QCheckBox::indicator:checked {{ background-color: {DesignSystem.COLOR_PRIMARY}; border-color: {DesignSystem.COLOR_PRIMARY}; }} QCheckBox::indicator:hover {{ border-color: {DesignSystem.COLOR_PRIMARY}; }}"

    @staticmethod
    def get_header_text_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_XL}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_TEXT}; border: none; background: transparent;"

    @staticmethod
    def get_settings_note_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none; background: transparent;"

    @staticmethod
    def get_settings_preview_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_PRIMARY}; border: none; background: transparent; font-style: italic;"

    @staticmethod
    def get_settings_error_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; color: {DesignSystem.COLOR_DANGER}; border: none; background: transparent;"

    @staticmethod
    def get_settings_success_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_SUCCESS}; border: none; background: transparent;"

    @staticmethod
    def get_settings_danger_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {DesignSystem.COLOR_DANGER}; border: none; background: transparent;"

    # ==================== RESULTS SCREEN (Screen 3) ====================

    @staticmethod
    def get_results_header_style(is_warning: bool = False) -> str:
        color = DesignSystem.COLOR_WARNING if is_warning else DesignSystem.COLOR_SUCCESS
        return f"font-size: {DesignSystem.FONT_SIZE_XL}px; font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; color: {color}; border: none; background: transparent;"

    @staticmethod
    def get_results_summary_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_BASE}px; color: {DesignSystem.COLOR_TEXT_SECONDARY}; border: none; background: transparent;"

    @staticmethod
    def get_results_table_style() -> str:
        return f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE}; border: 1px solid {DesignSystem.COLOR_BORDER}; border-radius: {DesignSystem.RADIUS_LG}px; padding: 0px; }}"

    # ==================== MISC ====================

    @staticmethod
    def get_progressbar_style() -> str:
        return f"QProgressBar {{ border: none; border-radius: {DesignSystem.RADIUS_SM}px; background-color: {DesignSystem.COLOR_SECONDARY_LIGHT}; text-align: center; height: 6px; }} QProgressBar::chunk {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {DesignSystem.COLOR_PRIMARY}, stop:1 {DesignSystem.COLOR_PRIMARY_HOVER}); border-radius: {DesignSystem.RADIUS_SM}px; }}"

    @staticmethod
    def get_scroll_area_style() -> str:
        return f"QScrollArea {{ border: none; background-color: transparent; }} QScrollBar:vertical {{ border: none; background-color: {DesignSystem.COLOR_BACKGROUND}; width: 8px; border-radius: 4px; }} QScrollBar::handle:vertical {{ background-color: {DesignSystem.COLOR_BORDER}; border-radius: 4px; min-height: 30px; }} QScrollBar::handle:vertical:hover {{ background-color: {DesignSystem.COLOR_TEXT_SECONDARY}; }} QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"

    @staticmethod
    def get_separator_label_style() -> str:
        return f"font-size: {DesignSystem.FONT_SIZE_SM}px; font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD}; color: {DesignSystem.COLOR_TEXT_SECONDARY}; text-transform: uppercase; letter-spacing: 1px; border: none; background: transparent;"

    # ==================== DETAILS DIALOG ====================

    @staticmethod
    def get_details_dialog_style() -> str:
        return f"QDialog {{ background-color: {DesignSystem.COLOR_BACKGROUND}; }}"

    @staticmethod
    def get_details_header_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_SURFACE};"
            f" border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f" border-top-left-radius: {DesignSystem.RADIUS_LG}px;"
            f" border-top-right-radius: {DesignSystem.RADIUS_LG}px;"
            f" padding: {DesignSystem.SPACE_8}px {DesignSystem.SPACE_12}px; }}"
        )

    @staticmethod
    def get_details_header_title_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )

    @staticmethod
    def get_details_header_subtitle_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"border: none; background: transparent;"
        )

    @staticmethod
    def get_details_section_card_style() -> str:
        return (
            f"QFrame#detailsSection {{ background-color: {DesignSystem.COLOR_SURFACE};"
            f" border: 1px solid {DesignSystem.COLOR_CARD_BORDER};"
            f" border-radius: {DesignSystem.RADIUS_LG}px;"
            f" padding: {DesignSystem.SPACE_16}px; }}"
        )

    @staticmethod
    def get_details_section_title_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_BASE}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
            f"padding-bottom: {DesignSystem.SPACE_4}px;"
        )

    @staticmethod
    def get_details_key_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};"
            f"border: none; background: transparent;"
        )

    @staticmethod
    def get_details_value_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )

    @staticmethod
    def get_details_mono_value_style() -> str:
        return (
            f"font-family: {DesignSystem.FONT_FAMILY_MONO};"
            f"font-size: {DesignSystem.FONT_SIZE_SM}px;"
            f"color: {DesignSystem.COLOR_TEXT};"
            f"border: none; background: transparent;"
        )

    @staticmethod
    def get_details_badge_style(bg: str, fg: str) -> str:
        return (
            f"QLabel {{ background-color: {bg}; color: {fg};"
            f" border-radius: {DesignSystem.RADIUS_SM}px;"
            f" padding: 2px 8px;"
            f" font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f" font-weight: {DesignSystem.FONT_WEIGHT_BOLD}; }}"
        )

    @staticmethod
    def get_details_divider_style() -> str:
        return f"background-color: {DesignSystem.COLOR_BORDER_LIGHT}; border: none;"

    @staticmethod
    def get_details_feature_row_style(present: bool) -> str:
        bg = DesignSystem.COLOR_SUCCESS_SOFT_BG if present else "transparent"
        return (
            f"QFrame {{ background-color: {bg};"
            f" border-radius: {DesignSystem.RADIUS_SM}px;"
            f" padding: 4px 8px;"
            f" border: none; }}"
        )

    @staticmethod
    def get_details_warning_style() -> str:
        return (
            f"QFrame {{ background-color: {DesignSystem.COLOR_WARNING_BG};"
            f" border: 1px solid {DesignSystem.COLOR_WARNING};"
            f" border-radius: {DesignSystem.RADIUS_MD}px;"
            f" padding: {DesignSystem.SPACE_12}px; }}"
        )

    @staticmethod
    def get_details_image_table_header_style() -> str:
        return (
            f"font-size: {DesignSystem.FONT_SIZE_XS}px;"
            f"font-weight: {DesignSystem.FONT_WEIGHT_BOLD};"
            f"color: {DesignSystem.COLOR_TEXT_SECONDARY};"
            f"text-transform: uppercase;"
            f"letter-spacing: 0.5px;"
            f"border: none; background: transparent;"
        )

    @staticmethod
    def get_details_image_row_style(even: bool) -> str:
        bg = DesignSystem.COLOR_SURFACE if even else DesignSystem.COLOR_BACKGROUND
        return (
            f"QFrame {{ background-color: {bg};"
            f" border: none;"
            f" border-bottom: 1px solid {DesignSystem.COLOR_BORDER_LIGHT};"
            f" padding: 3px 0px; }}"
        )

    # ==================== ABOUT / TUTORIAL DIALOG ====================

    @staticmethod
    def get_tutorial_tab_widget_style() -> str:
        return f"""
            QTabWidget::pane {{
                border: none;
                background-color: {DesignSystem.COLOR_SURFACE};
                border-radius: 0;
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {DesignSystem.COLOR_TEXT_SECONDARY};
                padding: {DesignSystem.SPACE_10}px {DesignSystem.SPACE_12}px;
                border: none;
                border-left: 3px solid transparent;
                margin-bottom: 0px;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
                min-width: 100px;
                text-align: left;
            }}
            QTabBar::tab:selected {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                color: {DesignSystem.COLOR_PRIMARY};
                border-left: 3px solid {DesignSystem.COLOR_PRIMARY};
                font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {DesignSystem.COLOR_SECONDARY_LIGHT};
                color: {DesignSystem.COLOR_TEXT};
            }}
        """

    @staticmethod
    def get_tutorial_section_header_style() -> str:
        return f"""
            font-size: {DesignSystem.FONT_SIZE_LG}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
            color: {DesignSystem.COLOR_TEXT};
            padding-bottom: {DesignSystem.SPACE_8}px;
        """

    @staticmethod
    def get_tutorial_scroll_area_style() -> str:
        return f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background-color: {DesignSystem.COLOR_BACKGROUND};
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {DesignSystem.COLOR_BORDER};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {DesignSystem.COLOR_TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """

    @staticmethod
    def get_tutorial_step_card_style() -> str:
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """

    @staticmethod
    def get_tutorial_step_number_style() -> str:
        return f"""
            QLabel {{
                background-color: {DesignSystem.COLOR_PRIMARY};
                color: white;
                font-size: {DesignSystem.FONT_SIZE_SM}px;
                font-weight: {DesignSystem.FONT_WEIGHT_BOLD};
                border-radius: 12px;
                qproperty-alignment: AlignCenter;
            }}
        """

    @staticmethod
    def get_tutorial_card_title_style() -> str:
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        """

    @staticmethod
    def get_tutorial_card_desc_style() -> str:
        return f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            line-height: 1.2;
        """

    @staticmethod
    def get_tutorial_tip_card_style() -> str:
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_PRIMARY_LIGHT};
                border: none;
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
        """

    @staticmethod
    def get_tutorial_feature_card_accent_style(accent_color: str) -> str:
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-left: 4px solid {accent_color};
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_16}px;
            }}
        """

    @staticmethod
    def get_about_tool_card_category_style(bg_color: str, border_color: str) -> str:
        return f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                border-radius: {DesignSystem.RADIUS_LG}px;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """

    @staticmethod
    def get_about_category_header_style(accent_color: str) -> str:
        return f"""
            QFrame {{
                background-color: transparent;
                border: none;
                padding-bottom: {DesignSystem.SPACE_2}px;
                margin-top: {DesignSystem.SPACE_8}px;
                margin-bottom: {DesignSystem.SPACE_2}px;
            }}
        """

    @staticmethod
    def get_about_info_card_style() -> str:
        return f"""
            QFrame {{
                background-color: {DesignSystem.COLOR_BACKGROUND};
                border: none;
                border-radius: {DesignSystem.RADIUS_MD}px;
                padding: {DesignSystem.SPACE_2}px;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """

    @staticmethod
    def get_about_info_label_style() -> str:
        return f"color: {DesignSystem.COLOR_TEXT_SECONDARY}; font-size: {DesignSystem.FONT_SIZE_XS}px;"

    @staticmethod
    def get_about_info_value_style() -> str:
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_XS}px;
            font-weight: {DesignSystem.FONT_WEIGHT_MEDIUM};
        """

    @staticmethod
    def get_about_formats_text_style() -> str:
        return f"color: {DesignSystem.COLOR_TEXT}; font-size: {DesignSystem.FONT_SIZE_XS}px;"

    @staticmethod
    def get_about_value_card_style() -> str:
        return f"""
            QFrame {{
                background-color: transparent;
                border: none;
            }}
        """

    @staticmethod
    def get_about_value_title_style() -> str:
        return f"""
            color: {DesignSystem.COLOR_TEXT};
            font-size: {DesignSystem.FONT_SIZE_SM}px;
            font-weight: {DesignSystem.FONT_WEIGHT_SEMIBOLD};
        """

    @staticmethod
    def get_about_value_desc_style() -> str:
        return f"""
            color: {DesignSystem.COLOR_TEXT_SECONDARY};
            font-size: {DesignSystem.FONT_SIZE_XS}px;
        """

    @staticmethod
    def get_about_separator_style() -> str:
        return f"background-color: {DesignSystem.COLOR_BORDER_LIGHT}; max-height: 1px;"

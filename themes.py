# themes.py

from dataclasses import dataclass
from PyQt5.QtGui import QPalette, QColor


@dataclass
class Theme:
    name: str
    window_bg: str  # Main background
    panel_bg: str   # Card/Container background
    text: str
    muted_text: str
    accent: str     # Primary branding color
    accent_hover: str
    accent_soft: str # Light version of accent for backgrounds
    border: str
    success: str    # Green for selected seats
    error: str      # Red for errors/cancel


# 1. Elite Light: Clean, soft shadows, professional slate colors.
LIGHT = Theme(
    name="light",
    window_bg="#F1F5F9",       # Slate 100
    panel_bg="#FFFFFF",        # White
    text="#1E293B",            # Slate 800
    muted_text="#64748B",      # Slate 500
    accent="#2563EB",          # Blue 600
    accent_hover="#1D4ED8",    # Blue 700
    accent_soft="#EFF6FF",     # Blue 50
    border="#E2E8F0",          # Slate 200
    success="#10B981",         # Emerald 500
    error="#EF4444",           # Red 500
)

# 2. Pro Dark: Deep blue-greys, high contrast, easy on eyes.
DARK = Theme(
    name="dark",
    window_bg="#0B1120",       # Very dark slate/blue
    panel_bg="#1E293B",        # Slate 800
    text="#F8FAFC",            # Slate 50
    muted_text="#94A3B8",      # Slate 400
    accent="#6366F1",          # Indigo 500
    accent_hover="#818CF8",    # Indigo 400
    accent_soft="#312E81",     # Indigo 900
    border="#334155",          # Slate 700
    success="#34D399",         # Emerald 400
    error="#F87171",           # Red 400
)

# 3. Midnight (Night): Pure black/grey for OLED screens.
NIGHT = Theme(
    name="night",
    window_bg="#000000",
    panel_bg="#111111",
    text="#E5E5E5",
    muted_text="#737373",
    accent="#F59E0B",          # Amber 500 (Gold look)
    accent_hover="#D97706",    # Amber 600
    accent_soft="#451A03",     # Dark amber
    border="#262626",
    success="#22C55E",
    error="#EF4444",
)

THEMES = {
    "light": LIGHT,
    "dark": DARK,
    "night": NIGHT,
}


def apply_theme_to_palette(theme: Theme, palette: QPalette) -> None:
    """Set basic palette colors for the given theme."""
    palette.setColor(QPalette.Window, QColor(theme.window_bg))
    palette.setColor(QPalette.WindowText, QColor(theme.text))
    palette.setColor(QPalette.Base, QColor(theme.panel_bg))
    palette.setColor(QPalette.AlternateBase, QColor(theme.panel_bg))
    palette.setColor(QPalette.ToolTipBase, QColor(theme.text))
    palette.setColor(QPalette.ToolTipText, QColor(theme.panel_bg))
    palette.setColor(QPalette.Text, QColor(theme.text))
    palette.setColor(QPalette.Button, QColor(theme.panel_bg))
    palette.setColor(QPalette.ButtonText, QColor(theme.text))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor(theme.accent))
    palette.setColor(QPalette.Highlight, QColor(theme.accent))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
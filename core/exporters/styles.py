"""Shared theme tokens.

SCREEN_THEME is applied by ui/theme.py in the browser (black bg, green
bold headers, white body).

EXPORT_THEME is used by the exporters when building PDF / Excel / TXT
documents (white page, green bold headers, black body). This is the
single source of truth for the "swap colors on export" rule.
"""

# On-screen palette
SCREEN_THEME = {
    "bg":    "#000000",
    "title": "#00FF66",
    "body":  "#FFFFFF",
    "muted": "#888888",
    "border": "#00FF66",
}

# Exported-document palette
EXPORT_THEME = {
    "bg":    "#FFFFFF",
    "title": "#008A3A",   # dark green — readable on white paper
    "body":  "#000000",
    "muted": "#666666",
    "border": "#CCCCCC",
}

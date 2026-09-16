from nicegui import ui

CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">

<style>
  /* === Base === */
  html, body, #app, .nicegui-content, .q-page-container, .q-page {
    background: #000000 !important;
    color: #ffffff !important;
  }
  html, body, * {
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace !important;
  }

  /* === Typography === */
  h1, h2, h3, h4, h5, h6,
  .dpr-title,
  .q-card h1, .q-card h2, .q-card h3 {
    color: #00FF66 !important;
    font-weight: 700 !important;
    letter-spacing: 0.5px;
  }
  p, span, div, label, li, td, th,
  .q-label, .q-field__label, .q-field__native,
  .q-item__label, .q-btn__content {
    color: #ffffff !important;
  }

  /* === Cards === */
  .q-card, .q-card__section {
    background: #0a0a0a !important;
    border: 1px solid #00FF66 !important;
    color: #ffffff !important;
    box-shadow: 0 0 12px rgba(0,255,102,0.15) !important;
  }

  /* === Buttons — kill Material blue === */
  .q-btn,
  .q-btn--standard,
  .q-btn--flat,
  .q-btn--outline,
  button.q-btn {
    background: #000000 !important;
    color: #00FF66 !important;
    border: 1.5px solid #00FF66 !important;
    border-radius: 4px !important;
    font-weight: 700 !important;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 6px 16px;
    box-shadow: none !important;
    transition: all .15s ease;
  }
  .q-btn:hover {
    background: #00FF66 !important;
    color: #000000 !important;
    box-shadow: 0 0 16px rgba(0,255,102,0.6) !important;
  }
  .q-btn__content, .q-btn .q-icon { color: inherit !important; }

  /* === Separators === */
  .q-separator { background: #00FF66 !important; height: 1px !important; }

  /* === Inputs / Upload === */
  .q-field__control,
  .q-field__control:before,
  .q-field__control:after {
    border-color: #00FF66 !important;
    background: #050505 !important;
  }
  .q-uploader {
    background: #0a0a0a !important;
    border: 1.5px dashed #00FF66 !important;
    color: #ffffff !important;
    width: 100%;
  }
  .q-uploader__header {
    background: #001a0a !important;
    color: #00FF66 !important;
  }
  .q-uploader__list { background: #0a0a0a !important; }
  .q-uploader__file { color: #ffffff !important; }

  /* === Progress bar === */
  .q-linear-progress {
    background: #0a0a0a !important;
  }
  .q-linear-progress__track { background: #0a0a0a !important; }
  .q-linear-progress__model { background: #00FF66 !important; }

  /* === Tables === */
  .q-table, .q-table td, .q-table th {
    color: #ffffff !important;
    background: transparent !important;
    border-color: #1f3f1f !important;
  }
  .q-table thead th { color: #00FF66 !important; }

  /* === Links === */
  a { color: #00FF66 !important; }
  a:hover { text-decoration: underline; }

  /* === Console === */
  .dpr-console {
    background: #050505 !important;
    border: 1px solid #00FF66 !important;
    color: #00FF66 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px;
    padding: 10px;
    max-height: 240px;
    overflow: auto;
    white-space: pre-wrap;
  }

  /* === Notifications === */
  .q-notification {
    background: #0a0a0a !important;
    color: #00FF66 !important;
    border: 1px solid #00FF66 !important;
  }

  /* === Scrollbar === */
  ::-webkit-scrollbar { width: 10px; height: 10px; }
  ::-webkit-scrollbar-track { background: #000; }
  ::-webkit-scrollbar-thumb { background: #00FF66; border-radius: 5px; }
</style>
"""


def apply_theme() -> None:
    """Register global CSS. `shared=True` makes it apply to every page."""
    ui.add_head_html(CSS, shared=True)

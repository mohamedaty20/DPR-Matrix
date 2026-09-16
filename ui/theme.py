from nicegui import ui


def apply_theme() -> None:
    """Inject global CSS. Black bg, green headers, white body, mono font."""
    ui.add_head_html("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/assets/styles.css">
    <style>
      html, body { background:#000 !important; color:#fff !important;
        font-family:'JetBrains Mono','Fira Code',Consolas,monospace !important;
        margin:0; padding:0; }
      .nicegui-content { background:#000 !important; }
      h1, h2, h3, h4, .dpr-title { color:#00FF66 !important; font-weight:700 !important; }
      .q-label, p, span, td, th { color:#fff !important; }
      .q-table, .q-table td, .q-table th { color:#fff !important; background:transparent !important; }
      .q-table thead th { color:#00FF66 !important; }
      .q-field__control, .q-field__native, .q-field__label { color:#fff !important; }
      .q-field__control:before { border-color:#00FF66 !important; }
      a { color:#00FF66 !important; }
      .q-btn { background:#0b0b0b !important; color:#00FF66 !important;
        border:1px solid #00FF66 !important; }
      .q-btn:hover { background:#00FF66 !important; color:#000 !important; }
      .q-card { background:#0a0a0a !important; border:1px solid #00FF66 !important;
        color:#fff !important; }
      .q-separator { background:#00FF66 !important; }
      .dpr-console { background:#050505; border:1px solid #1f3f1f;
        color:#00FF66; font-size:12px; padding:8px; max-height:220px; overflow:auto; }
      ::-webkit-scrollbar { width:10px; height:10px; }
      ::-webkit-scrollbar-track { background:#000; }
      ::-webkit-scrollbar-thumb { background:#00FF66; border-radius:5px; }
    </style>
    """)

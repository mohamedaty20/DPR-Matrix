from nicegui import ui

CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">

<style>
:root {
  --dpr-bg:            #050506;
  --dpr-surface:       #0c0c0f;
  --dpr-surface-2:     #121216;
  --dpr-surface-3:     #17171c;
  --dpr-border:        rgba(0, 255, 102, 0.14);
  --dpr-border-hover:  rgba(0, 255, 102, 0.38);
  --dpr-primary:       #00FF66;
  --dpr-primary-dim:   #00cc52;
  --dpr-text:          #e8e8ea;
  --dpr-text-muted:    #85858c;
  --dpr-text-dim:      #4f4f56;
  --dpr-danger:        #ff4d6a;
  --dpr-warning:       #ffb020;
  --dpr-radius:        12px;
  --dpr-radius-sm:     8px;
}

/* ── Base ─────────────────────────────────────────────────────────── */
html, body, #app, .nicegui-content, .q-page-container, .q-page {
  background: var(--dpr-bg) !important;
  color: var(--dpr-text) !important;
}
html, body, * {
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace !important;
  -webkit-font-smoothing: antialiased;
}

/* ── Typography ───────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 { color: var(--dpr-text) !important; font-weight: 600 !important; }
p, span, div, label, li, td, th,
.q-label, .q-field__label, .q-field__native,
.q-item__label {
  color: var(--dpr-text) !important;
}

.dpr-app-title {
  color: var(--dpr-primary) !important;
  font-size: 26px !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin: 0 !important;
}
.dpr-app-subtitle {
  color: var(--dpr-text-muted) !important;
  font-size: 13px !important;
  line-height: 1.6;
  margin: 6px 0 20px 0;
  max-width: 780px;
}
.dpr-title {
  color: var(--dpr-primary) !important;
  font-weight: 700 !important;
  font-size: 12px !important;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin: 0 !important;
}
.dpr-muted { color: var(--dpr-text-muted) !important; font-size: 12px; }
.dpr-mono  { font-family: 'JetBrains Mono', monospace !important; font-size: 13px; }

/* ── Card ─────────────────────────────────────────────────────────── */
.q-card, .q-card__section, .dpr-card {
  background: linear-gradient(180deg, var(--dpr-surface) 0%, #08080a 100%) !important;
  border: 1px solid var(--dpr-border) !important;
  border-radius: var(--dpr-radius) !important;
  color: var(--dpr-text) !important;
  box-shadow: 0 1px 0 rgba(255,255,255,0.02) inset !important;
  padding: 18px 20px !important;
}

/* ── Buttons — small, ghost, no uppercase ─────────────────────────── */
.q-btn, button.q-btn {
  background: transparent !important;
  color: var(--dpr-text) !important;
  border: 1px solid var(--dpr-border) !important;
  border-radius: var(--dpr-radius-sm) !important;
  font-weight: 600 !important;
  font-size: 12.5px !important;
  letter-spacing: 0.01em !important;
  text-transform: none !important;
  min-height: 34px !important;
  padding: 0 14px !important;
  box-shadow: none !important;
  transition: background-color .12s ease, border-color .12s ease, color .12s ease;
}
.q-btn:hover {
  background: rgba(255,255,255,0.03) !important;
  border-color: var(--dpr-border-hover) !important;
  color: var(--dpr-primary) !important;
  box-shadow: none !important;
}
.q-btn:disabled, .q-btn--disabled {
  opacity: 0.35 !important;
  cursor: not-allowed !important;
}
.q-btn__content, .q-btn .q-icon { color: inherit !important; font-size: 13px !important; }

/* Primary — solid green */
.dpr-btn-primary.q-btn {
  background: var(--dpr-primary) !important;
  color: #050506 !important;
  border-color: var(--dpr-primary) !important;
  font-weight: 700 !important;
}
.dpr-btn-primary.q-btn:hover {
  background: var(--dpr-primary-dim) !important;
  color: #050506 !important;
  border-color: var(--dpr-primary-dim) !important;
}

/* Danger — red ghost */
.dpr-btn-danger.q-btn {
  border-color: rgba(255,77,106,0.35) !important;
  color: var(--dpr-danger) !important;
}
.dpr-btn-danger.q-btn:hover {
  border-color: var(--dpr-danger) !important;
  background: rgba(255,77,106,0.08) !important;
  color: var(--dpr-danger) !important;
}

/* Icon-only (queue remove) */
.dpr-icon-btn.q-btn {
  padding: 0 !important;
  min-height: 26px !important;
  width: 26px !important;
  min-width: 26px !important;
  border-radius: 6px !important;
  color: var(--dpr-text-muted) !important;
  border-color: transparent !important;
}
.dpr-icon-btn.q-btn:hover {
  color: var(--dpr-danger) !important;
  border-color: rgba(255,77,106,0.4) !important;
  background: rgba(255,77,106,0.06) !important;
}

/* ── Separators ───────────────────────────────────────────────────── */
.q-separator { background: var(--dpr-border) !important; height: 1px !important; }

/* ── Inputs / Upload ──────────────────────────────────────────────── */
.q-field__control,
.q-field__control:before,
.q-field__control:after {
  border-color: var(--dpr-border) !important;
  background: var(--dpr-surface-2) !important;
}
.q-field--focused .q-field__control { border-color: var(--dpr-primary) !important; }
.q-uploader {
  background: var(--dpr-surface-2) !important;
  border: 1px dashed var(--dpr-border-hover) !important;
  border-radius: var(--dpr-radius-sm) !important;
  color: var(--dpr-text) !important;
  width: 100%;
  box-shadow: none !important;
}
.q-uploader__header {
  background: var(--dpr-surface-3) !important;
  color: var(--dpr-text-muted) !important;
  font-size: 12px !important;
}
.q-uploader__list { background: var(--dpr-surface-2) !important; }
.q-uploader__file { color: var(--dpr-text) !important; }

/* ── Progress bar ─────────────────────────────────────────────────── */
.q-linear-progress {
  background: var(--dpr-surface-2) !important;
  border-radius: 999px !important;
  overflow: hidden;
  height: 4px !important;
}
.q-linear-progress__track { background: var(--dpr-surface-2) !important; }
.q-linear-progress__model { background: var(--dpr-primary) !important; }

/* ── Tables ───────────────────────────────────────────────────────── */
.q-table, .q-table td, .q-table th {
  color: var(--dpr-text) !important;
  background: transparent !important;
  border-color: var(--dpr-border) !important;
}
.q-table thead th { color: var(--dpr-primary) !important; font-weight: 600 !important; }

/* ── Links ────────────────────────────────────────────────────────── */
a { color: var(--dpr-primary) !important; text-decoration: none; }
a:hover { color: var(--dpr-primary-dim) !important; }

/* ── Console ──────────────────────────────────────────────────────── */
.dpr-console {
  background: #06060a !important;
  border: 1px solid var(--dpr-border) !important;
  border-radius: var(--dpr-radius-sm) !important;
  color: #a8e5c0 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11.5px !important;
  line-height: 1.65 !important;
  padding: 12px 14px !important;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
}

/* ── Status badges ────────────────────────────────────────────────── */
.dpr-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border: 1px solid var(--dpr-border);
  color: var(--dpr-text-muted) !important;
  background: rgba(255,255,255,0.02);
  white-space: nowrap;
}
.dpr-badge-queued     { color: var(--dpr-text-muted) !important; }
.dpr-badge-extracting { color: var(--dpr-warning) !important; border-color: rgba(255,176,32,0.4) !important; }
.dpr-badge-done       { color: var(--dpr-primary) !important; border-color: rgba(0,255,102,0.4) !important; }
.dpr-badge-error      { color: var(--dpr-danger)  !important; border-color: rgba(255,77,106,0.4) !important; }

/* ── Queue row ────────────────────────────────────────────────────── */
.dpr-queue-row {
  background: var(--dpr-surface-2);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius-sm);
  padding: 10px 14px;
  transition: border-color .12s ease;
}
.dpr-queue-row:hover { border-color: var(--dpr-border-hover); }
.dpr-queue-name {
  font-size: 13px !important;
  color: var(--dpr-text) !important;
  font-weight: 500;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dpr-queue-size {
  color: var(--dpr-text-dim) !important;
  font-size: 11.5px;
}

/* ── Notifications ────────────────────────────────────────────────── */
.q-notification {
  background: var(--dpr-surface-2) !important;
  color: var(--dpr-text) !important;
  border: 1px solid var(--dpr-border) !important;
  border-radius: var(--dpr-radius-sm) !important;
  font-size: 12.5px !important;
}

/* ── Scrollbar ────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 102, 0.18);
  border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(0, 255, 102, 0.4); }
</style>
"""


def apply_theme() -> None:
    """Register global CSS. `shared=True` makes it apply to every page."""
    ui.add_head_html(CSS, shared=True)

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

/* ── Buttons ──────────────────────────────────────────────────────── */
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

.dpr-btn-danger.q-btn {
  border-color: rgba(255,77,106,0.35) !important;
  color: var(--dpr-danger) !important;
}
.dpr-btn-danger.q-btn:hover {
  border-color: var(--dpr-danger) !important;
  background: rgba(255,77,106,0.08) !important;
  color: var(--dpr-danger) !important;
}

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

/* ═══════════════════════════════════════════════════════════════════
   Pass 7.5 — Dashboard
   ═══════════════════════════════════════════════════════════════════ */

/* ── Metadata strip ───────────────────────────────────────────────── */
.dpr-meta-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px;
  background: var(--dpr-border);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius-sm);
  overflow: hidden;
  margin: 12px 0;
}
.dpr-meta-item {
  background: var(--dpr-surface);
  padding: 12px 14px;
}
.dpr-meta-label {
  color: var(--dpr-text-muted) !important;
  font-size: 10.5px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 6px;
}
.dpr-meta-value {
  color: var(--dpr-text) !important;
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── KPI grid ─────────────────────────────────────────────────────── */
.dpr-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin: 14px 0;
  width: 100%;
}
.dpr-kpi {
  background: linear-gradient(180deg, var(--dpr-surface-2) 0%, #08080a 100%);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius);
  padding: 16px 18px;
  position: relative;
  overflow: hidden;
  transition: border-color .14s ease, transform .14s ease;
}
.dpr-kpi:hover {
  border-color: var(--dpr-border-hover);
  transform: translateY(-1px);
}
.dpr-kpi-label {
  color: var(--dpr-text-muted) !important;
  font-size: 10.5px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 600;
  margin-bottom: 10px;
}
.dpr-kpi-value {
  color: var(--dpr-text) !important;
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
}
.dpr-kpi-sub {
  color: var(--dpr-text-dim) !important;
  font-size: 11px;
  margin-top: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dpr-kpi-primary .dpr-kpi-value { color: var(--dpr-primary) !important; }
.dpr-kpi-warning .dpr-kpi-value { color: var(--dpr-warning) !important; }
.dpr-kpi-danger  .dpr-kpi-value { color: var(--dpr-danger)  !important; }

/* ── Charts grid ──────────────────────────────────────────────────── */
.dpr-chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
  margin: 14px 0;
  width: 100%;
}
.dpr-chart {
  background: linear-gradient(180deg, var(--dpr-surface-2) 0%, #08080a 100%);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius);
  padding: 16px 18px;
}
.dpr-chart-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.dpr-chart-title {
  color: var(--dpr-text) !important;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: -0.005em;
}
.dpr-chart-total {
  color: var(--dpr-primary) !important;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
  white-space: nowrap;
}
.dpr-chart-total-label {
  color: var(--dpr-text-dim) !important;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 600;
  margin-left: 4px;
}
.dpr-chart-subtitle {
  color: var(--dpr-text-dim) !important;
  font-size: 11px;
  line-height: 1.55;
  margin-bottom: 16px;
  max-width: 340px;
}
.dpr-bar-chart {
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.dpr-bar-row {
  display: grid;
  grid-template-columns: 110px 1fr 70px;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.dpr-bar-label {
  color: var(--dpr-text) !important;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dpr-bar-track {
  background: rgba(255,255,255,0.03);
  border-radius: 999px;
  height: 8px;
  overflow: hidden;
}
.dpr-bar-fill {
  background: linear-gradient(90deg, var(--dpr-primary-dim), var(--dpr-primary));
  height: 100%;
  border-radius: 999px;
  transition: width .3s ease;
}
.dpr-bar-value {
  color: var(--dpr-text-muted) !important;
  font-size: 11.5px;
  text-align: right;
  font-weight: 600;
}
.dpr-bar-value .dpr-bar-pct {
  color: var(--dpr-text-dim) !important;
  font-weight: 400;
  margin-left: 6px;
  font-size: 10.5px;
}
.dpr-chart-empty {
  color: var(--dpr-text-dim) !important;
  font-size: 12px;
  padding: 8px 0;
  font-style: italic;
}

/* ── Download bar ─────────────────────────────────────────────────── */
.dpr-download-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  background: linear-gradient(90deg,
      rgba(0,255,102,0.05) 0%,
      rgba(0,255,102,0.02) 100%);
  border: 1px solid var(--dpr-border-hover);
  border-radius: var(--dpr-radius);
  padding: 14px 18px;
  margin: 16px 0;
  flex-wrap: wrap;
}
.dpr-download-bar-label {
  color: var(--dpr-text) !important;
  font-size: 12.5px;
  font-weight: 600;
}
.dpr-download-bar-label small {
  color: var(--dpr-text-muted) !important;
  font-weight: 400;
  display: block;
  margin-top: 3px;
  font-size: 11px;
}

/* ── Section header (title + subtitle) ────────────────────────────── */
.dpr-section-subtitle {
  color: var(--dpr-text-muted) !important;
  font-size: 11.5px;
  line-height: 1.55;
  margin: 4px 0 14px 0;
  max-width: 640px;
}
</style>
"""


def apply_theme() -> None:
    """Register global CSS. `shared=True` makes it apply to every page."""
    ui.add_head_html(CSS, shared=True)

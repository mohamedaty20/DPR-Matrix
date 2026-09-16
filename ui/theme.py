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
  --dpr-border:        rgba(34, 197, 94, 0.20);
  --dpr-border-hover:  rgba(34, 197, 94, 0.42);
  --dpr-primary:       #22c55e;
  --dpr-primary-dim:   #16a34a;
  --dpr-primary-soft:  rgba(34, 197, 94, 0.12);
  --dpr-text:          #e8e8ea;
  --dpr-text-muted:    #85858c;
  --dpr-text-dim:      #4f4f56;
  --dpr-danger:        #ff4d6a;
  --dpr-warning:       #ffb020;
  --dpr-radius:        12px;
  --dpr-radius-sm:     8px;
  --dpr-topbar-h:      52px;
  --dpr-sidebar-w:     232px;
}

/* ── Base background ──────────────────────────────────────────────── */
html, body, #app, .nicegui-content, .q-page-container, .q-page {
  background: var(--dpr-bg) !important;
  color: var(--dpr-text) !important;
}

/* ── Font: apply to text elements ONLY (never `*`) ────────────────── */
html, body {
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace !important;
  -webkit-font-smoothing: antialiased;
}
body, .q-page, .q-card, .q-btn, .q-field, .q-item, .q-label,
.dpr-shell, .dpr-shell-sidebar, .dpr-shell-main,
.dpr-nav-item, .dpr-nav-label, .dpr-brand-mark, .dpr-brand-name,
.dpr-page-title, .dpr-page-subtitle, .dpr-panel, .dpr-stat,
.dpr-pill, .dpr-meta-strip, .dpr-meta-item, .dpr-console,
.dpr-bar-label, .dpr-bar-value, .dpr-chart-title, .dpr-chart-total,
.dpr-hist-label, .dpr-hist-value, .dpr-toplist-name, .dpr-toplist-value,
.dpr-ratio-label, .dpr-ratio-total, .dpr-ratio-legend,
.dpr-download-bar, .dpr-download-bar-label,
.dpr-matrix-head, .dpr-matrix-row-head, .dpr-matrix-cell,
.dpr-badge, .dpr-queue-name, .dpr-queue-size,
.dpr-section-subtitle, .dpr-topbar-crumb,
.dpr-app-title, .dpr-app-subtitle, .dpr-title, .dpr-muted {
  font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, monospace !important;
}

/* ── Icons MUST keep their own font — do NOT override ─────────────── */
.q-icon, .material-icons, .material-icons-outlined,
.material-icons-round, .material-icons-sharp,
.material-symbols-outlined, .material-symbols-rounded,
.q-btn .q-icon, .q-item .q-icon, [class*="q-icon"] {
  font-family: 'Material Icons', 'Material Icons Outlined',
               'Material Icons Round', 'Material Symbols Outlined',
               'Material Icons Sharp', sans-serif !important;
  font-feature-settings: 'liga' !important;
  -webkit-font-feature-settings: 'liga' !important;
  font-weight: normal !important;
}

/* ── Header / general typography ──────────────────────────────────── */
h1, h2, h3, h4, h5, h6 { color: var(--dpr-text) !important; font-weight: 600 !important; }
p, span, div, label, li, td, th,
.q-label, .q-field__label, .q-field__native,
.q-item__label {
  color: var(--dpr-text);
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
.q-btn:disabled, .q-btn--disabled { opacity: 0.35 !important; cursor: not-allowed !important; }
.q-btn__content, .q-btn .q-icon { color: inherit !important; font-size: 13px !important; }

.dpr-btn-primary.q-btn {
  background: var(--dpr-primary) !important;
  color: #050506 !important;
  border-color: var(--dpr-primary) !important;
  font-weight: 700 !important;
}
.dpr-btn-primary.q-btn:hover {
  background: var(--dpr-primary-dim) !important;
  border-color: var(--dpr-primary-dim) !important;
  color: #050506 !important;
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
.q-field__control, .q-field__control:before, .q-field__control:after {
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

/* ── Tables (Quasar) ──────────────────────────────────────────────── */
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
  color: #8fd8a8 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 11.5px !important;
  line-height: 1.65 !important;
  padding: 12px 14px !important;
  max-height: 280px;
  overflow: auto;
  white-space: pre-wrap;
}

/* ── Badges ───────────────────────────────────────────────────────── */
.dpr-badge {
  display: inline-flex; align-items: center;
  padding: 3px 9px; border-radius: 999px;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  border: 1px solid var(--dpr-border);
  color: var(--dpr-text-muted) !important;
  background: rgba(255,255,255,0.02);
  white-space: nowrap;
}
.dpr-badge-queued     { color: var(--dpr-text-muted) !important; }
.dpr-badge-extracting { color: var(--dpr-warning) !important;
  border-color: rgba(255,176,32,0.4) !important; }
.dpr-badge-done       { color: var(--dpr-primary) !important;
  border-color: var(--dpr-border-hover) !important; }
.dpr-badge-error      { color: var(--dpr-danger)  !important;
  border-color: rgba(255,77,106,0.4) !important; }

/* ── Queue rows ───────────────────────────────────────────────────── */
.dpr-queue-row {
  background: var(--dpr-surface-2);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius-sm);
  padding: 10px 14px;
  transition: border-color .12s ease;
}
.dpr-queue-row:hover { border-color: var(--dpr-border-hover); }
.dpr-queue-name { font-size: 13px !important; color: var(--dpr-text) !important;
  font-weight: 500; flex: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dpr-queue-size { color: var(--dpr-text-dim) !important; font-size: 11.5px; }

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
  background: rgba(34, 197, 94, 0.22);
  border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(34, 197, 94, 0.42); }

/* ═══════════════════════════════════════════════════════════════════
   Shell — pure CSS grid
   ═══════════════════════════════════════════════════════════════════ */
.dpr-shell {
  display: grid;
  grid-template-columns: var(--dpr-sidebar-w) 1fr;
  min-height: 100vh;
  background: var(--dpr-bg);
}
.dpr-shell-sidebar {
  display: flex;
  flex-direction: column;
  background: #08080a;
  border-right: 1px solid var(--dpr-border);
  padding: 18px 12px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}
.dpr-shell-sidebar-spacer { flex: 1; }
.dpr-shell-brand {
  padding: 4px 12px 20px 12px;
  font-size: 15px;
  font-weight: 700;
}
.dpr-shell-nav { display: flex; flex-direction: column; gap: 2px; }
.dpr-shell-sidebar-footer {
  display: flex; flex-direction: column; gap: 6px;
  padding-top: 12px; margin-top: 12px;
  border-top: 1px solid var(--dpr-border);
}
.dpr-shell-main { display: flex; flex-direction: column; min-width: 0; background: var(--dpr-bg); }
.dpr-shell-topbar {
  height: var(--dpr-topbar-h);
  min-height: var(--dpr-topbar-h);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px;
  background: rgba(8, 8, 12, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--dpr-border);
  position: sticky; top: 0; z-index: 10;
}
.dpr-shell-topbar-left, .dpr-shell-topbar-right {
  display: flex; align-items: center; gap: 8px;
}
.dpr-topbar-crumb {
  color: var(--dpr-text-muted); font-size: 12px; font-weight: 500;
  letter-spacing: 0.02em;
}
.dpr-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px;
  background: var(--dpr-primary-soft);
  border: 1px solid var(--dpr-border);
  border-radius: 999px;
  font-size: 11px; font-weight: 600;
  color: var(--dpr-text) !important;
  letter-spacing: 0.02em;
}
.dpr-pill-dot {
  width: 6px; height: 6px;
  background: var(--dpr-primary);
  border-radius: 50%;
}
.dpr-pill-warn {
  color: var(--dpr-warning) !important;
  border-color: rgba(255,176,32,0.4) !important;
}

/* ── Nav items ────────────────────────────────────────────────────── */
.dpr-nav-item {
  display: block;
  padding: 8px 12px !important;
  border-radius: var(--dpr-radius-sm);
  color: var(--dpr-text-muted) !important;
  text-decoration: none !important;
  transition: background-color .12s ease, color .12s ease;
  cursor: pointer;
}
.dpr-nav-item:hover {
  background: rgba(255,255,255,0.03);
  color: var(--dpr-text) !important;
  text-decoration: none !important;
}
.dpr-nav-active {
  background: var(--dpr-primary-soft) !important;
  color: var(--dpr-primary) !important;
  position: relative;
}
.dpr-nav-active::before {
  content: "";
  position: absolute;
  left: -12px; top: 8px; bottom: 8px;
  width: 2px;
  background: var(--dpr-primary);
  border-radius: 0 2px 2px 0;
}
.dpr-nav-active .dpr-nav-label { color: var(--dpr-primary) !important; }
.dpr-nav-icon { font-size: 18px !important; }
.dpr-nav-label { font-size: 13px !important; font-weight: 500; }

/* ── Page header / body ───────────────────────────────────────────── */
.dpr-page-header { padding: 24px 28px 8px 28px; display: flex; flex-direction: column; gap: 4px; }
.dpr-page-body { padding: 16px 28px 40px 28px; display: flex; flex-direction: column; gap: 16px; max-width: 1400px; }
.dpr-page-title {
  color: var(--dpr-text) !important;
  font-size: 22px !important; font-weight: 600 !important;
  letter-spacing: -0.02em; line-height: 1.2; margin: 0 !important;
}
.dpr-page-subtitle {
  color: var(--dpr-text-muted) !important;
  font-size: 13px !important; line-height: 1.55;
  margin: 2px 0 0 0; max-width: 780px;
}

@media (max-width: 820px) {
  .dpr-shell { grid-template-columns: 1fr; }
  .dpr-shell-sidebar {
    position: relative; height: auto;
    border-right: none; border-bottom: 1px solid var(--dpr-border);
    padding: 12px 16px;
  }
  .dpr-shell-brand { padding: 0 0 10px 0; }
  .dpr-shell-nav { flex-direction: row; overflow-x: auto; gap: 6px; }
  .dpr-nav-item { padding: 8px 12px !important; white-space: nowrap; }
  .dpr-shell-sidebar-footer { display: none; }
  .dpr-shell-topbar { padding: 0 16px; }
  .dpr-page-header { padding: 18px 16px 8px 16px; }
  .dpr-page-body { padding: 12px 16px 32px 16px; }
}

/* ═══════════════════════════════════════════════════════════════════
   Analytics widgets
   ═══════════════════════════════════════════════════════════════════ */
.dpr-stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px; width: 100%;
}
.dpr-stat {
  background: linear-gradient(180deg, var(--dpr-surface-2) 0%, #08080a 100%);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius);
  padding: 16px 18px;
  transition: border-color .14s ease, transform .14s ease;
}
.dpr-stat:hover { border-color: var(--dpr-border-hover); transform: translateY(-1px); }
.dpr-stat-label {
  color: var(--dpr-text-muted) !important; font-size: 10.5px;
  letter-spacing: 0.12em; text-transform: uppercase;
  font-weight: 600; margin-bottom: 10px;
}
.dpr-stat-value {
  color: var(--dpr-text) !important; font-size: 28px;
  font-weight: 700; line-height: 1; letter-spacing: -0.02em;
}
.dpr-stat-sub {
  color: var(--dpr-text-dim) !important; font-size: 11px;
  margin-top: 8px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap;
}
.dpr-stat-primary .dpr-stat-value { color: var(--dpr-primary) !important; }
.dpr-stat-warning .dpr-stat-value { color: var(--dpr-warning) !important; }
.dpr-stat-danger  .dpr-stat-value { color: var(--dpr-danger)  !important; }

.dpr-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 14px; width: 100%;
}
.dpr-panel {
  background: linear-gradient(180deg, var(--dpr-surface-2) 0%, #08080a 100%);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius);
  padding: 18px 20px;
  display: flex; flex-direction: column;
}
.dpr-panel-wide { grid-column: 1 / -1; }
.dpr-panel-header {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 12px; margin-bottom: 4px;
}
.dpr-panel-title {
  color: var(--dpr-text) !important;
  font-size: 13px; font-weight: 600; letter-spacing: -0.005em;
}
.dpr-panel-total {
  color: var(--dpr-primary) !important;
  font-size: 16px; font-weight: 700; letter-spacing: -0.01em; white-space: nowrap;
}
.dpr-panel-total small {
  color: var(--dpr-text-dim) !important;
  font-size: 10px; text-transform: uppercase;
  letter-spacing: 0.1em; font-weight: 600; margin-left: 4px;
}
.dpr-panel-sub {
  color: var(--dpr-text-dim) !important;
  font-size: 11px; line-height: 1.55;
  margin-bottom: 16px; max-width: 340px;
}
.dpr-panel-empty {
  color: var(--dpr-text-dim) !important;
  font-size: 12px; padding: 6px 0; font-style: italic;
}

.dpr-bars { display: flex; flex-direction: column; gap: 9px; }
.dpr-bar-row {
  display: grid; grid-template-columns: 120px 1fr 78px;
  align-items: center; gap: 10px; font-size: 12px;
}
.dpr-bar-label {
  color: var(--dpr-text) !important; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dpr-bar-track {
  background: rgba(255,255,255,0.03); border-radius: 999px;
  height: 8px; overflow: hidden;
}
.dpr-bar-fill {
  background: linear-gradient(90deg, var(--dpr-primary-dim), var(--dpr-primary));
  height: 100%; border-radius: 999px; transition: width .3s ease;
}
.dpr-bar-value {
  color: var(--dpr-text-muted) !important; font-size: 11.5px;
  text-align: right; font-weight: 600;
}
.dpr-bar-value .dpr-bar-pct {
  color: var(--dpr-text-dim) !important;
  font-weight: 400; margin-left: 6px; font-size: 10.5px;
}

.dpr-ratio-row { display: flex; flex-direction: column; gap: 6px; margin-bottom: 12px; }
.dpr-ratio-top {
  display: flex; justify-content: space-between;
  font-size: 12px; font-weight: 500;
}
.dpr-ratio-label { color: var(--dpr-text) !important; }
.dpr-ratio-total { color: var(--dpr-text-muted) !important; font-size: 11px; }
.dpr-ratio-track {
  display: flex; height: 8px;
  border-radius: 999px; overflow: hidden;
  background: rgba(255,255,255,0.03);
}
.dpr-ratio-skilled {
  background: linear-gradient(90deg, var(--dpr-primary-dim), var(--dpr-primary));
}
.dpr-ratio-helpers { background: rgba(34, 197, 94, 0.28); }
.dpr-ratio-legend {
  display: flex; gap: 16px; font-size: 10.5px;
  color: var(--dpr-text-muted) !important; margin-top: 4px;
}
.dpr-ratio-dot {
  display: inline-block; width: 8px; height: 8px;
  border-radius: 2px; margin-right: 6px; vertical-align: middle;
}

.dpr-histogram {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px; align-items: end;
  height: 160px; margin-top: 4px;
}
.dpr-hist-col {
  display: flex; flex-direction: column;
  align-items: center; gap: 6px; height: 100%;
}
.dpr-hist-bar-wrap { flex: 1; display: flex; align-items: flex-end; width: 100%; min-height: 0; }
.dpr-hist-bar {
  width: 100%;
  background: linear-gradient(180deg, var(--dpr-primary), var(--dpr-primary-dim));
  border-radius: 4px 4px 2px 2px;
  min-height: 3px; transition: opacity .12s ease;
}
.dpr-hist-bar:hover { opacity: 0.85; }
.dpr-hist-value { color: var(--dpr-text) !important; font-size: 12px; font-weight: 700; }
.dpr-hist-label {
  color: var(--dpr-text-muted) !important;
  font-size: 10px; letter-spacing: 0.06em;
  text-transform: uppercase; text-align: center; line-height: 1.2;
}

.dpr-matrix { display: grid; gap: 2px; font-size: 11px; overflow-x: auto; }
.dpr-matrix-cell {
  padding: 6px 8px; text-align: center;
  border-radius: 4px; color: var(--dpr-text) !important;
  font-weight: 500; min-width: 56px;
}
.dpr-matrix-head {
  color: var(--dpr-text-muted) !important;
  font-size: 10px; letter-spacing: 0.06em;
  text-transform: uppercase; font-weight: 600;
  padding: 6px 8px; text-align: center; white-space: nowrap;
}
.dpr-matrix-row-head {
  color: var(--dpr-text) !important;
  font-size: 11px; font-weight: 600;
  padding: 6px 10px 6px 0;
  text-align: left; white-space: nowrap;
}

.dpr-toplist { display: flex; flex-direction: column; gap: 0; }
.dpr-toplist-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--dpr-border);
  font-size: 12.5px;
}
.dpr-toplist-row:last-child { border-bottom: none; }
.dpr-toplist-rank {
  color: var(--dpr-text-dim) !important;
  font-size: 11px; font-weight: 700; min-width: 20px;
}
.dpr-toplist-name {
  flex: 1; color: var(--dpr-text) !important; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.dpr-toplist-value {
  color: var(--dpr-primary) !important;
  font-weight: 700; font-size: 12.5px;
}

.dpr-download-bar {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px;
  background: var(--dpr-primary-soft);
  border: 1px solid var(--dpr-border-hover);
  border-radius: var(--dpr-radius);
  padding: 14px 18px; margin: 0; flex-wrap: wrap;
}
.dpr-download-bar-label {
  color: var(--dpr-text) !important;
  font-size: 12.5px; font-weight: 600;
}
.dpr-download-bar-label small {
  color: var(--dpr-text-muted) !important;
  font-weight: 400; display: block;
  margin-top: 3px; font-size: 11px;
}

.dpr-meta-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px;
  background: var(--dpr-border);
  border: 1px solid var(--dpr-border);
  border-radius: var(--dpr-radius-sm);
  overflow: hidden;
}
.dpr-meta-item { background: var(--dpr-surface); padding: 12px 14px; }
.dpr-meta-label {
  color: var(--dpr-text-muted) !important;
  font-size: 10.5px; letter-spacing: 0.1em;
  text-transform: uppercase; font-weight: 600; margin-bottom: 6px;
}
.dpr-meta-value {
  color: var(--dpr-text) !important;
  font-size: 13px; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.dpr-section-subtitle {
  color: var(--dpr-text-muted) !important;
  font-size: 11.5px; line-height: 1.55;
  margin: 4px 0 14px 0; max-width: 640px;
}
</style>
"""


def apply_theme() -> None:
    ui.add_head_html(CSS, shared=True)

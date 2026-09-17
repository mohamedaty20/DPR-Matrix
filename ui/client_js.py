"""Client-side JS injections.

Two pieces:

1. Drag-to-close for the report sidebar (`.dpr-proj-sidebar`).
   Watches touchstart/mousedown on the sidebar itself. If the user drags
   left by >50px, we click the toggle button (`.dpr-proj-toggle`) so
   NiceGUI's own state machinery runs — no duplicated open/close logic.

2. /ping keepalive every 25s. Render's free-tier proxy drops idle
   websockets after ~15 min; this keeps the HTTP side warm while any
   browser tab has the app open. ~40 bytes per ping.
"""
from __future__ import annotations

from nicegui import ui


JS = """
<script>
(function () {
    if (window.__dprClientInstalled) return;
    window.__dprClientInstalled = true;

    // ── 1. Drag-to-close the report sidebar ──────────────────────────
    function installDrag() {
        document.querySelectorAll('.dpr-proj-sidebar').forEach(function (sb) {
            if (sb.__dprDragBound) return;
            sb.__dprDragBound = true;

            var startX = 0;
            var dragging = false;

            function down(x) {
                startX = x;
                dragging = true;
            }
            function move(x) {
                if (!dragging) return;
                var dx = x - startX;
                if (dx < -50) {
                    var btn = sb.querySelector('.dpr-proj-toggle');
                    if (btn && typeof btn.click === 'function') btn.click();
                    dragging = false;
                }
            }
            function up() { dragging = false; }

            // Touch
            sb.addEventListener('touchstart', function (e) {
                if (e.touches && e.touches.length === 1) down(e.touches[0].clientX);
            }, { passive: true });
            sb.addEventListener('touchmove', function (e) {
                if (e.touches && e.touches.length === 1) move(e.touches[0].clientX);
            }, { passive: true });
            sb.addEventListener('touchend', up);

            // Mouse
            sb.addEventListener('mousedown', function (e) {
                if (e.target.closest('input,textarea,button,select,.q-field,.q-btn,.q-uploader'))
                    return;
                down(e.clientX);
            });
            document.addEventListener('mousemove', function (e) {
                move(e.clientX);
            });
            document.addEventListener('mouseup', up);
        });
    }

    installDrag();
    // NiceGUI swaps DOM per page nav — re-bind on mutation.
    new MutationObserver(installDrag).observe(document.body, {
        childList: true, subtree: true
    });

    // ── 2. Connection keepalive ──────────────────────────────────────
    // Tiny GET every 25s. Keeps Render's proxy from dropping the HTTP
    // side; fails silently if the server is waking up.
    function keepAlive() {
        try {
            fetch('/ping', { method: 'GET', cache: 'no-store' })
                .catch(function () { /* ignore */ });
        } catch (e) { /* ignore */ }
    }
    setInterval(keepAlive, 25000);
    // Fire once after a short delay so we don't race the initial page load.
    setTimeout(keepAlive, 3000);
})();
</script>
"""


def install() -> None:
    """Inject the client JS once at boot. Safe to call multiple times."""
    ui.add_head_html(JS, shared=True)

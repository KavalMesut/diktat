// KDE Plasma 6 / KWin Wayland helper for Diktat's frameless recording HUD.
// Wayland deliberately ignores client-requested top-level window positions;
// placement must therefore be performed by the compositor.
const marginX = 12;
const marginY = 10;
let lastNonHudWindow = workspace.activeWindow;

function mainOutput() {
    // This workstation's middle/main monitor.  Keep a generic center-screen
    // fallback so the development branch remains usable on another layout.
    for (const output of workspace.screens) {
        if (output.name === "DP-2") {
            return output;
        }
    }

    const virtualArea = workspace.virtualScreenGeometry;
    const centerX = virtualArea.x + virtualArea.width / 2;
    const centerY = virtualArea.y + virtualArea.height / 2;
    for (const output of workspace.screens) {
        const geometry = output.geometry;
        if (centerX >= geometry.x && centerX < geometry.x + geometry.width &&
            centerY >= geometry.y && centerY < geometry.y + geometry.height) {
            return output;
        }
    }
    return workspace.activeScreen;
}

function placeHud(window) {
    if (window.caption !== "Diktat HUD") {
        return;
    }
    // Keep the HUD on the physical middle/main screen even when the cursor or
    // focused window is on one of the side monitors.
    const output = mainOutput();
    const desktop = workspace.currentDesktopForScreen(output);
    const area = workspace.clientArea(KWin.WorkArea, output, desktop);
    window.keepAbove = true;
    window.skipTaskbar = true;
    window.skipPager = true;
    window.skipSwitcher = true;
    const target = {
        x: area.x + area.width - window.width - marginX,
        y: area.y + area.height - window.height - marginY,
        width: window.width,
        height: window.height
    };
    const current = window.frameGeometry;
    if (current.x !== target.x || current.y !== target.y) {
        window.frameGeometry = target;
    }
}

workspace.windowAdded.connect(function(window) {
    if (window.caption !== "Diktat HUD") {
        return;
    }
    placeHud(window);
    window.frameGeometryChanged.connect(function() {
        placeHud(window);
    });
});

workspace.windowActivated.connect(function(window) {
    if (window && window.caption !== "Diktat HUD") {
        lastNonHudWindow = window;
        return;
    }
    if (window && window.caption === "Diktat HUD" && lastNonHudWindow) {
        workspace.activeWindow = lastNonHudWindow;
    }
});

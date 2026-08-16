"""
Backward compatibility layer for legacy dikte_app imports.
Directs to windows.diktat_app.
"""
from .diktat_app import (
    DiktatApplication,
    DikteApplication,
    SettingsDialog,
    FloatingHUD,
    AudioRecorder,
    GlobalKeyListener,
    AppSignals,
    windows_paste,
)

if __name__ == "__main__":
    app = DiktatApplication()
    app.run()

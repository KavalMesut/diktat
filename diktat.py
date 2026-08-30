"""
Diktat - Zero-Friction AI Voice Dictation (Cross-Platform: Windows & Linux / CachyOS)
Global Shortcut: Ctrl + Space (or `diktat --toggle` from any window manager/compositor)
"""
import sys
from pathlib import Path

# Ensure root package is in path
sys.path.insert(0, str(Path(__file__).parent))

def send_ipc_command(command: str) -> bool:
    """Send command to running Diktat instance via local socket/named pipe."""
    try:
        from PyQt6.QtCore import QCoreApplication
        from PyQt6.QtNetwork import QLocalSocket
        
        qt_app = QCoreApplication.instance()
        if not qt_app:
            qt_app = QCoreApplication(sys.argv)
            
        socket = QLocalSocket()
        socket.connectToServer("diktat_ipc_socket")
        if socket.waitForConnected(400):
            socket.write((command + "\n").encode("utf-8"))
            socket.waitForBytesWritten(400)
            socket.disconnectFromServer()
            return True
    except Exception as e:
        pass
    return False

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--toggle" in args:
        if send_ipc_command("toggle"):
            sys.exit(0)
    elif "--cancel" in args:
        if send_ipc_command("cancel"):
            sys.exit(0)
    elif "--settings" in args or "--show" in args:
        if send_ipc_command("settings"):
            sys.exit(0)
    elif "--help" in args or "-h" in args:
        print("Diktat - AI Voice Dictation")
        print("Usage:")
        print("  diktat             Start Diktat background application")
        print("  diktat --toggle    Toggle recording on running instance (useful for Wayland / i3 / Hyprland)")
        print("  diktat --cancel    Cancel current recording")
        print("  diktat --settings  Open settings dialog")
        sys.exit(0)
        
    # If no flag or not running, start main application
    from windows.diktat_app import DiktatApplication
    app = DiktatApplication()
    app.run()

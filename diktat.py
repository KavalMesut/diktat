"""
Diktat - Zero-Friction AI Voice Dictation for Windows
Global Shortcut: Ctrl + Space
"""
import sys
from pathlib import Path

# Ensure root package is in path
sys.path.insert(0, str(Path(__file__).parent))

from windows.diktat_app import DiktatApplication

if __name__ == "__main__":
    app = DiktatApplication()
    app.run()

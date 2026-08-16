"""
Diktat - Zero-Friction AI Voice Dictation for Windows
Global Shortcut: Ctrl + Space
"""
import sys
from pathlib import Path

# Ensure root package is in path
sys.path.insert(0, str(Path(__file__).parent))

from windows.dikte_app import DikteApplication

if __name__ == "__main__":
    app = DikteApplication()
    app.run()

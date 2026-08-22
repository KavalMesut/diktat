import os
import sys
import json
import shutil
import winreg
from pathlib import Path
from dataclasses import dataclass, asdict

REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "Diktat"

def get_app_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        p = Path(app_data) / "Diktat"
        # Migration from legacy "Dikte" directory if exists and Diktat does not
        legacy_p = Path(app_data) / "Dikte"
        if legacy_p.exists() and not p.exists():
            try:
                shutil.copytree(legacy_p, p)
            except Exception:
                pass
    else:
        p = Path.home() / ".config" / "diktat"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_config_file() -> Path:
    return get_app_dir() / "config.json"

def get_launch_command() -> str:
    """Returns the command line string to launch Diktat in the background on startup."""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        py_exe = sys.executable
        pyw_exe = Path(py_exe).parent / "pythonw.exe"
        runner_exe = str(pyw_exe) if pyw_exe.exists() else py_exe
        
        root_dir = Path(__file__).parent.parent
        main_script = root_dir / "diktat.py"
        if not main_script.exists():
            main_script = Path(__file__).resolve()
        return f'"{runner_exe}" "{main_script.resolve()}"'

def is_autostart_enabled() -> bool:
    """Check if Diktat is registered in Windows startup registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Autostart check error: {e}")
        return False

def set_autostart(enable: bool) -> bool:
    """Add or remove Diktat from Windows startup registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"Autostart set error: {e}")
        return False

def load_env_file():
    """Load API keys from .env if present in bundle, current dir, exe dir or appdata."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).parent.parent / ".env",
        Path(sys.executable).parent / ".env" if getattr(sys, 'frozen', False) else None,
        Path(getattr(sys, '_MEIPASS', '')) / ".env" if getattr(sys, 'frozen', False) else None,
        get_app_dir() / ".env"
    ]
    for p in candidates:
        if p and p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("\"'")
                            if k and not os.environ.get(k):
                                os.environ[k] = v
            except Exception:
                pass

load_env_file()

DEFAULT_CONFIG = {
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    "provider": "local",  # "local", "gemini", or "openai"
    "local_llm_model": "qwen2.5-3b",  # "qwen2.5-3b" or "qwen3-4b"
    "language": "tr",       # "tr", "en", "auto"
    "ui_language": "tr",
    "hotkey": "ctrl+space",
    "cancel_hotkey": "ctrl+alt+space",
    "auto_start": False,
    "auto_paste": True,
    "play_sound": True,
    "overlay_corner": "bottom-right",  # "bottom-right", "bottom-left", "top-right", "top-left"
    "glossary": "Kubernetes, Grafana, PyQt, OpenAI, Claude, Whisper, Gemini",
    "silence_db": -50.0,
    "sample_rate": 16000,
    "max_duration_seconds": 300,
    "cleanup_enabled": True
}

class ConfigManager:
    def __init__(self):
        self.config_path = get_config_file()
        self.config = self.load()

    def load(self) -> dict:
        config = dict(DEFAULT_CONFIG)
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    config.update(data)
            except Exception as e:
                print(f"Config load error: {e}")
        # Always fallback to env if keys empty
        if not config.get("gemini_api_key") and os.environ.get("GEMINI_API_KEY"):
            config["gemini_api_key"] = os.environ.get("GEMINI_API_KEY", "")
        if not config.get("openai_api_key") and os.environ.get("OPENAI_API_KEY"):
            config["openai_api_key"] = os.environ.get("OPENAI_API_KEY", "")
        return config

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Config save error: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

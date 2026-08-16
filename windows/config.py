import os
import json
from pathlib import Path
from dataclasses import dataclass, asdict

def get_app_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if app_data:
        p = Path(app_data) / "Dikte"
    else:
        p = Path.home() / ".config" / "dikte"
    p.mkdir(parents=True, exist_ok=True)
    return p

def get_config_file() -> Path:
    return get_app_dir() / "config.json"

def load_env_file():
    """Load API keys from .env if present in bundle, current dir, exe dir or appdata."""
    import sys
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
    "provider": "gemini",  # "gemini" or "openai"
    "language": "tr",       # "tr", "en", "auto"
    "ui_language": "tr",
    "hotkey": "ctrl+space",
    "cancel_hotkey": "ctrl+alt+space",
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

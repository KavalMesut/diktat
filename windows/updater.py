"""
Diktat - Otomatik Güncelleme & Bildirim Modülü (Cross-Platform Auto-Updater)
Windows ve Linux (CachyOS/Arch/Ubuntu) için GitHub senkronizasyonu ve tek tıkla güncelleme.
"""

import sys
import os
import subprocess
import json
import urllib.request
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

GITHUB_API_URL = "https://api.github.com/repos/KavalMesut/diktat/commits/main"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def get_local_commit() -> Optional[str]:
    """Mevcut yerel git commit hash'ini alır."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass

    # Alternatif: .git klasöründen doğrudan oku
    git_head_file = PROJECT_ROOT / ".git" / "HEAD"
    if git_head_file.exists():
        try:
            ref = git_head_file.read_text(encoding="utf-8").strip()
            if ref.startswith("ref:"):
                ref_path = PROJECT_ROOT / ".git" / ref.split(" ", 1)[1].strip()
                if ref_path.exists():
                    return ref_path.read_text(encoding="utf-8").strip()
            else:
                return ref
        except Exception:
            pass
    return None

def check_for_updates() -> Dict[str, Any]:
    """
    GitHub reposunu kontrol eder. Yeni commit varsa detayları döndürür.
    Zaman aşımı 5 saniyedir ve sistemi asla dondurmaz.
    """
    local_sha = get_local_commit()
    result = {
        "update_available": False,
        "local_sha": local_sha[:7] if local_sha else "bilinmiyor",
        "remote_sha": "",
        "message": "",
        "author": "",
        "date": "",
        "error": None
    }

    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "User-Agent": "Diktat-AutoUpdater",
            "Accept": "application/vnd.github.v3+json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                remote_sha = data.get("sha", "")
                commit_info = data.get("commit", {})
                message = commit_info.get("message", "").split("\n")[0]
                author = commit_info.get("author", {}).get("name", "Geliştirici")
                date = commit_info.get("author", {}).get("date", "")

                result["remote_sha"] = remote_sha[:7] if remote_sha else ""
                result["message"] = message
                result["author"] = author
                result["date"] = date

                if local_sha and remote_sha:
                    if not remote_sha.startswith(local_sha) and not local_sha.startswith(remote_sha):
                        result["update_available"] = True
                elif remote_sha:
                    # Yerel git bilgisi okunamasa bile uzaktaki son sürüm mesajını ver
                    result["update_available"] = True
    except Exception as e:
        result["error"] = str(e)

    return result

def apply_update() -> Tuple[bool, str]:
    """
    Projeyi en son sürüme günceller (git pull veya update.sh çalıştırır).
    """
    try:
        if sys.platform != "win32":
            update_sh = PROJECT_ROOT / "update.sh"
            if update_sh.exists():
                subprocess.run(["chmod", "+x", str(update_sh)], check=False)
                res = subprocess.run(
                    ["/bin/bash", str(update_sh)],
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=60
                )
                if res.returncode == 0:
                    return True, "Linux güncellemesi başarıyla tamamlandı."
                return False, res.stderr or res.stdout

        # Genel git pull
        res = subprocess.run(
            ["git", "pull"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=45
        )
        if res.returncode == 0:
            return True, "Kodlar başarıyla güncellendi."
        else:
            return False, res.stderr or res.stdout
    except Exception as e:
        return False, str(e)

def restart_diktat():
    """Mevcut Diktat uygulamasını kapatıp güncel sürümüyle yeniden başlatır."""
    try:
        main_script = PROJECT_ROOT / "diktat.py"
        if getattr(sys, 'frozen', False):
            # PyInstaller binary
            subprocess.Popen([sys.executable])
        else:
            subprocess.Popen([sys.executable, str(main_script)])
    except Exception as e:
        print(f"Restart error: {e}")
    finally:
        sys.exit(0)

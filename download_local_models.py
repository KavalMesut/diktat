import os
import sys
from pathlib import Path
from huggingface_hub import hf_hub_download
from faster_whisper import WhisperModel

# Ensure root package is in path
sys.path.insert(0, str(Path(__file__).parent))
from windows.config import get_app_dir

def download_models():
    models_dir = get_app_dir() / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("1/2: Downloading / Caching faster-whisper (large-v3-turbo)...")
    print("==================================================")
    whisper_model = WhisperModel(
        "large-v3-turbo",
        device="cuda",
        compute_type="float16",
        download_root=str(models_dir / "whisper")
    )
    print("Faster-Whisper (large-v3-turbo) successfully initialized on CUDA!")

    print("\n==================================================")
    print("2/3: Downloading Qwen 2.5 3B Instruct 4-bit GGUF...")
    print("==================================================")
    qwen_path = hf_hub_download(
        repo_id="Qwen/Qwen2.5-3B-Instruct-GGUF",
        filename="qwen2.5-3b-instruct-q4_k_m.gguf",
        local_dir=str(models_dir / "llm")
    )
    print(f"Qwen 2.5 3B GGUF downloaded to: {qwen_path}")

    print("\n==================================================")
    print("3/3: Downloading Qwen3 4B Instruct 2507 4-bit GGUF...")
    print("==================================================")
    qwen3_path = hf_hub_download(
        repo_id="unsloth/Qwen3-4B-Instruct-2507-GGUF",
        filename="Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
        local_dir=str(models_dir / "llm")
    )
    print(f"Qwen3 4B GGUF downloaded to: {qwen3_path}")

    print("\nAll local AI models (Whisper + Qwen 2.5 3B + Qwen3 4B) downloaded and verified successfully!")

if __name__ == "__main__":
    download_models()

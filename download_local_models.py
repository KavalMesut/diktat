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
    try:
        whisper_model = WhisperModel(
            "large-v3-turbo",
            device="cuda",
            compute_type="float16",
            download_root=str(models_dir / "whisper")
        )
        print("Faster-Whisper (large-v3-turbo) successfully initialized on CUDA!")
    except Exception as e:
        print(f"CUDA initialization failed ({e}), falling back to CPU...")
        whisper_model = WhisperModel(
            "large-v3-turbo",
            device="cpu",
            compute_type="int8",
            download_root=str(models_dir / "whisper")
        )
        print("Faster-Whisper (large-v3-turbo) initialized on CPU.")

    print("\n==================================================")
    print("2/2: Downloading Google Gemma 3 4B Instruct 4-bit GGUF...")
    print("==================================================")
    gemma_path = hf_hub_download(
        repo_id="ggml-org/gemma-3-4b-it-GGUF",
        filename="gemma-3-4b-it-Q4_K_M.gguf",
        local_dir=str(models_dir / "llm")
    )
    print(f"Google Gemma 3 4B GGUF downloaded to: {gemma_path}")

    print("\nAll local AI models (Faster-Whisper + Google Gemma 3 4B) verified successfully!")

if __name__ == "__main__":
    download_models()

import os
import sys
import time
import threading
from pathlib import Path
import numpy as np

from .config import get_app_dir
from .prompts import CLEANUP_PROMPT_TR, CLEANUP_PROMPT_EN

# Optional imports handled gracefully
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

try:
    import llama_cpp
except ImportError:
    llama_cpp = None

class LocalAIEngine:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, config=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config)
            elif config:
                cls._instance.config = config
            return cls._instance

    def __init__(self, config=None):
        self.config = config or {}
        self.whisper_model = None
        self.llm_model = None
        self._is_loading = False
        self._load_lock = threading.Lock()
        self._ready_event = threading.Event()

    def get_models_dir(self) -> Path:
        p = get_app_dir() / "models"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_whisper_dir(self) -> Path:
        p = self.get_models_dir() / "whisper"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_llm_path(self) -> Path:
        p = self.get_models_dir() / "llm" / "qwen2.5-3b-instruct-q4_k_m.gguf"
        return p

    def is_available(self) -> bool:
        """Check if local dependencies and models are present."""
        if WhisperModel is None or llama_cpp is None:
            return False
        return self.get_llm_path().exists()

    def preload_in_background(self):
        """Asynchronously warm up and load models into VRAM."""
        threading.Thread(target=self._ensure_models_loaded, daemon=True).start()

    def _ensure_models_loaded(self):
        with self._load_lock:
            if self.whisper_model is not None and self.llm_model is not None:
                self._ready_event.set()
                return

            self._is_loading = True
            models_dir = self.get_models_dir()

            # 1. Load Whisper
            if self.whisper_model is None and WhisperModel is not None:
                try:
                    whisper_dir = self.get_whisper_dir()
                    # Use CUDA if available, fallback to CPU
                    device = "cuda"
                    compute_type = "float16"
                    try:
                        self.whisper_model = WhisperModel(
                            "large-v3-turbo",
                            device=device,
                            compute_type=compute_type,
                            download_root=str(whisper_dir)
                        )
                    except Exception as e:
                        print(f"Whisper CUDA init error, falling back to CPU: {e}")
                        self.whisper_model = WhisperModel(
                            "large-v3-turbo",
                            device="cpu",
                            compute_type="int8",
                            download_root=str(whisper_dir)
                        )
                except Exception as e:
                    print(f"Failed to load local Whisper: {e}")

            # 2. Load Qwen LLM
            if self.llm_model is None and llama_cpp is not None:
                try:
                    llm_path = self.get_llm_path()
                    if llm_path.exists():
                        self.llm_model = llama_cpp.Llama(
                            model_path=str(llm_path),
                            n_gpu_layers=-1,  # Offload all layers to RTX 4060 Ti GPU
                            n_ctx=2048,
                            verbose=False
                        )
                        # Warm up 1 token
                        self.llm_model.create_chat_completion(
                            messages=[{"role": "user", "content": "hi"}],
                            max_tokens=1
                        )
                    else:
                        print(f"Local Qwen model not found at: {llm_path}")
                except Exception as e:
                    print(f"Failed to load local Qwen LLM: {e}")

            self._is_loading = False
            self._ready_event.set()

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "tr", glossary: str = "") -> str:
        self._ensure_models_loaded()
        if self.whisper_model is None:
            raise RuntimeError("Local Whisper model is not loaded.")

        # Ensure float32 mono audio
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        lang_arg = None if language == "auto" else language
        
        # Turkish-optimized priming prompt to guide capitalization and punctuation
        if language == "tr":
            base_prompt = "Merhaba. Diktat ile Türkçe sesli dikte yapıyorum. Noktalama işaretlerine, büyük/küçük harflere ve Türkçe karakterlere (ç, ğ, ı, ö, ş, ü) dikkat et."
            prompt_arg = f"{base_prompt} {glossary}".strip() if glossary else base_prompt
        elif language == "en":
            base_prompt = "Hello. Dictating in English with correct capitalization and punctuation."
            prompt_arg = f"{base_prompt} {glossary}".strip() if glossary else base_prompt
        else:
            prompt_arg = glossary if glossary else None

        segments, info = self.whisper_model.transcribe(
            audio_data,
            beam_size=3,  # Optimized beam search for Turkish suffix accuracy on RTX 4060 Ti
            best_of=3,
            temperature=0.0,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            language=lang_arg,
            initial_prompt=prompt_arg,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=350,
                speech_pad_ms=200,
                threshold=0.45
            )
        )

        texts = [segment.text.strip() for segment in segments if segment.text.strip()]
        return " ".join(texts).strip()

    def cleanup_text(self, raw_text: str, language: str = "tr", glossary: str = "") -> str:
        if not raw_text or not raw_text.strip():
            return ""

        self._ensure_models_loaded()
        if self.llm_model is None:
            return raw_text

        prompt = CLEANUP_PROMPT_TR if language == "tr" else CLEANUP_PROMPT_EN
        if glossary:
            prompt += f"\n\nÖZEL İSİMLER VE TERİMLER (MUTLAKA BU ŞEKİLDE YAZ):\n{glossary}"

        system_instruction = f"{prompt}\n\nSADECE temizlenmiş metni döndür, başka hiçbir açıklama veya markdown bloğu yazma."
        
        tag = "konusma" if language == "tr" else "speech"
        user_content = f"<{tag}>{raw_text.strip()}</{tag}>"

        try:
            response = self.llm_model.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0,      # Deterministic dictation formatting
                top_p=0.9,
                repeat_penalty=1.1,   # Prevents repetitive chat babble
                max_tokens=512,
                stop=["<|im_end|>", "<|endoftext|>", "\n\n", "<|im_start|>"]
            )
            cleaned = response["choices"][0]["message"]["content"].strip()
            
            # Remove any markdown backticks or tags
            if cleaned.startswith("```") and cleaned.endswith("```"):
                cleaned = "\n".join(cleaned.splitlines()[1:-1]).strip()
            
            cleaned = cleaned.replace("<konusma>", "").replace("</konusma>", "")
            cleaned = cleaned.replace("<speech>", "").replace("</speech>", "").strip()
            if cleaned.startswith('"') and cleaned.endswith('"'):
                cleaned = cleaned[1:-1].strip()

            # Anti-conversational hallucination guard
            hallucination_indicators = [
                "özür dilerim", "üzgünüm", "verilen metni analiz", "yardımcı olabilirim",
                "lütfen verilen metn", "nasıl yardımcı", "i apologize", "as an ai", "how can i help"
            ]
            lower_clean = cleaned.lower()
            lower_raw = raw_text.lower()
            is_hallucination = any(h in lower_clean and h not in lower_raw for h in hallucination_indicators)

            if is_hallucination or (len(cleaned) > 2.5 * len(raw_text) and len(raw_text) > 10):
                print(f"[Diktat] LLM sohbet halüsinasyonu yakalandı, ham ses dökümüne dönülüyor:\n  Ham: '{raw_text}'\n  LLM: '{cleaned}'")
                return raw_text

            return cleaned if cleaned else raw_text
        except Exception as e:
            print(f"Local Qwen cleanup error: {e}")
            return raw_text

    def transcribe_and_cleanup(self, audio_data: np.ndarray, sample_rate: int = 16000, language: str = "tr", glossary: str = "", cleanup_enabled: bool = True) -> tuple[str, str]:
        raw_text = self.transcribe(audio_data, sample_rate=sample_rate, language=language, glossary=glossary)
        if not raw_text:
            return "", ""

        if cleanup_enabled:
            cleaned_text = self.cleanup_text(raw_text, language=language, glossary=glossary)
        else:
            cleaned_text = raw_text

        return raw_text, cleaned_text

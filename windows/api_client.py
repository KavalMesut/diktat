import base64
import json
import io
import requests
import soundfile as sf
import numpy as np
from .prompts import CLEANUP_PROMPT_TR, CLEANUP_PROMPT_EN
from .local_engine import LocalAIEngine

class AIClient:
    def __init__(self, config: dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "aistudio-build",
            "Content-Type": "application/json"
        })
        self.local_engine = LocalAIEngine.get_instance(config)

    def audio_to_wav_bytes(self, audio_data: np.ndarray, sample_rate: int = 16000) -> bytes:
        """Convert float32 array to compact 16-bit PCM WAV bytes."""
        buffer = io.BytesIO()
        sf.write(buffer, audio_data, sample_rate, format='WAV', subtype='PCM_16')
        return buffer.getvalue()

    def transcribe_and_cleanup(self, audio_data: np.ndarray, sample_rate: int = 16000) -> tuple[str, str]:
        """
        Processes audio using configured provider:
        - "local": RTX 4060 Ti GPU Faster-Whisper + Qwen 2.5 3B (Offline)
        - "gemini": Google Gemini 3.7 Flash
        - "openai": OpenAI Whisper + GPT-4o-mini
        """
        provider = self.config.get("provider", "local")
        lang = self.config.get("language", "tr")
        glossary = self.config.get("glossary", "")
        cleanup_enabled = self.config.get("cleanup_enabled", True)

        # 1. Local AI Engine (RTX 4060 Ti CUDA)
        if provider == "local":
            try:
                return self.local_engine.transcribe_and_cleanup(
                    audio_data,
                    sample_rate=sample_rate,
                    language=lang,
                    glossary=glossary,
                    cleanup_enabled=cleanup_enabled
                )
            except Exception as e:
                print(f"Local AI Engine execution error: {e}")
                # Fallback to Gemini if API key exists
                if self.config.get("gemini_api_key"):
                    print("Falling back to Gemini Flash...")
                    wav_bytes = self.audio_to_wav_bytes(audio_data, sample_rate)
                    cleaned = self._single_pass_gemini(wav_bytes)
                    if cleaned:
                        return cleaned, cleaned

        # 2. Single-Pass Ultra-Fast Gemini
        elif provider == "gemini":
            wav_bytes = self.audio_to_wav_bytes(audio_data, sample_rate)
            api_key = self.config.get("gemini_api_key")
            if api_key:
                try:
                    cleaned = self._single_pass_gemini(wav_bytes)
                    if cleaned:
                        return cleaned, cleaned
                except Exception as e:
                    print(f"Gemini single-pass failed: {e}")

        # 3. OpenAI Whisper + GPT-4o-mini
        elif provider == "openai":
            wav_bytes = self.audio_to_wav_bytes(audio_data, sample_rate)
            if self.config.get("openai_api_key"):
                try:
                    raw = self._transcribe_openai(wav_bytes)
                    cleaned = self._cleanup_openai(raw) if cleanup_enabled else raw
                    return raw, cleaned
                except Exception as e:
                    print(f"OpenAI pipeline failed: {e}")

        return "", ""

    def _single_pass_gemini(self, wav_bytes: bytes) -> str:
        api_key = self.config.get("gemini_api_key")
        b64_audio = base64.b64encode(wav_bytes).decode('utf-8')
        lang = self.config.get("language", "tr")
        glossary = self.config.get("glossary", "")

        cleanup_prompt = CLEANUP_PROMPT_TR if lang == "tr" else CLEANUP_PROMPT_EN
        if glossary:
            cleanup_prompt += f"\n\nÖZEL İSİMLER VE TERİMLER (MUTLAKA BU ŞEKİLDE YAZ):\n{glossary}"

        system_instruction = f"""{cleanup_prompt}

SESLİ DİKTE GÖREVİ:
Sana verilen ses kaydını dinle ve yukarıdaki temizleme kurallarına (düşünme seslerini, dolguları sil, noktalama ekle, teknik terimleri koru) harfiyen uyarak DOĞRUDAN TEMİZLENMİŞ VE YAYINA HAZIR METİN olarak yaz.
SADECE temizlenmiş nihai metni döndür, başka hiçbir açıklama veya markdown bloğu yazma."""

        # High-speed flash model candidates
        models = ["gemini-3.7-flash", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]

        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/wav",
                                    "data": b64_audio
                                }
                            },
                            {
                                "text": "Bu ses kaydını dinle ve doğrudan temizlenmiş metni yaz."
                            }
                        ]
                    }
                ],
                "systemInstruction": {
                    "parts": [{"text": system_instruction}]
                },
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 2048
                }
            }

            try:
                resp = self.session.post(url, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "").strip()
                            if text:
                                return text
            except Exception:
                pass

        return ""

    def _transcribe_openai(self, wav_bytes: bytes) -> str:
        api_key = self.config.get("openai_api_key")
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        lang = self.config.get("language", "tr")
        prompt = self.config.get("glossary", "")

        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"model": "whisper-1"}
        if lang and lang != "auto":
            data["language"] = lang
        if prompt:
            data["prompt"] = prompt

        resp = self.session.post(url, headers=headers, files=files, data=data, timeout=12)
        if resp.status_code == 200:
            return resp.json().get("text", "").strip()
        return ""

    def _cleanup_openai(self, raw_text: str) -> str:
        api_key = self.config.get("openai_api_key")
        lang = self.config.get("language", "tr")
        prompt = CLEANUP_PROMPT_TR if lang == "tr" else CLEANUP_PROMPT_EN

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"<transcript>\n{raw_text}\n</transcript>"}
            ],
            "temperature": 0.1
        }
        resp = self.session.post(url, headers=headers, json=payload, timeout=8)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return raw_text

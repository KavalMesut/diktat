import time
import numpy as np
from faster_whisper import WhisperModel
import llama_cpp
from windows.config import get_app_dir
from windows.prompts import CLEANUP_PROMPT_TR

def test_pipeline():
    models_dir = get_app_dir() / "models"
    llm_path = models_dir / "llm" / "gemma-3-4b-it-Q4_K_M.gguf"
    whisper_dir = models_dir / "whisper"

    print("1. Initializing Whisper on CUDA...")
    t0 = time.time()
    whisper = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16", download_root=str(whisper_dir))
    print(f"   Whisper loaded in {time.time() - t0:.2f}s")

    print("\n2. Initializing Gemma 3 4B (4-bit) on CUDA (n_gpu_layers=-1)...")
    t0 = time.time()
    llm = llama_cpp.Llama(model_path=str(llm_path), n_gpu_layers=-1, n_ctx=2048, verbose=False)
    print(f"   Gemma loaded in {time.time() - t0:.2f}s")

    # Test Gemma text cleanup
    test_raw_text = "ıı ben şey bugün saat beşte toplantıya hani gidecektim ama yani iptal oldu"
    print(f"\n3. Testing Gemma cleanup on text: '{test_raw_text}'")
    t0 = time.time()
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": CLEANUP_PROMPT_TR},
            {"role": "user", "content": test_raw_text}
        ],
        temperature=0.1,
        max_tokens=256
    )
    cleaned = response["choices"][0]["message"]["content"].strip()
    inference_time = (time.time() - t0) * 1000
    print(f"   Cleaned result: '{cleaned}'")
    print(f"   Inference took: {inference_time:.1f} ms!")

    # Test Whisper on 2 seconds of synthetic audio (silence/tone)
    print("\n4. Testing Whisper STT on synthetic audio...")
    synthetic_audio = np.zeros(16000 * 2, dtype=np.float32)
    t0 = time.time()
    segments, info = whisper.transcribe(synthetic_audio, language="tr", beam_size=1)
    results = list(segments)
    whisper_time = (time.time() - t0) * 1000
    print(f"   Whisper transcription executed in {whisper_time:.1f} ms (detected lang: {info.language})")

    print("\n>>> LOCAL PIPELINE BENCHMARK COMPLETED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_pipeline()

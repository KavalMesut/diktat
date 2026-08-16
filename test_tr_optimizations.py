import time
from windows.local_engine import LocalAIEngine

def test_turkish_optimizations():
    engine = LocalAIEngine.get_instance()
    print("Loading / warming up engine...")
    engine._ensure_models_loaded()
    print("Models ready!")

    test_sentences = [
        "ıı ben şey bugün saat beşte toplantıya hani gidecektim ama yani iptal oldu",
        "kubernetes ve grafana kullanarak mikroservis mimarisini ayağa kaldırdık mı",
        "ee yarın sabah erkenden istanbuldan ankaraya yola çıkacağız yani öyle planladık",
        "şey bu raporu müdüre ilettin mi yoksa daha onaylanmadı mı"
    ]

    print("\n--- TEST: Turkish LLM Cleanup Quality & Speed ---")
    for s in test_sentences:
        t0 = time.time()
        cleaned = engine.cleanup_text(s, language="tr", glossary="Kubernetes, Grafana, PostgreSQL")
        ms = (time.time() - t0) * 1000
        print(f"\nHam:     {s}")
        print(f"Temiz:   {cleaned}")
        print(f"Süre:    {ms:.1f} ms")

if __name__ == "__main__":
    test_turkish_optimizations()

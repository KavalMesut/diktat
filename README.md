# 🎙️ Dictator — Zero-Friction AI Voice Dictation for Windows

**Dictator**, Windows üzerinde herhangi bir uygulamada (Word, VS Code, Not Defteri, WhatsApp, Chrome, Slack vb.) **`Ctrl + Space`** tuşuna basarak konuştuğunuz her şeyi anında yazıya döken ve yapay zeka ile otomatik temizleyerek imlecinizin durduğu yere yapıştıran ultra hızlı, hafif bir masaüstü asistanıdır.

---

## ✨ Özellikler

- 🚀 **Sıfır Sürtünme (Zero Friction)**: Ekranda gereksiz pencereler açılmaz; arka planda sistem tepsisinde (System Tray) sessizce bekler.
- 🎯 **Doğrudan İmlece Yapıştırma**: İmleciniz neredeyse oraya anında (`Ctrl + V`) yazar.
- ⚡ **Ultra Hızlı (Single-Pass Pipeline)**: Gemini 3.7 Flash / 3.5 Flash Lite motoru ile konuşma biter bitmez milisaniyeler içinde metne çevrilir.
- 🧹 **Akıllı Konuşma Temizleme**: "ıı", "şey", "yani", "hani" gibi düşünme seslerini, kekelemeleri ve tekrarları otomatik siler; noktalama işaretlerini ve büyük harfleri mükemmel ekler.
- 📚 **Özel Terimler Sözlüğü (Glossary)**: Kodlama dilleri, teknik kavramlar (örn. *Kubernetes, Grafana, PyQt, Claude*) ve özel isimleri doğru yazar.
- 🔔 **Sesli & Görsel Geri Bildirim**: Kayıt başladığında/bittiğinde zarif bir bip sesi çalar ve ekranın köşesinde yarı saydam mini kayıt göstergesi belirir.

---

## ⌨️ Kısayol Tuşları

| Kısayol | İşlem |
|---|---|
| **`Ctrl + Space`** | Dikteyi Başlat / Durdur & Yapıştır |
| **`Ctrl + Alt + Space`** | Dikteyi İptal Et |

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler
- Windows 10 / 11
- Python 3.10+ (veya doğrudan `.exe` sürümü)

### 2. Kurulum
```bash
git clone https://github.com/KULLANICI_ADINIZ/dictator.git
cd dictator

pip install -r requirements.txt
```

### 3. API Anahtarı
`.env.example` dosyasını `.env` olarak kopyalayın ve Google AI Studio API anahtarınızı girin:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Çalıştırma
```bash
python dictator.py
# veya
run_dictator.bat
```

---

## 📦 Tek Dosya (.exe) Derleme
İsterseniz Python kurulumu gerektirmeyen bağımsız bir `Dictator.exe` oluşturabilirsiniz:
```bash
build_exe.bat
```
Çıktı dosyası `dist/Dictator.exe` konumunda oluşturulacaktır.

---

## 📄 Lisans
Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

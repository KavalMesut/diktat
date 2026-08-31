# 🎙️ Diktat — Zero-Friction AI Voice Dictation (Cross-Platform)

<p align="center">
  <img src="screenshots/ss1.png" alt="Diktat Ayarlar Arayüzü" width="520" />
</p>

**Diktat**, **Windows 10/11** ve **Linux (CachyOS, Arch, Ubuntu/Debian)** üzerinde herhangi bir uygulamada (Word, VS Code, Not Defteri, WhatsApp, Chrome, Slack vb.) **`Ctrl + Space`** tuşuna basarak konuştuğunuz her şeyi anında yazıya döken ve yapay zeka ile otomatik temizleyerek imlecinizin durduğu yere yapıştıran ultra hızlı, hafif ve çoklu platform bir masaüstü asistanıdır.

---

## ✨ Özellikler

- 🚀 **Sıfır Sürtünme (Zero Friction)**: Ekranda gereksiz pencereler açılmaz; arka planda sistem tepsisinde (System Tray) sessizce bekler.
- 🐧 **Tam Linux & CachyOS Desteği**: PipeWire, Wayland (KDE Plasma, Hyprland, GNOME) ve X11 üzerinde yerel Linux desteği. Kısayol tetikleme için `diktat --toggle` IPC soketi.
- 💻 **%100 Yerel AI Desteği (GPU / CUDA)**: NVIDIA RTX ekran kartınızda çalışan **`faster-whisper (large-v3-turbo)`** ve **`Google Gemma 3 4B Instruct (4-bit GGUF)`** modelleri ile sıfır internet, sıfır kota ve maksimum gizlilik ile tam çevrimdışı çalışma.
- 🎙️ **ReSpeaker XMOS XVF3800 & Far-Field DSP Uyumlu**: Otomatik örnekleme oranı tespiti ve 48 kHz polifaz resampling ile donanımsal gürültü engellemeli mikrofonlarla kusursuz uyum.
- ⚡ **Cümle Bazlı Canlı Dikte (Pipelined Streaming)**: İster tek seferde ister konuşurken eşzamanlı olarak cümle cümle yapıştırma desteği.
- 🎤 **Çoklu Mikrofon Yönetimi**: Bilgisayara bağlı tüm donanımlar arasından dilediğiniz mikrofonu (örn. *ReSpeaker XVF3800*) sabitleme.
- 🎯 **Doğrudan İmlece Yapıştırma**: İmleciniz neredeyse oraya anında (`Ctrl + V`, `wtype`, `xdotool`) yazar.
- 🧹 **Akıllı Konuşma Temizleme (YAP/YAPMA Mimarisi)**: "ıı", "şey", "yani", "hani" gibi düşünme seslerini siler; soru kalıplarına cevap vermez, metne sadık kalarak noktalama işaretlerini ve büyük harfleri ekler.
- 🔄 **Otomatik Başlatma**: Windows Başlangıç veya Linux Autostart (`~/.config/autostart`) desteği.
- 📚 **Özel Terimler Sözlüğü (Glossary)**: Kodlama dilleri, teknik kavramlar ve özel isimleri doğru yazar.
- 🔔 **Sesli & Görsel Geri Bildirim**: Kayıt başladığında/bittiğinde zarif bir ses çalar ve ekranın köşesinde modern mini kayıt göstergesi belirir.

---

## ⌨️ Kısayol Tuşları & Komutlar

| Kısayol / Komut | Platform | İşlem |
|---|---|---|
| **`Ctrl + Space`** | Windows / Linux X11 | Diktatı Başlat / Durdur & Yapıştır |
| **`Ctrl + Alt + Space`** | Windows / Linux X11 | Diktatı İptal Et |
| **`diktat --toggle`** | Linux (Wayland / Hyprland / KDE) | Arka plandaki Diktat kaydını aç/kapa |
| **`diktat --cancel`** | Linux (CLI) | Kaydı iptal et |
| **`diktat --settings`** | Tüm Platformlar | Ayarlar penceresini aç |

---

## 🚀 Hızlı Başlangıç

### 🐧 Linux (CachyOS / Arch / Ubuntu) Kurulumu:
```bash
git clone https://github.com/KavalMesut/diktat.git
cd diktat

# CachyOS / Arch için tek komutla tam kurulum:
chmod +x install_cachyos.sh
./install_cachyos.sh

# Başlatmak için:
./run_diktat.sh
```

> **Hyprland / KDE Plasma Wayland Kısayol Ayarı:**  
> Kısayol yöneticinize komut olarak `~/.local/share/applications/diktat/run_diktat.sh --toggle` (veya `diktat --toggle`) atayarak dilediğiniz tuş kombinasyonuyla (`Super+D`, `Ctrl+Space`) tetikleyebilirsiniz.

---

### 🪟 Windows Kurulumu:
```bash
git clone https://github.com/KavalMesut/diktat.git
cd diktat

pip install -r requirements.txt
python download_local_models.py
python diktat.py
```

---

## 🗺️ Yol Haritası (Roadmap)

- [x] **%100 Çevrimdışı / Yerel Mod**: `faster-whisper (large-v3-turbo)` + `Google Gemma 3 4B Instruct` (llama-cpp CUDA).
- [x] **Çoklu Platform (Linux / CachyOS Desteği)**: Wayland & PipeWire uyumu, IPC socket tetikleyicisi (`--toggle`), XDG standartları.
- [x] **ReSpeaker XMOS XVF3800 Donanım Uyarlaması**: 48 kHz polifaz resampling ve uzak alan desteği.
- [x] **🎤 Çoklu Giriş Mikrofonu Seçimi**: Bağlı tüm aygıtların tespiti ve kalıcı seçim desteği.
- [x] **⚡ Cümle Bazlı Canlı Dikte (Streaming)**: Asenkron kuyruk mimarisiyle konuşurken arka planda temizleyip ardışık yapıştırma.
- [ ] **⏱️ Ayarlanabilir / Sınırsız Kayıt Süresi (Configurable Duration)**: Canlı dikte modu için 15 dk, 30 dk, 1 saat veya limitsiz süre seçeneği ve ayarlar menüsü kontrolü.
- [ ] **🧠 Dinamik Kullanıcı Hafızası & Kişiselleştirme (Stephen Hawking / ACAT Modeli)**: Kullanıcı dikte ettikçe en çok kullandığı teknik terimleri yerel olarak öğrenen akıllı hafıza.
- [ ] **Hibrit Mod (Yerel Whisper STT + Bulut Gemini Flash-Lite LLM)**: Ses tanımanın yerel GPU'da, metin temizlemenin bulutta yapıldığı hibrit mod.
- [ ] **Ses Dosyası Transkripsiyonu**: `.mp3`, `.wav`, `.m4a` dosyalarını sürükle-bırak ile metne dökme.

---

## 📄 Lisans
Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

#!/usr/bin/env bash
# ==============================================================================
# Diktat - CachyOS / Arch Linux Kurulum Scripti
# %100 Yerel AI Sesli Dikte (Faster-Whisper + Google Gemma 3 4B)
# ==============================================================================
set -e

echo "=================================================="
echo "🎙️  Diktat Kurulumu Başlatılıyor (CachyOS / Arch Linux)..."
echo "=================================================="

# 1. Sistem Bağımlılıkları (Pacman / Yay / Paru)
echo -e "\n[1/5] Sistem paketleri kontrol ediliyor..."
PACKAGES=(
    python
    python-pip
    python-virtualenv
    portaudio
    pipewire
    pipewire-pulse
    pipewire-alsa
    xdotool
    wl-clipboard
    wtype
    git
    cmake
    base-devel
)

if command -v pacman &> /dev/null; then
    echo "Arch / CachyOS paket yöneticisi tespit edildi."
    sudo pacman -S --needed --noconfirm "${PACKAGES[@]}"
elif command -v apt &> /dev/null; then
    echo "Debian / Ubuntu paket yöneticisi tespit edildi."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv portaudio19-dev libasound2-dev xdotool wl-clipboard cmake build-essential
else
    echo "⚠️ Bilinmeyen paket yöneticisi. Lütfen portaudio, xdotool ve wl-clipboard paketlerinin kurulu olduğundan emin olun."
fi

# 2. Python Sanal Ortamı (Virtualenv)
echo -e "\n[2/5] Python sanal ortamı (venv) oluşturuluyor..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Pip Güncelleme ve Bağımlılıklar (CUDA Hızlandırmalı)
echo -e "\n[3/5] Python kütüphaneleri ve CUDA hızlandırması kuruluyor..."
pip install --upgrade pip setuptools wheel

# NVIDIA GPU ve çalışan sürücü tespiti
if command -v nvidia-smi &> /dev/null && nvidia-smi &> /dev/null; then
    echo "⚡ NVIDIA GPU tespit edildi! llama-cpp-python CUDA desteğiyle derleniyor..."
    CMAKE_ARGS="-DGGML_CUDA=on" pip install --no-cache-dir llama-cpp-python
    # Faster-Whisper/CTranslate2 loads these shared libraries at runtime.
    pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
else
    echo "ℹ️ Standart CPU kurulumu yapılıyor..."
    pip install llama-cpp-python
fi

pip install -r requirements.txt

# 4. Yerel Yapay Zeka Modellerini İndirme
echo -e "\n[4/5] Yerel yapay zeka modelleri (Whisper + Gemma 3 4B) indiriliyor..."
python download_local_models.py

# 5. Başlatıcı Script ve Masaüstü Kısayolu
echo -e "\n[5/5] Masaüstü kısayolu ve izinler ayarlanıyor..."
chmod +x run_diktat.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat <<EOF > "$DESKTOP_DIR/diktat.desktop"
[Desktop Entry]
Type=Application
Name=Diktat
GenericName=AI Voice Dictation
Comment=Zero-Friction AI Voice Dictation (Ctrl+Space)
Exec=$SCRIPT_DIR/run_diktat.sh
Icon=$SCRIPT_DIR/icon.png
Terminal=false
Categories=Utility;AudioVideo;
Keywords=dictation;speech;whisper;gemma;ai;voice;
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR/diktat.desktop"

echo "=================================================="
echo "✅ Diktat kurulumu başarıyla tamamlandı!"
echo ""
echo "Çalıştırmak için:"
echo "  1. Masaüstü menüsünden 'Diktat' uygulamasını açabilirsiniz."
echo "  2. Veya terminalden: ./run_diktat.sh"
echo "  3. Wayland/KDE/Hyprland kısayolu için komut: $SCRIPT_DIR/run_diktat.sh --toggle"
echo "=================================================="

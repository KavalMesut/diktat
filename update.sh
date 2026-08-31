#!/usr/bin/env bash
# ==============================================================================
# Diktat - Tek Komutla Güncelleme Scripti (Linux / CachyOS)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🔄 Diktat Güncelleniyor..."
echo "=================================================="

# 1. En son kodları GitHub'dan çek
git pull

# 2. Varsa yeni gereksinimleri kontrol et
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt --quiet
fi

# 3. İzinleri yenile
chmod +x run_diktat.sh install_cachyos.sh update.sh 2>/dev/null || true

echo "=================================================="
echo "✅ Diktat başarıyla güncellendi!"
echo "Başlatmak için: ./run_diktat.sh"
echo "=================================================="

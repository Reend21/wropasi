#!/usr/bin/env bash
# install.sh — wropasi yerel kurulum betiği (geliştirme / test için)
#
# Sistem genelinde kurulum (deb/rpm paketi) yapmadan ~/.local altına kurar.
# Kaldırmak için: ./install.sh --uninstall

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${HOME}/.local"

MIME_TYPES=(
    "application/vnd.debian.binary-package"
    "application/x-rpm"
    "application/vnd.snap"
    "application/vnd.flatpak"
    "application/vnd.appimage"
)

# ── Kaldırma ──────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "→ wropasi kaldırılıyor..."
    rm -f  "$PREFIX/bin/wropasi"
    rm -f  "$PREFIX/share/applications/io.github.wropasi.desktop"
    rm -f  "$PREFIX/share/icons/hicolor/256x256/apps/io.github.wropasi.png"
    rm -f  "$PREFIX/share/mime/packages/io.github.wropasi.mime.xml"
    update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
    update-mime-database    "$PREFIX/share/mime"         2>/dev/null || true
    echo "✓ Kaldırıldı."
    exit 0
fi

# ── Kurulum ───────────────────────────────────────────────────────────────────
echo "→ wropasi kuruluyor → $PREFIX"

# Çalıştırılabilir
install -Dm755 "$SCRIPT_DIR/src/wropasi.py" "$PREFIX/bin/wropasi"

# İkon
install -Dm644 "$SCRIPT_DIR/../wropasi-logo.png" \
            "$PREFIX/share/icons/hicolor/256x256/apps/io.github.wropasi.png"

# Desktop dosyası
install -Dm644 "$SCRIPT_DIR/data/io.github.wropasi.desktop" \
            "$PREFIX/share/applications/io.github.wropasi.desktop"

# MIME tanımları
install -Dm644 "$SCRIPT_DIR/data/io.github.wropasi.mime.xml" \
            "$PREFIX/share/mime/packages/io.github.wropasi.mime.xml"

# Veri tabanlarını güncelle
echo "→ Veri tabanları güncelleniyor..."
update-desktop-database "$PREFIX/share/applications" 2>/dev/null \
    && echo "  ✓ desktop-database" || echo "  ⚠ update-desktop-database bulunamadı"

update-mime-database "$PREFIX/share/mime" 2>/dev/null \
    && echo "  ✓ mime-database"    || echo "  ⚠ update-mime-database bulunamadı"

# MIME handling
echo "→ MIME ilişkilendirmeleri ayarlanıyor..."
for mime in "${MIME_TYPES[@]}"; do
    xdg-mime default io.github.wropasi.desktop "$mime" 2>/dev/null \
        && echo "  ✓ $mime" || echo "  ⚠ $mime (xdg-mime başarısız)"
done

echo ""
echo "✓ Kurulum tamamlandı."
echo "  Test: wropasi /path/to/some.rpm"

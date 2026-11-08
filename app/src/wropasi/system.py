"""Sistem paket yöneticisi tespiti, cache ve masaüstü kurulum yardımcıları."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from .constants import APP_ID, DESKTOP_ENTRY, MIME_XML, MIME_TYPES

# -- Paket yöneticisi görüntü adları ------------------------------------------

PM_DISPLAY: dict[str, str] = {
    "dpkg":   "APT/dpkg",
    "rpm":    "RPM",
    "pacman": "Pacman",
    "zypper": "Zypper",
    "dnf":    "DNF",
}

# -- Yardımcılar --------------------------------------------------------------


def _local_prefix() -> Path:
    return Path.home() / ".local"


def _run_quiet(*cmd: str) -> bool:
    """Komutu sessizce çalıştır, başarılıysa True döndür."""
    try:
        subprocess.run(
            cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# -- Cache ---------------------------------------------------------------------


def _cache_path() -> Path:
    """wropasi cache dosyasının yolunu döndür (XDG_CACHE_HOME uyumlu)."""
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "wropasi" / "pm_cache.json"


def _build_cache() -> dict:
    """Sistemdeki paket yöneticilerini ve yardımcı araçları tespit edip cache sözlüğü oluştur."""
    native_pm: str | None = None
    for pm in ("dpkg", "rpm", "pacman", "zypper", "dnf"):
        if shutil.which(pm):
            native_pm = pm
            break

    return {
        "native_pm":   native_pm,
        "has_flatpak": shutil.which("flatpak") is not None,
        "has_snap":    shutil.which("snap") is not None,
        "has_alien":   shutil.which("alien") is not None,
    }


def _write_cache(data: dict) -> None:
    """Cache verisini diske yaz."""
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _read_cache() -> dict | None:
    """Mevcut cache'i oku; dosya yoksa veya bozuksa None döndür."""
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        required = {"native_pm", "has_flatpak", "has_snap", "has_alien"}
        if not required.issubset(data.keys()):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def get_system_info() -> dict:
    """Cache'den sistem bilgilerini al; cache yoksa oluştur."""
    cache = _read_cache()
    if cache is not None:
        return cache
    cache = _build_cache()
    _write_cache(cache)
    return cache


def detect_native_pm() -> str | None:
    return get_system_info()["native_pm"]


def get_native_install_cmd(pkg: str) -> str:
    """Verilen paket adı için yerel paket yöneticisine göre kurulum komutu döner."""
    if shutil.which("zypper"):
        return f"sudo zypper install {pkg}"
    elif shutil.which("dnf"):
        return f"sudo dnf install {pkg}"
    elif shutil.which("apt"):
        return f"sudo apt install {pkg}"
    elif shutil.which("pacman"):
        return f"sudo pacman -S {pkg}"
    elif shutil.which("pkcon"):
        return f"pkcon install {pkg}"

    info = get_system_info()
    native = info.get("native_pm")
    if native == "dpkg":
        return f"sudo apt install {pkg}"
    elif native == "rpm":
        return f"sudo rpm -i {pkg}"
    return f"pkcon install {pkg}"


# -- Masaüstü kurulumu --------------------------------------------------------


def desktop_install() -> None:
    """~/.local altına desktop entry, ikon, MIME XML kur ve ilişkilendir."""
    prefix = _local_prefix()
    src_dir = Path(__file__).resolve().parent      # wropasi/ paket dizini

    # Paket dosyalarını kopyala
    pkg_dest = prefix / "share" / "wropasi" / "wropasi"
    if pkg_dest.exists():
        shutil.rmtree(pkg_dest)
    pkg_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, pkg_dest)
    print(f"  ✓ Paket kopyalandı → {pkg_dest}")

    # Başlatıcı script oluştur
    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "wropasi"
    launcher.write_text(
        "#!/usr/bin/env python3\n"
        "import sys, os\n"
        f"sys.path.insert(0, os.path.expanduser('{prefix / 'share' / 'wropasi'}'))\n"
        "from wropasi.app import main\n"
        "main()\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    exec_path = str(launcher)
    print(f"  ✓ {launcher}")

    # Desktop entry
    desktop_dir = prefix / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / f"{APP_ID}.desktop"
    desktop_file.write_text(
        DESKTOP_ENTRY.format(exec_path=exec_path, icon_name=APP_ID),
        encoding="utf-8",
    )
    print(f"  ✓ {desktop_file}")

    # İkon
    icon_candidates = [
        src_dir.parent.parent.parent / "wropasi-logo.png",   # repo kökü
        src_dir.parent.parent / "wropasi-logo.png",
        Path.cwd() / "wropasi-logo.png",
    ]
    icon_src = next((p for p in icon_candidates if p.exists()), None)
    icon_dst = (
        prefix / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_ID}.png"
    )
    if icon_src:
        icon_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_src, icon_dst)
        print(f"  ✓ {icon_dst}")
    elif icon_dst.exists():
        print(f"  ✓ {icon_dst} (mevcut ikon korundu)")
    else:
        print("  ⚠ İkon bulunamadı: wropasi-logo.png")

    # MIME XML
    mime_dir = prefix / "share" / "mime" / "packages"
    mime_dir.mkdir(parents=True, exist_ok=True)
    mime_file = mime_dir / f"{APP_ID}.mime.xml"
    mime_file.write_text(MIME_XML, encoding="utf-8")
    print(f"  ✓ {mime_file}")

    # Veritabanlarını güncelle
    print("→ Veritabanları güncelleniyor...")
    apps_dir = str(prefix / "share" / "applications")
    mime_base = str(prefix / "share" / "mime")
    icons_dir = str(prefix / "share" / "icons" / "hicolor")
    icon_cache_tool = (
        "gtk4-update-icon-cache"
        if shutil.which("gtk4-update-icon-cache")
        else "gtk-update-icon-cache"
    )
    print(
        "  ✓ desktop-database"
        if _run_quiet("update-desktop-database", apps_dir)
        else "  ⚠ update-desktop-database bulunamadı"
    )
    print(
        "  ✓ mime-database"
        if _run_quiet("update-mime-database", mime_base)
        else "  ⚠ update-mime-database bulunamadı"
    )
    print(
        "  ✓ icon-cache"
        if _run_quiet(icon_cache_tool, "-f", "-t", icons_dir)
        else "  ⚠ gtk-update-icon-cache bulunamadı"
    )

    # MIME ilişkilendirmeleri
    print("→ MIME ilişkilendirmeleri ayarlanıyor...")
    for mime in MIME_TYPES:
        ok = _run_quiet("xdg-mime", "default", f"{APP_ID}.desktop", mime)
        print(f"  {'✓' if ok else '⚠'} {mime}")

    print("\n✓ Kurulum tamamlandı.")


def desktop_uninstall() -> None:
    """desktop_install ile kurulan dosyaları kaldır."""
    prefix = _local_prefix()
    targets = [
        prefix / "bin" / "wropasi",
        prefix / "share" / "applications" / f"{APP_ID}.desktop",
        prefix / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_ID}.png",
        prefix / "share" / "mime" / "packages" / f"{APP_ID}.mime.xml",
    ]
    for p in targets:
        if p.exists():
            p.unlink()
            print(f"  ✓ Silindi: {p}")
        else:
            print(f"  - Yok: {p}")

    # Paket dizinini kaldır
    pkg_dir = prefix / "share" / "wropasi"
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
        print(f"  ✓ Silindi: {pkg_dir}")

    icon_cache_tool = (
        "gtk4-update-icon-cache"
        if shutil.which("gtk4-update-icon-cache")
        else "gtk-update-icon-cache"
    )
    _run_quiet("update-desktop-database", str(prefix / "share" / "applications"))
    _run_quiet("update-mime-database", str(prefix / "share" / "mime"))
    _run_quiet(icon_cache_tool, "-f", "-t", str(prefix / "share" / "icons" / "hicolor"))
    print("✓ Kaldırıldı.")

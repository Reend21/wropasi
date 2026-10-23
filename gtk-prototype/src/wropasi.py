#!/usr/bin/env python3

# InitS
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
import sys
import os
import json
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from textwrap import dedent

APP_ID = "io.github.wropasi"

# ── Desktop Integration (geliştirme / test kurulumu) ─────────────────────────
# .deb/.rpm paketlerinde bu fonksiyonlar KULLANILMAZ; paket yöneticisi
# dosyaları doğrudan /usr/share altına yerleştirir.  Bu sadece install.sh
# yerine "wropasi --install" ile yerel kurulum yapmak isteyenler içindir.

DESKTOP_ENTRY = dedent("""\
    [Desktop Entry]
    Name=wropasi
    Comment=Wrong Package Silly! wropasi solves an UX problem about package management in modern distros
    Exec={exec_path} %f
    Icon={icon_name}
    Terminal=false
    NoDisplay=true
    Type=Application
    Categories=System;PackageManager;Settings;
    Keywords=package;install;deb;rpm;flatpak;snap;appimage;paket;
    MimeType=application/vnd.debian.binary-package;application/x-rpm;application/vnd.snap;application/vnd.flatpak;application/vnd.appimage;
""")

MIME_XML = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">

      <mime-type type="application/vnd.flatpak">
        <comment>Flatpak Application Bundle</comment>
        <comment xml:lang="tr">Flatpak Uygulama Paketi</comment>
        <acronym>Flatpak</acronym>
        <glob pattern="*.flatpak"/>
      </mime-type>

      <!-- AppImage (.AppImage / .appimage) -->
      <mime-type type="application/vnd.appimage">
        <comment>AppImage Application Bundle</comment>
        <comment xml:lang="tr">AppImage Uygulama Paketi</comment>
        <acronym>AppImage</acronym>
        <glob pattern="*.AppImage"/>
        <glob pattern="*.appimage"/>
        <magic priority="60">
          <match type="string" offset="8" value="AI\\x02"/>
        </magic>
      </mime-type>

    </mime-info>
""")

MIME_TYPES = [
    "application/vnd.debian.binary-package",
    "application/x-rpm",
    "application/vnd.snap",
    "application/vnd.flatpak",
    "application/vnd.appimage",
]


def _local_prefix() -> Path:
    return Path.home() / ".local"


def _run_quiet(*cmd: str) -> bool:
    """Komutu sessizce çalıştır, başarılıysa True döndür."""
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def desktop_install() -> None:
    """~/.local altına desktop entry, ikon, MIME XML kur ve ilişkilendir."""
    prefix = _local_prefix()
    src_dir = Path(__file__).resolve().parent

    # Exec yolu: kurulu binary veya bu script
    exec_path = shutil.which("wropasi") or str(src_dir / "wropasi.py")

    # ── Desktop dosyası ──
    desktop_dir = prefix / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / f"{APP_ID}.desktop"
    desktop_file.write_text(
        DESKTOP_ENTRY.format(exec_path=exec_path, icon_name=APP_ID),
        encoding="utf-8",
    )
    print(f"  ✓ {desktop_file}")

    # ── İkon ──
    icon_src = src_dir.parent.parent / "wropasi-logo.png"
    if icon_src.exists():
        icon_dst = prefix / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_ID}.png"
        icon_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_src, icon_dst)
        print(f"  ✓ {icon_dst}")
    else:
        print(f"  ⚠ İkon bulunamadı: {icon_src}")

    # ── MIME XML ──
    mime_dir = prefix / "share" / "mime" / "packages"
    mime_dir.mkdir(parents=True, exist_ok=True)
    mime_file = mime_dir / f"{APP_ID}.mime.xml"
    mime_file.write_text(MIME_XML, encoding="utf-8")
    print(f"  ✓ {mime_file}")

    # ── Veritabanlarını güncelle ──
    print("→ Veritabanları güncelleniyor...")
    apps_dir = str(prefix / "share" / "applications")
    mime_base = str(prefix / "share" / "mime")
    print("  ✓ desktop-database" if _run_quiet("update-desktop-database", apps_dir) else "  ⚠ update-desktop-database bulunamadı")
    print("  ✓ mime-database"    if _run_quiet("update-mime-database", mime_base)    else "  ⚠ update-mime-database bulunamadı")

    # ── MIME ilişkilendirmeleri ──
    print("→ MIME ilişkilendirmeleri ayarlanıyor...")
    for mime in MIME_TYPES:
        ok = _run_quiet("xdg-mime", "default", f"{APP_ID}.desktop", mime)
        print(f"  {'✓' if ok else '⚠'} {mime}")

    print("\n✓ Kurulum tamamlandı.")


def desktop_uninstall() -> None:
    """desktop_install ile kurulan dosyaları kaldır."""
    prefix = _local_prefix()
    targets = [
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

    _run_quiet("update-desktop-database", str(prefix / "share" / "applications"))
    _run_quiet("update-mime-database",    str(prefix / "share" / "mime"))
    print("✓ Kaldırıldı.")

# Package handling
FORMAT_PM: dict[str, str | None] = {
    ".deb":      "dpkg",
    ".rpm":      "rpm",
    ".flatpak":  "flatpak",
    ".snap":     "snap",
    ".appimage": None,
}

PM_DISPLAY = {
    "dpkg":   "APT/dpkg",
    "rpm":    "RPM",
    "pacman": "Pacman",
    "zypper": "Zypper",
    "dnf":    "DNF",
}

FORMAT_DISPLAY = {
    ".deb":      "Debian (.deb)",
    ".rpm":      "RPM (.rpm)",
    ".flatpak":  "Flatpak (.flatpak)",
    ".snap":     "Snap (.snap)",
    ".appimage": "AppImage (.AppImage)",
}


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
        "native_pm": native_pm,
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
        # Gerekli anahtarlar var mı kontrol et
        required = {"native_pm", "has_flatpak", "has_snap", "has_alien"}
        if not required.issubset(data.keys()):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def get_pm_cache() -> dict:
    """Cache'den paket yöneticisi bilgilerini al; cache yoksa oluştur."""
    cache = _read_cache()
    if cache is not None:
        return cache
    cache = _build_cache()
    _write_cache(cache)
    return cache


def detect_native_pm() -> str | None:
    return get_pm_cache()["native_pm"]


def match_pkg(filepath: str) -> str:
    base = os.path.basename(filepath)
    name, _ = os.path.splitext(base)
    return name.split("_")[0].split("-")[0]

# App
class wropasi(Adw.Application):
    def __init__(self, filepath: str):
        super().__init__(application_id=APP_ID)
        self.filepath = filepath
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        WropasiWindow(application=self, filepath=self.filepath).present()


# Window
class WropasiWindow(Adw.ApplicationWindow):
    def __init__(self, filepath: str, **kwargs):
        super().__init__(**kwargs)
        self.filepath  = filepath
        self.ext       = os.path.splitext(filepath)[1].lower()
        self.name      = match_pkg(filepath)
        self.native_pm = detect_native_pm()
        self.file_pm   = FORMAT_PM.get(self.ext, "UNKNOWN")

        if self.file_pm == "UNKNOWN":
            self.state = "unknown"
        elif self.file_pm is None:
            self.state = "standalone"   # AppImage-like
        elif self.file_pm == self.native_pm:
            self.state = "compatible"
        else:
            self.state = "incompatible"

        self.set_title("wropasi")
        self.set_default_size(1024, -1)
        self.set_resizable(False)
        self._build_ui()

    def _build_ui(self):
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        root.set_margin_top(24)
        root.set_margin_bottom(32)
        root.set_margin_start(24)
        root.set_margin_end(24)

        match self.state:
            case "compatible":   self._page_compatible(root)
            case "incompatible": self._page_incompatible(root)
            case "standalone":   self._page_standalone(root)
            case _:              self._page_unknown(root)

        scroll = Gtk.ScrolledWindow(
            child=root,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=True,
        )
        tv.set_content(scroll)
        self.set_content(tv)

    def _page_compatible(self, box):
        self._status(box, "emblem-ok-symbolic", "success",
            "Bu paket sisteminizde çalışabilir.",
            f"<b>{self.name}</b> paketi sisteminizle uyumludur.")
        self._close_btn(box, "Peki", suggested=True)

    def _page_standalone(self, box):
        self._status(box, "emblem-ok-symbolic", "success",
            "AppImage",
            f"<b>{self.name}</b> bir AppImage paketidir. "
            "Taşınabilir ve her dağıtımda çalışabilir. Dilerseniz 'Gear Lever' ile bu paketi kuralım!")
        self._close_btn(box, "Peki", suggested=True)

    def _page_unknown(self, box):
        self._status(box, "dialog-error-symbolic", "error",
            "Bu ne be?",
            f"<b>{self.ext or '(uzantısız)'}</b> formatını tanımıyoruz. Bu bizim eşşekliğimizse affola. "
            "Ancak bu paketleme sistemi ya çok niş, yada gerçek değil.")
        self._close_btn(box, "Kapat")

    def _page_incompatible(self, box):
        native_str = PM_DISPLAY.get(self.native_pm, self.native_pm or "bilinmiyor")
        fmt_str    = FORMAT_DISPLAY.get(self.ext, self.ext)

        self._status(
            box, "dialog-warning-symbolic", "warning",
            "Uyumsuz Paket",
            f"<b>{self.name}</b>, <b>{fmt_str}</b> formatını kullanıyor; "
            f"sisteminiz ise <b>{native_str}</b> kullanıyor.\n"
            "Bu paket sisteminizle uyumsuzdur ve bu yüzden sisteminize yüklenemez.",
        )

        hdr = Gtk.Label(label="Ne yapabilirsiniz?")
        hdr.add_css_class("heading")
        hdr.set_xalign(0)
        box.append(hdr)

        lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        lb.add_css_class("boxed-list")

        if shutil.which("flatpak"):
            lb.append(self._action_row(
                "Flathub'da Ara",
                "Evrensel yazılım mağzasında paketinizi arayın",
                "system-software-install-symbolic",
                self._open_flathub,
            ))

        if shutil.which("snap"):
            lb.append(self._action_row(
                "Snap Store'da Ara",
                "Cannonical'ın standart yazılım mağzasında paketinizi arayın",
                "system-software-install-symbolic",
                self._open_snap,
            ))

        if shutil.which("alien"):
            lb.append(self._action_row(
                "alien ile Dönüştür (Önerilemz)",
                f"Paketi {PM_DISPLAY.get(self.native_pm, self.native_pm)} formatına çevirin (Sadece son çareniz buysa)",
                "system-run-symbolic",
                self._show_alien_hint,
            ))

        lb.append(self._action_row(
            "Uyumlu sürümü manuel ara",
            "Genel ağ üzerinden paketi manuel arayın.",
            "web-browser-symbolic",
            self._open_web_search,
        ))

        box.append(lb)
        self._close_btn(box, "İptal")

    def _status(self, box, icon_name, css, title, body):
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(72)
        icon.add_css_class(css)
        box.append(icon)

        lbl_title = Gtk.Label(label=title)
        lbl_title.add_css_class("title-1")
        lbl_title.set_wrap(True)
        lbl_title.set_justify(Gtk.Justification.CENTER)
        box.append(lbl_title)

        lbl_body = Gtk.Label(label=body)
        lbl_body.set_use_markup(True)
        lbl_body.add_css_class("body")
        lbl_body.set_wrap(True)
        lbl_body.set_justify(Gtk.Justification.CENTER)
        lbl_body.set_xalign(0.5)
        box.append(lbl_body)

    def _close_btn(self, box, label, suggested=False):
        btn = Gtk.Button(label=label)
        btn.add_css_class("pill")
        if suggested:
            btn.add_css_class("suggested-action")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(4)
        btn.connect("clicked", lambda _: self.close())
        box.append(btn)

    def _action_row(self, title, subtitle, icon_name, callback) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=subtitle, activatable=True)

        prefix = Gtk.Image.new_from_icon_name(icon_name)
        prefix.set_pixel_size(24)
        row.add_prefix(prefix)

        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        row.add_suffix(chevron)

        row.connect("activated", lambda _: callback())
        return row

# Actions
    def _open_flathub(self):
        self._xdg_open(f"https://flathub.org/apps/search?q={urllib.parse.quote(self.name)}")

    def _open_snap(self):
        self._xdg_open(f"https://snapcraft.io/search?q={urllib.parse.quote(self.name)}")

    def _open_web_search(self):
        q = f"{self.name} {self.native_pm or 'linux'} download"
        self._xdg_open(f"https://duckduckgo.com/?q={urllib.parse.quote(q)}")

    def _show_alien_hint(self):
        target = "deb" if self.native_pm == "dpkg" else "rpm"
        fname  = os.path.basename(self.filepath)
        d = Adw.AlertDialog(
            heading="alien ile Dönüştürme",
            body=f"Terminalde şu komutu çalıştırın:\n\n"
            f"sudo alien --to-{target} \"{fname}\"",
        )
        d.add_response("ok", "Tamam")
        d.present(self)

    @staticmethod
    def _xdg_open(url: str):
        try:
            subprocess.Popen(["xdg-open", url])
        except OSError:
            pass


# Open
def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--install":
        print("→ wropasi kuruluyor...")
        desktop_install()
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--uninstall":
        print("→ wropasi kaldırılıyor...")
        desktop_uninstall()
        sys.exit(0)

    if len(sys.argv) < 2:
        print("usage: wropasi <app-path>  |  wropasi --install  |  wropasi --uninstall",
              file=sys.stderr)
        sys.exit(1)

    app = wropasi(filepath=sys.argv[1])
    sys.exit(app.run(sys.argv[:1]))

if __name__ == "__main__":
    main()

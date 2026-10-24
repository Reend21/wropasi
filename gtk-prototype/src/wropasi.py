#!/usr/bin/env python3

# Init
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib
import sys
import os
import json
import shutil
import subprocess
import urllib.parse
from pathlib import Path
from textwrap import dedent

APP_ID = "io.github.wropasi"

# Desktop entry for quick developing

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
    MimeType=application/vnd.debian.binary-package;application/x-rpm;application/vnd.snap;application/vnd.flatpak;application/vnd.flatpakref;application/vnd.flatpak.ref;application/vnd.appimage;
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

    <mime-type type="application/vnd.flatpakref">
        <comment>Flatpak Reference</comment>
        <comment xml:lang="tr">Flatpak Referans Dosyası</comment>
        <acronym>Flatpak</acronym>
        <glob pattern="*.flatpakref"/>
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
    "application/vnd.flatpakref",
    "application/vnd.flatpak.ref",
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

    bin_dir = prefix / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_bin = bin_dir / "wropasi"
    shutil.copy2(src_dir / "wropasi.py", target_bin)
    target_bin.chmod(0o755)
    exec_path = str(target_bin)

    desktop_dir = prefix / "share" / "applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / f"{APP_ID}.desktop"
    desktop_file.write_text(
        DESKTOP_ENTRY.format(exec_path=exec_path, icon_name=APP_ID),
        encoding="utf-8",
    )
    print(f"  ✓ {desktop_file}")

    icon_candidates = [
        src_dir.parent.parent / "wropasi-logo.png",
        Path.cwd() / "wropasi-logo.png",
    ]
    icon_src = next((p for p in icon_candidates if p.exists()), None)
    icon_dst = prefix / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_ID}.png"
    if icon_src:
        icon_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_src, icon_dst)
        print(f"  ✓ {icon_dst}")
    elif icon_dst.exists():
        print(f"  ✓ {icon_dst} (mevcut ikon korundu)")
    else:
        print(f"  ⚠ İkon bulunamadı: wropasi-logo.png")

    mime_dir = prefix / "share" / "mime" / "packages"
    mime_dir.mkdir(parents=True, exist_ok=True)
    mime_file = mime_dir / f"{APP_ID}.mime.xml"
    mime_file.write_text(MIME_XML, encoding="utf-8")
    print(f"  ✓ {mime_file}")

    print("→ Veritabanları güncelleniyor...")
    apps_dir = str(prefix / "share" / "applications")
    mime_base = str(prefix / "share" / "mime")
    icons_dir = str(prefix / "share" / "icons" / "hicolor")
    icon_cache_tool = "gtk4-update-icon-cache" if shutil.which("gtk4-update-icon-cache") else "gtk-update-icon-cache"
    print("  ✓ desktop-database" if _run_quiet("update-desktop-database", apps_dir) else "  ⚠ update-desktop-database bulunamadı")
    print("  ✓ mime-database"    if _run_quiet("update-mime-database", mime_base)    else "  ⚠ update-mime-database bulunamadı")
    print("  ✓ icon-cache"       if _run_quiet(icon_cache_tool, "-f", "-t", icons_dir) else "  ⚠ gtk-update-icon-cache bulunamadı")

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

    icon_cache_tool = "gtk4-update-icon-cache" if shutil.which("gtk4-update-icon-cache") else "gtk-update-icon-cache"
    _run_quiet("update-desktop-database", str(prefix / "share" / "applications"))
    _run_quiet("update-mime-database",    str(prefix / "share" / "mime"))
    _run_quiet(icon_cache_tool,           "-f", "-t", str(prefix / "share" / "icons" / "hicolor"))
    print("✓ Kaldırıldı.")

# Package handling
FORMAT_PM: dict[str, str | None] = {
    ".deb":         "dpkg",
    ".rpm":         "rpm",
    ".flatpak":     "flatpak",
    ".flatpakref":  "flatpak",
    ".snap":        "snap",
    ".appimage":    None,
}

PM_DISPLAY = {
    "dpkg":   "APT/dpkg",
    "rpm":    "RPM",
    "pacman": "Pacman",
    "zypper": "Zypper",
    "dnf":    "DNF",
}

FORMAT_DISPLAY = {
    ".deb":        "Debian (.deb)",
    ".rpm":        "RPM (.rpm)",
    ".flatpak":    "Flatpak (.flatpak)",
    ".flatpakref": "Flatpak Referansı (.flatpakref)",
    ".snap":       "Snap (.snap)",
    ".appimage":   "AppImage (.AppImage)",
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
    # .flatpakref dosyalarında Title veya Name alanını oku
    if filepath.lower().endswith(".flatpakref") and os.path.isfile(filepath):
        try:
            ref_title = None
            ref_name = None
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Title="):
                        ref_title = line.split("=", 1)[1].strip()
                    elif line.startswith("Name="):
                        ref_name = line.split("=", 1)[1].strip()
            if ref_title:
                return ref_title
            if ref_name:
                return ref_name
        except Exception:
            pass
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
        self.filepath    = filepath
        self.ext         = os.path.splitext(filepath)[1].lower()
        self.name        = match_pkg(filepath)
        self.native_pm   = detect_native_pm()
        self.file_pm     = FORMAT_PM.get(self.ext, "UNKNOWN")
        self.has_flatpak = shutil.which("flatpak") is not None

        if self.ext == ".flatpakref":
            if self.has_flatpak:
                self.state = "flatpakref_has_flatpak"
            else:
                self.state = "flatpakref_no_flatpak"
        elif self.file_pm == "UNKNOWN":
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
            case "compatible":             self._page_compatible(root)
            case "incompatible":           self._page_incompatible(root)
            case "standalone":             self._page_standalone(root)
            case "flatpakref_has_flatpak": self._page_flatpakref_has_flatpak(root)
            case "flatpakref_no_flatpak":  self._page_flatpakref_no_flatpak(root)
            case _:                        self._page_unknown(root)

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
            "Belki şaşıracaksın ama, bu her yerde çalışır!",
            f"<b>{self.name}</b> bir AppImage paketidir. "
            "Aplikasyon Imajları (.AppImage) dosyaları taşınabilir ve tüm Linux sistemlerinde çalışır. "
            "Direkt çalıştırmak yerine <b>Gear Level</b> veya <b>AppImage Launcher</b> kullanarak bu Aplikasyon Imajını sisteminize yükleyebilirsiniz.")
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

    def _page_flatpakref_has_flatpak(self, box):
        self._status(
            box, "dialog-warning-symbolic", "warning",
            "PackageKit Entegrasyonu Çalışmıyor",
            f"Sisteminizde <b>Flatpak</b> kurulu, ancak PackageKit veya yazılım mağazası entegrasyonu "
            f"bu dosyayı doğrudan işleyemedi.\n"
            f"<b>{self.name}</b> paketi normal şartlarda doğrudan yazılım mağazanız tarafından açılmalıydı, ama sanırım PackageKit'in size hizmet etmekten daha önemli işleri var..",
        )

        hdr = Gtk.Label(label="Ne yapabilirsiniz?")
        hdr.add_css_class("heading")
        hdr.set_xalign(0)
        box.append(hdr)

        lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        lb.add_css_class("boxed-list")

        lb.append(self._action_row(
            "Y",
            "Dosyayı sistemdeki yazılım mağazasına veya PackageKit arayüzüne yönlendir",
            "system-software-install-symbolic",
            self._launch_packagekit_or_store_file,
        ))

        lb.append(self._action_row(
            "Terminal ile Kur (flatpak install)",
            f"flatpak install {os.path.basename(self.filepath)}",
            "utilities-terminal-symbolic",
            self._show_flatpak_install_hint,
        ))

        box.append(lb)
        self._close_btn(box, "Kapat")

    def _page_flatpakref_no_flatpak(self, box):
        self._status(
            box, "dialog-warning-symbolic", "warning",
            "Flatpak Kurulu Değil",
            f"<b>{self.name}</b> bir Flatpak paketidir (.flatpakref).\n"
            "Linux'un evrensel paket yöneticisi Flatpak sisteminizde kurulu değil.",
        )

        hdr = Gtk.Label(label="Ne yapabilirsiniz?")
        hdr.add_css_class("heading")
        hdr.set_xalign(0)
        box.append(hdr)

        lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        lb.add_css_class("boxed-list")

        lb.append(self._action_row(
            "Flatpak'i Kur",
            "Yazılım mağazanız aracılığıyla Flatpak paket yöneticisini kurun",
            "system-software-install-symbolic",
            self._install_flatpak_system,
        ))

        if shutil.which("snap"):
            lb.append(self._action_row(
                "Snap Store'da Ara",
                "Cannonical'ın standart yazılım mağzasında paketinizi arayın",
                "system-software-install-symbolic",
                self._open_snap,
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
    def _launch_packagekit_or_store_file(self):
        """Flatpakref dosyasını PackageKit veya yazılım mağazası ile açmayı dener."""
        abs_path = os.path.abspath(self.filepath)

        # 1. PackageKit session DBus çağrısı (org.freedesktop.PackageKit.Modify.InstallPackageFiles)
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                "org.freedesktop.PackageKit",
                "/org/freedesktop/PackageKit",
                "org.freedesktop.PackageKit.Modify",
                "InstallPackageFiles",
                GLib.Variant("(uass)", (0, [abs_path], "")),
                None,
                Gio.DBusCallFlags.NONE,
                1500,
                None,
            )
            return
        except Exception:
            pass

        # 2. Grafiksel yazılım mağazalarını doğrudan çağırma
        for store, args in (
            ("gnome-software", ["gnome-software", f"--local-filename={abs_path}"]),
            ("plasma-discover", ["plasma-discover", abs_path]),
            ("io.elementary.appcenter", ["io.elementary.appcenter", abs_path]),
            ("pamac-installer", ["pamac-installer", abs_path]),
            ("pamac-manager", ["pamac-manager", abs_path]),
            ("gpk-install-local-file", ["gpk-install-local-file", abs_path]),
            ("bauh", ["bauh", abs_path]),
        ):
            if shutil.which(store):
                try:
                    subprocess.Popen(args)
                    return
                except OSError:
                    continue

        # 3. Grafiksel mağaza yanıt vermezse terminal talimatı göster
        cmd = f"flatpak install \"{self.filepath}\""
        self._show_command_dialog(
            "Yazılım Mağazası / PackageKit Açılamadı",
            "Sisteminizde PackageKit oturum servisi veya grafiksel bir yazılım mağazası başlatılamadı.\n"
            "Dosyayı terminalden doğrudan şu komutla kurabilirsiniz:",
            cmd,
        )

    def _install_flatpak_system(self):
        """PackageKit veya yazılım mağazasına yönlendirerek Flatpak desteğini kurar."""
        # 1. PackageKit session DBus çağrısı (org.freedesktop.PackageKit.Modify.InstallPackageNames)
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                "org.freedesktop.PackageKit",
                "/org/freedesktop/PackageKit",
                "org.freedesktop.PackageKit.Modify",
                "InstallPackageNames",
                GLib.Variant("(uass)", (0, ["flatpak"], "")),
                None,
                Gio.DBusCallFlags.NONE,
                1500,
                None,
            )
            return
        except Exception:
            pass

        # 2. Grafiksel yazılım mağazalarında arama açma
        for store, args in (
            ("gnome-software", ["gnome-software", "--search=flatpak"]),
            ("plasma-discover", ["plasma-discover", "--mode", "search", "flatpak"]),
            ("io.elementary.appcenter", ["io.elementary.appcenter", "--search", "flatpak"]),
            ("pamac-manager", ["pamac-manager", "--search", "flatpak"]),
            ("bauh", ["bauh", "flatpak"]),
        ):
            if shutil.which(store):
                try:
                    subprocess.Popen(args)
                    return
                except OSError:
                    continue

        # 3. appstream:// URI'si ile açmayı dene
        try:
            subprocess.Popen(["xdg-open", "appstream://flatpak"])
            return
        except OSError:
            pass

        # 4. Grafiksel mağaza yoksa paket yöneticisi komutu göster
        cmd = self._get_native_install_cmd("flatpak")
        self._show_command_dialog(
            "Flatpak Kurulumu",
            "Grafiksel yazılım mağazası veya PackageKit servisi bulunamadı.\n"
            "Flatpak paketini terminal üzerinden şu komutla kurabilirsiniz:",
            cmd,
        )

    def _show_flatpak_install_hint(self):
        cmd = f"flatpak install \"{self.filepath}\""
        self._show_command_dialog(
            "Terminal ile Kurulum",
            "Terminalde şu komutu çalıştırarak paketi doğrudan kurabilirsiniz:",
            cmd,
        )

    def _get_native_install_cmd(self, pkg: str) -> str:
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
        elif self.native_pm == "dpkg":
            return f"sudo apt install {pkg}"
        elif self.native_pm == "rpm":
            return f"sudo rpm -i {pkg}"
        return f"pkcon install {pkg}"

    def _show_command_dialog(self, heading: str, body_text: str, command: str):
        d = Adw.AlertDialog(
            heading=heading,
            body=f"{body_text}\n\n<b>{command}</b>",
        )
        d.set_body_use_markup(True)
        d.add_response("copy", "Komutu Kopyala")
        d.add_response("ok", "Tamam")
        d.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)

        def on_response(_dialog, response_id):
            if response_id == "copy":
                clipboard = Gdk.Display.get_default().get_clipboard()
                clipboard.set(command)

        d.connect("response", on_response)
        d.present(self)

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

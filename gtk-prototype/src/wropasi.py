#!/usr/bin/env python3

# InitS
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw
import sys
import os
import shutil
import subprocess
import urllib.parse

APP_ID = "io.github.wropasi"

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


def detect_native_pm() -> str | None:
    for pm in ("dpkg", "rpm", "pacman", "zypper", "dnf"):
        if shutil.which(pm):
            return pm
    return None


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
    if len(sys.argv) < 2:
        print("usage: wropasi <app-path> you cant run this app without an argument", file=sys.stderr)
        sys.exit(1)

    app = wropasi(filepath=sys.argv[1])
    sys.exit(app.run(sys.argv[:1]))

if __name__ == "__main__":
    main()

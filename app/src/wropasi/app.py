# Main GTK4 / Libadwaita user interface.

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib  # noqa: E402

from .constants import APP_ID
from .i18n import _
from .system import get_system_info, desktop_install, desktop_uninstall
from .formats import get_handler, get_unknown_result
from .formats.base import Action, FormatResult


# Application class managing lifecycle and single/multi instance behavior
class WropasiApp(Adw.Application):
    def __init__(self, filepath: str, test_system_info: dict | None = None):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )
        self.filepath = filepath
        self.test_system_info = test_system_info
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        win = WropasiWindow(
            application=self,
            filepath=self.filepath,
            override_system_info=self.test_system_info,
        )
        if win.result is None:
            win.destroy()
            self.quit()
            return
        win.present()


# Main dialog window presenting package analysis and available actions
class WropasiWindow(Adw.ApplicationWindow):
    def __init__(self, filepath: str, override_system_info: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.filepath = filepath
        self.system_info = override_system_info if override_system_info is not None else get_system_info()

        # Resolve format handler for this filepath / extension
        handler = get_handler(filepath)
        if handler is not None:
            self.result = handler.analyze(filepath, self.system_info)
        else:
            self.ext = os.path.splitext(filepath)[1].lower()
            # Do not trigger a dialog for standard archive files that aren't packages
            if self.ext in (".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".zst", ".tgz", ".txz"):
                self.result = None
            else:
                self.result = get_unknown_result(self.ext)

        # Silent exit if format was rejected (e.g. non-Arch tar file)
        if self.result is None:
            return

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

        self._render_result(root, self.result)

        scroll = Gtk.ScrolledWindow(
            child=root,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=True,
        )
        tv.set_content(scroll)
        self.set_content(tv)

    def _render_result(self, box: Gtk.Box, result: FormatResult):
        # Header banner with icon, title, and body description
        self._status(
            box,
            result.status.icon_name,
            result.status.css_class,
            result.status.title,
            result.status.body,
        )

        # Action list guiding the user
        if result.actions:
            hdr = Gtk.Label(label=_("What can you do?"))
            hdr.add_css_class("heading")
            hdr.set_xalign(0)
            box.append(hdr)

            lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            lb.add_css_class("boxed-list")
            for action in result.actions:
                lb.append(self._action_row(action))
            box.append(lb)

        close_text = result.close_label or _("Close")
        self._close_btn(box, close_text, suggested=result.close_suggested)

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

    def _action_row(self, action: Action) -> Adw.ActionRow:
        row = Adw.ActionRow(
            title=action.title, subtitle=action.subtitle, activatable=True,
        )

        prefix = Gtk.Image.new_from_icon_name(action.icon_name)
        prefix.set_pixel_size(24)
        if action.danger:
            prefix.add_css_class("warning")
        row.add_prefix(prefix)

        if action.danger:
            badge = Gtk.Label(label=_("⚠ Not recommended"))
            badge.add_css_class("caption")
            badge.add_css_class("warning")
            badge.set_valign(Gtk.Align.CENTER)
            row.add_suffix(badge)
        else:
            chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
            chevron.add_css_class("dim-label")
            row.add_suffix(chevron)

        row.connect("activated", lambda _: self._execute_action(action))
        return row

    def _execute_action(self, action: Action):
        match action.action_type:
            case "url":
                self._xdg_open(action.payload)
            case "command":
                self._exec_in_terminal(
                    action.payload,
                    fallback_heading=action.dialog_heading or _("No Terminal Found"),
                    fallback_body=action.dialog_body or _("Could not find a terminal emulator. Run this command manually:"),
                )
            case "packagekit_file":
                self._exec_packagekit_file(action)
            case "packagekit_install":
                self._exec_packagekit_install(action)
            case "alien":
                self._exec_alien(action)

    # Attempt to open package file via PackageKit session bus or GUI software store
    def _exec_packagekit_file(self, action: Action):
        abs_path = os.path.abspath(action.payload)

        # 1. PackageKit session DBus call
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

        # 2. Known software stores
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

        # 3. Fallback command dialog
        self._show_command_dialog(
            action.dialog_heading or _("Package Manager Not Found"),
            action.dialog_body or _("You can install the package manually via terminal:"),
            action.fallback_command,
        )

    # Attempt to install package by name via PackageKit session bus or GUI software store
    def _exec_packagekit_install(self, action: Action):
        pkg_name = action.payload

        # 1. PackageKit session DBus
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call_sync(
                "org.freedesktop.PackageKit",
                "/org/freedesktop/PackageKit",
                "org.freedesktop.PackageKit.Modify",
                "InstallPackageNames",
                GLib.Variant("(uass)", (0, [pkg_name], "")),
                None,
                Gio.DBusCallFlags.NONE,
                1500,
                None,
            )
            return
        except Exception:
            pass

        # 2. Known software stores
        for store, args in (
            ("gnome-software", ["gnome-software", f"--search={pkg_name}"]),
            ("plasma-discover", ["plasma-discover", "--mode", "search", pkg_name]),
            ("io.elementary.appcenter", ["io.elementary.appcenter", "--search", pkg_name]),
            ("pamac-manager", ["pamac-manager", "--search", pkg_name]),
            ("bauh", ["bauh", pkg_name]),
        ):
            if shutil.which(store):
                try:
                    subprocess.Popen(args)
                    return
                except OSError:
                    continue

        # 3. appstream:// URI fallback
        try:
            subprocess.Popen(["xdg-open", f"appstream://{pkg_name}"])
            return
        except OSError:
            pass

        # 4. Fallback command dialog
        self._show_command_dialog(
            action.dialog_heading or _("Installation"),
            action.dialog_body or _("You can install this package via terminal:"),
            action.fallback_command,
        )

    # Show alien package conversion dialog
    def _exec_alien(self, action: Action):
        native_pm = self.system_info.get("native_pm")
        target = "deb" if native_pm in ("dpkg", "apt") else "rpm"
        fname = os.path.basename(action.payload)
        cmd = f'sudo alien --to-{target} "{fname}"'

        self._show_command_dialog(
            action.dialog_heading or _("Alien Package Converter"),
            action.dialog_body or _("Run this in your terminal and pray to the package gods:"),
            cmd,
        )

    # Try to open a terminal emulator and run the command inside it.
    # Falls back to a copy-command dialog if no terminal is found.
    def _exec_in_terminal(self, command: str, fallback_heading: str = "", fallback_body: str = ""):
        shell_cmd = command + '; echo; read -rp "Press Enter to close..." _'
        q = shlex.quote(shell_cmd)

        env_term = os.environ.get("TERMINAL", "")

        # Build ordered list of (binary, args) attempts.
        # Terminals that accept `-- bash -c CMD` pass CMD as a single arg to bash;
        # terminals using -e expect a quoted shell string.
        attempts: list[list[str]] = []
        if env_term:
            attempts.append([env_term, "-e", f"bash -c {q}"])

        attempts += [
            ["gnome-terminal", "--",   "bash", "-c", shell_cmd],
            ["kgx",            "--",   "bash", "-c", shell_cmd],
            ["konsole",        "-e",   "bash", "-c", shell_cmd],
            ["xterm",          "-e",   "bash", "-c", shell_cmd],
            ["alacritty",      "-e",   "bash", "-c", shell_cmd],
            ["kitty",                  "bash", "-c", shell_cmd],
            ["foot",                   "bash", "-c", shell_cmd],
            ["wezterm", "start", "--", "bash", "-c", shell_cmd],
            ["xfce4-terminal", "-e",   f"bash -c {q}"],
            ["mate-terminal",  "-e",   f"bash -c {q}"],
            ["tilix",          "-e",   f"bash -c {q}"],
        ]

        for args in attempts:
            if shutil.which(args[0]):
                try:
                    subprocess.Popen(args)
                    return
                except OSError:
                    continue

        # No terminal found — fall back to copy dialog
        self._show_command_dialog(
            fallback_heading or _("No Terminal Found"),
            fallback_body or _("Could not find a terminal emulator. Run this command manually:"),
            command,
        )

    def _show_command_dialog(self, heading: str, body_text: str, command: str):
        d = Adw.AlertDialog(
            heading=heading,
            body=f"{body_text}\n\n<b>{command}</b>",
        )
        d.set_body_use_markup(True)
        d.add_response("copy", _("Copy Command"))
        d.add_response("ok", _("Got it"))
        d.set_response_appearance("copy", Adw.ResponseAppearance.SUGGESTED)

        def on_response(_dialog, response_id):
            if response_id == "copy":
                clipboard = Gdk.Display.get_default().get_clipboard()
                clipboard.set(command)

        d.connect("response", on_response)
        d.present(self)

    @staticmethod
    def _xdg_open(url: str):
        try:
            subprocess.Popen(["xdg-open", url])
        except OSError:
            pass


# Test scenarios for --test CLI flag.
# Each entry: scenario_id -> (fake_filepath, system_info_dict)
_TEST_SCENARIOS: dict[str, tuple[str, dict]] = {
    # .deb – native APT/dpkg system → compatible ✅
    "deb-compatible": (
        "/tmp/test-pkg_1.0_amd64.deb",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # .deb – DNF system, no alien → incompatible ⚠️
    "deb-incompatible": (
        "/tmp/test-pkg_1.0_amd64.deb",
        {"native_pm": "dnf", "has_flatpak": True,  "has_snap": True,  "has_alien": False},
    ),
    # .deb – DNF system WITH alien → incompatible + alien button ⚠️
    "deb-incompatible-alien": (
        "/tmp/test-pkg_1.0_amd64.deb",
        {"native_pm": "dnf", "has_flatpak": True,  "has_snap": False, "has_alien": True},
    ),
    # .rpm – native DNF system → compatible ✅
    "rpm-compatible": (
        "/tmp/test-pkg-1.0.x86_64.rpm",
        {"native_pm": "dnf", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # .rpm – APT system, no alien → incompatible ⚠️
    "rpm-incompatible": (
        "/tmp/test-pkg-1.0.x86_64.rpm",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": True,  "has_alien": False},
    ),
    # .rpm – APT system WITH alien → incompatible + alien button ⚠️
    "rpm-incompatible-alien": (
        "/tmp/test-pkg-1.0.x86_64.rpm",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": False, "has_alien": True},
    ),
    # .flatpak bundle – flatpak installed → install dialog ✅
    "flatpak-has": (
        "/tmp/test-pkg.flatpak",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # .flatpak bundle – flatpak missing ⚠️
    "flatpak-no": (
        "/tmp/test-pkg.flatpak",
        {"native_pm": "apt", "has_flatpak": False, "has_snap": True,  "has_alien": False},
    ),
    # .flatpakref – flatpak installed (MIME-route dialog) ⚠️
    "flatpakref-has": (
        "/tmp/test-pkg.flatpakref",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # .flatpakref – flatpak missing ⚠️
    "flatpakref-no": (
        "/tmp/test-pkg.flatpakref",
        {"native_pm": "apt", "has_flatpak": False, "has_snap": True,  "has_alien": False},
    ),
    # .snap – snapd installed ✅
    "snap-has": (
        "/tmp/test-pkg_1.0_amd64.snap",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": True,  "has_alien": False},
    ),
    # .snap – snapd missing ⚠️
    "snap-no": (
        "/tmp/test-pkg_1.0_amd64.snap",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # .AppImage – always portable ✅
    "appimage": (
        "/tmp/TestApp-1.0-x86_64.AppImage",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # Arch Linux (.pkg.tar.zst) – Pacman system → compatible ✅
    "pacman-compatible": (
        "/tmp/test-pkg-1.0-1-x86_64.pkg.tar.zst",
        {"native_pm": "pacman", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # Arch Linux (.pkg.tar.zst) – APT system → incompatible ⚠️
    "pacman-incompatible": (
        "/tmp/test-pkg-1.0-1-x86_64.pkg.tar.zst",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": True,  "has_alien": False},
    ),
    # PKGBUILD – Pacman / makepkg system → compatible ✅
    "pkgbuild-compatible": (
        "/tmp/PKGBUILD",
        {"native_pm": "pacman", "has_flatpak": True,  "has_snap": False, "has_alien": False},
    ),
    # PKGBUILD – DNF system → incompatible ⚠️
    "pkgbuild-incompatible": (
        "/tmp/PKGBUILD",
        {"native_pm": "dnf", "has_flatpak": True,  "has_snap": True,  "has_alien": False},
    ),
    # unknown extension ❌
    "unknown": (
        "/tmp/test-pkg.xyz",
        {"native_pm": "apt", "has_flatpak": True,  "has_snap": True,  "has_alien": False},
    ),
}


# CLI entry point
def main():
    if len(sys.argv) >= 2 and sys.argv[1] in ("--help", "-h"):
        print(
            "usage: wropasi <app-path>  |  wropasi --install  |  wropasi --uninstall\n"
            "       wropasi --test <scenario-id>  |  wropasi --test list"
        )
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--install":
        print("> installing wropasi")
        desktop_install()
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--uninstall":
        print("removing wropasi <")
        desktop_uninstall()
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--test":
        if len(sys.argv) < 3 or sys.argv[2] == "list":
            print("Available test scenarios:\n")
            for sid, (fpath, sinfo) in _TEST_SCENARIOS.items():
                pm   = sinfo.get("native_pm") or "none"
                fp   = "flatpak" if sinfo.get("has_flatpak") else "no-flatpak"
                sn   = "snap"    if sinfo.get("has_snap")    else "no-snap"
                al   = "alien"   if sinfo.get("has_alien")   else "no-alien"
                print(f"  {sid:<26}  ({pm}, {fp}, {sn}, {al})")
            sys.exit(0)

        scenario_id = sys.argv[2]
        if scenario_id not in _TEST_SCENARIOS:
            print(
                f"error: unknown scenario '{scenario_id}'\n"
                "run 'wropasi --test list' to see available scenarios.",
                file=sys.stderr,
            )
            sys.exit(1)

        fake_path, fake_sinfo = _TEST_SCENARIOS[scenario_id]
        app = WropasiApp(filepath=fake_path, test_system_info=fake_sinfo)
        sys.exit(app.run(sys.argv[:1]))

    if len(sys.argv) < 2:
        print(
            "usage: wropasi <app-path>  |  wropasi --install  |  wropasi --uninstall",
            file=sys.stderr,
        )
        sys.exit(1)

    app = WropasiApp(filepath=sys.argv[1])
    sys.exit(app.run(sys.argv[:1]))

# ! GUI App

from __future__ import annotations

import os
import shutil
import subprocess
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Gio, GLib  # noqa: E402

from .constants import APP_ID
from .system import get_system_info, desktop_install, desktop_uninstall
from .formats import get_handler, get_unknown_result
from .formats.base import Action, FormatResult

# ! open the app
class WropasiApp(Adw.Application):
    def __init__(self, filepath: str):
        super().__init__(application_id=APP_ID)
        self.filepath = filepath
        self.connect("activate", self._on_activate)

    def _on_activate(self, _app):
        WropasiWindow(application=self, filepath=self.filepath).present()

# ! windows
class WropasiWindow(Adw.ApplicationWindow):
    def __init__(self, filepath: str, **kwargs):
        super().__init__(**kwargs)
        self.filepath = filepath
        self.ext = os.path.splitext(filepath)[1].lower()
        self.system_info = get_system_info()

        # ! get format handler
        handler = get_handler(self.ext)
        if handler is not None:
            self.result = handler.analyze(filepath, self.system_info)
        else:
            self.result = get_unknown_result(self.ext)

        self.set_title("wropasi")
        self.set_default_size(1024, -1)
        self.set_resizable(False)
        self._build_ui()

    # ! create ui
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
        # ! situation banner
        self._status(
            box,
            result.status.icon_name,
            result.status.css_class,
            result.status.title,
            result.status.body,
        )

        # ! Guide list
        if result.actions:
            hdr = Gtk.Label(label="What can you do?")
            hdr.add_css_class("heading")
            hdr.set_xalign(0)
            box.append(hdr)
            lb = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
            lb.add_css_class("boxed-list")
            for action in result.actions:
                lb.append(self._action_row(action))
            box.append(lb)
        self._close_btn(box, result.close_label, suggested=result.close_suggested)

    # ! UI Helpers
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
        row.add_prefix(prefix)

        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        row.add_suffix(chevron)

        row.connect("activated", lambda _: self._execute_action(action))
        return row

    # ! Guide actions
    def _execute_action(self, action: Action):
        match action.action_type:
            case "url":
                self._xdg_open(action.payload)
            case "command":
                self._show_command_dialog(
                    action.dialog_heading or "command",
                    action.dialog_body or "Run this command on terminal",
                    action.payload,
                )
            case "packagekit_file":
                self._exec_packagekit_file(action)
            case "packagekit_install":
                self._exec_packagekit_install(action)
            case "alien":
                self._exec_alien(action)

    def _exec_packagekit_file(self, action: Action):
        """tries to open the package with packagekit or app center"""
        abs_path = os.path.abspath(action.payload)

        # ! PackageKit session DBus call
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

        # ! App center call
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

        # ! Fallback / manual
        self._show_command_dialog(
            action.dialog_heading or "We cant find package manager",
            action.dialog_body or "You can install the package via terminal",
            action.fallback_command,
        )

    def _exec_packagekit_install(self, action: Action):
        """Install package with packagekit"""
        pkg_name = action.payload

        # ! PackageKit session DBus
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

        # ! App center
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

        # ! appstream:// URI'si
        try:
            subprocess.Popen(["xdg-open", f"appstream://{pkg_name}"])
            return
        except OSError:
            pass

        # ! Fallback / manual
        self._show_command_dialog(
            action.dialog_heading or "Setup",
            action.dialog_body or "You can install the package via terminal",
            action.fallback_command,
        )

    def _exec_alien(self, action: Action):
        """turn with alien"""
        native_pm = self.system_info.get("native_pm")
        target = "deb" if native_pm == "dpkg" else "rpm"
        fname = os.path.basename(action.payload)

        d = Adw.AlertDialog(
            heading="Alien",
            body=f"Run this command on terminal:\n\n"
            f'sudo alien --to-{target} "{fname}"',
        )
        d.add_response("ok", "Tamam")
        d.present(self)

    # ! Helpers
    def _show_command_dialog(self, heading: str, body_text: str, command: str):
        d = Adw.AlertDialog(
            heading=heading,
            body=f"{body_text}\n\n<b>{command}</b>",
        )
        d.set_body_use_markup(True)
        d.add_response("copy", "Copy command")
        d.add_response("ok", "Allright")
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

# ! CLI
def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--install":
        print("> installing wropasi")
        desktop_install()
        sys.exit(0)

    if len(sys.argv) >= 2 and sys.argv[1] == "--uninstall":
        print("removing wropasi <")
        desktop_uninstall()
        sys.exit(0)

    if len(sys.argv) < 2:
        print(
            "usage: wropasi <app-path>  |  wropasi --install  |  wropasi --uninstall",
            file=sys.stderr,
        )
        sys.exit(1)

    app = WropasiApp(filepath=sys.argv[1])
    sys.exit(app.run(sys.argv[:1]))

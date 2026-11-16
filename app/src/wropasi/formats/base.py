# Base classes and data structures for package format handlers.

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..i18n import _


# Status information displayed to the user (icon + CSS class + title + body)
@dataclass
class StatusInfo:
    icon_name: str
    css_class: str   # "success", "warning", "error"
    title: str
    body: str


# A single action presented to the user
# Action types:
# "url"                 – Open payload URL with xdg-open.
# "command"             – Show a dialog with the command to copy/run.
# "packagekit_file"     – Try to open file with PackageKit or App Center; fallback to command dialog.
# "packagekit_install"  – Try to install package name via PackageKit or App Center; fallback to command dialog.
# "alien"               – Show alien package conversion dialog.
@dataclass
class Action:
    title: str
    subtitle: str
    icon_name: str
    action_type: str
    payload: str = ""
    dialog_heading: str = ""
    dialog_body: str = ""
    fallback_command: str = ""


# Analysis result of a format handler
@dataclass
class FormatResult:
    status: StatusInfo
    actions: list[Action] = field(default_factory=list)
    close_label: str = ""
    close_suggested: bool = False


# Abstract base class that all format handlers must implement
class BaseFormatHandler(ABC):
    extensions: tuple[str, ...] = ()
    display_name: str = ""
    required_pm: str | None = None

    # Extract the application / package name from a filepath
    @abstractmethod
    def extract_name(self, filepath: str) -> str:
        ...

    # Analyze the package file in the context of the user's system
    @abstractmethod
    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        ...


# Base handler for packages tied to a native package manager (deb, rpm, etc.)
class NativeFormatHandler(BaseFormatHandler):
    compatible_pms: tuple[str, ...] = ()

    def is_compatible(self, native_pm: str | None) -> bool:
        if not native_pm:
            return False
        if self.compatible_pms:
            return native_pm in self.compatible_pms
        return native_pm == self.required_pm

    def extract_name(self, filepath: str) -> str:
        import os
        import re

        base = os.path.basename(filepath)
        name, _ = os.path.splitext(base)
        cleaned = re.sub(
            r"[-.](x86_64|aarch64|armv7hl|armhf|i686|noarch|ppc64le|s390x|x64)$",
            "",
            name,
            flags=re.I,
        )
        if "_" in cleaned:
            return cleaned.split("_")[0]
        parts = re.split(r"-(?=\d)", cleaned)
        return parts[0]

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name = self.extract_name(filepath)
        native_pm = system_info.get("native_pm")

        if self.is_compatible(native_pm):
            return self._build_compatible(name, filepath, native_pm, system_info)

        return self._build_incompatible(name, filepath, native_pm, system_info)

    def _build_compatible(
        self,
        name: str,
        filepath: str,
        native_pm: str | None,
        system_info: dict,
    ) -> FormatResult:
        if native_pm in ("dpkg", "apt"):
            fallback_cmd = f'sudo apt install "{filepath}"'
        elif native_pm == "dnf":
            fallback_cmd = f'sudo dnf install "{filepath}"'
        elif native_pm == "zypper":
            fallback_cmd = f'sudo zypper install "{filepath}"'
        elif native_pm == "rpm":
            fallback_cmd = f'sudo rpm -i "{filepath}"'
        elif native_pm == "pacman":
            fallback_cmd = f'sudo pacman -U "{filepath}"'
        else:
            fallback_cmd = f'pkcon install-local "{filepath}"'

        actions: list[Action] = [
            Action(
                title=_("Open with Software Center"),
                subtitle=_("Hand the file over to your GUI software center or PackageKit"),
                icon_name="system-software-install-symbolic",
                action_type="packagekit_file",
                payload=filepath,
                dialog_heading=_("Software Center Vanished"),
                dialog_body=_(
                    "Neither PackageKit session bus nor any graphical software store wanted to talk to us.\n"
                    "You can still install the package yourself via terminal:"
                ),
                fallback_command=fallback_cmd,
            ),
            Action(
                title=_("Install via Terminal"),
                subtitle=f"{fallback_cmd}",
                icon_name="utilities-terminal-symbolic",
                action_type="command",
                payload=fallback_cmd,
                dialog_heading=_("Terminal Installation"),
                dialog_body=_("Run this command in your terminal to install the package:"),
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                _("Miracle! This package actually works on your system."),
                _(
                    "<b>{name}</b> is completely compatible with your system. "
                    "Go ahead and install it before you change your mind."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Close"),
            close_suggested=False,
        )

    def _build_incompatible(
        self,
        name: str,
        filepath: str,
        native_pm: str | None,
        system_info: dict,
    ) -> FormatResult:
        import os
        import urllib.parse
        from ..system import PM_DISPLAY

        native_str = PM_DISPLAY.get(native_pm, native_pm or _("unknown"))
        ext = os.path.splitext(filepath)[1].lower()

        actions: list[Action] = []

        if system_info.get("has_flatpak"):
            actions.append(
                Action(
                    title=_("Search on Flathub"),
                    subtitle=_("Check the universal sandbox emporium for this app"),
                    icon_name="system-software-install-symbolic",
                    action_type="url",
                    payload=f"https://flathub.org/apps/search?q={urllib.parse.quote(name)}",
                )
            )

        if system_info.get("has_snap"):
            actions.append(
                Action(
                    title=_("Search on Snap Store"),
                    subtitle=_("Search Canonical's walled-ish garden for this app"),
                    icon_name="system-software-install-symbolic",
                    action_type="url",
                    payload=f"https://snapcraft.io/search?q={urllib.parse.quote(name)}",
                )
            )

        can_alien = (
            system_info.get("has_alien")
            and ext in (".deb", ".rpm")
            and native_pm in ("dpkg", "apt", "rpm", "dnf", "zypper")
        )
        if can_alien:
            target_str = "DEB" if native_pm in ("dpkg", "apt") else "RPM"
            actions.append(
                Action(
                    title=_("Convert with alien (Desperate times only)"),
                    subtitle=_(
                        "Mutate the package to {target} format (May work, may summon demons)"
                    ).format(target=target_str),
                    icon_name="system-run-symbolic",
                    action_type="alien",
                    payload=filepath,
                )
            )

        actions.append(
            Action(
                title=_("Search the Web Manually"),
                subtitle=_("Hunt for a compatible installer across the wild internet"),
                icon_name="web-browser-symbolic",
                action_type="url",
                payload=(
                    "https://duckduckgo.com/?q="
                    + urllib.parse.quote(f"{name} {native_pm or 'linux'} download")
                ),
            )
        )

        return FormatResult(
            status=StatusInfo(
                "dialog-warning-symbolic",
                "warning",
                _("Wrong Package, Silly!"),
                _(
                    "<b>{name}</b> is packaged as <b>{format}</b>, but your system speaks <b>{native}</b>.\n"
                    "Trying to shove this into your system won't end well."
                ).format(name=name, format=self.display_name, native=native_str),
            ),
            actions=actions,
            close_label=_("Cancel"),
        )

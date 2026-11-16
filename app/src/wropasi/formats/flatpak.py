# Flatpak (.flatpak / .flatpakref) format handlers.

from __future__ import annotations

import os
import re
import urllib.parse

from ..i18n import _
from .base import (
    BaseFormatHandler,
    Action,
    FormatResult,
    StatusInfo,
)
from ..system import get_native_install_cmd


# Handler for Flatpak application bundles (.flatpak)
class FlatpakBundleHandler(BaseFormatHandler):
    extensions = (".flatpak",)
    display_name = "Flatpak (.flatpak)"

    def extract_name(self, filepath: str) -> str:
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
        has_flatpak = system_info.get("has_flatpak", False)

        if has_flatpak:
            return self._has_flatpak(name, filepath)
        return self._no_flatpak(name, filepath, system_info)

    def _has_flatpak(self, name: str, filepath: str) -> FormatResult:
        fallback_cmd = f'flatpak install "{filepath}"'

        actions = [
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
                title=_("Install via Terminal (flatpak install)"),
                subtitle=f"flatpak install {os.path.basename(filepath)}",
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
                _("Flatpak Bundle Ready to Deploy"),
                _(
                    "<b>{name}</b> is an offline Flatpak bundle (.flatpak).\n"
                    "Flatpak is installed on your system, so you can install this right away."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Close"),
            close_suggested=False,
        )

    def _no_flatpak(
        self,
        name: str,
        filepath: str,
        system_info: dict,
    ) -> FormatResult:
        actions: list[Action] = []

        flatpak_install_cmd = get_native_install_cmd("flatpak")
        actions.append(
            Action(
                title=_("Install Flatpak"),
                subtitle=_("Install the Flatpak package manager through your software center"),
                icon_name="system-software-install-symbolic",
                action_type="packagekit_install",
                payload="flatpak",
                dialog_heading=_("Flatpak Installation"),
                dialog_body=_(
                    "No graphical software store or PackageKit service was found.\n"
                    "You can install Flatpak via terminal with this command:"
                ),
                fallback_command=flatpak_install_cmd,
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

        native_pm = system_info.get("native_pm")
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
                _("Flatpak is Missing"),
                _(
                    "<b>{name}</b> is a Flatpak bundle (.flatpak).\n"
                    "Linux's favorite universal sandbox runtime is not installed on this machine."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Cancel"),
        )


# Handler for Flatpak reference files (.flatpakref)
class FlatpakRefHandler(BaseFormatHandler):
    extensions = (".flatpakref",)
    display_name = "Flatpak Reference (.flatpakref)"
    required_pm = "flatpak"

    def extract_name(self, filepath: str) -> str:
        if os.path.isfile(filepath):
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
        has_flatpak = system_info.get("has_flatpak", False)

        if has_flatpak:
            return self._has_flatpak(name, filepath)
        return self._no_flatpak(name, filepath, system_info)

    def _has_flatpak(self, name: str, filepath: str) -> FormatResult:
        fallback_cmd = f'flatpak install "{filepath}"'

        actions = [
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
                title=_("Install via Terminal (flatpak install)"),
                subtitle=f"flatpak install {os.path.basename(filepath)}",
                icon_name="utilities-terminal-symbolic",
                action_type="command",
                payload=fallback_cmd,
                dialog_heading=_("Terminal Installation"),
                dialog_body=_("Run this command in your terminal to install the package:"),
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "dialog-warning-symbolic",
                "warning",
                _("MIME Handler Took a Nap"),
                _(
                    "Your system has <b>Flatpak</b> installed, but the desktop didn't route "
                    "this <b>{name}</b> reference file properly.\n"
                    "PackageKit seems to have more important business to attend to."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Close"),
        )

    def _no_flatpak(
        self,
        name: str,
        filepath: str,
        system_info: dict,
    ) -> FormatResult:
        actions: list[Action] = []

        flatpak_install_cmd = get_native_install_cmd("flatpak")
        actions.append(
            Action(
                title=_("Install Flatpak"),
                subtitle=_("Install the Flatpak package manager through your software center"),
                icon_name="system-software-install-symbolic",
                action_type="packagekit_install",
                payload="flatpak",
                dialog_heading=_("Flatpak Installation"),
                dialog_body=_(
                    "No graphical software store or PackageKit service was found.\n"
                    "You can install Flatpak via terminal with this command:"
                ),
                fallback_command=flatpak_install_cmd,
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

        native_pm = system_info.get("native_pm")
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
                _("Flatpak is Missing"),
                _(
                    "<b>{name}</b> is a Flatpak reference file (.flatpakref).\n"
                    "Linux's favorite universal sandbox runtime is not installed on this machine."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Cancel"),
        )

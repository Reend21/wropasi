# Snap (.snap) format handler.

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


class SnapHandler(BaseFormatHandler):
    extensions = (".snap",)
    display_name = "Snap (.snap)"

    def extract_name(self, filepath: str) -> str:
        base = os.path.basename(filepath)
        cleaned = re.sub(r"\.snap$", "", base, flags=re.I)
        cleaned = cleaned.split("_")[0]
        parts = re.split(r"-(?=\d)", cleaned)
        return parts[0]

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name = self.extract_name(filepath)
        has_snap = system_info.get("has_snap", False)

        if has_snap:
            return self._has_snap(name, filepath)
        return self._no_snap(name, filepath, system_info)

    def _has_snap(self, name: str, filepath: str) -> FormatResult:
        fallback_cmd = f'sudo snap install --dangerous "{filepath}"'

        actions = [
            Action(
                title=_("Install via Terminal (snap install)"),
                subtitle=f"snap install --dangerous {os.path.basename(filepath)}",
                icon_name="utilities-terminal-symbolic",
                action_type="command",
                payload=fallback_cmd,
                dialog_heading=_("Terminal Installation"),
                dialog_body=_(
                    "Snap local packages require the --dangerous flag since they are not\n"
                    "verified by the Snap Store. Run this command in your terminal:"
                ),
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                _("Snap Package Ready"),
                _(
                    "<b>{name}</b> is a Snap package (.snap).\n"
                    "Snap is installed on your system, so you can install this right away.\n"
                    "Note: local Snap packages need the <b>--dangerous</b> flag because they are "
                    "not verified by the Snap Store."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("OK"),
            close_suggested=False,
        )

    def _no_snap(
        self,
        name: str,
        filepath: str,
        system_info: dict,
    ) -> FormatResult:
        actions: list[Action] = []

        snap_install_cmd = get_native_install_cmd("snapd")
        actions.append(
            Action(
                title=_("Install Snap"),
                subtitle=_("Add Snap package manager support to your system via Software Center"),
                icon_name="folder-download-symbolic",
                action_type="packagekit_install",
                payload="snapd",
                dialog_heading=_("Snap Installation"),
                dialog_body=_(
                    "No graphical software store or PackageKit service was found.\n"
                    "You can install Snap via terminal with this command:"
                ),
                fallback_command=snap_install_cmd,
            )
        )

        if system_info.get("has_flatpak"):
            actions.append(
                Action(
                    title=_("Search on Flathub"),
                    subtitle=_("Check the universal sandbox emporium for this app"),
                    icon_name="edit-find-symbolic",
                    action_type="url",
                    payload=f"https://flathub.org/apps/search?q={urllib.parse.quote(name)}",
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
                _("Snap is Not Installed"),
                _(
                    "<b>{name}</b> is a Snap package (.snap).\n"
                    "Your system does not have Snap installed to run it.\n"
                    "Snap is Canonical's universal package format that works across many Linux distributions."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("OK"),
        )

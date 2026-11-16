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
                dialog_body=_("Run this command in your terminal to install the Snap package:"),
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                _("Snap Package Ready"),
                _(
                    "<b>{name}</b> is a Snap package (.snap).\n"
                    "Snap is installed on your system, so you can install this right away."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Close"),
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
                title=_("Install Snap (snapd)"),
                subtitle=_("Add Snap package manager support to your system"),
                icon_name="system-software-install-symbolic",
                action_type="command",
                payload=snap_install_cmd,
                dialog_heading=_("Snap Installation"),
                dialog_body=_(
                    "You can install the Snap package manager via terminal with this command:"
                ),
            )
        )

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
                _("Snapd is Nowhere to be Found"),
                _(
                    "<b>{name}</b> is a Snap package (.snap).\n"
                    "Your system does not have snapd installed to run it."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("Cancel"),
        )

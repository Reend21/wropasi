# ! Snap format handler.

from __future__ import annotations

import os
import re
import urllib.parse

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
                title="Terminal ile Kur (snap install)",
                subtitle=f"snap install --dangerous {os.path.basename(filepath)}",
                icon_name="utilities-terminal-symbolic",
                action_type="command",
                payload=fallback_cmd,
                dialog_heading="Terminal ile Kurulum",
                dialog_body="Snap paketini terminalde şu komutla kurabilirsiniz:",
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                "Bu paket sisteminizde çalışabilir.",
                f"<b>{name}</b> bir Snap paketidir (.snap).\n"
                f"Sisteminizde Snap kurulu olduğu için bu paketi kurabilirsiniz.",
            ),
            actions=actions,
            close_label="Kapat",
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
                title="Snap'i (snapd) Kur",
                subtitle="Sisteminize Snap paket yöneticisi desteğini kurun",
                icon_name="system-software-install-symbolic",
                action_type="command",
                payload=snap_install_cmd,
                dialog_heading="Snap Kurulumu",
                dialog_body=(
                    "Snap paket yöneticisini terminal üzerinden şu komutla kurabilirsiniz:"
                ),
            )
        )

        if system_info.get("has_flatpak"):
            actions.append(
                Action(
                    title="Flathub'da Ara",
                    subtitle="Evrensel yazılım mağzasında paketinizi arayın",
                    icon_name="system-software-install-symbolic",
                    action_type="url",
                    payload=f"https://flathub.org/apps/search?q={urllib.parse.quote(name)}",
                )
            )

        native_pm = system_info.get("native_pm")
        actions.append(
            Action(
                title="Uyumlu sürümü manuel ara",
                subtitle="Genel ağ üzerinden paketi manuel arayın.",
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
                "Snap Kurulu Değil",
                f"<b>{name}</b> bir Snap paketidir (.snap).\n"
                "Sisteminizde Snap paket yöneticisi (snapd) kurulu değil.",
            ),
            actions=actions,
            close_label="İptal",
        )

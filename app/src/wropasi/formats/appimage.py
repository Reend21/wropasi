# AppImage (.AppImage) format handler.

from __future__ import annotations

import os
import re

from ..i18n import _
from .base import BaseFormatHandler, FormatResult, StatusInfo


class AppImageHandler(BaseFormatHandler):
    extensions = (".appimage",)
    display_name = "AppImage (.AppImage)"
    required_pm = None  # Portable bundle; does not require a native package manager

    def extract_name(self, filepath: str) -> str:
        base = os.path.basename(filepath)
        cleaned = re.sub(r"\.appimage$", "", base, flags=re.I)
        cleaned = re.sub(
            r"-(x86_64|aarch64|armhf|i686|x64)$", "", cleaned, flags=re.I
        )
        parts = re.split(r"-(?=\d)", cleaned)
        return parts[0]

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name = self.extract_name(filepath)

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                _("Surprise! This actually runs everywhere."),
                _(
                    "<b>{name}</b> is an AppImage. Believe it or not, these portable bundles "
                    "work on virtually any Linux distro without throwing a tantrum. "
                    "Instead of launching it raw, you might want to use <b>Gear Lever</b> or "
                    "<b>AppImageLauncher</b> to integrate it into your desktop."
                ).format(name=name),
            ),
            close_label=_("All right"),
            close_suggested=True,
        )

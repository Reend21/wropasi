# ! AppImage format handler.

from __future__ import annotations

import os
import re

from .base import BaseFormatHandler, FormatResult, StatusInfo


class AppImageHandler(BaseFormatHandler):
    extensions = (".appimage",)
    display_name = "AppImage (.AppImage)"
    required_pm = None          # Yerel PM gerektirmez

    def extract_name(self, filepath: str) -> str:
        base = os.path.basename(filepath)
        cleaned = re.sub(r"\.appimage$", "", base, flags=re.I)
        cleaned = re.sub(r"-(x86_64|aarch64|armhf|i686|x64)$", "", cleaned, flags=re.I)
        parts = re.split(r"-(?=\d)", cleaned)
        return parts[0]

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name = self.extract_name(filepath)

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                "Belki şaşıracaksın ama, bu her yerde çalışır!",
                f"<b>{name}</b> bir AppImage paketidir. "
                "Aplikasyon Imajları (.AppImage) dosyaları taşınabilir ve tüm Linux "
                "sistemlerinde çalışır. Direkt çalıştırmak yerine <b>Gear Level</b> veya "
                "<b>AppImage Launcher</b> kullanarak bu Aplikasyon Imajını sisteminize "
                "yükleyebilirsiniz.",
            ),
            close_label="Peki",
            close_suggested=True,
        )

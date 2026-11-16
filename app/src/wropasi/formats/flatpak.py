# ! Flatpak handler

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

# ! Flatpak application bundle (.flatpak)
class FlatpakBundleHandler(BaseFormatHandler):
    extensions = (".flatpak",)
    display_name = "Flatpak (.flatpak)"

    def extract_name(self, filepath: str) -> str:
        base = os.path.basename(filepath)
        name, _ = os.path.splitext(base)
        cleaned = re.sub(r"[-.](x86_64|aarch64|armv7hl|armhf|i686|noarch|ppc64le|s390x|x64)$", "", name, flags=re.I)
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
                title="Yazılım Mağazası ile Aç",
                subtitle="Dosyayı sistemdeki yazılım mağazasına veya PackageKit arayüzüne yönlendir",
                icon_name="system-software-install-symbolic",
                action_type="packagekit_file",
                payload=filepath,
                dialog_heading="Yazılım Mağazası / PackageKit Açılamadı",
                dialog_body=(
                    "Sisteminizde PackageKit oturum servisi veya grafiksel bir "
                    "yazılım mağazası başlatılamadı.\n"
                    "Dosyayı terminalden doğrudan şu komutla kurabilirsiniz:"
                ),
                fallback_command=fallback_cmd,
            ),
            Action(
                title="Terminal ile Kur (flatpak install)",
                subtitle=f"flatpak install {os.path.basename(filepath)}",
                icon_name="utilities-terminal-symbolic",
                action_type="command",
                payload=fallback_cmd,
                dialog_heading="Terminal ile Kurulum",
                dialog_body="Terminalde şu komutu çalıştırarak paketi doğrudan kurabilirsiniz:",
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                "Bu paket sisteminizde çalışabilir.",
                f"<b>{name}</b> bir Flatpak uygulama paketidir (.flatpak).\n"
                f"Sisteminizde Flatpak kurulu olduğu için bu paketi kurabilirsiniz.",
            ),
            actions=actions,
            close_label="Kapat",
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
                title="Flatpak'i Kur",
                subtitle="Yazılım mağazanız aracılığıyla Flatpak paket yöneticisini kurun",
                icon_name="system-software-install-symbolic",
                action_type="packagekit_install",
                payload="flatpak",
                dialog_heading="Flatpak Kurulumu",
                dialog_body=(
                    "Grafiksel yazılım mağazası veya PackageKit servisi bulunamadı.\n"
                    "Flatpak paketini terminal üzerinden şu komutla kurabilirsiniz:"
                ),
                fallback_command=flatpak_install_cmd,
            )
        )

        if system_info.get("has_snap"):
            actions.append(
                Action(
                    title="Snap Store'da Ara",
                    subtitle="Cannonical'ın standart yazılım mağzasında paketinizi arayın",
                    icon_name="system-software-install-symbolic",
                    action_type="url",
                    payload=f"https://snapcraft.io/search?q={urllib.parse.quote(name)}",
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
                "Flatpak Kurulu Değil",
                f"<b>{name}</b> bir Flatpak paketidir (.flatpak).\n"
                "Linux'un evrensel paket yöneticisi Flatpak sisteminizde kurulu değil.",
            ),
            actions=actions,
            close_label="İptal",
        )


# ! if flatpak installed, then the mime handler is broken
# ! if flatpak not installed, then show a dialog that tells to install flatpak
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
        cleaned = re.sub(r"[-.](x86_64|aarch64|armv7hl|armhf|i686|noarch|ppc64le|s390x|x64)$", "", name, flags=re.I)
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
                title="Yazılım Mağazası ile Aç",
                subtitle="Dosyayı sistemdeki yazılım mağazasına veya PackageKit arayüzüne yönlendir",
                icon_name="system-software-install-symbolic",
                action_type="packagekit_file",
                payload=filepath,
                dialog_heading="Yazılım Mağazası / PackageKit Açılamadı",
                dialog_body=(
                    "Sisteminizde PackageKit oturum servisi veya grafiksel bir "
                    "yazılım mağazası başlatılamadı.\n"
                    "Dosyayı terminalden doğrudan şu komutla kurabilirsiniz:"
                ),
                fallback_command=fallback_cmd,
            ),
            Action(
                title="Terminal ile Kur (flatpak install)",
                subtitle=f"flatpak install {os.path.basename(filepath)}",
                icon_name="utilities-terminal-symbolic",
                action_type="command",
                payload=fallback_cmd,
                dialog_heading="Terminal ile Kurulum",
                dialog_body="Terminalde şu komutu çalıştırarak paketi doğrudan kurabilirsiniz:",
            ),
        ]

        return FormatResult(
            status=StatusInfo(
                "dialog-warning-symbolic",
                "warning",
                "MIME Handler is not working",
                f"Your system has Flatpak package manager but looks like "
                f"your system didn't directed you properly to install the package.\n"
                f"Now we can try to fix the false Flatpak handling or you can install the package right now ",
            ),
            actions=actions,
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
                title="Flatpak'i Kur",
                subtitle="Yazılım mağazanız aracılığıyla Flatpak paket yöneticisini kurun",
                icon_name="system-software-install-symbolic",
                action_type="packagekit_install",
                payload="flatpak",
                dialog_heading="Flatpak Kurulumu",
                dialog_body=(
                    "Grafiksel yazılım mağazası veya PackageKit servisi bulunamadı.\n"
                    "Flatpak paketini terminal üzerinden şu komutla kurabilirsiniz:"
                ),
                fallback_command=flatpak_install_cmd,
            )
        )

        if system_info.get("has_snap"):
            actions.append(
                Action(
                    title="Snap Store'da Ara",
                    subtitle="Cannonical'ın standart yazılım mağzasında paketinizi arayın",
                    icon_name="system-software-install-symbolic",
                    action_type="url",
                    payload=f"https://snapcraft.io/search?q={urllib.parse.quote(name)}",
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
                "Flatpak Kurulu Değil",
                f"<b>{name}</b> bir Flatpak paketidir (.flatpakref).\n"
                "Linux'un evrensel paket yöneticisi Flatpak sisteminizde kurulu değil.",
            ),
            actions=actions,
            close_label="İptal",
        )

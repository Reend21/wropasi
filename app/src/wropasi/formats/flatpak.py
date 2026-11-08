# Flatpak (.flatpak) ve Flatpak Referansı (.flatpakref) format handler'ları.

from __future__ import annotations

import os
import urllib.parse

from .base import (
    BaseFormatHandler,
    NativeFormatHandler,
    Action,
    FormatResult,
    StatusInfo,
)
from ..system import get_native_install_cmd


# Flatpak paket dosyaları (.flatpak) için handler.
# Flatpak yerel bir PM olmadığından (native_pm listesinde yok),
# NativeFormatHandler mantığıyla her zaman "uyumsuz" sonucu verir.
class FlatpakBundleHandler(NativeFormatHandler):
    extensions = (".flatpak",)
    display_name = "Flatpak (.flatpak)"
    required_pm = "flatpak"


# .flatpakref dosyaları için özel handler.
# İki durumu vardır:
# - Flatpak kuruluysa  → PackageKit/mağaza entegrasyonu arızalanmış demektir.
# - Flatpak kurulu değilse → Flatpak'i kurması gerektiğini bildirir.
class FlatpakRefHandler(BaseFormatHandler):
    extensions = (".flatpakref",)
    display_name = "Flatpak Referansı (.flatpakref)"
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
        return name.split("_")[0].split("-")[0]

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name = self.extract_name(filepath)
        has_flatpak = system_info.get("has_flatpak", False)

        if has_flatpak:
            return self._has_flatpak(name, filepath)
        return self._no_flatpak(name, filepath, system_info)

    # -- Flatpak kurulu ama PackageKit çalışmıyor ------------------------------

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
                "PackageKit Entegrasyonu Çalışmıyor",
                f"Sisteminizde <b>Flatpak</b> kurulu, ancak PackageKit veya yazılım mağazası "
                f"entegrasyonu bu dosyayı doğrudan işleyemedi.\n"
                f"<b>{name}</b> paketi normal şartlarda doğrudan yazılım mağazanız tarafından "
                f"açılmalıydı, ama sanırım PackageKit'in size hizmet etmekten daha önemli "
                f"işleri var..",
            ),
            actions=actions,
        )

    # -- Flatpak kurulu değil --------------------------------------------------

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

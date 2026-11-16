# ! base structre for format handling

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ! status info
@dataclass
class StatusInfo:
    icon_name: str
    css_class: str   # "success", "warning", "error"
    title: str
    body: str


# ! actions
# ? "url"                 – open payload url with xdg-open
# ? "command"             – show the payload command
# ? "packagekit_file"     – open app with the app center, if fail, show fallback dialog
# ? "packagekit_install"  – install ap with app center, if fail, show fallback dialog
# ? "alien"               – alien translation

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

@dataclass
class FormatResult:
    status: StatusInfo
    actions: list[Action] = field(default_factory=list)
    close_label: str = "Kapat"
    close_suggested: bool = False


# ! base format handler structre 
class BaseFormatHandler(ABC):
    extensions: tuple[str, ...] = ()
    display_name: str = ""
    required_pm: str | None = None

    # ! get app name
    @abstractmethod
    def extract_name(self, filepath: str) -> str:
        ...

    # ! format result handler
    @abstractmethod
    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        ...


# ! PM detection base
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
        cleaned = re.sub(r"[-.](x86_64|aarch64|armv7hl|armhf|i686|noarch|ppc64le|s390x|x64)$", "", name, flags=re.I)
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
        import os

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
                title="Terminal ile Kur",
                subtitle=f"{fallback_cmd}",
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
                f"<b>{name}</b> paketi sisteminizle uyumludur.",
            ),
            actions=actions,
            close_label="Kapat",
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

        native_str = PM_DISPLAY.get(native_pm, native_pm or "bilinmiyor")
        ext = os.path.splitext(filepath)[1].lower()

        actions: list[Action] = []

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

        can_alien = (
            system_info.get("has_alien")
            and ext in (".deb", ".rpm")
            and native_pm in ("dpkg", "apt", "rpm", "dnf", "zypper")
        )
        if can_alien:
            target_str = "DEB" if native_pm in ("dpkg", "apt") else "RPM"
            actions.append(
                Action(
                    title="alien ile Dönüştür (Önerilemz)",
                    subtitle=f"Paketi {target_str} formatına çevirin (Sadece son çareniz buysa)",
                    icon_name="system-run-symbolic",
                    action_type="alien",
                    payload=filepath,
                )
            )

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
                "Uyumsuz Paket",
                f"<b>{name}</b>, <b>{self.display_name}</b> formatını kullanıyor; "
                f"sisteminiz ise <b>{native_str}</b> kullanıyor.\n"
                "Bu paket sisteminizle uyumsuzdur ve bu yüzden sisteminize yüklenemez.",
            ),
            actions=actions,
            close_label="İptal",
        )

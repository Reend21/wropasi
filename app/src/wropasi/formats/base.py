"""Format handler'lar için temel sınıflar ve veri yapıları."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class StatusInfo:
    """Kullanıcıya gösterilecek durum bilgisi (ikon + başlık + açıklama)."""

    icon_name: str
    css_class: str   # "success", "warning", "error"
    title: str
    body: str


@dataclass
class Action:
    """Kullanıcıya sunulacak tek bir aksiyon satırı.

    action_type değerleri
    ---------------------
    "url"                 – payload URL'sini xdg-open ile aç.
    "command"             – Komutu (payload) gösteren bir diyalog aç.
    "packagekit_file"     – Dosyayı (payload) PackageKit/mağaza ile açmayı dene,
                            başarısız olursa fallback_command'ı göster.
    "packagekit_install"  – Paket adını (payload) PackageKit/mağaza ile kurmayı dene,
                            başarısız olursa fallback_command'ı göster.
    "alien"               – payload dosyasını alien ile dönüştürme talimatı göster.
    """

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
    """Bir format handler'ının analiz sonucu.

    Window bu yapıyı alır ve jenerik olarak render eder:
    durum bannerı + aksiyon listesi + kapat butonu.
    """

    status: StatusInfo
    actions: list[Action] = field(default_factory=list)
    close_label: str = "Kapat"
    close_suggested: bool = False


class BaseFormatHandler(ABC):
    """Tüm format handler'larının uygulaması gereken soyut temel sınıf."""

    extensions: tuple[str, ...] = ()
    display_name: str = ""
    required_pm: str | None = None

    @abstractmethod
    def extract_name(self, filepath: str) -> str:
        """Dosyadan uygulama/paket adını çıkarır."""
        ...

    @abstractmethod
    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        """Dosyayı sistem bilgilerine göre analiz edip sonuç döner."""
        ...


class NativeFormatHandler(BaseFormatHandler):
    """Yerel paket yöneticisine bağlı formatlar için ortak temel (deb, rpm, vb.).

    Eğer ``required_pm`` sistemin yerel PM'i ile eşleşiyorsa "uyumlu",
    değilse "uyumsuz" sonucu üretir; uyumsuz durumda standart aksiyon
    listesi (Flathub, Snap Store, alien, web arama) sunar.
    """

    def extract_name(self, filepath: str) -> str:
        import os

        base = os.path.basename(filepath)
        name, _ = os.path.splitext(base)
        return name.split("_")[0].split("-")[0]

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name = self.extract_name(filepath)
        native_pm = system_info.get("native_pm")

        if native_pm == self.required_pm:
            return FormatResult(
                status=StatusInfo(
                    "emblem-ok-symbolic",
                    "success",
                    "Bu paket sisteminizde çalışabilir.",
                    f"<b>{name}</b> paketi sisteminizle uyumludur.",
                ),
                close_label="Peki",
                close_suggested=True,
            )

        return self._build_incompatible(name, filepath, native_pm, system_info)

    # ------------------------------------------------------------------

    def _build_incompatible(
        self,
        name: str,
        filepath: str,
        native_pm: str | None,
        system_info: dict,
    ) -> FormatResult:
        import urllib.parse
        from ..system import PM_DISPLAY

        native_str = PM_DISPLAY.get(native_pm, native_pm or "bilinmiyor")

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

        if system_info.get("has_alien"):
            actions.append(
                Action(
                    title="alien ile Dönüştür (Önerilemz)",
                    subtitle=f"Paketi {native_str} formatına çevirin (Sadece son çareniz buysa)",
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

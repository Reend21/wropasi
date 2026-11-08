# ! Format handler registry

from __future__ import annotations

from .base import BaseFormatHandler, FormatResult, StatusInfo, Action  # noqa: F401
from .deb import DebHandler
from .rpm import RpmHandler
from .flatpak import FlatpakBundleHandler, FlatpakRefHandler
from .snap import SnapHandler
from .appimage import AppImageHandler

_HANDLERS: list[BaseFormatHandler] = [
    DebHandler(),
    RpmHandler(),
    FlatpakBundleHandler(),
    FlatpakRefHandler(),
    SnapHandler(),
    AppImageHandler(),
]

_REGISTRY: dict[str, BaseFormatHandler] = {}
for _handler in _HANDLERS:
    for _ext in _handler.extensions:
        _REGISTRY[_ext] = _handler


def get_handler(extension: str) -> BaseFormatHandler | None:
    return _REGISTRY.get(extension.lower())


def get_unknown_result(ext: str) -> FormatResult:
    """Tanınmayan format için varsayılan sonuç üretir."""
    return FormatResult(
        status=StatusInfo(
            "dialog-error-symbolic",
            "error",
            "Bu ne be?",
            f"<b>{ext or '(uzantısız)'}</b> formatını tanımıyoruz. Bu bizim eşşekliğimizse "
            "affola. Ancak bu paketleme sistemi ya çok niş, yada gerçek değil.",
        ),
    )

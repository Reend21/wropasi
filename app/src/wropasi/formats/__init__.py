# Format handler registry.

from __future__ import annotations

from ..i18n import _
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


# Generate fallback result for unknown / unsupported formats.
def get_unknown_result(ext: str) -> FormatResult:
    ext_label = ext or _("(no extension)")
    return FormatResult(
        status=StatusInfo(
            "dialog-error-symbolic",
            "error",
            _("What on earth is this?"),
            _(
                "We don't recognize the <b>{ext}</b> format. If this is our blunder, "
                "our apologies. But this packaging system is either wildly niche or straight up made up."
            ).format(ext=ext_label),
        ),
        close_label=_("Dismiss"),
        close_suggested=True,
    )

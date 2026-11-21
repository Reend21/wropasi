# Format handler registry.

from __future__ import annotations

import os
import re

from ..i18n import _
from .base import BaseFormatHandler, FormatResult, StatusInfo, Action  # noqa: F401
from .deb import DebHandler
from .rpm import RpmHandler
from .flatpak import FlatpakBundleHandler, FlatpakRefHandler
from .snap import SnapHandler
from .appimage import AppImageHandler
from .pacman import PkgTarHandler, PKGBUILDHandler

_HANDLERS: list[BaseFormatHandler] = [
    DebHandler(),
    RpmHandler(),
    FlatpakBundleHandler(),
    FlatpakRefHandler(),
    SnapHandler(),
    AppImageHandler(),
    PkgTarHandler(),
    PKGBUILDHandler(),
]

_REGISTRY: dict[str, BaseFormatHandler] = {}
for _handler in _HANDLERS:
    for _ext in _handler.extensions:
        _REGISTRY[_ext] = _handler


def get_handler(filepath_or_ext: str) -> BaseFormatHandler | None:
    # 1. Bare filename: e.g. "PKGBUILD"
    basename = os.path.basename(filepath_or_ext)
    if basename.upper() == "PKGBUILD":
        return _REGISTRY.get("PKGBUILD")

    # 2. Arch Linux package compound extension: .pkg.tar(.zst|.xz|...)
    if re.search(r"\.pkg\.tar(\.[a-z0-9]+)?$", filepath_or_ext, re.I):
        return _REGISTRY.get(".pkg.tar")

    # 3. Standard extension lookup
    ext = os.path.splitext(filepath_or_ext)[1].lower()
    if ext in _REGISTRY:
        return _REGISTRY[ext]

    # 4. Direct match (e.g. if ".deb" was passed directly)
    return _REGISTRY.get(filepath_or_ext.lower())


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
        close_label=_("OK"),
        close_suggested=True,
    )

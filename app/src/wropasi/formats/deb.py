# Debian (.deb) format handler.

from __future__ import annotations

from .base import NativeFormatHandler


class DebHandler(NativeFormatHandler):
    extensions = (".deb",)
    display_name = "Debian (.deb)"
    required_pm = "dpkg"
    compatible_pms = ("dpkg", "apt")

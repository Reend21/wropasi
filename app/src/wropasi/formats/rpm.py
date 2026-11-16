# RPM (.rpm) format handler.

from __future__ import annotations

from .base import NativeFormatHandler


class RpmHandler(NativeFormatHandler):
    extensions = (".rpm",)
    display_name = "RPM (.rpm)"
    required_pm = "rpm"
    compatible_pms = ("rpm", "dnf", "zypper")

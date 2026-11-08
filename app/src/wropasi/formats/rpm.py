"""RPM (.rpm) format handler."""

from .base import NativeFormatHandler


class RpmHandler(NativeFormatHandler):
    extensions = (".rpm",)
    display_name = "RPM (.rpm)"
    required_pm = "rpm"

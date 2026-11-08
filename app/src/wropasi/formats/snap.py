"""Snap (.snap) format handler."""

from .base import NativeFormatHandler


class SnapHandler(NativeFormatHandler):
    extensions = (".snap",)
    display_name = "Snap (.snap)"
    required_pm = "snap"

# Pacman / AUR format handlers.
#
# PkgTarHandler  – Arch Linux binary packages (.pkg.tar.zst / .pkg.tar.xz / …)
#                  Registered under the virtual extension ".pkg.tar".
#                  Performs a content check (looks for .PKGINFO) so that
#                  ordinary .tar.zst archives never trigger a wropasi dialog.
#
# PKGBUILDHandler – Arch / AUR source-build recipes (bare filename "PKGBUILD").
#                   No content check is needed; nobody names a random file PKGBUILD.

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tarfile
import urllib.parse

from ..i18n import _
from .base import (
    NativeFormatHandler,
    BaseFormatHandler,
    Action,
    FormatResult,
    StatusInfo,
)
from ..system import get_native_install_cmd


# ---------------------------------------------------------------------------
# Arch Linux binary package handler
# ---------------------------------------------------------------------------

class PkgTarHandler(NativeFormatHandler):
    extensions    = (".pkg.tar",)       # virtual compound-extension key
    display_name  = "Arch Linux Package (.pkg.tar)"
    compatible_pms = ("pacman",)

    def _read_pkginfo_name(self, filepath: str) -> str | None:
        """Attempt to read the exact pkgname from .PKGINFO inside the archive."""
        try:
            with tarfile.open(filepath, "r:*") as tf:
                try:
                    f = tf.extractfile(".PKGINFO")
                    if f:
                        for line in f:
                            s = line.decode("utf-8", "ignore").strip()
                            if s.startswith("pkgname ="):
                                return s.split("=", 1)[1].strip()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            proc = subprocess.run(
                ["tar", "-xOf", filepath, ".PKGINFO"],
                capture_output=True, text=True, timeout=5,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    s = line.strip()
                    if s.startswith("pkgname ="):
                        return s.split("=", 1)[1].strip()
        except Exception:
            pass
        return None

    def extract_name(self, filepath: str) -> str:
        if os.path.exists(filepath):
            exact = self._read_pkginfo_name(filepath)
            if exact:
                return exact

        basename = os.path.basename(filepath)
        # Strip compound suffix: foo-1.0-1-x86_64.pkg.tar.zst → foo-1.0-1-x86_64
        name = re.sub(
            r"\.pkg\.tar(\.(zst|xz|gz|bz2|lz4|lzop|lzo|lz|sz|Z))?$",
            "",
            basename,
            flags=re.I,
        )
        # Strip version-pkgrel-arch: foo-1.0-1-x86_64 → foo
        name = re.sub(r"-\d.*$", "", name)
        return name or basename

    @staticmethod
    def _is_arch_package(filepath: str) -> bool:
        """Return True if the archive contains a .PKGINFO entry (Arch package marker)."""
        # Try Python tarfile first – supports gz, bz2, xz natively.
        try:
            with tarfile.open(filepath, "r:*") as tf:
                for member in tf:
                    if member.name == ".PKGINFO":
                        return True
            return False
        except (tarfile.CompressionError, tarfile.ReadError):
            pass   # fall through to system tar (handles zstd on Python < 3.14)
        except Exception:
            pass

        # Fallback: system tar via libarchive (handles zstd on Arch and most distros).
        try:
            proc = subprocess.run(
                ["tar", "tf", filepath],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode == 0:
                return ".PKGINFO" in proc.stdout.splitlines()
        except (OSError, subprocess.TimeoutExpired):
            pass

        return False

    def analyze(self, filepath: str, system_info: dict) -> FormatResult | None:
        # Content gate: if the file exists and isn't an Arch package, signal the
        # caller to close silently by returning None.
        # Non-existent paths (test / mock mode) bypass the check.
        if os.path.exists(filepath) and not self._is_arch_package(filepath):
            return None
        # Delegate to NativeFormatHandler – it already handles pacman in
        # _build_compatible(), and alien is excluded automatically in
        # _build_incompatible() because ext ≠ ".deb" / ".rpm".
        return super().analyze(filepath, system_info)


# ---------------------------------------------------------------------------
# PKGBUILD source-recipe handler
# ---------------------------------------------------------------------------

class PKGBUILDHandler(BaseFormatHandler):
    extensions   = ("PKGBUILD",)        # bare filename, not an extension
    display_name = "PKGBUILD (Arch / AUR)"

    def extract_name(self, filepath: str) -> str:
        """Read pkgname= from the PKGBUILD; fall back to parent directory name."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("pkgname="):
                        val = line.split("=", 1)[1].strip().strip("'\"()")
                        val = val.split()[0].strip("'\"")
                        if val:
                            return val
        except Exception:
            pass
        parent = os.path.basename(os.path.dirname(os.path.abspath(filepath)))
        if parent and parent != "/":
            return parent
        return "package"

    def analyze(self, filepath: str, system_info: dict) -> FormatResult:
        name      = self.extract_name(filepath)
        native_pm = system_info.get("native_pm")
        # Treat the system as makepkg-capable when native_pm is pacman (covers
        # test / mock mode) or when makepkg is actually on PATH.
        has_makepkg = (
            native_pm == "pacman"
            or shutil.which("makepkg") is not None
        )

        if has_makepkg:
            return self._build_compatible(name, filepath)
        return self._build_incompatible(name, filepath, native_pm, system_info)

    # -- compatible path -------------------------------------------------

    def _build_compatible(self, name: str, filepath: str) -> FormatResult:
        pkg_dir   = os.path.dirname(os.path.abspath(filepath))
        build_cmd = f'cd "{pkg_dir}" && makepkg -si'

        return FormatResult(
            status=StatusInfo(
                "emblem-ok-symbolic",
                "success",
                _("PKGBUILD Detected — Arch Territory"),
                _(
                    "<b>{name}</b> is an Arch Linux PKGBUILD source recipe.\n"
                    "makepkg is available on your system, so you can build and "
                    "install it right here."
                ).format(name=name),
            ),
            actions=[
                Action(
                    title=_("Build & Install via Terminal (makepkg -si)"),
                    subtitle="makepkg -si",
                    icon_name="utilities-terminal-symbolic",
                    action_type="command",
                    payload=build_cmd,
                    dialog_heading=_("Build & Install"),
                    dialog_body=_(
                        "Run this command in your terminal to build and install the package:"
                    ),
                ),
            ],
            close_label=_("OK"),
            close_suggested=False,
        )

    # -- incompatible path -----------------------------------------------

    def _build_incompatible(
        self,
        name: str,
        filepath: str,
        native_pm: str | None,
        system_info: dict,
    ) -> FormatResult:
        actions: list[Action] = []

        if system_info.get("has_flatpak"):
            actions.append(
                Action(
                    title=_("Search on Flathub"),
                    subtitle=_("Check the universal sandbox emporium for this app"),
                    icon_name="edit-find-symbolic",
                    action_type="url",
                    payload=f"https://flathub.org/apps/search?q={urllib.parse.quote(name)}",
                )
            )

        if system_info.get("has_snap"):
            actions.append(
                Action(
                    title=_("Search on Snap Store"),
                    subtitle=_("Search Canonical's walled-ish garden for this app"),
                    icon_name="edit-find-symbolic",
                    action_type="url",
                    payload=f"https://snapcraft.io/search?q={urllib.parse.quote(name)}",
                )
            )

        actions.append(
            Action(
                title=_("Search the Web Manually"),
                subtitle=_("Hunt for a compatible installer across the wild internet"),
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
                _("Wrong Package, Silly!"),
                _(
                    "<b>{name}</b> is an Arch Linux PKGBUILD source recipe, "
                    "but your system does not use Pacman or makepkg.\n"
                    "This can only be built on an Arch-based system."
                ).format(name=name),
            ),
            actions=actions,
            close_label=_("OK"),
        )

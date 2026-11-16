"""Internationalization (i18n) support for wropasi."""

from __future__ import annotations

import gettext
import os
from pathlib import Path

APP_ID = "io.github.wropasi"


def _get_locale_dir() -> Path:
    if "WROPASI_LOCALE_DIR" in os.environ:
        return Path(os.environ["WROPASI_LOCALE_DIR"])

    # 1. Package-local locale directory: app/src/wropasi/locale
    pkg_locale = Path(__file__).resolve().parent / "locale"
    if (pkg_locale / "tr" / "LC_MESSAGES" / f"{APP_ID}.mo").exists():
        return pkg_locale

    # 2. User local install: ~/.local/share/locale
    user_locale = Path.home() / ".local" / "share" / "locale"
    if (user_locale / "tr" / "LC_MESSAGES" / f"{APP_ID}.mo").exists():
        return user_locale

    # 3. System install: /usr/share/locale
    sys_locale = Path("/usr/share/locale")
    if (sys_locale / "tr" / "LC_MESSAGES" / f"{APP_ID}.mo").exists():
        return sys_locale

    return pkg_locale


_locale_dir = _get_locale_dir()

try:
    _trans = gettext.translation(
        domain=APP_ID,
        localedir=str(_locale_dir),
        fallback=True,
    )
    _ = _trans.gettext
    ngettext = _trans.ngettext
except Exception:
    _ = lambda s: s
    ngettext = lambda s, p, n: s if n == 1 else p

# ! constant variables

from textwrap import dedent

APP_ID = "io.github.wropasi"

DESKTOP_ENTRY = dedent("""\
    [Desktop Entry]
    Name=wropasi
    Comment=Wrong Package Silly! wropasi solves an UX problem about package management in modern distros
    Exec={exec_path} %f
    Icon={icon_name}
    Terminal=false
    NoDisplay=true
    Type=Application
    Categories=System;PackageManager;Settings;
    Keywords=package;install;deb;rpm;flatpak;snap;appimage;paket;
    MimeType=application/vnd.debian.binary-package;application/x-rpm;application/vnd.snap;application/vnd.flatpak;application/vnd.flatpakref;application/vnd.flatpak.ref;application/vnd.appimage;
""")

MIME_XML = dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info">

    <mime-type type="application/vnd.flatpak">
        <comment>Flatpak Application Bundle</comment>
        <comment xml:lang="tr">Flatpak Uygulama Paketi</comment>
        <acronym>Flatpak</acronym>
        <glob pattern="*.flatpak"/>
    </mime-type>

    <mime-type type="application/vnd.flatpakref">
        <comment>Flatpak Reference</comment>
        <comment xml:lang="tr">Flatpak Referans Dosyası</comment>
        <acronym>Flatpak</acronym>
        <glob pattern="*.flatpakref"/>
    </mime-type>

    <!-- AppImage (.AppImage / .appimage) -->
    <mime-type type="application/vnd.appimage">
        <comment>AppImage Application Bundle</comment>
        <comment xml:lang="tr">AppImage Uygulama Paketi</comment>
        <acronym>AppImage</acronym>
        <glob pattern="*.AppImage"/>
        <glob pattern="*.appimage"/>
        <magic priority="60">
        <match type="string" offset="8" value="AI\\x02"/>
        </magic>
    </mime-type>

    </mime-info>
""")

MIME_TYPES = [
    "application/vnd.debian.binary-package",
    "application/x-rpm",
    "application/vnd.snap",
    "application/vnd.flatpak",
    "application/vnd.flatpakref",
    "application/vnd.flatpak.ref",
    "application/vnd.appimage",
]

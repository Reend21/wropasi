const fs = require("fs")
const os = require("os")

const commandExists = require("command-exists")

let detectedPM = null

commandExists("rpm", function(err, commandExists) {
    if (commandExists) {
        detectedPM = "rpm"
        console.log(detectedPM, "tespit edildi")
        return
    } 
    else {
        console.log("bu paket yöneticisi hakkında bilgim yok..")
    }
})

commandExists("dpkg", function(err, commandExists) {
    if (commandExists) {
        detectedPM = "dpkg"
        console.log(detectedPM, "tespit edildi")
        return
    }
})

const appName = "wropasi"
const desktopFile = `[Desktop Entry]
Name=wropasi
Comment=An utility to solve an UX problem about package management in modern linux distributions
Exec=wropasi
Icon=./wropasi-logo
Terminal=true
Type=Application
Categories=GTK;Utility
Keywords=GTK;Adwaita;UX;Package;Package-Management`


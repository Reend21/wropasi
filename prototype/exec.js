const fs = require("fs")
const os = require("os")
const path = require("path")
const { execFileSync } = require("child_process")
const commandExists = require("command-exists")

const appID = "wropasi"
const home = os.homedir()
const dataHome = process.env.XDG_DATA_HOME || path.join(home, '.local/share');

const nodeBin = process.execPath
const scriptPath = fs.realpathSync(process.argv[1])

const appsDir = path.join(dataHome, "applications")
fs.mkdirSync(appsDir, {recursive: true})
const desktopFile = '${appID}.desktop'
fs.writeFileSync(path.join(appsDir, desktopFile),
`[Desktop Entry]
Name=wropasi
Comment=An utility to solve an UX problem about package management in modern linux distributions
Exec=${nodeBin} ${scriptPath} %f
Icon=./wropasi-logo
Terminal=true
NoDisplay=true
Type=Application
Categories=GTK;Utility
Keywords=GTK;Adwaita;UX;Package;Package-Management`
),  
execFileSync('update-desktop-database', [appsDir]);

function detectPM() {
    if (commandExists.sync("rpm")) return "rpm"
    if (commandExists.sync("dpkg")) return "dpkg"
    return null
}

const detectedPM = detectPM()

if (!detectedPM) {
    console.log("Bilgim yok...")
} else {
    console.log(detectedPM, "paket yöneticisi sisteminizde bulundu")
}

const file = process.argv[2];
if (!file) {
    console.log("dosya yok")
    process.exit(1)
}
const pmFormats = { ".rpm": "rpm", ".deb": "dpkg" }
const ext = path.extname(file).toLowerCase();
const filePM = pmFormats[ext]


if (!filePM) {
    console.log("Bu paketleme formatını tanımıyorum, formatın doğru olduğuna emin misin?")
} else if (!detectedPM) {
    console.log("Sistemde desteklemediğim/tanımadığım bir paket yöneticisine sahip olmalısınız.")
} else if (filePM === detectedPM) {
    console.log("Bu paket sisteminize gönül rahatlığıyla kurulabilir.")
} else {
    console.log(`Bu yazılım paketi ${ext} formatını kullanıyor, ancak sizin sisteminiz ${detectedPM} paketleme sistemini kullanıyor ve dolayısıyla bu yazılım sisteminize kurulamaz.`)
    console.warn("Genel ağ üzerinden yazılım paketinin sizin sisteminiz için paketlenmiş versiyonunu bulun, veya paket yöneticinizden yazılımı indirin.")
}

process.stdin.once('data', () => process.exit(0));

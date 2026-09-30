const commandExists = require("command-exists")

let detectedPM = null

commandExists("rpm", function(err, commandExists) {
    if (commandExists) {
        detectedPM = "rpm"
        console.log(detectedPM, "tespit edildi, define.js'ten yazıyorum")
        return
    } else {
        console.log("bu paket yöneticisi hakkında bilgim yok..")
    }
})

module.exports = { detectedPM };
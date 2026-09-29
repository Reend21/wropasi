![wropasi-logo](wropasi%20logo.png)

# wropasi (wrong package silly)

> wropasi still in development and only have a prototype that developed with node.js. The software will going to develop with Python + GTK4 in stable release.

wropasi, is an utility that solves an UX problem for the modern and user friendly Linux distributions.

## What does utility actually do?

Let me explain, in a regular user-friendly Linux distributions, when you install a package that doesn't compatible with your package manager (installing .rpm on Linux Mint for an example) then if you try to install it, it will open the app selection dialog that connected to your desktop enviroment or just will open your archive manager.

And this can be confusing for an new Linux user, because on Windows or MacOS you need to install just one package management. This is a problem because Linux has so many package maneger and package format. wropasi targets to solve this problem.

## How it is wropasi solves the problem?

wropasi, approach the problem with 2 simple method: **Inform the User** and **Guide the User**

With **Inform the User** method, we first want to inform the user that installed package isn't compatible with their system. wropasi will inform the user with nice and understandable text and symbolic image. Now the user knows that their system can't install the current package. But without any **Guide**, means leaving the user in the lurch.

And the **Guide the User** method solves that. After the text and symbolic images, now we give a few options to the user with the package, according to their native package management and the package format that they currently trying to install. Searching the package in distributions repositories, searching on flatpak or snap, converting to .deb & .rpm with alien and a few other for other package management. With this method, now the user informed and knows what to do. Bam!

## Screenshots

Placeholder, no screenshots or gifs yet.

## Development

Prototype of wropasi developed with just nodejs, for prototype development, there is no guide yet. Development guide will be released when project have a working version with python

## License

wropasi, licensed with GPL-3.0 License. Chec the LICENSE file for more information.

Icons that used on logo:
[Question icons created by Magnific - Flaticon](https://www.flaticon.com/free-icons/question "question icons")
[Alert icons created by Magnific - Flaticon](https://www.flaticon.com/free-icons/alert "alert icons")
[Road signs icons created by Jesus Chavarria - Flaticon](https://www.flaticon.com/free-icons/road-signs "road signs icons")
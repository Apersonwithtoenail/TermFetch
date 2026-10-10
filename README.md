# 🖥️ termfetch

**Fast, pretty system info for Linux. No dependencies.**

A lightweight alternative to neofetch — instant startup, accurate on
modern systems, and hackable. Pure Python 3 standard library.

## Install

    git clone https://github.com/Apersonwithtoenail/termfetch.git
    cd termfetch
    ./install.sh

Make sure ~/.local/bin is in your PATH. Then run:

    termfetch

Or without installing:

    ./termfetch.py

## Usage

    termfetch [OPTIONS]

      -n, --no-color     disable colors
      -c, --color        force colors
      -l, --logo NAME    pick a logo (default: auto)
          --json         print as JSON
      -V, --version      show version
      -h, --help         show this help

Pipe-friendly — --no-color plays nice with grep and tee.

    termfetch --json | jq .ram
    termfetch --no-color >> ~/system-specs.txt

## What it shows

| Field   | Source                                       |
|---------|----------------------------------------------|
| OS      | /etc/os-release                              |
| Kernel  | uname                                        |
| Uptime  | /proc/uptime                                 |
| Shell   | $SHELL, $ZSH_VERSION / $BASH_VERSION         |
| WM      | $XDG_CURRENT_DESKTOP + $XDG_SESSION_TYPE     |
| CPU     | /proc/cpuinfo                                |
| RAM     | /proc/meminfo                                |
| Disk    | statvfs("/")                                 |
| GPU     | lspci                                        |
| Display | xrandr                                       |

## Roadmap

- More logos (Debian, Ubuntu, Arch, Fedora)
- Theme files in ~/.config/termfetch/
- Wallpaper thumbnail support (kitty/sixel)
- Show running apps (PaperRuner, cava, tmux)

## License

MIT — see LICENSE.

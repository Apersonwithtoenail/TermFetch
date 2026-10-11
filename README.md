# 🖥️ termfetch

**Fast, pretty system info for Linux. No dependencies.**

Pure Python 3 standard library. Reads `/proc` and `/sys` directly.
Instantly shows your system info like fastfetch, with an amber/gradient look.

## Install

    git clone https://github.com/Apersonwithtoenail/termfetch.git
    cd termfetch
    ./install.sh

Make sure `~/.local/bin` is in your `PATH`. Then:

    termfetch

## Usage

    termfetch                # print system info
    termfetch --no-color     # for piping
    termfetch --json         # machine-readable

Live updates via `watch`:

    watch -n 1 -t termfetch

Ctrl+C to stop.

## What it shows

| Field   | Source                                   |
|---------|------------------------------------------|
| OS      | /etc/os-release                          |
| Kernel  | uname                                    |
| Uptime  | /proc/uptime                             |
| Load    | /proc/loadavg                            |
| Shell   | $SHELL, $ZSH_VERSION / $BASH_VERSION     |
| WM      | $XDG_CURRENT_DESKTOP + $XDG_SESSION_TYPE |
| CPU     | /proc/cpuinfo                            |
| RAM     | /proc/meminfo                            |
| Disk    | statvfs("/")                             |
| Net     | /proc/net/dev                            |
| GPU     | lspci                                    |

## License

MIT — see LICENSE.

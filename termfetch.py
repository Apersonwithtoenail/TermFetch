#!/usr/bin/env python3
"""termfetch — fast, pretty system info for Linux. No dependencies."""

import os
import re
import sys
import json
import shutil
import platform
import subprocess

VERSION = "0.1.0"

COLORS = {
    "accent": "\033[38;5;208m",   # amber, matches PaperRuner
    "reset":  "\033[0m",
}

LOGOS = {
    "kali": r"""
      ,;:ccc,.
    .';;;:::;,,.x,
 ..'''.            0Xxoc:,.
.                ,ONkc;,;cokOdc',
                dMc               :OO;
                0M.                 .:o.
                ;Wd
                 ;XO,
                   ,d0Odlc;,..
                       ..',;:cdOOd::,.
                                .:d;.':;.
                                   'd,  .'
                                     ;l   ..
                                      .o
""",
}


# ---------- low-level helpers ----------

def read_file(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default


def run(cmd, timeout=0.6):
    try:
        return subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        ).decode(errors="replace").strip()
    except Exception:
        return ""


def bar(pct, width=10):
    filled = max(0, min(width, int(round(pct * width))))
    return "▓" * filled + "░" * (width - filled)


# ---------- collectors ----------

def distro():
    data = {}
    for line in read_file("/etc/os-release").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            data[k] = v.strip().strip('"')
    name = data.get("NAME", "Linux")
    ver = data.get("VERSION_ID") or data.get("VERSION", "")
    return f"{name} {ver}".strip()


def uptime():
    try:
        secs = float(read_file("/proc/uptime").split()[0])
    except Exception:
        return "unknown"
    d = int(secs // 86400)
    h = int((secs % 86400) // 3600)
    m = int((secs % 3600) // 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    return " ".join(parts)


def shell():
    sh = os.environ.get("SHELL", "")
    name = os.path.basename(sh) or "sh"
    ver = ""
    if "zsh" in name:
        ver = os.environ.get("ZSH_VERSION", "")
    elif "bash" in name:
        ver = os.environ.get("BASH_VERSION", "").split(".")[0]
    return f"{name} {ver}".strip()


def wm():
    sess = os.environ.get("XDG_SESSION_TYPE", "").lower()
    de = (os.environ.get("XDG_CURRENT_DESKTOP")
          or os.environ.get("DESKTOP_SESSION", ""))
    if de and sess:
        return f"{de} ({sess})"
    if de:
        return de
    return "unknown"


def cpu():
    info = read_file("/proc/cpuinfo")
    model = ""
    count = 0
    for line in info.splitlines():
        if line.startswith("processor"):
            count += 1
        elif line.startswith("model name") and not model:
            model = line.split(":", 1)[1].strip()
    count = count or os.cpu_count() or 1
    model = re.sub(r"\s+CPU\s+", " ", model)
    model = re.sub(r"\s+", " ", model).strip()
    return f"{model} ({count}c)" if model else f"{count}-core CPU"


def ram():
    info = read_file("/proc/meminfo")
    total = avail = 0
    for line in info.splitlines():
        if line.startswith("MemTotal:"):
            total = int(line.split()[1])
        elif line.startswith("MemAvailable:"):
            avail = int(line.split()[1])
    if not total:
        return "unknown"
    used = total - avail
    pct = used / total
    return f"{used/1024/1024:.1f} / {total/1024/1024:.1f} GB  {bar(pct)}"


def disk(path="/"):
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        pct = used / total if total else 0
        return f"/  {used/1024**3:.0f} / {total/1024**3:.0f} GB  {bar(pct)}"
    except Exception:
        return "unknown"


def gpu():
    out = run(["lspci"], timeout=0.8)
    for line in out.splitlines():
        if "VGA" in line or "3D controller" in line:
            return line.split(": ", 1)[-1]
    return ""


def resolution():
    if not shutil.which("xrandr"):
        return ""
    out = run(["xrandr"], timeout=0.5)
    for line in out.splitlines():
        m = re.search(r"(\d+)x(\d+)\+.*\*", line)
        if m:
            return f"{m.group(1)}x{m.group(2)}"
    return ""


def detect_logo():
    data = read_file("/etc/os-release").lower()
    if "kali" in data:
        return "kali"
    return "kali"


# ---------- rendering ----------

def kv(opts, key, value):
    a = opts["accent"]
    r = opts["reset"]
    return f"{a}{key:<8}{r}{value}"


def info_lines(opts):
    a = opts["accent"]
    r = opts["reset"]
    user = os.environ.get("USER", "user")
    host = platform.node() or "host"
    sep = "─" * 30
    out = [
        f"{a}{user}@{host}{r}",
        sep,
        kv(opts, "OS", distro()),
        kv(opts, "Kernel", platform.release()),
        kv(opts, "Uptime", uptime()),
        kv(opts, "Shell", shell()),
        kv(opts, "WM", wm()),
        kv(opts, "CPU", cpu()),
        kv(opts, "RAM", ram()),
        kv(opts, "Disk", disk()),
    ]
    g = gpu()
    if g:
        out.append(kv(opts, "GPU", g))
    d = resolution()
    if d:
        out.append(kv(opts, "Display", d))
    return out


def render(logo_lines, info_lines_, opts):
    a = opts["accent"]
    r = opts["reset"]
    max_logo = max((len(l) for l in logo_lines), default=0)
    n = max(len(logo_lines), len(info_lines_))
    out = []
    for i in range(n):
        left = logo_lines[i] if i < len(logo_lines) else ""
        right = info_lines_[i] if i < len(info_lines_) else ""
        pad = " " * (max_logo - len(left) + 4)
        out.append(f"{a}{left}{r}{pad}{right}")
    return "\n".join(out)


# ---------- CLI ----------

HELP = """\
termfetch — fast, pretty system info

Usage: termfetch [OPTIONS]

Options:
  -n, --no-color     disable colors
  -c, --color        force colors
  -l, --logo NAME    pick a logo (default: auto)
      --json         print as JSON
  -V, --version      show version
  -h, --help         show this help
"""


def parse_args(argv):
    opts = {
        "color": sys.stdout.isatty(),
        "logo": None,
        "json": False,
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--no-color", "-n"):
            opts["color"] = False
        elif a in ("--color", "-c"):
            opts["color"] = True
        elif a == "--json":
            opts["json"] = True
        elif a in ("--logo", "-l") and i + 1 < len(argv):
            i += 1
            opts["logo"] = argv[i]
        elif a in ("--version", "-V"):
            print(f"termfetch {VERSION}")
            sys.exit(0)
        elif a in ("--help", "-h"):
            print(HELP)
            sys.exit(0)
        i += 1
    return opts


def as_json():
    return json.dumps({
        "user": os.environ.get("USER"),
        "host": platform.node(),
        "os": distro(),
        "kernel": platform.release(),
        "uptime": uptime(),
        "shell": shell(),
        "wm": wm(),
        "cpu": cpu(),
        "ram": ram(),
        "disk": disk(),
        "gpu": gpu(),
        "display": resolution(),
    }, indent=2)


def main(argv):
    opts = parse_args(argv)

    if opts["json"]:
        print(as_json())
        return 0

    if not opts["color"]:
        opts["accent"] = ""
        opts["reset"] = ""
    else:
        opts["accent"] = COLORS["accent"]
        opts["reset"] = COLORS["reset"]

    key = opts["logo"] or detect_logo()
    logo = LOGOS.get(key, LOGOS["kali"])
    logo_lines = logo.strip("\n").splitlines()
    info = [""] + info_lines(opts)
    print(render(logo_lines, info, opts))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

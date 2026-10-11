#!/usr/bin/env python3
"""termfetch — fast, pretty system info for Linux."""

import os, re, sys, json, platform, subprocess

VERSION = "0.5.0"
ESC = "\033["
RESET = "\033[0m"

def fg(n): return f"{ESC}38;5;{n}m"
def rgb(r, g, b): return f"{ESC}38;2;{r};{g};{b}m"

GRAD = [
    (255, 176,  58), (255, 108, 158), (167, 108, 255),
    ( 82, 196, 255), (108, 255, 176), (255, 176,  58),
]

def grad_color(t):
    t = t % 1.0
    n = len(GRAD) - 1
    seg = t * n; i = int(seg); f = seg - i
    a, b = GRAD[i], GRAD[i + 1]
    return (int(a[0]+(b[0]-a[0])*f),
            int(a[1]+(b[1]-a[1])*f),
            int(a[2]+(b[2]-a[2])*f))

SPARK = "▁▂▃▄▅▆▇█"
PARTIALS = "▏▎▍▌▋▊▉"
AMBER = 208

LOGOS = {"kali": r"""
      ,;:ccc,.
    .';;;:::;,,.x,
 ..'''.            0Xxoc:,.
.                ,ONkc;,;cokOdc',
                dMc               :OO;
                0M.                 .:o.
                ;Wd
                 ;XO,
                   ,d0Odlc;,..
                       ..,;:cdOOd::,.
                                .:d;.':;.
                                   'd,  .'
                                     ;l   ..
                                      .o
"""}

def read_file(p, d=""):
    try:
        with open(p) as f: return f.read().strip()
    except Exception: return d

def run(cmd, t=0.6):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                       timeout=t).decode(errors="replace").strip()
    except Exception: return ""

def distro():
    d = {}
    for line in read_file("/etc/os-release").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v.strip().strip('"')
    return f"{d.get('NAME','Linux')} {d.get('VERSION_ID') or d.get('VERSION','')}".strip()

def uptime_str():
    try: s = float(read_file("/proc/uptime").split()[0])
    except: s = 0.0
    dd = int(s//86400); h = int((s%86400)//3600)
    m = int((s%3600)//60); sec = int(s%60)
    parts = []
    if dd: parts.append(f"{dd}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{sec}s")
    return " ".join(parts)

def shell():
    name = os.path.basename(os.environ.get("SHELL", "")) or "sh"
    if "zsh" in name:
        return f"zsh {os.environ.get('ZSH_VERSION','')}".strip()
    if "bash" in name:
        return f"bash {os.environ.get('BASH_VERSION','').split('.')[0]}".strip()
    return name

def wm():
    sess = os.environ.get("XDG_SESSION_TYPE", "").lower()
    de = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION", "")
    return f"{de} ({sess})" if de and sess else (de or "?")

def cpu_model():
    info = read_file("/proc/cpuinfo")
    model = ""; count = 0
    for line in info.splitlines():
        if line.startswith("processor"): count += 1
        elif line.startswith("model name") and not model:
            model = line.split(":", 1)[1].strip()
    count = count or os.cpu_count() or 1
    model = re.sub(r"\s+CPU\s+", " ", model)
    model = re.sub(r"\s+", " ", model).strip()
    return f"{model} ({count}c)" if model else f"{count}c"

def ram_stats():
    info = read_file("/proc/meminfo")
    t = a = 0
    for line in info.splitlines():
        if line.startswith("MemTotal:"): t = int(line.split()[1])
        elif line.startswith("MemAvailable:"): a = int(line.split()[1])
    used = t - a if t else 0
    return used, t, (used/t if t else 0)

def disk_stats(p="/"):
    try:
        st = os.statvfs(p)
        t = st.f_blocks * st.f_frsize
        f = st.f_bavail * st.f_frsize
        u = t - f
        return u, t, (u/t if t else 0)
    except: return 0, 0, 0

def load_avg():
    try: return read_file("/proc/loadavg").split()[:3]
    except: return ["0","0","0"]

def proc_count():
    try: return len([p for p in os.listdir("/proc") if p.isdigit()])
    except: return 0

def net_bytes():
    rx = tx = 0
    try:
        for line in read_file("/proc/net/dev").splitlines()[2:]:
            if ":" not in line: continue
            iface, data = line.split(":", 1)
            if iface.strip() == "lo": continue
            p = data.split()
            rx += int(p[0]); tx += int(p[8])
    except: pass
    return rx, tx

def gpu():
    for line in run(["lspci"], t=0.8).splitlines():
        if "VGA" in line or "3D controller" in line:
            return line.split(": ", 1)[-1]
    return ""

def bar(pct, w=12):
    pct = max(0.0, min(1.0, pct))
    e = int(pct * w * 8)
    full = e // 8; part = e % 8
    filled = "█" * full
    if part and full < w:
        filled += PARTIALS[part - 1]; full += 1
    empty = w - full
    c = fg(120) if pct < 0.5 else (fg(214) if pct < 0.75 else fg(202))
    return f"{c}{filled}{fg(238)}{'░'*empty}{RESET}"

def gradient_logo(logo_lines, phase=0.0):
    out = []
    for i, line in enumerate(logo_lines):
        t0 = (i / max(1, len(logo_lines)) + phase) % 1.0
        colored = []
        for j, ch in enumerate(line):
            if ch == " ":
                colored.append(ch); continue
            t = t0 + (j / max(1, len(line))) * 0.4
            r, g, b = grad_color(t)
            colored.append(f"{rgb(r,g,b)}{ch}")
        colored.append(RESET)
        out.append("".join(colored))
    return out

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
def vlen(s): return len(ANSI_RE.sub("", s))

def kv(k, v): return f"{fg(AMBER)}{k:<8}{RESET}{v}"

def render_static():
    used, total, rpct = ram_stats()
    dused, dtotal, dpct = disk_stats()
    user = os.environ.get("USER", "user")
    host = platform.node() or "host"
    info = [
        f"{fg(AMBER)}{user}@{host}{RESET}",
        "─" * 44,
        kv("OS",     distro()),
        kv("Kernel", platform.release()),
        kv("Uptime", uptime_str()),
        kv("Load",   "  ".join(load_avg())),
        kv("Shell",  shell()),
        kv("WM",     wm()),
        kv("CPU",    cpu_model()),
        kv("RAM",    f"{used/1024/1024:.1f} / {total/1024/1024:.1f} GB  {bar(rpct, 12)}"),
        kv("Disk",   f"/  {dused/1024**3:.0f} / {dtotal/1024**3:.0f} GB  {bar(dpct, 12)}"),
        kv("Procs",  str(proc_count())),
    ]
    g = gpu()
    if g:
        info.append(kv("GPU", g[:60]))
    logo_lines = LOGOS["kali"].strip("\n").splitlines()
    colored = gradient_logo(logo_lines, 0.0)
    max_w = max(vlen(l) for l in colored)
    n = max(len(colored), len(info))
    out = []
    for i in range(n):
        left  = colored[i] if i < len(colored) else ""
        right = info[i]    if i < len(info)    else ""
        pad = " " * (max_w - vlen(left) + 4)
        out.append(f"{left}{pad}{right}")
    return "\n".join(out)

def as_json():
    used, rtotal, _ = ram_stats()
    dused, dtotal, _ = disk_stats()
    rx, tx = net_bytes()
    return json.dumps({
        "user": os.environ.get("USER"), "host": platform.node(),
        "os": distro(), "kernel": platform.release(),
        "uptime": uptime_str(), "shell": shell(), "wm": wm(),
        "cpu": cpu_model(),
        "ram_used_mb": round(used/1024), "ram_total_mb": round(rtotal/1024),
        "disk_used_gb": round(dused/1024**3, 1),
        "disk_total_gb": round(dtotal/1024**3, 1),
        "gpu": gpu(), "net_rx_bytes": rx, "net_tx_bytes": tx,
        "procs": proc_count(),
    }, indent=2)

HELP = """termfetch — system info

Usage: termfetch [OPTIONS]
  -n, --no-color   disable colors
      --json       print JSON
  -V, --version    show version
  -h, --help       show help

Live updates:
  watch -n 1 -t termfetch
  Ctrl+C to quit
"""

def parse_args(argv):
    opts = {"color": sys.stdout.isatty(), "json": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if   a in ("--no-color","-n"): opts["color"] = False
        elif a == "--json":            opts["json"] = True
        elif a in ("--version","-V"):
            print(f"termfetch {VERSION}"); sys.exit(0)
        elif a in ("--help","-h"):
            print(HELP); sys.exit(0)
        i += 1
    return opts

def main(argv):
    opts = parse_args(argv)
    if opts["json"]:
        print(as_json()); return 0
    if not opts["color"]:
        g = globals()
        g["fg"] = lambda n: ""
        g["rgb"] = lambda r, gg, b: ""
    print(render_static())
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

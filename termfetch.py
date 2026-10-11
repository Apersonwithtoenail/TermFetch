#!/usr/bin/env python3
"""termfetch — live system info + cava."""

import os, re, sys, json, time, queue, select, shutil, platform
import threading, subprocess, termios, atexit

VERSION = "0.5.0"
ESC = "\033["
RESET = "\033[0m"
HIDE_CURSOR = ESC + "?25l"
SHOW_CURSOR = ESC + "?25h"

def fg(n): return f"{ESC}38;5;{n}m"
def rgb(r, g, b): return f"{ESC}38;2;{r};{g};{b}m"

SPINNER  = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
SPARK    = "▁▂▃▄▅▆▇█"
PARTIALS = "▏▎▍▌▋▊▉"

GRAD = [
    (255, 176,  58), (255, 108, 158), (167, 108, 255),
    ( 82, 196, 255), (108, 255, 176), (255, 176,  58),
]

# Themes: list of RGB stops. More stops = smoother gradient.
THEMES = [
    # 0 — default amber→pink→violet→cyan→mint
    GRAD,

    # 1 — solid amber
    [(255,176,58),(255,176,58)],

    # 2 — cyan → mint
    [(82,196,255),(108,255,176),(82,196,255)],

    # 3 — magenta → violet
    [(255,108,158),(167,108,255),(255,108,158)],

    # 4 — fire (red → orange → yellow)
    [(220,40,40),(255,120,40),(255,210,60),(255,120,40),(220,40,40)],

    # 5 — ocean (deep blue → cyan → white)
    [(30,60,180),(60,140,240),(120,220,255),(230,250,255),(120,220,255),(60,140,240),(30,60,180)],

    # 6 — forest (dark green → lime → yellow-green)
    [(20,80,40),(60,180,90),(140,230,120),(60,180,90),(20,80,40)],

    # 7 — synthwave (hot pink → purple → cyan)
    [(255,60,180),(180,60,255),(60,180,255),(180,60,255),(255,60,180)],

    # 8 — lava lamp (red → orange → magenta → purple)
    [(200,30,30),(255,90,40),(255,40,140),(180,40,220),(255,40,140),(255,90,40),(200,30,30)],

    # 9 — matrix (dark green → bright green → white)
    [(20,80,20),(40,200,60),(180,255,180),(40,200,60),(20,80,20)],

    # 10 — rainbow (full spectrum)
    [(255,0,0),(255,128,0),(255,255,0),(0,255,0),(0,255,255),(0,128,255),(128,0,255),(255,0,128),(255,0,0)],

    # 11 — ice (white → pale blue → deep blue)
    [(240,250,255),(160,200,255),(80,140,240),(160,200,255),(240,250,255)],
]

THEME_NAMES = [
    "gradient", "amber", "cyan", "magenta",
    "fire", "ocean", "forest", "synthwave",
    "lava", "matrix", "rainbow", "ice",
]

def active_gradient(theme_idx):
    return THEMES[theme_idx % len(THEMES)]

def grad_color(t, theme=0):
    pal = active_gradient(theme)
    t = t % 1.0
    n = len(pal) - 1
    seg = t * n; i = int(seg); f = seg - i
    a, b = pal[i], pal[i + 1]
    return (int(a[0]+(b[0]-a[0])*f),
            int(a[1]+(b[1]-a[1])*f),
            int(a[2]+(b[2]-a[2])*f))

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
def vlen(s): return len(ANSI_RE.sub("", s))

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

# ---------- io ----------
def read_file(p, d=""):
    try:
        with open(p) as f: return f.read().strip()
    except Exception: return d

def run(cmd, t=0.6):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                       timeout=t).decode(errors="replace").strip()
    except Exception: return ""

def human_bytes(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"

# ---------- collectors ----------
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

def read_cpu():
    parts = [int(x) for x in read_file("/proc/stat").splitlines()[0].split()[1:]]
    idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
    return idle, sum(parts)

def cpu_pct(prev, cur):
    di = cur[0] - prev[0]; dt = cur[1] - prev[1]
    if dt <= 0: return 0.0
    return max(0.0, min(100.0, 100.0 * (1 - di/dt)))

def sparkline(vals, w=10):
    if not vals: return ""
    return "".join(SPARK[min(len(SPARK)-1, int(v/100*len(SPARK)))] for v in vals[-w:])

def bar(pct, w=10):
    pct = max(0.0, min(1.0, pct))
    e = int(pct * w * 8)
    full = e // 8; part = e % 8
    filled = "█" * full
    if part and full < w:
        filled += PARTIALS[part - 1]; full += 1
    empty = w - full
    c = fg(120) if pct < 0.5 else (fg(214) if pct < 0.75 else fg(202))
    return f"{c}{filled}{fg(238)}{'░'*empty}{RESET}"

def gradient_logo(logo_lines, phase, theme=0):
    out = []
    for i, line in enumerate(logo_lines):
        t0 = (i / max(1, len(logo_lines)) + phase) % 1.0
        colored = []
        for j, ch in enumerate(line):
            if ch == " ":
                colored.append(ch); continue
            t = t0 + (j / max(1, len(line))) * 0.4
            r, g, b = grad_color(t, theme)
            colored.append(f"{rgb(r,g,b)}{ch}")
        colored.append(RESET)
        out.append("".join(colored))
    return out

# ---------- cava ----------
CAVA_CONF = "/tmp/termfetch-cava.conf"

def start_cava(bars=64):
    if not shutil.which("cava"): return None
    with open(CAVA_CONF, "w") as f:
        f.write(f"""[general]
framerate = 60
bars = {bars}

[input]
method = pulse
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
channels = mono
""")
    try:
        return subprocess.Popen(["cava", "-p", CAVA_CONF],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, bufsize=0)
    except Exception:
        return None

def cava_thread(proc, q, stop):
    try:
        while not stop.is_set():
            line = proc.stdout.readline()
            if not line: break
            try:
                s = line.decode(errors="replace").strip().rstrip(";")
                vals = [int(x) for x in s.split(";") if x.strip()]
                if vals:
                    while not q.empty():
                        try: q.get_nowait()
                        except: break
                    q.put(vals)
            except: pass
    except: pass

def render_cava(vals, height, phase, theme=0):
    """2D gradient: horizontal across bars, vertical up each bar."""
    if not vals or height < 2:
        return ["" for _ in range(height)]
    n = len(vals)
    pal = active_gradient(theme)
    grid = [[" "] * (n * 2) for _ in range(height)]
    for b, v in enumerate(vals):
        e = int((v / 100.0) * (height * 8))
        full = e // 8; rem = e % 8
        base_hue = (b / max(1, n) + phase * 0.3) % 1.0
        for r in range(height):
            fb = height - 1 - r
            if fb < full: ch = "█"
            elif fb == full and rem: ch = PARTIALS[rem - 1]
            else: continue
            # vertical offset: 0 at bottom → 1 at top of terminal
            row_ratio = (height - 1 - fb) / max(1, height - 1)
            hue = (base_hue + row_ratio * 0.55) % 1.0
            # smooth interpolation through palette
            seg = hue * (len(pal) - 1)
            i = int(seg); f = seg - i
            a = pal[i]; bb = pal[i + 1]
            r0 = int(a[0] + (bb[0] - a[0]) * f)
            g0 = int(a[1] + (bb[1] - a[1]) * f)
            b0 = int(a[2] + (bb[2] - a[2]) * f)
            col = rgb(r0, g0, b0)
            grid[r][b*2] = f"{col}{ch}{RESET}"
            grid[r][b*2+1] = f"{col}{ch}{RESET}"
    return ["".join(row) for row in grid]

# ---------- info ----------
def kv(k, v): return f"{fg(208)}{k:<8}{RESET}{v}"

def build_info(s, show_spark=True, theme=0):
    user = os.environ.get("USER", "user")
    host = platform.node() or "host"
    spin = SPINNER[s["frame"] % len(SPINNER)]
    lines = [
        f"{fg(208)}{user}@{host}{RESET}  {fg(208)}{spin}{RESET}",
        "─" * 44,
        kv("OS",     s["distro"]),
        kv("Kernel", s["kernel"]),
        kv("Uptime", s["uptime"]),
        kv("Load",   "  ".join(s["load"])),
        kv("Shell",  s["shell"]),
        kv("WM",     s["wm"]),
        kv("CPU",    f"{s['cpu']:5.1f}%  {bar(s['cpu']/100, 10)}" + (f" {sparkline(s['cpu_history'], 10)}" if show_spark else "")),
        kv("RAM",    f"{s['ram_used']/1024/1024:>4.1f}/{s['ram_total']/1024/1024:.1f}G {bar(s['ram_pct'], 10)}"),
        kv("Disk",   f"{s['disk_used']/1024**3:>3.0f}/{s['disk_total']/1024**3:.0f}G   {bar(s['disk_pct'], 10)}"),
        kv("Net",    f"▼{s['rx_rate']}  ▲{s['tx_rate']}"),
        kv("Procs",  str(s["proc_count"])),
    ]
    if s.get("gpu"):
        lines.append(kv("GPU", s["gpu"][:44]))
    lines.append("")
    tname = THEME_NAMES[theme % len(THEME_NAMES)]
    lines.append(
        f"{fg(208)}q{RESET} quit   "
        f"{fg(208)}spc{RESET} pause   "
        f"{fg(208)}l{RESET} logo   "
        f"{fg(208)}c{RESET} cava   "
        f"{fg(208)}s{RESET} spark   "
        f"{fg(208)}t{RESET} theme: {fg(214)}{tname}{RESET}"
    )
    return lines

# ---------- live ----------
def run_live():
    fd = sys.stdin.fileno()
    old_t = termios.tcgetattr(fd)

    paused = False
    show_logo = True
    show_cava = True
    show_spark = True
    theme = 0          # 0=gradient 1=amber 2=cyan 3=magenta
    frame = 0
    prev_cpu = None
    prev_net = None
    cpu_hist = []
    stats = None
    last_sample = 0.0
    prev_rows = 0

    cava_proc = start_cava(bars=64)
    cava_q = queue.Queue(maxsize=2)
    cava_stop = threading.Event()
    cava_bars = []
    if cava_proc and cava_proc.stdout:
        threading.Thread(target=cava_thread,
                         args=(cava_proc, cava_q, cava_stop),
                         daemon=True).start()

    def cleanup():
        cava_stop.set()
        try:
            if cava_proc: cava_proc.terminate()
        except: pass
        try:
            sys.stdout.write(RESET + SHOW_CURSOR + "\n")
            sys.stdout.flush()
        except: pass
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_t)
        except: pass

    atexit.register(cleanup)

    try:
        ts = termios.tcgetattr(fd)
        ts[3] &= ~(termios.ICANON | termios.ECHO)
        ts[6][termios.VMIN] = 0
        ts[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, ts)

        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.flush()

        while True:
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                try: ch = os.read(fd, 1)
                except: ch = b""
                if ch in (b"q", b"Q", b"\x03"):
                    break
                if ch == b" ":
                    paused = not paused
                if ch in (b"l", b"L"):
                    show_logo = not show_logo
                if ch in (b"c", b"C"):
                    show_cava = not show_cava
                if ch in (b"s", b"S"):
                    show_spark = not show_spark
                if ch in (b"t", b"T"):
                    theme = (theme + 1) % len(THEMES)

            if not paused:
                frame += 1

            now = time.time()
            if stats is None or (not paused and now - last_sample >= 0.5):
                idle, total = read_cpu()
                pct = cpu_pct(prev_cpu, (idle, total)) if prev_cpu else 0.0
                prev_cpu = (idle, total)
                cpu_hist.append(pct)
                cpu_hist = cpu_hist[-40:]

                rx, tx = net_bytes()
                if prev_net and prev_net[2] > 0:
                    dt = now - prev_net[2]
                    rx_rate = human_bytes(max(0, (rx-prev_net[0])/dt)) + "/s"
                    tx_rate = human_bytes(max(0, (tx-prev_net[1])/dt)) + "/s"
                else:
                    rx_rate = tx_rate = "—"
                prev_net = (rx, tx, now)

                used, rtotal, rpct = ram_stats()
                dused, dtotal, dpct = disk_stats()
                stats = {
                    "distro": distro(), "kernel": platform.release(),
                    "uptime": uptime_str(), "load": load_avg(),
                    "shell": shell(), "wm": wm(),
                    "cpu": pct, "cpu_history": cpu_hist,
                    "ram_used": used, "ram_total": rtotal, "ram_pct": rpct,
                    "disk_used": dused, "disk_total": dtotal, "disk_pct": dpct,
                    "rx_rate": rx_rate, "tx_rate": tx_rate,
                    "proc_count": proc_count(), "gpu": gpu(),
                }
                last_sample = now

            if stats is None: continue
            stats["frame"] = frame
            stats["uptime"] = uptime_str()

            try:
                while True: cava_bars = cava_q.get_nowait()
            except queue.Empty: pass

            logo_lines = LOGOS["kali"].strip("\n").splitlines()
            colored = gradient_logo(logo_lines, phase=(frame * 0.02) % 1.0, theme=theme) if show_logo else [""] * 15
            info = build_info(stats, show_spark, theme)

            cols, rows = shutil.get_terminal_size((120, 30))
            max_lw = max(vlen(l) for l in colored)
            info_w = max(vlen(l) for l in info)

            total_h = max(len(colored), len(info))
            cava_lines = ["" for _ in range(total_h)]
            room = cols - max_lw - info_w - 8

            if show_cava and room >= 4:
                max_bars = room // 2
                if not cava_bars:
                    cava_bars = [0] * max_bars
                else:
                    if len(cava_bars) < max_bars:
                        rep = (max_bars + len(cava_bars) - 1) // len(cava_bars)
                        cava_bars = (cava_bars * rep)[:max_bars]
                    else:
                        cava_bars = cava_bars[:max_bars]
                cava_lines = render_cava(cava_bars, total_h,
                                         phase=frame * 0.02, theme=theme)

            n = max(len(colored), len(info))
            lines = []
            for i in range(n):
                left  = colored[i]    if i < len(colored)    else ""
                right = info[i]       if i < len(info)       else ""
                cav   = cava_lines[i] if i < len(cava_lines) else ""
                pad = " " * (max_lw - vlen(left) + 4)
                gap = info_w - vlen(right)
                right_padded = right + (" " * gap if gap > 0 else "")
                lines.append(f"{left}{pad}{right_padded}  {cav}")

            if len(lines) > rows - 1:
                lines = lines[:rows - 1]

            padded = []
            for ln in lines:
                gap = cols - vlen(ln)
                padded.append(ln + (" " * gap if gap > 0 else ""))
            body = "\n".join(padded)

            if prev_rows:
                sys.stdout.write(f"{ESC}{prev_rows}A")
            sys.stdout.write(body + ESC + "J" + "\n")
            sys.stdout.flush()
            prev_rows = len(padded)

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
    return 0

# ---------- static ----------
def render_static():
    used, total, rpct = ram_stats()
    dused, dtotal, dpct = disk_stats()
    user = os.environ.get("USER", "user")
    host = platform.node() or "host"
    info = [
        f"{fg(208)}{user}@{host}{RESET}",
        "─" * 44,
        kv("OS", distro()), kv("Kernel", platform.release()),
        kv("Uptime", uptime_str()), kv("Load", "  ".join(load_avg())),
        kv("Shell", shell()), kv("WM", wm()), kv("CPU", cpu_model()),
        kv("RAM", f"{used/1024/1024:.1f} / {total/1024/1024:.1f} GB  {bar(rpct, 12)}"),
        kv("Disk", f"/  {dused/1024**3:.0f} / {dtotal/1024**3:.0f} GB  {bar(dpct, 12)}"),
        kv("Procs", str(proc_count())),
    ]
    g = gpu()
    if g: info.append(kv("GPU", g[:60]))
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

HELP = """termfetch

  -s, --static   one-shot output
  -n, --no-color
      --json     JSON
  -V, --version
  -h, --help

Live keys: q quit, space pause
"""

def parse_args(argv):
    o = {"color": sys.stdout.isatty(), "static": False, "json": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--no-color","-n"): o["color"] = False
        elif a in ("--static","-s"): o["static"] = True
        elif a == "--json":          o["json"] = True
        elif a in ("--version","-V"): print(f"termfetch {VERSION}"); sys.exit(0)
        elif a in ("--help","-h"):    print(HELP); sys.exit(0)
        i += 1
    return o

def main(argv):
    o = parse_args(argv)
    if o["json"]:
        print(as_json()); return 0
    if not o["color"]:
        g = globals()
        g["fg"] = lambda n: ""
        g["rgb"] = lambda r, gg, b: ""
    if o["static"] or not sys.stdout.isatty():
        print(render_static()); return 0
    return run_live()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

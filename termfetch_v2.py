#!/usr/bin/env python3
"""termfetch v0.6.0 - boxed layout, gradient, cava."""

import os, re, sys, time, queue, select, shutil, platform, threading, subprocess, termios, atexit

VERSION = "0.6.0"
ESC = "\033["
RESET = "\033[0m"
HIDE = ESC + "?25l"
SHOW = ESC + "?25h"
ACCENT = "\033[38;5;208m"

def rgb(r, g, b): return f"{ESC}38;2;{r};{g};{b}m"
def fg(n): return f"{ESC}38;5;{n}m"

GRAD = [(255,176,58),(255,108,158),(167,108,255),(82,196,255),(108,255,176),(255,176,58)]
THEMES = [GRAD]
TNAMES = ["aurora"]

def grad_color(t, pal=GRAD):
    t = t % 1.0
    n = len(pal) - 1
    seg = t * n; i = int(seg); f = seg - i
    a = pal[i]; b = pal[i+1] if i+1 < len(pal) else pal[0]
    return (int(a[0]+(b[0]-a[0])*f), int(a[1]+(b[1]-a[1])*f), int(a[2]+(b[2]-a[2])*f))

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
def vlen(s): return len(ANSI_RE.sub("", s))

def read_file(p, d=""):
    try:
        with open(p) as f: return f.read().strip()
    except: return d

def run(cmd, t=0.6):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=t).decode(errors="replace").strip()
    except: return ""

def uptime_str():
    try:
        s = float(read_file("/proc/uptime").split()[0])
        d = int(s // 86400); h = int((s % 86400) // 3600); m = int((s % 3600) // 60)
        return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
    except: return "?"

def load_avg():
    parts = read_file("/proc/loadavg", "0 0 0").split()
    return "  ".join(parts[:3])

def read_cpu():
    try:
        v = [int(x) for x in read_file("/proc/stat").splitlines()[0].split()[1:]]
        return v[3] + v[4], sum(v)
    except: return 0, 0

def ram_stats():
    d = {}
    for line in read_file("/proc/meminfo", "").splitlines():
        k, v = line.split(":", 1)
        d[k] = int(v.strip().split()[0])
    total = d.get("MemTotal", 1) / 1024 / 1024
    used = (d.get("MemTotal", 0) - d.get("MemAvailable", 0)) / 1024 / 1024
    return used, total, used / total if total else 0

def disk_stats():
    try:
        s = os.statvfs("/")
        total = s.f_blocks * s.f_frsize / 1024**3
        free = s.f_bavail * s.f_frsize / 1024**3
        return total - free, total, (total - free) / total
    except: return 0, 1, 0

def net_bytes():
    rx = tx = 0
    try:
        for i in os.listdir("/sys/class/net"):
            if i == "lo": continue
            rx += int(read_file(f"/sys/class/net/{i}/statistics/rx_bytes", "0") or 0)
            tx += int(read_file(f"/sys/class/net/{i}/statistics/tx_bytes", "0") or 0)
    except: pass
    return rx, tx

def human(n):
    for u in ("B","K","M","G"):
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}T"

def distro():
    for line in read_file("/etc/os-release", "").splitlines():
        if line.startswith("PRETTY_NAME="):
            return line.split("=", 1)[1].strip().strip('"')
    return platform.platform()

def shell():
    return os.path.basename(os.environ.get("SHELL", "sh"))

def wm():
    return os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "?"

def cpu_model():
    for line in read_file("/proc/cpuinfo", "").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "CPU"


# ---------- box drawing ----------
def panel(lines, width, title=None, pal=None, phase=0.0):
    """lines = [(key, value, bar_width), ...]  -> boxed panel"""
    top_l, top_r, bot_l, bot_r = "╭", "╮", "╰", "╯"
    h, v = "─", "│"
    c = rgb(*grad_color(phase, pal)) if pal else ACCENT
    out = []
    if title:
        pad = width - vlen(title) - 4
        out.append(f"{c}{top_l}{h} {title} {h * pad}{top_r}{RESET}")
    else:
        out.append(f"{c}{top_l}{h * (width-2)}{top_r}{RESET}")
    for key, val, bar in lines:
        key_s = f"{c}{key:<6}{RESET}"
        if bar:
            bar_s = bar_line(bar, width - 12)
            content = f"{key_s} {val:<12} {bar_s}"
        else:
            content = f"{key_s} {val}"
        gap = width - 4 - vlen(content)
        out.append(f"{c}{v}{RESET} {content}{' ' * max(0, gap)} {c}{v}{RESET}")
    out.append(f"{c}{bot_l}{h * (width-2)}{bot_r}{RESET}")
    return out

def bar_line(pct, w):
    pct = max(0.0, min(1.0, pct))
    fill = int(pct * w)
    empty = w - fill
    return f"{ACCENT}{'█' * fill}{fg(238)}{'░' * empty}{RESET}"

def dot_row(cols, pal, phase):
    out = []
    for i in range(cols):
        t = (phase + i * 0.05) % 1.0
        out.append(rgb(*grad_color(t, pal)) + "●")
    return "".join(out) + RESET

def render(theme, frame, cols):
    pal = THEMES[theme]
    phase = (frame * 0.02) % 1.0
    out = []
    # header
    user = os.environ.get("USER", "user")
    host = platform.node() or "host"
    out.append(f"{rgb(*grad_color(phase, pal))}{user}@{host}{RESET}  {rgb(*grad_color((phase+0.5)%1, pal))}{chr(0x2591)}{RESET}")
    out.append("")
    # system panel
    w = min(60, cols - 4)
    sys_lines = [
        ("OS",     distro(), None),
        ("Kernel", platform.release(), None),
        ("Uptime", uptime_str(), None),
        ("Shell",  shell(), None),
        ("WM",     wm(), None),
    ]
    for line in panel(sys_lines, w, title="system", pal=pal, phase=phase):
        out.append(line)
    out.append("")
    # hardware panel
    cu, ct, cp = ram_stats()
    du, dt, dp = disk_stats()
    idle, total = read_cpu()
    cpu_lines = [
        ("CPU",  cpu_model()[:22], None),
        ("Load", load_avg(), None),
    ]
    for line in panel(cpu_lines, w, title="hardware", pal=pal, phase=phase):
        out.append(line)
    return out


# ---------- cava ----------
CAVA_CONF = "/tmp/termfetch-cava.conf"
CAVA_FPS = 20

def start_cava():
    if not shutil.which("cava"): return None
    try:
        open(CAVA_CONF, "w").write(f"""[general]
framerate = {CAVA_FPS}
bars = 64

[input]
method = pulse
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
bar_delimiter = 59
frame_delimiter = 10
""")
        return subprocess.Popen(["cava","-p",CAVA_CONF], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, bufsize=1,
                                universal_newlines=True)
    except: return None

def cava_thread(proc, q, stop):
    while not stop.is_set():
        try:
            line = proc.stdout.readline()
            if not line: break
            vals = [int(x) for x in line.strip().split(";") if x.isdigit()]
            if vals:
                try: q.get_nowait()
                except: pass
                q.put(vals)
        except: break

def render_cava(bars, height):
    if not bars or height < 1: return [""] * height
    n = len(bars)
    levels = " ▁▂▃▄▅▆▇█"
    rows = [""] * height
    for i, val in enumerate(bars):
        pct = min(1.0, val / 100)
        h = pct * height
        full = int(h)
        frac = h - full
        for r in range(height):
            if r < full:
                rows[height-1-r] += "█"
            elif r == full and frac > 0:
                idx = int(frac * 8)
                rows[height-1-r] += levels[idx] if idx else " "
            else:
                rows[height-1-r] += " "
    return rows

# ---------- main loop ----------
def main():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    cava_proc = start_cava()
    cava_q = queue.Queue(maxsize=2)
    stop = threading.Event()
    if cava_proc:
        threading.Thread(target=cava_thread, args=(cava_proc, cava_q, stop), daemon=True).start()

    def cleanup():
        stop.set()
        try: termios.tcsetattr(fd, termios.TCSANOW, old)
        except: pass
        sys.stdout.write(SHOW); sys.stdout.flush()
        if cava_proc:
            try: cava_proc.terminate()
            except: pass
    atexit.register(cleanup)

    try:
        ts = termios.tcgetattr(fd)
        ts[3] &= ~(termios.ICANON | termios.ECHO)
        ts[6][termios.VMIN] = 0
        ts[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, ts)

        sys.stdout.write(HIDE); sys.stdout.flush()

        frame = 0
        theme = 0
        last_render = 0.0
        prev_rows = 0

        while True:
            r,_,_ = select.select([fd], [], [], 0.05)
            if r:
                ch = os.read(fd, 1)
                if ch in (b"q", b"Q", b"\x03"): break
                if ch == b"t":
                    theme = (theme + 1) % len(THEMES)

            frame += 1
            now = time.time()
            if now - last_render < 0.10: continue
            last_render = now

            cols, rows = shutil.get_terminal_size((100, 30))
            body_lines = render(theme, frame, cols)

            # grab cava frame
            bars = None
            try:
                while True: bars = cava_q.get_nowait()
            except queue.Empty: pass
            if bars:
                cav_h = 6
                for i, line in enumerate(render_cava(bars, cav_h)):
                    body_lines.append(line)

            # cap to terminal
            if len(body_lines) > rows - 1:
                body_lines = body_lines[:rows - 1]

            # pad + write
            padded = []
            for ln in body_lines:
                gap = cols - vlen(ln)
                padded.append(ln + " " * max(0, gap))
            body = "\n".join(padded)

            if prev_rows:
                sys.stdout.write(f"{ESC}{prev_rows}A")
            sys.stdout.write(body + ESC + "J\n")
            sys.stdout.flush()
            prev_rows = len(padded)

    except KeyboardInterrupt: pass
    finally:
        cleanup()
    return 0

if __name__ == "__main__":
    sys.exit(main())

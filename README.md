# TermFetch

Fast, pretty system info for Linux. No dependencies.

Pure Python 3 standard library. Reads /proc and /sys directly.

## Install

```bash
git clone https://github.com/Apersonwithtoenail/TermFetch.git
cd TermFetch
./install.sh
```

## Use

```bash
termfetch
```

Live dashboard with cava, gradient logo, and three layout variants.

## Keys

| key | action |
|-----|--------|
| `q` | quit |
| `spc` | pause updates |
| `l` | toggle logo |
| `c` | toggle cava bars |
| `s` | toggle sparkline |
| `v` | cycle variant (classic / boxed / fancy) |
| `t` | cycle theme |

## Variants

- **classic** — classic flat layout with gradient logo
- **boxed** — system / hardware panels in boxes
- **fancy** — grouped panels (PC / OS / LIVE / Uptime)

## Themes

10 gradient themes: aurora, cyan, magenta, fire, ocean, forest, synthwave, matrix, rainbow, ice

## Performance

v0.6.0 dropped CPU usage from ~14.4% to ~1.6% by:

- throttling redraws to ~8fps
- dropping cava framerate to 15
- skipping render when nothing changed

## License

MIT

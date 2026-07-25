# zetamac-tui

TUI zetamac clone (identical core interface) plus SQLite tracking, replay, and flash anzan (also mental arithmetic), built with [Textual](https://github.com/Textualize/textual).

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Textual](https://img.shields.io/badge/built%20with-Textual-magenta)
![License](https://img.shields.io/badge/license-GPLv3-green)

## Screenshots

<!-- https://raw.githubusercontent.com/yaofanfish/zetamac-tui/refs/heads/main -->
![Settings](https://raw.githubusercontent.com/yaofanfish/zetamac-tui/refs/heads/main/assets/63dd43f7-3f04-4e29-a218-b13fdf09415e.png)
![Play](https://raw.githubusercontent.com/yaofanfish/zetamac-tui/refs/heads/main/assets/16c844ea-70ce-4e1a-9d76-011f095fc959.png)
![View runs](https://raw.githubusercontent.com/yaofanfish/zetamac-tui/refs/heads/main/assets/c63567db-c70a-4e45-a05c-efcdf6736680.png)
<video src="https://github.com/yaofanfish/zetamac-tui/raw/refs/heads/main/assets/demo.mp4" controls="controls" style="max-width: 100%;">
  Your browser does not support the video tag.
</video>

## Features

* **All features** from arithmetic.zetamac.com with an identical interface and functionality (as shown above), like addition, subtraction, division. 
* Local SQLite run history with per-problem timings (only runs with default setting though, otherwise everything gets jumbled and you can't track data effectively)
* A pretty interface for selecting runs with summaries for each
* Able to replay any run, or replay all the hardest questions (questions which took the longest time)
* Per-run analytics to identify weak spots
* Fully keyboard-driven terminal UI (what Textual does). 

* An additional flash anzan gamemode, although that doesn't have the logging the core does

* Written in python, so can descend into a python or sqlite shell for directly interacting with the state. For dev, and can be normally used with helper functions defined. 

## Installation / Quick Start

Requires Python 3.10+.

### Install from PyPI (recommended) - pipx

```bash
pipx install "zetamac-tui[opt]"
```

### Using pip

```bash
pip install "zetamac-tui[opt]"
```

---

### Install from github

```bash
git clone https://github.com/yaofanfish/zetamac-tui.git
cd zetamac-tui
pipx install -e ".[opt]"
```

## Usage

```bash
zetamac-tui
```
The interface is generally straightforward, and as mentioned before, the core is identical to the web zetamac. 
Configure settings, start a round, review past runs, or replay difficult questions directly from the menu.

## Data Storage

(
	On windows, replace ~ with %USERPROFILE%\AppData\Local\zetamac-tui, so settings would be C:\Users\DemoUser\AppData\Local\zetamac-tui\.local\state\zetamac-tui\settings.json
	It is linux first, so the paths are a bit awkward. 
)

* Settings: `~/.local/state/zetamac-tui/settings.json`
* Run history: `~/.local/share/zetamac-tui/runs.db`
* Python rc file: `~/.config/zetamac-tui/pyrc.py`

## Contributing

Issues and pull requests are welcome.

```bash
git clone https://github.com/yaofanfish/zetamac-tui.git
cd zetamac-tui
pip install -e ".[dev,opt]"
```

## License

GPL-3.0

## Acknowledgments

Inspired by [Zetamac](https://arithmetic.zetamac.com/) by Zach Wissner-Gross.


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
<video src='https://github.com/user-attachments/assets/d07dafff-032a-4b23-bc4d-1c64ac901a8f'></video>



## Features

* **All features** from arithmetic.zetamac.com with an identical interface and functionality (as shown above), like addition, subtraction, division. 
* Local SQLite run history with per-problem timings (only runs with default setting though)
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

### Install from ![AUR](https://aur.archlinux.org/packages/zetamac-tui-git) (Arch linux)

```bash
yay -S zetamac-tui-git
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

* Settings: `~/.local/state/zetamac-tui/settings.json` (`%LOCALAPPDATA%\zetamac-tui\settings.json` on windows)
* Run history: `~/.local/share/zetamac-tui/runs.db` (`%LOCALAPPDATA%\zetamac-tui\runs.db` on windows)
* Python rc file: `~/.config/zetamac-tui/pyrc.py` (`%APPDATA%\zetamac-tui\pyrc.py` on windows)

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


#!/usr/bin/env python3

from __future__ import annotations

import json
import math
import sqlite3
import sys, os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import array

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Checkbox, Input, Label, ListItem, ListView, Static
from textual.binding import Binding
from textual import events, on

import rich, rich.console, rich.text
import asyncio

sys.path.append(str(Path(__file__).parent.resolve()))

console = rich.console.Console()

import presets
from presets import DEFAULT_SETTINGS, _DEFAULT_RUN

# lazy_import modules that aren't used on startup, to make startup snappier

import importlib.util

def lazy_import(name):
    spec = importlib.util.find_spec(name)
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module

datetime = lazy_import("datetime")
tempfile = lazy_import("tempfile")
signal = lazy_import("signal")
subprocess = lazy_import("subprocess")
time = lazy_import("time")
random = lazy_import("random")

# NOTE: data_anlysis.py

def _analytics(json_logs, id = None) -> dict:
    if type(json_logs) in (list, dict):
        raw_logs = json_logs
    else:
        raw_logs = json.loads(str(json_logs))

    timeline = []
    for ts_str, eq in raw_logs.items():
        timeline.append({"ts": float(ts_str), "eq": eq})
    timeline.sort(key=lambda x: x["ts"])

    incremental = []
    total_time = 0.0
    total_questions = len(timeline)

    for i, entry in enumerate(timeline):
        if i == 0:
            time_used = entry["ts"]
        else:
            time_used = entry["ts"] - timeline[i - 1]["ts"]
        
        incremental.append([entry["eq"], time_used])
        total_time += time_used

    fastest = [[item[0], item[1]] for item in incremental]
    slowest = [[item[0], item[1]] for item in incremental]

    fastest.sort(key=lambda x: x[1])
    slowest.sort(key=lambda x: x[1], reverse=True)

    average_time = (total_time / total_questions) if total_questions > 0 else 0.0
    
    median_time = 0.0
    if total_questions > 0:
        if total_questions % 2 == 1:
            mid = total_questions // 2
            median_time = fastest[mid][1]
        else:
            mid2 = total_questions // 2
            mid1 = mid2 - 1
            median_time = (fastest[mid1][1] + fastest[mid2][1]) / 2.0

    summary_limit = min(3, total_questions)
    summary_fastest = fastest[:summary_limit]
    summary_slowest = slowest[:summary_limit]
    
    return {
        "incremental": incremental,
        "fastest": fastest,
        "slowest": slowest,
        "summary": {
            "total_questions": total_questions,
            "average_seconds": math.floor(average_time * 1000) / 1000,
            "median_seconds": math.floor(median_time * 1000) / 1000,
            "fastest": summary_fastest,
            "slowest": summary_slowest,
            "id": id
        }
    }

def _analytics_summary_(json_logs, id = None) -> str:
    a = _analytics(json_logs, id)
    s = a["summary"]
    for i in range(len(s["fastest"])):
        s["fastest"][i] = f"\x1b[32m{s['fastest'][i][0]}\x1b[0m: \x1b[36m{s['fastest'][i][1]}\x1b[0m"
    for i in range(len(s["slowest"])):
        s["slowest"][i] = f"\x1b[32m{s['slowest'][i][0]}\x1b[0m: \x1b[36m{s['slowest'][i][1]}\x1b[0m"
    
    with console.capture() as capture:
        console.print_json(data=s)

    summary = capture.get()

    dbgf.write(f"raw summary: {summary}\n")

    summary = summary.replace(r"\u001b", "\u001b") # rich prints escape sequences in json literally, so fix that
    
    return summary


def ids_info(conn=None):
    if conn is None: # conn should always be passed in actual code, this is just a workaround for the user calling in the repl
        try:
            conn = globals()["conn"]
            if type(conn) != sqlite3.Connection:
                raise Exception("not a conn")
        except:
            conn = sqlite3.connect(LOCALSHAREDIR / "runs.db")

    today = datetime.date.today().isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            MIN(CASE WHEN ts >= ? AND ts < ? THEN id END),
            MAX(id)
        FROM runs
        """,
        (today, tomorrow),
    )

    first_today_id, highest_id = cur.fetchone()
    highest_id = highest_id or 0

    return {
        "first_today_id": first_today_id if first_today_id is not None else highest_id + 1,
        "highest_id": highest_id,
    }


def run_avg(conn=None):
    if conn is None:
        conn = globals()["conn"]
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(score) FROM runs")
    row = cursor.fetchone()
    return (row[0] if row and row[0] is not None else 0.0)


def run_avg_today(conn=None):
    if conn is None:
        conn = globals()["conn"]
    start_id = ids_info(conn)["first_today_id"]
    cursor = conn.cursor()
    cursor.execute("SELECT AVG(score) FROM runs WHERE id >= ?", (start_id,))
    row = cursor.fetchone()
    return (row[0] if row and row[0] is not None else 0.0)


def run_max(conn=None):
    if conn is None:
        conn = globals()["conn"]
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(score) FROM runs")
    row = cursor.fetchone()
    return (row[0] if row and row[0] is not None else 0)


def run_max_today(conn=None):
    if conn is None:
        conn = globals()["conn"]
    start_id = ids_info(conn)["first_today_id"]
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(score) FROM runs WHERE id >= ?", (start_id,))
    row = cursor.fetchone()
    return (row[0] if row and row[0] is not None else 0)



# NOTE: END: data_analysis.py




HOME = (Path.home() / "Appdata" / "Local" / "zetamac-tui" if os.name == "nt" else Path.home()).resolve()

CONFIGDIR = HOME / ".config" / "zetamac-tui"

LOCALSHAREDIR = HOME / ".local" / "share" / "zetamac-tui"

LOCALSTATEDIR = HOME / ".local" / "state" / "zetamac-tui"

SETTINGSFILE = LOCALSTATEDIR / "settings.json"

RCFILE = CONFIGDIR / "pyrc.py"

try:
    dbgf = open("/tmp/zetamac-tui-debug.log", "w", encoding="utf-8", buffering=1)
except:
    # windows / error occurred
    dbgf = sys.stderr

@dataclass
class Settings:
    """Game configuration (see zetamac_tui_doc.SETTINGS_DOC)."""
    game_duration: float = 120.0
    cheat_mode: bool = False
    no_log: int = 0
    addition_bounds: list[int] = field(default_factory=lambda: [2, 100, 2, 100])
    multiplication_bounds: list[int] = field(default_factory=lambda: [2, 12, 2, 100])
    operations: list[str] = field(default_factory=lambda: ["+", "-", "*", "/"])
    flash_digits: int = 1
    flash_duration: float = 1.0
    flash_number: int = 10
    flash_volume: int = 100
    save_settings_state: bool = True
    # The generator is persisted as the global function name string.
    # At runtime it is resolved back to the callable.
    generation_function: str | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict:
        data = asdict(self)
        gf = data.get("generation_function")
        if callable(gf):
            data["generation_function"] = gf.__name__
        elif gf is not None and not isinstance(gf, str):
            data["generation_function"] = None
        return data

def sql_sh(conn=(HOME / ".local" / "share" / "zetamac-tui" / "runs.db")):
    if type(conn) == sqlite3.Connection:
        path = conn.execute(
            "SELECT file FROM pragma_database_list WHERE name = 'main';"
        ).fetchone()[0]
    else:
        path = str(conn)

    old_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        subprocess.run(["sqlite3", path])
    except Exception as e:
        dbgf.write(f"sql_sh: Exception - {e}\n")
    finally:
        signal.signal(signal.SIGINT, old_handler)
"""
Enter the cli SQL shell
Needs some weird signal workarounds due to a race condition
"""


class AppState:
    """Persistent settings and DB connection (see zetamac_tui_doc.APP_STATE_DOC)."""
    def __init__(self, config_dir: str | Path | None = None, db_path: str | Path | None = None) -> None:
        self.home = HOME
        # allow tests and callers to override locations
        self.config_dir = Path(config_dir) if config_dir is not None else CONFIGDIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.localstate_dir = LOCALSTATEDIR
        self.localstate_dir.mkdir(parents=True, exist_ok=True)
        # settings file lives inside the config dir
        self.config_path = Path(self.config_dir) / "settings.json"
        # allow overriding database path for tests
        self.db_path = Path(db_path) if db_path is not None else (LOCALSHAREDIR / "runs.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings = self.load_settings()
        self.conn = self.open_db()

    def default_settings(self) -> Settings:
        defaults = Settings(**DEFAULT_SETTINGS)
        return defaults

    def load_settings(self, fallback="default") -> Settings:
        defaults = self.default_settings()
        default_dict = defaults.to_dict()
        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
                if not isinstance(raw, dict):
                    raise ValueError("settings JSON must contain an object")
                # generation_function is persisted as the global function name.
                allowed = set(Settings.__dataclass_fields__.keys())
                filtered = {k: v for k, v in raw.items() if k in allowed}
                merged = dict(default_dict)
                for key, value in filtered.items():
                    if key == "generation_function":
                        merged[key] = value if isinstance(value, str) else None
                    elif key == "operations":
                        # require a complete, valid operations list; partial legacy
                        # configs should fall back to defaults to avoid UI errors
                        if (
                            isinstance(value, list)
                            and set(value) == {"+", "-", "*", "/"}
                            and all(isinstance(item, str) for item in value)
                        ):
                            merged[key] = list(value)
                        else:
                            merged[key] = list(default_dict[key])
                    elif key in {"addition_bounds", "multiplication_bounds"}:
                        # The settings UI indexes all four values, so reject
                        # partial or malformed ranges rather than leaving it
                        # with an object that will fail when displayed.
                        if (
                            isinstance(value, list)
                            and len(value) == 4
                            and all(isinstance(item, (int, float)) and math.isfinite(item) for item in value)
                        ):
                            merged[key] = list(value)
                        else:
                            merged[key] = list(default_dict[key])
                    elif key == "game_duration":
                        if isinstance(value, (int, float)) and math.isfinite(value):
                            merged[key] = value
                    elif key == "flash_volume":
                        if isinstance(value, int) and 1 <= value <= 100:
                            merged[key] = value
                        elif isinstance(value, float) and math.isfinite(value):
                            merged[key] = min(100, max(1, int(value)))
                        else:
                            merged[key] = default_dict[key]
                    elif key == "no_log":
                        if isinstance(value, int):
                            merged[key] = value
                    else:
                        merged[key] = value
                merged['no_log'] &= 0b11
                return Settings(**merged)
            except Exception:
                if fallback == "default":
                    return defaults
                elif fallback == "self.settings":
                    return self.settings
                else:
                    return fallback
        return defaults

    def save_settings(self, force=False) -> None:
        if not self.settings.save_settings_state and not force:
            # don't save settings if save_settings_state is disabled, instead just save the flag and lock the settings for the future so it doesn't revert
            data = {"save_settings_state": False}
        else:
            data = self.settings.to_dict()
        with self.config_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)

    def open_db(self) -> sqlite3.Connection:
        global conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                score INTEGER,
                ts VARCHAR(64),
                logs TEXT
            )
            """
        )
        conn.commit()
        return conn

    def all_init(self):
        RCFILE.touch()
        RCFILE.chmod(0o600) # naturally close permissions for executed code, though this is a local project so there is little/none security issues - main security issues would come from horizontal privesc
        try:
            with open(RCFILE, "r") as f:
                rc = f.read()
            exec(rc, globals(), globals())
        except Exception as e:
            dbgf.write(f"Error whilst loading pyrc.py: {e}")

def preset(ps, st=None):
    if st is None:
        global state
        state.settings = replace(state.settings, **ps)
    else:
        st.settings = replace(st.settings, **ps)




def generate_problem(settings: Settings) -> tuple[str, int]:
    operations = settings.operations or ["+", "-", "*", "/"] # prevent nothing being selected from crashing
    operation = random.choice(operations)

    if operation in ["*", "/"]:
        lo1, hi1, lo2, hi2 = settings.multiplication_bounds[:4]
    else:
        lo1, hi1, lo2, hi2 = settings.addition_bounds[:4]

    if lo1 > hi1:
        lo1, hi1 = hi1, lo1
    if lo2 > hi2:
        lo2, hi2 = hi2, lo2

    # Generate the base integers
    a = random.randint(int(lo1), int(hi1))
    b = random.randint(int(lo2), int(hi2))

    if operation == "+":
        return f"{a} + {b}", int(a + b)

    if operation == "-":
        # Ensure a >= b for a positive integer result
        if b > a:
            a, b = b, a
        return f"{a} - {b}", int(a - b)

    if operation == "*":
        return f"{a} * {b}", int(a * b)

    if operation == "/":
        # To ensure integer results, we treat it as: (a * b) / a = b
        # We use a as the quotient and b as the divisor
        # Avoid division by zero
        if a == 0:
            a = 1
        product = a * b
        return f"{product} / {a}", int(b)


# The operands used by the built-in times-table generator.  ``tt`` changes
# these for the current process; it intentionally does not persist them.
tt_a: list[int] = []
tt_b: list[int] = []


def _tt() -> tuple[str, int]:
    """Generate one multiplication question from the lists configured by tt."""
    a = random.choice(tt_a)
    b = random.choice(tt_b)
    return f"{a} * {b}", int(a * b)


def resolve_generation_function(value):
    """Resolve either a function object or a global function name to a callable."""
    if value is None:
        return None
    if callable(value):
        return value
    if isinstance(value, str):
        func = globals().get(value)
        if func is None or not callable(func):
            return None
        return func
    return None


def tt(b: list[int], a: list[int] = [], settings=None) -> None:
    """Use selected multiplication operands for PlayScreen's generator.

    Empty operand lists inherit the corresponding current multiplication range.
    When called from ``pyrc.py`` without ``settings``, the running app's global
    settings are used.
    """
    global tt_a, tt_b

    if settings is None:
        settings = globals().get("state", None)
        settings = settings.settings if settings is not None else Settings()

    bounds = settings.multiplication_bounds[:4]
    lo_a, hi_a, lo_b, hi_b = (int(value) for value in bounds)
    if lo_a > hi_a:
        lo_a, hi_a = hi_a, lo_a
    if lo_b > hi_b:
        lo_b, hi_b = hi_b, lo_b

    tt_a = list(a) if a else list(range(lo_a, hi_a + 1))
    tt_b = list(b) if b else list(range(lo_b, hi_b + 1))
    settings.generation_function = _tt.__name__


def parse_answer(raw: str) -> int | float | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return None


def record_run(conn: sqlite3.Connection, table: str, score: int, logs: dict[str, str]) -> int:
    ensure_schema(conn)
    now = datetime.datetime.now().isoformat()
    values = (
        score,
        now,
        json.dumps(logs),
    )
    global dbgf
    dbgf.write(f"record_run: table={table}, score={score}, logs={logs}; values = {json.dumps(values)}\n")
    conn.execute(
        f"INSERT INTO {table}(score, ts, logs) VALUES(?, ?, ?)",
        values,
    )
    conn.commit()
    row_obj = conn.execute("SELECT last_insert_rowid() AS row_id").fetchone()
    if row_obj is None:
        return 0
    if isinstance(row_obj, sqlite3.Row):
        row_id = row_obj["row_id"]
    else:
        row_id = row_obj[0]
    return int(row_id)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER,
            ts VARCHAR(64),
            logs TEXT
        )
        """
    )
    conn.commit()


def get_recent_runs(conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id, ts, score FROM runs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    result: list[dict] = []
    for row in rows:
        if isinstance(row, sqlite3.Row):
            result.append(dict(row))
        else:
            result.append({"id": row[0], "ts": row[1], "score": row[2]})
    return result


def get_all_run_metadata(conn: sqlite3.Connection) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT id, ts, score FROM runs ORDER BY id DESC",
    ).fetchall()
    result: list[dict] = []
    for row in rows:
        if isinstance(row, sqlite3.Row):
            result.append(dict(row))
        else:
            result.append({"id": row[0], "ts": row[1], "score": row[2]})
    return result


def get_run(conn: sqlite3.Connection, run_id: int) -> dict | None:
    ensure_schema(conn)
    row = conn.execute(
        "SELECT id, ts, score, logs FROM runs WHERE id = ?",
        (run_id,),
    ).fetchone()
    if not row:
        return None
    result = dict(row)
    if result.get("logs"):
        result["logs"] = json.loads(result["logs"])
    return result


def get_all_runs(conn: sqlite3.Connection) -> list[dict]:
    ensure_schema(conn)
    rows = conn.execute("SELECT id, ts, score, logs FROM runs ORDER BY id ASC").fetchall()
    result: list[dict] = []
    for row in rows:
        item = dict(row)
        if item.get("logs"):
            item["logs"] = json.loads(item["logs"])
        result.append(item)
    return result


def compute_timeline(logs: dict[str, str]) -> list[tuple[float, str]]:
    timeline: list[tuple[float, str]] = []
    for key, expression in sorted(logs.items(), key=lambda item: float(item[0])):
        timeline.append((float(key), expression))
    return timeline

# still doesn't work lmao
# might just be miniaudio's fault but idk
async def beep(duration: float = 1.0, volume: int = 100) -> None:
    dbgf.write("beep\n")
    sound_path = Path(__file__).parent.resolve() / "assets" / "beep.wav"
    sound_str = str(sound_path)

    if sound_path.exists():
        try:
            import miniaudio
            sound = miniaudio.stream_file(sound_str)
            device = miniaudio.PlaybackDevice()

            volume = max(1, min(100, int(volume)))
            if volume != 100:
                def scaled_sound(source):
                    # Transparent proxy generator: forwards whatever the
                    # consumer sends (frame_count) into the underlying
                    # stream generator, and scales the returned samples.
                    value = None
                    while True:
                        try:
                            frame = next(source) if value is None else source.send(value)
                        except StopIteration:
                            return
                        if isinstance(frame, array.array) and frame.typecode == 'h':
                            frame = array.array(
                                'h',
                                (max(-32768, min(32767, int(s * volume / 100))) for s in frame),
                            )
                        value = yield frame
                sound = scaled_sound(sound)

            device.start(sound)
            await asyncio.sleep(duration)
            device.stop()
            device.close()
            dbgf.write("miniaudio succeeded\n")
            return
        except Exception as e:
            dbgf.write(f"miniaudio failed - {e}\n")

    if sys.platform == "linux":
        dbgf.write("using linux\n")
        normalized_volume = str(max(0.01, min(1.0, volume / 100)))
        for player, args in (
            ("ffplay", ["-nodisp", "-autoexit", "-t", str(duration), "-volume", normalized_volume, sound_str]),
            ("timeout", [str(duration), "aplay", sound_str]),
            ("timeout", [str(duration), "paplay", sound_str]),
        ):
            playerrealname = args[1] if player == "timeout" else player
            is_timeout_wrapped = player == "timeout"
            try:
                proc = await asyncio.create_subprocess_exec(
                    player, *args,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                rc = await proc.wait()
                success = rc == 0 or (is_timeout_wrapped and rc in (124, 143))
                if success:
                    dbgf.write(f"{playerrealname} succeeded\n")
                    return
                dbgf.write(f"{playerrealname} exited with code {rc}\n")
            except FileNotFoundError:
                dbgf.write(f"{playerrealname} not found\n")
            except Exception as e:
                dbgf.write(f"{playerrealname} failed - {e}\n")
        # all linux players failed - fall through to terminal bell below

    elif sys.platform == "darwin":
        try:
            proc = await asyncio.create_subprocess_exec(
                "afplay", "-t", str(duration), sound_str,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            rc = await proc.wait()
            if rc == 0:
                return
            dbgf.write(f"afplay exited with code {rc}\n")
        except Exception as e:
            dbgf.write(f"afplay failed - {e}\n")

    # windows has native sound generators
    if sys.platform == "win32":
        try:
            import winsound
            if sound_path.exists():
                winsound.PlaySound(sound_str, winsound.SND_FILENAME | winsound.SND_ASYNC)
                await asyncio.sleep(duration)
                winsound.PlaySound(None, winsound.SND_PURGE)
                return
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, winsound.Beep, 440, int(duration * 1000))
                return
        except Exception:
            pass

    # native players for all 3 "big" kernels failed
    # no idea what ur running on
    print("\a")
        
def open_file(tempfname):
    import shutil
    try:
        editors = [f"{os.getenv('EDITOR', 'nvim')}", "xdg-open", "open", "notepad.exe", "nvim", "vim", "nano", "vi"]
        for editor in editors:
            if shutil.which(editor):
                try:
                    dbgf.write("used editor " + editor + "\n")
                    subprocess.run([editor, tempfname])
                    return
                except BaseException as e:
                    dbgf.write(f"Failed to open {tempfname} with {editor}: {e}\n")
        if sys.platform == "linux":
            subprocess.run(["vi", tempfname])
        elif sys.platform == "darwin":
            subprocess.run(["vim", tempfname]) # vim is installed by default
        elif sys.platform == "win32":
            os.startfile(tempfname)
        subprocess.run(["nano", tempfname])
    except:
        pass
    finally:
        pass

class SettingsScreen(Screen):

    BINDINGS = [
         ("ctrl+s", "save", "Save"),
         ("5", "save_and_play", "Save and play"),
         ("ctrl+d", "defaults", "Defaults"),
         ("p", "focus_presets", "Focus onto presets input"),
         ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    SettingsScreen {
        padding: 1;
        align: center top;
        /* background: #ffffff; */
    }
    #settings-container {
        width: 80;
        height: auto;
        background: #272727;
        color: white;
        padding: 2 4 2 4;
        border: solid #272727; /* Subtle border to define the edge against terminal backgrounds */
    }
    .section {
        height: auto;
        margin-bottom: 1;
    }
    .checkbox-row {
        height: 1;
        align-vertical: middle;
    }
    .checkbox-row Label {
        margin-left: 1; /* Replicates the native text spacing next to the checkbox graphic */
    }
    .indented-row {
        height: 3;
        padding-left: 4;
        align-vertical: middle;
    }
    .indented-text {
        padding-left: 4;
        height: 1;
        color: #aaaaaa; /* Light grey so description text is readable but secondary */
    }
    Checkbox {
        height: auto;
        width: auto;
        color: white; /* White text for contrast */
        background: transparent;
        border: none;
    }
    Input {
        width: 8;
        height: 1;
        min-width: 4;
        border: none;
        background: #161616; /* Darker fields inside the box for a sleek inset look */
        color: white;
        margin: 0 1;
    }
    Label {
        height: 1;
        color: white; /* White text for inline formulas/ranges */
        content-align-vertical: middle;
    }
    #duration-input {
        width: 14;
    }
    .advanced-settings-button {
        width: auto;
        min-width: 0;
        height: 1;
        color: #888888;
        border: none;
        margin: 1 0 0 1;
    }
    .spacer {
        width: 1fr;
    }
    .button-row {
        height: auto;
        align-horizontal: left;
        margin-top: 1;
    }
    /* Button {
        height: 3;
        margin-left: 1;
        min-width: 10;
        background: #3a3a3a;
        color: white;
        border: solid #4e4e4e;
    } */
    Button {
        height: 3;
        margin-left: 1;
        min-width: 10;
        width: 20;
        margin: 1 0 0 1;
        color: white;
    }
    .duration-row {
        height: 3;
        margin-top: 1;
        align-vertical: middle;
    }
    .more-stuff {
        height: 2;
        margin-top: 1;
        align-vertical: middle;
    }
    #duration-input {
        width: 14;
    }
    """

    def __init__(self, parent_view: "MainView") -> None:
        super().__init__()
        self.parent_view = parent_view
        self.settings = parent_view.settings

    def compose(self) -> ComposeResult:
        with Container(id="settings-container"):
            # Addition Section
            with Container(classes="section"):
                with Horizontal(classes="checkbox-row"):
                    yield Checkbox(value="+" in self.settings.operations, id="addition-check")
                    yield Label("Addition")
                with Horizontal(classes="indented-row"):
                    yield Label("Range: (")
                    yield Input(value=str(int(self.settings.addition_bounds[0])), id="add-min-a")
                    yield Label(" to ")
                    yield Input(value=str(int(self.settings.addition_bounds[1])), id="add-max-a")
                    yield Label(") + (")
                    yield Input(value=str(int(self.settings.addition_bounds[2])), id="add-min-b")
                    yield Label(" to ")
                    yield Input(value=str(int(self.settings.addition_bounds[3])), id="add-max-b")
                    yield Label(")")

            # Subtraction Section
            with Container(classes="section"):
                with Horizontal(classes="checkbox-row"):
                    yield Checkbox(value="-" in self.settings.operations, id="subtraction-check")
                    yield Label("Subtraction")
                yield Label("Addition problems in reverse.", classes="indented-text")

            # Multiplication Section
            with Container(classes="section"):
                with Horizontal(classes="checkbox-row"):
                    yield Checkbox(value="*" in self.settings.operations, id="multiplication-check")
                    yield Label("Multiplication")
                with Horizontal(classes="indented-row"):
                    yield Label("Range: (")
                    yield Input(value=str(int(self.settings.multiplication_bounds[0])), id="mul-min-a")
                    yield Label(" to ")
                    yield Input(value=str(int(self.settings.multiplication_bounds[1])), id="mul-max-a")
                    yield Label(") × (")
                    yield Input(value=str(int(self.settings.multiplication_bounds[2])), id="mul-min-b")
                    yield Label(" to ")
                    yield Input(value=str(int(self.settings.multiplication_bounds[3])), id="mul-max-b")
                    yield Label(")")

            # Division Section
            with Container(classes="section"):
                with Horizontal(classes="checkbox-row"):
                    yield Checkbox(value="/" in self.settings.operations, id="division-check")
                    yield Label("Division")
                yield Label("Multiplication problems in reverse.", classes="indented-text")

            # Duration Section
            with Horizontal(classes="duration-row"):
                yield Label("Duration: ")
                yield Input(placeholder="seconds", value=str(int(self.settings.game_duration)), id="duration-input")

            with Horizontal(classes="more-stuff"):
                yield Button("Revert to Defaults", id="revert-settings", classes="advanced-settings-button")
                
                yield Input(placeholder="Load preset #", id="preset-input", classes="advanced-settings-button")
                yield Static(classes="spacer")
                yield Button("Advanced/json...", id="advanced-settings-btn", classes="advanced-settings-button")

            # Action Buttons
            with Horizontal(classes="button-row"):
                yield Button("Save", id="save-btn")
                yield Button("Cancel", id="cancel-btn")
                yield Static(classes="spacer")
                yield Button("Save and Play", id="save-play-btn")

            # button to skip directly to Play

    def on_mount(self) -> None:
        self.query_one("#cancel-btn").focus() # if the user just wants to go back to the normal menu
        self.nopop = 0

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "preset-input":
            try:
                index = int(event.value)
                preset(presets.presets[index], self.parent_view.state)
                self.settings = self.parent_view.state.settings
                self.update()
            except (ValueError, IndexError) as e:
                dbgf.write(f"exception whilst applying preset: {e}")
            finally:
                event.input.value = ""

    def save_settings(self) -> None:
        try:
            duration = float(self.query_one("#duration-input", Input).value)
            self.settings.game_duration = duration
        except ValueError:
            self.settings.game_duration = DEFAULT_SETTINGS['game_duration']

        self.settings.operations = []
        if self.query_one("#addition-check", Checkbox).value:
            self.settings.operations.append("+")
        if self.query_one("#subtraction-check", Checkbox).value:
            self.settings.operations.append("-")
        if self.query_one("#multiplication-check", Checkbox).value:
            self.settings.operations.append("*")
        if self.query_one("#division-check", Checkbox).value:
            self.settings.operations.append("/")

        def parse_bounds(prefix: str) -> list[float]:
            values: list[float] = []
            for field_id in [f"{prefix}-min-a", f"{prefix}-max-a", f"{prefix}-min-b", f"{prefix}-max-b"]:
                try:
                    values.append(float(self.query_one(f"#{field_id}", Input).value))
                except ValueError:
                    values.append(0.0)
            return values

        self.settings.addition_bounds = parse_bounds("add")
        self.settings.multiplication_bounds = parse_bounds("mul")

        self.parent_view.settings = self.settings
        self.parent_view.state.settings = self.settings
        self.parent_view.state.save_settings()
        self.parent_view.update_status()
        self.parent_view.clear_annotations()


        if not self.nopop:
            self.app.pop_screen()

        self.nopop = 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self.save_settings()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "save-play-btn":
            self.save_settings()
            self.parent_view.show_play()
        elif event.button.id == "advanced-settings-btn":
            # The editor must always receive the complete current Settings
            # object.  This also preserves a just-selected preset or reverted
            # settings that has not yet been saved through the normal form.
            self.parent_view.state.settings = self.parent_view.settings = self.settings
            self.parent_view.state.save_settings(force=True)
            with self.app.suspend():
                open_file(self.parent_view.state.config_path)
            self.parent_view.state.settings = self.parent_view.settings = self.settings = self.parent_view.state.load_settings("self.settings")
            self.update()
            self.parent_view.clear_annotations()
        elif event.button.id == "revert-settings":
            self.settings = self.parent_view.state.default_settings()
            self.update()
    def update(self) -> None:
        operations = { # the 2 args, then their value, e.g., for self.query_one("#duration-input", Input).value = str(int(self.settings.game_duration)) it will be ("#duration-input", Input), str(int(self.settings.game_duration)))
            ("#duration-input", Input): str(int(self.settings.game_duration)),
            ("#addition-check", Checkbox): "+" in self.settings.operations,
            ("#subtraction-check", Checkbox): "-" in self.settings.operations,
            ("#multiplication-check", Checkbox): "*" in self.settings.operations,
            ("#division-check", Checkbox): "/" in self.settings.operations,
            ("#add-min-a", Input): str(int(self.settings.addition_bounds[0])),
            ("#add-max-a", Input): str(int(self.settings.addition_bounds[1])),
            ("#add-min-b", Input): str(int(self.settings.addition_bounds[2])),
            ("#add-max-b", Input): str(int(self.settings.addition_bounds[3])),
            ("#mul-min-a", Input): str(int(self.settings.multiplication_bounds[0])),
            ("#mul-max-a", Input): str(int(self.settings.multiplication_bounds[1])),
            ("#mul-min-b", Input): str(int(self.settings.multiplication_bounds[2])),
            ("#mul-max-b", Input): str(int(self.settings.multiplication_bounds[3])),
            # ("#no-log-input", Input): str(self.settings.no_log),
            # ("#flash-digits-input", Input): str(self.settings.flash_digits),
            # ("#flash-duration-input", Input): str(self.settings.flash_duration),
            # ("#flash-number-input", Input): str(self.settings.flash_number),
            # ("#save-settings-state-check", Checkbox): self.settings.save_settings_state,
            # ("#cheat-mode-check", Checkbox): self.settings.cheat_mode,
        }
        for query, value in operations.items():
            try:
                self.query_one(*query).value = value
            except Exception as e:
                dbgf.write(f"exception whilst reverting to default settings: {e}")
        # save_settings_state doesn't mean what you think, it means saving it to disk, and it doesn't mean letting the user change the settings!

    def action_save(self) -> None:
        self.nopop = 1
        self.query_one("#save-btn").press()

    def action_save_and_play(self) -> None:
        self.query_one("#save-play-btn").press()

    def action_defaults(self) -> None:
        self.query_one("#revert-settings").press()

    def action_focus_presets(self) -> None:
        self.query_one("#preset-input").focus()

    def action_cancel(self) -> None:
        self.app.pop_screen()



class PlayScreen(Screen):
    CSS = """
    PlayScreen { background: #111111; color: white; padding: 1 2; }
    #play-root { width: 100%; height: 100%; }
    #hud { layout: horizontal; width: 100%; margin-bottom: 2; }
    #time-left { width: 1fr; }
    #score-right { width: 1fr; text-align: right; }
    #play-center {
        width: 100%;
        height: auto; 
        align-vertical: middle;
        align-horizontal: center;
        /* This ensures the Label and Input sit next to each other */
    }

    #problem-label {
        width: auto;
        padding-right: 1; /* Space between the = and the box */
        padding-top: 1;
        height: 3;
    }

    #answer-input {
        width: 24;
    }
    #quit-run { width: 20; margin: 1 0 0 0; }
    """
    """
    #play-center { width: 100%; height: 1fr; content-align: center middle; }
    #problem-label { width: 100%; text-align: center; padding: 1 0; }
    #answer-input { width: 24; }
    """

    def __init__(self, parent_view: "MainView", problem_factory, settings: Settings, is_replay: bool = False, replay_stats = {}, uses_custom_generator: bool | None = None) -> None:
        super().__init__()
        self.parent_view = parent_view
        self.problem_factory = problem_factory
        self.settings = settings
        self.is_replay = is_replay
        self.replay_stats = replay_stats
        # Infer the flag for direct PlayScreen callers too.  Replay screens
        # pass their own factory, so a configured custom generator does not
        # accidentally suppress replay behaviour.
        resolved_generator = resolve_generation_function(settings.generation_function)
        self.uses_custom_generator = (
            bool(settings.generation_function)
            and problem_factory is resolved_generator
            if uses_custom_generator is None
            else uses_custom_generator
        )
        self.current_problem: tuple[str, float] | None = None
        self.score = 0
        self.elapsed = 0.0
        self.start_time = 0.0
        self.question_deadline = 0.0
        self.round_running = False
        self.round_logs: dict[str, str] = {}
        self._tick_timer = None

    def compose(self) -> ComposeResult:
        yield Container(
            Container(
                Label("Seconds used: --" if self.is_replay else "Seconds left: --", id="time-left"),
                Label(f"Replayed: 0 / {self.replay_stats['question_number']}" if self.is_replay else "Score: 0", id="score-right"),
                id="hud",
            ),
            Container(
                Horizontal(
                    Label("", id="problem-label"),
                    Input(placeholder="", id="answer-input"),
                    id="play-center",
                ),
            ),
            Button("Quit Run", id="quit-run"),
            id="play-root",
        )

    def on_mount(self) -> None:
        self.start_round()

    def start_round(self) -> None:
        if self._tick_timer is not None:
            self._tick_timer.stop()
        self.score = 0
        self.elapsed = 0.0
        self.start_time = time.monotonic()
        self.question_deadline = self.start_time + self.parent_view.settings.game_duration
        self.round_logs = {}
        self.round_running = True
        self._tick_timer = self.set_interval(0.1, self.tick)
        self.next_question()

    def next_question(self) -> None:
        if not self.round_running:
            return
        problem = self.problem_factory()
        if problem is None:
            self.finish_round()
            return
        self.current_problem = problem
        problem_text = self.current_problem[0]
        # answers may be of different length
        # exceptionally, there may be a 100+100, which is (100 + 100), which is 9 len
        # so we pad
        problem_text = (9 - len(problem_text)) * " " + problem_text
        self.query_one("#problem-label", Label).update(f"{problem_text} =")
        input_widget = self.query_one("#answer-input", Input)
        input_widget.display = True
        input_widget.value = ""
        input_widget.focus()

        if self.settings.cheat_mode:
            input_widget.placeholder = str(problem[1])


    def on_input_changed(self, event: Input.Changed) -> None:
        # we won't change the problem label to update with the user answer; previously it was done with
        if not self.round_running or self.current_problem is None:
            return
        if event.input.id != "answer-input":
            return
        candidate = event.value.strip()
        self.elapsed = time.monotonic() - self.start_time
        if not candidate:
            return
        try:
            value = float(candidate)
        except ValueError:
            return
        answer = self.current_problem[1]
        if math.isfinite(value) and abs(value - answer) < 1e-9:
            self.score += 1
            self.round_logs[str(round(self.elapsed, 3))] = self.current_problem[0]
            self.query_one("#score-right", Label).update(f"Score: {self.score}" if not self.is_replay else f"Replayed: {self.score} / {self.replay_stats['question_number']}")
            self.next_question()
        else:
            pass

    def key_q(self) -> None:
        self.quit_run()

    def key_escape(self) -> None:
        self.quit_run()

    def quit_run(self) -> None:
        if not self.round_running:
            return
        self.finish_round(quit_requested=True)

    def finish_round(self, quit_requested: bool = False) -> None:
        if not self.round_running:
            return
        self.round_running = False
        s = self.parent_view.settings
        if self._tick_timer is not None:
            self._tick_timer.stop()
            self._tick_timer = None
        is_satisfied = all(
            getattr(s, key) == expected_value 
            for key, expected_value in _DEFAULT_RUN.items() # internal use, should not be modified since that could introduce bugs
        ) # some fields don't matter, which don't feature in _DEFAULT_RUN
        pb = 0
        if not s.no_log and not self.uses_custom_generator and not quit_requested and s.cheat_mode == False and is_satisfied:
            logged = 1
            max_score = run_max(self.parent_view.state.conn) # get it BEFORE logging the run
            record_run(self.parent_view.state.conn, "runs", self.score, self.round_logs)
            dbgf.write(f"self.score = {self.score}; max_score = {max_score};\n")
            if self.score > max_score:
                pb = 1
                dbgf.write(f"pb!\n")
            else:
                dbgf.write(f"no pb\n")
        else:
            logged = 0
        if (self.parent_view.settings.no_log & 2):
            self.parent_view.settings.no_log ^= 2
        if pb:
            header = f"[gold]NEW PB!!![/] (previous: {max_score})\n"
        else:
            val = self.is_replay | (2 * quit_requested)
            header = [
                "Time's up!",
                "Finished replay!",
                "Run quit!",
                "Replay quit!",
            ][val]
        # generate analytics using _analytics function from data_analysis.py
        try:
            summary = _analytics_summary_(json.dumps(self.round_logs))
        except Exception as exc:
            summary = f"Unable to compute analytics: {exc}"
        if self.is_replay:
            # if it is a replay_hardest, just display the finish time and original finish time
            # otherwise, display what the user would have scored with the normal time, and what they originally took
            special_bit = f"You would have scored {(self.score * self.replay_stats['time_taken'] / (self.elapsed or 0.01)):.2f} with the normal time. " if self.replay_stats["type"] == "replay" else f"Originally, you took {'around ' if quit_requested else ''}{(self.replay_stats['time_taken'] * self.score / (self.replay_stats['question_number'] or 0.01)):.2f} seconds. "
            detail = f"{header}\n\nTime taken: {self.elapsed:.2f}s\n" + special_bit + f"\nSummary:\n{summary}"
        else:
            detail = f"{header}\n{'Logged run!' if logged else 'On this pace, you would have scored ~' + str(round(self.score * DEFAULT_SETTINGS['game_duration'] / (self.elapsed or 0.01), 2)) + f' if you had finished the run. ' if quit_requested else ''}\nScore: {self.score}{f'; Time taken: {self.elapsed:.1f}' if quit_requested else ''}\nSummary:\n{summary}"
        self.parent_view.query_one("#detail", Label).update(detail)
        # this may be confusing to look at, but **THIS IS NOT BUGGED**. through testing, one can see that everything is printed correctly
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-run":
            self.quit_run()

    def tick(self) -> None:
        if self.round_running:
            self.elapsed = max(0.0, time.monotonic() - self.start_time)
            if self.is_replay or self.settings.game_duration == -1:
                pass
                self.query_one("#time-left", Label).update(f"Seconds used: {self.elapsed:.0f}")
            else:
                remaining = max(0.0, self.question_deadline - time.monotonic())
                self.query_one("#time-left", Label).update(f"Seconds left: {remaining:.0f}")
                if remaining <= 0 and not self.is_replay:
                    self.finish_round()


class ReplaySelectionScreen(Screen):
    PAGE_SIZE = 32
    LOAD_AHEAD = 8
    BINDINGS = [Binding("delete", "request_delete", "Delete run")]

    CSS = """
    ReplaySelectionScreen { background: #111111; color: white; padding: 1 2; }
    #replay-select-root { width: 100%; height: 100%; }
    #pane-row { width: 100%; height: 100%; }
    #run-pane { width: 36%; min-width: 36; height: 100%; padding-right: 1; border-right: solid #444444; layout: vertical; }
    #summary-pane { width: 1fr; height: 100%; padding-left: 1; }
    #run-list {
        height: 0.36fr;
        max-height: 1fr;
        min-height: 0;
    }
    #run-summary { width: 100%; height: 100%; overflow: auto; border: solid #444444; padding: 1; }
    #replay-instructions { padding-bottom: 1; }
    #run-controls { padding-top: 1; align-horizontal: right; }
    Button {
        margin-right: 1;
        height: 3;
    }
    .spacer {
        width: 1fr;
    }
    #stats-label {
        align-horizontal: right;
        margin-right: 1;
        height: auto;
    }
    """

    def __init__(self, parent_view: "MainView", default_id: int, mode: str = "replay") -> None:
        super().__init__()
        self.parent_view = parent_view
        # Metadata is deliberately fetched in pages below.  ``available_runs``
        # remains an argument for compatibility with the callers, but retaining
        # it here would keep the full history in the widget unnecessarily.
        self.available_runs: list[dict] = []
        self._loaded_runs = 0
        self._has_more_runs = True
        self.default_id = default_id
        self.mode = mode
        self.selected_run_id: int | None = None
        self.last_selected: int | None = None
        self._pending_delete_id: int | None = None

    def compose(self) -> ComposeResult:
        with Container(id="replay-select-root"):
            yield Label(
                "Select a run to preview. Press Enter once for preview; press Enter twice quickly to confirm.",
                id="replay-instructions",
            )
            with Horizontal(id="pane-row"):
                with Container(id="run-pane"):
                    yield ListView(
                        id="run-list",
                    )
                    with Horizontal(id="run-controls"):
                        if self.mode != "replay":
                            yield Label(f"Average: {run_avg(self.parent_view.state.conn)}\nAverage today: {run_avg_today(self.parent_view.state.conn)}\nHighscore: {run_max(self.parent_view.state.conn)}\nHighscore today: {run_max_today(self.parent_view.state.conn)}", id="stats-label")
                            yield Static(classes="spacer")
                        yield Button("Back", id="back-btn")
                with Container(id="summary-pane"):
                    yield Static("No run selected.", id="run-summary")

    def on_mount(self) -> None:
        run_list = self.query_one("#run-list", ListView)
        run_list.focus()
        self._load_more_runs()
        if self.available_runs:
            run_list.index = 0
            self.selected_run_id = int(self.available_runs[0]["id"])
            self._refresh_summary(self.selected_run_id)

    def _load_more_runs(self) -> None:
        """Append one metadata page, newest runs first."""
        if not self._has_more_runs:
            return
        rows = self.parent_view.state.conn.execute(
            "SELECT id, ts, score FROM runs ORDER BY id DESC LIMIT ? OFFSET ?",
            (self.PAGE_SIZE, self._loaded_runs),
        ).fetchall()
        page = [dict(row) for row in rows]
        self._loaded_runs += len(page)
        self._has_more_runs = len(page) == self.PAGE_SIZE
        if not page:
            return
        self.available_runs.extend(page)
        run_list = self.query_one("#run-list", ListView)
        for run in page:
            run_list.append(
                ListItem(Label(f"{run['id']} | score={run['score']} | ts={run['ts']}"))
            )

    def _load_more_if_needed(self, index: int) -> None:
        if self._has_more_runs and index >= len(self.available_runs) - self.LOAD_AHEAD:
            self._load_more_runs()

    @on(ListView.Highlighted)
    def on_run_highlighted(self, event: ListView.Highlighted) -> None:
        if event.list_view.id != "run-list":
            return
        index = event.list_view.index
        if index is None or index < 0 or index >= len(self.available_runs):
            return
        self.selected_run_id = int(self.available_runs[index]["id"])
        self._pending_delete_id = None
        self._refresh_summary(self.selected_run_id)
        self._load_more_if_needed(index)

    @on(ListView.Selected)
    def on_run_selected(self, event: ListView.Selected) -> None:
        event.stop()
        if event.list_view.id != "run-list":
            return
        index = event.list_view.index
        if index is None or index < 0 or index >= len(self.available_runs):
            return
        self._load_more_if_needed(index)

    def _refresh_summary(self, run_id: int) -> None:
        run = get_run(self.parent_view.state.conn, run_id)
        if not run:
            self.query_one("#run-summary", Static).update("Unable to load run details.")
            return
        logs = run.get("logs") or {}
        try:
            summary = _analytics_summary_(json.dumps(logs))
        except Exception as exc:
            summary = f"Unable to compute analytics: {exc}"
        dbgf.write(f"{rich.text.Text.from_ansi(summary)}\n")
        nsummary = rich.text.Text.from_ansi(f"Run ID: {run['id']}\nScore: {run['score']}\nTS: {run['ts']}\n{summary}")
        self.query_one("#run-summary", Static).update(
            nsummary
        )

    def _activate_selected(self, run_id: int) -> None:
        if self.mode == "replay":
            self.app.pop_screen()
            self.parent_view._launch_replay(run_id, self.default_id)
            return
        run = get_run(self.parent_view.state.conn, run_id)
        if run is None:
            self.query_one("#run-summary", Label).update("Unable to load full run JSON.")
            return

        try:
            with self.app.suspend():
                tempf = tempfile.NamedTemporaryFile(prefix="zetamac-tui_", suffix=".json", delete=False) # delete after editing to accomodate windows systems
                tempf.write(json.dumps(run, indent="\t").encode("utf-8"))
                tempf.flush()
                tempf.close()
                open_file(tempf.name)
        except Exception as e:
            self.query_one("#run-summary", Label).update(
                f"Error whilst opening json: {e}"
            )


    def _select_or_activate(self, run_id: int) -> None:
        if self.last_selected == run_id:
            self._activate_selected(run_id)
            self.last_selected = None
            return
        self.last_selected = run_id
        self._refresh_summary(run_id)

    def key_enter(self) -> None:
        if self.selected_run_id is None:
            return
        self._select_or_activate(self.selected_run_id)

    def key_escape(self) -> None:
        self.app.pop_screen()

    def action_request_delete(self) -> None:
        """Require a second Delete press before permanently removing a run."""
        if self.selected_run_id is None:
            return
        if self._pending_delete_id != self.selected_run_id:
            self._pending_delete_id = self.selected_run_id
            self.query_one("#run-summary", Static).update(
                f"Delete run {self.selected_run_id}? Press Delete again to confirm."
            )
            return

        run_id = self.selected_run_id
        self.parent_view.state.conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        self.parent_view.state.conn.commit()
        index = next(
            index for index, run in enumerate(self.available_runs)
            if int(run["id"]) == run_id
        )
        del self.available_runs[index]
        self._loaded_runs -= 1
        self._pending_delete_id = None
        self.last_selected = None
        run_list = self.query_one("#run-list", ListView)
        run_list.remove_items([index])

        if not self.available_runs:
            self.selected_run_id = None
            self.query_one("#run-summary", Static).update("No runs available.")
            return
        new_index = min(index, len(self.available_runs) - 1)
        run_list.index = new_index
        self.selected_run_id = int(self.available_runs[new_index]["id"])
        self._refresh_summary(self.selected_run_id)
        self._load_more_if_needed(new_index)

    @on(events.Click, "#run-list")
    def on_run_list_click(self, event: events.Click) -> None:
        event.stop()
        if self.selected_run_id is None:
            return
        if event.chain == 1:
            self._select_or_activate(self.selected_run_id)
        elif event.chain == 2:
            self._activate_selected(self.selected_run_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()


class FlashAnzan(Screen):
    """A timed mental-addition exercise using the configured flash settings."""

    CSS = """
    FlashAnzan {
        background: #111111;
        color: white;
        padding: 1 2;
    }
    #flash-root {
        width: 100%;
        height: 100%;
    }
    #flash-content {
        width: 100%;
        height: 1fr;
        align: center middle;
    }
    #flash-number, #flash-result {
        width: 100%;
        text-align: center;
    }
    #flash-number {
        text-style: bold;
    }
    #flash-answer-row {
        width: auto;
        height: 3;
        align-vertical: middle;
        align-horizontal: center;
        width: 100%;
        text-align: center;
    }
    #what-is-the-sum {
        padding-top: 1;
        height: 3;
    }
    #flash-answer-input {
        width: 24;
        margin-left: 1;
    }
    #flash-answer-input:focus {
        border: solid blue;
    }
    #flash-quit {
        dock: bottom;
        width: 20;
        margin: 0 0 1 0;
    }
    #red-box {
        width: 2;
        height: 1;
        background: red;
        align-horizontal: left;
        align-vertical: top;
    }
    #flashed-count {
        margin-left: 1;
        width: auto;
    }
    /* make metadata on the very top of the screen */
    #metadata-row {
        width: 100%;
        height: 1;
        align-horizontal: left;
        align-vertical: top;
    }
    .spacer {
        width: 1fr;
    }
    """

    def __init__(self, parent_view: "MainView") -> None:
        super().__init__()
        self.parent_view = parent_view
        self.settings = parent_view.settings
        self.numbers: list[int] = []
        self.total = 0
        self.playing = True
        self.awaiting_answer = False
        self._flash_worker = None

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Static(id="red-box"),
            Static(classes="spacer"),
            Label(f"0 / {self.settings.flash_number}", id="flashed-count"),
            id="metadata-row",
        )
        yield Container(
            Label("", id="flash-number"),
            Horizontal(
                Label("What is the sum?", id="what-is-the-sum"),
                Input(placeholder="Sum", id="flash-answer-input"),
                id="flash-answer-row",
            ),
            Label("", id="flash-result"),
            id="flash-content",
        )
        yield Button("Quit", id="flash-quit")

    def fmt(self, x):
        try:
            import pyfiglet
            return pyfiglet.figlet_format(str(x))
        except:
            return str(x)

    def on_mount(self) -> None:
        self.query_one("#flash-answer-row").display = False

        self.red_box = self.query_one("#red-box", Static)
        self.hide_red_box()
        self.call_after_refresh(self._start_flashing)
    
    def _start_flashing(self) -> None:
        self._flash_worker = self.run_worker(self.play_numbers(), exclusive=True)

    async def play_numbers(self) -> None:
        """Display each generated number for the configured duration."""
        digits = max(1, int(self.settings.flash_digits))
        count = max(1, int(self.settings.flash_number))
        duration = max(0.0, float(self.settings.flash_duration))
        minimum = 10 ** (digits - 1)
        maximum = (10 ** digits) - 1
        self.numbers = [random.randint(minimum, maximum) for _ in range(count)]
        self.total = sum(self.numbers)
        number_label = self.query_one("#flash-number", Label)


        self._tasks = set()
        self.flashed_count = 0
        self.flashed_count_label = self.query_one("#flashed-count", Label)
        self.red_box = self.query_one("#red-box", Static)
        self.red_box.display = True
        for number in self.numbers:
            if not self.playing:
                return
            number_label.update(self.fmt(str(number)))
            timer_const = 0.5
            t = asyncio.create_task(beep(duration*timer_const, self.settings.flash_volume))
            self._tasks.add(t)
            self.flashed_count += 1
            self.flashed_count_label.update(f"{self.flashed_count} / {self.settings.flash_number}")
            self.red_box.display = True
            t = self.set_timer(duration*timer_const, self.hide_red_box)
            self._tasks.add(t)
            await asyncio.sleep(duration)

        if not self.playing:
            return
        number_label.update("")
        self.awaiting_answer = True
        answer_row = self.query_one("#flash-answer-row")
        answer_row.display = True
        self.query_one("#flash-answer-input", Input).focus()

    def hide_red_box(self) -> None:
        self.red_box.display = False

    @on(Input.Submitted, "#flash-answer-input")
    def check_answer(self, event: Input.Submitted) -> None:
        if not self.awaiting_answer:
            return
        answer = parse_answer(event.value)
        result = self.query_one("#flash-result", Label)
        if answer is not None and answer == self.total:
            result.update("Correct!")
        else:
            result.update(f"Incorrect. The sum was {self.total}.")
        self.awaiting_answer = False
        self.query_one("#flash-answer-input", Input).disabled = True

    def quit(self) -> None:
        self.playing = False
        if self._flash_worker is not None:
            self._flash_worker.cancel()
        self.parent_view.clear_annotations()
        self.app.pop_screen()

    def key_escape(self) -> None:
        self.quit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "flash-quit":
            self.quit()

def _manual_wildcard_import(module_name, target_globals):
    module = __import__(module_name)
    
    if hasattr(module, '__all__'):
        attrs = module.__all__
    else:
        attrs = [name for name in dir(module) if not name.startswith('_')]
        
    for attr in attrs:
        target_globals[attr] = getattr(module, attr)

class MainView(App):
    CSS = """
    Screen { background: #111111; color: white; }
    #menu-list { height: 8.5; }
    #status { padding: 1 2; }
    #detail { padding: 1 2; text-wrap: wrap; }
    .spacer {
        width: 1fr;
    }
    #root {
        height: 100%;
    }
    #bottom-bar {
        dock: bottom;
        width: 100%;
        height: 3;
        padding: 0 1;
        background: #111111;
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.settings = state.settings
        self.menu_items = ["Settings", "Play", "Flash Anzan", "Replay", "Replay Hardest", "View Runs and Stats", "SQLite3 shell", "Python repl", "Quit"]
        self.selected = 0

    def compose(self) -> ComposeResult:
        with Container(id="root"):
            yield Label("zetamac-tui, on yaofanfish/zetamac-tui", id="title")
            yield Label("Use ↑/↓ or j/k to move, Enter to select.", id="status")
            yield ListView(*[ListItem(Label(item)) for item in self.menu_items], id="menu-list")
            yield Label("", id="detail")
            with Horizontal(id="bottom-bar"):
                yield Button("Quit", id="quit")
                yield Static(classes="spacer")
                yield Button("Clear Annotations", id="clear-annotations-btn")

    def on_mount(self) -> None:
        self.query_one("#menu-list", ListView).index = self.selected
        self.update_status()

        self.state.all_init()

        # closer to the real zetamac experience
        self.show_settings()

    def update_status(self) -> None:
        self.query_one("#status", Label).update(
            f"Duration: {self.settings.game_duration:.0f}s | Ops: {''.join(self.settings.operations)}"
        )

    def action_cursor_down(self) -> None:
        self.selected = (self.selected + 1) % len(self.menu_items)
        self.query_one("#menu-list", ListView).index = self.selected

    def action_cursor_up(self) -> None:
        self.selected = (self.selected - 1) % len(self.menu_items)
        self.query_one("#menu-list", ListView).index = self.selected

    @on(ListView.Selected)
    def handle_menu_selection(self, event: ListView.Selected) -> None:
        index = event.list_view.index
        if index is None or index >= len(self.menu_items):
            return

        selected_label = self.menu_items[index]
        
        self.do_action(selected_label)

    def key_j(self) -> None:
        self.action_cursor_down()

    def key_k(self) -> None:
        self.action_cursor_up()

    def key_q(self) -> None:
        self.exit()

    def activate_selection(self) -> None:
        item = self.menu_items[self.selected]
        self.do_action(item)
    
    def do_action(self, item) -> None:
        if item == "Play":
            self.show_play()
        elif item == "Settings":
            self.show_settings()
        elif item == "Flash Anzan":
            self.show_flash_anzan()
        elif item == "Replay":
            self.show_replay()
        elif item == "Replay Hardest":
            self.show_replay_hardest()
        elif item == "View Runs and Stats":
            self.show_runs()
        elif item == "SQLite3 shell":
            self.sqlite3_shell()
        elif item == "Python repl":
            self.python_repl()
        elif item == "Quit":
            self.exit()

    def show_play(self) -> None:
        custom_generator = resolve_generation_function(self.settings.generation_function)
        if self.settings.generation_function is not None and custom_generator is None:
            self.query_one("#detail", Label).update(f"[red]Error[/]: Could not resolve generation function '{self.settings.generation_function}'. \nPlease check if the function is defined,\n or turn this off by going to Settings --> Advanced/json...,\n and then replacing \"generation_function\": \"{self.settings.generation_function}\" with \"generation_function\": null. ")
            return
        problem_factory = custom_generator if custom_generator else (lambda: generate_problem(self.settings))
        self.push_screen(
            PlayScreen(
                self,
                problem_factory=problem_factory,
                settings=self.settings,
                uses_custom_generator=bool(custom_generator),
            )
        )

    def show_settings(self) -> None:
        self.push_screen(SettingsScreen(self))

    def show_flash_anzan(self) -> None:
        self.push_screen(FlashAnzan(self))

    def show_replay(self) -> None:
        latest_run = get_recent_runs(self.state.conn, limit=1)
        if not latest_run:
            self.query_one("#detail", Label).update("No runs available yet.")
            return
        latest_id = int(latest_run[0]["id"])
        self.push_screen(ReplaySelectionScreen(self, latest_id, mode="replay"))

    def show_runs(self) -> None:
        latest_run = get_recent_runs(self.state.conn, limit=1)
        if not latest_run:
            self.query_one("#detail", Label).update("No runs available yet.")
            return
        latest_id = int(latest_run[0]["id"])
        self.push_screen(ReplaySelectionScreen(self, latest_id, mode="browse"))

    def sqlite3_shell(self):
        with self.suspend():
            try:
                os.system("cls" if os.name == "nt" else "clear")
#                print("\x1b[1mDo NOT exit via ^C if you don't want to terminate the entire program. \x1b[0m") # fixed now
                sql_sh(self.state.conn)
            except BaseException as e:
                dbgf.write(f"Error in sql_sh: {e}\n")

    def python_repl(self) -> None:
        """Menu action: drop into an interactive Python REPL exposing
        the running app's state, for calling lower functions/dev/debugging/lower-level work."""

        global userfuncs, presets
        import userfuncs
        _manual_wildcard_import("userfuncs", globals())
        import presets

        import zetamac_tui_doc
        zetamac_tui_doc.apply_repl_docs(globals())

        import code

        repl_locals = dict(globals(), **locals())
        repl_locals.update({
            "state": self.state,
            "settings": self.settings,
            "conn": self.state.conn,
            "help": zetamac_tui_doc.ReplHelp(),
        })
        banner = f"Python {sys.version} on {sys.platform}. \nEntering zetamac shell; Type help() to see what's available.\n"

        with self.suspend():
            try:
                os.system("cls" if os.name == "nt" else "clear")
                code.interact(local=repl_locals, banner=banner)
            except BaseException as e: # need to catch SystemExit
                dbgf.write(str(e)+"\n")

    def _launch_replay(self, selected_id: int, fallback_id: int) -> None:
        run = get_run(self.state.conn, selected_id)
        if run is None:
            run = get_run(self.state.conn, fallback_id)
        if run is None:
            self.query_one("#detail", Label).update("No runs available yet.")
            return
        self.settings.no_log |= 2
        self.push_screen(
            PlayScreen(
                self,
                problem_factory=ReplayProblemFactory(run.get("logs") or {}),
                settings=self.settings,
                is_replay=True,
                replay_stats={"time_taken": DEFAULT_SETTINGS['game_duration'], "type": "replay", "question_number": len(run["logs"])}, # logged will always be default
            )
        )

    def show_replay_hardest(self) -> None:
        runs = get_all_runs(self.state.conn)
        if not runs:
            self.query_one("#detail", Label).update("No runs available yet.")
            return

        replay_logs, time_taken = build_hardest_replay_logs(runs)
        if not replay_logs:
            self.query_one("#detail", Label).update("No replayable questions available yet.")
            return

        self.settings.no_log += 2
        self.push_screen(
            PlayScreen(
                self,
                problem_factory=ReplayProblemFactory(replay_logs),
                settings=self.settings,
                is_replay=True,
                replay_stats={"time_taken": time_taken, "type": "replay_hardest", "question_number": len(replay_logs)},
            )
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.exit()
        elif event.button.id == "clear-annotations-btn":
            self.clear_annotations()
    
    def clear_annotations(self):
        self.query_one("#detail", Label).update("")



class ReplayProblemFactory:
    def __init__(self, logs: dict) -> None:
        self.timeline = compute_timeline(logs or {})
        self.index = 0

    def __call__(self) -> tuple[str, float] | None:
        while self.index < len(self.timeline):
            entry = self.timeline[self.index]
            self.index += 1
            parsed = _parse_logged_problem(entry[1])
            if parsed is not None:
                return parsed
        return None


def _parse_logged_problem(raw: str) -> tuple[str, float] | None:
    expression = raw.strip()
    if not expression:
        return None
    parts = expression.split()
    if len(parts) != 3:
        return None
    left, op, right = parts
    try:
        a = float(left)
        b = float(right)
    except ValueError:
        return None
    if op == "+":
        answer = a + b
    elif op == "-":
        answer = a - b
    elif op == "*":
        answer = a * b
    elif op == "/":
        if b == 0:
            return None
        answer = a / b
    else:
        return None
    return expression, answer


def build_hardest_replay_logs(runs):
    replay_logs: dict[str, str] = {}
    cumulative_time = 0.0

    for run in runs:
        logs = run.get("logs") or {}
        if not logs:
            continue

        analytics = _analytics(json.dumps(logs))
        slowest_questions = analytics["summary"]["slowest"][:3]

        for expression, time_used in slowest_questions:
            cumulative_time += float(time_used)
            replay_logs[str(round(cumulative_time, 3))] = expression

    return replay_logs, cumulative_time

def run_demo() -> None:
    state = AppState()
    settings = state.settings
    expr, answer = generate_problem(settings)
    print("Demo problem:", expr, "=>", answer)
    record_run(state.conn, "runs", 3, {"0.1": expr})
    print("Saved demo run to", state.db_path)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"--demo", "demo"}:
        run_demo()
        return
    global state, app
    state = AppState()
    app = MainView(state)
    try:
        app.run()
    finally:
        state.save_settings()

    try:
        import miniaudio
        import pyfiglet
    except:
        print("\x1b[31mYou have not installed the [opt] dependencies for this project, which means that some features may not work as well for you. If you change you mind, run\n\tpipx install -e zetamac-tui[opt] # do [dev,opt] if you want the dev stuff too")


if __name__ == "__main__":
    main()

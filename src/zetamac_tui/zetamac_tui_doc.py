"""REPL documentation heredocs for zetamac-tui.

Doc strings defined here are attached to the corresponding objects in
main.py so that help(<name>) in the debug REPL shows useful reference text.
"""

import pydoc
from typing import Any


SETTINGS_DOC = """
Settings -- game configuration dataclass.

Attributes:
    game_duration (float): Seconds per timed round (default 120).
    cheat_mode (bool): When True, show the correct answer while playing.
    no_log (int): When non-zero, skip writing runs to the database.
    addition_bounds (list[int]): [min_a, max_a, min_b, max_b] for + and -.
    multiplication_bounds (list[int]): [min_a, max_a, min_b, max_b] for * and /.
    operations (list[str]): Enabled operators, subset of "+", "-", "*", "/".
    flash_digits (int): Digits shown per flash in Flash Anzan mode.
    flash_duration (float): Seconds each flash digit stays visible.
    flash_number (int): How many digits to flash before the answer prompt.
    flash_volume (int): Volume for flash sounds, from 1 (quiet) to 100 (full).
    generation_function (callable | None): Optional runtime-only question
        generator.  A truthy callable returning ``(expression, answer)`` is
        used by PlayScreen instead of generate_problem.  Custom-generator runs
        are not saved to the runs database.  This value is not stored in
        settings.json; falsey values use the normal generator.
    save_settings_state (bool): When False, in-app edits are not persisted.

Loaded from ~/.config/zetamac-tui/settings.json via AppState.load_settings().
Persist changes with state.save_settings() after editing the in-memory instance.

Example:
    >>> settings.game_duration = 60
    >>> settings.operations = ["+", "-"]
    >>> state.save_settings()

    >>> settings.generation_function = lambda: ("6 * 7", 42)
"""


APP_STATE_DOC = """
AppState -- persistent settings and sqlite3 connection for the running app.

Attributes:
    settings (Settings): Current game configuration (mutate, then save_settings()).
    conn (sqlite3.Connection): Open connection to runs.db (table: runs).
    config_path (Path): Path to settings.json (~/.config/zetamac-tui/settings.json).
    db_path (Path): Path to runs.db (~/.local/share/zetamac-tui/runs.db).
    config_dir (Path): Parent directory of settings.json.
    home (Path): Resolved home directory for config/data paths.

Methods:
    load_settings() -> Settings: Read settings.json, merge with defaults.
    save_settings(force=False) -> None: Write settings to settings.json.
    open_db() -> sqlite3.Connection: Connect and ensure the runs table exists.
    default_settings() -> Settings: Return a fresh Settings with app defaults.

In the REPL, `state` is the live AppState for the running session; `settings`
and `conn` are shortcuts for state.settings and state.conn.
"""


APP_STATE_SAVE_SETTINGS_DOC = """
Persist state.settings to settings.json on disk.

If settings.save_settings_state is False, only that flag is written unless
force=True. Call this after editing settings in the REPL:

    settings.game_duration = 90
    state.save_settings()
"""


APP_STATE_LOAD_SETTINGS_DOC = """
Read settings.json and return a Settings instance merged with defaults.

Missing or invalid keys fall back to DEFAULT_SETTINGS. Called automatically
when AppState is constructed.
"""


APP_STATE_OPEN_DB_DOC = """
Open (or create) the sqlite3 runs database and ensure the schema exists.

Returns a connection with row_factory=sqlite3.Row. The runs table columns are:
id, score, ts (ISO timestamp), logs (JSON object of elapsed-seconds -> expression).
"""


GENERATE_PROBLEM_DOC = """
Generate one random arithmetic problem from the given Settings.

Args:
    settings: A Settings instance controlling operations and operand ranges.

Returns:
    (expression_str, answer): e.g. ("12 + 7", 19). Division problems are
    constructed so the answer is always an integer.

Example:
    >>> expr, ans = generate_problem(settings)
    >>> print(expr, "=>", ans)
"""


TT_DOC = """
Configure the built-in times-table generator for PlayScreen.

Args:
    a: Allowed values for the left-hand multiplier.
    b: Allowed values for the right-hand multiplier. Defaults to an empty
       list.
    settings: Settings to update. When omitted, uses the running app's global
       state.settings.

Empty operand lists expand to the corresponding current multiplication range.
The function sets settings.generation_function to _tt.  This is a runtime-only
override, so its games are not logged and it is not written to settings.json.

Examples:
    >>> tt([6, 7], [2, 3])
    >>> tt([], [12], settings)  # current left-hand range × 12
"""


COMPUTE_TIMELINE_DOC = """
Convert a run's logs dict into a sorted timeline of (elapsed_seconds, expression).

Args:
    logs: Mapping of elapsed-seconds strings to problem expressions, as stored
          in the database by record_run, e.g. {"1.203": "5 + 7", "2.891": "3 * 4"}.

Returns:
    List of (float, str) tuples sorted by elapsed time ascending.

Example:
    >>> run = get_run(conn, 1)
    >>> compute_timeline(run["logs"])
    [(1.203, '5 + 7'), (2.891, '3 * 4')]
"""


RECORD_RUN_DOC = """
Insert a finished run into the database.

Args:
    conn: sqlite3 connection (typically state.conn).
    table: Table name, usually "runs".
    score: Number of correct answers in the round.
    logs: Dict mapping elapsed-seconds (str) -> problem expression (str),
          e.g. {"0.842": "6 + 3", "1.701": "4 * 7"}.

Returns:
    The integer id of the newly inserted row.

Example:
    >>> run_id = record_run(conn, "runs", 12, {"0.5": "2 + 2", "1.2": "3 * 3"})
    >>> run_id
    42
"""


GET_RECENT_RUNS_DOC = """
Fetch metadata for the most recent runs (no log payloads).

Args:
    conn: sqlite3 connection.
    limit: Maximum number of rows to return (default 10).

Returns:
    List of dicts with keys id, ts, score, newest first.

Example:
    >>> get_recent_runs(conn, limit=5)
    [{'id': 10, 'ts': '2026-07-21T12:00:00', 'score': 15}, ...]
"""


GET_ALL_RUN_METADATA_DOC = """
Fetch id/ts/score for every run, newest first.

Args:
    conn: sqlite3 connection.

Returns:
    List of dicts with keys id, ts, score (logs column omitted for speed).
"""


GET_RUN_DOC = """
Fetch a single run by id, including parsed logs.

Args:
    conn: sqlite3 connection.
    run_id: Primary key in the runs table.

Returns:
    Dict with keys id, ts, score, logs (logs is a dict after JSON parse),
    or None if no row matches.

Example:
    >>> run = get_run(conn, 3)
    >>> run["logs"]
    {'1.1': '5 + 7', '2.0': '8 - 3'}
"""


GET_ALL_RUNS_DOC = """
Fetch every run with full log payloads, oldest first.

Args:
    conn: sqlite3 connection.

Returns:
    List of dicts with keys id, ts, score, logs (each logs value is parsed JSON).
"""


REPL_BANNER = """
zetamac-tui debug REPL
=====================
Type help() for a quick reference of variables and functions in this session.
Type help(<name>) for docs on settings, record_run, AppState, etc.
Type exit() or Ctrl-D to return to the game.
"""


class ReplHelp:
    """Custom help() for the zetamac-tui debug REPL.

    Calling help() with no arguments prints a cheat sheet of what's
    available in this session (state, settings, conn, helper functions).
    Calling help(x) with an argument falls through to Python's normal
    built-in help(), so help(settings), help(record_run), help(str),
    etc. all still work exactly as they always have.
    """

    _OVERVIEW = """
zetamac-tui semi-internals (intentionally exposed functions for the user) -- quick reference
===================================

Variables available in this session:

  state       AppState instance for the running app.
              - state.settings         -> the Settings in use (see below)
              - state.conn              -> sqlite3.Connection to runs.db
              - state.db_path           -> Path to runs.db
              - state.config_path       -> Path to settings.json
              - state.save_settings()   -> persist state.settings to disk

  settings    Shortcut for state.settings (a Settings dataclass instance).
              - settings.game_duration        float, seconds per round
              - settings.operations           list of "+", "-", "*", "/"
              - settings.addition_bounds       [min_a, max_a, min_b, max_b]
              - settings.multiplication_bounds [min_a, max_a, min_b, max_b]
              - settings.cheat_mode, flash_digits, flash_duration, ...
              NOTE: edits here are in-memory only -- call
              state.save_settings() to write them to settings.json.

  conn        Shortcut for state.conn (sqlite3.Connection to runs.db).
              Helper functions that take `conn` as their first argument:
                record_run(conn, "runs", score, logs_dict)
                get_recent_runs(conn, limit=10)
                get_all_run_metadata(conn)
                get_run(conn, run_id)
                get_all_runs(conn)
              You can also run raw SQL:
                conn.execute("SELECT * FROM runs").fetchall()

  generate_problem(settings)  -> (expression_str, answer) new problem
  tt(a, b=[], settings=None)   configure an unlogged times-table run
  compute_timeline(logs)      -> sorted [(elapsed_seconds, expression), ...]

User helper functions (from userfuncs.py):
  runs_table(conn, limit=10)       tabular view of recent runs
  show_run(conn, run_id)           one run with per-question timeline
  analyze_run(conn, run_id)        timing stats for a run
  preview_problem(settings)        generate and print a sample problem
  paths(state)                     print config/db file locations
  sql(conn, query, params=())      run a SELECT and print rows
  sql_sh(conn)                     enter the sqlite3 shell
  save(state)                      shortcut for state.save_settings()

Type help(<name>) for full docs on any of the above, e.g.:
  help(settings)
  help(record_run)
  help(AppState)

Type exit() or press Ctrl-D to leave the REPL and return to the game.
"""

    def __call__(self, *args, **kwargs):
        if not args and not kwargs:
            print(self._OVERVIEW)
            return None
        # Anything else (help(obj), help("modules"), etc.) behaves
        # exactly like the real built-in help().
        return pydoc.help(*args, **kwargs)

    def __repr__(self) -> str:
        return "Type help() for zetamac-tui REPL help, or help(x) for help about x."


def apply_repl_docs(namespace: dict[str, Any]) -> None:
    """Attach heredoc documentation to REPL-visible objects in main."""
    bindings: list[tuple[str, str]] = [
        ("Settings", SETTINGS_DOC),
        ("AppState", APP_STATE_DOC),
        ("generate_problem", GENERATE_PROBLEM_DOC),
        ("tt", TT_DOC),
        ("compute_timeline", COMPUTE_TIMELINE_DOC),
        ("record_run", RECORD_RUN_DOC),
        ("get_recent_runs", GET_RECENT_RUNS_DOC),
        ("get_all_run_metadata", GET_ALL_RUN_METADATA_DOC),
        ("get_run", GET_RUN_DOC),
        ("get_all_runs", GET_ALL_RUNS_DOC),
    ]
    for name, doc in bindings:
        obj = namespace.get(name)
        if obj is not None:
            obj.__doc__ = doc.strip()

    app_state = namespace.get("AppState")
    if app_state is not None:
        app_state.save_settings.__doc__ = APP_STATE_SAVE_SETTINGS_DOC.strip()
        app_state.load_settings.__doc__ = APP_STATE_LOAD_SETTINGS_DOC.strip()
        app_state.open_db.__doc__ = APP_STATE_OPEN_DB_DOC.strip()

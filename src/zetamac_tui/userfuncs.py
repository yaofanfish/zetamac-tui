"""User-facing REPL helper functions for zetamac-tui.

These are loaded into the debug REPL session only; the app backend does not
import or call them. They wrap common inspection and experimentation tasks.
"""

from __future__ import annotations

import os
import json
import sqlite3
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def runs_table(conn: sqlite3.Connection, limit: int = 10) -> list[dict[str, Any]]:
    """Print a table of recent runs and return the underlying rows."""
    from zetamac_tui.main import get_recent_runs

    rows = get_recent_runs(conn, limit=limit)
    table = Table(title=f"Recent runs (limit={limit})")
    table.add_column("id", justify="right")
    table.add_column("score", justify="right")
    table.add_column("timestamp")
    if not rows:
        table.add_row("-", "-", "(no runs yet)")
    else:
        for row in rows:
            table.add_row(str(row["id"]), str(row["score"]), str(row["ts"]))
    console.print(table)
    return rows


def show_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    """Print one run's metadata and per-question timeline."""
    from zetamac_tui.main import compute_timeline, get_run

    run = get_run(conn, run_id)
    if run is None:
        console.print(f"[red]No run with id={run_id}[/red]")
        return None

    console.print(f"[bold]Run {run['id']}[/bold]  score={run['score']}  ts={run['ts']}")
    logs = run.get("logs") or {}
    timeline = compute_timeline(logs)
    if not timeline:
        console.print("(empty logs)")
        return run

    table = Table(title="Timeline")
    table.add_column("#", justify="right")
    table.add_column("elapsed (s)", justify="right")
    table.add_column("expression")
    for index, (elapsed, expression) in enumerate(timeline, start=1):
        table.add_row(str(index), f"{elapsed:.3f}", expression)
    console.print(table)
    return run


def analyze_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    """Print timing analytics (fastest/slowest questions) for a run."""
    from zetamac_tui.main import _analytics, get_run

    run = get_run(conn, run_id)
    if run is None:
        console.print(f"[red]No run with id={run_id}[/red]")
        return None

    logs = run.get("logs") or {}
    result = _analytics(json.dumps(logs), id=run_id)
    console.print_json(data=result["summary"])
    return result


def preview_problem(settings: Any, count: int = 1) -> list[tuple[str, int]]:
    """Generate and print sample problem(s) using the current settings."""
    from zetamac_tui.main import generate_problem

    problems: list[tuple[str, int]] = []
    for _ in range(max(1, count)):
        expr, answer = generate_problem(settings)
        problems.append((expr, answer))
        console.print(f"{expr}  =>  [green]{answer}[/green]")
    return problems


def paths(state: Any) -> dict[str, Path]:
    """Print and return config/db paths for the current AppState."""
    locations = {
        "config_path": state.config_path,
        "db_path": state.db_path,
        "config_dir": state.config_dir,
    }
    for label, path in locations.items():
        console.print(f"{label}: {path}")
    return locations


def sql(
    conn: sqlite3.Connection,
    query: str,
    params: tuple[Any, ...] | list[Any] = (),
) -> list[Any]:
    """Run a read query and print rows (use for SELECT-style inspection)."""
    rows = conn.execute(query, params).fetchall()
    if not rows:
        console.print("(no rows)")
        return []
    for row in rows:
        if hasattr(row, "keys"):
            console.print(dict(row))
        else:
            console.print(row)
    return list(rows)


def save(state: Any, force: bool = False) -> None:
    """Persist settings to disk (shortcut for state.save_settings())."""
    state.save_settings(force=force)
    console.print(f"Saved settings to {state.config_path}")

"""Teacher mode analytics dashboard.

When launched with --mode teacher, queries the SQLite trace store
and renders a Rich terminal report, then exits. No REPL.
"""

from pathlib import Path


def run_teacher_mode(args):
    from .trace_db import StudentTraceStore

    workspace = Path(args.cwd).resolve()
    db_path = workspace / ".educoder" / "traces.db"
    if not db_path.exists():
        print("No student trace data found. Run in student mode first.")
        raise SystemExit(0)
    store = StudentTraceStore(db_path)
    metrics = store.query_metrics()
    _render_report(metrics)


def _render_report(metrics):
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
    except ImportError:
        _render_plain(metrics)
        return

    console.print()
    console.print(Panel("[bold]EduCoder Teacher Dashboard[/bold]", expand=False))
    console.print()

    summary_table = Table(title="Session Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    summary_table.add_row("Total interactions", str(metrics["total_traces"]))
    summary_table.add_row("Total sessions", str(metrics["total_sessions"]))
    summary_table.add_row("Avg queries/session", f"{metrics['avg_queries_per_session']:.1f}")
    console.print(summary_table)
    console.print()

    if metrics["top_errors"]:
        error_table = Table(title="Recent Errors", show_header=True)
        error_table.add_column("#", style="dim")
        error_table.add_column("Error", style="red")
        for i, err in enumerate(metrics["top_errors"][:5], 1):
            error_table.add_row(str(i), err[:120])
        console.print(error_table)
        console.print()

    if metrics["recent_traces"]:
        trace_table = Table(title="Recent Interactions", show_header=True)
        trace_table.add_column("ID", style="dim")
        trace_table.add_column("Session", style="cyan")
        trace_table.add_column("Query", style="white")
        for t in metrics["recent_traces"][:5]:
            trace_table.add_row(str(t["id"]), t["session_id"][:12], t["query"][:60])
        console.print(trace_table)
        console.print()

    if metrics["top_errors"]:
        console.print(Panel("[bold]Teaching Suggestions[/bold]\n" + "\n".join("- Review common error patterns with students" for _ in range(1)), expand=False))
    else:
        console.print(Panel("[bold]Teaching Suggestions[/bold]\n- No errors recorded yet — students may need more challenging tasks", expand=False))
    console.print()


def _render_plain(metrics):
    print("\n=== EduCoder Teacher Dashboard ===\n")
    print(f"Total interactions: {metrics['total_traces']}")
    print(f"Total sessions:     {metrics['total_sessions']}")
    print(f"Avg queries/session: {metrics['avg_queries_per_session']:.1f}")
    if metrics["top_errors"]:
        print("\nRecent Errors:")
        for i, err in enumerate(metrics["top_errors"][:5], 1):
            print(f"  {i}. {err[:120]}")
    print()

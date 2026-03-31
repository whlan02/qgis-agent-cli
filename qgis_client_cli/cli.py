from __future__ import annotations

import os
from typing import Any, Dict, Optional

import click

from .application import CommandRunner, print_envelope


def _execute_action(
    *,
    ctx: click.Context,
    action: str,
    payload: Optional[Dict[str, Any]] = None,
    preflight_error: Optional[str] = None,
) -> None:
    runner = CommandRunner(
        ws_url=ctx.obj["ws_url"],
        timeout_ms=ctx.obj["timeout_ms"],
    )
    envelope = runner.execute(action=action, payload=payload, preflight_error=preflight_error)
    print_envelope(envelope)
    if envelope.get("status") != "ok":
        ctx.exit(1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, help="QGIS Agent CLI client (Control QGIS via WebSocket).")
@click.option(
    "--ws-url",
    default="ws://127.0.0.1:8765",
    show_default=True,
    help="WebSocket service address inside QGIS plugin.",
)
@click.option(
    "--timeout",
    default=5000,
    show_default=True,
    type=int,
    help="WebSocket connect/send/receive timeout (milliseconds).",
)
@click.option(
    "--json",
    "json_flag",
    is_flag=True,
    default=False,
    help="(Placeholder) Reserved for future support of colored output like HARNESS/REPL.",
)
@click.pass_context
def main(ctx: click.Context, ws_url: str, timeout: int, json_flag: bool) -> None:
    # Current stage: always output Envelope JSON to stdout.
    # json_flag is intentionally unused.
    ctx.ensure_object(dict)
    ctx.obj["ws_url"] = ws_url
    ctx.obj["timeout_ms"] = timeout


@main.command(help="Test if WebSocket connection is alive (send ping to QGIS).")
@click.pass_context
def status(ctx: click.Context) -> None:
    _execute_action(ctx=ctx, action="ping")


@main.group(help="Vector layer related operations.")
def vector() -> None:
    pass


@vector.command(name="load", help="Load a vector layer (by absolute path).")
@click.option("--path", "path_", required=True, type=str, help="Absolute path of vector data file.")
@click.pass_context
def vector_load(ctx: click.Context, path_: str) -> None:
    # Ensure request contains an absolute path (server assumes it).
    abs_path = os.path.abspath(path_)
    preflight_error: Optional[str] = None
    if not os.path.exists(abs_path):
        preflight_error = f"Vector path does not exist: {abs_path}"

    _execute_action(
        ctx=ctx,
        action="add_vector_layer",
        payload={"path": abs_path},
        preflight_error=preflight_error,
    )


@vector.command(name="buffer", help="Run buffer analysis on a specific layer and load result as a new vector layer.")
@click.option("--layer-name", required=True, type=str, help="Target layer name (as shown in QGIS layer panel).")
@click.option("--dist", required=True, type=float, help="Buffer distance (float).")
@click.pass_context
def vector_buffer(ctx: click.Context, layer_name: str, dist: float) -> None:
    _execute_action(
        ctx=ctx,
        action="buffer_layer",
        payload={"layer_name": layer_name, "distance": float(dist)},
    )


@main.group(help="Project and map export related operations.")
def project() -> None:
    pass


@project.command(name="export", help="Export current QGIS canvas as image file.")
@click.option("--out-path", required=True, type=str, help="Absolute output path for exported image (e.g. C:\\\\out\\\\map.png).")
@click.pass_context
def project_export(ctx: click.Context, out_path: str) -> None:
    abs_path = os.path.abspath(out_path)
    _execute_action(
        ctx=ctx,
        action="export_map",
        payload={"output_path": abs_path},
    )


@project.command(name="layers", help="List current layers loaded in QGIS.")
@click.pass_context
def project_layers(ctx: click.Context) -> None:
    _execute_action(ctx=ctx, action="get_layers")


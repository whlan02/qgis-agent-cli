from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional

import click

from .protocol import make_envelope, make_request
from .ws_client import call_ws_json


def _print_envelope(envelope: Dict[str, Any]) -> None:
    # ensure_ascii=False keeps non-ascii paths readable for humans/logs.
    click.echo(json.dumps(envelope, ensure_ascii=False))


def _run_ws_call(*, ws_url: str, timeout_ms: int, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous wrapper around async WebSocket call.
    """
    # Each CLI invocation is one-shot; using asyncio.run keeps it simple.
    return asyncio.run(call_ws_json(ws_url=ws_url, request=request, timeout_ms=timeout_ms))


def _emit_ok_or_error(
    *,
    ctx: click.Context,
    action: str,
    request: Dict[str, Any],
    response: Optional[Dict[str, Any]],
    elapsed_ms: int,
    error_message: Optional[str] = None,
) -> None:
    envelope = make_envelope(
        action=action,
        request=request,
        response=response,
        elapsed_ms=elapsed_ms,
        status="error" if error_message else None,
        message=error_message,
    )
    _print_envelope(envelope)

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
    ws_url = ctx.obj["ws_url"]
    timeout_ms = ctx.obj["timeout_ms"]

    action = "ping"
    request = make_request(action)

    start = time.perf_counter()
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    try:
        response = _run_ws_call(ws_url=ws_url, timeout_ms=timeout_ms, request=request)
    except Exception as e:
        error_message = f"WebSocket call failed: {e}"
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    _emit_ok_or_error(
        ctx=ctx,
        action=action,
        request=request,
        response=response,
        elapsed_ms=elapsed_ms,
        error_message=error_message,
    )


@main.group(help="Vector layer related operations.")
def vector() -> None:
    pass


@vector.command(name="load", help="Load a vector layer (by absolute path).")
@click.option("--path", "path_", required=True, type=str, help="Absolute path of vector data file.")
@click.pass_context
def vector_load(ctx: click.Context, path_: str) -> None:
    ws_url = ctx.obj["ws_url"]
    timeout_ms = ctx.obj["timeout_ms"]

    # Ensure request contains an absolute path (server assumes it).
    abs_path = os.path.abspath(path_)
    action = "add_vector_layer"
    request = make_request(action, path=abs_path)

    if not os.path.isabs(path_):
        # Still convert to absolute, but tell agents about normalization.
        # (We keep it in message for future diagnostics.)
        pass

    if not os.path.exists(abs_path):
        start = time.perf_counter()
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        _emit_ok_or_error(
            ctx=ctx,
            action=action,
            request=request,
            response=None,
            elapsed_ms=elapsed_ms,
            error_message=f"Vector path does not exist: {abs_path}",
        )
        return

    start = time.perf_counter()
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    try:
        response = _run_ws_call(ws_url=ws_url, timeout_ms=timeout_ms, request=request)
    except Exception as e:
        error_message = f"WebSocket call failed: {e}"
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    _emit_ok_or_error(
        ctx=ctx,
        action=action,
        request=request,
        response=response,
        elapsed_ms=elapsed_ms,
        error_message=error_message,
    )


@vector.command(name="buffer", help="Run buffer analysis on a specific layer and load result as a new vector layer.")
@click.option("--layer-name", required=True, type=str, help="Target layer name (as shown in QGIS layer panel).")
@click.option("--dist", required=True, type=float, help="Buffer distance (float).")
@click.pass_context
def vector_buffer(ctx: click.Context, layer_name: str, dist: float) -> None:
    ws_url = ctx.obj["ws_url"]
    timeout_ms = ctx.obj["timeout_ms"]

    action = "buffer_layer"
    request = make_request(action, layer_name=layer_name, distance=float(dist))

    start = time.perf_counter()
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    try:
        response = _run_ws_call(ws_url=ws_url, timeout_ms=timeout_ms, request=request)
    except Exception as e:
        error_message = f"WebSocket call failed: {e}"
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    _emit_ok_or_error(
        ctx=ctx,
        action=action,
        request=request,
        response=response,
        elapsed_ms=elapsed_ms,
        error_message=error_message,
    )


@main.group(help="Project and map export related operations.")
def project() -> None:
    pass


@project.command(name="export", help="Export current QGIS canvas as image file.")
@click.option("--out-path", required=True, type=str, help="Absolute output path for exported image (e.g. C:\\\\out\\\\map.png).")
@click.pass_context
def project_export(ctx: click.Context, out_path: str) -> None:
    ws_url = ctx.obj["ws_url"]
    timeout_ms = ctx.obj["timeout_ms"]

    abs_path = os.path.abspath(out_path)
    action = "export_map"
    request = make_request(action, output_path=abs_path)

    start = time.perf_counter()
    response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    try:
        response = _run_ws_call(ws_url=ws_url, timeout_ms=timeout_ms, request=request)
    except Exception as e:
        error_message = f"WebSocket call failed: {e}"
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    _emit_ok_or_error(
        ctx=ctx,
        action=action,
        request=request,
        response=response,
        elapsed_ms=elapsed_ms,
        error_message=error_message,
    )


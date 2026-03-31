# qgis-agent-cli

`qgis-agent-cli` is a local GIS automation toolkit, composed of two parts:

- `qgis_server_plugin`: A plugin that runs inside QGIS Desktop and starts a local WebSocket service.
- `qgis_client_cli`: A Python CLI running in the terminal, remotely invoking QGIS capabilities via WebSocket.

The goal is to enable scripts or agents to reliably drive QGIS on the local machine via standard command-line tools to perform common operations.

## Table of Contents

- [Project Architecture](#project-architecture)
- [Existing Features](#existing-features)
- [Environment Requirements](#environment-requirements)
- [Creating a Python Virtual Environment](#creating-a-python-virtual-environment)
- [Dependency Installation Guide](#dependency-installation-guide)
- [QGIS Plugin Installation Guide](#qgis-plugin-installation-guide)
- [Getting Started](#getting-started)
- [FAQ](#faq)
- [Future Plans (from TODO)](#future-plans-from-todo)
- [Minimal Developer Guide](#minimal-developer-guide)

## Project Architecture

The system adopts a **Client / Server (on the same machine)** architecture:

1. The user or automation workflow executes a CLI command (e.g. `python -m qgis_client_cli status`).
2. The CLI packages the request into JSON (`action + parameters`) and sends it via `ws://127.0.0.1:8765` to the QGIS plugin.
3. The QGIS plugin receives the request and routes it to the actual implementation (e.g. loading layers, buffer analysis, exporting maps).
4. The plugin returns a JSON response, and the CLI outputs a unified Envelope JSON result (including `status/message/action/elapsed_ms`).

Core modules:

- `qgis_client_cli/cli.py`: Command definitions and argument parsing (Click).
- `qgis_client_cli/application/command_runner.py`: Action execution flow (request -> WS -> envelope).
- `qgis_client_cli/ws_client.py`: WebSocket transport client.
- `qgis_client_cli/protocol.py`: Envelope and request structure helpers.
- `qgis_server_plugin/qgis_server_plugin.py`: Plugin lifecycle, WS service, and dependency wiring.
- `qgis_server_plugin/ws_protocol.py`: Request parsing + validation + dispatch entry.
- `qgis_server_plugin/application/actions/*`: Action-level orchestration (one feature per file).
- `qgis_server_plugin/infrastructure/qgis/*`: Concrete QGIS implementation details.

## Existing Features

The following features are currently implemented:

- **Connection status check**: `status` (`ping`)
- **Vector layer loading**: `vector load --path <absolute path>`
- **Buffer analysis**: `vector buffer --layer-name <layer name> --dist <distance>`
- **Map export**: `project export --out-path <absolute output path>`

CLI output is standardized to JSON for easy parsing by scripts and automation tools.

## Environment Requirements

- Python 3.9+ (recommended)
- QGIS 3.x (plugin `qgisMinimumVersion=3.0`)
- Operating system: Windows / Linux / macOS (as long as local QGIS and Python are available)

## Creating a Python Virtual Environment

In the project root directory, run:

```bash
python -m venv .venv
```

Activate the virtual environment:

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows CMD

```bat
.venv\Scripts\activate.bat
```

### Linux / macOS

```bash
source .venv/bin/activate
```

## Dependency Installation Guide

After activating the virtual environment, run:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Core dependencies:

- `click>=8.0.0`
- `websockets>=12.0`

## QGIS Plugin Installation Guide

The repository contains the plugin directory: `qgis_server_plugin/`.

### Method 1: Directly Copy to QGIS Plugin Directory (Recommended for Development and Debugging)

1. Find the QGIS user plugin directory:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Copy the entire `qgis_server_plugin` directory from the repository into this `plugins` directory.
3. Restart QGIS, go to `Plugins -> Manage and Install Plugins`, and enable **QGIS Agent WebSocket Server**.
4. Once enabled, the plugin will listen on `ws://127.0.0.1:8765`.

### Method 2: Symbolic Link (Suitable for Local Development)

Create a symlink from `qgis_server_plugin` to the QGIS plugin directory for instant code updates to take effect (usually you still need to reload/restart the plugin in QGIS).

## Getting Started

Be sure that:

- QGIS is running;
- The plugin is enabled;
- The Python virtual environment is activated and dependencies are installed.

Then, in the project root directory, run:

```bash
python -m qgis_client_cli --help
python -m qgis_client_cli status
```

Example commands:

```bash
python -m qgis_client_cli vector load --path "D:\data\roads.shp"
python -m qgis_client_cli vector buffer --layer-name "roads" --dist 100
python -m qgis_client_cli project export --out-path "D:\output\map.png"
```

## FAQ

- **Connection failed in status**
  - Check if QGIS is running and the plugin is enabled.
  - Check if port `8765` is occupied by another process.
- **Failed to load layer**
  - The input path must be accessible by the local machine; it's recommended to use absolute paths.
- **Export failed**
  - Make sure the output directory is writable; create the directory manually if needed.

## Future Plans (from TODO)

- Command-level undo/redo fault tolerance mechanism (based on `QgsUndoNode`).

## Minimal Developer Guide

How to add a new feature (action), and how to validate it.

### 1) Add a feature (4 steps)

1. Create a new action file in the correct domain folder:  
   `qgis_server_plugin/application/actions/<domain>/xxx_action.py`
2. Add only these two required parts:  
   - `ACTION_NAME = "xxx"`  
   - `def handle(request, context, sock): ...`
3. Add request validation for the new action in `qgis_server_plugin/ws_protocol.py` (`_validate_request`).
4. Add a CLI command in `qgis_client_cli/cli.py`, then call `_execute_action(action="xxx", payload=...)`.

Note: actions are auto-discovered. You do not need to edit the dispatcher manually.

### 2) Validate the feature (1 command + 1 manual check)

#### Automated check (required)

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Pass condition: output contains `OK`.

#### Manual check (required)

1. Open QGIS (plugin loaded).
2. Run your new CLI command.
3. Check the CLI envelope output:  
   - `status` must be `ok`  
   - `action` must match your `ACTION_NAME`  
   - business output fields must exist (for example `layerId` / `output_path`)

If both automated and manual checks pass, the feature is valid.

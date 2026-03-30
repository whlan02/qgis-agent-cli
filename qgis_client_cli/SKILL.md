---
name: "qgis-remote-cli"
description: "Command-line interface for remotely controlling QGIS via WebSocket"
---

# QGIS Remote CLI Skill

This is a specialized tool for remotely controlling the local QGIS desktop application.
**Environment requirement:** You must be in the root directory of `qgis-agent-cli` and have the `.venv` virtual environment activated before use.

## Core Rule: Dynamic Discovery Mechanism (Layered Loading)
**This tool's commands are multilayered. Never hallucinate or guess commands and parameters!**
When you receive a user's GIS request, strictly follow this exploration path in the terminal:

1. **Step 1 (Main Menu):** Run `python -m qgis_client_cli --help` to view the available top-level command groups (e.g., vector, project).
2. **Step 2 (Submenu):** Once you have determined the business domain, run commands like `python -m qgis_client_cli vector --help` or `python -m qgis_client_cli project --help` to see specific features.
3. **Step 3 (Command Arguments):** After finding the target command, always run the command with `--help` (for example, `... vector buffer --help`) to get the required parameters.
4. **Step 4 (Execute Operation):** Assemble the full command and run it in the terminal. Read the returned Envelope JSON to confirm success.

## General Conventions
- When dealing with local files, you must provide absolute paths to QGIS.
- You may execute shell commands directly in the current terminal to complete the user's tasks.
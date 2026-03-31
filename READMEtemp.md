# qgis-agent-cli

Minimal developer guide: how to add a new feature (action), and how to validate it.

## 1) Add a feature (3 steps)

1. Create a new action file in the correct domain folder:  
   `qgis_server_plugin/application/actions/<domain>/xxx_action.py`
2. Add only these two required parts:  
   - `ACTION_NAME = "xxx"`  
   - `def handle(request, context, sock): ...`
3. Add a CLI command in `qgis_client_cli/cli.py`, then call `_execute_action(action="xxx", payload=...)`.

Note: actions are auto-discovered. You do not need to edit the dispatcher manually.

## 2) Validate the feature (1 command + 1 manual check)

### Automated check (required)

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Pass condition: output contains `OK`.

### Manual check (required)

1. Open QGIS (plugin loaded).
2. Run your new CLI command.
3. Check the CLI envelope output:  
   - `status` must be `ok`  
   - `action` must match your `ACTION_NAME`  
   - business output fields must exist (for example `layerId` / `output_path`)

If both automated and manual checks pass, the feature is valid.


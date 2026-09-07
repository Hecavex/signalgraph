"""Keep bounded service status, never raw logs, container env or auth traces."""

import json
import subprocess
from pathlib import Path


def public_status(value):
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise TypeError("Unexpected Compose status response")
    return [
        {key: str(item.get(key, ""))[:100] for key in ("Service", "State", "Health", "ExitCode")}
        for item in value[:6]
    ]


def main():
    result = subprocess.run(
        ["docker", "compose", "ps", "--all", "--format", "json"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    try:
        output = result.stdout[:100_000]
        try:
            value = json.loads(output)
        except json.JSONDecodeError:
            value = [json.loads(line) for line in output.splitlines() if line.strip()]
        report = {"synthetic": True, "services": public_status(value)}
    except (ValueError, TypeError):
        report = {"synthetic": True, "status": "Status collection unavailable", "exitCode": result.returncode}
    Path("ci-health.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

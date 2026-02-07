"""Linting script for the AI Assistant application."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        print(f"✓ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed")
        print(e.stdout)
        if e.stderr:
            print(e.stderr)
        return False
    except FileNotFoundError:
        print("✗ Command not found. Please install dev dependencies:")
        print('  pip install -e ".[dev]"')
        return False


def main() -> int:
    """Run all linting checks."""
    project_root = Path(__file__).parent
    app_dir = project_root / "app"

    print("AI Assistant - Code Quality Checks")
    print("=" * 60)

    results = []

    # Run ruff format check
    results.append(run_command(["ruff", "format", str(app_dir)], "Ruff Format"))

    # Run ruff linter
    results.append(run_command(["ruff", "check", "--fix", str(app_dir)], "Ruff Linter"))

    # Run mypy
    results.append(run_command(["mypy", str(app_dir)], "MyPy Type Checker"))

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary")
    print(f"{'=' * 60}")

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✓ All checks passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

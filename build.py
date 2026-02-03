"""Build script for creating standalone executable with Nuitka."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Build standalone executable."""
    project_root = Path(__file__).parent

    print("=" * 60)
    print("Building AI Assistant executable with Nuitka")
    print("=" * 60)

    # Nuitka command
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--enable-plugin=tk-inter",
        "--windows-disable-console",  # No console window on Windows
        "--output-dir=dist",
        (
            "--output-filename=AIAssistant.exe"
            if sys.platform == "win32"
            else "--output-filename=AIAssistant"
        ),
        "--company-name=AI Assistant",
        "--product-name=AI Assistant",
        "--file-version=0.1.0",
        "--product-version=0.1.0",
        "--file-description=OpenAI-powered desktop assistant",
        "--copyright=Copyright (c) 2026",
        "--include-data-dir=app=app",
        "-m",
        "app",
    ]

    print("\nRunning command:")
    print(" ".join(cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
        print("\n" + "=" * 60)
        print("✓ Build completed successfully!")
        print("=" * 60)
        print(f"\nExecutable location: {project_root / 'dist'}")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("✗ Build failed!")
        print("=" * 60)
        print(f"\nError: {e}")
        return 1
    except FileNotFoundError:
        print("\n" + "=" * 60)
        print("✗ Nuitka not found!")
        print("=" * 60)
        print("\nPlease install Nuitka:")
        print("  pip install nuitka")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""Single build entry point for local development and CI."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def build_command(mode, output_dir, work_dir):
    return [
        sys.executable, "-m", "PyInstaller", "--noconfirm",
        "--distpath", str(output_dir), "--workpath", str(work_dir),
        str(ROOT / "packaging/IP-Suite-Tool.spec"),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("release", "development"), default="release")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "bin")
    parser.add_argument("--work-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--dry-run", action="store_true", help="Check inputs and display the build command")
    args = parser.parse_args()
    checker = ROOT / "scripts/check_public_content.py"
    subprocess.run([sys.executable, str(checker)], cwd=ROOT, check=True)
    command = build_command(args.mode, args.output_dir.resolve(), args.work_dir.resolve())
    if args.dry_run:
        print(f"Mode: {args.mode}")
        print(subprocess.list2cmdline(command))
        return
    if importlib.util.find_spec("PyInstaller") is None:
        parser.error("Install build dependencies: python -m pip install -r requirements-dev.txt")
    environment = os.environ.copy()
    environment["IP_SUITE_BUILD_MODE"] = args.mode
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    name = "IP-Suite-Tool" + ("-dev" if args.mode == "development" else "")
    executable = args.output_dir.resolve() / (name + (".exe" if sys.platform == "win32" else ""))
    if args.mode == "development":
        executable = args.output_dir.resolve() / name / executable.name
    if not executable.is_file():
        raise FileNotFoundError("Build finished without the expected executable")
    if args.mode == "release":
        subprocess.run([sys.executable, str(checker), "--binary", str(executable)], cwd=ROOT, check=True)
    print(f"Built: {executable}")


if __name__ == "__main__":
    main()

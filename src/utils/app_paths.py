"""Keep private runtime state outside the source tree and packaged resources."""
import os
import sys
from pathlib import Path


def data_directory() -> Path:
    override = os.environ.get("IP_SUITE_DATA_DIR")
    if override:
        directory = Path(override).expanduser().resolve()
    elif sys.platform == "win32":
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "IP-Suite-Tool"
    elif sys.platform == "darwin":
        directory = Path.home() / "Library/Application Support/IP-Suite-Tool"
    else:
        directory = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "IP-Suite-Tool"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def config_path(name: str) -> Path:
    if Path(name).name != name:
        raise ValueError("Configuration name must be a file name")
    directory = data_directory() / "cfgs"
    directory.mkdir(exist_ok=True)
    return directory / name


def resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base.joinpath(*parts)


def configure_frozen_tk_paths() -> None:
    """Keep Windows Tcl/Tk from renormalizing the bundled library paths."""
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return
    for variable, folder in (("TCL_LIBRARY", "_tcl_data"), ("TK_LIBRARY", "_tk_data")):
        directory = resource_path(folder)
        if not directory.is_dir():
            continue
        value = str(directory)
        if not value.startswith("\\\\?\\"):
            value = "\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value
        os.environ[variable] = value

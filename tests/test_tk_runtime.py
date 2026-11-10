import os
import sys

import pytest

from utils.app_paths import configure_frozen_tk_paths


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Tcl/Tk path handling")
def test_frozen_tk_uses_its_bundled_libraries(tmp_path, monkeypatch):
    for folder in ("_tcl_data", "_tk_data"):
        (tmp_path / folder).mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    for variable in ("TCL_LIBRARY", "TK_LIBRARY"):
        monkeypatch.setenv(variable, "stale-library")

    configure_frozen_tk_paths()

    for variable, folder in (("TCL_LIBRARY", "_tcl_data"), ("TK_LIBRARY", "_tk_data")):
        expected = str(tmp_path / folder).replace("/", "\\")
        assert os.environ[variable] == "\\\\?\\" + expected


def test_source_run_preserves_the_selected_tk_libraries(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setenv("TCL_LIBRARY", "selected-tcl")
    monkeypatch.setenv("TK_LIBRARY", "selected-tk")
    configure_frozen_tk_paths()
    assert os.environ["TCL_LIBRARY"] == "selected-tcl"
    assert os.environ["TK_LIBRARY"] == "selected-tk"

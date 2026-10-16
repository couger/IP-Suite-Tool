from pathlib import Path
import subprocess
import sys

from ip_work_stats import WorkStats
from tests.helpers import monthly_stats_bulk_fixture

ROOT = Path(__file__).resolve().parents[1]


def test_monthly_fixture_generator_survives_directory_move(tmp_path, monkeypatch):
    batch = tmp_path / "synthetic-batch"
    monkeypatch.setattr(monthly_stats_bulk_fixture, "BATCH", batch)
    monthly_stats_bulk_fixture.main()
    generated = list(batch.glob("*.xlsx"))
    assert len(generated) == 48
    stats = object.__new__(WorkStats)
    for index, path in enumerate(generated, 1):
        record = stats._read_record(index, str(path))
        assert record.status == "成功"
        assert record.applicant_unit.startswith("示例单位")
        assert record.applicant.startswith("示例人员")


def test_build_entrypoint_works_from_an_unrelated_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build.py"), "--dry-run"],
        cwd=tmp_path, capture_output=True, text=True, check=True,
    )
    assert "Public content check: passed" in result.stdout
    assert "packaging" in result.stdout
    assert "IP-Suite-Tool.spec" in result.stdout

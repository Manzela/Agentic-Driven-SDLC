# tests/spine/test_baseline_writer.py
import importlib.util, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
def _load():
    s = importlib.util.spec_from_file_location("bw", ROOT / "tools/baseline_writer.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def test_write_baseline_roundtrip(tmp_path):
    bw = _load(); out = tmp_path / "coverage_baseline.json"
    bw.write_baseline(required_in_scope=["A", "B"], out_path=out)
    assert json.loads(out.read_text())["required_in_scope"] == ["A", "B"]

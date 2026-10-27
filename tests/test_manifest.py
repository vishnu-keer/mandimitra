"""The run manifest describes the files that are actually in the repository.

If any of these fail, the published numbers and the manifest have drifted
apart: re-run the pipeline if needed, then `python scripts/make_manifest.py`.
"""
import ast
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

from src import config

MANIFEST = config.OUTPUTS / "run_manifest.json"
ROOT = config.PROJECT_ROOT

sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.skipif(not MANIFEST.exists(),
                                reason="no run manifest generated yet")


def _m():
    return json.loads(MANIFEST.read_text())


def _sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def test_every_input_hash_matches_the_file_on_disk():
    m = _m()
    assert m["inputs"], "manifest lists no inputs"
    stale = [p for p, v in m["inputs"].items() if _sha(p) != v["sha256"]]
    assert not stale, f"inputs changed since the manifest was written: {stale}"


def test_every_output_hash_matches_the_file_on_disk():
    m = _m()
    for f in ["best_model.csv", "model_comparison.csv", "predictions.csv",
              "forecast.csv"]:
        assert f"outputs/{f}" in m["outputs"], f"{f} not in manifest"
    stale = [p for p, v in m["outputs"].items() if _sha(p) != v["sha256"]]
    assert not stale, f"outputs changed since the manifest was written: {stale}"


def test_manifest_code_hash_matches_the_current_source():
    from make_manifest import code_hash
    assert code_hash() == _m()["code_sha256"], (
        "app.py / src / scripts changed after the manifest was generated; "
        "re-run scripts/make_manifest.py")


def test_manifest_says_the_data_is_historical_and_matches_the_results():
    m = _m()
    assert m["status"].startswith("HISTORICAL")
    best = pd.read_csv(config.OUTPUTS / "best_model.csv")
    got = [(r["commodity"], r["horizon"], r["best_model"]) for r in m["selected"]]
    want = list(zip(best["commodity"], best["horizon"], best["best_model"]))
    assert got == want


def test_dashboard_never_imports_training_code():
    """The app reads results; it must not be able to fit a model on page load."""
    banned = {"src.models", "src.evaluate", "src.forecast", "sklearn",
              "statsmodels", "src.intervals"}
    for f in ["app.py", "src/dashboard_data.py"]:
        tree = ast.parse((ROOT / f).read_text())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                base = ("src." if node.level else "") + (node.module or "")
                mods.add(base)
                mods |= {f"{base}.{a.name}".replace("src..", "src.")
                         for a in node.names}
        hit = {m for m in mods for b in banned if m == b or m.startswith(b + ".")}
        assert not hit, f"{f} imports training code: {hit}"


def test_dashboard_data_layer_does_not_pull_in_model_libraries_transitively():
    import subprocess
    code = ("import sys; sys.path.insert(0, %r); import src.dashboard_data; "
            "print(sorted({m.split('.')[0] for m in sys.modules} & "
            "{'sklearn', 'statsmodels'}))" % str(ROOT))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, check=True).stdout.strip()
    assert out == "[]", f"loading the dashboard data layer imported {out}"

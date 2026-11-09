import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_app_builds():
    import app

    assert app.build() is not None

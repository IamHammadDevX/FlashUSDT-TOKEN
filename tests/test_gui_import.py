import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "flashDemotoken_generator"))


def test_gui_class_imports_without_launching_window():
    from ui.gui import USDGeneratorApp

    assert USDGeneratorApp.__name__ == "USDGeneratorApp"

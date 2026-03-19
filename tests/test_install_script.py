import os
import subprocess
from pathlib import Path


def test_install_script_creates_working_launcher(tmp_path):
    root = Path(__file__).resolve().parents[1]
    install_script = root / "scripts" / "install.sh"
    install_dir = tmp_path / "bin"

    result = subprocess.run(
        ["bash", str(install_script)],
        cwd=root,
        env={
            **os.environ,
            "CODEX_TTS_INSTALL_DIR": str(install_dir),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    launcher = install_dir / "codex-tts"
    assert launcher.exists()
    assert os.access(launcher, os.X_OK)
    assert str(root) in launcher.read_text(encoding="utf-8")

    help_result = subprocess.run(
        [str(launcher), "--help"],
        cwd=root,
        capture_output=True,
        text=True,
    )

    assert help_result.returncode == 0, help_result.stderr
    assert "--preset" in help_result.stdout

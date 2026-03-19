import os
import subprocess
from pathlib import Path


def copy_script(root: Path, destination_root: Path, script_name: str) -> Path:
    source = root / "scripts" / script_name
    target = destination_root / "scripts" / script_name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    target.chmod(0o755)
    return target


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


def test_uninstall_script_removes_launcher(tmp_path):
    root = Path(__file__).resolve().parents[1]
    install_script = root / "scripts" / "install.sh"
    uninstall_script = root / "scripts" / "uninstall.sh"
    install_dir = tmp_path / "bin"
    env = {
        **os.environ,
        "CODEX_TTS_INSTALL_DIR": str(install_dir),
    }

    install_result = subprocess.run(
        ["bash", str(install_script)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert install_result.returncode == 0, install_result.stderr
    assert (install_dir / "codex-tts").exists()

    uninstall_result = subprocess.run(
        ["bash", str(uninstall_script)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert uninstall_result.returncode == 0, uninstall_result.stderr
    assert not (install_dir / "codex-tts").exists()


def test_uninstall_script_is_idempotent_when_launcher_missing(tmp_path):
    root = Path(__file__).resolve().parents[1]
    uninstall_script = root / "scripts" / "uninstall.sh"
    install_dir = tmp_path / "bin"

    result = subprocess.run(
        ["bash", str(uninstall_script)],
        cwd=root,
        env={
            **os.environ,
            "CODEX_TTS_INSTALL_DIR": str(install_dir),
        },
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_install_script_reports_missing_virtualenv_python(tmp_path):
    root = Path(__file__).resolve().parents[1]
    fake_root = tmp_path / "project"
    install_script = copy_script(root, fake_root, "install.sh")
    (fake_root / "pyproject.toml").write_text("[project]\nname = 'fake'\nversion = '0.0.0'\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(install_script)],
        cwd=fake_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "codex-tts install: missing virtualenv python at" in result.stderr
    assert "bash scripts/bootstrap.sh" in result.stderr


def test_bootstrap_script_creates_virtualenv_when_missing(tmp_path):
    root = Path(__file__).resolve().parents[1]
    fake_root = tmp_path / "project"
    bootstrap_script = copy_script(root, fake_root, "bootstrap.sh")

    result = subprocess.run(
        ["bash", str(bootstrap_script)],
        cwd=fake_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (fake_root / ".venv" / "bin" / "python").exists()
    assert f'source "{fake_root}/.venv/bin/activate"' in result.stdout

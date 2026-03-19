import argparse
import runpy
import sys

import pytest

from codex_tts.cli import build_parser, main, merge_config, positive_float, positive_int
from codex_tts.config import AppConfig


def test_positive_float_rejects_non_positive_values():
    with pytest.raises(argparse.ArgumentTypeError, match="value must be greater than 0"):
        positive_float("0")


def test_positive_int_rejects_non_positive_values():
    with pytest.raises(argparse.ArgumentTypeError, match="value must be greater than 0"):
        positive_int("-1")


def test_merge_config_enables_verbose_override():
    args = build_parser().parse_args(["--verbose"])

    merged = merge_config(AppConfig(verbose=False), args)

    assert merged.verbose is True


def test_main_raises_when_codex_binary_is_missing(monkeypatch, tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    monkeypatch.setattr("codex_tts.cli.load_config", lambda path: AppConfig())
    monkeypatch.setattr("codex_tts.cli.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="Could not find `codex` in PATH."):
        main(["--config", str(config_path)])


def test_cli_module_main_entrypoint_exits_cleanly_for_help(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["codex-tts", "--help"])

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("codex_tts.cli", run_name="__main__")

    assert exc.value.code == 0


def test_build_parser_keeps_default_config_path_under_codex_tts_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))

    args = build_parser().parse_args([])

    assert args.config == tmp_path / ".codex-tts" / "config.toml"

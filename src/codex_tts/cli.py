import argparse


class CodexTTSArgumentParser(argparse.ArgumentParser):
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args=args, namespace=namespace)
        if parsed.codex_args and parsed.codex_args[0] == "--":
            parsed.codex_args = parsed.codex_args[1:]
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = CodexTTSArgumentParser(prog="codex-tts")
    parser.add_argument("codex_args", nargs=argparse.REMAINDER)
    return parser


def main() -> int:
    build_parser().parse_args()
    return 0

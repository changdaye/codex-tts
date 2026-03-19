from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedRolloutEvent:
    kind: str
    text: str = ""

import os
from dataclasses import dataclass, field
from pathlib import Path

from .call_event import CallEvent


class UserProfile:
    """CallEventとキーバインド設定を保持するコンテナ"""

    def __init__(self, mappings: list[tuple[str, CallEvent]]) -> None:
        self._mappings = mappings

    def __iter__(self):
        return iter(self._mappings)

    def find_by_key(self, char: str) -> tuple[int, CallEvent] | None:
        for i, (key, event) in enumerate(self._mappings):
            if key == char:
                return i, event
        return None


@dataclass
class CallgenConfig:
    bpm: float = 120.0
    resolution: int = 480
    chars_per_beat: int = 1
    profile: UserProfile = field(default_factory=lambda: UserProfile([]))
    pj_root_path = Path(Path(os.environ["VIRTUAL_ENV"]).parent)


if __name__ == "__main__":
    config = CallgenConfig()
    print(config)

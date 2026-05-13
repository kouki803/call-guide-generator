from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class CallEvent:
    """コールの定義"""
    label: str
    midi_note: int
    sound_path: Path
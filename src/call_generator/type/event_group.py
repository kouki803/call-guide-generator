from dataclasses import dataclass

from .call_event import CallEvent


@dataclass
class EventGroup:
    """複数回出現するコールを縮約したクラス"""

    call: CallEvent
    count: int  # 繰り返し回数
    pos: int

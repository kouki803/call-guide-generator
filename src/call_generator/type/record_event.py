from typing import NamedTuple
from .call_event import CallEvent

class RecordedEvent(NamedTuple):
    """コールの打点クラス"""
    timestamp: float
    call: CallEvent
from datetime import datetime
from typing import List

import mido

from call_generator.type import CallgenConfig, RecordedEvent


class MidiExporter:
    """MIDIファイルへの書き出しクラス
    """
    def __init__(self, config: CallgenConfig):
        """_summary_

        Args:
            config (CallgenConfig): _description_
        """
        self.config = config

    def save(self, events: List[RecordedEvent], filename: str = f"output_{datetime.now().strftime('%y%m%d%H%M%S')}.mid") -> None:
        """イベントのリストを読み込んでmidiファイルを生成する

        Args:
            events (List[RecordedEvent]): イベントリスト
            filename (str): ファイル名
        """
        mid = mido.MidiFile(ticks_per_beat=self.config.resolution)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(self.config.bpm)))

        last_tick = 0
        for e in sorted(events, key=lambda x: x.timestamp):
            event_def = e.call
            abs_tick = int(round(e.timestamp * (self.config.bpm / 60.0) * self.config.resolution))
            delta = max(0, abs_tick - last_tick)
            
            track.append(mido.Message('note_on', note=event_def.midi_note, velocity=100, time=delta))
            track.append(mido.Message('note_off', note=event_def.midi_note, velocity=0, time=10))
            last_tick = abs_tick + 10

        mid.save(f'{self.config.pj_root_path}/export/{filename}')
        print(f" MIDI saved: {filename}")

if __name__ == "__main__":
    from pathlib import Path

    from call_generator.type import CallEvent, CallgenConfig

    midiex = MidiExporter(config=CallgenConfig())  
    
    test_mappings = [
        CallEvent("ﾊｲ!", 60, Path(".sounds/hai.wav")),
        CallEvent("ﾌッフー!", 62, Path(".sounds/fufu.wav")),
        CallEvent("fw!", 64, Path(".sounds/fw.wav"))
    ]

    events: List[RecordedEvent] = []

    current_relative_time = 0.0
    for i in range(10):
        current_relative_time += 1.0 
        events.append(RecordedEvent(
            timestamp=current_relative_time, 
            call=test_mappings[i % 3]
        ))
    
    midiex.save(events)
from datetime import datetime

import mido

from call_generator.type import CallgenConfig, RecordedEvent


class MidiExporter:
    """MIDIファイルへの書き出しクラス"""

    def __init__(self, config: CallgenConfig, lrc_name: str):
        """_summary_

        Args:
            config (CallgenConfig): _description_
            lrc_name (str): LRCファイルの名前
        """
        self.config = config
        self.lrc_name = lrc_name

        # calc_quantize_unit
        self.GRID_16N = (
            self.config.resolution // 4
        )  # 16分は4分音符の1/4 (midiは4分音符基準)

    def save(self, events: list[RecordedEvent], filename: str | None = None) -> None:
        """イベントのリストを読み込んでmidiファイルを生成する

        Args:
            events (List[RecordedEvent]): イベントリスト
            filename (str): ファイル名
        """
        if filename is None:
            filename = f"{self.lrc_name}_{datetime.now().strftime('%y%m%d%H%M%S')}.mid"

        mid = mido.MidiFile(ticks_per_beat=self.config.resolution)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(
            mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.config.bpm))
        )

        current_tick = 0
        sorted_events = sorted(events, key=lambda x: x.timestamp)

        for e in sorted_events:
            event_def = e.call

            # 浮動小数点の秒数から生の絶対tickを算出
            raw_tick = round(
                e.timestamp * (self.config.bpm / 60.0) * self.config.resolution
            )

            # 16分音符のグリッドに丸める
            abs_tick = round(raw_tick / self.GRID_16N) * self.GRID_16N

            # 前のメッセージからのデルタタイムを計算
            delta_on = max(0, abs_tick - current_tick)
            track.append(
                mido.Message(
                    "note_on", note=event_def.midi_note, velocity=100, time=delta_on
                )
            )

            # note_on 後の時刻を更新
            current_tick = abs_tick

            # note_off の処理
            duration = self.GRID_16N // 2
            track.append(
                mido.Message(
                    "note_off", note=event_def.midi_note, velocity=0, time=duration
                )
            )

            # note_off 後の時刻を更新
            current_tick += duration

        # ファイル保存
        save_path = self.config.pj_root_path / "export" / filename
        mid.save(save_path)
        print(f" MIDI saved: {save_path}")


if __name__ == "__main__":
    from pathlib import Path

    from call_generator.type import CallEvent, CallgenConfig

    midiex = MidiExporter(config=CallgenConfig(), lrc_name="test")

    test_mappings = [
        CallEvent("ﾊｲ!", 60, Path(".sounds/hai.wav")),
        CallEvent("ﾌッフー!", 62, Path(".sounds/fufu.wav")),
        CallEvent("fw!", 64, Path(".sounds/fw.wav")),
    ]

    events: list[RecordedEvent] = []

    current_relative_time = 0.0
    for i in range(10):
        current_relative_time += 1.0
        events.append(
            RecordedEvent(timestamp=current_relative_time, call=test_mappings[i % 3])
        )

    midiex.save(events)

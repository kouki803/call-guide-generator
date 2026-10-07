import re
import threading
import time
from pathlib import Path

from pynput import keyboard

from call_generator.type import CallgenConfig, RecordedEvent


class CallgeneratorApp:
    def __init__(self, config: CallgenConfig, lrc_path: Path):
        self.config = config
        self.lrc_path = lrc_path

        if not self.lrc_path.exists():
            raise FileNotFoundError(f"LRCファイルが見つかりません: {self.lrc_path}")

        self.lyrics: list[tuple[float, str]] = self._load_lrc(self.lrc_path)
        self.recorded_events: list[RecordedEvent] = []
        self.is_recording = False
        self.start_time = 0.0
        self.kb_controller = keyboard.Controller()
        self.display_thread: threading.Thread | None = None

    def _load_lrc(self, file_path: Path) -> list[tuple[float, str]]:
        """LRCファイルをパースして (秒数, 歌詞テキスト) の昇順リストを返す"""
        lyrics = []
        time_tag_pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                match = time_tag_pattern.match(line.strip())
                if match:
                    minutes, seconds, text = match.groups()
                    timestamp = int(minutes) * 60 + float(seconds)
                    text = text.strip()
                    if text:
                        lyrics.append((timestamp, text))

        lyrics.sort(key=lambda x: x[0])
        return lyrics

    def _lyrics_display_loop(self):
        """再生時間に合わせて歌詞を逐次表示するループ"""
        lyric_idx = 0
        total_lyrics = len(self.lyrics)

        while self.is_recording:
            current_elapsed = time.time() - self.start_time
            while lyric_idx < total_lyrics and current_elapsed >= self.lyrics[lyric_idx][0]:
                t, text = self.lyrics[lyric_idx]
                mins, secs = divmod(int(t), 60)
                print(f"\n🎵 [{mins:02d}:{secs:02d}] {text}")
                lyric_idx += 1

            time.sleep(0.05)

    def on_press(self, key):
        try:
            # 録音開始/停止のトグル (Space)
            if key == keyboard.Key.space:
                self.is_recording = not self.is_recording
                # メディア再生キー送出
                self.kb_controller.press(keyboard.Key.media_play_pause)
                self.kb_controller.release(keyboard.Key.media_play_pause)

                if self.is_recording:
                    self.recorded_events = []
                    self.start_time = time.time()
                    print("\n🔴 Recording Started...")

                    # 歌詞表示スレッド開始
                    self.display_thread = threading.Thread(
                        target=self._lyrics_display_loop, daemon=True
                    )
                    self.display_thread.start()
                else:
                    print("\n⏹️ Recording Stopped.")
                    return False  # リスナーを終了
                return

            # コール入力の記録
            if self.is_recording and hasattr(key, "char"):
                found = self.config.profile.find_by_key(key.char)
                if found:
                    _, event_def = found
                    elapsed = time.time() - self.start_time
                    self.recorded_events.append(RecordedEvent(elapsed, event_def))
                    print(f"Captured: {event_def.label}")

        except (AttributeError, TypeError, ValueError) as e:
            print(f"Error in on_press: {e}")

    def run(self):
        """リスナーを起動し、完了するまで待機する"""
        print("--- Call Generator Prototype ---")
        print("1. 音楽プレイヤー（YouTube等）を準備してください。")
        print("2. [SPACE] を押すと再生と同時にレコーディング開始。")
        print("3. 数字キー [1]〜[0] 押下でコールを入力。")
        print("4. もう一度 [SPACE] を押すと終了し、ファイルを保存")
        
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()

# ---  テスト実行用 Main ---

if __name__ == "__main__":
    from argparse import ArgumentParser

    from call_generator.midi_exporter import MidiExporter
    from call_generator.text_exporter import TextChartExporter
    from call_generator.type import CallEvent, UserProfile

        # ハードコーディングによるテスト設定
    test_mappings = [
        ("1", CallEvent("fu", 60, Path(".sounds/fu.wav"))),
        ("2", CallEvent("fufuu", 62, Path(".sounds/fufuu.wav"))),
        ("3", CallEvent("fwfw", 64, Path(".sounds/fwfw.wav"))),
        ("4", CallEvent("PPPH", 65, Path(".sounds/PPPH.wav"))),
        ("5", CallEvent("Yeah", 66, Path(".sounds/yeah.wav"))),
        ("6", CallEvent("hi", 67, Path(".sounds/hi.wav"))),
        ("7", CallEvent("👏", 68, Path(".sounds/clap.wav"))),
        ("9", CallEvent("○○", 69, Path(".sounds/waah.wav"))),
    ]

    test_profile = UserProfile(test_mappings)
    config = CallgenConfig(bpm=140.0, profile=test_profile)

    arg_parser = ArgumentParser(description="Call Generator Prototype")
    arg_parser.add_argument("lrc", type=Path, help="LRCファイル")
    args = arg_parser.parse_args()

    app = CallgeneratorApp(config, lrc_path=args.lrc)
    app.run()

    # export
    if app.recorded_events:
        MidiExporter(config, lrc_name=args.lrc.stem).save(app.recorded_events)
        TextChartExporter(config).export(args.lrc, app.recorded_events)
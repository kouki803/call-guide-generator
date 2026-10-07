import time

from pynput import keyboard

from call_generator.type import CallgenConfig, RecordedEvent


class CallgeneratorApp:
    def __init__(self, config: CallgenConfig):
        self.config = config
        self.recorded_events: list[RecordedEvent] = []
        self.is_recording = False
        self.start_time = 0.0
        self.kb_controller = keyboard.Controller()

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
                else:
                    print("⏹️ Recording Stopped.")
                    return False  # リスナーを停止して保存フェーズへ
                return

            # コール入力の記録
            if self.is_recording and hasattr(key, 'char'):
                found = self.config.profile.find_by_key(key.char)
                if found:
                    _, event_def = found
                    self.recorded_events.append(RecordedEvent(time.time() - self.start_time, event_def))
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
    from pathlib import Path

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
        ("9", CallEvent("○○", 69, Path(".sounds/waah.wav")))
    ]
    
    test_profile = UserProfile(test_mappings)
    config = CallgenConfig(bpm=140.0, profile=test_profile)
    
    # ダミー歌詞データ
    lrc = config.pj_root_path / "export" / "fripSide_LEVEL5_-judgelight-.lrc"

    app = CallgeneratorApp(config)
    app.run() # Spaceで録音開始、もう一度Spaceで終了

    from call_generator.midi_exporter import MidiExporter
    from call_generator.text_exporter import TextChartExporter

    # export
    if app.recorded_events:
        MidiExporter(config).save(app.recorded_events)
        TextChartExporter(config).export(Path(lrc), app.recorded_events)
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from call_generator.type import CallgenConfig, EventGroup, RecordedEvent


class TextChartExporter:
    """歌詞＋コール表のテキストを書き出すクラス"""
    def __init__(self, config: CallgenConfig):
        self.config = config

    def _zenkaku_width(self, text: str) -> int:
        return sum(2 if unicodedata.east_asian_width(c) in "FWA" else 1 for c in text)

    def _lrc_to_lines(self, lrc_path: Path) -> list[tuple[float, str]]:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lrc_content = f.read()
        lines: list[tuple[float, str]] = []
        for _ in lrc_content.splitlines():
            m = re.match(r'\[(\d+):(\d+\.\d+)\](.*)', _)
            if m:
                sec = int(m.group(1)) * 60 + float(m.group(2))
                lines.append((sec, m.group(3).strip()))
        lines.sort(key=lambda x: x[0])
        return lines

    def export(self, lrc_path: Path, events: list[RecordedEvent], filename: str = f"output_{datetime.now().strftime('%y%m%d%H%M%S')}.txt") -> None:
        """歌詞とコールの生txtを出力する

        Args:
            lrc_path (Path): lrc(歌詞)ファイルのパス
            events (list[RecordedEvent]): イベントのリスト
            filename (str): ファイル名
        """
        output: list[str] = []
        lrc_lines = self._lrc_to_lines(lrc_path)

        for i, (start_t, text) in enumerate(lrc_lines):
            # 歌詞区間に含まれるイベントを抽出
            next_t = lrc_lines[i+1][0] if i+1 < len(lrc_lines) else start_t + 10.0
            cur_events = sorted([e for e in events if start_t <= e.timestamp < next_t], key=lambda x: x.timestamp)
            
            # 歌詞行の追加
            output.append(text)

            # コール行の追加
            if not cur_events:
                output.append("")
            else:
                call_row = ""
                last_v_pos = 0 # 行内の列位置
                aggregated: list[EventGroup] = []
                
                current__call_label = ""
                occur_count = 0
                first_pos = 0

                # 同一コールの縮約
                for e in cur_events:
                    pos = round((e.timestamp - start_t) * (self.config.bpm / 60.0) * self.config.chars_per_beat)
                    
                    if e.call.label == current__call_label:
                        occur_count += 1
                    else:
                        # ラベルが変わったのでリセット
                        current__call_label = e.call.label
                        occur_count = 1                    
                        first_pos = pos
                    
                    # 判定
                    if occur_count == 5:
                        for _ in range(4): # 4コ分を破棄
                            aggregated.pop() 
                        
                        aggregated.append(EventGroup(call=e.call, count=5, pos=first_pos))  # pyright: ignore[reportPossiblyUnboundVariable]
                    
                    elif occur_count > 5: # 6個目以降はカウントアップのみ
                        aggregated[-1].count += 1
                    else:
                        # 1〜4個目までは個別に打点どおり追加
                        aggregated.append(EventGroup(call=e.call, count=1, pos=pos))


                # コール行の構築
                for event in aggregated:
                    # 前のコールとの間を全角スペースで埋める
                    gap = max(0, event.pos - last_v_pos)
                    call_row += "　" * gap
                    
                    # ラベル生成 (例: 【ﾊｲ!】x20 )
                    label = f"({event.call.label})"
                    if event.count > 1:
                        label += f"x{event.count}"
                    
                    call_row += label
                    
                    # 次の追加位置列算出
                    label_v_width = self._zenkaku_width(label) // 2
                    last_v_pos = event.pos + label_v_width
                output.append(call_row)
            
            # 行間追加
            # output.append("")

        # ファイル書き出し
        save_path = Path(self.config.pj_root_path) / "export" / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"Text Chart saved: {save_path}")

if __name__ == "__main__":
    from pathlib import Path

    from call_generator.type import CallEvent, CallgenConfig, RecordedEvent

    config = CallgenConfig()

    # 1. 試験用LRCファイルの作成
    test_lrc = config.pj_root_path / "export" / Path("test_sample.lrc")
    test_lrc.write_text(
        "[00:00.00] イントロダクション\n"
        "[00:04.00] 響き合う 願いが今、目醒めてく\n"
        "[00:08.00] (間奏)\n",
        encoding="utf-8"
    )

    
    exporter = TextChartExporter(config)

    call_hai = CallEvent("ﾊｲ!", 60, Path(""))
    call_fufu = CallEvent("ﾌッフー!", 62, Path(""))

    events: list[RecordedEvent] = [
        # 4秒の歌詞に対して、4.5s, 5.0s, 5.5s に配置 (1拍 = 0.5s)
        RecordedEvent(4.5, call_hai),
        RecordedEvent(5.0, call_hai),
        RecordedEvent(5.5, call_hai),
        
        # 8秒の間奏に対して、10.0s から 1拍おきに ﾊｲ! x6
        RecordedEvent(10.0, call_hai),
        RecordedEvent(10.5, call_hai),
        RecordedEvent(11.0, call_hai),
        RecordedEvent(11.5, call_hai),
        RecordedEvent(12.0, call_hai),
        RecordedEvent(12.5, call_hai),
        
        # 最後に ﾌッフー!
        RecordedEvent(13.5, call_fufu),
    ]

    # 4. 実行
    exporter.export(test_lrc, events, "debug_chart1.txt")

    print(Path("./export/debug_chart1.txt").read_text(encoding="utf-8"))
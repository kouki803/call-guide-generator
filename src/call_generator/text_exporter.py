import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from call_generator.type import CallgenConfig, RecordedEvent


class TextChartExporter:
    """歌詞＋コール表のテキストを書き出すクラス"""
    def __init__(self, config: CallgenConfig):
        self.config = config

    def _zenkaku_width(self, text: str) -> int:
        return sum(1 for c in text if unicodedata.east_asian_width(c) in "FWA")

    def _lrc_to_lines(self, lrc_path: Path) -> List[Tuple[float, str]]:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lrc_content = f.read()
        lines: List[tuple[float, str]] = []
        for _ in lrc_content.splitlines():
            m = re.match(r'\[(\d+):(\d+\.\d+)\](.*)', _)
            if m:
                sec = int(m.group(1)) * 60 + float(m.group(2))
                lines.append((sec, m.group(3).strip()))
        lines.sort(key=lambda x: x[0])
        return lines

    def export(self, lrc_path: Path, events: List[RecordedEvent], filename: str = f"output_{datetime.now().strftime('%y%m%d%H%M%S')}.txt") -> None:
        """歌詞とコールの生txtを出力する

        Args:
            lrc_path (Path): lrc(歌詞)ファイルのパス
            events (List[RecordedEvent]): イベントのリスト
            filename (str): ファイル名
        """
        output: List[str] = []
        lines = self._lrc_to_lines(lrc_path)

        for i, (start_t, text) in enumerate(lines):
            # 歌詞区間に含まれるイベントを抽出
            next_t = lines[i+1][0] if i+1 < len(lines) else start_t + 10.0
            cur_evs = sorted([e for e in events if start_t <= e.timestamp < next_t], key=lambda x: x.timestamp)
            
            # 歌詞行の追加
            output.append(text)

            # コール行の追加
            if not cur_evs:
                output.append("")
            else:
                call_row = ""
                last_v_pos = 0
                aggregated: list[list] = [] 

                # 同一コールの縮約
                for e in cur_evs:
                    pos = int(round((e.timestamp - start_t) * (self.config.bpm / 60.0) * self.config.chars_per_beat))
                    if aggregated and aggregated[-1][0] == e.call.label:
                        aggregated[-1][1] += 1
                    else:
                        aggregated.append([e.call, 1, pos])

                # コール行の構築
                for call_def, count, pos in aggregated:
                    # 前のコールとの間を全角スペースで埋める
                    gap = max(0, pos - last_v_pos)
                    call_row += "　" * gap
                    
                    # ラベル生成 (例: 【ﾊｲ!】x20 )
                    label = f"【{call_def.label}】"
                    if count > 1:
                        label += f"x{count}"
                    
                    call_row += label
                    
                    # 次の追加位置列算出
                    label_v_width = self._zenkaku_width(label) // 2
                    last_v_pos = pos + label_v_width
                output.append(call_row)
            
            # 行間追加
            output.append("")

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
    test_lrc = config.pj_root_path / Path("test_sample.lrc")
    test_lrc.write_text(
        "[00:00.00] イントロダクション\n"
        "[00:04.00] 響き合う 願いが今、目醒めてく\n"
        "[00:08.00] (間奏)\n",
        encoding="utf-8"
    )

    
    exporter = TextChartExporter(config)

    call_hai = CallEvent("ﾊｲ!", 60, Path(""))
    call_fufu = CallEvent("ﾌッフー!", 62, Path(""))

    events: List[RecordedEvent] = [
        # 4秒の歌詞に対して、4.5s, 5.0s, 5.5s に配置 (1拍 = 0.5s)
        RecordedEvent(4.5, call_hai),
        RecordedEvent(5.0, call_hai),
        RecordedEvent(5.5, call_hai),
        
        # 8秒の間奏に対して、10.0s から 1拍おきに ﾊｲ! x4
        RecordedEvent(10.0, call_hai),
        RecordedEvent(10.5, call_hai),
        RecordedEvent(11.0, call_hai),
        RecordedEvent(11.5, call_hai),
        
        # 最後に ﾌッフー!
        RecordedEvent(12.5, call_fufu),
    ]

    # 4. 実行
    exporter.export(test_lrc, events, "debug_chart.txt")

    print(Path("./export/debug_chart.txt").read_text(encoding="utf-8"))
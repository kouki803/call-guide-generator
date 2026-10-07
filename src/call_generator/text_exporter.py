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

    def export(
        self, 
        lrc_path: Path, 
        events: list[RecordedEvent], 
        filename: str | None = None
    ) -> None:
        """歌詞とコールの生txtを出力する

        Args:
            lrc_path (Path): lrc(歌詞)ファイルのパス
            events (list[RecordedEvent]): イベントのリスト
            filename (str, optional): 出力ファイル名。未指定時は現在日時から生成。
        """
        if filename is None:
            filename = f"{lrc_path.stem}_{datetime.now().strftime('%y%m%d%H%M%S')}.txt"

        output: list[str] = []
        lrc_lines = self._lrc_to_lines(lrc_path)

        for i, (start_t, text) in enumerate(lrc_lines):
            # 歌詞区間に含まれるイベントを抽出
            next_t = lrc_lines[i+1][0] if i+1 < len(lrc_lines) else start_t + 10.0
            cur_events = sorted(
                [e for e in events if start_t <= e.timestamp < next_t], 
                key=lambda x: x.timestamp
            )
            
            # 歌詞行の追加
            output.append(text)

            # コールのキー入力がある場合のみコール行を追加
            if cur_events:
                call_row = ""
                last_v_pos = 0  # 行内の列位置
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
                        for _ in range(4):  # 4コ分を破棄
                            aggregated.pop() 
                        aggregated.append(EventGroup(call=e.call, count=5, pos=first_pos))
                    elif occur_count > 5:  # 6個目以降はカウントアップのみ
                        aggregated[-1].count += 1
                    else:
                        # 1〜4個目までは個別に打点どおり追加
                        aggregated.append(EventGroup(call=e.call, count=1, pos=pos))

                # コール行の構築
                for event in aggregated:
                    # 前のコールとの間を半角スペースで埋める
                    gap = max(0, event.pos - last_v_pos)
                    call_row += " " * gap
                    
                    # ラベル生成 (例: (ﾊｲ!)x20 )
                    label = f"({event.call.label})"
                    if event.count > 1:
                        label += f"x{event.count}"
                    
                    call_row += label
                    
                    # 次の追加位置列算出
                    label_v_width = self._zenkaku_width(label) // 2
                    last_v_pos = event.pos + label_v_width

                output.append(call_row)

        # ファイル書き出し
        save_path = Path(self.config.pj_root_path) / "export" / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"Text Chart saved: {save_path}")
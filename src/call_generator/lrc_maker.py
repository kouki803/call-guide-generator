"""Interactively add LRC timestamps to a plain, line-broken lyrics file."""

import argparse
import ctypes
import msvcrt
import time
from pathlib import Path


def _play_pause() -> None:
    """Windowsのメディア再生/一時停止キーイベントを送信"""
    user32 = ctypes.windll.user32
    vk_media_play_pause = 0xB3
    keyeventf_keyup = 0x0002
    user32.keybd_event(vk_media_play_pause, 0, 0, 0)
    user32.keybd_event(vk_media_play_pause, 0, keyeventf_keyup, 0)


def _timestamp(seconds: float) -> str:
    centiseconds = int(seconds * 100)
    minutes, remainder = divmod(centiseconds, 6000)
    secs, centis = divmod(remainder, 100)
    return f"[{minutes:02d}:{secs:02d}.{centis:02d}]"


def _format_line(lines: list, marked: dict, index: int) -> str:
    """行のプレビュー文字列を生成"""
    if index < 0 or index >= len(lines):
        return "(なし)"
    raw_text = lines[index]
    display_text = raw_text if raw_text.strip() else "(空白行)"
    prefix = marked.get(index, "")
    return f"{prefix}{display_text}"


def _show(lines: list, marked: dict, position: int, started_at: float) -> None:
    # 画面を完全クリアしてカーソルを左上へ
    print("\033[2J\033[H", end="")

    if started_at is None:
        print(
            "【状態: 再生開始待ち】(スペース押下: 再生開始 & 1行目のスタンプ待機 / q: 終了)"
        )
    elif position >= len(lines):
        print("【状態: 完了】全ての行にタイムスタンプを付けました。(q: 保存して終了)")
    else:
        elapsed = time.monotonic() - started_at
        print(
            f"【経過時間: {elapsed:.2f}秒】(スペース押下: 現在行にスタンプ / q: 終了)"
        )

    print("-" * 50)

    # 確定行 (-2)
    line_minus_2 = _format_line(lines, marked, position - 2)
    print(f"   {line_minus_2}")

    # 確定行 (-1)
    line_minus_1 = _format_line(lines, marked, position - 1)
    print(f"   {line_minus_1}")

    # スタンプ待ち行 (0)
    if position < len(lines):
        curr_text = lines[position]
        disp_curr = curr_text if curr_text.strip() else "(空白行)"
        print(f"> : {disp_curr}")
    else:
        print("> : (全行スタンプ完了)")

    print("-" * 50)


def resolve_output_path(source: Path, output_arg: str | None = None) -> Path:
    """出力先パスを決定し、既存ファイルと重複しない一意のパスを返す"""
    if output_arg:
        base_path = Path(output_arg)
    else:
        base_path = source.parent / f"{source.stem}_timed.lrc"
    base_path.parent.mkdir(parents=True, exist_ok=True)

    if not base_path.exists():
        return base_path
    else:
        # 既存ファイルがある場合に重複しない_nを採番
        parent = base_path.parent
        stem = base_path.stem
        suffix = base_path.suffix

        n = 1
        while True:
            candidate = parent / f"{stem}_{n}{suffix}"
            if not candidate.exists():
                return candidate
            n += 1


def make_lrc(source: Path, lrc_out: Path) -> None:
    lines = source.read_text(encoding="utf-8-sig").splitlines()
    marked = {}
    position = 0
    started_at = None

    _show(lines, marked, position, started_at)
    while True:
        key = msvcrt.getwch()
        if key.lower() == "q" or key == "\x1b":
            break
        if key != " ":
            continue

        if started_at is None:
            # 初回スペース: 再生開始
            _play_pause()
            started_at = time.monotonic()
        elif position < len(lines):
            # 空白行であっても現在位置にタイムスタンプを付与
            marked[position] = _timestamp(time.monotonic() - started_at)
            position += 1

        _show(lines, marked, position, started_at)

    output = [
        f"{marked[i]}{line}" if i in marked else line for i, line in enumerate(lines)
    ]
    lrc_out.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"\n保存しました: {lrc_out}")


def main():
    parser = argparse.ArgumentParser(
        description="歌詞テキストにLRCタイムスタンプを付けます"
    )
    parser.add_argument("lyrics", help="時刻無しの歌詞テキスト")
    parser.add_argument(
        "-o",
        "--output",
        help="出力ファイル (既定: 入力フォルダ内/[入力ファイル名]_timed.lrc)",
    )
    args = parser.parse_args()

    source_path = Path(args.lyrics)
    lrc_out = resolve_output_path(source_path, args.output)

    make_lrc(source_path, lrc_out)


if __name__ == "__main__":
    main()

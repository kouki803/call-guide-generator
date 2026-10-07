"""Interactively add LRC timestamps to a plain, line-broken lyrics file."""

import argparse
import ctypes
import msvcrt
import time
from pathlib import Path


def _play_pause():
	"""Send the Windows media play/pause key event."""
	user32 = ctypes.windll.user32
	vk_media_play_pause = 0xB3
	keyeventf_keyup = 0x0002
	user32.keybd_event(vk_media_play_pause, 0, 0, 0)
	user32.keybd_event(vk_media_play_pause, 0, keyeventf_keyup, 0)


def _timestamp(seconds):
	centiseconds = int(seconds * 100)
	minutes, remainder = divmod(centiseconds, 6000)
	secs, centis = divmod(remainder, 100)
	return f"[{minutes:02d}:{secs:02d}.{centis:02d}]"

def _format_line_text(line):
	"""CLI表示用のテキスト整形（空白行の場合はプレースホルダーを表示）"""
	return line if line.strip() else "(空白行)"

def _show(lines, lyric_indices, marked, position, started_at):
	print("\033[2J\033[H", end="")
	# print("スペース: 再生開始 / 次の行にタイムスタンプ   q: 保存して終了")
	if started_at is None:
		print("再生開始待ち")
	else:
		pass
        # print(f"経過時間: {time.monotonic() - started_at:.2f} 秒")

	if position >= len(lyric_indices):
		print("全ての歌詞にタイムスタンプを付けました。")
		return

	# 前2行、現在行、次1行を表示
	start_idx = max(0, position - 2)
	end_idx = min(len(lines), position + 2)

	for index in range(start_idx, end_idx):
		marker = ">" if index == position else " "
		prefix = marked.get(index, "")
		text = _format_line_text(lines[index])
		print(f"{marker} {prefix}{text}")

	current = lyric_indices[position]
	for index in range(max(0, current - 1), min(len(lines), current + 2)):
		if index == current:
			marker = ">"
		elif index < current:
			marker = " "
		else:
			marker = " "
		prefix = marked.get(index, "")
		text = _format_line_text(lines[index])
		print(f"{marker} {prefix}{text}")


def make_lrc(source, destination):
	lines = Path(source).read_text(encoding="utf-8-sig").splitlines()
	lyric_indices = [i for i, line in enumerate(lines) if line.strip()]
	marked = {}
	position = 0
	started_at = None

	_show(lines, lyric_indices, marked, position, started_at)
	while True:
		key = msvcrt.getwch()
		if key.lower() == "q" or key == "\x1b":
			break
		if key != " ":
			continue

		if started_at is None:
			_play_pause()
			started_at = time.monotonic()
		elif position < len(lyric_indices):
			marked[lyric_indices[position]] = _timestamp(time.monotonic() - started_at)
			position += 1
		_show(lines, lyric_indices, marked, position, started_at)

	output = [f"{marked[i]}{line}" if i in marked else line for i, line in enumerate(lines)]
	Path(destination).write_text("\n".join(output) + "\n", encoding="utf-8")
	print(f"保存しました: {destination}")


def main():
	parser = argparse.ArgumentParser(description="歌詞テキストにLRCタイムスタンプを付けます")
	parser.add_argument("lyrics", help="時刻無しの歌詞テキスト")
	parser.add_argument("-o", "--output", help="出力ファイル (既定: 入力名.lrc)")
	args = parser.parse_args()
	source = Path(args.lyrics)
	destination = Path("./export/") / args.output if args.output else source.with_suffix(".lrc")
	make_lrc(source, destination)


if __name__ == "__main__":
	main()

from __future__ import annotations

import argparse
import errno
import html
import re
import sys
from dataclasses import asdict
from pathlib import Path

from call_generator.type.html_rendar_config import RenderConfig
from call_generator.util.fname_resolver import FnameResolver
from call_generator.util.png_renderer import PlaywrightRenderer

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        *, *::before, *::after {{
            box-sizing: border-box;
        }}
        body {{
            background-color: {body_bg_color};
            display: flex;
            justify-content: center;
            align-items: flex-start;
            min-height: 100vh;
            margin: 0;
            padding: 32px 16px;
            font-family: {font_family};
        }}
        .card {{
            background: {card_bg_color};
            width: 100%;
            max-width: {card_max_width};
            padding: {card_padding};
            border-radius: {card_border_radius};
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            margin: 0 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid {border_color};
            gap: 16px;
        }}
        .title {{
            font-size: {title_font_size};
            font-weight: 700;
            color: {title_color};
            margin: 0;
            font-family: {font_family};
            line-height: 1.2;
            word-break: break-word;
        }}
        .legend {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 4px 8px;
            background-color: {body_bg_color};
            border: 1px solid {border_color};
            border-radius: 6px;
            font-size: {legend_font_size};
            font-family: {font_family};
            white-space: nowrap;
            flex-shrink: 0;
        }}
        .legend-title {{
            font-size: 11px;
            font-weight: 700;
            color: #262D36;
            padding-right: 8px;
            border-right: 1px solid {border_color};
            line-height: 1;
        }}
        .legend-items {{
            display: flex;
            flex-direction: column;
            gap: 2px;
            font-weight: 700;
            line-height: 1.2;
        }}
        .lyrics-container {{
            line-height: {line_height};
            font-size: {line_font_size};
            font-family: {font_family};
            word-break: break-all;
        }}
        .line {{
            display: block;
            min-height: 1em; 
            margin: 0;
            padding: 0;
            white-space: pre-wrap;
        }}
        .line.lyrics {{
            color: {lyrics_color};
        }}
        .line.call, .call {{
            color: {call_color};
            font-weight: {call_font_weight};
        }}
        /* カスタム着色スタイル */
        {extra_color_styles}
    </style>
</head>
<body>
    <article class="card">
        <header class="header">
            <h1 class="title">{title}</h1>
            {legend_content}
        </header>
        <div class="lyrics-container">{body_content}</div>
    </article>
</body>
</html>
"""


class GuideTxtFormatter:
    """歌詞テキストファイルを解析し、装飾済みHTMLまたはPNG画像を出力するクラス"""

    def __init__(
        self,
        config: RenderConfig,
        renderer: PlaywrightRenderer | None = None,
        song_title: str | None = None,
    ):
        self.config = config
        self._rule_map = {rule.marker: rule for rule in self.config.marker_rules}
        self._marker_pattern = self._build_marker_regex()
        self._renderer = renderer
        self.song_title = song_title

    def _get_renderer(self) -> PlaywrightRenderer:
        """PNG生成時に必要に応じてPlaywrightRendererインスタンス初期化"""
        if self._renderer is None:
            self._renderer = PlaywrightRenderer()
        return self._renderer

    def _build_marker_regex(self) -> re.Pattern | None:
        """設定内のマーカー一覧から正規表現を生成 (コール)x数字+記号 または (コール)+記号"""
        if not self._rule_map:
            return None

        escaped_markers = "|".join(
            re.escape(marker) for marker in self._rule_map
        )
        pattern_str = rf"(\([^)]+\)(?:x\d+)?)({escaped_markers})"
        return re.compile(pattern_str)

    def _build_extra_styles(self) -> str:
        """CSS用の予備カラースタイル文字列を生成"""
        styles = []
        for rule in self.config.marker_rules:
            if rule.color:
                styles.append(
                    f".{rule.css_class} {{ color: {rule.color} !important; }}"
                )
        return "\n        ".join(styles)

    def _build_legend_html(self, used_markers: set[str] | None = None) -> str:
        """設定内のMarkerRulesから、本文中に存在するマーカーのみ凡例HTML要素を生成"""
        items: list[str] = []
        for rule in self.config.marker_rules:
            if not rule.label:
                continue
            if used_markers is not None and rule.marker not in used_markers:
                continue
            escaped_label = html.escape(rule.label)
            items.append(
                f'<span class="{rule.css_class}">({escaped_label})</span>'
            )
        if not items:
            return ""
        items_str = "\n                ".join(items)
        return (
            f'<div class="legend">\n'
            f'            <span class="legend-title">凡<br>例</span>\n'
            f'            <div class="legend-items">\n'
            f'                {items_str}\n'
            f'            </div>\n'
            f'        </div>'
        )

    def _apply_marker_rules(
        self,
        text: str,
        used_markers: set[str] | None = None,
    ) -> str:
        """マーカー記号付きコールを検出し、spanタグと全角空白に置換"""
        if not self._marker_pattern:
            return text

        def _replacer(match: re.Match) -> str:
            call_body = match.group(1)
            marker = match.group(2)
            if used_markers is not None:
                used_markers.add(marker)
            rule = self._rule_map[marker]
            return f'<span class="{rule.css_class}">{call_body}</span>{rule.replacement_char}'

        return self._marker_pattern.sub(_replacer, text)

    def _parse_lines_to_html(self, raw_text: str) -> tuple[str, set[str]]:
        """元テキストの行構造・空行をそのままHTML要素へ変換"""
        html_elements: list[str] = []
        used_markers: set[str] = set()
        lines = raw_text.splitlines()

        for line in lines:
            if not line:
                html_elements.append('<span class="line lyrics">&nbsp;</span>')
                continue

            escaped = html.escape(line)

            if line.startswith((" ", "\u3000")):
                processed = self._apply_marker_rules(escaped, used_markers)
                html_elements.append(
                    f'<span class="line call">{processed}</span>'
                )
            else:
                html_elements.append(
                    f'<span class="line lyrics">{escaped}</span>'
                )

        return "\n".join(html_elements), used_markers

    def build_html_content(self, src_path: Path) -> str:
        """テキストファイルを解析し、レンダリング用のHTML文字列を生成"""
        raw_text = src_path.read_text(encoding="utf-8")
        if self.song_title is None:
            title = FnameResolver.extract_title(src_path.stem)
        else: 
            title = self.song_title
        body_content, used_markers = self._parse_lines_to_html(raw_text)

        context = {
            **asdict(self.config),
            "title": html.escape(title),
            "legend_content": self._build_legend_html(used_markers),
            "body_content": body_content,
            "extra_color_styles": self._build_extra_styles(),
        }
        return HTML_TEMPLATE.format(**context)

    def convert_to_html(
        self,
        src_path: Path,
        save_folder_path: Path | None = None,
    ) -> Path:
        """HTMLファイルを生成して保存し、出力先のPathを返す"""
        rendered_html = self.build_html_content(src_path)

        if save_folder_path is None:
            save_folder_path = src_path.parent
        base_out_path = save_folder_path / src_path.stem

        out_file = base_out_path.with_suffix(".html")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(rendered_html, encoding="utf-8")

        return out_file

    def convert_to_png(
        self,
        src_path: Path,
        save_folder_path: Path | None = None,
    ) -> Path:
        """HTML文字列を生成し、レンダラーから取得したPNGバイナリをファイルに保存する"""
        rendered_html = self.build_html_content(src_path)

        if save_folder_path is None:
            save_folder_path = src_path.parent
        title = self.song_title or src_path.stem
        out_file = (save_folder_path / title).with_suffix(".png")
        out_file.parent.mkdir(parents=True, exist_ok=True)


        png_data = self._get_renderer().render_to_png_bytes(rendered_html)
        out_file.write_bytes(png_data)

        return out_file

def main():
    parser = argparse.ArgumentParser(
        description="歌詞テキストファイルからコール着色済みHTMLまたはPNGを生成する"
    )
    parser.add_argument(
        "src_file",
        type=Path,
        help="入力元のテキストファイルパス (.txt)",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=None,
        help="出力先ディレクトリ",
    )
    parser.add_argument(
        "-p",
        "--preview",
        action="store_true",
        help="PNG画像の代わりにHTMLでプレビューする",
    )
    parser.add_argument(
        "-t",
        "--title",
        type=str,
        default=None,
        help="出力HTML/PNG内の歌詞タイトル（未指定時はファイル名から自動抽出）",
    )

    args = parser.parse_args()

    if not args.src_file.exists():
        print(
            f"[Error] 指定されたファイルが存在しません: {args.src_file}",
            file=sys.stderr,
        )
        sys.exit(1)
    
    config = RenderConfig()
    formatter = GuideTxtFormatter(config=config, song_title=args.title)

    try:
        out_dir = args.out_dir or args.src_file.parent

        if args.preview:
            out_path = formatter.convert_to_html(
                src_path=args.src_file,
                save_folder_path=out_dir,
            )
            print(f"[Success] HTMLを出力しました: {out_path.resolve()}")
        else:
            out_path = formatter.convert_to_png(
                src_path=args.src_file,
                save_folder_path=out_dir,
            )
            print(f"[Success] PNGを出力しました: {out_path.resolve()}")
        
    except (PermissionError, OSError) as e:
        if e.errno in (errno.EINVAL, errno.EACCES):
            target = e.filename or "出力先ファイル"
            print(
                f"[Error] 出力先ファイル '{target}' が他のプログラム（画像ビューアなど）で開かれているためアクセスできません。",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[Error] 処理中にエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)
    except (UnicodeError, ValueError, KeyError, RuntimeError) as e:
        print(f"[Error] 処理中にエラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
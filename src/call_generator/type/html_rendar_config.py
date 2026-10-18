from dataclasses import dataclass


@dataclass(frozen=True)
class MarkerRule:
    """記号によるコールの特殊装飾ルールの定義"""

    marker: str  # トリガーとなる記号 (例: "△")
    color: str  # 特殊装飾用のカラーコード (例: "#0db654")
    label: str = ""  # 色・マーカーの表示名 (例: "赤字", "緑字")
    description: str = ""  # 凡例用の説明文 (例: "要注意箇所", "お好みで")
    css_class: str = ""  # 付与するCSSクラス (例: "call-green", 省略時は自動生成)
    replacement_char: str = "\u3000"  # マーカーを除去した後の代替文字（等幅維持用）

    def __post_init__(self) -> None:
        if not self.css_class and self.marker:
            object.__setattr__(
                self, "css_class", f"call-marker-{ord(self.marker[0])}"
            )


@dataclass(frozen=True)
class RenderConfig:
    """HTMLレンダリング用のスタイル・フォント設定パラメータ"""

    # カラー定義
    lyrics_color: str = "#222222"  # 通常行（黒系）
    call_color: str = "#1a73e8"  # コール行（青系）
    title_color: str = "#111827"  # タイトル文字色
    card_bg_color: str = "#ffffff"  # カード背景色
    body_bg_color: str = "#f8fafc"  # 全体背景色
    border_color: str = "#B9CDE8"  # タイトル下などの区切り線
    legend_desc_color: str = "#3A434F"  # 凡例説明文の文字色

    # マーカー・装飾ルール定義
    marker_rules: tuple[MarkerRule, ...] = (
        # 一番上から描画されるので重要度順に並べる
        MarkerRule(
            marker="☆",
            color="#E43434",
            css_class="call-orange",
            label="赤字",
            description="演者さん希望",
        ),
        MarkerRule(
            marker="△",
            color="#0db654",
            css_class="call-green",
            label="緑字",
            description="お好みで",
        ),
        MarkerRule(
            marker="◆",
            color="#d66210",
            css_class="call-red",
            label="橙字",
            description="要注意箇所",
        ),
        # 将来ルールが増えた場合もここに追加して対応
    )

    # フォント・サイズ・行間
    font_family: str = (
        '"BIZ UDGothic", "MS Gothic", "Osaka-mono", Consolas, '
        '"Courier New", Courier, monospace'
    )
    title_font_size: str = "24px"
    line_font_size: str = "16px"
    legend_font_size: str = "12px"
    line_height: float = 1.2
    call_font_weight: str = "normal"

    # レイアウト
    card_max_width: str = "500px"
    card_padding: str = "30px"
    card_border_radius: str = "12px"

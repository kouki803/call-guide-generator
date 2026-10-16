from dataclasses import dataclass, field


@dataclass(frozen=True)
class MarkerRule:
    """記号によるコールの特殊装飾ルールの定義"""

    marker: str  # トリガーとなる記号 (例: "△")
    css_class: str  # 付与するCSSクラス (例: "call-green")
    replacement_char: str = "\u3000"  # マーカーを除去した後の代替文字（等幅維持用）


@dataclass(frozen=True)
class RenderConfig:
    """HTMLレンダリング用のスタイル・フォント設定パラメータ"""

    # カラー定義
    lyrics_color: str = "#222222"  # 通常行（黒系）
    call_color: str = "#1a73e8"  # コール行（青系）
    title_color: str = "#111827"  # タイトル文字色
    card_bg_color: str = "#ffffff"  # カード背景色
    body_bg_color: str = "#f8fafc"  # 全体背景色
    border_color: str = "#e2e8f0"  # タイトル下などの区切り線

    # 特記事項用カラー定義
    alt_colors: dict[str, str] = field(default_factory=lambda: {
        "call-green": "#0db654",     # 提案コール用の色    
    })
    marker_rules: tuple[MarkerRule, ...] = (
        MarkerRule(marker="△", css_class="call-green", replacement_char=" "),
        # 将来ルールが増えた場合もここに追加して対応
        # MarkerRule(marker="★", css_class="call-orange", replacement_char=" "),
    )

    # フォント・サイズ・行間
    font_family: str = (
        '"BIZ UDGothic", "MS Gothic", "Osaka-mono", Consolas, '
        '"Courier New", Courier, monospace'
    )
    title_font_size: str = "24px"
    line_font_size: str = "15px"
    line_height: float = 1.2
    call_font_weight: str = "normal"

    # レイアウト
    card_max_width: str = "515px"
    card_padding: str = "40px"
    card_border_radius: str = "12px"

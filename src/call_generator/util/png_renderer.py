from __future__ import annotations

from playwright.sync_api import sync_playwright


class PlaywrightRenderer:
    """HTML文字列を受け取り、PNGバイナリデータをレンダリングして返すクラス"""

    def __init__(
        self,
        scale_factor: float = 1.5,
        # channel: str | None = None,
    ) -> None:
        """
        Args:
            scale_factor: 出力用のスケールファクター (デフォルト1.5)
            channel: システムのChromeを使う場合は 'chrome' を指定 (未指定時はPlaywrightのChromium)
        """
        self.scale_factor = scale_factor
        # self.channel = channel

    def render_to_png_bytes(
        self,
        html_content: str,
        clip_card: bool = True,
    ) -> bytes:
        """HTML文字列からPNG画像バイナリを生成して返す"""
        with sync_playwright() as p:
            launch_kwargs = {}
            # if self.channel:
            #     launch_kwargs["channel"] = self.channel

            browser = p.chromium.launch(**launch_kwargs)
            page = browser.new_page(device_scale_factor=self.scale_factor)
            page.set_content(html_content)

            if clip_card:
                png_bytes = page.locator(".card").screenshot()
            else:
                png_bytes = page.screenshot(full_page=True)

            browser.close()

        return png_bytes


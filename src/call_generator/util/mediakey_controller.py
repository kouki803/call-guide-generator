import os
import time

from pynput import keyboard


class MediaKeyController:
    """Media Go（WM_APPCOMMAND 直接送信）と Spotify / ブラウザ(YouTube) 等の

    グローバルメディアキー送出を自動切り替えするコントローラー
    """

    def __init__(self):
        self.is_windows = os.name == "nt"
        self.kb_controller = keyboard.Controller()

        if self.is_windows:
            import ctypes

            self.user32 = ctypes.windll.user32

            # Win32 定数
            self.WM_APPCOMMAND = 0x0319
            self.APPCOMMAND_MEDIA_PLAY_PAUSE = 14
            self.HWND_BROADCAST = 0xFFFF
            self.VK_MEDIA_PLAY_PAUSE = 0xB3
            self.KEYEVENTF_KEYUP = 0x0002
            self.KEYEVENTF_EXTENDEDKEY = 0x0001

    def _find_mediago_hwnd(self) -> int | None:
        """Media Go のメインウィンドウハンドルを検出（非起動時は None）"""
        if not self.is_windows:
            return None

        import ctypes

        found_hwnd = None

        def enum_windows_proc(hwnd, lparam):
            nonlocal found_hwnd
            if not self.user32.IsWindowVisible(hwnd):
                return True

            length = self.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                # タイトルに "Media Go" が含まれるか確認
                if "media go" in title.lower():
                    found_hwnd = hwnd
                    return False  # 見つかったら列挙終了
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
        )
        self.user32.EnumWindows(WNDENUMPROC(enum_windows_proc), 0)
        return found_hwnd

    def _send_mediago_appcommand(self, hwnd: int) -> None:
        """Media Go のウィンドウに直接 WM_APPCOMMAND を送信（方式4: バックグラウンド動作）"""
        lparam = self.APPCOMMAND_MEDIA_PLAY_PAUSE << 16
        # PostMessage だと破棄される場合があるため、テスト成功時と同じ SendMessageW を使用
        self.user32.SendMessageW(hwnd, self.WM_APPCOMMAND, hwnd, lparam)

    def _send_global_media_key(self) -> None:
        """Spotify / YouTube (ブラウザ) 等に向けた汎用グローバルメディアキー送出"""
        if self.is_windows:
            try:
                # 1. システム全体へ WM_APPCOMMAND をブロードキャスト
                lparam = self.APPCOMMAND_MEDIA_PLAY_PAUSE << 16
                self.user32.SendNotifyMessageW(
                    self.HWND_BROADCAST, self.WM_APPCOMMAND, 0, lparam
                )

                # 2. ハードウェア仮想キー (VK_MEDIA_PLAY_PAUSE) も送出
                self.user32.keybd_event(
                    self.VK_MEDIA_PLAY_PAUSE, 0, self.KEYEVENTF_EXTENDEDKEY, 0
                )
                time.sleep(0.01)
                self.user32.keybd_event(
                    self.VK_MEDIA_PLAY_PAUSE,
                    0,
                    self.KEYEVENTF_EXTENDEDKEY | self.KEYEVENTF_KEYUP,
                    0,
                )
                return
            except (AttributeError, OSError, TypeError, ValueError) as e:
                print(f"[Warning] Failed to send global media key: {e}")

        # macOS / Linux または例外発生時のフォールバック
        self.kb_controller.press(keyboard.Key.media_play_pause)
        self.kb_controller.release(keyboard.Key.media_play_pause)

    def send_play_pause(self) -> None:
        """再生/一時停止を送出（Media Go が起動中なら直接送信、それ以外は汎用送信）"""
        mg_hwnd = self._find_mediago_hwnd()

        if mg_hwnd is not None:
            self._send_mediago_appcommand(mg_hwnd)
            return

        # Media Go が起動していない場合（Spotify / YouTube 等）
        self._send_global_media_key()


if __name__ == "__main__":
    controller = MediaKeyController()

    print("=== MediaKeyController 動作確認 ===")
    mg = controller._find_mediago_hwnd()
    if mg is not None:
        print(f"✅ Media Go を検出 (HWND={hex(mg)}): 直接 WM_APPCOMMAND で制御します。")
    else:
        print("ℹ️ Media Go は非起動: 汎用メディアキー(Spotify/YouTube等)で制御します。")

    print("\n【再生/一時停止】を送出します...")
    time.sleep(0.1)
    controller.send_play_pause()
    print("▶️ 送出完了（もう一度1秒後に送出）")

    time.sleep(1)
    controller.send_play_pause()
    print("⏹️ 送出完了")
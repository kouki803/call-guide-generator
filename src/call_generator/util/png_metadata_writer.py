from __future__ import annotations

import io
import os
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, PngImagePlugin


class PngMetadataWriter:
    """PNG画像にメタデータ（作成日時・更新日時、Exif等）を付与して保存するクラス"""

    @classmethod
    def _extract_creation_time(
        cls, existing_path: Path
    ) -> tuple[str, str] | None:
        """既存PNGファイルから (creation_time_iso, creation_time_exif) を抽出する"""
        if not existing_path.exists():
            return None

        # 1. 既存PNGのメタデータから抽出
        try:
            with Image.open(existing_path) as im:
                # テキストチャンク (Creation Time)
                creation_str = im.text.get("Creation Time")
                if creation_str:
                    try:
                        dt = datetime.fromisoformat(creation_str)
                        return dt.isoformat(), dt.strftime("%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass

                # Exif (DateTimeOriginal: 0x9003)
                exif = im.getexif()
                exif_orig = exif.get(0x9003)
                if exif_orig:
                    try:
                        clean_date = str(exif_orig).strip("\x00")
                        dt = datetime.strptime(
                            clean_date, "%Y:%m:%d %H:%M:%S"
                        ).astimezone()
                        return dt.isoformat(), dt.strftime("%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass
        except (OSError, ValueError):
            pass

        # 2. ファイルシステムの ctime からのフォールバック
        try:
            ctime = existing_path.stat().st_ctime
            dt = datetime.fromtimestamp(ctime, tz=UTC).astimezone()
            return dt.isoformat(), dt.strftime("%Y:%m:%d %H:%M:%S")
        except (OSError, ValueError):
            return None

    @classmethod
    def save_with_metadata(
        cls,
        raw_png_bytes: bytes,
        out_file: Path,
        now: datetime | None = None,
    ) -> None:
        """PNGバイナリにメタデータを付与して指定パスに保存する。

        同名の既存ファイルが存在する場合は初回の作成日時（Creation Time / DateTimeOriginal）を
        キープし、更新日時（Last Modification Time / DateTime / ファイルmtime）のみを最新日時に更新します。

        Args:
            raw_png_bytes: レンダラーから取得した生のPNG画像バイナリ
            out_file: 保存先ファイルパス (.png)
            now: 更新日時（テスト等で指定がない場合は現在日時）
        """
        if now is None:
            now = datetime.now().astimezone()

        # 既存ファイルから作成日時を取得（なければ現在日時）
        existing_creation = cls._extract_creation_time(out_file)
        if existing_creation is not None:
            creation_iso, creation_exif = existing_creation
        else:
            creation_iso = now.isoformat()
            creation_exif = now.strftime("%Y:%m:%d %H:%M:%S")

        mod_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        mod_exif_str = now.strftime("%Y:%m:%d %H:%M:%S")

        # Pillow (PIL) で画像を開き、メタデータを付与
        image = Image.open(io.BytesIO(raw_png_bytes))

        # PNG text メタデータ
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Creation Time", creation_iso)
        pnginfo.add_text("Last Modification Time", mod_time_str)

        # Exif メタデータ
        exif = image.getexif()
        exif[0x0132] = mod_exif_str  # DateTime (最終変更日時)
        exif[0x9003] = creation_exif  # DateTimeOriginal (作成日時)

        # ファイルへ保存
        out_file.parent.mkdir(parents=True, exist_ok=True)
        image.save(out_file, "PNG", pnginfo=pnginfo, exif=exif)

        # ファイルシステムの更新日時 (mtime) も同期
        ts = now.timestamp()
        os.utime(out_file, (ts, ts))

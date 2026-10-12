from datetime import datetime
from pathlib import Path

from pathvalidate import sanitize_filename


class FnameResolver:

    @classmethod
    def out_file_path(cls, lrc_name: str, save_folder_path: Path | None = None) -> Path:
        """保存先ファイルパスを返す（拡張子なし）

        Args:
            lrc_name (str): _description_
            save_folder_path (Path | None, optional): _description_. Defaults to None.

        Returns:
            Path: _description_
        """
        safe_lrc_name = sanitize_filename(lrc_name)
        filename = f"{safe_lrc_name}_{datetime.now().strftime('%y%m%d%H%M%S')}"

        if save_folder_path is None:
            save_path = Path("export")/ safe_lrc_name / filename # defalt
        else:
            save_path = save_folder_path / filename
        return save_path

    @classmethod
    def resolve_output_path(cls, source: Path, output_arg: str | None = None) -> Path:
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

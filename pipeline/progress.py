"""Thanh tiến trình tối giản cho các bước chạy lâu.

Không phụ thuộc thư viện ngoài. Khi chạy trong terminal, thanh được vẽ lại
trên cùng một dòng (\\r). Khi output bị chuyển vào file (chạy nền), mỗi dòng
được ghi ra định kỳ để log vẫn đọc được và không phình to.
"""

from __future__ import annotations

import shutil
import sys
import time
from typing import TextIO


def human(seconds: float | None) -> str:
    """Đổi giây thành mm:ss hoặc h:mm:ss."""
    if seconds is None:
        return "--:--"
    seconds = max(0, int(round(seconds)))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class Progress:
    """Thanh tiến trình có % , số lượng, thời gian đã chạy và ETA."""

    def __init__(
        self,
        total: float,
        label: str,
        *,
        unit: str = "",
        width: int = 22,
        stream: TextIO | None = None,
    ) -> None:
        self.total = max(float(total), 1.0)
        self.label = label
        self.unit = unit
        self.width = width
        self.stream = stream if stream is not None else sys.stderr
        self.started = time.perf_counter()
        self.current = 0.0
        self.detail = ""

        # Màn hình không phải UTF-8 hoặc output bị chuyển vào file thì dùng
        # ký tự ASCII cho chắc (log mở bằng editor/console cũ vẫn đọc được).
        encoding = (getattr(self.stream, "encoding", "") or "").lower()
        self._tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self._unicode = "utf" in encoding and self._tty
        self._sep = " · " if self._unicode else " | "
        self._last_draw = 0.0
        self._last_text = ""
        self.draw(force=True)

    # ------------------------------------------------------------ internals

    def _elapsed(self) -> float:
        return time.perf_counter() - self.started

    def _eta(self) -> float | None:
        if self.current <= 0:
            return None
        rate = self.current / max(self._elapsed(), 1e-9)
        if rate <= 0:
            return None
        return max(0.0, (self.total - self.current) / rate)

    def _text(self) -> str:
        ratio = min(1.0, self.current / self.total)
        filled = int(round(self.width * ratio))
        full, empty = ("█", "░") if self._unicode else ("#", "-")
        bar = full * filled + empty * (self.width - filled)

        unit = f" {self.unit}" if self.unit else ""
        parts = [
            self.label,
            f"[{bar}]",
            f"{ratio * 100:5.1f}%",
            f"{self.current:.0f}/{self.total:.0f}{unit}",
            f"đã {human(self._elapsed())}",
        ]
        if ratio < 1.0:
            parts.append(f"còn {human(self._eta())}")

        text = "  " + self._sep.join(parts)
        try:
            columns = shutil.get_terminal_size((120, 24)).columns
        except OSError:
            columns = 120
        room = columns - 1 - len(text) - len(self._sep)
        if self.detail:
            if room >= 8:
                detail = self.detail
                if len(detail) > room:
                    detail = detail[: max(1, room - 3)] + ("…" if self._unicode else "...")
                text += self._sep + detail
        return text

    # ------------------------------------------------------------ public

    def set(self, current: float, detail: str | None = None, total: float | None = None) -> None:
        if total is not None:
            self.total = max(float(total), 1.0)
        self.current = min(self.total, max(self.current, float(current)))
        if detail is not None:
            self.detail = detail
        self.draw()

    def update(self, advance: float = 1.0, detail: str | None = None) -> None:
        self.set(self.current + advance, detail)

    def draw(self, *, force: bool = False) -> None:
        now = time.perf_counter()
        if not force:
            # Terminal: 10 lần/giây. File log: 1 dòng mỗi 5 giây.
            limit = 0.1 if self._tty else 5.0
            if now - self._last_draw < limit and self.current < self.total:
                return
        self._last_draw = now
        ending = "\r" if self._tty else "\n"
        text = self._text()
        try:
            self.stream.write(text + ending)
        except UnicodeEncodeError:
            self._unicode = False
            self._sep = " | "
            text = self._text()
            self.stream.write(text + ending)
        self.stream.flush()
        self._last_text = text

    def close(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        self.current = self.total
        text = self._text()
        if self._tty:
            self.stream.write(text + "\n")
        elif text != self._last_text:
            # Chạy nền: không in trùng dòng 100% vừa in.
            self.stream.write(text + "\n")
        self.stream.flush()
        self._last_text = text

    def __enter__(self) -> "Progress":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

"""Đo bề rộng chữ từ file font (TTF/OTF) bằng thư viện chuẩn.

Chỉ đọc các bảng head/hhea/hmtx/cmap: đủ để ước lượng một dòng chữ rộng bao
nhiêu em, không xét kerning hay ligature (sai số vài phần trăm).
"""

from __future__ import annotations

import struct
from pathlib import Path


class FontMetrics:
    def __init__(self, path: Path) -> None:
        data = path.read_bytes()
        count = struct.unpack(">H", data[4:6])[0]
        tables = {}
        for index in range(count):
            tag, _, offset, length = struct.unpack(">4sIII", data[12 + 16 * index : 28 + 16 * index])
            tables[tag.decode("latin-1")] = (offset, length)

        head = tables["head"][0]
        self.units = struct.unpack(">H", data[head + 18 : head + 20])[0]
        hhea = tables["hhea"][0]
        self.ascent, self.descent = struct.unpack(">hh", data[hhea + 4 : hhea + 8])
        metrics_count = struct.unpack(">H", data[hhea + 34 : hhea + 36])[0]

        hmtx = tables["hmtx"][0]
        self.advances = [
            struct.unpack(">H", data[hmtx + 4 * i : hmtx + 4 * i + 2])[0]
            for i in range(metrics_count)
        ]
        self.cmap = self._read_cmap(data, tables["cmap"][0])
        space = self.cmap.get(ord(" "))
        self.fallback = self._advance(space) if space is not None else self.units // 2

    def _advance(self, glyph: int) -> int:
        return self.advances[min(glyph, len(self.advances) - 1)]

    @staticmethod
    def _read_cmap(data: bytes, base: int) -> dict[int, int]:
        count = struct.unpack(">H", data[base + 2 : base + 4])[0]
        best: tuple[int, int] | None = None  # (format, offset)
        for index in range(count):
            platform, encoding, offset = struct.unpack(">HHI", data[base + 4 + 8 * index : base + 12 + 8 * index])
            if platform not in (0, 3):
                continue
            fmt = struct.unpack(">H", data[base + offset : base + offset + 2])[0]
            if fmt in (4, 12) and (best is None or fmt > best[0]):
                best = (fmt, base + offset)
        mapping: dict[int, int] = {}
        if best is None:
            return mapping
        fmt, table = best
        if fmt == 12:
            groups = struct.unpack(">I", data[table + 12 : table + 16])[0]
            for index in range(groups):
                start, end, glyph = struct.unpack(">III", data[table + 16 + 12 * index : table + 28 + 12 * index])
                for code in range(start, end + 1):
                    mapping[code] = glyph + code - start
            return mapping
        segments = struct.unpack(">H", data[table + 6 : table + 8])[0] // 2
        ends = table + 14
        starts = ends + 2 * segments + 2
        deltas = starts + 2 * segments
        ranges = deltas + 2 * segments
        for index in range(segments):
            end = struct.unpack(">H", data[ends + 2 * index : ends + 2 * index + 2])[0]
            start = struct.unpack(">H", data[starts + 2 * index : starts + 2 * index + 2])[0]
            delta = struct.unpack(">h", data[deltas + 2 * index : deltas + 2 * index + 2])[0]
            range_offset = struct.unpack(">H", data[ranges + 2 * index : ranges + 2 * index + 2])[0]
            for code in range(start, min(end, 0xFFFE) + 1):
                if range_offset == 0:
                    glyph = (code + delta) & 0xFFFF
                else:
                    at = ranges + 2 * index + range_offset + 2 * (code - start)
                    glyph = struct.unpack(">H", data[at : at + 2])[0]
                    if glyph:
                        glyph = (glyph + delta) & 0xFFFF
                if glyph:
                    mapping[code] = glyph
        return mapping

    def line_height_em(self) -> float:
        return (self.ascent - self.descent) / self.units

    def width_em(self, text: str) -> float:
        total = 0
        for char in text:
            glyph = self.cmap.get(ord(char))
            total += self._advance(glyph) if glyph is not None else self.fallback
        return total / self.units

"""Phân tích video mẫu để tạo template giao diện.

Luồng (xem docs/ANALYZE.md):

    video mẫu ──media──► frame + audio
                 │
                 ├─frames─► cắt cảnh, nền, bảng màu
                 ├─text───► OCR: phụ đề, watermark, màu chữ
                 └─audio──► độ ồn, nhạc nền
                       │
                  measure ──► analysis.json (số đo, JSON-able)
                       │
                   infer ───► config/templates/<id>.json
                       │
                 compare ───► render project mẫu bằng template, đo lại, so với video mẫu

Mỗi tầng chỉ nhận/trả dữ liệu thuần nên test được bằng dữ liệu giả.
"""

# Nguồn SFX

SFX trong pipeline là **sound effect thật tải từ Mixkit**, không tổng hợp bằng
numpy/scipy. Build chỉ copy asset cục bộ nên render không cần mạng.

> **Whoosh đã bị bỏ** theo yêu cầu: không dùng trong video, không còn trong
> `config/sfx.json`, `assets/sfx/` hay schema.

## File đang dùng

| File | Nội dung | Nguồn | Giấy phép |
|---|---|---|---|
| `assets/sfx/tick.wav` | Cool interface click tone (Mixkit #2568) | https://mixkit.co/free-sound-effects/click/ · tải trực tiếp: https://assets.mixkit.co/active_storage/sfx/2568/2568.wav | Mixkit Sound Effects Free License |

Tải ngày **2026-10-21**. Danh mục và âm lượng mặc định nằm ở `config/sfx.json`.

Giấy phép: https://mixkit.co/license/modal/sfxFree/ — cho phép dùng miễn phí
trong cả dự án thương mại và phi thương mại (YouTube, social, quảng cáo, phim,
game, broadcast…), **không bắt buộc ghi công**. Không được bán lại/redistribute
SFX như một asset độc lập, như stock, template hoặc kèm source file.

## Cách chuẩn hoá `tick.wav`

- Cắt 0,12 s đầu của bản gốc.
- Resample 44,1 → 48 kHz.
- Fade-out 30 ms.
- Chuẩn hoá đỉnh −5 dBFS.

## Ứng viên click khác (để nghe thử)

Các file trong `assets/sfx/candidates/` là bản tải gốc, chưa xử lý:

- `221-positive-interface-beep.wav` — beep hai nốt, dễ bị "game" quá.
- `2568-cool-interface-click-tone.wav` — bản gốc của tick đang dùng.
- `2577-interface-device-click.wav` — click bén, có đuôi, hợp UI.
- `3124-modern-technology-select.wav` — click rất ngắn, khá nhỏ.

Mở `assets/sfx/audition.html` để nghe trực tiếp. Muốn đổi âm mặc định: thay
`assets/sfx/tick.wav` bằng file đã chuẩn hoá 48 kHz, hoặc thêm item mới vào
`config/sfx.json` rồi trỏ `file` tới asset tương ứng.

## Ghi công

Không bắt buộc. Nếu muốn ghi trong mô tả video:

> SFX: Mixkit (mixkit.co) — Mixkit Sound Effects Free License

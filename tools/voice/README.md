# Công cụ giọng đọc

Các script trong thư mục này là **công cụ dev**, không thuộc pipeline chính.
Chúng dùng chung adapter trong `pipeline/voice/` và đọc `config/brand.json`
hoặc brand của từng kênh trong `config/brands/`.

| Script | Việc |
|---|---|
| `make_voice_ref.py` | Sinh ứng viên giọng OmniVoice cho brand mặc định, khoá mẫu, kiểm tra f0 |
| `make_channel_voice.py` | Sinh/khoá giọng OmniVoice riêng cho một brand/kênh bất kỳ |
| `check_providers.py` | Đọc thử một câu bằng provider được chọn |
| `test_vieneu.py` | Liệt kê / thử 25 giọng VieNeu |

## Khoá giọng OmniVoice riêng cho kênh

```powershell
$env:PYTHONUTF8=1

# Sinh 4 ứng viên bằng design mode, in thời lượng + f0
.\.venv\Scripts\python.exe -u tools\voice\make_channel_voice.py `
    --brand config\brands\english-learner-1218.json --candidates 4

# Nghe out/voice-samples/english-learner-1218/voice-*.wav,
# chọn một file rồi khoá vào brand
.\.venv\Scripts\python.exe -u tools\voice\make_channel_voice.py `
    --brand config\brands\english-learner-1218.json `
    --lock 1 --name englishlearner
```

Sau khi khoá, brand chuyển sang `mode: "clone"` và trỏ tới
`assets/voice/omnivoice-<name>.wav`, nên mọi scene của kênh dùng đúng một
giọng. Không dùng chung file mẫu giữa hai kênh nếu muốn hai giọng khác nhau.

## Giọng tiếng Việt cho kênh song ngữ

Kênh dạy tiếng Anh có giải thích tiếng Việt nên cần hai giọng: một giọng đọc
tiếng Anh và một giọng đọc tiếng Việt. Có hai lựa chọn:

1. **VieNeu preset** (khuyến nghị cho tiếng Việt): cố định bằng `voiceId`, chạy
   ONNX CPU, không cần clone file ngoài.

   ```json
   "voices": {
     "vi": {
       "provider": "vieneu",
       "vieneu": { "voiceId": "Mai Anh", "language": "vi" }
     }
   }
   ```

   Xem danh sách preset:

   ```powershell
   .\.venv\Scripts\python.exe -u -m pipeline.tts --list-voices --provider vieneu
   ```

2. **OmniVoice riêng**: sinh một mẫu tiếng Việt do model tạo, khoá thành file
   trong `assets/voice/`, rồi thêm `voices.vi` với `provider: "omnivoice"` và
   `refAudio`/`refText` tương ứng. Cách này giữ toàn bộ kênh trên một engine
   nhưng cần kiểm tra kỹ chất lượng tiếng Việt.

`EnglishLearner1218` hiện dùng cách 1: OmniVoice cho tiếng Anh, VieNeu
`Mai Anh` cho tiếng Việt. Không dùng `mode=auto` cho video nhiều scene vì model
có thể đổi giọng giữa các lần generate.

## Khoá giọng OmniVoice mặc định

```powershell
$env:PYTHONUTF8=1

# Sinh 4 ứng viên, in thời lượng + f0
.\.venv\Scripts\python.exe -u tools\voice\make_voice_ref.py --candidates 4

# Nghe tools/voice/out/samples/*.wav, chọn một file rồi khoá
.\.venv\Scripts\python.exe -u tools\voice\make_voice_ref.py `
    --lock tools/voice/out/samples/voice-2.wav --name nam

# Kiểm tra độ ổn định f0 giữa các câu
.\.venv\Scripts\python.exe -u tools\voice\make_voice_ref.py --test
```

Kết quả khoá: `assets/voice/omnivoice-nam.wav`. Không nhân bản giọng người
ngoài; mẫu phải do chính model sinh ra.

## Kiểm tra provider

```powershell
.\.venv\Scripts\python.exe -u tools\voice\check_providers.py `
    --provider omnivoice --mode clone --out tools\voice\out\check-omni.wav

.\.venv\Scripts\python.exe -u tools\voice\test_vieneu.py --all
```

## Lưu ý

- OmniVoice cần **CUDA**; nếu không thấy GPU, pipeline dừng. Chỉ đặt
  `OMNIVOICE_DEVICE=cpu` khi debug.
- VieNeu xuất 48 kHz; khi transcribe thử phải resample về 16 kHz, nếu không
  Whisper sẽ nghe sai.
- `tools/voice/out/` là output tạm, có thể xoá.
- Không commit file giọng mẫu thay thế nếu không rõ nguồn/giấy phép.

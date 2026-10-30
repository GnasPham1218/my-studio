from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from . import config, paths, review
from .progress import Progress
from .voice import PROVIDERS, get_provider, resolve_spec, voice_config

ROOT = Path(__file__).resolve().parent.parent

# Khoảng lặng mặc định giữa hai đoạn khác ngôn ngữ trong cùng một scene.
DEFAULT_SEGMENT_PAUSE_MS = 180.0

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(  # type: ignore[attr-defined]
            encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_key(text: str, fingerprint: str) -> str:
    raw = f"{fingerprint}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def normalize(audio: np.ndarray, target_dbfs: float, peak_dbfs: float) -> np.ndarray:
    """Đưa RMS về mức mục tiêu, chặn đỉnh để không bị clip."""
    audio = np.asarray(audio, dtype=np.float32)
    rms = float(np.sqrt(np.mean(audio**2)) + 1e-9)
    audio = audio * (10 ** (target_dbfs / 20) / rms)

    peak = float(np.max(np.abs(audio)))
    ceiling = 10 ** (peak_dbfs / 20)
    if peak > ceiling:
        audio = audio * (ceiling / peak)
    return audio


def resample(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate:
        return audio
    import soxr

    return np.asarray(soxr.resample(audio, source_rate, target_rate), dtype=np.float32)


def pad(audio: np.ndarray, sample_rate: int, lead: float, tail: float) -> np.ndarray:
    return np.concatenate(
        [
            np.zeros(int(lead * sample_rate), dtype=np.float32),
            audio,
            np.zeros(int(tail * sample_rate), dtype=np.float32),
        ]
    )


def spec_label(provider_name: str, spec: dict[str, Any]) -> str:
    if provider_name == "vieneu":
        return str(spec.get("voiceId") or "mặc định")
    if provider_name == "omnivoice":
        mode = str(spec.get("mode") or "auto")
        detail = spec.get("refAudio") if mode == "clone" else spec.get("instruct")
        return f"{mode}{f' · {detail}' if detail else ''}"
    return provider_name


def build_spec(
    brand_voice: dict[str, Any],
    provider_name: str,
    args: argparse.Namespace,
    *,
    apply_voice_overrides: bool = True,
) -> dict[str, Any]:
    spec = resolve_spec(brand_voice, provider_name)
    if apply_voice_overrides:
        if args.voice:
            spec["voiceId"] = args.voice
        if args.mode:
            spec["mode"] = args.mode
        if args.ref_audio:
            spec["refAudio"] = args.ref_audio
        if args.ref_text:
            spec["refText"] = args.ref_text
        if args.instruct:
            spec["instruct"] = args.instruct
    # Tốc độ và số bước có thể áp dụng cho mọi giọng.
    if args.speed:
        spec["speed"] = args.speed
    if args.num_step:
        spec["numStep"] = args.num_step
    return spec


def scene_segments(scene: dict[str, Any], script_language: str) -> list[dict[str, Any]]:
    """Trả về các đoạn đọc của scene.

    `segments` cho phép trộn tiếng Việt/Anh trong cùng scene. Scene cũ chỉ có
    `narration` vẫn chạy như trước, dùng `scene.language` hoặc ngôn ngữ script.
    """
    raw = scene.get("segments") or []
    if raw:
        result: list[dict[str, Any]] = []
        for segment in raw:
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            result.append(
                {
                    "language": str(
                        segment.get("language")
                        or scene.get("language")
                        or script_language
                    ),
                    "text": text,
                    "pauseAfterMs": float(
                        segment.get("pauseAfterMs", DEFAULT_SEGMENT_PAUSE_MS)
                    ),
                }
            )
        if result:
            return result

    return [
        {
            "language": str(scene.get("language") or script_language),
            "text": str(scene.get("narration") or "").strip(),
            "pauseAfterMs": 0.0,
        }
    ]


def plan_cache_key(segments: list[dict[str, Any]]) -> str:
    payload = [
        {
            "language": segment["language"],
            "text": segment["text"],
            "provider": segment["provider"],
            "fingerprint": segment["fingerprint"],
            "pauseAfterMs": segment["pauseAfterMs"],
        }
        for segment in segments
    ]
    return cache_key(
        json.dumps(payload, ensure_ascii=False, sort_keys=True), "multi-voice"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.tts",
        description="Sinh voiceover cho từng scene bằng engine TTS local (VieNeu / OmniVoice).",
    )
    parser.add_argument("--project-id", help="Bắt buộc, trừ khi dùng --list-voices")
    parser.add_argument("--format", choices=config.format_ids(), help="Mặc định tự dò")
    parser.add_argument("--provider", choices=PROVIDERS, help="Mặc định lấy từ brand.json")
    parser.add_argument("--voice", help="[vieneu] Tên giọng preset")
    parser.add_argument("--mode", choices=["auto", "design", "clone"], help="[omnivoice] Kiểu giọng")
    parser.add_argument("--ref-audio", help="[omnivoice] File WAV mẫu để clone giọng")
    parser.add_argument("--ref-text", help="[omnivoice] Lời thoại đúng của file mẫu")
    parser.add_argument("--instruct", help="[omnivoice] Mô tả giọng cho chế độ design")
    parser.add_argument("--speed", type=float, help="[omnivoice] Hệ số tốc độ (>1 nhanh hơn)")
    parser.add_argument("--num-step", type=int, help="[omnivoice] Số bước giải mã (mặc định 32)")
    parser.add_argument("--list-voices", action="store_true", help="In danh sách giọng rồi thoát")
    parser.add_argument("--force", action="store_true", help="Bỏ qua cache")
    parser.add_argument("--only", help="Chỉ sinh các scene này, ví dụ: s01,s02")
    parser.add_argument(
        "--unapproved",
        action="store_true",
        help="Chạy nháp khi script chưa được duyệt (pipeline.review)",
    )
    args = parser.parse_args(argv)

    pid = args.project_id
    # --list-voices có thể chạy không cần project: dùng brand mặc định.
    brand = (
        paths.load_brand(pid)
        if pid
        else json.loads((ROOT / "config" / "brand.json").read_text(encoding="utf-8"))
    )

    default_voice = voice_config(brand, None)
    provider_name = args.provider or default_voice.get("provider") or "vieneu"
    spec = build_spec(default_voice, provider_name, args)
    provider = get_provider(provider_name)
    provider.fingerprint(spec)  # kiểm tra spec sớm; cache key tính theo từng đoạn

    if provider_name == "omnivoice" and (spec.get("mode") or "auto") == "auto":
        print(
            "  ! mode=auto: model có thể đổi cả giọng nam/nữ giữa các scene.\n"
            "    Khoá một giọng cố định bằng: python tools/voice/make_voice_ref.py --lock <file> --name <tên>",
            flush=True,
        )

    if args.list_voices:
        print(f"Giọng của {provider_name}:")
        for voice in provider.list_voices():
            print(f"  - {voice}")
        return 0

    if not args.project_id:
        parser.error("--project-id là bắt buộc")

    fmt = args.format or paths.detect_format(pid)
    if not fmt:
        raise SystemExit(
            f"Không thấy scripts/short.json hay scripts/long.json trong "
            f"{paths.rel(paths.source_dir(pid))}"
        )

    review.require_approved(pid, fmt, bypass=args.unapproved)
    script = load_json(paths.script_path(pid, fmt))
    paths.snapshot(pid)
    audio_cfg = brand["audio"]
    sample_rate = int(audio_cfg["sampleRate"])
    script_language = str(script.get("meta", {}).get("language") or "vi")

    only = {s.strip() for s in args.only.split(",")} if args.only else None

    # Mỗi format có thư mục audio riêng: short và long không ghi đè file của nhau.
    audio_dir = paths.audio_dir(pid, fmt)
    audio_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = paths.manifest_path(pid, fmt)
    manifest: dict[str, Any] = (
        load_json(manifest_path) if manifest_path.exists() else {"scenes": {}}
    )

    # Script bớt scene thì bỏ entry + wav cũ, nếu không totalSec bị cộng thừa.
    # Với --only chỉ chạy một phần nên không biết chắc scene nào đã bị xoá.
    pruned: list[str] = []
    if not only:
        current_ids = {s["id"] for s in script["scenes"]}
        pruned = [sid for sid in manifest["scenes"] if sid not in current_ids]
        for sid in pruned:
            manifest["scenes"].pop(sid)
            paths.audio_path(pid, fmt, sid).unlink(missing_ok=True)
        if pruned:
            print(f"  · bỏ {len(pruned)} scene không còn trong script: {', '.join(pruned)}")

    scenes = [s for s in script["scenes"] if not only or s["id"] in only]
    provider_objects: dict[str, Any] = {}

    def get_provider_object(name: str):
        if name not in provider_objects:
            provider_objects[name] = get_provider(name)
        return provider_objects[name]

    plans: list[dict[str, Any]] = []
    for scene in scenes:
        segments: list[dict[str, Any]] = []
        for segment in scene_segments(scene, script_language):
            language = segment["language"]
            lang_voice = voice_config(brand, language)
            segment_provider = str(
                args.provider
                if language == script_language and args.provider
                else lang_voice.get("provider") or default_voice.get("provider") or "vieneu"
            )
            # CLI --voice/--mode/--ref-* chỉ áp dụng cho ngôn ngữ mặc định;
            # giọng của ngôn ngữ khác phải lấy đúng từ brand.voices.
            segment_spec = build_spec(
                lang_voice,
                segment_provider,
                args,
                apply_voice_overrides=language == script_language,
            )
            segment_provider_obj = get_provider_object(segment_provider)
            segments.append(
                {
                    **segment,
                    "provider": segment_provider,
                    "spec": segment_spec,
                    "fingerprint": segment_provider_obj.fingerprint(segment_spec),
                }
            )

        plans.append(
            {
                "scene": scene,
                "segments": segments,
                "key": plan_cache_key(segments),
            }
        )

    def is_cached(plan: dict[str, Any]) -> bool:
        sid = plan["scene"]["id"]
        previous = manifest["scenes"].get(sid)
        return bool(
            not args.force
            and previous
            and previous.get("hash") == plan["key"]
            and paths.audio_path(pid, fmt, sid).exists()
        )

    if plans and all(is_cached(plan) for plan in plans):
        if pruned:
            manifest["totalSec"] = round(
                sum(entry["durationSec"] for entry in manifest["scenes"].values()), 2
            )
            write_json(manifest_path, manifest)
        print(f"  · {len(plans)} scene đã có trong cache, không cần nạp model")
        print(f"  · tổng {manifest.get('totalSec', 0):.1f}s audio")
        return 0

    # Chỉ nạp các provider thật sự cần cho scene chưa cache.
    loaded_providers: dict[str, Any] = {}
    for plan in plans:
        if is_cached(plan):
            continue
        for segment in plan["segments"]:
            name = segment["provider"]
            if name in loaded_providers:
                continue
            started = time.perf_counter()
            print(
                f"Nạp {name} (giọng: {spec_label(name, segment['spec'])})…"
            )
            provider_obj = get_provider_object(name)
            provider_obj.load()
            loaded_providers[name] = provider_obj
            print(f"Nạp xong sau {time.perf_counter() - started:.1f}s\n")

    # Ước lượng độ dài audio để ETA có ý nghĩa ngay từ scene đầu.
    # Tốc độ nói thật đo được nằm ở config/formats.json (wordsPerSecond).
    estimated = (
        sum(
            len(segment["text"].split())
            for plan in plans
            for segment in plan["segments"]
        )
        / config.words_per_second()
    )

    total_audio = 0.0
    total_time = 0.0
    synthesized = 0
    done_audio = 0.0

    bar = Progress(estimated, "TTS", unit="giây audio")

    for index, plan in enumerate(plans, start=1):
        scene = plan["scene"]
        sid = scene["id"]
        segments = plan["segments"]
        target = paths.audio_path(pid, fmt, sid)

        if is_cached(plan):
            previous_duration = float(manifest["scenes"][sid]["durationSec"])
            done_audio += previous_duration
            total_audio += previous_duration
            bar.set(
                done_audio,
                detail=f"{sid} · cache · {index}/{len(plans)} scene",
                total=max(estimated, done_audio),
            )
            continue

        started = time.perf_counter()
        pieces: list[np.ndarray] = []
        segment_entries: list[dict[str, Any]] = []
        cursor_samples = 0
        for segment_index, segment in enumerate(segments):
            provider_obj = loaded_providers[segment["provider"]]
            audio = provider_obj.synthesize(segment["text"], segment["spec"])
            audio = resample(audio, provider_obj.sampleRate, sample_rate)
            audio = normalize(audio, audio_cfg["targetDbfs"], audio_cfg["peakDbfs"])

            start_sec = cursor_samples / sample_rate
            duration_sec = len(audio) / sample_rate
            segment_entries.append(
                {
                    "text": segment["text"],
                    "language": segment["language"],
                    "startSec": round(start_sec, 3),
                    "durationSec": round(duration_sec, 3),
                    "endSec": round(start_sec + duration_sec, 3),
                    "provider": segment["provider"],
                    "spec": segment["spec"],
                }
            )
            pieces.append(audio)
            cursor_samples += len(audio)

            if segment_index < len(segments) - 1 and segment["pauseAfterMs"] > 0:
                gap_samples = int(round(segment["pauseAfterMs"] / 1000 * sample_rate))
                if gap_samples > 0:
                    pieces.append(np.zeros(gap_samples, dtype=np.float32))
                    cursor_samples += gap_samples

        scene_audio = (
            np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        )
        scene_audio = pad(
            scene_audio,
            sample_rate,
            audio_cfg["leadInSec"],
            audio_cfg["tailOutSec"],
        )
        lead = float(audio_cfg["leadInSec"])
        for entry in segment_entries:
            entry["startSec"] = round(entry["startSec"] + lead, 3)
            entry["endSec"] = round(entry["endSec"] + lead, 3)

        sf.write(target, scene_audio, sample_rate, subtype="PCM_16")

        elapsed = time.perf_counter() - started
        duration = len(scene_audio) / sample_rate
        total_audio += duration
        total_time += elapsed
        synthesized += 1
        done_audio += duration

        providers_used = {segment["provider"] for segment in segments}
        entry = {
            "file": target.relative_to(ROOT).as_posix(),
            "hash": plan["key"],
            "durationSec": round(duration, 3),
            "chars": sum(len(segment["text"]) for segment in segments),
            "provider": next(iter(providers_used)) if len(providers_used) == 1 else "mixed",
            "spec": segments[0]["spec"] if segments else spec,
        }
        if len(segments) > 1:
            entry["segments"] = segment_entries
        manifest["scenes"][sid] = entry

        rtf = elapsed / duration if duration else 0
        languages = "+".join(dict.fromkeys(segment["language"] for segment in segments))
        bar.set(
            done_audio,
            detail=(
                f"{sid} · {duration:.2f}s · {languages} · RTF {rtf:.2f} "
                f"· {index}/{len(plans)} scene"
            ),
            total=max(estimated, done_audio),
        )

    voices_used: dict[str, dict[str, Any]] = {}
    for plan in plans:
        for segment in plan["segments"]:
            voices_used.setdefault(
                segment["language"],
                {"provider": segment["provider"], "spec": segment["spec"]},
            )

    default_segment = next(
        (
            segment
            for plan in plans
            for segment in plan["segments"]
            if segment["language"] == script_language
        ),
        plans[0]["segments"][0] if plans and plans[0]["segments"] else None,
    )
    if default_segment is not None:
        manifest["voice"] = {
            "provider": default_segment["provider"],
            "spec": default_segment["spec"],
        }
    if len(voices_used) > 1:
        manifest["voices"] = voices_used
    else:
        manifest.pop("voices", None)

    manifest["format"] = fmt
    manifest["provider"] = (
        next(iter({v["provider"] for v in voices_used.values()}))
        if len(voices_used) == 1
        else "mixed"
    )
    manifest["sampleRate"] = sample_rate
    manifest["totalSec"] = round(
        sum(entry["durationSec"] for entry in manifest["scenes"].values()), 2
    )
    write_json(manifest_path, manifest)
    bar.close()

    print(
        f"\n✓ {synthesized} scene mới · {total_audio:.1f}s audio · "
        f"{total_time:.1f}s xử lý · tổng {manifest['totalSec']:.1f}s"
    )
    print(f"  manifest: {paths.rel(manifest_path)}")
    paths.update_status(
        pid,
        voice=manifest.get("voice"),
        voices=manifest.get("voices"),
        audio={fmt: {"scenes": len(manifest["scenes"]), "totalSec": manifest["totalSec"]}},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

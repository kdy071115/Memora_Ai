"""음성 강의 → 트랜스크립트 + 자동 요약/챕터 분리.

faster-whisper 를 우선 시도하고, 설치되어 있지 않으면 명시적 에러를 던진다.
모델은 'base' (영어/한국어 모두 적당한 정확도, CPU 1-2x 실시간) 를 기본으로 사용.
"""

import json
import logging
import os
import re
import tempfile
from typing import List, Tuple

from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.audio_summary import AUDIO_SUMMARY_PROMPT
from app.models.schemas import AudioTranscribeResponse, AudioChapter

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.4,
    max_tokens=2048,
)

# faster-whisper 는 의존성이 무겁고 모델 다운로드 시간이 길어 lazy import
_whisper_model = None
_whisper_model_size = os.environ.get("WHISPER_MODEL_SIZE", "base")


def _get_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "faster-whisper 가 설치되어 있지 않습니다. "
            "`pip install faster-whisper` 후 서버를 재시작하세요."
        ) from e

    logger.info("[whisper] 모델 로딩 시작 size=%s", _whisper_model_size)
    # CPU int8 — Apple Silicon 포함 대부분 환경에서 잘 동작
    _whisper_model = WhisperModel(_whisper_model_size, device="cpu", compute_type="int8")
    logger.info("[whisper] 모델 로딩 완료")
    return _whisper_model


def transcribe(file_bytes: bytes, language_hint: str | None = "ko") -> AudioTranscribeResponse:
    model = _get_model()

    # faster-whisper 는 파일 경로를 받기 때문에 임시 파일에 쓴다
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=True) as tmp:
        tmp.write(file_bytes)
        tmp.flush()

        segments_iter, info = model.transcribe(
            tmp.name,
            language=language_hint,
            beam_size=1,
            vad_filter=True,
        )

        segments: List[Tuple[float, str]] = []  # (startSec, text)
        for seg in segments_iter:
            segments.append((float(seg.start), seg.text.strip()))

    duration = float(getattr(info, "duration", 0.0))
    full_transcript = " ".join(s[1] for s in segments)

    if not full_transcript.strip():
        return AudioTranscribeResponse(
            fullTranscript="",
            summary="음성에서 텍스트를 추출하지 못했어요. 더 깨끗한 음원으로 다시 시도해주세요.",
            chapters=[],
            durationSec=duration,
        )

    # AI 요약 + 챕터 분리
    summary, chapters = _summarize_with_ai(full_transcript, segments, duration)

    return AudioTranscribeResponse(
        fullTranscript=full_transcript,
        summary=summary,
        chapters=chapters,
        durationSec=duration,
    )


def _summarize_with_ai(
    transcript: str,
    segments: List[Tuple[float, str]],
    duration: float,
) -> tuple[str, List[AudioChapter]]:
    # 트랜스크립트가 너무 길면 컷
    snippet = transcript[:12000]
    prompt = AUDIO_SUMMARY_PROMPT.format(transcript=snippet)

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error("[whisper] 요약 LLM 호출 실패: %s", e)
        return ("## 강의 요약\n\n자동 요약에 실패했습니다. 트랜스크립트는 그대로 확인할 수 있어요.", [])

    parsed = _parse_json(response.content)
    if parsed is None:
        return ("## 강의 요약\n\n응답 파싱에 실패했어요.", [])

    summary = str(parsed.get("summary", ""))
    chapters: List[AudioChapter] = []
    for c in parsed.get("chapters", []) or []:
        try:
            chapters.append(
                AudioChapter(
                    title=str(c.get("title", "")),
                    startSec=float(c.get("startSec", 0.0)),
                    summary=str(c.get("summary", "")),
                )
            )
        except Exception:
            continue
    return summary, chapters


def _parse_json(text):
    if text is None:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", str(text).strip())
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None

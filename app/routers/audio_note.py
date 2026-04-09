from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models.schemas import AudioTranscribeResponse
from app.services import audio_note_service

router = APIRouter(prefix="/ai/audio-note", tags=["AudioNote"])


@router.post("/transcribe", response_model=AudioTranscribeResponse)
async def transcribe(
    file: UploadFile = File(...),
    languageHint: str = Form("ko"),
) -> AudioTranscribeResponse:
    """강의 음성 파일 → faster-whisper 트랜스크립션 + AI 요약 + 챕터 분리."""
    try:
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail="빈 파일입니다.")
        return audio_note_service.transcribe(data, language_hint=languageHint)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"transcribe 실패: {e}")

import base64
import json
import logging
import re
from langchain_anthropic import ChatAnthropic

from app.config import settings
from app.prompts.assignment_feedback import ASSIGNMENT_FEEDBACK_PROMPT
from app.models.schemas import AssignmentFeedbackRequest, AssignmentFeedbackResponse
from app.utils.pdf_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)

llm = ChatAnthropic(
    model=settings.llm_model,
    api_key=settings.anthropic_api_key,
    temperature=0.4,
    max_tokens=2048,
)

# 너무 큰 첨부는 잘라서 모델 컨텍스트를 보호
MAX_ATTACHMENT_CHARS = 12000


def evaluate(req: AssignmentFeedbackRequest) -> AssignmentFeedbackResponse:
    logger.info(
        "과제 피드백 시작 student=%s submission_len=%d has_attachment=%s",
        req.studentName,
        len(req.submissionContent or ""),
        bool(req.attachmentBase64),
    )

    attachment_text = _read_attachment(req.attachmentName, req.attachmentBase64)
    if attachment_text and len(attachment_text) > MAX_ATTACHMENT_CHARS:
        attachment_text = attachment_text[:MAX_ATTACHMENT_CHARS] + "\n... (이하 생략)"

    if not (req.submissionContent or "").strip() and not attachment_text:
        return _empty_submission_response()

    prompt = ASSIGNMENT_FEEDBACK_PROMPT.format(
        assignment_title=req.assignmentTitle or "(제목 없음)",
        assignment_description=req.assignmentDescription or "(과제 안내 없음)",
        student_name=req.studentName or "학생",
        submission_content=(req.submissionContent or "").strip() or "(본문이 비어 있습니다)",
        attachment_text=attachment_text or "(첨부 본문 없음)",
    )

    try:
        response = llm.invoke(prompt)
    except Exception as e:
        logger.error("과제 피드백 LLM 호출 실패: %s", e)
        return _fallback("AI 호출에 실패했어요. 잠시 후 다시 시도해주세요.")

    parsed = _parse_json(response.content)
    if parsed is None:
        logger.warning("과제 피드백 JSON 파싱 실패. raw 앞부분: %s", str(response.content)[:300])
        return _fallback("AI 응답 형식을 해석하지 못했어요. 다시 시도해주세요.")

    try:
        return AssignmentFeedbackResponse(
            overallScore=int(parsed.get("overallScore", 0)),
            grade=parsed.get("grade", "AVERAGE"),
            summary=str(parsed.get("summary", "")),
            strengths=list(parsed.get("strengths", [])),
            improvements=list(parsed.get("improvements", [])),
            missingPoints=list(parsed.get("missingPoints", [])),
            suggestions=list(parsed.get("suggestions", [])),
            instructorDraft=str(parsed.get("instructorDraft", "")),
        )
    except Exception as e:
        logger.error("과제 피드백 응답 매핑 실패: %s", e)
        return _fallback("AI 응답을 정리하는 중 문제가 생겼어요.")


def _read_attachment(name: str | None, b64: str | None) -> str:
    if not b64:
        return ""
    try:
        raw = base64.b64decode(b64)
    except Exception as e:
        logger.warning("첨부 base64 디코딩 실패: %s", e)
        return ""

    lower = (name or "").lower()
    if lower.endswith(".pdf"):
        try:
            pages = extract_text_from_pdf(raw)
            return "\n\n".join(f"[p.{i}] {t}" for i, t in pages)
        except Exception as e:
            logger.warning("PDF 추출 실패: %s", e)
            return ""
    # 텍스트 류
    if lower.endswith((".txt", ".md", ".csv", ".json", ".html", ".htm")):
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""
    # 알 수 없는 바이너리는 패스 (Word/PPT 등은 향후 별도 파서 필요)
    return ""


def _empty_submission_response() -> AssignmentFeedbackResponse:
    return AssignmentFeedbackResponse(
        overallScore=0,
        grade="NEEDS_WORK",
        summary="제출 본문과 첨부 모두 비어 있어 평가할 내용이 없습니다.",
        strengths=[],
        improvements=["과제 안내에 따라 본문 또는 첨부 파일을 작성해 다시 제출하세요."],
        missingPoints=[],
        suggestions=["과제 주제를 다시 한 번 확인하고, 본인의 생각을 글로 정리해 보세요."],
        instructorDraft="아직 제출 내용이 비어 있어요. 과제 안내를 다시 읽어보고 본문 또는 첨부를 채워 다시 제출해 주세요. 어떤 부분이 어렵다면 언제든 알려주세요!",
    )


def _fallback(message: str) -> AssignmentFeedbackResponse:
    return AssignmentFeedbackResponse(
        overallScore=0,
        grade="NEEDS_WORK",
        summary=message,
        strengths=[],
        improvements=[],
        missingPoints=[],
        suggestions=[],
        instructorDraft="",
    )


def _parse_json(text: str):
    if text is None:
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
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

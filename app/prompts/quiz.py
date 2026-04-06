QUIZ_PROMPT = """당신은 교육 평가 전문가입니다.
아래 강의 내용을 기반으로 학습 확인용 문제를 생성하세요.

[강의 내용]
{lecture_content}

[요청 사항]
- 문제 수: {count}개
- 유형: {quiz_types}
- 난이도: {difficulty}
- 관련 개념: {concept_tags}

각 문제는 다음 JSON 형식의 배열로 출력하세요. 다른 설명은 포함하지 마세요:
[
  {{
    "question": "문제 텍스트",
    "quizType": "MULTIPLE_CHOICE | SHORT_ANSWER | ESSAY",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correctAnswer": "정답",
    "explanation": "해설",
    "conceptTag": "관련 개념",
    "difficulty": "{difficulty}"
  }}
]

규칙:
- 단순 암기가 아닌 이해를 확인하는 문제를 출제하세요.
- 객관식 선택지는 그럴듯한 오답을 포함하세요.
- 서술형/주관식의 경우 options는 null로 설정하세요.
- 해설은 왜 정답인지, 왜 오답인지 설명하세요.
- 반드시 유효한 JSON 배열만 출력하세요.
"""

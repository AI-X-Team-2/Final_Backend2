# app/schemas.py
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr
from datetime import datetime


# =========================
# 공용 타입
# =========================
FeedbackType = Literal["basic", "real_life"]


# =========================
# 사용자 스키마
# =========================
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserDelete(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: int
    username: str
    email: EmailStr
    max_stage: Optional[int] = None
    max_step: Optional[int] = None
    max_level: Optional[int] = None

    class Config:
        from_attributes = True  # pydantic v2


# =========================
# 음절 단위 상세 피드백 (SyllableFeedback)
# =========================
class SyllableFeedbackCreate(BaseModel):
    syllable: str                      # 예: "바", "ㅂ+ㅏ"
    correct_syllable: str
    wrong_initial: Optional[str] = None
    wrong_medial: Optional[str] = None
    wrong_final: Optional[str] = None
    mouth_shape_feedback: Optional[str] = None
    tongue_shape_feedback: Optional[str] = None
    breath_feedback: Optional[str] = None
    image_url: Optional[str] = None
    answer_video_url: Optional[str] = None

class SyllableFeedbackOut(BaseModel):
    syllable_feedback_id: int
    syllable: str
    correct_syllable: str
    wrong_initial: Optional[str] = None
    wrong_medial: Optional[str] = None
    wrong_final: Optional[str] = None
    mouth_shape_feedback: Optional[str] = None
    tongue_shape_feedback: Optional[str] = None
    breath_feedback: Optional[str] = None
    image_url: Optional[str] = None
    answer_video_url: Optional[str] = None

    class Config:
        from_attributes = True


# =========================
# 타입별 1:1 상세 (Basic / RealLife)
# =========================
class BasicPronunciationFeedbackCreate(BaseModel):
    score: int
    pronounced_word: str
    problem_word: str

class RealLifePronunciationFeedbackCreate(BaseModel):
    score: int
    pronounced_word: str
    problem_word: str

class BasicPronunciationFeedbackOut(BaseModel):
    feedback_id: int
    score: int
    pronounced_word: str
    problem_word: str

    class Config:
        from_attributes = True

class RealLifePronunciationFeedbackOut(BaseModel):
    feedback_id: int
    score: int
    pronounced_word: str
    problem_word: str

    class Config:
        from_attributes = True


# =========================
# 상위 FEEDBACK (부모)
# =========================
class FeedbackCreate(BaseModel):
    """
    피드백 생성용 입력 스키마.
    1) Feedback 레코드 생성 (feedback_type 지정)
    2) 타입별 상세(basic/real_life) 1:1 내용
    3) 하위 음절 상세들(0개 이상)
    """
    user_id: int
    feedback_type: FeedbackType

    # 타입별 1:1 상세 (둘 중 하나만 채우는 걸 컨트롤러/서비스에서 보장)
    basic: Optional[BasicPronunciationFeedbackCreate] = None
    real_life: Optional[RealLifePronunciationFeedbackCreate] = None

    # 음절 상세(선택)
    syllable_feedbacks: Optional[List[SyllableFeedbackCreate]] = None


class FeedbackOut(BaseModel):
    feedback_id: int
    user_id: int
    feedback_type: FeedbackType
    created_at: Optional[datetime] = None  # ISO 문자열로 직렬화됨

    # 타입별 1:1 상세
    basic: Optional[BasicPronunciationFeedbackOut] = None
    real_life: Optional[RealLifePronunciationFeedbackOut] = None

    # 하위 음절 상세들
    syllable_feedbacks: List[SyllableFeedbackOut] = []

    class Config:
        from_attributes = True


# =========================
# (선택) 발음 분석 응답 포맷
#  - 서비스 레이어에서 분석 결과를 즉시 내려줄 때 사용
#  - DB 스키마와 1:1 매핑은 아님
# =========================
class PronunciationFeedback(BaseModel):
    wrong_text: str
    expected: str
    teaching_point: str
    correct_img_url: Optional[str] = None
    correct_video_url: Optional[str] = None
    mouth_feedback: str
    tongue_position_feedback: str
    breathing_feedback: str

class PronunciationAnalysisResponse(BaseModel):
    score: int                 # 점수는 숫자형이 자연스러워서 int 권장
    my_text: str               # 사용자가 실제로 말한 텍스트
    target_word: str           # 목표/문제 단어
    incorrect_points: List[PronunciationFeedback]

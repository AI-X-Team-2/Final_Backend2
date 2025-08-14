# app/schemas.py
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr
from datetime import datetime

# =========================
# 공용 타입
# =========================
FeedbackType = Literal["basic", "real_life"]

# =========================
# 사용자 스키마 (변경 없음)
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
    max_stage: Optional[int] = 0
    max_step: Optional[int] = 0
    max_level: Optional[int] = 0

    class Config:
        from_attributes = True  # pydantic v2


# =========================
# 음절 단위 상세 피드백 (SyllableFeedback)
#  - 모델에 없는 wrong_* 필드는 제거
# =========================
class SyllableFeedbackCreate(BaseModel):
    syllable: str
    correct_syllable: str
    mouth_shape_feedback: Optional[str] = None
    tongue_shape_feedback: Optional[str] = None
    breath_feedback: Optional[str] = None
    image_url: Optional[str] = None
    answer_video_url: Optional[str] = None

class SyllableFeedbackOut(BaseModel):
    syllable_feedback_id: int
    syllable: str
    correct_syllable: str
    mouth_shape_feedback: Optional[str] = None
    tongue_shape_feedback: Optional[str] = None
    breath_feedback: Optional[str] = None
    image_url: Optional[str] = None
    answer_video_url: Optional[str] = None

    class Config:
        from_attributes = True


# =========================
# 단일 1:1 상세 (PronunciationFeedback)
#  - 기존 basic/real_life 2종을 통합
# =========================
class PronunciationIn(BaseModel):
    score: int
    pronounced_word: str
    problem_word: str

class PronunciationOut(BaseModel):
    feedback_id: int
    score: int
    pronounced_word: str
    problem_word: str

    class Config:
        from_attributes = True


# =========================
# 상위 FEEDBACK (부모)
#  - basic / real_life 대신 pronunciation 1개만 둠
# =========================
class FeedbackCreate(BaseModel):
    """
    1) Feedback(feedback_type) 생성
    2) pronunciation(1:1) 선택 생성
    3) syllable_feedbacks(0..N) 선택 생성
    """
    user_id: int
    feedback_type: FeedbackType                   # "basic" | "real_life"
    pronunciation: Optional[PronunciationIn] = None
    syllable_feedbacks: Optional[List[SyllableFeedbackCreate]] = None

class FeedbackOut(BaseModel):
    feedback_id: int
    user_id: int
    feedback_type: FeedbackType
    created_at: Optional[datetime] = None

    pronunciation: Optional[PronunciationOut] = None
    syllable_feedbacks: List[SyllableFeedbackOut] = []

    class Config:
        from_attributes = True


# =========================
# (선택) 발음 분석 응답 포맷
#  - 서비스 레이어의 즉시 응답용 (DB 스키마와 1:1은 아님)
#  - 모델 클래스명과 헷갈리지 않게 이름을 바꾸는 것을 권장
# =========================
class AnalysisPoint(BaseModel):  # ← 이전 이름: PronunciationFeedback (혼동 방지 변경)
    wrong_text: str
    expected: str
    teaching_point: str
    correct_img_url: Optional[str] = None
    correct_video_url: Optional[str] = None
    mouth_feedback: str
    tongue_position_feedback: str
    breathing_feedback: str

class PronunciationAnalysisResponse(BaseModel):
    score: int
    my_text: str
    target_word: str
    incorrect_points: List[AnalysisPoint]

# -------- 응답 스키마(필요한 3개만) --------
class ProgressOut(BaseModel):
    max_stage: Optional[int] = 0
    max_step: Optional[int] = 0
    max_level: Optional[int] = 0
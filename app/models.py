# app/models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Enum, DateTime, Text
)
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from app.database import Base

# =========================
# USERS
# =========================
class User(Base):
    __tablename__ = "users"

    user_id   = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username  = Column(String(50), unique=True, nullable=False)
    email     = Column(String(100), unique=True, nullable=False)
    password  = Column(String(255), nullable=False)

    # 학습 진행도
    max_stage = Column(Integer)   # 최대 진행 stage
    max_step  = Column(Integer)   # 최대 진행 step
    max_level = Column(Integer)   # 최대 진행 level

    # 하나의 유저는 여러 피드백을 가질 수 있음
    feedbacks = relationship(
        "Feedback",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================
# FEEDBACK (상위 엔티티)
# =========================
class Feedback(Base):
    __tablename__ = "feedback"

    feedback_id   = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type = Column(
        Enum("basic", "real_life", name="feedback_type_enum"),
        nullable=False
    )
    created_at    = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    user = relationship("User", back_populates="feedbacks")

    # 1:N (자모 단위 피드백)
    syllable_feedbacks = relationship(
        "SyllableFeedback",
        back_populates="feedback",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 1:1 (피드백 타입별 상세)
    basic = relationship(
        "BasicPronunciationFeedback",
        back_populates="feedback",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    real_life = relationship(
        "RealLifePronunciationFeedback",
        back_populates="feedback",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================
# SYLLABLE_FEEDBACK (1:N)
# =========================
class SyllableFeedback(Base):
    __tablename__ = "syllable_feedback"

    syllable_feedback_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feedback_id          = Column(Integer, ForeignKey("feedback.feedback_id", ondelete="CASCADE"), nullable=False, index=True)

    # 자모/정답/오류 위치
    syllable         = Column(String(50),  nullable=False)   # 예: "바", "ㅂ+ㅏ"
    correct_syllable = Column(String(50),  nullable=False)
    wrong_initial    = Column(String(50))                     # 초성 오류
    wrong_medial     = Column(String(50))                     # 중성 오류
    wrong_final      = Column(String(50))                     # 종성 오류

    # 가이드/피드백
    mouth_shape_feedback  = Column(Text)
    tongue_shape_feedback = Column(Text)
    breath_feedback       = Column(Text)

    # 참고 리소스
    image_url        = Column(String(255))
    answer_video_url = Column(String(255))

    feedback = relationship("Feedback", back_populates="syllable_feedbacks")


# =========================
# BASIC_PRONUNCIATION_FEEDBACK (1:1)
# =========================
class BasicPronunciationFeedback(Base):
    __tablename__ = "basic_pronunciation_feedback"

    # FEEDBACK와 1:1 매핑 (feedback_id가 PK이자 FK)
    feedback_id     = Column(Integer, ForeignKey("feedback.feedback_id", ondelete="CASCADE"), primary_key=True)
    score           = Column(Integer, nullable=False)
    pronounced_word = Column(String(100), nullable=False)
    problem_word    = Column(String(100), nullable=False)

    feedback = relationship("Feedback", back_populates="basic", uselist=False)


# =========================
# REAL_LIFE_PRONUNCIATION_FEEDBACK (1:1)
# =========================
class RealLifePronunciationFeedback(Base):
    __tablename__ = "real_life_pronunciation_feedback"

    # FEEDBACK와 1:1 매핑 (feedback_id가 PK이자 FK)
    feedback_id     = Column(Integer, ForeignKey("feedback.feedback_id", ondelete="CASCADE"), primary_key=True)
    score           = Column(Integer, nullable=False)
    pronounced_word = Column(String(100), nullable=False)
    problem_word    = Column(String(100), nullable=False)

    feedback = relationship("Feedback", back_populates="real_life", uselist=False)



class PronunciationData(Base):
    __tablename__ = "pronunciation_data"

    id          = Column(Integer, primary_key=True, index=True)
    hangul_char = Column(String(255), unique=True, index=True, nullable=False)
    image_url   = Column(String(255), nullable=True)
    video_url   = Column(String(255), nullable=True)

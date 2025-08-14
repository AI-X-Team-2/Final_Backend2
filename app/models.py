# app/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, Text, Index
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from app.database import Base


# =========================
# USERS
# =========================
class User(Base):
    __tablename__ = "users"

    user_id   = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username  = Column(String(50), unique=True, nullable=False)   # 아이디=닉네임
    email     = Column(String(100), unique=True, nullable=False)
    password  = Column(String(255), nullable=False)

    # 학습 진행도
    max_stage = Column(Integer, default=0)   # 최대 진행 stage
    max_step  = Column(Integer, default=0)   # 최대 진행 step
    max_level = Column(Integer, default=0)   # 최대 진행 level

    # 1:N Feedback
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
    feedback_type = Column(Enum("basic", "real_life", name="feedback_type_enum"), nullable=False)
    created_at    = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))

    # 인덱스 (user_id, feedback_type)
    __table_args__ = (Index("ix_feedback_user_type", "user_id", "feedback_type"),)

    user = relationship("User", back_populates="feedbacks")

    # 1:N (자모 단위 피드백)
    syllable_feedbacks = relationship(
        "SyllableFeedback",
        back_populates="feedback",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 1:1 (상세 점수/단어) - 단일 테이블
    pronunciation = relationship(
        "PronunciationFeedback",
        back_populates="feedback",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# =========================
# PRONUNCIATION_FEEDBACK (1:1)
# =========================
class PronunciationFeedback(Base):
    __tablename__ = "pronunciation_feedback"

    # FEEDBACK와 1:1 매핑 (feedback_id가 PK이자 FK)
    feedback_id     = Column(Integer, ForeignKey("feedback.feedback_id", ondelete="CASCADE"), primary_key=True)
    score           = Column(Integer, nullable=False)
    pronounced_word = Column(String(100), nullable=False)
    problem_word    = Column(String(100), nullable=False)

    feedback = relationship("Feedback", back_populates="pronunciation", uselist=False)


# =========================
# SYLLABLE_FEEDBACK (1:N)
# =========================
class SyllableFeedback(Base):
    __tablename__ = "syllable_feedback"

    syllable_feedback_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    feedback_id          = Column(Integer, ForeignKey("feedback.feedback_id", ondelete="CASCADE"), nullable=False, index=True)

    # 정답/오류 위치
    syllable         = Column(String(50),  nullable=False)   # 예: "바", "ㅂ+ㅏ"
    correct_syllable = Column(String(50),  nullable=False)

    # 가이드/피드백
    mouth_shape_feedback  = Column(Text)
    tongue_shape_feedback = Column(Text)
    breath_feedback       = Column(Text)

    # 참고 리소스
    image_url        = Column(String(255))
    answer_video_url = Column(String(255))

    feedback = relationship("Feedback", back_populates="syllable_feedbacks")


# =========================
# 그대로 유지 요청한 테이블
# =========================
class PronunciationData(Base):
    __tablename__ = "pronunciation_data"

    id          = Column(Integer, primary_key=True, index=True)
    hangul_char = Column(String(255), unique=True, index=True, nullable=False)
    image_url   = Column(String(255), nullable=True)
    video_url   = Column(String(255), nullable=True)


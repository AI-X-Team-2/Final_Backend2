from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, CheckConstraint, text, Boolean
from sqlalchemy.sql import func, expression
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON as MYSQL_JSON, BIGINT as MYSQL_BIGINT, CHAR

from app.database import Base
from app.utils.utils import generate_code

# =========================
# USERS
# =========================
class User(Base):
    __tablename__ = "users"

    user_id  = Column(MYSQL_BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email    = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    # ❌ server_default 제거, ✅ ORM 기본값 사용
    max_level = Column(
        MYSQL_JSON,
        nullable=False,
        default=lambda: [1],   # INSERT 시 SQLAlchemy가 자동으로 [1] 넣어줌
    )

# =========================
# 발음 가이드(참고)
# =========================
class PronunciationData(Base):
    __tablename__ = "pronunciation_data"

    id          = Column(MYSQL_BIGINT(unsigned=True), primary_key=True, index=True, autoincrement=True)
    hangul_char = Column(String(255), unique=True, index=True, nullable=False)
    image_url   = Column(String(255), nullable=True)
    video_url   = Column(String(255), nullable=True)

# ================================
# 학습 세션 (learning_sessions)
# ================================
class StudySession(Base):
    __tablename__ = "study_sessions"

    session_id = Column(CHAR(8), primary_key=True, default=generate_code, comment="세션 고유 ID")
    user_id    = Column(MYSQL_BIGINT(unsigned=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    learning_type  = Column(String(20), nullable=True)  # e.g. daily/basic
    total_words    = Column(Integer, nullable=False, default=0)
    status         = Column(String(20), nullable=False, server_default="in_progress")
    created_at     = Column(DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    completed_at   = Column(DateTime(timezone=True), nullable=True)

    # ✅ level: JSON 배열로 저장 (예: [0], [1,2])
    level = Column(
        MYSQL_JSON,
        nullable=False,
        default=lambda: [0],   # INSERT 시 [0]
        comment="학습 레벨 리스트(JSON). 요청의 level(int)을 [level]로 변환해 저장"
    )

    isPassed = Column(Boolean, nullable=False, server_default=expression.false(), comment="통과 여부")

    __table_args__ = (
        CheckConstraint("total_words >= 0", name="ck_session_total_words_non_negative"),
    )

    feedbacks = relationship(
        "StudyFeedback",
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

# ================================
# 학습 결과 (learning_results)
# ================================
class StudyResult(Base):
    __tablename__ = "study_results"

    result_id  = Column(MYSQL_BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="결과 고유 ID")
    session_id = Column(CHAR(8), ForeignKey("study_sessions.session_id", ondelete="CASCADE"),
                        nullable=False, comment="세션 ID")
    score      = Column(Integer, nullable=False, comment="해당 단어 점수")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="학습 시작 시각")

    __table_args__ = (
        CheckConstraint("score >= 0", name="check_score_non_negative"),
    )

# ================================
# 학습 피드백 (learning_feedbacks)
# ================================
class StudyFeedback(Base):
    __tablename__ = "study_feedbacks"

    id         = Column(MYSQL_BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="피드백 고유 ID")
    session_id = Column(CHAR(8), ForeignKey("study_sessions.session_id", ondelete="CASCADE"),
                        nullable=False, comment="세션 ID")
    score      = Column(Integer, nullable=False, comment="채점 점수")
    mouth_feedback            = Column(Text, nullable=True, comment="입 모양 피드백")
    tongue_position_feedback  = Column(Text, nullable=True, comment="혀 위치 피드백")
    breathing_feedback        = Column(Text, nullable=True, comment="호흡 피드백")
    teaching_point            = Column(Text, nullable=True, comment="학습 포인트")

    __table_args__ = (
        CheckConstraint("score >= 0", name="check_feedback_score_non_negative"),
    )

    session = relationship("StudySession", back_populates="feedbacks")

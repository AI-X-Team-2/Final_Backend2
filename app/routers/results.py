# app/routers/feedback.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload, selectinload
from app.database import get_db
from app.models import (
    Feedback,
    SyllableFeedback,
    BasicPronunciationFeedback,
    RealLifePronunciationFeedback,
)
from app.schemas import (
    FeedbackCreate,
    FeedbackOut,
)
from typing import List

router = APIRouter()

# 생성: 상위 Feedback + (타입별 1:1) + (음절 상세들 0..N)
@router.post("/feedbacks", response_model=FeedbackOut)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)):
    # 1) 부모 생성
    fb = Feedback(user_id=payload.user_id, feedback_type=payload.feedback_type)
    db.add(fb)
    db.flush()  # feedback_id 확보

    # 2) 타입별 1:1 상세
    if payload.feedback_type == "basic":
        if not payload.basic:
            raise HTTPException(status_code=400, detail="basic payload is required for feedback_type=basic")
        b = BasicPronunciationFeedback(
            feedback_id=fb.feedback_id,
            **payload.basic.model_dump(exclude_none=True),
        )
        db.add(b)

    elif payload.feedback_type == "real_life":
        if not payload.real_life:
            raise HTTPException(status_code=400, detail="real_life payload is required for feedback_type=real_life")
        r = RealLifePronunciationFeedback(
            feedback_id=fb.feedback_id,
            **payload.real_life.model_dump(exclude_none=True),
        )
        db.add(r)

    # 3) 음절 상세(선택)
    if payload.syllable_feedbacks:
        for sf in payload.syllable_feedbacks:
            db.add(SyllableFeedback(
                feedback_id=fb.feedback_id,
                **sf.model_dump(exclude_none=True),
            ))

    db.commit()

    # 4) 응답용으로 관계까지 로드해서 반환
    fb_full = (
        db.query(Feedback)
          .options(
              joinedload(Feedback.basic),
              joinedload(Feedback.real_life),
              selectinload(Feedback.syllable_feedbacks),
          )
          .filter(Feedback.feedback_id == fb.feedback_id)
          .one()
    )
    return fb_full


# 조회: 특정 유저의 모든 피드백 목록
@router.get("/feedbacks/user/{user_id}", response_model=List[FeedbackOut])
def list_user_feedbacks(user_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Feedback)
          .options(
              joinedload(Feedback.basic),
              joinedload(Feedback.real_life),
              selectinload(Feedback.syllable_feedbacks),
          )
          .filter(Feedback.user_id == user_id)
          .order_by(Feedback.created_at.desc())
          .all()
    )
    return rows


# (선택) 단건 조회
@router.get("/feedbacks/{feedback_id}", response_model=FeedbackOut)
def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    fb = (
        db.query(Feedback)
          .options(
              joinedload(Feedback.basic),
              joinedload(Feedback.real_life),
              selectinload(Feedback.syllable_feedbacks),
          )
          .filter(Feedback.feedback_id == feedback_id)
          .first()
    )
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb

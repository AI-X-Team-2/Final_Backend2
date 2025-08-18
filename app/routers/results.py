from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db

from app.auth import get_current_user, CurrentUser
from app.models import StudySession
from app.schemas import PracticeSessionCreate, PracticeSessionCreateResponse


router = APIRouter()

@router.post("/practice-sessions", response_model=PracticeSessionCreateResponse, status_code=status.HTTP_201_CREATED)
def create_practice_session(
    payload: PracticeSessionCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    # ✅ 서버 단 검증
    level_int = int(payload.level)
    if level_int < 0:
        raise HTTPException(status_code=400, detail="level은 0 이상이어야 합니다.")
    if payload.total_words < 0:
        raise HTTPException(status_code=400, detail="total_words는 0 이상이어야 합니다.")

    session_row = StudySession(
        user_id=current_user.user_id,
        learning_type=payload.mode,
        total_words=payload.total_words,
        status="in_progress",
        level=[level_int],                 # ✅ JSON 배열로 저장
    )

    db.add(session_row)
    db.commit()
    db.refresh(session_row)

    return PracticeSessionCreateResponse(session_id=session_row.session_id)
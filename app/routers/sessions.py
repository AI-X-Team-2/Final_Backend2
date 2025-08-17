from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import StudySession, StudyResult, User   # ✅ StudyResult 추가
from app.auth import get_current_user
from app.schemas import StudySessionOut

router = APIRouter()

@router.patch("/{session_id}/complete", response_model=StudySessionOut, status_code=status.HTTP_200_OK)
def complete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 내 세션 조회
    session = (
        db.query(StudySession)
        .filter(
            StudySession.session_id == session_id,
            StudySession.user_id == current_user.user_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없거나 권한이 없습니다.")

    # ✅ 점수 집계: 해당 세션의 결과물 기준
    total_cnt = (
        db.query(func.count(StudyResult.result_id))
        .filter(StudyResult.session_id == session_id)
        .scalar()
    ) or 0

    perfect_cnt = (
        db.query(func.count(StudyResult.result_id))
        .filter(
            StudyResult.session_id == session_id,
            StudyResult.score == 100
        )
        .scalar()
    ) or 0

    is_passed_bool = perfect_cnt > (total_cnt / 2)  # "절반 초과" (strictly greater)

    # ✅ 완료 처리 + 통과 여부 저장
    if session.status != "completed":
        session.status = "completed"
        session.completed_at = func.now()

    # ⚠️ 현재 컬럼 타입이 String(10)이라면 문자열로 저장하는 편이 안전
    #    (가능하면 Boolean으로 마이그레이션 권장 – 아래 참고)
    try:
        # 만약 컬럼을 Boolean으로 바꿨다면: session.isPassed = is_passed_bool
        session.isPassed = "true" if is_passed_bool else "false"
    except Exception:
        session.isPassed = "true" if is_passed_bool else "false"

    db.add(session)
    db.commit()
    db.refresh(session)

    # 응답은 bool로 반환 (스키마가 bool이면 더 안전)
    return StudySessionOut(
        session_id=session.session_id,
        user_id=session.user_id,
        status=session.status,
        created_at=session.created_at,
        completed_at=session.completed_at,
        total_words=session.total_words,
        level=session.level,
        isPassed=is_passed_bool,  # ✅ bool로 반환
    )

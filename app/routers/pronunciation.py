# api/pronunciation.py (수정 후)
# API 엔드포인트를 정의하고, 서비스 로직 함수들을 호출합니다.

from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends # Depends 임포트
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db 
from app.schemas import PronunciationAnalysisResponse
from app.services.analysis_service import analyze_user_pronunciation, transcribe_audio_for_minigame


# API 라우터 객체를 생성합니다.
router = APIRouter()

@router.post("/analyze", response_model=PronunciationAnalysisResponse, tags=["Pronunciation Analysis"])
async def analyze_pronunciation_endpoint(

    target_sentence: str = Form(...),
    audio_file: UploadFile = File(...),
    session_id: str | None = Form(None),  # ★ 추가: 세션 ID(없으면 저장 스킵)
    isReview: bool = Form(False),  # ★ 추가: 리뷰 여부
    db: Session = Depends(get_db)
):
    try:
        # ★ session_id 전달
        response_data = await analyze_user_pronunciation(target_sentence, audio_file, db, session_id=session_id, is_review=isReview)
        return JSONResponse(content=response_data)
    except Exception as e:
        print(f"발음 분석 중 심각한 오류 발생: {e}")

        raise HTTPException(status_code=500, detail=f"서버에서 오디오 파일을 처리하는 중 오류가 발생했습니다: {str(e)}")

@router.post("/transcribe_audio", tags=["Minigame"])
async def transcribe_audio_for_minigame_endpoint(audio: UploadFile = File(...)):
    """
    오디오 파일을 받아 텍스트로 변환하는 간단한 STT 기능입니다.
    미니게임 등 실시간 텍스트 변환이 필요할 때 사용합니다.
    """
    try:
        return await transcribe_audio_for_minigame(audio)
    except Exception as e:
        print(f"미니게임 STT 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 처리 중 서버 오류 발생: {str(e)}")

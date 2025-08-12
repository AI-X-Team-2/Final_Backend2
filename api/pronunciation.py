# api/pronunciation.py
# API 엔드포인트를 정의하고, 서비스 로직 함수들을 호출합니다.

from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from models.pronunciation import PronunciationAnalysisResponse
from services.analysis_service import analyze_user_pronunciation, transcribe_audio_for_minigame
from fastapi import APIRouter, File, UploadFile
import shutil
import uuid
from fastapi.responses import FileResponse
from fastapi import BackgroundTasks
from services.video_service import isolate_mouth_from_video, TEMP_VIDEO_DIR
import os
# API 라우터 객체를 생성합니다.
router = APIRouter()

@router.post("/analyze", response_model=PronunciationAnalysisResponse, tags=["Pronunciation Analysis"])
async def analyze_pronunciation_endpoint(target_sentence: str = Form(...), audio_file: UploadFile = File(...)):
    """사용자의 발음을 분석하고, 틀린 글자별 상세 피드백을 반환합니다."""
    try:
        response_data = await analyze_user_pronunciation(target_sentence, audio_file)
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
    
    
@router.post("/upload_video", tags=["Video Processing"])
async def process_video_endpoint(background_tasks: BackgroundTasks, video_file: UploadFile = File(...)):
    """
    사용자 영상을 받아 입 모양만 추출한 영상을 반환합니다.
    """
    # 임시 파일로 저장
    temp_input_path = os.path.join(TEMP_VIDEO_DIR, f"{uuid.uuid4()}_{video_file.filename}")
    with open(temp_input_path, "wb") as buffer:
        shutil.copyfileobj(video_file.file, buffer)

    processed_video_path = None
    try:
        # 비디오 처리 서비스 호출
        processed_video_path = isolate_mouth_from_video(temp_input_path)
        if not processed_video_path:
            raise HTTPException(status_code=500, detail="영상 처리 중 오류가 발생했습니다.")
        
        # 처리된 파일을 응답으로 보내고, 응답이 완료된 후 파일을 삭제하도록 예약
        background_tasks.add_task(os.remove, processed_video_path)
        return FileResponse(path=processed_video_path, media_type="video/webm", filename="mouth_video.webm")

    finally:
        # 원본 임시 파일 삭제
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
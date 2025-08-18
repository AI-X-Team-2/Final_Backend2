# app/routers/video.py
import os
import shutil
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.services.video_service import isolate_mouth_from_video, TEMP_VIDEO_DIR

router = APIRouter()

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
# main.py
# FastAPI 앱을 실행하는 진입점입니다.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# API 라우터, 서비스 로직, 설정 파일에서 필요한 항목들을 임포트합니다.
from api.pronunciation import router as pronunciation_router

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# FastAPI 앱 생성 및 설정
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터를 메인 앱에 포함시킵니다.
app.include_router(pronunciation_router)

# 정적 파일(이미지)을 서빙할 경로를 마운트합니다.
app.mount("/static/images", StaticFiles(directory="static/images"), name="static_images")

# 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "의사소통 보조 AI 유음"}
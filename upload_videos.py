# upload_videos.py (Images + Videos to Cloudinary)

import os
import csv
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

from app.database import SessionLocal
from app.models import PronunciationData
from app.utils.hangul import decompose_hangul
from app.core.config import IMAGE_GUIDE_MAP  # 자모음→이미지 파일명 매핑

load_dotenv()

# --- Cloudinary ---
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# 로컬 파일 폴더 (원본 영상/이미지 위치)
VIDEO_LOCAL_DIR = os.getenv("VIDEO_LOCAL_DIR", "videos_to_upload")
IMAGE_LOCAL_DIR = os.getenv("IMAGE_LOCAL_DIR", "static/images")  # 기존에 쓰던 경로 그대로 사용

# 입력 CSV
MAPPING_FILE = os.getenv("MAPPING_FILE", "mapping.csv")

db = SessionLocal()

def upsert_pronunciation_data(hangul_char: str, video_url: str | None, image_url: str | None):
    row = db.query(PronunciationData).filter(PronunciationData.hangul_char == hangul_char).first()
    if not row:
        row = PronunciationData(hangul_char=hangul_char)
        db.add(row)
    if video_url:
        row.video_url = video_url
    if image_url:
        row.image_url = image_url
    db.commit()

def upload_cloudinary(local_path: str, public_id: str, resource_type: str):
    """
    resource_type: "video" or "image"
    """
    return cloudinary.uploader.upload(
        local_path,
        public_id=public_id,
        resource_type=resource_type,
        overwrite=True,         # 동일 public_id면 덮어쓰기
        unique_filename=False,  # public_id 그대로 사용
    )

def upload_and_save_all_data():
    if not os.path.exists(MAPPING_FILE):
        print(f"[오류] {MAPPING_FILE} 파일을 찾을 수 없습니다.")
        return

    with open(MAPPING_FILE, mode="r", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            hangul_char = (row.get("hangul_char") or "").strip()
            video_filename = (row.get("video_filename") or "").strip()

            if not hangul_char or not video_filename:
                print(f"[경고] CSV 데이터 부족: {row}")
                continue

            print(f"\n=== '{hangul_char}' 처리 시작 ===")

            # ---------- 1) 비디오 업로드 ----------
            video_path = os.path.join(VIDEO_LOCAL_DIR, video_filename)
            if not os.path.exists(video_path):
                print(f"[경고] 비디오 파일 없음: {video_path} (건너뜀)")
                video_url = None
            else:
                try:
                    print(f" -> 비디오 업로드: {video_path}")
                    vres = upload_cloudinary(
                        video_path,
                        public_id=f"pronunciation_videos/{os.path.splitext(video_filename)[0]}",
                        resource_type="video",
                    )
                    video_url = vres.get("secure_url")
                    print(f" -> 비디오 업로드 성공: {video_url}")
                except Exception as e:
                    print(f"[오류] 비디오 업로드 실패: {e}")
                    video_url = None

            # ---------- 2) 이미지 선택 & 업로드 ----------
            # 이미지 파일명은 IMAGE_GUIDE_MAP에서 자모 기준 매핑
            try:
                chosung, jungsung, _ = decompose_hangul(hangul_char)
            except Exception:
                chosung, jungsung = None, None

            image_filename = None
            if chosung and chosung in IMAGE_GUIDE_MAP:
                image_filename = IMAGE_GUIDE_MAP[chosung]
            elif jungsung and jungsung in IMAGE_GUIDE_MAP:
                image_filename = IMAGE_GUIDE_MAP[jungsung]
            else:
                image_filename = "default.png"

            image_path = os.path.join(IMAGE_LOCAL_DIR, image_filename)
            if not os.path.exists(image_path):
                print(f"[경고] 이미지 파일 없음: {image_path} (default.png 시도)")
                # default.png도 없으면 이미지URL 스킵
                if image_filename != "default.png":
                    image_filename = "default.png"
                    image_path = os.path.join(IMAGE_LOCAL_DIR, image_filename)

            if os.path.exists(image_path):
                try:
                    print(f" -> 이미지 업로드: {image_path}")
                    ires = upload_cloudinary(
                        image_path,
                        public_id=f"pronunciation_images/{os.path.splitext(image_filename)[0]}",
                        resource_type="image",
                    )
                    image_url = ires.get("secure_url")
                    print(f" -> 이미지 업로드 성공: {image_url}")
                except Exception as e:
                    print(f"[오류] 이미지 업로드 실패: {e}")
                    image_url = None
            else:
                print(f"[경고] 이미지 파일을 최종적으로 찾지 못함. 이미지 URL 저장 생략.")
                image_url = None

            # ---------- 3) DB 반영 ----------
            try:
                upsert_pronunciation_data(hangul_char, video_url, image_url)
                print(" -> DB 저장 완료")
            except Exception as e:
                db.rollback()
                print(f"[DB 오류] 저장 실패: {e}")

if __name__ == "__main__":
    try:
        upload_and_save_all_data()
    finally:
        db.close()
        print("\n모든 작업이 완료되었습니다.")

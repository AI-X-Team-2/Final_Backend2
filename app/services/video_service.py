import os
import cv2 # OpenCV
import mediapipe as mp 
import uuid # 고유 파일명 생성
import numpy as np

# MediaPipe 얼굴 인식 모델 초기화
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=1)

# 입술 주변의 랜드마크 인덱스 (MediaPipe 기준)
LIP_LANDMARKS = [
    61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291,
    78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308
]

TEMP_VIDEO_DIR = "temp_videos"
os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)


def isolate_mouth_from_video(video_path: str):
    """
    영상 파일 경로를 받아 입 모양만 추출한 새 영상을 생성하고,
    처리된 영상의 경로를 반환합니다.
    """
    output_filename = f"mouth_{uuid.uuid4()}.webm"
    output_path = os.path.join(TEMP_VIDEO_DIR, output_filename)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: 영상을 열 수 없습니다.")
        return None

    # 원본 영상의 속성 가져오기 (너비, 높이, FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # 비디오 작성을 위한 설정 (VP9 코덱 사용, webm 컨테이너)
    fourcc = cv2.VideoWriter_fourcc(*'VP90')
    out = cv2.VideoWriter(output_path, fourcc, fps, (200, 100)) # 입모양 영상 크기 고정 (200x100)

    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            # 성능 향상을 위해 이미지를 읽기 전용으로 표시
            frame.flags.writeable = False
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(image_rgb)
            frame.flags.writeable = True

            # 얼굴 랜드마크가 감지된 경우
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    # 입술 랜드마크 좌표 추출
                    lip_points = [(int(face_landmarks.landmark[i].x * width), int(face_landmarks.landmark[i].y * height)) for i in LIP_LANDMARKS]
                    
                    # 입술 영역의 경계 상자 계산
                    x_coords = [p[0] for p in lip_points]
                    y_coords = [p[1] for p in lip_points]
                    x_min, x_max = min(x_coords), max(x_coords)
                    y_min, y_max = min(y_coords), max(y_coords)
                    
                    # 경계에 여백 추가
                    padding = 20
                    x_min = max(0, x_min - padding)
                    y_min = max(0, y_min - padding)
                    x_max = min(width, x_max + padding)
                    y_max = min(height, y_max + padding)
                    
                    # 프레임에서 입술 부분만 잘라내기
                    mouth_frame = frame[y_min:y_max, x_min:x_max]

                    if mouth_frame.size > 0:
                        # 잘라낸 입술 영상을 고정된 크기로 리사이즈
                        resized_mouth = cv2.resize(mouth_frame, (200, 100))
                        out.write(resized_mouth)
                    else:
                        # 입술이 안보이면 검은 화면 출력
                        out.write(np.zeros((100, 200, 3), dtype=np.uint8)) #  cv2.zeros -> np.zeros 로 수정
            else:
                # 얼굴이 감지 안되면 검은 화면 출력
                 out.write(np.zeros((100, 200, 3), dtype=np.uint8)) # cv2.zeros -> np.zeros 로 수정
    finally:
        cap.release()
        out.release()
        
    return output_path

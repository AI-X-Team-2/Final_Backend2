# =================================================================
# 1. 모든 라이브러리 임포트 (All Library Imports)
# =================================================================
import os
import numpy as np
import noisereduce as nr
import datetime
import json
import io
import soundfile as sf
from pydub import AudioSegment
from openai import OpenAI
from dotenv import load_dotenv
from typing import List

from fastapi import FastAPI, APIRouter, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import torch
from faster_whisper import WhisperModel

# =================================================================
# 2. 환경변수 로드 (Load Environment Variables)
# =================================================================
# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()


# =================================================================
# 3. 유틸리티 함수 (from utils/hangul.py)
# =================================================================
def decompose_hangul(char):
    """한글 음절을 초성, 중성, 종성으로 분해합니다."""
    if '가' <= char <= '힣':
        char_code = ord(char) - ord('가')
        chosung_index = char_code // (21 * 28)
        jungsung_index = (char_code % (21 * 28)) // 28
        jongsung_index = char_code % 28
        CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
        JONGSUNG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        return CHOSUNG[chosung_index], JUNGSUNG[jungsung_index], JONGSUNG[jongsung_index]
    return char, '', ''


# =================================================================
# 4. 설정 (from core/config.py)
# =================================================================
PRONUNCIATION_GUIDES = [
    {"chars": ["ㄱ", "ㄲ", "ㅋ", "ㅇ"], "imageFile": "c-g.png"},
    {"chars": ["ㄴ", "ㄷ", "ㄸ", "ㅌ"], "imageFile": "c-n.png"},
    {"chars": ["ㄹ"], "imageFile": "c-r.png"},
    {"chars": ["ㅁ", "ㅂ", "ㅃ", "ㅍ"], "imageFile": "c-m.png"},
    {"chars": ["ㅅ", "ㅆ", "ㅈ", "ㅉ", "ㅊ"], "imageFile": "c-s.png"},
    {"chars": ["변이음_ㅅ", "변이음_ㅆ"], "imageFile": "c-s-alt.png"},
    {"chars": ["ㅏ"], "imageFile": "v-a.png"},
    {"chars": ["ㅔ", "ㅐ"], "imageFile": "v-e.png"},
    {"chars": ["ㅓ", "ㅗ"], "imageFile": "v-eo.png"},
    {"chars": ["ㅣ", "ㅑ", 'ㅒ', "ㅕ", "ㅖ", "ㅛ", "ㅠ"], "imageFile": "v-i.png"},
    {"chars": ["ㅡ", "ㅜ", "ㅘ", "ㅙ", "ㅚ", "ㅝ", "ㅞ", "ㅟ", "ㅢ"], "imageFile": "v-u.png"}
]
IMAGE_GUIDE_MAP = {char: guide["imageFile"] for guide in PRONUNCIATION_GUIDES for char in guide["chars"]}


# =================================================================
# 5. 데이터 모델 (from models/pronunciation.py)
# =================================================================
class IncorrectPoint(BaseModel):
    expected: str
    actual: str
    img: str
    diff_detail: str
    mouth_shape: str
    tongue_shape: str
    breathing: str

class PronunciationAnalysisResponse(BaseModel):
    score: str
    transcription: str
    incorrect_points: List[IncorrectPoint]


# =================================================================
# 6. 서비스 로직 (from services/analysis_service.py)
# =================================================================
# faster-whisper 'medium' 모델
MODEL_SIZE = "medium"
device = "cuda" if torch.cuda.is_available() else "cpu"
# GPU 사용 시 float16으로 계산하여 속도 향상
compute_type = "float16" if torch.cuda.is_available() else "default"

print(f"Faster Whisper 모델 로드를 시작합니다. 모델 크기: '{MODEL_SIZE}', 장치: {device}, 계산 타입: {compute_type}")

# faster-whisper 모델을 전역으로 로드합니다.
whisper_model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)

print("Faster Whisper 모델 로드 완료!")


# --- 폴더 분리 및 생성 ---
PRONUNCIATION_AUDIO_DIR = "pronunciation_audio_files"
MINIGAME_AUDIO_DIR = "minigame_audio_files"
os.makedirs(PRONUNCIATION_AUDIO_DIR, exist_ok=True)
os.makedirs(MINIGAME_AUDIO_DIR, exist_ok=True)


def _reduce_noise(audio_data, sample_rate):
    print("... 오디오 노이즈 제거를 시작합니다 ...")
    reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=sample_rate, stationary=False, prop_decrease=0.8)
    print("노이즈 제거 완료!")
    return reduced_noise_audio


# 음성 인식 (STT) -> faster-whisper 모델 사용
def _speech_to_text(audio_file_path: str):
    print(f"\nSTT 시작 (faster-whisper): '{audio_file_path}'")
    try:
        if not os.path.exists(audio_file_path):
            print(f"오디오 파일이 존재하지 않습니다: {audio_file_path}")
            return ""

        # 미리 로드해 둔 모델을 사용해 음성을 텍스트로 변환합니다.
        segments, _ = whisper_model.transcribe(audio_file_path, language="ko")
        
        # 인식된 텍스트 조각들을 하나로 합침
        transcription = "".join(segment.text for segment in segments).strip()

        print(f"STT 결과: {transcription}")
        return transcription
    except Exception as e:
        print(f"faster-whisper 모델 처리 중 오류 발생: {e}")
        return ""


def _create_diff_detail(expected_char, actual_char):
    if not actual_char: return "누락된 단어"
    if not expected_char: return "추가된 단어"
    e_cho, e_jung, e_jong = decompose_hangul(expected_char)
    a_cho, a_jung, a_jong = decompose_hangul(actual_char)
    diffs = []
    if a_cho != e_cho: diffs.append(f"초성: {a_cho} → {e_cho}")
    if a_jung != e_jung: diffs.append(f"중성: {a_jung} → {e_jung}")
    if a_jong != e_jong:
        if not a_jong: diffs.append(f"종성: {e_jong} 추가")
        elif not e_jong: diffs.append(f"종성: {a_jong} 제외")
        else: diffs.append(f"종성: {a_jong} → {e_jong}")
    return ", ".join(diffs)

def _evaluate_pronunciation_with_llm(llm_input_pairs):
    if not llm_input_pairs:
        return {"incorrect_points": []}
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        system_prompt = f"""
        당신은 한국어 발음 교정을 전문으로 하는 언어 치료사입니다.
        아래 '분석 요청 목록'에 있는 각 쌍에 대해, 'expected' 글자를 올바르게 발음하기 위한 '입 모양', '혀 위치', '호흡법' 피드백을 쉽고 구체적으로 생성합니다.
        'diff_detail'은 이미 분석된 정확한 정보이므로, 내용을 수정하지 말고 피드백 생성에 참고만 하세요.
        # 출력 지침
        1. 반드시 아래의 JSON 형식으로만 응답해야 합니다.
        2. 점수(score)는 절대 응답에 포함하지 마세요.
        {{
          "incorrect_points": [
            {{ "expected": "목표 글자", "actual": "사용자가 발음한 글자", "diff_detail": "주어진 교정 포인트 그대로", "mouth_shape": "생성된 입 모양 피드백", "tongue_shape": "생성된 혀 위치 피드백", "breathing": "생성된 호흡법 피드백" }}
          ]
        }}
        """
        user_prompt = f"다음은 분석 요청 목록입니다. 이 목록을 바탕으로 위 지시에 따라 JSON을 생성해주세요: {json.dumps(llm_input_pairs, ensure_ascii=False)}"
        response = client.chat.completions.create(model="gpt-4o-mini", response_format={"type": "json_object"}, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
        evaluation_result = json.loads(response.choices[0].message.content)

        print("LLM 피드백 생성 완료! 응답 데이터:", evaluation_result)
        return evaluation_result
    except Exception as e:
        print(f"LLM 평가 중 심각한 오류 발생: {e}")
        return {"incorrect_points": []}


# --- analyze_user_pronunciation 함수 ---
async def analyze_user_pronunciation(target_sentence: str, audio_file: UploadFile):
    audio_content = await audio_file.read()
    audio_stream = io.BytesIO(audio_content)
    audio = AudioSegment.from_file(audio_stream)
    wav_stream = io.BytesIO()
    audio.set_frame_rate(16000).set_channels(1).export(wav_stream, format="wav")
    wav_stream.seek(0)
    audio_data, sample_rate = sf.read(wav_stream)
    
    # 노이즈 제거
    clean_audio_data = _reduce_noise(audio_data, sample_rate) if np.any(audio_data) else audio_data

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 노이즈 제거된 파일을 발음 교정 전용 폴더에 저장
    cleaned_audio_path = os.path.join(PRONUNCIATION_AUDIO_DIR, f"practice_cleaned_{timestamp}.wav")
    sf.write(cleaned_audio_path, clean_audio_data, sample_rate)

    # 노이즈 제거된 파일로 STT 수행
    user_transcript = _speech_to_text(cleaned_audio_path)
    if not user_transcript: user_transcript = ""

    normalized_target = target_sentence.strip()
    normalized_user = user_transcript.strip()

    if normalized_target == normalized_user:
        return {"score": "100", "transcription": normalized_user, "incorrect_points": []}

    total_score = 0
    max_score = len(normalized_target) * 3
    processed_incorrect_points = []
    is_any_meaningful_similarity_found = False

    for i in range(len(normalized_target)):
        expected_char = normalized_target[i]
        actual_char = normalized_user[i] if i < len(normalized_user) else ""

        if expected_char == actual_char:
            total_score += 3
            is_any_meaningful_similarity_found = True
            continue

        e_cho, e_jung, e_jong = decompose_hangul(expected_char)
        a_cho, a_jung, a_jong = decompose_hangul(actual_char)
        char_score = 0
        if e_cho == a_cho:
            char_score += 1
            is_any_meaningful_similarity_found = True
        if e_jung == a_jung:
            char_score += 1
            is_any_meaningful_similarity_found = True
        if e_jong and e_jong == a_jong:
            char_score += 1
            is_any_meaningful_similarity_found = True

        total_score += char_score
        processed_incorrect_points.append({
            "expected": expected_char,
            "actual": actual_char,
            "diff_detail": _create_diff_detail(expected_char, actual_char)
        })

    if len(normalized_user) > len(normalized_target):
        for i in range(len(normalized_target), len(normalized_user)):
            processed_incorrect_points.append({
                "expected": "", "actual": normalized_user[i], "diff_detail": "추가된 단어"
            })

    if not is_any_meaningful_similarity_found and len(normalized_user) >= len(normalized_target):
        final_score = 0
    else:
        final_score = int((total_score / max_score) * 100) if max_score > 0 else 0

    if 0 < final_score < 100:
        llm_input_pairs = [p for p in processed_incorrect_points if p.get("diff_detail") not in ["누락된 단어", "추가된 단어"]]
        if llm_input_pairs:
            llm_analysis = _evaluate_pronunciation_with_llm(llm_input_pairs)
            llm_feedback_map = {(p['expected'], p['actual']): p for p in llm_analysis.get('incorrect_points', [])}
            for point in processed_incorrect_points:
                feedback = llm_feedback_map.get((point['expected'], point['actual']))
                if feedback:
                    point.update({
                        "mouth_shape": feedback.get("mouth_shape", ""),
                        "tongue_shape": feedback.get("tongue_shape", ""),
                        "breathing": feedback.get("breathing", ""),
                    })

    for point in processed_incorrect_points:
        if "mouth_shape" not in point:
            point.update({"mouth_shape": "", "tongue_shape": "", "breathing": ""})
        expected_char = point.get("expected")
        img_filename = "default.png"
        if expected_char:
            if expected_char in IMAGE_GUIDE_MAP:
                img_filename = IMAGE_GUIDE_MAP[expected_char]
            elif '가' <= expected_char <= '힣':
                chosung, jungsung, _ = decompose_hangul(expected_char)
                img_filename = IMAGE_GUIDE_MAP.get(chosung, IMAGE_GUIDE_MAP.get(jungsung, "default.png"))
        point["img"] = img_filename

    response_data = {
        "score": str(final_score),
        "transcription": normalized_user,
        "incorrect_points": processed_incorrect_points
    }
    
    # 발음 교정 파일은 삭제하지 않고 남겨둡니다.
    if not os.path.exists(cleaned_audio_path):
        print(f"경고: 노이즈 제거된 오디오 파일이 이미 삭제되었거나 존재하지 않습니다: {cleaned_audio_path}")

    return response_data

# =================================================================
# 7. API 라우터 및 경로 정의 (from routes/pronunciation.py)
# =================================================================
router = APIRouter()

@router.get("/")
async def root():
    return {"message": "의사소통 보조 AI 유음"}

@router.post("/analyze", response_model=PronunciationAnalysisResponse, tags=["Pronunciation Analysis"])
async def analyze_pronunciation_endpoint(target_sentence: str = Form(...), audio_file: UploadFile = File(...)):
    """사용자의 발음을 분석하고, 틀린 글자별 상세 피드백을 반환합니다."""
    try:
        response_data = await analyze_user_pronunciation(target_sentence, audio_file)
        return JSONResponse(content=response_data)
    except Exception as e:
        print(f"발음 분석 중 심각한 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"서버에서 오디오 파일을 처리하는 중 오류가 발생했습니다: {str(e)}")
    
# --- transcribe_audio_for_minigame 함수 ---
@router.post("/transcribe_audio", tags=["Minigame"])
async def transcribe_audio_for_minigame(audio: UploadFile = File(...)):
    """
    오디오 파일을 받아 텍스트로 변환하는 간단한 STT 기능입니다.
    미니게임 등 실시간 텍스트 변환이 필요할 때 사용합니다.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="오디오 파일이 없습니다.")

    # 임시 파일 경로 생성
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 미니게임 전용 폴더에 오디오 파일 저장
    temp_filepath = os.path.join(MINIGAME_AUDIO_DIR, f"minigame_audio_{timestamp}.wav")

    try:
        # 전송된 오디오 파일을 임시 저장
        with open(temp_filepath, "wb") as f:
            content = await audio.read()
            f.write(content)
        print(f"미니게임용 오디오 저장 완료: {temp_filepath}")

        # 노이즈 제거 없이 원본 파일로 바로 STT 수행
        segments, info = whisper_model.transcribe(temp_filepath, beam_size=5, language="ko")
        transcription = "".join(segment.text for segment in segments).strip()

        print(f"미니게임 STT 결과: {transcription}")

        return {"transcription": transcription}

    except Exception as e:
        print(f"미니게임 STT 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 처리 중 서버 오류 발생: {str(e)}")
    
    
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/images", StaticFiles(directory="static/images"), name="static_images")
app.include_router(router)
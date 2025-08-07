# services/analysis_service.py
# 음성 파일 처리, STT, LLM 평가 등 핵심 비즈니스 로직을 담고 있습니다.

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

import torch
from faster_whisper import WhisperModel
from fastapi import HTTPException
from app.utils.hangul import decompose_hangul

from sqlalchemy.orm import Session
from app.models import PronunciationData
# from app.core.config import IMAGE_GUIDE_MAP


# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()


# === 모델 로드 및 설정 ===
MODEL_SIZE = "medium"
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if torch.cuda.is_available() else "default"

print(f"Faster Whisper 모델 로드를 시작합니다. 모델 크기: '{MODEL_SIZE}', 장치: {device}, 계산 타입: {compute_type}")
whisper_model = WhisperModel(MODEL_SIZE, device=device, compute_type=compute_type)
print("Faster Whisper 모델 로드 완료!")


# --- 폴더 분리 및 생성 ---
# 음성 파일 저장 폴더를 정의하고 생성합니다.
PRONUNCIATION_AUDIO_DIR = "pronunciation_audio_files"
MINIGAME_AUDIO_DIR = "minigame_audio_files"
os.makedirs(PRONUNCIATION_AUDIO_DIR, exist_ok=True)
os.makedirs(MINIGAME_AUDIO_DIR, exist_ok=True)


def _reduce_noise(audio_data, sample_rate):
    """오디오 데이터의 노이즈를 제거합니다."""
    print("... 오디오 노이즈 제거를 시작합니다 ...")
    reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=sample_rate, stationary=False, prop_decrease=0.8)
    print("노이즈 제거 완료!")
    return reduced_noise_audio


def _speech_to_text(audio_file_path: str):
    """지정된 오디오 파일 경로에서 음성 인식(STT)을 수행합니다."""
    print(f"\nSTT 시작 (faster-whisper): '{audio_file_path}'")
    try:
        if not os.path.exists(audio_file_path):
            print(f"오디오 파일이 존재하지 않습니다: {audio_file_path}")
            return ""

        segments, _ = whisper_model.transcribe(audio_file_path, language="ko")
        transcription = "".join(segment.text for segment in segments).strip()
        print(f"STT 결과: {transcription}")
        return transcription
    except Exception as e:
        print(f"faster-whisper 모델 처리 중 오류 발생: {e}")
        return ""


def _create_diff_detail(expected_char, actual_char):
    """예상 글자와 실제 발음 글자의 차이를 분석하여 상세 정보를 생성합니다."""
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
    """LLM을 사용하여 발음 교정 피드백을 생성합니다."""
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
            {{ "expected": "목표 글자", "actual": "사용자가 발음한 글자", "diff_detail": "주어진 교정 포인트 그대로", "mouth_feedback": "생성된 입 모양 피드백", "tongue_position_feedback": "생성된 혀 위치 피드백", "breathing_feedback": "생성된 호흡법 피드백" }}
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


# --- 발음 교정 기능 함수 ---
async def analyze_user_pronunciation(target_sentence: str, audio_file, db: Session):
    """사용자 발음을 분석하고 피드백을 반환합니다."""
    audio_content = await audio_file.read()
    audio_stream = io.BytesIO(audio_content)
    audio = AudioSegment.from_file(audio_stream)
    wav_stream = io.BytesIO()
    audio.set_frame_rate(16000).set_channels(1).export(wav_stream, format="wav")
    wav_stream.seek(0)
    audio_data, sample_rate = sf.read(wav_stream)
    
    clean_audio_data = _reduce_noise(audio_data, sample_rate) if np.any(audio_data) else audio_data

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cleaned_audio_path = os.path.join(PRONUNCIATION_AUDIO_DIR, f"practice_cleaned_{timestamp}.wav")
    sf.write(cleaned_audio_path, clean_audio_data, sample_rate)

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
                        "mouth_feedback": feedback.get("mouth_feedback", ""),
                        "tongue_position_feedback": feedback.get("tongue_position_feedback", ""),
                        "breathing_feedback": feedback.get("breathing_feedback", ""),
                        "teaching_point": feedback.get("diff_detail", "") # teaching_point에 diff_detail 값을 할당
                    })

    for point in processed_incorrect_points:
        # 기존의 mouth_shape 등을 초기화하는 부분을 아래와 같이 통일
        if "mouth_feedback" not in point:
            point.update({
                "mouth_feedback": "",
                "tongue_position_feedback": "",
                "breathing_feedback": "",
                "teaching_point": point.get("diff_detail", "") # teaching_point 할당
            })

        expected_char = point.get("expected")
        correct_img_url = "default.png" # 기본 이미지
        correct_video_url = None # 영상 URL은 기본적으로 없음
        
        if expected_char and '가' <= expected_char <= '힣':
            # 한글 음절일 경우 초성, 중성을 분리
            chosung, jungsung, _ = decompose_hangul(expected_char)
            
            # 1순위: 초성으로 데이터 검색
            char_data = db.query(PronunciationData).filter(PronunciationData.hangul_char == chosung).first()
            if not char_data:
                # 2순위: 초성 데이터가 없으면 중성으로 검색
                char_data = db.query(PronunciationData).filter(PronunciationData.hangul_char == jungsung).first()

            if char_data:
                correct_img_url = char_data.image_url # DB에서 이미지 URL 가져오기
                correct_video_url = char_data.video_url # DB에서 비디오 URL 가져오기
        
        point["correct_img_url"] = correct_img_url
        point["correct_video_url"] = correct_video_url # 응답에 비디오 URL 추가
        point["wrong_text"] = point.get("actual", "")
        
    response_data = {
        "score": str(final_score),
        "my_text": normalized_user,
        "target_word": normalized_target,
        "incorrect_points": processed_incorrect_points
    }
    return response_data


# --- 미니게임 기능 함수 ---
async def transcribe_audio_for_minigame(audio):
    """
    오디오 파일을 받아 텍스트로 변환하는 간단한 STT 기능입니다.
    미니게임 등 실시간 텍스트 변환이 필요할 때 사용합니다.
    """
    if not audio:
        raise HTTPException(status_code=400, detail="오디오 파일이 없습니다.")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_filepath = os.path.join(MINIGAME_AUDIO_DIR, f"minigame_audio_{timestamp}.wav")

    try:
        with open(temp_filepath, "wb") as f:
            content = await audio.read()
            f.write(content)
        print(f"미니게임용 오디오 저장 완료: {temp_filepath}")

        segments, info = whisper_model.transcribe(temp_filepath, beam_size=5, language="ko")
        transcription = "".join(segment.text for segment in segments).strip()
        print(f"미니게임 STT 결과: {transcription}")
        return {"my_text": transcription}

    except Exception as e:
        print(f"미니게임 STT 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 처리 중 서버 오류 발생: {str(e)}")
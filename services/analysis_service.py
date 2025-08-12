# services/analysis_service.py
# 음성 파일 처리, STT, LLM 평가 등 핵심 비즈니스 로직을 담고 있습니다.

import os
import numpy as np
import noisereduce as nr
import datetime
import json
import io
import soundfile as sf
import requests  # Ollama 연동을 위해 추가
import time  # 시간 측정을 위해 추가
from pydub import AudioSegment
# from openai import OpenAI # Ollama를 사용하므로 더 이상 필요하지 않습니다.
from dotenv import load_dotenv

import torch
from faster_whisper import WhisperModel

from fastapi import HTTPException

# 다른 파일에서 필요한 함수, 설정, 모델들을 임포트합니다.
from utils.hangul import decompose_hangul
from core.config import IMAGE_GUIDE_MAP
# from models.pronunciation import IncorrectPoint, PronunciationAnalysisResponse


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
        
        # --- 시간 측정 시작 ---
        stt_start_time = time.time()

        segments, _ = whisper_model.transcribe(audio_file_path, language="ko")
        transcription = "".join(segment.text for segment in segments).strip()
        
        # --- 시간 측정 종료 및 출력 ---
        stt_end_time = time.time()
        print(f"STT 처리 완료! (소요 시간: {stt_end_time - stt_start_time:.2f}초)")
        
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

# _evaluate_pronunciation_with_llm 함수를 아래 내용으로 교체해 주세요.

def _evaluate_pronunciation_with_llm(llm_input_pairs):
    """LLM(Ollama Qwen2)을 사용하여 발음 교정 피드백을 생성합니다."""
    if not llm_input_pairs:
        return {"incorrect_points": []}

    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_api_url = f"{ollama_host}/api/chat"

    # === [Qwen2 맞춤형 고급 프롬프트] ===
    system_prompt = f"""
# 지시사항
당신은 음성학 박사입니다.
주어진 각 항목에 대해 'mouth_shape', 'tongue_shape', 'breathing' 키에 대한 구체적인 한국어 교정 피드백을 짧게 생성하세요.

# 출력 규칙
- 답변 생성 시, 한글, 일반적인 구두점(.) 외에 다른 언어(특히 한자, 일본어, 영어)의 문자가 절대 포함되어서는 안 됩니다.
- 반드시 '필수 JSON 출력 형식'에 맞춰 실제 데이터만 담아 응답하세요.
- JSON 외에 다른 설명은 절대 추가하지 마세요.


# 필수 JSON 출력 형식
{{
  "incorrect_points": [
{{ "expected": "목표 글자", "actual": "사용자가 발음한 글자", "diff_detail": "주어진 교정 포인트 그대로", "mouth_feedback": "틀린 글자의 대한 입 모양 피드백", "tongue_position_feedback": "틀린 글자의 대한 혀 위치 피드백", "breathing_feedback": "생성된 호흡법 피드백" }}
  ]
}}
"""
    # [수정됨] 사용자 프롬프트를 더 직접적인 명령으로 변경
    user_prompt = f"""
당신은 음성학 박사입니다. 다음 '분석 요청 목록'의 각 항목에 대해, 당신의 지시사항과 사고 과정에 따라 분석하고, 모범 피드백 예시와 같은 수준으로 피드백을 생성한 후, 
'필수 JSON 출력 형식'에 맞춰 응답하세요. 분석 요청 목록: {json.dumps(llm_input_pairs, ensure_ascii=False)}
"""

    payload = {
    # `ollama create`로 만든 Qwen2 모델의 별명을 사용합니다.
    "model": "qwen2-7b-instruct-q4_0", 
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "format": "json",
    "stream": False
}

    try:
        print("LLM에 전달하는 데이터:", json.dumps(llm_input_pairs, ensure_ascii=False, indent=2))
        print(f"Ollama 모델 '{payload['model']}'에 발음 평가 요청을 보냅니다...")
        llm_start_time = time.time()
        
        response = requests.post(ollama_api_url, json=payload, timeout=60)
        response.raise_for_status()
        
        response_data = response.json()
        message_content = response_data.get('message', {}).get('content', '{}')
        evaluation_result = json.loads(message_content)
        
        llm_end_time = time.time()
        print(f"Ollama 피드백 생성 완료! (소요 시간: {llm_end_time - llm_start_time:.2f}초)")
        print("응답 데이터:", evaluation_result)
        return evaluation_result

    except Exception as e:
        print(f"LLM(Ollama) 평가 중 심각한 오류 발생: {e}")
        if 'message_content' in locals():
            print("LLM 원본 응답:", message_content)
        return {"incorrect_points": []}

# --- 발음 교정 기능 함수 ---
async def analyze_user_pronunciation(target_sentence: str, audio_file):
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

        # 만약 점수가 100점이지만, 사용자 발음이 목표 단어보다 길다면 100점이 아니도록 조정합니다.
    if final_score == 100 and len(normalized_user) != len(normalized_target):
        final_score = 80 # 100점이 아니도록 감점하거나, 원하는 다른 점수로 설정할 수 있습니다.
    
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

    # === [수정됨] 이미지 전달 방식을 딕셔너리로 변경 ===
    for point in processed_incorrect_points:
        if "mouth_feedback" not in point:
            point.update({"mouth_feedback": "","tongue_position_feedback": "","breathing_feedback": "","teaching_point": point.get("diff_detail", "")})
            
        expected_char = point.get("expected")
        # 자음/모음 이미지 파일명을 담을 딕셔너리 생성
        image_guides = {}

        if expected_char:
            # 글자가 한글 음절인 경우 자음/모음 분리
            if '가' <= expected_char <= '힣':
                chosung, jungsung, _ = decompose_hangul(expected_char)
                
                # 자음(초성) 이미지 확인 및 추가
                chosung_img = IMAGE_GUIDE_MAP.get(chosung)
                if chosung_img:
                    image_guides["chosung_img"] = chosung_img
                
                # 모음(중성) 이미지 확인 및 추가
                jungsung_img = IMAGE_GUIDE_MAP.get(jungsung)
                if jungsung_img:
                    image_guides["jungsung_img"] = jungsung_img
            # 한글 음절이 아닌 경우 (자/모 단독, 영어 등)
            else:
                default_img = IMAGE_GUIDE_MAP.get(expected_char)
                if default_img:
                    image_guides["default_img"] = default_img
        
        # 기존 'img' 키 대신 'image_guides' 키에 딕셔너리를 할당
        point["image_guides"] = image_guides
        # 기존 'img' 키는 제거 (프론트엔드 혼동 방지)
        if "img" in point:
            del point["img"]

    response_data = {
        "score": str(final_score),
        "my_text": normalized_user,
        "target_word": normalized_target,
        "incorrect_points": processed_incorrect_points
    }
    
    if not os.path.exists(cleaned_audio_path):
        print(f"경고: 노이즈 제거된 오디오 파일이 이미 삭제되었거나 존재하지 않습니다: {cleaned_audio_path}")

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
        return {"transcription": transcription}

    except Exception as e:
        print(f"미니게임 STT 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"오디오 처리 중 서버 오류 발생: {str(e)}")
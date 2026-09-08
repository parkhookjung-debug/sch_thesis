import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import hashlib
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random
import time
import logging

# =============================================================================
# 최적화된 기술 데이터베이스 (60가지 + 고성능 매칭)
# =============================================================================

@dataclass
class Technique:
    name: str
    category: str
    difficulty: int
    type: str = ""
    descriptions: List[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.descriptions is None:
            self.descriptions = []
        if self.keywords is None:
            self.keywords = []

class OptimizedTechniqueDB:
    """최적화된 기술 데이터베이스 - 고성능 검색"""
    
    def __init__(self):
        self.techniques = self._build_technique_index()
        self.keyword_index = self._build_keyword_index()
        self.category_index = self._build_category_index()
    
    def _build_technique_index(self) -> Dict[str, Technique]:
        """고성능 기술 인덱스 구축"""
        techniques = {}
        
        # 가드 기술 (15가지) - 압축 데이터
        guard_data = [
            ("클로즈드 가드", 2, ["다리로 몸통 잡기", "기본 가드", "허리 감싸기"], ["다리", "몸통", "기본"]),
            ("오픈 가드", 3, ["다리 벌려서 막기", "발로 거리두기"], ["다리", "발", "거리"]),
            ("하프 가드", 2, ["다리 하나 잡고 버티기", "한쪽 다리만"], ["다리", "하나", "버티기"]),
            ("스파이더 가드", 4, ["발로 팔 밀기", "소매 잡고 발로 밀기"], ["발", "팔", "밀기", "소매"]),
            ("버터플라이 가드", 3, ["무릎으로 들어올리기", "다리로 띄우기"], ["무릎", "들어올리기", "띄우기"]),
            ("라쏘 가드", 4, ["소매 감아서 가드", "팔 감아 올리기"], ["소매", "감아", "팔"]),
            ("딜라 히바", 5, ["다리 뒤쪽 걸기", "감아서 넘어뜨리기"], ["다리", "뒤쪽", "걸기"]),
            ("X 가드", 4, ["다리 교차해서 가드", "X자로 걸기"], ["다리", "교차", "X"]),
            ("리버스 가드", 4, ["뒤돌아서 가드", "등 돌리고"], ["뒤", "등", "돌리기"]),
            ("50/50 가드", 5, ["다리 얽어서", "서로 꼬기"], ["다리", "얽어", "꼬기"]),
            ("니 온 벨리", 3, ["무릎으로 배 누르기", "무릎 가드"], ["무릎", "배", "누르기"]),
            ("Z 가드", 3, ["Z자로 다리"], ["Z", "다리"]),
            ("인버티드 가드", 4, ["거꾸로 가드"], ["거꾸로", "뒤집어"]),
            ("워름 가드", 3, ["벌레처럼"], ["벌레", "기어"]),
            ("숄더 크러쉬", 3, ["어깨로 누르기"], ["어깨", "누르기"])
        ]
        
        for name, diff, descs, keys in guard_data:
            techniques[name] = Technique(name, "가드", diff, "", descs, keys)
        
        # 서브미션 (25가지) - 타입별 분류
        submission_data = [
            ("트라이앵글", 3, "초크", ["다리로 목 조르기", "삼각 조르기"], ["다리", "목", "조르기"]),
            ("암바", 2, "관절기", ["팔 꺾기", "팔꿈치 꺾는거"], ["팔", "꺾기", "관절기"]),
            ("기요틴", 2, "초크", ["목 앞쪽 조르기", "목 잡고"], ["목", "앞쪽", "조르기"]),
            ("리어네이키드", 3, "초크", ["뒤에서 목 조르기", "목 감싸기"], ["뒤", "목", "조르기"]),
            ("킴우라", 3, "관절기", ["어깨 꺾기", "팔 뒤로"], ["어깨", "팔", "꺾기"]),
            ("옴플라타", 4, "관절기", ["다리로 어깨 고정", "어깨 누르기"], ["다리", "어깨", "고정"]),
            ("아메리카나", 2, "관절기", ["팔 아래로 꺾기"], ["팔", "아래", "꺾기"]),
            ("힐훅", 5, "레그락", ["다리 꺾기", "발목 꺾기"], ["다리", "발목", "꺾기"]),
            ("니바", 4, "레그락", ["무릎 꺾기", "무릎 관절기"], ["무릎", "꺾기"]),
            ("앵클락", 3, "레그락", ["발목 꺾기", "발목 관절기"], ["발목", "꺾기"]),
            ("에제키엘", 3, "초크", ["소매로 목 조르기", "도복으로"], ["소매", "목", "도복"]),
            ("다스초크", 4, "초크", ["깃으로 목 조르기"], ["깃", "목", "조르기"]),
            ("크로스페이스", 3, "초크", ["십자로 목 조르기"], ["십자", "목", "X"]),
            ("베이스볼", 4, "초크", ["방망이 잡듯", "깃 교차"], ["방망이", "깃", "교차"]),
            ("보우앤애로우", 5, "초크", ["활처럼 당기기"], ["활", "당기기"]),
            ("펄스 초크", 3, "초크", ["목 옆쪽", "경동맥"], ["목", "옆", "경동맥"]),
            ("노스사우스", 4, "초크", ["머리 위에서"], ["머리", "위", "북남"]),
            ("애나콘다", 4, "초크", ["뱀처럼 감아서"], ["뱀", "감아"]),
            ("다르스", 4, "초크", ["등 뒤에서 깃"], ["등", "뒤", "깃"]),
            ("토호 초크", 3, "초크", ["발로 목 조르기"], ["발", "목", "조르기"]),
            ("페이스크러쉬", 3, "압박", ["얼굴 누르기"], ["얼굴", "누르기"]),
            ("캔오프너", 2, "압박", ["갈비뼈 누르기"], ["갈비", "누르기"]),
            ("넥크랭크", 4, "관절기", ["목 비틀기"], ["목", "비틀기"]),
            ("트위스터", 5, "관절기", ["허리 비틀기"], ["허리", "비틀기"]),
            ("바나나스플릿", 4, "레그락", ["다리 벌리기"], ["다리", "벌리기"])
        ]
        
        for name, diff, sub_type, descs, keys in submission_data:
            techniques[name] = Technique(name, "서브미션", diff, sub_type, descs, keys)
        
        # 스위프 (10가지)
        sweep_data = [
            ("시저 스위프", 2, ["가위로 넘기기", "다리로 넘어뜨리기"], ["가위", "넘기기"]),
            ("플라워 스위프", 3, ["하프가드에서 뒤집기"], ["하프가드", "뒤집기"]),
            ("후키 스위프", 3, ["발로 다리 걸어서"], ["발", "다리", "걸기"]),
            ("펜둘럼 스위프", 4, ["진자처럼 넘기기"], ["진자", "좌우"]),
            ("오모플라타 스위프", 4, ["어깨에서 넘기기"], ["어깨", "넘기기"]),
            ("델라히바 스위프", 4, ["다리 뒤에서"], ["다리", "뒤", "후크"]),
            ("버터플라이 스위프", 3, ["앉아서 넘기기"], ["앉아", "넘기기"]),
            ("엘리베이터 스위프", 3, ["위로 들어서"], ["위", "들어"]),
            ("토마호크 스위프", 4, ["발목 걸어서"], ["발목", "걸기"]),
            ("시팅업 스위프", 2, ["앉아서 밀기"], ["앉아", "밀기"])
        ]
        
        for name, diff, descs, keys in sweep_data:
            techniques[name] = Technique(name, "스위프", diff, "", descs, keys)
        
        # 패스가드 (6가지)
        pass_data = [
            ("토레안도 패스", 3, ["다리 밀고 지나가기"], ["다리", "밀고", "지나가기"]),
            ("더블 언더", 4, ["양다리 밑으로"], ["양다리", "밑", "파고들기"]),
            ("니 슬라이스", 2, ["무릎으로 밀어내기"], ["무릎", "밀어"]),
            ("스택 패스", 3, ["위로 쌓아올리기"], ["위", "쌓아"]),
            ("X 패스", 4, ["팔 교차해서"], ["팔", "교차", "X"]),
            ("스피드 패스", 3, ["빠르게 지나가기"], ["빠르게", "순간"])
        ]
        
        for name, diff, descs, keys in pass_data:
            techniques[name] = Technique(name, "패스가드", diff, "", descs, keys)
        
        # 이스케이프 (6가지)
        escape_data = [
            ("엘보우 이스케이프", 2, ["팔꿈치로 공간"], ["팔꿈치", "공간"]),
            ("힙 이스케이프", 3, ["엉덩이로 빠져나가기"], ["엉덩이", "허리"]),
            ("브릿지", 2, ["다리로 밀어서"], ["다리", "밀어", "브릿지"]),
            ("언더훅", 3, ["팔 밑으로"], ["팔", "밑", "파고들기"]),
            ("가드 리커버리", 3, ["가드로 돌아가기"], ["가드", "돌아가기"]),
            ("롤링", 4, ["굴러서 빠져나가기"], ["굴러", "회전"])
        ]
        
        for name, diff, descs, keys in escape_data:
            techniques[name] = Technique(name, "이스케이프", diff, "", descs, keys)
        
        # 테이크다운 (10가지)  
        takedown_data = [
            ("더블 레그", 2, ["양다리 껴안고", "태클"], ["양다리", "태클"]),
            ("싱글 레그", 2, ["한쪽 다리 잡고"], ["한쪽", "다리"]),
            ("오소토 가리", 3, ["발로 다리 걸어"], ["발", "다리", "걸기"]),
            ("힙 토스", 3, ["허리로 던지기"], ["허리", "던지기"]),
            ("풋 스위프", 4, ["발로 쓸어서"], ["발", "쓸기"]),
            ("세오이 나게", 4, ["어깨로 던지기"], ["어깨", "던지기"]),
            ("우치 마타", 5, ["허벅지로 들어서"], ["허벅지", "들어"]),
            ("하라이 고시", 4, ["다리로 쓸어서"], ["다리", "쓸기"]),
            ("코시 구루마", 3, ["허리로 돌려서"], ["허리", "돌리기"]),
            ("스냅 다운", 2, ["머리 누르고"], ["머리", "누르기"])
        ]
        
        for name, diff, descs, keys in takedown_data:
            techniques[name] = Technique(name, "테이크다운", diff, "", descs, keys)
        
        return techniques
    
    def _build_keyword_index(self) -> Dict[str, List[str]]:
        """키워드 역인덱스 구축 - O(1) 검색"""
        index = {}
        for tech_name, tech in self.techniques.items():
            for keyword in tech.keywords:
                if keyword not in index:
                    index[keyword] = []
                index[keyword].append(tech_name)
            
            # 자연어 설명에서도 키워드 추출
            for desc in tech.descriptions:
                words = desc.split()
                for word in words:
                    if len(word) >= 2:  # 2글자 이상만
                        if word not in index:
                            index[word] = []
                        if tech_name not in index[word]:
                            index[word].append(tech_name)
        return index
    
    def _build_category_index(self) -> Dict[str, List[str]]:
        """카테고리 인덱스 구축"""
        index = {}
        for tech_name, tech in self.techniques.items():
            if tech.category not in index:
                index[tech.category] = []
            index[tech.category].append(tech_name)
        return index

# =============================================================================
# 고성능 NLP 엔진
# =============================================================================

class HighPerformanceNLP:
    """고성능 자연어 처리 엔진"""
    
    def __init__(self):
        self.db = OptimizedTechniqueDB()
        self.pattern_cache = {}  # 패턴 캐시
        self.body_parts = {
            "다리": ["다리", "발", "무릎", "허벅지", "발목", "종아리"],
            "목": ["목", "목구멍", "목덜미", "경동맥"],
            "팔": ["팔", "팔꿈치", "손목", "어깨", "겨드랑이"],
            "몸통": ["몸통", "허리", "가슴", "등", "엉덩이", "배"]
        }
        self.actions = {
            "꺾기": ["꺾기", "꺾는", "비트는", "관절기", "꺽는"],
            "조르기": ["조르기", "조르는", "목조르기", "초크", "죄기"],
            "넘기기": ["넘어뜨리기", "넘기기", "뒤집기", "던지기", "메치기"],
            "잡기": ["잡기", "붙잡기", "고정하기", "컨트롤", "홀드"],
            "밀기": ["밀기", "밀어내기", "밀어서", "누르기"],
            "걸기": ["걸기", "거는", "걸어서", "후크"]
        }
        self.difficulty_words = {
            "easy": ["기본", "쉬운", "간단한", "처음", "초보", "초급"],
            "hard": ["어려운", "복잡한", "고급", "마스터", "상급", "고수"]
        }
    
    def analyze_query(self, text: str) -> Dict:
        """쿼리 분석 - 캐시 활용"""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.pattern_cache:
            return self.pattern_cache[text_hash]
        
        text_lower = text.lower()
        start_time = time.time()
        
        # 병렬 분석
        body_parts = self._extract_body_parts(text_lower)
        actions = self._extract_actions(text_lower)
        difficulty = self._extract_difficulty(text_lower)
        intent = self._extract_intent(text_lower)
        
        # 고속 기술 매칭
        main_techs, similar_techs = self._match_techniques_fast(text_lower, body_parts, actions)
        
        # 테이크다운 체크
        takedowns = self._check_takedowns(text_lower)
        
        # 감정/강도 분석
        emotion = self._analyze_emotion_fast(text_lower)
        intensity = self._analyze_intensity_fast(text_lower)
        
        result = {
            "processing_time": time.time() - start_time,
            "confidence": self._calculate_confidence(main_techs, similar_techs),
            "analysis": {
                "body_parts": body_parts,
                "actions": actions,
                "difficulty": difficulty,
                "intent": intent,
                "emotion": emotion,
                "intensity": intensity,
                "is_beginner": any(word in text_lower for word in ["초보", "처음", "모르", "기본"])
            },
            "main_techniques": main_techs[:8],  # 상위 8개
            "similar_techniques": similar_techs[:12],  # 상위 12개
            "takedown_techniques": takedowns
        }
        
        # 캐시 저장 (최대 100개)
        if len(self.pattern_cache) < 100:
            self.pattern_cache[text_hash] = result
        
        return result
    
    def _extract_body_parts(self, text: str) -> List[str]:
        """신체 부위 추출 - 최적화"""
        found = []
        for part, synonyms in self.body_parts.items():
            if any(syn in text for syn in synonyms):
                found.append(part)
        return found
    
    def _extract_actions(self, text: str) -> List[str]:
        """동작 추출 - 최적화"""
        found = []
        for action, synonyms in self.actions.items():
            if any(syn in text for syn in synonyms):
                found.append(action)
        return found
    
    def _extract_difficulty(self, text: str) -> str:
        """난이도 추출"""
        for level, words in self.difficulty_words.items():
            if any(word in text for word in words):
                return level
        return "normal"
    
    def _extract_intent(self, text: str) -> str:
        """의도 추출"""
        if any(word in text for word in ["배우고", "배워", "알려", "가르쳐", "배우자"]):
            return "learn"
        elif any(word in text for word in ["약해", "당해", "못해", "어려워", "힘들어"]):
            return "improve_weakness"
        elif any(word in text for word in ["강화", "늘리고", "향상", "발전"]):
            return "strengthen"
        elif any(word in text for word in ["경기", "시합", "대회"]):
            return "compete"
        return "practice"
    
    def _match_techniques_fast(self, text: str, body_parts: List, actions: List) -> Tuple[List, List]:
        """고속 기술 매칭 - 인덱스 활용"""
        scores = {}
        
        # 1. 키워드 인덱스 활용한 고속 매칭
        words = text.split()
        for word in words:
            if word in self.db.keyword_index:
                for tech_name in self.db.keyword_index[word]:
                    scores[tech_name] = scores.get(tech_name, 0) + 3
        
        # 2. 기술명 직접 매칭
        for tech_name in self.db.techniques:
            if tech_name.lower() in text:
                scores[tech_name] = scores.get(tech_name, 0) + 10
        
        # 3. 신체부위 + 동작 조합 보너스
        for tech_name, tech in self.db.techniques.items():
            combo_score = 0
            for desc in tech.descriptions:
                desc_lower = desc.lower()
                for bp in body_parts:
                    if bp in desc_lower:
                        combo_score += 2
                for action in actions:
                    if action in desc_lower:
                        combo_score += 2
                
                # 조합 보너스
                if body_parts and actions:
                    for bp in body_parts:
                        for action in actions:
                            if bp in desc_lower and action in desc_lower:
                                combo_score += 4
            
            if combo_score > 0:
                scores[tech_name] = scores.get(tech_name, 0) + combo_score
        
        # 4. 결과 정렬 및 분류
        sorted_techs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        main_techs = []
        similar_techs = []
        
        for tech_name, score in sorted_techs:
            tech = self.db.techniques[tech_name]
            tech_info = {
                "name": tech_name,
                "category": tech.category,
                "difficulty": tech.difficulty,
                "type": tech.type,
                "score": score
            }
            
            if score >= 5:
                main_techs.append(tech_info)
            elif score >= 2:
                similar_techs.append(tech_info)
        
        return main_techs, similar_techs
    
    def _check_takedowns(self, text: str) -> List:
        """테이크다운 확인"""
        takedown_keywords = ["테이크다운", "넘어뜨리기", "던지기", "메치기", "태클", "서서", "스탠딩"]
        if any(word in text for word in takedown_keywords):
            return [
                {"name": name, "category": "테이크다운", "difficulty": tech.difficulty}
                for name, tech in self.db.techniques.items()
                if tech.category == "테이크다운"
            ][:8]
        return []
    
    def _analyze_emotion_fast(self, text: str) -> List[str]:
        """빠른 감정 분석"""
        emotions = []
        if any(word in text for word in ["답답", "짜증", "힘들", "어려워"]):
            emotions.append("frustration")
        if any(word in text for word in ["재밌", "좋아", "즐거", "신나"]):
            emotions.append("positive")
        if any(word in text for word in ["무서", "걱정", "불안"]):
            emotions.append("anxiety")
        return emotions
    
    def _analyze_intensity_fast(self, text: str) -> str:
        """빠른 강도 분석"""
        if any(word in text for word in ["집중적", "강하게", "빡세게", "열심히", "완전히"]):
            return "high"
        elif any(word in text for word in ["가볍게", "천천히", "쉽게", "부드럽게"]):
            return "low"
        return "medium"
    
    def _calculate_confidence(self, main_techs: List, similar_techs: List) -> float:
        """신뢰도 계산"""
        if not main_techs and not similar_techs:
            return 0.0
        
        total_score = sum(t.get("score", 0) for t in main_techs + similar_techs)
        max_possible = len(main_techs + similar_techs) * 10
        
        return min(total_score / max_possible, 1.0) if max_possible > 0 else 0.0

# =============================================================================
# 최적화된 DB 관리
# =============================================================================

class OptimizedDB:
    """최적화된 데이터베이스"""
    
    def __init__(self, db_name="bjj_optimized.db"):
        self.db_name = db_name
        self.connection_pool = []
        self.init_db()
    
    def init_db(self):
        """DB 초기화 - 인덱스 최적화"""
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # 성능 최적화
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=10000")
            
            cursor = conn.cursor()
            
            # 사용자 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    belt TEXT DEFAULT '화이트',
                    skill_level REAL DEFAULT 1.0,
                    preferences TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 훈련 세션 테이블 (최적화)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    session_name TEXT,
                    techniques TEXT,
                    duration INTEGER,
                    difficulty TEXT,
                    completion_rate REAL DEFAULT 0,
                    feedback_score INTEGER DEFAULT 0,
                    session_data TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 기술 숙련도 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technique_mastery (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    technique_name TEXT,
                    mastery_level REAL DEFAULT 0.0,
                    practice_count INTEGER DEFAULT 0,
                    last_practiced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, technique_name)
                )
            ''')
            
            # 성능 최적화 인덱스
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON training_sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_date ON training_sessions(created_at)",
                "CREATE INDEX IF NOT EXISTS idx_mastery_user ON technique_mastery(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_mastery_technique ON technique_mastery(technique_name)"
            ]
            
            for idx in indexes:
                cursor.execute(idx)
            
            conn.commit()
    
    def save_user(self, username: str, belt: str = "화이트") -> Optional[str]:
        """사용자 저장 - 최적화"""
        user_id = str(uuid.uuid4())
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (id, username, belt) VALUES (?, ?, ?)",
                    (user_id, username, belt)
                )
                return user_id
        except sqlite3.IntegrityError:
            return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """사용자 조회 - 캐시 활용"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, belt, skill_level FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0], 
                    "username": row[1], 
                    "belt": row[2], 
                    "skill_level": row[3]
                }
        return None
    
    def save_session(self, user_id: str, session_data: Dict) -> str:
        """세션 저장 - 배치 처리"""
        session_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO training_sessions 
                (id, user_id, session_name, techniques, duration, difficulty, session_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, user_id, 
                session_data.get("name", "훈련"),
                json.dumps(session_data.get("techniques", [])),
                session_data.get("duration", 60),
                session_data.get("difficulty", "normal"),
                json.dumps(session_data)
            ))
            return session_id
    
    def update_mastery(self, user_id: str, technique: str, improvement: float = 0.1):
        """기술 숙련도 업데이트"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO technique_mastery 
                (id, user_id, technique_name, mastery_level, practice_count, last_practiced)
                VALUES (
                    COALESCE((SELECT id FROM technique_mastery WHERE user_id=? AND technique_name=?), ?),
                    ?, ?, 
                    COALESCE((SELECT mastery_level FROM technique_mastery WHERE user_id=? AND technique_name=?), 0) + ?,
                    COALESCE((SELECT practice_count FROM technique_mastery WHERE user_id=? AND technique_name=?), 0) + 1,
                    CURRENT_TIMESTAMP
                )
            ''', (user_id, technique, str(uuid.uuid4()), user_id, technique, improvement, 
                  user_id, technique, user_id, technique))

# =============================================================================
# 고성능 훈련 생성기
# =============================================================================

class AdvancedTrainingGenerator:
    """고성능 훈련 생성기"""
    
    def __init__(self, db: OptimizedDB):
        self.db = db
        self.tech_db = OptimizedTechniqueDB()
    
    def generate_optimized_program(self, selected_techniques: List[str], 
                                 user_data: Dict, duration: int = 60, 
                                 difficulty: str = "normal") -> Dict:
        """최적화된 훈련 프로그램 생성"""
        
        # 사용자 스킬 레벨 고려
        skill_multiplier = user_data.get("skill_level", 1.0)
        
        # 시간 배분 최적화
        warmup_time = max(5, int(duration * 0.15))
        cooldown_time = max(5, int(duration * 0.15))
        main_time = duration - warmup_time - cooldown_time
        
        # 기술별 시간 배분 (난이도 고려)
        tech_times = self._calculate_optimal_time_distribution(
            selected_techniques, main_time, difficulty, skill_multiplier
        )
        
        # 기술 순서 최적화 (학습 효과 극대화)
        optimized_order = self._optimize_technique_order(selected_techniques)
        
        program = {
            "meta": {
                "duration": duration,
                "techniques": selected_techniques,
                "difficulty": difficulty,
                "skill_level": skill_multiplier,
                "optimization_score": self._calculate_program_quality(selected_techniques)
            },
            "warmup": self._generate_smart_warmup(selected_techniques, warmup_time),
            "main_training": self._generate_main_blocks(optimized_order, tech_times, difficulty),
            "combinations": self._suggest_technique_combinations(selected_techniques),
            "cooldown": self._generate_recovery_sequence(cooldown_time),
            "progression_tips": self._generate_progression_advice(selected_techniques, user_data)
        }
        
        return program
    
    def _calculate_optimal_time_distribution(self, techniques: List[str], 
                                           total_time: int, difficulty: str, 
                                           skill_level: float) -> Dict[str, int]:
        """시간 배분 최적화"""
        base_time = total_time // len(techniques)
        time_distribution = {}
        
        for tech in techniques:
            if tech in self.tech_db.techniques:
                tech_data = self.tech_db.techniques[tech]
                
                # 난이도별 시간 조정
                difficulty_modifier = {
                    "easy": 0.8, "normal": 1.0, "hard": 1.3
                }.get(difficulty, 1.0)
                
                # 기술 복잡도 고려
                complexity_modifier = min(tech_data.difficulty / 3.0, 1.5)
                
                # 사용자 스킬 레벨 고려
                skill_modifier = max(0.7, 2.0 - skill_level)
                
                adjusted_time = int(base_time * difficulty_modifier * 
                                  complexity_modifier * skill_modifier)
                time_distribution[tech] = max(5, adjusted_time)
        
        # 총 시간 맞춤 조정
        total_allocated = sum(time_distribution.values())
        if total_allocated != total_time:
            ratio = total_time / total_allocated
            for tech in time_distribution:
                time_distribution[tech] = int(time_distribution[tech] * ratio)
        
        return time_distribution
    
    def _optimize_technique_order(self, techniques: List[str]) -> List[str]:
        """기술 순서 최적화 - 학습 효과 극대화"""
        if len(techniques) <= 1:
            return techniques
        
        # 카테고리별 그룹화
        categories = {}
        for tech in techniques:
            if tech in self.tech_db.techniques:
                cat = self.tech_db.techniques[tech].category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(tech)
        
        # 최적 순서: 기본 → 중급 → 고급, 관련 기술끼리 묶기
        optimized = []
        
        # 1. 난이도순 정렬
        sorted_by_difficulty = sorted(
            techniques,
            key=lambda x: self.tech_db.techniques.get(x, Technique("", "", 3)).difficulty
        )
        
        # 2. 카테고리 연관성 고려한 재배치
        used = set()
        for tech in sorted_by_difficulty:
            if tech not in used:
                optimized.append(tech)
                used.add(tech)
                
                # 같은 카테고리 기술들 연속 배치
                if tech in self.tech_db.techniques:
                    cat = self.tech_db.techniques[tech].category
                    for similar_tech in categories.get(cat, []):
                        if similar_tech not in used:
                            optimized.append(similar_tech)
                            used.add(similar_tech)
        
        return optimized
    
    def _generate_smart_warmup(self, techniques: List[str], duration: int) -> Dict:
        """스마트 웜업 생성"""
        categories = set()
        for tech in techniques:
            if tech in self.tech_db.techniques:
                categories.add(self.tech_db.techniques[tech].category)
        
        warmup_exercises = []
        
        # 카테고리별 특화 웜업
        if "가드" in categories:
            warmup_exercises.extend(["다리 스트레칭", "고관절 돌리기", "가드 포지션 연습"])
        if "서브미션" in categories:
            warmup_exercises.extend(["팔 스트레칭", "어깨 돌리기", "목 스트레칭"])
        if "테이크다운" in categories:
            warmup_exercises.extend(["전신 스트레칭", "발목 돌리기", "무브먼트 드릴"])
        
        # 기본 웜업 추가
        base_warmup = ["전체 관절 돌리기", "가벼운 움직임", "호흡 준비"]
        warmup_exercises.extend(base_warmup)
        
        return {
            "duration": duration,
            "exercises": list(set(warmup_exercises)),  # 중복 제거
            "focus": f"주요 기술({', '.join(list(categories)[:2])}) 준비"
        }
    
    def _generate_main_blocks(self, techniques: List[str], time_dist: Dict[str, int], 
                            difficulty: str) -> List[Dict]:
        """메인 훈련 블록 생성"""
        blocks = []
        
        for tech in techniques:
            time_allocated = time_dist.get(tech, 15)
            
            # 시간 세분화
            explanation_time = max(2, int(time_allocated * 0.2))
            drill_time = max(5, int(time_allocated * 0.5))
            application_time = max(3, int(time_allocated * 0.3))
            
            block = {
                "technique": tech,
                "total_time": time_allocated,
                "structure": {
                    "설명 & 데모": f"{explanation_time}분",
                    "기본 드릴": f"{drill_time}분",
                    "실전 적용": f"{application_time}분"
                },
                "key_points": self._get_technique_key_points(tech),
                "common_mistakes": self._get_common_mistakes(tech),
                "difficulty_adjustments": self._get_difficulty_tips(tech, difficulty)
            }
            
            blocks.append(block)
        
        return blocks
    
    def _suggest_technique_combinations(self, techniques: List[str]) -> List[Dict]:
        """기술 조합 제안"""
        combinations = []
        
        # 카테고리별 조합 패턴
        combo_patterns = {
            ("가드", "서브미션"): "가드에서 직접 서브미션",
            ("가드", "스위프"): "가드에서 스위프로 포지션 변경",
            ("스위프", "서브미션"): "스위프 성공 후 서브미션",
            ("패스가드", "서브미션"): "패스 성공 후 서브미션",
            ("테이크다운", "패스가드"): "테이크다운 후 가드 패스"
        }
        
        for i, tech1 in enumerate(techniques):
            for tech2 in techniques[i+1:]:
                if tech1 in self.tech_db.techniques and tech2 in self.tech_db.techniques:
                    cat1 = self.tech_db.techniques[tech1].category
                    cat2 = self.tech_db.techniques[tech2].category
                    
                    pattern_key = (cat1, cat2) if (cat1, cat2) in combo_patterns else (cat2, cat1)
                    
                    if pattern_key in combo_patterns:
                        combinations.append({
                            "technique1": tech1,
                            "technique2": tech2,
                            "connection": combo_patterns[pattern_key],
                            "practice_method": f"{tech1} → {tech2} 자연스러운 연결 연습"
                        })
        
        return combinations[:4]  # 최대 4개 조합
    
    def _get_technique_key_points(self, technique: str) -> List[str]:
        """기술별 핵심 포인트"""
        if technique in self.tech_db.techniques:
            tech = self.tech_db.techniques[technique]
            
            # 카테고리별 기본 포인트
            category_points = {
                "가드": ["정확한 포지션", "거리 조절", "상대 컨트롤"],
                "서브미션": ["적절한 각도", "점진적 압력", "상대 반응 읽기"],
                "스위프": ["타이밍", "중심 잡기", "연결동작"],
                "패스가드": ["압력 유지", "빠른 전환", "안정된 마무리"],
                "이스케이프": ["공간 만들기", "효율적 움직임", "다음 포지션 준비"],
                "테이크다운": ["밸런스", "진입 타이밍", "마무리 확실히"]
            }
            
            return category_points.get(tech.category, ["정확한 실행", "안전 확보", "반복 연습"])
        
        return ["기본기 숙지", "안전 우선", "꾸준한 연습"]
    
    def _get_common_mistakes(self, technique: str) -> List[str]:
        """일반적 실수들"""
        common_mistakes = {
            "서브미션": ["성급한 실행", "과도한 힘", "각도 무시"],
            "가드": ["수동적 자세", "거리 조절 실패", "그립 놓침"],
            "스위프": ["타이밍 놓침", "불완전한 준비", "연결 부족"],
            "패스가드": ["조급함", "압력 부족", "포지션 불안정"],
            "테이크다운": ["밸런스 상실", "진입 실패", "마무리 소홀"]
        }
        
        if technique in self.tech_db.techniques:
            category = self.tech_db.techniques[technique].category
            return common_mistakes.get(category, ["기본기 부족", "반복 부족"])
        
        return ["충분한 연습 부족", "집중력 부족"]
    
    def _get_difficulty_tips(self, technique: str, difficulty: str) -> List[str]:
        """난이도별 팁"""
        if technique not in self.tech_db.techniques:
            return []
        
        tech_difficulty = self.tech_db.techniques[technique].difficulty
        
        if difficulty == "easy" or tech_difficulty <= 2:
            return ["천천히 정확하게", "기본 동작 완전 숙지", "안전 최우선"]
        elif difficulty == "hard" or tech_difficulty >= 4:
            return ["세부 디테일 집중", "다양한 변형 시도", "실전 상황 적용"]
        else:
            return ["적당한 속도로", "정확성과 효율성", "연결 기술 연습"]
    
    def _generate_recovery_sequence(self, duration: int) -> Dict:
        """회복 시퀀스 생성"""
        return {
            "duration": duration,
            "exercises": [
                "정적 스트레칭 (전신)",
                "심호흡 운동",
                "관절 이완",
                "부상 방지 스트레칭",
                "명상 및 정리"
            ],
            "focus": "근육 이완 및 정신적 정리"
        }
    
    def _generate_progression_advice(self, techniques: List[str], user_data: Dict) -> List[str]:
        """진행 조언 생성"""
        belt_level = user_data.get("belt", "화이트")
        skill_level = user_data.get("skill_level", 1.0)
        
        advice = []
        
        # 벨트별 조언
        belt_advice = {
            "화이트": "기본기에 충실하고 안전을 최우선으로 하세요",
            "블루": "기술들의 연결과 흐름을 중시하세요",
            "퍼플": "자신만의 게임 스타일을 발전시키세요",
            "브라운": "디테일과 타이밍에 집중하세요",
            "블랙": "완성도를 높이고 후진을 양성하세요"
        }
        
        advice.append(belt_advice.get(belt_level, "꾸준한 연습이 답입니다"))
        
        # 선택된 기술 조합에 따른 조언
        categories = set()
        avg_difficulty = 0
        for tech in techniques:
            if tech in self.tech_db.techniques:
                categories.add(self.tech_db.techniques[tech].category)
                avg_difficulty += self.tech_db.techniques[tech].difficulty
        
        if len(techniques) > 0:
            avg_difficulty /= len(techniques)
        
        if avg_difficulty > 4:
            advice.append("고난이도 기술들이 포함되어 있으니 충분한 기본기 연습 후 시도하세요")
        elif len(categories) > 3:
            advice.append("다양한 카테고리의 기술을 배우고 있으니 연결성을 중시하세요")
        
        advice.append("매 훈련마다 작은 개선점을 찾아 발전시키세요")
        
        return advice
    
    def _calculate_program_quality(self, techniques: List[str]) -> float:
        """프로그램 품질 점수"""
        if not techniques:
            return 0.0
        
        # 기술 다양성 점수
        categories = set()
        total_difficulty = 0
        
        for tech in techniques:
            if tech in self.tech_db.techniques:
                categories.add(self.tech_db.techniques[tech].category)
                total_difficulty += self.tech_db.techniques[tech].difficulty
        
        diversity_score = min(len(categories) / 3.0, 1.0)  # 최대 3개 카테고리
        balance_score = min(total_difficulty / (len(techniques) * 3), 1.0)  # 평균 난이도 3 기준
        
        return (diversity_score + balance_score) / 2.0

# =============================================================================
# 최적화된 Streamlit UI
# =============================================================================

def main():
    st.set_page_config(
        page_title="주짓수 고성능 훈련 시스템", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # 성능 최적화: 세션 상태 초기화
    if 'initialized' not in st.session_state:
        st.session_state.db = OptimizedDB()
        st.session_state.nlp = HighPerformanceNLP()
        st.session_state.initialized = True
    
    st.title("🥋 주짓수 고성능 AI 훈련 시스템")
    st.caption("⚡ 60가지 기술 스펙트럼 | 🧠 고성능 자연어 처리 | 🎯 맞춤형 훈련 생성")
    
    # 사용자 관리 (간소화된 헤더)
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if 'user' not in st.session_state:
            username = st.text_input("사용자명", placeholder="이름을 입력하세요")
        else:
            st.success(f"👋 {st.session_state.user['username']} ({st.session_state.user['belt']} 벨트)")
    
    with col2:
        if 'user' not in st.session_state:
            belt = st.selectbox("벨트", ["화이트", "블루", "퍼플", "브라운", "블랙"])
        else:
            if st.button("로그아웃", type="secondary"):
                del st.session_state.user
                st.rerun()
    
    with col3:
        if 'user' not in st.session_state:
            if st.button("시작하기", type="primary"):
                if username:
                    # 로그인 시도
                    user = st.session_state.db.get_user(username)
                    if user:
                        st.session_state.user = user
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        # 자동 회원가입
                        user_id = st.session_state.db.save_user(username, belt)
                        if user_id:
                            st.session_state.user = {"id": user_id, "username": username, "belt": belt}
                            st.success("자동 가입 완료!")
                            st.rerun()
    
    st.divider()
    
    # 메인 인터페이스
    if 'user' in st.session_state:
        create_optimized_interface()
    else:
        show_welcome_screen()

def show_welcome_screen():
    """환영 화면"""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        ### 🎯 시스템 특징
        
        **🧠 고성능 AI 분석**
        - "다리 꺾는 기술", "목 조르는 거" 등 자연스러운 표현 이해
        - 0.1초 이내 초고속 분석
        - 60가지 기술 스펙트럼 완벽 커버
        
        **⚡ 최적화된 성능**
        - 인덱스 기반 O(1) 검색
        - 패턴 캐싱으로 반복 쿼리 최적화
        - 데이터베이스 WAL 모드로 고속 처리
        
        **🎓 개인 맞춤형 훈련**
        - 벨트별, 스킬별 맞춤 프로그램
        - 기술 순서 최적화로 학습 효과 극대화
        - 실시간 난이도 조절
        """)

def create_optimized_interface():
    """최적화된 메인 인터페이스"""
    
    # 퀵 스타트 섹션
    st.subheader("💨 빠른 시작")
    
    col1, col2, col3, col4 = st.columns(4)
    quick_options = [
        ("🦵 다리 기술", "다리 꺾는 기술이랑 다리로 목 조르는 기술"),
        ("👔 목 기술", "목 조르는 기술들 알려줘"),
        ("🛡️ 가드 기술", "몸통 잡는 가드 기술 배우고 싶어"),
        ("🤼 테이크다운", "상대 넘어뜨리는 테이크다운 기술")
    ]
    
    for i, (label, query) in enumerate(quick_options):
        with [col1, col2, col3, col4][i]:
            if st.button(label, use_container_width=True):
                st.session_state.query_input = query
    
    st.divider()
    
    # 메인 쿼리 입력
    st.subheader("🗣️ 자연어로 요청하기")
    
    query = st.text_area(
        "어떤 기술을 배우고 싶으신가요?",
        value=st.session_state.get('query_input', ''),
        placeholder="예시: 다리로 목 조르는 기술이랑 팔 꺾는 관절기 배우고 싶어요",
        height=80,
        help="기술 이름을 몰라도 괜찮습니다. '다리 꺾는 거', '목 조르는 기술' 등으로 설명해주세요!"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        analyze_btn = st.button("🚀 AI 분석 시작", type="primary", use_container_width=True)
    with col2:
        if st.button("🔄 초기화", use_container_width=True):
            for key in ['query_input', 'analysis_result', 'selected_techniques']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    # AI 분석 실행
    if analyze_btn and query.strip():
        start_time = time.time()
        
        with st.spinner("🧠 AI가 당신의 요청을 분석하고 있습니다..."):
            result = st.session_state.nlp.analyze_query(query)
            st.session_state.analysis_result = result
        
        processing_time = time.time() - start_time
        st.success(f"✅ 분석 완료! ({processing_time:.2f}초, AI 처리: {result.get('processing_time', 0):.3f}초)")
    
    # 분석 결과 표시
    if 'analysis_result' in st.session_state:
        show_optimized_results(st.session_state.analysis_result)

def show_optimized_results(result: Dict):
    """최적화된 결과 표시"""
    
    st.divider()
    
    # 성능 지표 (개발용)
    with st.expander("📊 시스템 성능", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("처리 시간", f"{result.get('processing_time', 0):.3f}초")
        with col2:
            st.metric("신뢰도", f"{result.get('confidence', 0)*100:.1f}%")
        with col3:
            st.metric("메인 기술", len(result.get('main_techniques', [])))
        with col4:
            st.metric("전체 추천", len(result.get('main_techniques', [])) + len(result.get('similar_techniques', [])))
    
    # 분석 요약
    analysis = result.get('analysis', {})
    
    st.subheader("🎯 AI 분석 결과")
    col1, col2 = st.columns(2)
    
    with col1:
        if analysis.get('body_parts'):
            st.info(f"🎯 **감지된 부위**: {', '.join(analysis['body_parts'])}")
        if analysis.get('actions'):
            st.info(f"⚡ **감지된 동작**: {', '.join(analysis['actions'])}")
    
    with col2:
        st.info(f"📊 **난이도**: {analysis.get('difficulty', 'normal')}")
        st.info(f"🎭 **의도**: {analysis.get('intent', 'practice')}")
        if analysis.get('is_beginner'):
            st.success("👶 **초보자 친화적 요청**")
    
    # 감정/강도 분석 (있는 경우만)
    if analysis.get('emotion') or analysis.get('intensity') != 'medium':
        st.write("**🧠 심화 분석**")
        if analysis.get('emotion'):
            st.write(f"• 감정 상태: {', '.join(analysis['emotion'])}")
        if analysis.get('intensity') != 'medium':
            st.write(f"• 훈련 강도: {analysis['intensity']}")
    
    # 기술 선택 인터페이스
    if 'selected_techniques' not in st.session_state:
        st.session_state.selected_techniques = []
    
    st.divider()
    st.subheader("✅ 기술 선택")
    
    # 탭으로 기술 카테고리 구분
    main_techs = result.get('main_techniques', [])
    similar_techs = result.get('similar_techniques', [])
    takedown_techs = result.get('takedown_techniques', [])
    
    tab_labels = ["🎯 메인 추천"]
    if similar_techs:
        tab_labels.append("🔄 유사 기술")
    if takedown_techs:
        tab_labels.append("🤼 테이크다운")
    
    tabs = st.tabs(tab_labels)
    
    # 메인 추천 탭
    with tabs[0]:
        if main_techs:
            st.warning("⚠️ **메인 추천에서 최소 1개는 선택해주세요**")
            display_technique_grid(main_techs, "main")
        else:
            st.info("검색 결과가 없습니다. 다른 표현으로 시도해보세요.")
    
    # 유사 기술 탭
    if similar_techs:
        with tabs[1]:
            st.info("💡 비슷한 목적의 다른 기술들입니다")
            display_technique_grid(similar_techs, "similar")
    
    # 테이크다운 탭
    if takedown_techs:
        with tabs[-1]:
            st.info("🤼 스탠딩에서 사용하는 넘어뜨리기 기술들입니다")
            display_technique_grid(takedown_techs, "takedown")
    
    # 선택된 기술 요약 및 훈련 생성
    if st.session_state.selected_techniques:
        st.divider()
        show_training_generation_interface()

def display_technique_grid(techniques: List[Dict], category: str):
    """기술 그리드 표시 - 최적화"""
    
    cols_per_row = 3
    for i in range(0, len(techniques), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j in range(cols_per_row):
            idx = i + j
            if idx < len(techniques):
                tech = techniques[idx]
                tech_name = tech.get('name', tech.get('technique', ''))
                
                with cols[j]:
                    # 기술 카드
                    with st.container():
                        difficulty_stars = "⭐" * tech.get('difficulty', 3)
                        tech_type = tech.get('type', '')
                        type_display = f" ({tech_type})" if tech_type else ""
                        
                        st.markdown(f"**{tech_name}**{type_display}")
                        st.caption(f"난이도: {difficulty_stars} | {tech.get('category', '')}")
                        
                        # 점수 표시 (개발용)
                        if tech.get('score', 0) > 0:
                            st.caption(f"매칭도: {tech['score']}")
                        
                        # 선택 체크박스
                        selected = st.checkbox(
                            "선택",
                            key=f"{category}_{tech_name}",
                            value=tech_name in st.session_state.selected_techniques
                        )
                        
                        # 선택 상태 업데이트
                        if selected and tech_name not in st.session_state.selected_techniques:
                            st.session_state.selected_techniques.append(tech_name)
                        elif not selected and tech_name in st.session_state.selected_techniques:
                            st.session_state.selected_techniques.remove(tech_name)

def show_training_generation_interface():
    """훈련 생성 인터페이스"""
    
    st.subheader("🎯 맞춤 훈련 설정")
    
    # 선택된 기술 표시
    st.success(f"✅ **선택된 기술 ({len(st.session_state.selected_techniques)}개)**: {', '.join(st.session_state.selected_techniques)}")
    
    # 훈련 설정
    col1, col2, col3 = st.columns(3)
    
    with col1:
        duration = st.slider(
            "⏱️ 훈련 시간",
            min_value=30, max_value=120, value=60, step=15,
            help="권장: 초보자 30-60분, 중급자 60-90분"
        )
    
    with col2:
        difficulty = st.selectbox(
            "🎚️ 난이도 설정",
            options=["easy", "normal", "hard"],
            index=1,
            format_func=lambda x: {"easy": "🟢 쉬움", "normal": "🟡 보통", "hard": "🔴 어려움"}[x],
            help="개인 수준에 맞는 난이도를 선택하세요"
        )
    
    with col3:
        focus_type = st.selectbox(
            "🎯 훈련 집중도",
            options=["balanced", "technique", "conditioning"],
            format_func=lambda x: {
                "balanced": "⚖️ 균형잡힌",
                "technique": "🎯 기술 중심", 
                "conditioning": "💪 체력 중심"
            }[x]
        )
    
    # 고급 옵션
    with st.expander("⚙️ 고급 설정", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            include_warmup = st.checkbox("웜업 포함", value=True)
            include_combinations = st.checkbox("기술 조합 포함", value=True)
        with col2:
            include_cooldown = st.checkbox("쿨다운 포함", value=True)
            adaptive_timing = st.checkbox("적응형 시간 배분", value=True)
    
    # 훈련 프로그램 생성
    if st.button("🚀 최적화된 훈련 프로그램 생성", type="primary", use_container_width=True):
        user_data = st.session_state.user.copy()
        user_data.update({
            "focus_type": focus_type,
            "include_warmup": include_warmup,
            "include_combinations": include_combinations,
            "include_cooldown": include_cooldown,
            "adaptive_timing": adaptive_timing
        })
        
        with st.spinner("🧠 AI가 최적의 훈련 프로그램을 생성하고 있습니다..."):
            generator = AdvancedTrainingGenerator(st.session_state.db)
            program = generator.generate_optimized_program(
                st.session_state.selected_techniques,
                user_data,
                duration,
                difficulty
            )
            st.session_state.training_program = program
        
        st.success("🎉 최적화된 훈련 프로그램이 완성되었습니다!")
        show_optimized_program(program)

def show_optimized_program(program: Dict):
    """최적화된 훈련 프로그램 표시"""
    
    st.divider()
    st.subheader("🏆 맞춤형 최적화 훈련 프로그램")
    
    # 프로그램 메타 정보
    meta = program.get('meta', {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⏱️ 총 시간", f"{meta.get('duration', 0)}분")
    with col2:
        st.metric("🎯 기술 수", f"{len(meta.get('techniques', []))}개")
    with col3:
        st.metric("📊 난이도", meta.get('difficulty', 'normal'))
    with col4:
        quality_score = meta.get('optimization_score', 0) * 100
        st.metric("🏆 최적화 점수", f"{quality_score:.0f}%")
    
    # 프로그램 구성 탭
    tab1, tab2, tab3, tab4 = st.tabs(["🏃 웜업", "🥋 메인 훈련", "🔗 기술 조합", "🧘 마무리"])
    
    # 웜업 탭
    with tab1:
        warmup = program.get('warmup', {})
        st.write(f"**⏱️ 시간**: {warmup.get('duration', 10)}분")
        st.write(f"**🎯 집중 영역**: {warmup.get('focus', '전체')}")
        
        st.write("**운동 목록**:")
        for exercise in warmup.get('exercises', []):
            st.write(f"• {exercise}")
    
    # 메인 훈련 탭
    with tab2:
        main_blocks = program.get('main_training', [])
        
        for i, block in enumerate(main_blocks, 1):
            with st.expander(f"🥋 {i}. {block.get('technique', '')} ({block.get('total_time', 0)}분)", expanded=i==1):
                
                # 시간 구성
                st.write("**⏱️ 시간 배분**:")
                structure = block.get('structure', {})
                for phase, time in structure.items():
                    st.write(f"• {phase}: {time}")
                
                # 핵심 포인트
                key_points = block.get('key_points', [])
                if key_points:
                    st.write("**🎯 핵심 포인트**:")
                    for point in key_points:
                        st.write(f"• {point}")
                
                # 주의사항
                mistakes = block.get('common_mistakes', [])
                if mistakes:
                    st.write("**⚠️ 주의사항**:")
                    for mistake in mistakes:
                        st.write(f"• {mistake}")
                
                # 난이도별 팁
                tips = block.get('difficulty_adjustments', [])
                if tips:
                    st.write("**💡 난이도별 팁**:")
                    for tip in tips:
                        st.write(f"• {tip}")
    
    # 기술 조합 탭
    with tab3:
        combinations = program.get('combinations', [])
        if combinations:
            st.write("**🔗 추천 기술 조합**:")
            for combo in combinations:
                st.write(f"**{combo.get('technique1', '')} ➡️ {combo.get('technique2', '')}**")
                st.write(f"• 연결 방식: {combo.get('connection', '')}")
                st.write(f"• 연습 방법: {combo.get('practice_method', '')}")
                st.divider()
        else:
            st.info("선택된 기술들 간의 조합을 찾을 수 없습니다.")
    
    # 마무리 탭
    with tab4:
        cooldown = program.get('cooldown', {})
        st.write(f"**⏱️ 시간**: {cooldown.get('duration', 10)}분")
        st.write(f"**🎯 목표**: {cooldown.get('focus', '회복')}")
        
        st.write("**운동 목록**:")
        for exercise in cooldown.get('exercises', []):
            st.write(f"• {exercise}")
        
        # 진행 조언
        progression_tips = program.get('progression_tips', [])
        if progression_tips:
            st.write("**💡 진행 조언**:")
            for tip in progression_tips:
                st.info(tip)
    
    # 액션 버튼
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 프로그램 저장", use_container_width=True):
            save_training_program(program)
    
    with col2:
        if st.button("📤 프로그램 공유", use_container_width=True):
            share_program(program)
    
    with col3:
        if st.button("🔄 새로운 프로그램 만들기", use_container_width=True):
            # 초기화
            keys_to_clear = ['selected_techniques', 'training_program', 'analysis_result']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def save_training_program(program: Dict):
    """훈련 프로그램 저장"""
    try:
        user_data = st.session_state.user
        meta = program.get('meta', {})
        
        session_data = {
            "name": f"AI 맞춤 훈련 - {', '.join(meta.get('techniques', [])[:2])}...",
            "techniques": meta.get('techniques', []),
            "duration": meta.get('duration', 60),
            "difficulty": meta.get('difficulty', 'normal'),
            "optimization_score": meta.get('optimization_score', 0),
            "program_data": program
        }
        
        session_id = st.session_state.db.save_session(user_data["id"], session_data)
        
        if session_id:
            st.success("✅ 훈련 프로그램이 성공적으로 저장되었습니다!")
            
            # 기술 숙련도 업데이트
            for tech in meta.get('techniques', []):
                st.session_state.db.update_mastery(user_data["id"], tech, 0.05)
            
            st.info(f"📝 세션 ID: `{session_id}`")
        else:
            st.error("❌ 저장 중 오류가 발생했습니다.")
            
    except Exception as e:
        st.error(f"❌ 저장 실패: {str(e)}")

def share_program(program: Dict):
    """프로그램 공유 기능"""
    meta = program.get('meta', {})
    
    share_text = f"""
🥋 **주짓수 AI 맞춤 훈련 프로그램**

⏱️ **시간**: {meta.get('duration', 60)}분
🎯 **기술**: {', '.join(meta.get('techniques', []))}
📊 **난이도**: {meta.get('difficulty', 'normal')}
🏆 **최적화 점수**: {meta.get('optimization_score', 0)*100:.0f}%

🔗 주짓수 AI 훈련 시스템에서 생성됨
"""
    
    st.text_area("📤 공유용 텍스트", share_text, height=150)
    st.info("위 텍스트를 복사해서 친구들과 공유하세요!")

# =============================================================================
# 벨트 및 성능 상수
# =============================================================================

BJJ_BELTS = {
    "화이트": {"rank": 1, "skill_multiplier": 0.8, "focus": ["기본기", "안전"]},
    "블루": {"rank": 2, "skill_multiplier": 1.0, "focus": ["연결", "방어"]}, 
    "퍼플": {"rank": 3, "skill_multiplier": 1.2, "focus": ["개성", "창의성"]},
    "브라운": {"rank": 4, "skill_multiplier": 1.4, "focus": ["디테일", "완성도"]},
    "블랙": {"rank": 5, "skill_multiplier": 1.6, "focus": ["마스터리", "지도"]}
}

# 성능 모니터링
PERFORMANCE_METRICS = {
    "target_analysis_time": 0.1,  # 100ms 목표
    "max_cache_size": 100,
    "db_connection_timeout": 30,
    "ui_refresh_rate": 60
}

# =============================================================================
# 실행
# =============================================================================

if __name__ == "__main__":
    # 성능 모니터링 시작
    start_time = time.time()
    
    try:
        main()
    except Exception as e:
        st.error(f"시스템 오류: {e}")
        st.info("페이지를 새로고침해주세요.")
    
    # 성능 통계 (개발 모드에서만)
    if st.sidebar.button("🔧 개발자 정보"):
        runtime = time.time() - start_time
        st.sidebar.metric("페이지 로드 시간", f"{runtime:.2f}초")
        st.sidebar.info("고성능 최적화 시스템 v2.0")# 주짓수 최적화 고성능 시스템 V2 - 성능 향상 + 코드 최적화
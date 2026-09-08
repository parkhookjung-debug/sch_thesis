# 주짓수 대별 맞춤 훈련 시스템 - 고도화된 NLP 통합 최종 버전
# 필수 패키지: pip install streamlit pandas numpy scikit-learn requests
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
import sys

# =============================================================================
# 고도화된 NLP 시스템 (새로 통합)
# =============================================================================

@dataclass
class IntentPattern:
    """의도 분석을 위한 패턴 클래스"""
    intent: str
    patterns: List[str]
    difficulty_modifier: int  # -1: 쉽게, 0: 보통, 1: 어렵게
    confidence_boost: float

class EnhancedNLPProcessor:
    """고도화된 NLP 처리기 - 패턴 기반 + 문맥 분석"""
    
    def __init__(self):
        self.intent_patterns = self._load_intent_patterns()
        self.negation_words = ['안', '않', '없', '못', '금지', '피하', '싫', '어려워', '힘들어']
        self.intensity_words = {
            'high': ['집중적', '강하게', '빡세게', '열심히', '완벽', '마스터', '경기', '시합'],
            'medium': ['보통', '적당히', '무난하게', '일반적'],
            'low': ['가볍게', '천천히', '쉽게', '부드럽게', '조심스럽게']
        }
        self.time_extractors = {
            '30분': 30, '1시간': 60, '90분': 90, '2시간': 120,
            '짧게': 30, '길게': 90, '오래': 120
        }
        self.bjj_technique_map = self._build_technique_map()
        
        # 기존 NLP 호환성 유지
        self.level_keywords = {
            'beginner': ['초보', '초급', '새로운', '처음', '기초', '화이트'],
            'intermediate': ['중급', '중간', '어느정도', '보통', '경험', '블루', '퍼플', '하프'],
            'advanced': ['고급', '상급', '고수', '전문', '숙련', '마스터', '브라운', '블랙', '딥하프']
        }
        
        self.position_keywords = {
            'guard': ['가드', '가아드', 'guard', '하체', '다리', '하프', 'half', '하프가드', '딥하프', 'z가드', 'Z가드'],
            'mount': ['마운트', 'mount', '올라타기', '압박'],
            'side_control': ['사이드', '사이드컨트롤', 'side', '옆'],
            'back_control': ['백', '등', 'back', '뒤'],
            'submission': ['서브미션', '서브', '조르기', '잠그기', '관절기'],
            'sweep': ['스윕', '뒤집기', 'sweep', '역전'],
            'guard_pass': ['패스', 'pass', '가드패스', '뚫기']
        }
        
        self.time_keywords = {
            'short': ['짧은', '빠른', '30분', '짧게'],
            'medium': ['중간', '1시간', '보통'],
            'long': ['긴', '오래', '2시간', '길게']
        }
        
    def _load_intent_patterns(self) -> List[IntentPattern]:
        """의도 분석 패턴 로드"""
        return [
            IntentPattern(
                intent='learn',
                patterns=['배우고', '학습', '익히고', '습득', '처음', '시작', '배워보고'],
                difficulty_modifier=-1,
                confidence_boost=0.8
            ),
            IntentPattern(
                intent='review',
                patterns=['복습', '다시', '재연습', '점검', '확인', '정리'],
                difficulty_modifier=0,
                confidence_boost=0.7
            ),
            IntentPattern(
                intent='practice',
                patterns=['연습', '훈련', '드릴', '반복'],
                difficulty_modifier=0,
                confidence_boost=0.6
            ),
            IntentPattern(
                intent='avoid',
                patterns=['피하고', '제외', '빼고', '하지말고', '말고'],
                difficulty_modifier=-1,
                confidence_boost=0.9
            ),
            IntentPattern(
                intent='compete',
                patterns=['경기', '시합', '대회', '승급', '심사', '테스트'],
                difficulty_modifier=1,
                confidence_boost=0.9
            ),
            IntentPattern(
                intent='improve_weakness',
                patterns=['약해서', '취약', '당하는', '못하겠', '어려워서', '힘들어서', '자꾸 당해'],
                difficulty_modifier=-1,
                confidence_boost=0.8
            ),
            IntentPattern(
                intent='strengthen',
                patterns=['강화', '발전', '향상', '늘리고', '키우고', '마스터하고'],
                difficulty_modifier=1,
                confidence_boost=0.7
            )
        ]
    
    def _build_technique_map(self) -> Dict[str, Dict]:
        """BJJ 기술 매핑 테이블 (확장)"""
        return {
            # 가드 관련
            '하프가드': {'category': 'guard', 'difficulty': 2, 'aliases': ['하프', '반가드', '하프 가드']},
            '클로즈드가드': {'category': 'guard', 'difficulty': 1, 'aliases': ['클로즈드', '풀가드', '클로즈 가드']},
            '오픈가드': {'category': 'guard', 'difficulty': 2, 'aliases': ['오픈', '오픈 가드']},
            '딥하프가드': {'category': 'guard', 'difficulty': 4, 'aliases': ['딥하프', '딥 하프', '딥 하프 가드']},
            '버터플라이가드': {'category': 'guard', 'difficulty': 2, 'aliases': ['버터플라이', '나비가드']},
            '스파이더가드': {'category': 'guard', 'difficulty': 3, 'aliases': ['스파이더', '거미가드']},
            'Z가드': {'category': 'guard', 'difficulty': 3, 'aliases': ['z가드', '지가드']},
            
            # 서브미션
            '암바': {'category': 'submission', 'difficulty': 2, 'aliases': ['팔꺾기', '관절기', '암바']},
            '초크': {'category': 'submission', 'difficulty': 2, 'aliases': ['조르기', '목조르기', '체크']},
            '트라이앵글': {'category': 'submission', 'difficulty': 3, 'aliases': ['삼각', '트라이앵글 초크']},
            '기요틴': {'category': 'submission', 'difficulty': 2, 'aliases': ['기요틴 초크', '단두대']},
            '키무라': {'category': 'submission', 'difficulty': 2, 'aliases': ['키무라 락']},
            '리어네이키드초크': {'category': 'submission', 'difficulty': 2, 'aliases': ['리어네이키드', '뒤초크', 'RNC']},
            
            # 스윕
            '스윕': {'category': 'sweep', 'difficulty': 2, 'aliases': ['뒤집기', '역전', '스위프']},
            '시저스윕': {'category': 'sweep', 'difficulty': 2, 'aliases': ['시저', '가위스윕']},
            '힙범프스윕': {'category': 'sweep', 'difficulty': 1, 'aliases': ['힙범프', '엉덩이스윕']},
            '플라워스윕': {'category': 'sweep', 'difficulty': 2, 'aliases': ['플라워', '꽃스윕']},
            '하프가드스윕': {'category': 'sweep', 'difficulty': 2, 'aliases': ['하프스윕']},
            '올드스쿨스윕': {'category': 'sweep', 'difficulty': 3, 'aliases': ['올드스쿨']},
            
            # 패스
            '가드패스': {'category': 'guard_pass', 'difficulty': 2, 'aliases': ['패스', '뚫기', '가드 패스']},
            '토리안도패스': {'category': 'guard_pass', 'difficulty': 2, 'aliases': ['토리안도', '투우사패스']},
            '더블언더패스': {'category': 'guard_pass', 'difficulty': 2, 'aliases': ['더블언더', '더블 언더']},
            '하프가드패스': {'category': 'guard_pass', 'difficulty': 2, 'aliases': ['하프패스']},
            '크로스페이스패스': {'category': 'guard_pass', 'difficulty': 3, 'aliases': ['크로스페이스', '크로스 페이스']},
            
            # 포지션
            '마운트': {'category': 'mount', 'difficulty': 1, 'aliases': ['마운팅', '마운트 포지션']},
            '하이마운트': {'category': 'mount', 'difficulty': 2, 'aliases': ['하이 마운트', '높은마운트']},
            'S마운트': {'category': 'mount', 'difficulty': 3, 'aliases': ['에스마운트', 'S-마운트']},
            '사이드컨트롤': {'category': 'side_control', 'difficulty': 1, 'aliases': ['사이드', '옆 컨트롤', '사이드 컨트롤']},
            '니온벨리': {'category': 'side_control', 'difficulty': 2, 'aliases': ['무릎배', '니 온 벨리']},
            '백컨트롤': {'category': 'back_control', 'difficulty': 2, 'aliases': ['백', '등 컨트롤', '백 컨트롤']},
            '바디트라이앵글': {'category': 'back_control', 'difficulty': 3, 'aliases': ['바디트라이앵글', '몸삼각']}
        }
    
    def analyze_user_request(self, text: str) -> Dict:
        """향상된 자연어 분석"""
        text_lower = text.lower()
        
        # 1. 기본 분석
        base_analysis = {
            'level': self._detect_experience_level(text_lower),
            'positions': self._detect_positions_advanced(text_lower),
            'duration': self._extract_duration(text_lower),
            'gi_preference': self._detect_gi_preference(text_lower)
        }
        
        # 2. 의도 분석 (고도화)
        intent_analysis = self._analyze_intent(text_lower)
        
        # 3. 감정/제약사항 분석
        emotion_analysis = self._analyze_emotions_and_constraints(text_lower)
        
        # 4. 기술 특화 분석
        technique_analysis = self._analyze_specific_techniques(text_lower)
        
        # 5. 종합 분석
        final_analysis = {
            **base_analysis,
            **intent_analysis,
            **emotion_analysis,
            **technique_analysis,
            'confidence_score': self._calculate_confidence(text_lower, intent_analysis),
            'analysis_method': 'enhanced_pattern_based'
        }
        
        return final_analysis
    
    def _detect_experience_level(self, text: str) -> str:
        """경험 수준 감지 (맥락 고려)"""
        beginner_indicators = [
            '초보', '처음', '시작', '기초', '기본', '화이트', '새로', '잘 모르',
            '배우고', '익히고', '습득하고'
        ]
        advanced_indicators = [
            '고급', '상급', '마스터', '완벽', '브라운', '블랙', '경기', '승급', '심사',
            '딥하프', '고도화', '세밀하게'
        ]
        intermediate_indicators = [
            '중급', '블루', '퍼플', '어느정도', '경험', '익숙', '연습해봤'
        ]
        
        # 부정 표현 고려
        if any(word in text for word in ['잘 못하', '어려워', '힘들어', '취약', '자꾸 당해']):
            return 'beginner'  # 어려워한다 = 초보 수준으로 조정
        
        # 고급 표현 우선 확인
        if any(word in text for word in advanced_indicators):
            return 'advanced'
        elif any(word in text for word in intermediate_indicators):
            return 'intermediate'
        elif any(word in text for word in beginner_indicators):
            return 'beginner'
        
        return 'intermediate'  # 기본값
    
    def _detect_positions_advanced(self, text: str) -> List[str]:
        """향상된 포지션 감지"""
        detected = []
        
        # 고도화된 기술 매핑 확인
        for technique, info in self.bjj_technique_map.items():
            # 메인 기술명 확인
            if technique in text:
                detected.append(info['category'])
                continue
            
            # 별칭 확인
            for alias in info['aliases']:
                if alias in text:
                    detected.append(info['category'])
                    break
        
        # 기존 키워드 시스템과 병합
        for position, keywords in self.position_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected.append(position)
        
        # 중복 제거 및 우선순위 적용
        unique_positions = list(set(detected))
        
        # 더 구체적인 포지션이 있으면 일반적인 것 제거
        if 'guard' in unique_positions:
            specific_guards = ['half_guard', 'closed_guard', 'open_guard']
            if any(sg in text for sg in ['하프', '클로즈드', '오픈']):
                # 구체적인 가드가 언급되면 일반 가드 제거하지 않고 유지
                pass
        
        return unique_positions
    
    def _extract_duration(self, text: str) -> str:
        """시간 추출 (더 정교하게)"""
        for time_expr, minutes in self.time_extractors.items():
            if time_expr in text:
                if minutes <= 40:
                    return 'short'
                elif minutes <= 80:
                    return 'medium'
                else:
                    return 'long'
        
        # 맥락 기반 추론
        if any(word in text for word in ['가볍게', '짧게', '빠르게', '간단히']):
            return 'short'
        elif any(word in text for word in ['오래', '길게', '집중적', '완벽하게', '마스터']):
            return 'long'
        
        return 'medium'
    
    def _analyze_intent(self, text: str) -> Dict:
        """의도 분석 (핵심 개선사항)"""
        detected_intents = []
        total_confidence = 0
        difficulty_modifiers = []
        
        for pattern in self.intent_patterns:
            for keyword in pattern.patterns:
                if keyword in text:
                    detected_intents.append(pattern.intent)
                    total_confidence += pattern.confidence_boost
                    difficulty_modifiers.append(pattern.difficulty_modifier)
                    break
        
        # 의도가 없으면 기본값
        if not detected_intents:
            primary_intent = 'practice'
            confidence = 0.5
        else:
            # 가장 강한 의도 선택
            primary_intent = max(set(detected_intents), key=detected_intents.count)
            confidence = min(total_confidence / len(detected_intents), 1.0)
        
        # 난이도 선호도 계산
        if difficulty_modifiers:
            avg_modifier = sum(difficulty_modifiers) / len(difficulty_modifiers)
            if avg_modifier > 0.3:
                difficulty_pref = 'challenging'
            elif avg_modifier < -0.3:
                difficulty_pref = 'easy'
            else:
                difficulty_pref = 'normal'
        else:
            difficulty_pref = 'normal'
        
        return {
            'intent': primary_intent,
            'intent_confidence': confidence,
            'difficulty_preference': difficulty_pref,
            'detected_intents': detected_intents
        }
    
    def _analyze_emotions_and_constraints(self, text: str) -> Dict:
        """감정 및 제약사항 분석"""
        constraints = []
        emotions = []
        
        # 부상/건강 제약사항
        injury_patterns = ['부상', '아파', '무릎', '어깨', '허리', '목', '손목', '발목']
        for pattern in injury_patterns:
            if pattern in text:
                constraints.append(f'{pattern} 관련 제약')
        
        # 시간 제약
        if any(word in text for word in ['바쁜', '급하게', '시간이 없어']):
            constraints.append('시간 제약')
        
        # 감정 상태
        if any(word in text for word in ['좌절', '답답', '어려워', '힘들어', '자꾸 당해']):
            emotions.append('frustration')
        elif any(word in text for word in ['자신감', '잘하고', '만족']):
            emotions.append('confidence')
        elif any(word in text for word in ['불안', '걱정', '무서워']):
            emotions.append('anxiety')
        
        return {
            'concerns_or_limitations': ', '.join(constraints) if constraints else '',
            'emotional_state': emotions,
            'safety_priority': 'high' if constraints else 'normal'
        }
    
    def _analyze_specific_techniques(self, text: str) -> Dict:
        """특정 기술 분석"""
        mentioned_techniques = []
        technique_categories = []
        
        for technique, info in self.bjj_technique_map.items():
            if technique in text:
                mentioned_techniques.append(technique)
                technique_categories.append(info['category'])
            else:
                for alias in info['aliases']:
                    if alias in text:
                        mentioned_techniques.append(technique)
                        technique_categories.append(info['category'])
                        break
        
        return {
            'specific_techniques': mentioned_techniques,
            'technique_categories': list(set(technique_categories)),
            'training_focus': 'technique' if mentioned_techniques else 'general'
        }
    
    def _detect_gi_preference(self, text: str) -> str:
        """도복 선호도 감지"""
        if any(word in text for word in ['도복', 'gi', '기']):
            return 'gi'
        elif any(word in text for word in ['노기', 'nogi', 'no-gi', '래쉬가드']):
            return 'no-gi'
        return 'both'
    
    def _calculate_confidence(self, text: str, intent_analysis: Dict) -> float:
        """분석 신뢰도 계산"""
        base_confidence = 0.7
        
        # 텍스트 길이 보너스 (더 자세할수록 높은 신뢰도)
        length_bonus = min(len(text) / 100, 0.2)
        
        # 의도 분석 신뢰도
        intent_confidence = intent_analysis.get('intent_confidence', 0.5)
        
        # 구체적 기술 언급 보너스
        specific_bonus = 0.1 if any(tech in text for tech in self.bjj_technique_map.keys()) else 0
        
        final_confidence = min(base_confidence + length_bonus + (intent_confidence * 0.3) + specific_bonus, 1.0)
        return round(final_confidence, 2)

# 개선된 데이터베이스 연결 관리 시스템
# 기존 BJJDatabase 클래스를 완전히 교체하세요

import sqlite3
import contextlib
import logging
from typing import Dict, List, Optional, Iterator
import uuid
import hashlib
import json
from datetime import datetime

# 커스텀 예외 클래스
class DatabaseError(Exception):
    """데이터베이스 관련 예외"""
    pass

class ConnectionError(DatabaseError):
    """데이터베이스 연결 예외"""
    pass

class DataIntegrityError(DatabaseError):
    """데이터 무결성 예외"""
    pass

class ImprovedBJJDatabase:
    """개선된 BJJ 훈련 시스템 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = "bjj_training.db"):
        self.db_path = db_path
        self.logger = self._setup_logger()
        
        # 데이터베이스 초기화
        try:
            self.init_database()
            self.logger.info(f"Database initialized successfully: {db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise ConnectionError(f"데이터베이스 초기화 실패: {e}")
    
    def _setup_logger(self) -> logging.Logger:
        """로거 설정"""
        logger = logging.getLogger(f"BJJDatabase_{id(self)}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    @contextlib.contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """
        안전한 데이터베이스 연결 컨텍스트 매니저
        자동으로 연결을 열고 닫으며, 에러 발생시 롤백 처리
        """
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=10.0,  # 10초 타임아웃
                check_same_thread=False  # Streamlit에서 필요
            )
            # Row factory 설정으로 딕셔너리 형태 결과 반환
            conn.row_factory = sqlite3.Row
            
            # WAL 모드 설정 (동시 읽기 성능 향상)
            conn.execute("PRAGMA journal_mode=WAL")
            
            # 외래키 제약 조건 활성화
            conn.execute("PRAGMA foreign_keys=ON")
            
            self.logger.debug("Database connection established")
            yield conn
            
        except sqlite3.OperationalError as e:
            self.logger.error(f"Database operational error: {e}")
            if conn:
                conn.rollback()
            raise ConnectionError(f"데이터베이스 연결 오류: {e}")
            
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Database integrity error: {e}")
            if conn:
                conn.rollback()
            raise DataIntegrityError(f"데이터 무결성 오류: {e}")
            
        except Exception as e:
            self.logger.error(f"Unexpected database error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(f"예상치 못한 데이터베이스 오류: {e}")
            
        finally:
            if conn:
                try:
                    conn.close()
                    self.logger.debug("Database connection closed")
                except Exception as e:
                    self.logger.error(f"Error closing connection: {e}")
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 사용자 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    current_belt TEXT NOT NULL,
                    current_stripes INTEGER DEFAULT 0,
                    experience_months INTEGER DEFAULT 0,
                    gi_preference TEXT DEFAULT 'both',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    total_sessions INTEGER DEFAULT 0,
                    total_hours REAL DEFAULT 0.0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            # 훈련 세션 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS training_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    belt_level TEXT NOT NULL,
                    total_duration INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    difficulty_rating INTEGER,
                    enjoyment_rating INTEGER,
                    techniques_practiced TEXT, -- JSON string
                    program_data TEXT, -- JSON string
                    notes TEXT,
                    nlp_analysis TEXT, -- NLP 분석 결과
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # 사용자 선호도 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferred_positions TEXT, -- JSON string
                    avoided_techniques TEXT, -- JSON string
                    training_goals TEXT, -- JSON string
                    weekly_frequency INTEGER DEFAULT 3,
                    preferred_session_length INTEGER DEFAULT 60,
                    injury_considerations TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            ''')
            
            # 기술 마스터리 추적 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS technique_mastery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    technique_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    difficulty INTEGER NOT NULL,
                    practice_count INTEGER DEFAULT 0,
                    last_practiced TIMESTAMP,
                    mastery_level REAL DEFAULT 0.0, -- 0.0 to 1.0
                    success_rate REAL DEFAULT 0.0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    UNIQUE(user_id, technique_name)
                )
            ''')
            
            # 인덱스 생성 (성능 향상)
            self._create_indexes(cursor)
            
            conn.commit()
            self.logger.info("Database tables created/verified successfully")
    
    def _create_indexes(self, cursor):
        """성능 향상을 위한 인덱스 생성"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_training_sessions_user_id ON training_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_training_sessions_date ON training_sessions(session_date)",
            "CREATE INDEX IF NOT EXISTS idx_technique_mastery_user_id ON technique_mastery(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_technique_mastery_technique ON technique_mastery(technique_name)",
            "CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                self.logger.debug(f"Index created: {index_sql}")
            except sqlite3.Error as e:
                self.logger.warning(f"Failed to create index: {e}")
    
    def create_user(self, username: str, email: str, password: str, belt: str) -> str:
        """새 사용자 생성 (개선된 에러 처리)"""
        try:
            user_id = str(uuid.uuid4())
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 사용자 생성
                cursor.execute('''
                    INSERT INTO users (id, username, email, password_hash, current_belt)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, username, email, password_hash, belt))
                
                # 기본 선호도 설정
                cursor.execute('''
                    INSERT INTO user_preferences (user_id, preferred_positions, training_goals)
                    VALUES (?, ?, ?)
                ''', (user_id, json.dumps([]), json.dumps(['technique'])))
                
                conn.commit()
                self.logger.info(f"User created successfully: {username}")
                return user_id
                
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if "username" in error_msg:
                raise DataIntegrityError("이미 사용 중인 사용자명입니다.")
            elif "email" in error_msg:
                raise DataIntegrityError("이미 등록된 이메일입니다.")
            else:
                raise DataIntegrityError(f"데이터 무결성 오류: {e}")
                
        except Exception as e:
            self.logger.error(f"Failed to create user {username}: {e}")
            raise DatabaseError(f"사용자 생성 실패: {e}")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """사용자 인증 (개선된 에러 처리)"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, email, current_belt, current_stripes, 
                           experience_months, gi_preference, total_sessions, total_hours,
                           created_at, last_login
                    FROM users 
                    WHERE username = ? AND password_hash = ? AND is_active = 1
                ''', (username, password_hash))
                
                result = cursor.fetchone()
                
                if result:
                    # 마지막 로그인 시간 업데이트
                    cursor.execute('''
                        UPDATE users SET last_login = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (result['id'],))
                    conn.commit()
                    
                    user_data = dict(result)
                    self.logger.info(f"User authenticated successfully: {username}")
                    return user_data
                else:
                    self.logger.warning(f"Authentication failed for user: {username}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Authentication error for {username}: {e}")
            raise DatabaseError(f"인증 중 오류가 발생했습니다: {e}")
    
    def check_username_availability(self, username: str) -> bool:
        """사용자명 사용 가능 여부 확인 (개선된 버전)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM users WHERE username = ?", 
                    (username,)
                )
                result = cursor.fetchone()
                return result['count'] == 0
                
        except Exception as e:
            self.logger.error(f"Error checking username availability: {e}")
            # 에러 발생시 안전하게 False 반환 (중복으로 간주)
            return False
    
    def check_email_availability(self, email: str) -> bool:
        """이메일 사용 가능 여부 확인"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM users WHERE email = ?", 
                    (email,)
                )
                result = cursor.fetchone()
                return result['count'] == 0
                
        except Exception as e:
            self.logger.error(f"Error checking email availability: {e}")
            return False
    
    def save_training_session(self, session_data: Dict) -> str:
        """훈련 세션 저장 (트랜잭션 안전성 강화)"""
        try:
            session_id = str(uuid.uuid4())
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 훈련 세션 저장
                cursor.execute('''
                    INSERT INTO training_sessions (
                        id, user_id, belt_level, total_duration, completion_rate,
                        difficulty_rating, enjoyment_rating, techniques_practiced,
                        program_data, notes, nlp_analysis
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session_id,
                    session_data['user_id'],
                    session_data['belt_level'],
                    session_data['total_duration'],
                    session_data['completion_rate'],
                    session_data.get('difficulty_rating'),
                    session_data.get('enjoyment_rating'),
                    json.dumps(session_data.get('techniques_practiced', [])),
                    json.dumps(session_data.get('program_data', {})),
                    session_data.get('notes', ''),
                    json.dumps(session_data.get('nlp_analysis', {}))
                ))
                
                # 사용자 통계 업데이트 (원자적 연산)
                cursor.execute('''
                    UPDATE users 
                    SET total_sessions = total_sessions + 1,
                        total_hours = total_hours + ?,
                        last_login = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (session_data['total_duration'] / 60.0, session_data['user_id']))
                
                # 변경된 행 수 확인
                if cursor.rowcount == 0:
                    raise DatabaseError("사용자를 찾을 수 없습니다.")
                
                conn.commit()
                self.logger.info(f"Training session saved: {session_id}")
                return session_id
                
        except Exception as e:
            self.logger.error(f"Failed to save training session: {e}")
            raise DatabaseError(f"훈련 세션 저장 실패: {e}")
    
    def get_user_stats(self, user_id: str) -> Dict:
        """사용자 통계 조회 (개선된 에러 처리)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 기본 사용자 정보
                cursor.execute('''
                    SELECT current_belt, total_sessions, total_hours, experience_months,
                           created_at, last_login
                    FROM users WHERE id = ?
                ''', (user_id,))
                user_info = cursor.fetchone()
                
                if not user_info:
                    raise DatabaseError("사용자를 찾을 수 없습니다.")
                
                # 최근 세션들
                cursor.execute('''
                    SELECT session_date, completion_rate, difficulty_rating, enjoyment_rating
                    FROM training_sessions 
                    WHERE user_id = ? 
                    ORDER BY session_date DESC 
                    LIMIT 10
                ''', (user_id,))
                recent_sessions = [dict(row) for row in cursor.fetchall()]
                
                # 기술 마스터리
                cursor.execute('''
                    SELECT technique_name, category, practice_count, mastery_level
                    FROM technique_mastery 
                    WHERE user_id = ? 
                    ORDER BY mastery_level DESC
                    LIMIT 20
                ''', (user_id,))
                top_techniques = [dict(row) for row in cursor.fetchall()]
                
                # 통계 계산
                import numpy as np
                avg_completion_rate = (
                    np.mean([s['completion_rate'] for s in recent_sessions]) 
                    if recent_sessions else 0
                )
                avg_difficulty = (
                    np.mean([s['difficulty_rating'] for s in recent_sessions 
                            if s['difficulty_rating'] is not None]) 
                    if recent_sessions else 0
                )
                
                result = {
                    'current_belt': user_info['current_belt'],
                    'total_sessions': user_info['total_sessions'],
                    'total_hours': user_info['total_hours'],
                    'experience_months': user_info['experience_months'],
                    'recent_sessions': recent_sessions,
                    'top_techniques': top_techniques,
                    'avg_completion_rate': avg_completion_rate,
                    'avg_difficulty': avg_difficulty,
                    'created_at': user_info['created_at'],
                    'last_login': user_info['last_login']
                }
                
                self.logger.debug(f"User stats retrieved for: {user_id}")
                return result
                
        except Exception as e:
            self.logger.error(f"Failed to get user stats for {user_id}: {e}")
            raise DatabaseError(f"사용자 통계 조회 실패: {e}")
    
    def update_technique_mastery(self, user_id: str, technique_name: str, 
                               category: str, difficulty: int, success: bool):
        """기술 마스터리 업데이트 (UPSERT 패턴 사용)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 기존 기록 확인
                cursor.execute('''
                    SELECT practice_count, mastery_level, success_rate
                    FROM technique_mastery 
                    WHERE user_id = ? AND technique_name = ?
                ''', (user_id, technique_name))
                
                result = cursor.fetchone()
                
                if result:
                    # 기존 기록 업데이트
                    practice_count = result['practice_count']
                    mastery_level = result['mastery_level']
                    success_rate = result['success_rate']
                    
                    new_practice_count = practice_count + 1
                    new_success_rate = (
                        (success_rate * practice_count + (1.0 if success else 0.0)) 
                        / new_practice_count
                    )
                    new_mastery_level = min(1.0, mastery_level + (0.1 if success else 0.05))
                    
                    cursor.execute('''
                        UPDATE technique_mastery 
                        SET practice_count = ?, mastery_level = ?, success_rate = ?, 
                            last_practiced = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND technique_name = ?
                    ''', (new_practice_count, new_mastery_level, new_success_rate, 
                          user_id, technique_name))
                else:
                    # 새 기록 생성
                    cursor.execute('''
                        INSERT INTO technique_mastery (
                            user_id, technique_name, category, difficulty, 
                            practice_count, mastery_level, success_rate, last_practiced
                        ) VALUES (?, ?, ?, ?, 1, ?, ?, CURRENT_TIMESTAMP)
                    ''', (user_id, technique_name, category, difficulty, 
                          0.1 if success else 0.05, 1.0 if success else 0.5))
                
                conn.commit()
                self.logger.debug(f"Technique mastery updated: {technique_name} for {user_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to update technique mastery: {e}")
            raise DatabaseError(f"기술 마스터리 업데이트 실패: {e}")
    
    def get_database_health(self) -> Dict:
        """데이터베이스 상태 확인"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 테이블별 레코드 수 확인
                tables = ['users', 'training_sessions', 'user_preferences', 'technique_mastery']
                health_info = {'status': 'healthy', 'tables': {}}
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cursor.fetchone()['count']
                    health_info['tables'][table] = count
                
                # 데이터베이스 크기 확인
                cursor.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                health_info['size_mb'] = (page_count * page_size) / (1024 * 1024)
                health_info['last_check'] = datetime.now().isoformat()
                
                return health_info
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}

# =============================================================================
# 기존 코드와의 호환성을 위한 래퍼
# =============================================================================

# 기존 BJJDatabase를 ImprovedBJJDatabase로 교체
BJJDatabase = ImprovedBJJDatabase

# =============================================================================
# 주짓수 벨트 시스템 정의
# =============================================================================

BJJ_BELTS = {
    "🤍 화이트 벨트": {
        "level": "beginner",
        "experience_months": "0-12개월",
        "max_difficulty": 2,
        "description": "기본기 위주, 안전한 훈련",
        "emoji": "🤍",
        "stripes_available": True
    },
    "🔵 블루 벨트": {
        "level": "intermediate", 
        "experience_months": "12-36개월",
        "max_difficulty": 3,
        "description": "기초 기술 숙련, 연결 기술 학습",
        "emoji": "🔵",
        "stripes_available": True
    },
    "🟣 퍼플 벨트": {
        "level": "intermediate",
        "experience_months": "36-60개월", 
        "max_difficulty": 4,
        "description": "중급 기술, 개인 스타일 개발",
        "emoji": "🟣",
        "stripes_available": True
    },
    "🟤 브라운 벨트": {
        "level": "advanced",
        "experience_months": "60-84개월",
        "max_difficulty": 5,
        "description": "고급 기술, 교육 역할",
        "emoji": "🟤",
        "stripes_available": True
    },
    "⚫ 블랙 벨트": {
        "level": "advanced",
        "experience_months": "84개월+",
        "max_difficulty": 5,
        "description": "마스터 레벨, 창의적 응용",
        "emoji": "⚫",
        "stripes_available": False
    }
}

STRIPE_OPTIONS = ["스트라이프 없음", "1줄", "2줄", "3줄", "4줄"]

BELT_FOCUS_AREAS = {
    "🤍 화이트 벨트": ["기본자세", "브레이크폴", "에스케이프", "기본 서브미션"],
    "🔵 블루 벨트": ["가드 플레이", "패스 가드", "포지션 트랜지션", "기본 스윕"],
    "🟣 퍼플 벨트": ["고급 가드", "연결 기술", "프레셔 패스", "다양한 서브미션"],
    "🟤 브라운 벨트": ["개인 스타일", "고급 연결", "카운터 기술", "게임 플랜"],
    "⚫ 블랙 벨트": ["완성도", "창의적 응용", "교육 기술", "마인드셋"]
}

# =============================================================================
# 기술 데이터베이스 (확장)
# =============================================================================

class BJJTechniqueDatabase:
    def __init__(self):
        self.techniques = self._load_techniques()
    
    def _load_techniques(self) -> List[Dict]:
        techniques_data = [
            # 가드 기술들 (확장)
            {
                'id': 1, 'name': '클로즈드 가드', 'name_en': 'Closed Guard',
                'category': 'guard', 'difficulty': 1, 'position': 'bottom', 'duration': 10,
                'description': '다리로 상대방의 허리를 감싸 컨트롤하는 기본 가드',
                'gi_no_gi': 'both', 'aliases': ['클로즈드', '풀가드']
            },
            {
                'id': 2, 'name': '오픈 가드', 'name_en': 'Open Guard',
                'category': 'guard', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '다리를 열어 다양한 각도에서 상대방을 컨트롤',
                'gi_no_gi': 'both', 'aliases': ['오픈']
            },
            {
                'id': 3, 'name': '델라리바 가드', 'name_en': 'De La Riva Guard',
                'category': 'guard', 'difficulty': 4, 'position': 'bottom', 'duration': 15,
                'description': '상대방의 다리 뒤쪽에 후킹하는 고급 오픈 가드',
                'gi_no_gi': 'both', 'aliases': ['DLR', '델라리바']
            },
            {
                'id': 4, 'name': '스파이더 가드', 'name_en': 'Spider Guard',
                'category': 'guard', 'difficulty': 3, 'position': 'bottom', 'duration': 15,
                'description': '상대방의 소매를 잡고 발로 팔을 컨트롤하는 가드',
                'gi_no_gi': 'gi', 'aliases': ['거미가드', '스파이더']
            },
            {
                'id': 5, 'name': '버터플라이 가드', 'name_en': 'Butterfly Guard',
                'category': 'guard', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '앉은 상태에서 발로 상대방의 다리를 후킹',
                'gi_no_gi': 'both', 'aliases': ['나비가드', '버터플라이']
            },
            
            # 하프 가드 시리즈 (확장)
            {
                'id': 23, 'name': '하프 가드', 'name_en': 'Half Guard',
                'category': 'guard', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '한쪽 다리만 감싸는 가드 포지션, 방어와 공격 모두 가능',
                'gi_no_gi': 'both', 'aliases': ['하프', '반가드']
            },
            {
                'id': 24, 'name': '딥 하프 가드', 'name_en': 'Deep Half Guard',
                'category': 'guard', 'difficulty': 4, 'position': 'bottom', 'duration': 15,
                'description': '상대방의 다리 깊숙이 들어가는 고급 하프 가드',
                'gi_no_gi': 'both', 'aliases': ['딥하프', '딥 하프']
            },
            {
                'id': 25, 'name': 'Z 가드', 'name_en': 'Z Guard',
                'category': 'guard', 'difficulty': 3, 'position': 'bottom', 'duration': 12,
                'description': '무릎 방패를 만드는 하프 가드 변형',
                'gi_no_gi': 'both', 'aliases': ['z가드', '지가드']
            },
            
            # 패스 가드 (확장)
            {
                'id': 6, 'name': '토리안도 패스', 'name_en': 'Toreando Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '상대방의 다리를 옆으로 밀어내며 패스하는 기술',
                'gi_no_gi': 'both', 'aliases': ['토리안도', '투우사패스']
            },
            {
                'id': 7, 'name': '더블 언더 패스', 'name_en': 'Double Under Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 12,
                'description': '양손으로 상대방의 다리 밑을 감싸며 압박하는 패스',
                'gi_no_gi': 'both', 'aliases': ['더블언더']
            },
            {
                'id': 30, 'name': '하프 가드 패스', 'name_en': 'Half Guard Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '하프 가드를 무력화하고 사이드 컨트롤로 패스',
                'gi_no_gi': 'both', 'aliases': ['하프패스']
            },
            {
                'id': 31, 'name': '크로스페이스 패스', 'name_en': 'Crossface Pass',
                'category': 'guard_pass', 'difficulty': 3, 'position': 'top', 'duration': 12,
                'description': '크로스페이스 압박으로 하프 가드 패스',
                'gi_no_gi': 'both', 'aliases': ['크로스페이스']
            },
            
            # 마운트 (확장)
            {
                'id': 8, 'name': '마운트 컨트롤', 'name_en': 'Mount Control',
                'category': 'mount', 'difficulty': 1, 'position': 'top', 'duration': 8,
                'description': '마운트 포지션에서 안정적으로 컨트롤 유지',
                'gi_no_gi': 'both', 'aliases': ['마운트', '마운팅']
            },
            {
                'id': 9, 'name': '하이 마운트', 'name_en': 'High Mount',
                'category': 'mount', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '상대방의 겨드랑이 쪽으로 올라가는 마운트',
                'gi_no_gi': 'both', 'aliases': ['하이 마운트', '높은마운트']
            },
            {
                'id': 10, 'name': 'S-마운트', 'name_en': 'S-Mount',
                'category': 'mount', 'difficulty': 3, 'position': 'top', 'duration': 12,
                'description': 'S자 형태로 다리를 배치하는 마운트 변형',
                'gi_no_gi': 'both', 'aliases': ['에스마운트', 'S마운트']
            },
            
            # 사이드 컨트롤 (확장)
            {
                'id': 11, 'name': '사이드 컨트롤', 'name_en': 'Side Control',
                'category': 'side_control', 'difficulty': 1, 'position': 'top', 'duration': 8,
                'description': '상대방의 옆에서 컨트롤하는 기본 포지션',
                'gi_no_gi': 'both', 'aliases': ['사이드', '옆 컨트롤']
            },
            {
                'id': 12, 'name': '니 온 벨리', 'name_en': 'Knee on Belly',
                'category': 'side_control', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '무릎으로 상대방의 배를 압박하는 포지션',
                'gi_no_gi': 'both', 'aliases': ['무릎배', '니온벨리']
            },
            
            # 백 컨트롤 (확장)
            {
                'id': 13, 'name': '백 컨트롤', 'name_en': 'Back Control',
                'category': 'back_control', 'difficulty': 2, 'position': 'back', 'duration': 12,
                'description': '상대방의 등 뒤에서 후크로 컨트롤',
                'gi_no_gi': 'both', 'aliases': ['백', '등 컨트롤']
            },
            {
                'id': 14, 'name': '바디 트라이앵글', 'name_en': 'Body Triangle',
                'category': 'back_control', 'difficulty': 3, 'position': 'back', 'duration': 15,
                'description': '다리로 삼각형을 만들어 더 강하게 컨트롤',
                'gi_no_gi': 'both', 'aliases': ['몸삼각', '바디트라이앵글']
            },
            
            # 서브미션 (확장)
            {
                'id': 15, 'name': '리어 네이키드 초크', 'name_en': 'Rear Naked Choke',
                'category': 'submission', 'difficulty': 2, 'position': 'back', 'duration': 8,
                'description': '뒤에서 목을 조르는 기본 초크',
                'gi_no_gi': 'both', 'aliases': ['RNC', '뒤초크', '리어네이키드']
            },
            {
                'id': 16, 'name': '마운트 암바', 'name_en': 'Armbar from Mount',
                'category': 'submission', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '마운트에서 팔을 꺾는 관절기',
                'gi_no_gi': 'both', 'aliases': ['마운트암바', '암바']
            },
            {
                'id': 17, 'name': '트라이앵글 초크', 'name_en': 'Triangle Choke',
                'category': 'submission', 'difficulty': 3, 'position': 'bottom', 'duration': 12,
                'description': '다리로 삼각형을 만들어 목을 조르는 기술',
                'gi_no_gi': 'both', 'aliases': ['삼각', '트라이앵글']
            },
            {
                'id': 18, 'name': '키무라', 'name_en': 'Kimura',
                'category': 'submission', 'difficulty': 2, 'position': 'various', 'duration': 10,
                'description': '어깨 관절을 공격하는 관절기',
                'gi_no_gi': 'both', 'aliases': ['키무라락']
            },
            {
                'id': 19, 'name': '기요틴 초크', 'name_en': 'Guillotine Choke',
                'category': 'submission', 'difficulty': 2, 'position': 'various', 'duration': 10,
                'description': '앞에서 목을 감싸 조르는 초크',
                'gi_no_gi': 'both', 'aliases': ['기요틴', '단두대']
            },
            
            # 스윕 (확장)
            {
                'id': 20, 'name': '시저 스윕', 'name_en': 'Scissor Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 10,
                'description': '다리를 가위처럼 사용하는 스윕',
                'gi_no_gi': 'both', 'aliases': ['시저', '가위스윕']
            },
            {
                'id': 21, 'name': '힙 범프 스윕', 'name_en': 'Hip Bump Sweep',
                'category': 'sweep', 'difficulty': 1, 'position': 'bottom', 'duration': 8,
                'description': '엉덩이로 밀어내는 기본 스윕',
                'gi_no_gi': 'both', 'aliases': ['힙범프', '엉덩이스윕']
            },
            {
                'id': 22, 'name': '플라워 스윕', 'name_en': 'Flower Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '상대방의 팔과 다리를 동시에 컨트롤하는 스윕',
                'gi_no_gi': 'gi', 'aliases': ['플라워', '꽃스윕']
            },
            {
                'id': 26, 'name': '하프 가드 스윕', 'name_en': 'Half Guard Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 10,
                'description': '하프 가드에서 언더훅을 이용한 기본 스윕',
                'gi_no_gi': 'both', 'aliases': ['하프스윕']
            },
            {
                'id': 27, 'name': '올드 스쿨 스윕', 'name_en': 'Old School Sweep',
                'category': 'sweep', 'difficulty': 3, 'position': 'bottom', 'duration': 12,
                'description': '하프 가드에서 상대방의 발목을 잡는 클래식 스윕',
                'gi_no_gi': 'both', 'aliases': ['올드스쿨']
            },
            {
                'id': 28, 'name': '딥 하프 스윕', 'name_en': 'Deep Half Sweep',
                'category': 'sweep', 'difficulty': 4, 'position': 'bottom', 'duration': 15,
                'description': '딥 하프 가드에서 실행하는 고급 스윕',
                'gi_no_gi': 'both', 'aliases': ['딥하프스윕']
            },
            
            # 하프 가드 서브미션
            {
                'id': 29, 'name': '하프 가드 킴플렉스', 'name_en': 'Half Guard Kimplex',
                'category': 'submission', 'difficulty': 4, 'position': 'bottom', 'duration': 12,
                'description': '하프 가드에서 다리를 이용한 키무라 변형',
                'gi_no_gi': 'both', 'aliases': ['킴플렉스']
            }
        ]
        
        return techniques_data
    
    def filter_techniques(self, max_difficulty: int = None, category: str = None, 
                         gi_preference: str = None, specific_techniques: List[str] = None) -> List[Dict]:
        """기술 필터링 (고도화)"""
        filtered = self.techniques.copy()
        
        # 특정 기술이 요청된 경우 우선 처리
        if specific_techniques:
            specific_filtered = []
            for tech in filtered:
                if tech['name'] in specific_techniques:
                    specific_filtered.append(tech)
                elif any(alias in specific_techniques for alias in tech.get('aliases', [])):
                    specific_filtered.append(tech)
            
            if specific_filtered:
                filtered = specific_filtered
        
        if max_difficulty:
            filtered = [t for t in filtered if t['difficulty'] <= max_difficulty]
        
        if category:
            filtered = [t for t in filtered if t['category'] == category]
        
        if gi_preference and gi_preference != 'both':
            filtered = [t for t in filtered if t['gi_no_gi'] in [gi_preference, 'both']]
        
        return filtered

# =============================================================================
# 스마트 훈련 프로그램 생성기 (고도화)
# =============================================================================

class SmartTrainingGenerator:
    def __init__(self, database: BJJTechniqueDatabase):
        self.db = database
        self.duration_map = {'short': 30, 'medium': 60, 'long': 90}
    
    def generate_program(self, analysis: Dict, belt_info: Dict) -> Dict:
        """고도화된 프로그램 생성 (NLP 분석 결과 활용)"""
        max_difficulty = belt_info['max_difficulty']
        total_duration = self.duration_map[analysis['duration']]
        
        # NLP 분석 결과 활용
        intent = analysis.get('intent', 'practice')
        difficulty_pref = analysis.get('difficulty_preference', 'normal')
        specific_techniques = analysis.get('specific_techniques', [])
        safety_priority = analysis.get('safety_priority', 'normal')
        
        # 난이도 조정
        if difficulty_pref == 'easy' or safety_priority == 'high':
            max_difficulty = max(1, max_difficulty - 1)
        elif difficulty_pref == 'challenging':
            max_difficulty = min(5, max_difficulty + 1)
        
        # 기술 필터링
        available_techniques = self.db.filter_techniques(
            max_difficulty=max_difficulty,
            gi_preference=analysis['gi_preference'],
            specific_techniques=specific_techniques
        )
        
        # 포지션별 기술 선별
        if analysis['positions']:
            position_techniques = []
            for position in analysis['positions']:
                position_techniques.extend([
                    t for t in available_techniques if t['category'] == position
                ])
            if position_techniques:
                available_techniques = position_techniques
        
        # 의도에 따른 프로그램 구성 조정
        program_structure = self._adjust_program_structure(intent, total_duration)
        
        program = {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_duration': total_duration,
                'belt': belt_info['emoji'] + ' ' + [k for k, v in BJJ_BELTS.items() if v == belt_info][0].split()[1],
                'max_difficulty': max_difficulty,
                'intent': intent,
                'difficulty_preference': difficulty_pref,
                'nlp_analysis': analysis
            },
            'warm_up': self._generate_warmup(program_structure['warmup']),
            'main_session': self._generate_main_session_advanced(
                available_techniques, 
                program_structure['main'], 
                intent, 
                specific_techniques
            ),
            'cool_down': self._generate_cooldown(program_structure['cooldown'])
        }
        
        return program
    
    def _adjust_program_structure(self, intent: str, total_duration: int) -> Dict:
        """의도에 따른 프로그램 구조 조정"""
        base_structure = {
            'warmup': int(total_duration * 0.2),
            'main': int(total_duration * 0.6),
            'cooldown': int(total_duration * 0.2)
        }
        
        if intent == 'learn':
            # 학습 의도: 워밍업 길게, 메인 세션 여유롭게
            base_structure['warmup'] = int(total_duration * 0.25)
            base_structure['main'] = int(total_duration * 0.55)
            base_structure['cooldown'] = int(total_duration * 0.2)
        elif intent == 'compete':
            # 경기 준비: 메인 세션 강화, 쿨다운 중요
            base_structure['warmup'] = int(total_duration * 0.15)
            base_structure['main'] = int(total_duration * 0.7)
            base_structure['cooldown'] = int(total_duration * 0.15)
        elif intent == 'improve_weakness':
            # 약점 보완: 워밍업 충분히, 메인 집중
            base_structure['warmup'] = int(total_duration * 0.3)
            base_structure['main'] = int(total_duration * 0.5)
            base_structure['cooldown'] = int(total_duration * 0.2)
        
        return base_structure
    
    def _generate_main_session_advanced(self, techniques: List[Dict], duration: int, 
                                      intent: str, specific_techniques: List[str]) -> List[Dict]:
        """고도화된 메인 세션 생성"""
        if not techniques:
            return []
        
        # 의도에 따른 기술 수 조정
        if intent == 'learn':
            num_techniques = min(len(techniques), max(2, duration // 20))  # 더 적은 기술, 더 많은 시간
        elif intent == 'strengthen' or intent == 'compete':
            num_techniques = min(len(techniques), max(4, duration // 10))  # 더 많은 기술
        else:
            num_techniques = min(len(techniques), max(3, duration // 12))
        
        # 특정 기술이 요청된 경우 우선순위 부여
        if specific_techniques:
            priority_techniques = [t for t in techniques if t['name'] in specific_techniques]
            other_techniques = [t for t in techniques if t['name'] not in specific_techniques]
            
            # 우선순위 기술을 먼저 포함
            selected_techniques = priority_techniques[:num_techniques]
            remaining_slots = num_techniques - len(selected_techniques)
            
            if remaining_slots > 0 and other_techniques:
                selected_techniques.extend(random.sample(other_techniques, 
                                                       min(remaining_slots, len(other_techniques))))
        else:
            selected_techniques = random.sample(techniques, num_techniques)
        
        time_per_technique = duration // len(selected_techniques)
        
        main_session = []
        for tech in selected_techniques:
            # 의도에 따른 시간 조정
            adjusted_duration = time_per_technique
            if intent == 'learn' and tech['name'] in specific_techniques:
                adjusted_duration = int(time_per_technique * 1.5)  # 학습 기술에 더 많은 시간
            elif intent == 'improve_weakness':
                adjusted_duration = int(time_per_technique * 1.3)  # 약점 보완에 더 많은 시간
            
            session_item = {
                'technique': tech['name'],
                'category': tech['category'],
                'difficulty': tech['difficulty'],
                'duration': adjusted_duration,
                'description': tech['description'],
                'difficulty_stars': '⭐' * tech['difficulty'],
                'aliases': tech.get('aliases', []),
                'intent_matched': tech['name'] in specific_techniques if specific_techniques else False
            }
            main_session.append(session_item)
        
        return main_session
    
    def _generate_warmup(self, duration: int) -> List[Dict]:
        """워밍업 생성"""
        warmup_exercises = [
            {'name': '관절 돌리기', 'duration': 3, 'description': '목, 어깨, 허리 관절 풀기'},
            {'name': '동적 스트레칭', 'duration': 4, 'description': '다리 벌리기, 허리 돌리기'},
            {'name': '기본 무브먼트', 'duration': 3, 'description': '쉬림프, 브릿지 연습'},
            {'name': '가벼운 롤링', 'duration': 5, 'description': '몸풀기용 가벼운 롤링'}
        ]
        
        selected = []
        current_duration = 0
        for exercise in warmup_exercises:
            if current_duration + exercise['duration'] <= duration:
                selected.append(exercise)
                current_duration += exercise['duration']
            if current_duration >= duration:
                break
        
        return selected
    
    def _generate_cooldown(self, duration: int) -> List[Dict]:
        """쿨다운 생성"""
        cooldown_exercises = [
            {'name': '정적 스트레칭', 'duration': duration // 2, 'description': '어깨, 허리, 다리 스트레칭'},
            {'name': '호흡 정리', 'duration': duration // 2, 'description': '복식호흡으로 심박수 안정화'}
        ]
        
        return cooldown_exercises

# =============================================================================
# YouTube 추천 시스템 (고도화)
# =============================================================================

class YouTubeRecommendationSystem:
    def __init__(self):
        # 유명 BJJ 강사들과 채널
        self.bjj_instructors = {
            'beginner': ['Gracie Breakdown', 'StephanKesting', 'GrappleArts', 'Gracie University'],
            'intermediate': ['BJJ Fanatics', 'Keenan Online', 'JiuJitsuX', 'ZombieProofBJJ'],
            'advanced': ['John Danaher', 'Gordon Ryan', 'Lachlan Giles', 'Craig Jones', 'Ryan Hall']
        }
        
        # 기술별 추가 검색 키워드
        self.technique_keywords = {
            'guard': ['guard retention', 'guard attack', 'bottom game'],
            'mount': ['mount control', 'mount attack', 'top control'],
            'side_control': ['side control escape', 'side mount', 'crossface'],
            'back_control': ['back mount', 'rear mount', 'back attack'],
            'submission': ['submission finish', 'tap', 'choke', 'joint lock'],
            'sweep': ['guard sweep', 'reversal', 'bottom to top'],
            'guard_pass': ['guard passing', 'pass the guard', 'top game']
        }
    
    def create_youtube_search_url(self, query: str) -> str:
        """YouTube 검색 URL 생성"""
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        return f"https://www.youtube.com/results?search_query={encoded_query}"
    
    def get_recommendations(self, program: Dict) -> List[Dict]:
        """고도화된 추천 시스템 (NLP 분석 활용)"""
        recommendations = []
        belt_level = program['metadata'].get('belt', '🤍 화이트')
        intent = program['metadata'].get('intent', 'practice')
        nlp_analysis = program['metadata'].get('nlp_analysis', {})
        
        for session_item in program['main_session']:
            technique_name = session_item['technique']
            category = session_item['category']
            difficulty = session_item.get('difficulty', 1)
            is_priority = session_item.get('intent_matched', False)
            
            # 의도와 우선순위에 따른 검색 쿼리 생성
            search_queries = self._create_intent_aware_queries(
                technique_name, category, difficulty, intent, is_priority
            )
            
            # 상위 추천만 선택
            top_queries = search_queries[:2 if is_priority else 1]
            
            for i, query_info in enumerate(top_queries):
                search_url = self.create_youtube_search_url(query_info['search_query'])
                
                recommendation = {
                    'technique': technique_name,
                    'video': {
                        'title': query_info['title'],
                        'channel': 'YouTube 실시간 검색',
                        'url': search_url,
                        'search_type': query_info['type'],
                        'query': query_info['search_query']
                    },
                    'why_recommended': self._generate_intent_aware_reason(
                        technique_name, query_info['type'], intent, is_priority
                    ),
                    'quality_indicator': self._get_quality_indicator(query_info['type'], i),
                    'search_tips': self._get_search_tips(query_info['type']),
                    'priority': 'high' if is_priority else 'normal'
                }
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _create_intent_aware_queries(self, technique_name: str, category: str, 
                                   difficulty: int, intent: str, is_priority: bool) -> List[Dict]:
        """의도를 고려한 검색 쿼리 생성"""
        queries = []
        
        # 기본 검색
        basic_query = f"{technique_name} BJJ tutorial"
        queries.append({
            'title': f'{technique_name} - 기본 튜토리얼',
            'search_query': basic_query,
            'type': '기본 학습',
            'priority': 1
        })
        
        # 의도별 특화 검색
        if intent == 'learn':
            learn_query = f"{technique_name} BJJ beginner step by step"
            queries.append({
                'title': f'{technique_name} - 초보자 단계별',
                'search_query': learn_query,
                'type': '단계별 학습',
                'priority': 0
            })
        elif intent == 'improve_weakness':
            improve_query = f"{technique_name} BJJ common mistakes details"
            queries.append({
                'title': f'{technique_name} - 실수 교정',
                'search_query': improve_query,
                'type': '약점 보완',
                'priority': 0
            })
        elif intent == 'compete':
            compete_query = f"{technique_name} BJJ competition high level"
            queries.append({
                'title': f'{technique_name} - 경기용 고급',
                'search_query': compete_query,
                'type': '경기 준비',
                'priority': 0
            })
        elif intent == 'strengthen':
            advanced_query = f"{technique_name} BJJ advanced variations"
            queries.append({
                'title': f'{technique_name} - 고급 변형',
                'search_query': advanced_query,
                'type': '고급 강화',
                'priority': 0
            })
        
        # 우선순위 기술에 대한 추가 검색
        if is_priority:
            detailed_query = f"{technique_name} BJJ breakdown analysis"
            queries.append({
                'title': f'{technique_name} - 상세 분석',
                'search_query': detailed_query,
                'type': '상세 분석',
                'priority': 2
            })
        
        return sorted(queries, key=lambda x: x['priority'])
    
    def _generate_intent_aware_reason(self, technique: str, search_type: str, 
                                    intent: str, is_priority: bool) -> str:
        """의도를 고려한 추천 이유 생성"""
        base_reasons = {
            '기본 학습': f"{technique} 기본 학습을 위한 검증된 튜토리얼",
            '단계별 학습': f"{technique}을 처음 배우시는 분을 위한 단계별 가이드",
            '약점 보완': f"{technique}에서 흔한 실수를 교정하고 개선하는 방법",
            '경기 준비': f"{technique}의 경기 활용법과 고급 테크닉",
            '고급 강화': f"{technique}의 다양한 변형과 응용법",
            '상세 분석': f"{technique}의 세밀한 디테일과 핵심 포인트"
        }
        
        reason = base_reasons.get(search_type, f"{technique} 관련 고품질 영상")
        
        if is_priority:
            reason = f"🎯 우선 학습 기술: " + reason
        
        intent_context = {
            'learn': "차근차근 배우시는 데 적합합니다",
            'improve_weakness': "약점을 보완하는 데 도움이 됩니다",
            'compete': "경기력 향상에 도움이 됩니다",
            'strengthen': "기술을 한 단계 발전시키는 데 유용합니다"
        }
        
        if intent in intent_context:
            reason += f" - {intent_context[intent]}"
        
        return reason
    
    def _get_quality_indicator(self, search_type: str, index: int) -> str:
        """품질 지표 생성"""
        if index == 0:
            return "🎯 최고 추천"
        elif '단계별 학습' in search_type:
            return "📚 초보자 친화"
        elif '약점 보완' in search_type:
            return "🔧 문제 해결"
        elif '경기 준비' in search_type:
            return "🏆 경기용"
        elif '상세 분석' in search_type:
            return "🔍 상세 분석"
        else:
            return "✅ 추천"
    
    def _get_search_tips(self, search_type: str) -> str:
        """검색 팁 제공"""
        tips = {
            '기본 학습': "💡 팁: 'fundamentals', 'basics' 키워드가 포함된 영상을 우선 시청하세요",
            '단계별 학습': "💡 팁: 'step by step', 'beginner' 키워드 영상이 도움됩니다",
            '약점 보완': "💡 팁: 'common mistakes', 'troubleshooting' 키워드 영상을 찾아보세요",
            '경기 준비': "💡 팁: 'competition', 'high level' 키워드 영상이 적합합니다",
            '고급 강화': "💡 팁: 'advanced', 'variations' 키워드로 더 많은 옵션을 찾아보세요",
            '상세 분석': "💡 팁: 'breakdown', 'details' 키워드가 포함된 영상이 유용합니다"
        }
        
        return tips.get(search_type, "💡 팁: 여러 영상을 비교해보고 자신에게 맞는 설명을 찾으세요")

# =============================================================================
# 피드백 시스템 (고도화)
# =============================================================================

class FeedbackSystem:
    def __init__(self):
        self.encouragements = {
            'high': ["훌륭합니다! 정말 열심히 하고 있어요! 🥋", "완벽한 훈련이었습니다! 💪"],
            'good': ["좋은 진전이에요! 꾸준히 발전하고 있습니다! 😊", "점점 나아지고 있어요! 🔥"],
            'needs_work': ["괜찮아요! 모든 고수들도 이런 과정을 거쳤답니다! 😌", "꾸준함이 가장 중요해요! 🌟"]
        }
    
    def generate_feedback(self, completion_rate: float, belt_name: str, 
                         nlp_analysis: Dict = None) -> Dict:
        """고도화된 피드백 생성 (NLP 분석 활용)"""
        if completion_rate >= 0.8:
            category = 'high'
            performance = "Excellent"
        elif completion_rate >= 0.6:
            category = 'good'  
            performance = "Good"
        else:
            category = 'needs_work'
            performance = "Keep Trying"
        
        # NLP 분석 결과 활용한 개인화된 피드백
        intent = nlp_analysis.get('intent', 'practice') if nlp_analysis else 'practice'
        emotional_state = nlp_analysis.get('emotional_state', []) if nlp_analysis else []
        
        feedback = {
            'performance': performance,
            'completion_rate': f"{completion_rate * 100:.0f}%",
            'encouragement': random.choice(self.encouragements[category]),
            'belt_specific_tip': self._get_belt_tip(belt_name),
            'intent_feedback': self._get_intent_feedback(intent, completion_rate),
            'emotional_support': self._get_emotional_support(emotional_state, completion_rate)
        }
        
        return feedback
    
    def _get_belt_tip(self, belt_name: str) -> str:
        """벨트별 맞춤 팁"""
        tips = {
            "화이트": "안전이 최우선입니다. 기본기를 완벽하게 익히세요!",
            "블루": "이제 기초가 탄탄해졌으니 연결 기술을 배워보세요!",
            "퍼플": "자신만의 게임을 개발할 시기입니다!",
            "브라운": "디테일과 타이밍에 더욱 집중하세요!",
            "블랙": "완성도를 높이고 창의적인 응용을 시도하세요!"
        }
        
        for color in tips.keys():
            if color in belt_name:
                return tips[color]
        
        return "꾸준한 연습이 답입니다!"
    
    def _get_intent_feedback(self, intent: str, completion_rate: float) -> str:
        """의도별 맞춤 피드백"""
        intent_feedbacks = {
            'learn': {
                'high': "새로운 기술을 훌륭하게 익히고 있습니다! 이 속도로 계속하세요!",
                'medium': "학습 과정이 순조롭습니다. 반복 연습으로 더욱 향상될 거예요!",
                'low': "새로운 것을 배우는 건 시간이 걸립니다. 천천히 꾸준히 하세요!"
            },
            'improve_weakness': {
                'high': "약점을 극복하려는 노력이 결실을 맺고 있습니다!",
                'medium': "약점 보완에 진전이 있습니다. 계속 집중해서 연습하세요!",
                'low': "약점 극복은 어렵지만 포기하지 마세요. 작은 발전도 의미가 있어요!"
            },
            'compete': {
                'high': "경기 준비가 완벽합니다! 자신감을 가지세요!",
                'medium': "경기력이 향상되고 있습니다. 더 집중해서 연습해보세요!",
                'low': "경기 준비는 시간이 걸립니다. 기본기를 더 탄탄히 하세요!"
            },
            'strengthen': {
                'high': "기술 강화가 성공적입니다! 한 단계 발전했어요!",
                'medium': "기술이 점점 정교해지고 있습니다!",
                'low': "기술 완성도를 높이는 건 시간이 걸립니다. 꾸준히 하세요!"
            }
        }
        
        level = 'high' if completion_rate >= 0.8 else 'medium' if completion_rate >= 0.6 else 'low'
        return intent_feedbacks.get(intent, {}).get(level, "꾸준한 연습이 가장 중요합니다!")
    
    def _get_emotional_support(self, emotional_states: List[str], completion_rate: float) -> str:
        """감정 상태에 따른 지원 메시지"""
        if not emotional_states:
            return ""
        
        if 'frustration' in emotional_states:
            if completion_rate >= 0.7:
                return "좌절감을 극복하고 좋은 결과를 얻었네요! 정말 대단합니다! 💪"
            else:
                return "좌절스러우시겠지만, 모든 고수들이 거치는 과정입니다. 포기하지 마세요! 🌟"
        
        elif 'anxiety' in emotional_states:
            return "불안한 마음을 가지고도 훈련을 완료하신 것이 대단합니다. 자신감을 가지세요! 😊"
        
        elif 'confidence' in emotional_states:
            return "자신감이 훈련 결과에 잘 나타났습니다! 이 기세를 유지하세요! 🔥"
        
        return ""

# =============================================================================
# 로그인 시스템
# =============================================================================

# 개선된 회원가입 시스템 - bjj_advanced_system.py에 추가할 코드

def create_login_system():
    """개선된 로그인/회원가입 시스템"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_data = None
    
    if not st.session_state.authenticated:
        st.title("🥋 BJJ 맞춤 훈련 시스템")
        st.markdown("**고도화된 NLP 분석**으로 개인화된 주짓수 훈련을 제공합니다")
        
        tab1, tab2 = st.tabs(["로그인", "회원가입"])
        
        with tab1:
            st.subheader("로그인")
            username = st.text_input("사용자명", key="login_username")
            password = st.text_input("비밀번호", type="password", key="login_password")
            
            if st.button("로그인"):
                if username and password:
                    db = BJJDatabase()
                    user_data = db.authenticate_user(username, password)
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.user_data = user_data
                        st.success("로그인 성공!")
                        st.rerun()
                    else:
                        st.error("로그인 실패. 사용자명과 비밀번호를 확인하세요.")
                else:
                    st.warning("사용자명과 비밀번호를 입력하세요.")
        
        with tab2:
            st.subheader("회원가입")
            
            # 사용자명 중복 확인 기능
            new_username = st.text_input("사용자명", key="signup_username")
            
            # 실시간 사용자명 확인
            if new_username:
                if check_username_availability(new_username):
                    st.success("✅ 사용 가능한 사용자명입니다!")
                else:
                    st.error("❌ 이미 사용 중인 사용자명입니다. 다른 이름을 선택해주세요.")
                    # 추천 사용자명 제안
                    suggestions = generate_username_suggestions(new_username)
                    st.info(f"💡 추천 사용자명: {', '.join(suggestions)}")
            
            new_email = st.text_input("이메일", key="signup_email")
            new_password = st.text_input("비밀번호", type="password", key="signup_password")
            confirm_password = st.text_input("비밀번호 확인", type="password", key="confirm_password")
            
            belt_options = list(BJJ_BELTS.keys())
            selected_belt = st.selectbox("현재 벨트", belt_options, key="signup_belt")
            
            # 개선된 회원가입 처리
            if st.button("회원가입"):
                # 입력 검증
                validation_errors = validate_signup_input(
                    new_username, new_email, new_password, confirm_password
                )
                
                if validation_errors:
                    for error in validation_errors:
                        st.error(error)
                else:
                    try:
                        db = BJJDatabase()
                        user_id = db.create_user(new_username, new_email, new_password, selected_belt)
                        st.success("🎉 회원가입 성공! 로그인해주세요.")
                        st.balloons()
                        
                        # 자동 로그인 옵션
                        if st.button("자동 로그인", key="auto_login"):
                            user_data = db.authenticate_user(new_username, new_password)
                            if user_data:
                                st.session_state.authenticated = True
                                st.session_state.user_data = user_data
                                st.rerun()
                                
                    except ValueError as e:
                        error_message = str(e)
                        if "UNIQUE constraint failed: users.username" in error_message:
                            st.error("❌ 이미 사용 중인 사용자명입니다.")
                        elif "UNIQUE constraint failed: users.email" in error_message:
                            st.error("❌ 이미 등록된 이메일입니다.")
                        else:
                            st.error(f"회원가입 실패: {error_message}")
        
        return False
    
    return True

def check_username_availability(username: str) -> bool:
    """사용자명 사용 가능 여부 확인"""
    try:
        db = BJJDatabase()
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        
        return result is None  # None이면 사용 가능
    except:
        return True  # 오류 시 일단 사용 가능으로 처리

def generate_username_suggestions(base_username: str) -> list:
    """사용자명 추천 생성"""
    import random
    
    suggestions = []
    
    # 숫자 추가
    for i in [2, 3, 4, 5]:
        suggestions.append(f"{base_username}{i}")
    
    # BJJ 관련 접미사 추가
    bjj_suffixes = ["_bjj", "_fighter", "_grappler", "_warrior", "_ninja"]
    for suffix in bjj_suffixes[:2]:
        suggestions.append(f"{base_username}{suffix}")
    
    # 년도 추가
    current_year = datetime.now().year
    suggestions.append(f"{base_username}_{current_year}")
    
    # 사용 가능한 것들만 필터링
    available_suggestions = []
    for suggestion in suggestions:
        if check_username_availability(suggestion):
            available_suggestions.append(suggestion)
        if len(available_suggestions) >= 3:  # 최대 3개만
            break
    
    return available_suggestions

def validate_signup_input(username: str, email: str, password: str, confirm_password: str) -> list:
    """회원가입 입력 검증"""
    errors = []
    
    # 사용자명 검증
    if not username:
        errors.append("사용자명을 입력하세요.")
    elif len(username) < 3:
        errors.append("사용자명은 3자 이상이어야 합니다.")
    elif len(username) > 20:
        errors.append("사용자명은 20자 이하여야 합니다.")
    elif not username.replace('_', '').replace('-', '').isalnum():
        errors.append("사용자명은 영문, 숫자, _, - 만 사용 가능합니다.")
    
    # 이메일 검증
    if not email:
        errors.append("이메일을 입력하세요.")
    elif '@' not in email or '.' not in email.split('@')[1]:
        errors.append("올바른 이메일 형식을 입력하세요.")
    
    # 비밀번호 검증
    if not password:
        errors.append("비밀번호를 입력하세요.")
    elif len(password) < 6:
        errors.append("비밀번호는 6자 이상이어야 합니다.")
    elif len(password) > 50:
        errors.append("비밀번호는 50자 이하여야 합니다.")
    
    # 비밀번호 확인
    if password != confirm_password:
        errors.append("비밀번호가 일치하지 않습니다.")
    
    # 사용자명 중복 확인
    if username and not check_username_availability(username):
        errors.append("이미 사용 중인 사용자명입니다.")
    
    return errors

# 추가: 계정 관리 기능
def create_account_management_tab():
    """계정 관리 탭 (설정 탭에 추가)"""
    st.subheader("🔐 계정 관리")
    
    user_data = st.session_state.user_data
    
    with st.expander("계정 정보 변경"):
        st.write("**현재 정보:**")
        st.write(f"- 사용자명: {user_data['username']}")
        st.write(f"- 이메일: {user_data.get('email', '없음')}")
        st.write(f"- 가입일: {user_data.get('created_at', '알 수 없음')}")
        st.write(f"- 총 훈련 세션: {user_data.get('total_sessions', 0)}회")
        
        st.warning("⚠️ 계정 정보 변경 기능은 추후 업데이트될 예정입니다.")
    
    with st.expander("⚠️ 위험 구역"):
        st.error("**주의**: 아래 작업은 되돌릴 수 없습니다!")
        
        if st.checkbox("모든 훈련 기록 삭제에 동의합니다"):
            if st.button("🗑️ 모든 훈련 기록 삭제", type="secondary"):
                if delete_all_training_records(user_data['user_id']):
                    st.success("모든 훈련 기록이 삭제되었습니다.")
                    st.rerun()
                else:
                    st.error("삭제 중 오류가 발생했습니다.")
        
        st.markdown("---")
        
        if st.checkbox("계정 삭제에 동의합니다"):
            delete_confirm = st.text_input("삭제를 확인하려면 '삭제확인'을 입력하세요:")
            if delete_confirm == "삭제확인":
                if st.button("❌ 계정 완전 삭제", type="secondary"):
                    if delete_user_account(user_data['user_id']):
                        st.success("계정이 삭제되었습니다. 안녕히 가세요!")
                        st.session_state.authenticated = False
                        st.session_state.user_data = None
                        st.rerun()
                    else:
                        st.error("계정 삭제 중 오류가 발생했습니다.")

def delete_all_training_records(user_id: str) -> bool:
    """사용자의 모든 훈련 기록 삭제"""
    try:
        db = BJJDatabase()
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 훈련 세션 기록 삭제
        cursor.execute("DELETE FROM training_sessions WHERE user_id = ?", (user_id,))
        
        # 기술 마스터리 기록 삭제
        cursor.execute("DELETE FROM technique_mastery WHERE user_id = ?", (user_id,))
        
        # 사용자 통계 초기화
        cursor.execute("""
            UPDATE users 
            SET total_sessions = 0, total_hours = 0.0 
            WHERE id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting training records: {e}")
        return False

def delete_user_account(user_id: str) -> bool:
    """사용자 계정 완전 삭제"""
    try:
        db = BJJDatabase()
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 모든 관련 데이터 삭제
        cursor.execute("DELETE FROM training_sessions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM technique_mastery WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting user account: {e}")
        return False

# =============================================================================
# 메인 Streamlit 앱 함수들
# =============================================================================

def create_training_program_tab(user_data):
    """훈련 프로그램 생성 탭 (고도화)"""
    st.header("🎯 AI 맞춤형 훈련 프로그램 생성")
    
    # 사용자 벨트 정보
    belt_info = BJJ_BELTS[user_data['current_belt']]
    
    # NLP 분석 기능 소개
    with st.expander("🤖 고도화된 AI 분석 기능"):
        st.markdown("""
        **새로운 NLP 분석 시스템이 다음을 자동으로 분석합니다:**
        
        - 🎯 **훈련 의도**: 학습, 복습, 경기 준비, 약점 보완 등
        - 🔧 **난이도 선호**: 쉽게, 보통, 도전적으로
        - 🏥 **안전 고려사항**: 부상, 제약사항 자동 감지
        - 🎨 **감정 상태**: 좌절, 자신감, 불안 등 감정 분석
        - 🥋 **특정 기술**: 언급된 구체적인 기술들 자동 추출
        
        **예시**: *"하프가드에서 자꾸 당하는데, 방어하는 방법부터 차근차근 배우고 싶어요"*
        → AI가 자동으로 **약점 보완**, **초급 난이도**, **하프가드 중심** 훈련을 생성합니다.
        """)
    
    st.info(f"**{belt_info['emoji']} {user_data['current_belt']} 수련생**\n"
            f"권장 난이도: {belt_info['max_difficulty']}/5 | "
            f"특징: {belt_info['description']}")
    
    # 향상된 훈련 요청 입력
    user_request = st.text_area(
        "🗣️ 자연스럽게 오늘의 훈련 목표를 말씀해 주세요:",
        placeholder="""예시:
• "하프가드에서 자꾸 당하는데, 방어하는 방법부터 차근차근 배우고 싶어요"
• "경기 준비 중인데 공격적인 가드 패스 기술들을 집중적으로 연습하고 싶습니다"  
• "트라이앵글 초크를 완벽하게 마스터하고 싶어요"
• "무릎 부상이 있어서 안전한 기술 위주로 30분만 가볍게 하고 싶어요" """,
        height=120
    )
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🤖 AI 분석 & 프로그램 생성", type="primary"):
            if user_request:
                with st.spinner("🔍 AI가 요청을 분석하고 맞춤 프로그램을 생성하는 중..."):
                    # 고도화된 NLP 분석
                    nlp = EnhancedNLPProcessor()
                    analysis = nlp.analyze_user_request(user_request)
                    
                    # 분석 결과 표시
                    with st.expander("🔍 AI 분석 결과", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("감지된 의도", analysis['intent'])
                            st.metric("난이도 선호", analysis['difficulty_preference'])
                        with col2:
                            st.metric("집중 영역", len(analysis['positions']))
                            st.metric("특정 기술", len(analysis['specific_techniques']))
                        with col3:
                            st.metric("분석 신뢰도", f"{analysis['confidence_score']:.0%}")
                            st.metric("안전 우선순위", analysis['safety_priority'])
                        
                        if analysis['specific_techniques']:
                            st.write("🎯 **감지된 기술들:**", ", ".join(analysis['specific_techniques']))
                        if analysis['concerns_or_limitations']:
                            st.warning(f"⚠️ **주의사항:** {analysis['concerns_or_limitations']}")
                    
                    # 프로그램 생성
                    generator = SmartTrainingGenerator(BJJTechniqueDatabase())
                    program = generator.generate_program(analysis, belt_info)
                    program['metadata']['user_id'] = user_data['user_id']
                    program['metadata']['belt'] = user_data['current_belt']
                    
                    st.session_state.current_program = program
                    st.session_state.current_analysis = analysis
                    
                    st.success("✅ AI 맞춤 프로그램 생성 완료!")
                    display_training_program(program, belt_info, analysis)
            else:
                st.warning("훈련 목표를 입력해주세요.")

def display_training_program(program, belt_info, analysis):
    """훈련 프로그램 표시 (고도화)"""
    if 'current_program' in st.session_state:
        program = st.session_state.current_program
        analysis = st.session_state.get('current_analysis', {})
        
        # 의도별 맞춤 메시지
        intent_messages = {
            'learn': "📚 학습 중심으로 구성된 프로그램입니다. 천천히 정확하게 연습하세요!",
            'improve_weakness': "🔧 약점 보완에 특화된 프로그램입니다. 꾸준히 연습하면 개선될 거예요!",
            'compete': "🏆 경기 준비용 고강도 프로그램입니다. 실전처럼 연습하세요!",
            'strengthen': "💪 기술 강화 중심 프로그램입니다. 디테일에 집중하세요!",
            'review': "🔄 복습 중심 프로그램입니다. 기존 기술을 점검해보세요!"
        }
        
        intent = analysis.get('intent', 'practice')
        if intent in intent_messages:
            st.info(intent_messages[intent])
        
        # 프로그램 요약
        st.subheader(f"📋 {belt_info['emoji']} AI 맞춤 프로그램 요약")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("총 시간", f"{program['metadata']['total_duration']}분")
        with col2:
            st.metric("벨트 수준", program['metadata']['belt'])
        with col3:
            st.metric("주요 기술", len(program['main_session']))
        with col4:
            st.metric("최대 난이도", f"{program['metadata']['max_difficulty']}/5")
        
        # 워밍업
        st.subheader("🔥 워밍업")
        for warmup in program['warm_up']:
            st.write(f"• {warmup['name']} ({warmup['duration']}분) - {warmup['description']}")
        
        # 메인 세션 (우선순위 표시)
        st.subheader("💪 메인 기술 연습")
        for i, session in enumerate(program['main_session'], 1):
            priority_icon = "🎯" if session.get('intent_matched', False) else "📝"
            
            with st.expander(f"{priority_icon} {i}. {session['technique']} ({session['duration']}분) - {session['difficulty_stars']}"):
                st.write(f"**카테고리:** {session['category']}")
                st.write(f"**설명:** {session['description']}")
                st.write(f"**난이도:** {session['difficulty']}/5")
                
                if session.get('aliases'):
                    st.write(f"**다른 이름:** {', '.join(session['aliases'])}")
                
                if session.get('intent_matched', False):
                    st.success("🎯 이 기술은 요청하신 특별 집중 기술입니다!")
        
        # 쿨다운
        st.subheader("🧘‍♂️ 쿨다운")
        for cooldown in program['cool_down']:
            st.write(f"• {cooldown['name']} ({cooldown['duration']}분) - {cooldown['description']}")

def create_video_recommendations_tab():
    """비디오 추천 탭 (고도화)"""
    st.header("📹 AI 맞춤 학습 영상 추천")
    
    if 'current_program' in st.session_state:
        analysis = st.session_state.get('current_analysis', {})
        youtube = YouTubeRecommendationSystem()
        video_recommendations = youtube.get_recommendations(st.session_state.current_program)
        
        if video_recommendations:
            # 의도별 추천 안내
            intent = analysis.get('intent', 'practice')
            intent_guides = {
                'learn': "🎓 학습용 영상들을 우선적으로 추천드립니다",
                'improve_weakness': "🔧 약점 보완에 도움되는 영상들을 찾았습니다",
                'compete': "🏆 경기 준비에 적합한 고급 영상들입니다",
                'strengthen': "💪 기술 향상을 위한 심화 영상들입니다"
            }
            
            if intent in intent_guides:
                st.info(intent_guides[intent])
            
            st.success(f"✅ {len(video_recommendations)}개의 맞춤 추천 영상을 찾았습니다!")
            
            # 우선순위별 그룹화
            priority_videos = [r for r in video_recommendations if r.get('priority') == 'high']
            normal_videos = [r for r in video_recommendations if r.get('priority') != 'high']
            
            if priority_videos:
                st.subheader("🎯 우선 추천 영상 (요청하신 특별 기술)")
                for i, rec in enumerate(priority_videos, 1):
                    display_video_recommendation(rec, i)
            
            if normal_videos:
                st.subheader("📚 추가 추천 영상")
                for i, rec in enumerate(normal_videos, len(priority_videos) + 1):
                    display_video_recommendation(rec, i)
        else:
            st.warning("추천할 영상을 찾지 못했습니다.")
    else:
        st.info("먼저 '훈련 프로그램 생성' 탭에서 프로그램을 만들어주세요.")

def display_video_recommendation(rec, index):
    """비디오 추천 표시"""
    video = rec['video']
    
    with st.expander(f"{index}. {rec['technique']} - {video['title']}"):
        col1, col2 = st.columns([2, 3])
        
        with col1:
            st.write(f"**채널:** {video['channel']}")
            st.write(f"**품질:** {rec['quality_indicator']}")
            st.write(f"**검색 유형:** {video['search_type']}")
        
        with col2:
            st.write(f"**추천 이유:** {rec['why_recommended']}")
            st.write(f"{rec['search_tips']}")
            st.link_button("🔗 영상 보기", video['url'])

def create_feedback_tab(user_data):
    """피드백 및 기록 탭 (고도화)"""
    st.header("📊 훈련 완료 및 스마트 피드백")
    
    if 'current_program' in st.session_state:
        program = st.session_state.current_program
        analysis = st.session_state.get('current_analysis', {})
        
        st.subheader("📝 훈련 완료 보고")
        
        col1, col2 = st.columns(2)
        with col1:
            completion_rate = st.slider("완주율 (%)", 0, 100, 80) / 100
            difficulty_rating = st.slider("체감 난이도 (1-5)", 1, 5, 3)
        
        with col2:
            enjoyment_rating = st.slider("만족도 (1-5)", 1, 5, 4)
            notes = st.text_area("훈련 노트", placeholder="오늘 훈련에서 배운 점, 어려웠던 점 등을 기록하세요")
        
        # 기술별 성공 여부 (우선순위 기술 표시)
        st.subheader("🎯 기술별 연습 결과")
        technique_results = {}
        for i, session in enumerate(program['main_session']):
            priority_icon = "🎯" if session.get('intent_matched', False) else "📝"
            technique_results[session['technique']] = st.checkbox(
                f"{priority_icon} {session['technique']} - 성공적으로 연습함",
                key=f"tech_{i}"
            )
        
        if st.button("🤖 AI 피드백 생성 & 기록 저장", type="primary"):
            # 고도화된 피드백 생성
            feedback_system = FeedbackSystem()
            feedback = feedback_system.generate_feedback(completion_rate, user_data['current_belt'], analysis)
            
            # 데이터베이스에 저장
            session_data = {
                'user_id': user_data['user_id'],
                'belt_level': user_data['current_belt'],
                'total_duration': program['metadata']['total_duration'],
                'completion_rate': completion_rate,
                'difficulty_rating': difficulty_rating,
                'enjoyment_rating': enjoyment_rating,
                'techniques_practiced': [s['technique'] for s in program['main_session']],
                'program_data': program,
                'notes': notes,
                'nlp_analysis': analysis  # NLP 분석 결과도 저장
            }
            
            db_manager = BJJDatabase()
            session_id = db_manager.save_training_session(session_data)
            
            # 기술 마스터리 업데이트
            for technique, success in technique_results.items():
                tech_data = next((s for s in program['main_session'] if s['technique'] == technique), None)
                if tech_data:
                    db_manager.update_technique_mastery(
                        user_data['user_id'],
                        technique,
                        tech_data['category'],
                        tech_data['difficulty'],
                        success
                    )
            
            # AI 피드백 표시
            st.success("✅ 훈련 기록이 저장되었습니다!")
            
            st.subheader("🤖 AI 개인화 피드백")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("성과 수준", feedback['performance'])
                st.metric("완주율", feedback['completion_rate'])
            
            with col2:
                st.write("**격려 메시지:**")
                st.info(feedback['encouragement'])
            
            # 의도별 맞춤 피드백
            if feedback['intent_feedback']:
                st.write("**목표 달성 피드백:**")
                st.success(feedback['intent_feedback'])
            
            # 벨트별 맞춤 팁
            st.subheader(f"💡 {user_data['current_belt']} 맞춤 팁")
            st.write(feedback['belt_specific_tip'])
            
            # 감정적 지원
            if feedback['emotional_support']:
                st.write("**감정적 지원:**")
                st.info(feedback['emotional_support'])
            
            # 분석 기반 개선 제안
            if analysis.get('intent') == 'improve_weakness' and completion_rate < 0.7:
                st.write("**개선 제안:**")
                st.warning("약점 보완에는 시간이 걸립니다. 다음 훈련에서는 더 기초적인 움직임부터 연습해보세요.")
            elif analysis.get('difficulty_preference') == 'challenging' and completion_rate >= 0.9:
                st.write("**도전 제안:**")
                st.success("현재 난이도가 적절해 보입니다. 다음엔 더 도전적인 변형을 시도해보세요!")
            
            st.balloons()
    else:
        st.info("먼저 훈련 프로그램을 생성하고 완료해주세요.")

def create_personal_stats_tab(user_data):
    """개인 통계 탭 (고도화)"""
    st.header("📈 개인 훈련 통계 & AI 분석")
    
    # 사용자 통계 조회
    db_manager = BJJDatabase()
    stats = db_manager.get_user_stats(user_data['user_id'])
    
    if stats:
        # 기본 통계
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 훈련 세션", stats['total_sessions'])
        with col2:
            st.metric("총 훈련 시간", f"{stats['total_hours']:.1f}시간")
        with col3:
            st.metric("평균 완주율", f"{stats['avg_completion_rate'] * 100:.1f}%")
        with col4:
            st.metric("평균 난이도", f"{stats['avg_difficulty']:.1f}/5")
        
        # 최근 세션 차트
        if stats['recent_sessions']:
            st.subheader("📊 최근 훈련 기록")
            sessions_df = pd.DataFrame(stats['recent_sessions'], 
                                     columns=['날짜', '완주율', '난이도', '만족도'])
            sessions_df['날짜'] = pd.to_datetime(sessions_df['날짜'])
            st.line_chart(sessions_df.set_index('날짜')[['완주율', '만족도']])
        
        # 기술 마스터리
        if stats['top_techniques']:
            st.subheader("🏆 기술 마스터리 순위")
            mastery_df = pd.DataFrame(stats['top_techniques'], 
                                    columns=['기술명', '카테고리', '연습 횟수', '숙련도'])
            mastery_df['숙련도'] = (mastery_df['숙련도'] * 100).round(1)
            st.dataframe(mastery_df, use_container_width=True)
        
        # AI 기반 개선 제안
        st.subheader("🤖 AI 개선 제안")
        if stats['avg_completion_rate'] < 0.6:
            st.warning("**완주율 개선 필요**: 더 짧은 세션으로 시작하거나 난이도를 낮춰보세요.")
        elif stats['avg_completion_rate'] > 0.9:
            st.success("**훌륭한 완주율**: 더 도전적인 훈련을 시도해볼 시기입니다!")
        
        if stats['avg_difficulty'] < 2:
            st.info("**난이도 상승 권장**: 현재 벨트에 맞는 더 높은 난이도를 시도해보세요.")
        elif stats['avg_difficulty'] > 4:
            st.warning("**과도한 난이도**: 기초를 더 탄탄히 한 후 고난이도에 도전하세요.")
    else:
        st.info("아직 훈련 기록이 없습니다. 첫 번째 훈련을 시작해보세요!")

def create_settings_tab(user_data):
    """설정 탭"""
    st.header("⚙️ 계정 설정")
    
    st.subheader("사용자 정보")
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("사용자명", value=user_data['username'], disabled=True)
        st.text_input("이메일", value=user_data.get('email', ''), disabled=True)
    
    with col2:
        st.selectbox("현재 벨트", 
                    list(BJJ_BELTS.keys()), 
                    index=list(BJJ_BELTS.keys()).index(user_data['current_belt']))
        st.selectbox("도복 선호도", 
                    ["both", "gi", "no-gi"], 
                    index=["both", "gi", "no-gi"].index(user_data['gi_preference']))
    
    # NLP 시스템 정보
    st.subheader("🤖 AI 시스템 정보")
    st.info("""
    **고도화된 NLP 분석 기능:**
    - 자연어 의도 분석 (학습, 복습, 경기 준비 등)
    - 감정 상태 감지 (좌절, 자신감, 불안 등)
    - 안전 고려사항 자동 감지
    - 특정 기술 자동 추출 및 우선순위 부여
    - 개인화된 피드백 생성
    """)
    
    if st.button("설정 저장"):
        st.success("설정이 저장되었습니다!")

def create_enhanced_streamlit_app():
    """고도화된 Streamlit 애플리케이션"""
    st.set_page_config(
        page_title="BJJ AI 훈련 시스템",
        page_icon="🥋",
        layout="wide"
    )
    
    # 로그인 확인
    if not create_login_system():
        return
    
    # 사용자 정보 표시
    user_data = st.session_state.user_data
    
    # 상단 네비게이션
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title(f"🥋 {user_data['username']}님의 BJJ AI 훈련 시스템")
        st.caption("🤖 고도화된 NLP 분석으로 개인화된 훈련 제공")
    with col2:
        st.metric("현재 벨트", user_data['current_belt'])
    with col3:
        if st.button("로그아웃"):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()
    
    st.markdown("---")
    
    # 메인 탭들
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 AI 훈련 프로그램", 
        "📹 맞춤 영상", 
        "📊 스마트 피드백", 
        "📈 개인 통계", 
        "⚙️ 설정"
    ])
    
    with tab1:
        create_training_program_tab(user_data)
    
    with tab2:
        create_video_recommendations_tab()
    
    with tab3:
        create_feedback_tab(user_data)
    
    with tab4:
        create_personal_stats_tab(user_data)
    
    with tab5:
        create_settings_tab(user_data)

# =============================================================================
# 메인 실행 함수
# =============================================================================

def main():
    """콘솔 버전 테스트"""
    print("🥋 BJJ AI 훈련 시스템 - 고도화된 NLP 통합 테스트")
    print("=" * 60)
    
    # 시스템 초기화
    db = BJJTechniqueDatabase()
    nlp = EnhancedNLPProcessor()
    generator = SmartTrainingGenerator(db)
    youtube = YouTubeRecommendationSystem()
    feedback = FeedbackSystem()
    
    # 고도화된 테스트 케이스
    test_requests = [
        ("🤍 화이트 벨트", "하프가드에서 자꾸 당하는데, 방어하는 방법부터 차근차근 배우고 싶어요"),
        ("🔵 블루 벨트", "경기 준비 중인데 공격적인 가드 패스 기술들을 집중적으로 연습하고 싶습니다"),
        ("🟣 퍼플 벨트", "트라이앵글 초크를 완벽하게 마스터하고 싶습니다"),
        ("🟤 브라운 벨트", "무릎 부상이 있어서 안전한 기술 위주로 30분만 가볍게 하고 싶어요"),
        ("⚫ 블랙 벨트", "딥하프가드에서 다양한 스윕 옵션들을 연구하고 싶습니다")
    ]
    
    for i, (belt, request) in enumerate(test_requests, 1):
        print(f"\n🥋 테스트 케이스 {i}: {belt}")
        print(f"요청: {request}")
        print("-" * 50)
        
        # 벨트 정보 가져오기
        belt_info = BJJ_BELTS[belt]
        
        # 고도화된 NLP 분석
        analysis = nlp.analyze_user_request(request)
        
        print(f"🤖 NLP 분석 결과:")
        print(f"- 의도: {analysis['intent']} (신뢰도: {analysis['intent_confidence']:.2f})")
        print(f"- 수준: {analysis['level']}")
        print(f"- 난이도 선호: {analysis['difficulty_preference']}")
        print(f"- 집중 영역: {analysis['positions']}")
        print(f"- 특정 기술: {analysis['specific_techniques']}")
        print(f"- 제약사항: {analysis['concerns_or_limitations'] or '없음'}")
        print(f"- 전체 신뢰도: {analysis['confidence_score']:.0%}")
        
        # 프로그램 생성
        program = generator.generate_program(analysis, belt_info)
        
        # 결과 출력
        print(f"\n📋 {belt_info['emoji']} {belt} 맞춤 프로그램:")
        print(f"- 총 시간: {program['metadata']['total_duration']}분")
        print(f"- 최대 난이도: {program['metadata']['max_difficulty']}/5")
        print(f"- 메인 기술 수: {len(program['main_session'])}")
        
        print(f"\n💪 주요 기술들:")
        for j, session in enumerate(program['main_session'], 1):
            priority = "🎯" if session.get('intent_matched', False) else "📝"
            print(f"  {priority} {j}. {session['technique']} ({session['duration']}분) {session['difficulty_stars']}")
        
        # 유튜브 추천
        videos = youtube.get_recommendations(program)
        if videos:
            print(f"\n📹 추천 영상:")
            for video_rec in videos[:2]:
                priority = "🎯" if video_rec.get('priority') == 'high' else "📚"
                print(f"  {priority} {video_rec['video']['title']}")
        
        # 샘플 피드백
        sample_feedback = feedback.generate_feedback(0.85, belt.split()[1], analysis)
        print(f"\n📊 AI 피드백 예시:")
        print(f"- 성과: {sample_feedback['performance']}")
        print(f"- 격려: {sample_feedback['encouragement']}")
        print(f"- 의도별 피드백: {sample_feedback['intent_feedback']}")
        print(f"- 벨트 팁: {sample_feedback['belt_specific_tip']}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    # 콘솔에서 실행시 테스트
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        main()
    else:
        # Streamlit 앱 실행
        create_enhanced_streamlit_app()

# 실행코드 = py -m streamlit run bjj_advanced_system.py
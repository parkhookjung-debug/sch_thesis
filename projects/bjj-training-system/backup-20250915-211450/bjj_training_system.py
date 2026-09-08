# requirements.txt에 추가할 패키지들:
# streamlit
# pandas
# numpy
# scikit-learn
# requests
# python-youtube
import sys
import streamlit as st
import pandas as pd
import numpy as np
import re
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests

# =============================================================================
# 데이터 모델
# =============================================================================

@dataclass
class BJJTechnique:
    """주짓수 기술 데이터 클래스"""
    id: int
    name: str
    name_en: str
    category: str
    subcategory: str
    difficulty: int  # 1-5
    position: str
    duration: int  # 분
    description: str
    prerequisites: List[str]
    youtube_keywords: List[str]
    gi_no_gi: str  # 'gi', 'no-gi', 'both'

@dataclass
class UserProfile:
    """사용자 프로필"""
    name: str
    level: str
    experience_months: int
    preferred_positions: List[str]
    goals: List[str]
    training_frequency: int  # 주당 횟수
    session_duration: int  # 분
    gi_preference: str
    avoided_techniques: List[str] = None

@dataclass
class TrainingSession:
    """훈련 세션"""
    date: datetime
    user: str
    program: Dict
    completion_rate: float
    feedback_score: int  # 1-5
    notes: str

# =============================================================================
# 기술 데이터베이스
# =============================================================================

class BJJTechniqueDatabase:
    """주짓수 기술 데이터베이스 - 확장된 버전"""
    
    def __init__(self):
        self.techniques = self._load_techniques()
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self._build_similarity_matrix()
    
    def _load_techniques(self) -> List[BJJTechnique]:
        """확장된 기술 데이터베이스 로드"""
        techniques_data = [
            # 가드 기술들
            {
                'id': 1, 'name': '클로즈드 가드', 'name_en': 'Closed Guard',
                'category': 'guard', 'subcategory': 'closed_guard', 'difficulty': 1,
                'position': 'bottom', 'duration': 10, 
                'description': '다리로 상대방의 허리를 감싸 컨트롤하는 기본 가드',
                'prerequisites': [], 'youtube_keywords': ['closed guard basics', 'closed guard control'],
                'gi_no_gi': 'both'
            },
            {
                'id': 2, 'name': '오픈 가드', 'name_en': 'Open Guard',
                'category': 'guard', 'subcategory': 'open_guard', 'difficulty': 2,
                'position': 'bottom', 'duration': 12,
                'description': '다리를 열어 다양한 각도에서 상대방을 컨트롤',
                'prerequisites': ['클로즈드 가드'], 'youtube_keywords': ['open guard concepts', 'open guard basics'],
                'gi_no_gi': 'both'
            },
            {
                'id': 3, 'name': '델라리바 가드', 'name_en': 'De La Riva Guard',
                'category': 'guard', 'subcategory': 'open_guard', 'difficulty': 4,
                'position': 'bottom', 'duration': 15,
                'description': '상대방의 다리 뒤쪽에 후킹하는 고급 오픈 가드',
                'prerequisites': ['오픈 가드'], 'youtube_keywords': ['de la riva guard', 'dlr guard sweeps'],
                'gi_no_gi': 'both'
            },
            {
                'id': 4, 'name': '스파이더 가드', 'name_en': 'Spider Guard',
                'category': 'guard', 'subcategory': 'open_guard', 'difficulty': 3,
                'position': 'bottom', 'duration': 15,
                'description': '상대방의 소매를 잡고 발로 팔을 컨트롤하는 가드',
                'prerequisites': ['오픈 가드'], 'youtube_keywords': ['spider guard', 'spider guard sweeps'],
                'gi_no_gi': 'gi'
            },
            {
                'id': 5, 'name': '버터플라이 가드', 'name_en': 'Butterfly Guard',
                'category': 'guard', 'subcategory': 'open_guard', 'difficulty': 2,
                'position': 'bottom', 'duration': 12,
                'description': '앉은 상태에서 발로 상대방의 다리를 후킹',
                'prerequisites': ['클로즈드 가드'], 'youtube_keywords': ['butterfly guard', 'butterfly sweeps'],
                'gi_no_gi': 'both'
            },
            
            # 패스 가드
            {
                'id': 6, 'name': '토리안도 패스', 'name_en': 'Toreando Pass',
                'category': 'guard_pass', 'subcategory': 'standing_pass', 'difficulty': 2,
                'position': 'top', 'duration': 10,
                'description': '상대방의 다리를 옆으로 밀어내며 패스하는 기술',
                'prerequisites': [], 'youtube_keywords': ['toreando pass', 'bullfighter pass'],
                'gi_no_gi': 'both'
            },
            {
                'id': 7, 'name': '더블 언더 패스', 'name_en': 'Double Under Pass',
                'category': 'guard_pass', 'subcategory': 'pressure_pass', 'difficulty': 2,
                'position': 'top', 'duration': 12,
                'description': '양손으로 상대방의 다리 밑을 감싸며 압박하는 패스',
                'prerequisites': [], 'youtube_keywords': ['double under pass', 'over under pass'],
                'gi_no_gi': 'both'
            },
            
            # 마운트
            {
                'id': 8, 'name': '마운트 컨트롤', 'name_en': 'Mount Control',
                'category': 'mount', 'subcategory': 'control', 'difficulty': 1,
                'position': 'top', 'duration': 8,
                'description': '마운트 포지션에서 안정적으로 컨트롤 유지',
                'prerequisites': [], 'youtube_keywords': ['mount control', 'mount maintenance'],
                'gi_no_gi': 'both'
            },
            {
                'id': 9, 'name': '하이 마운트', 'name_en': 'High Mount',
                'category': 'mount', 'subcategory': 'control', 'difficulty': 2,
                'position': 'top', 'duration': 10,
                'description': '상대방의 겨드랑이 쪽으로 올라가는 마운트',
                'prerequisites': ['마운트 컨트롤'], 'youtube_keywords': ['high mount', 'high mount attacks'],
                'gi_no_gi': 'both'
            },
            {
                'id': 10, 'name': 'S-마운트', 'name_en': 'S-Mount',
                'category': 'mount', 'subcategory': 'transition', 'difficulty': 3,
                'position': 'top', 'duration': 12,
                'description': 'S자 형태로 다리를 배치하는 마운트 변형',
                'prerequisites': ['하이 마운트'], 'youtube_keywords': ['s mount', 's mount armbar'],
                'gi_no_gi': 'both'
            },
            
            # 사이드 컨트롤
            {
                'id': 11, 'name': '사이드 컨트롤', 'name_en': 'Side Control',
                'category': 'side_control', 'subcategory': 'control', 'difficulty': 1,
                'position': 'top', 'duration': 8,
                'description': '상대방의 옆에서 컨트롤하는 기본 포지션',
                'prerequisites': [], 'youtube_keywords': ['side control', 'side control basics'],
                'gi_no_gi': 'both'
            },
            {
                'id': 12, 'name': '니 온 벨리', 'name_en': 'Knee on Belly',
                'category': 'side_control', 'subcategory': 'pressure', 'difficulty': 2,
                'position': 'top', 'duration': 10,
                'description': '무릎으로 상대방의 배를 압박하는 포지션',
                'prerequisites': ['사이드 컨트롤'], 'youtube_keywords': ['knee on belly', 'knee on stomach'],
                'gi_no_gi': 'both'
            },
            {
                'id': 13, 'name': '노스 사우스', 'name_en': 'North South',
                'category': 'side_control', 'subcategory': 'control', 'difficulty': 2,
                'position': 'top', 'duration': 10,
                'description': '머리와 머리가 반대 방향을 향하는 컨트롤',
                'prerequisites': ['사이드 컨트롤'], 'youtube_keywords': ['north south', 'north south choke'],
                'gi_no_gi': 'both'
            },
            
            # 백 컨트롤
            {
                'id': 14, 'name': '백 컨트롤', 'name_en': 'Back Control',
                'category': 'back_control', 'subcategory': 'control', 'difficulty': 2,
                'position': 'back', 'duration': 12,
                'description': '상대방의 등 뒤에서 후크로 컨트롤',
                'prerequisites': [], 'youtube_keywords': ['back control', 'rear mount'],
                'gi_no_gi': 'both'
            },
            {
                'id': 15, 'name': '바디 트라이앵글', 'name_en': 'Body Triangle',
                'category': 'back_control', 'subcategory': 'control', 'difficulty': 3,
                'position': 'back', 'duration': 15,
                'description': '다리로 삼각형을 만들어 더 강하게 컨트롤',
                'prerequisites': ['백 컨트롤'], 'youtube_keywords': ['body triangle', 'body lock'],
                'gi_no_gi': 'both'
            },
            
            # 서브미션
            {
                'id': 16, 'name': '리어 네이키드 초크', 'name_en': 'Rear Naked Choke',
                'category': 'submission', 'subcategory': 'choke', 'difficulty': 2,
                'position': 'back', 'duration': 8,
                'description': '뒤에서 목을 조르는 기본 초크',
                'prerequisites': ['백 컨트롤'], 'youtube_keywords': ['rear naked choke', 'RNC technique'],
                'gi_no_gi': 'both'
            },
            {
                'id': 17, 'name': '마운트 암바', 'name_en': 'Armbar from Mount',
                'category': 'submission', 'subcategory': 'joint_lock', 'difficulty': 2,
                'position': 'top', 'duration': 10,
                'description': '마운트에서 팔을 꺾는 관절기',
                'prerequisites': ['마운트 컨트롤'], 'youtube_keywords': ['mount armbar', 'armbar from mount'],
                'gi_no_gi': 'both'
            },
            {
                'id': 18, 'name': '트라이앵글 초크', 'name_en': 'Triangle Choke',
                'category': 'submission', 'subcategory': 'choke', 'difficulty': 3,
                'position': 'bottom', 'duration': 12,
                'description': '다리로 삼각형을 만들어 목을 조르는 기술',
                'prerequisites': ['클로즈드 가드'], 'youtube_keywords': ['triangle choke', 'triangle from guard'],
                'gi_no_gi': 'both'
            },
            {
                'id': 19, 'name': '키무라', 'name_en': 'Kimura',
                'category': 'submission', 'subcategory': 'joint_lock', 'difficulty': 2,
                'position': 'various', 'duration': 10,
                'description': '어깨 관절을 공격하는 관절기',
                'prerequisites': [], 'youtube_keywords': ['kimura lock', 'kimura technique'],
                'gi_no_gi': 'both'
            },
            {
                'id': 20, 'name': '아메리카나', 'name_en': 'Americana',
                'category': 'submission', 'subcategory': 'joint_lock', 'difficulty': 2,
                'position': 'top', 'duration': 8,
                'description': '사이드 컨트롤에서 어깨를 공격하는 관절기',
                'prerequisites': ['사이드 컨트롤'], 'youtube_keywords': ['americana lock', 'key lock'],
                'gi_no_gi': 'both'
            },
            {
                'id': 21, 'name': '기요틴 초크', 'name_en': 'Guillotine Choke',
                'category': 'submission', 'subcategory': 'choke', 'difficulty': 2,
                'position': 'various', 'duration': 10,
                'description': '앞에서 목을 감싸 조르는 초크',
                'prerequisites': [], 'youtube_keywords': ['guillotine choke', 'front choke'],
                'gi_no_gi': 'both'
            },
            
            # 스윕
            {
                'id': 22, 'name': '시저 스윕', 'name_en': 'Scissor Sweep',
                'category': 'sweep', 'subcategory': 'guard_sweep', 'difficulty': 2,
                'position': 'bottom', 'duration': 10,
                'description': '다리를 가위처럼 사용하는 스윕',
                'prerequisites': ['클로즈드 가드'], 'youtube_keywords': ['scissor sweep', 'basic guard sweep'],
                'gi_no_gi': 'both'
            },
            {
                'id': 23, 'name': '힙 범프 스윕', 'name_en': 'Hip Bump Sweep',
                'category': 'sweep', 'subcategory': 'guard_sweep', 'difficulty': 1,
                'position': 'bottom', 'duration': 8,
                'description': '엉덩이로 밀어내는 기본 스윕',
                'prerequisites': ['클로즈드 가드'], 'youtube_keywords': ['hip bump sweep', 'sit up sweep'],
                'gi_no_gi': 'both'
            },
            {
                'id': 24, 'name': '플라워 스윕', 'name_en': 'Flower Sweep',
                'category': 'sweep', 'subcategory': 'guard_sweep', 'difficulty': 2,
                'position': 'bottom', 'duration': 12,
                'description': '상대방의 팔과 다리를 동시에 컨트롤하는 스윕',
                'prerequisites': ['클로즈드 가드'], 'youtube_keywords': ['flower sweep', 'pendulum sweep'],
                'gi_no_gi': 'gi'
            },
            {
                'id': 25, 'name': '버터플라이 스윕', 'name_en': 'Butterfly Sweep',
                'category': 'sweep', 'subcategory': 'guard_sweep', 'difficulty': 2,
                'position': 'bottom', 'duration': 10,
                'description': '버터플라이 가드에서 실행하는 스윕',
                'prerequisites': ['버터플라이 가드'], 'youtube_keywords': ['butterfly sweep', 'butterfly guard sweep'],
                'gi_no_gi': 'both'
            }
        ]
        
        return [BJJTechnique(**tech) for tech in techniques_data]
    
    def _build_similarity_matrix(self):
        """기술 간 유사도 매트릭스 구성"""
        descriptions = [f"{tech.name} {tech.description} {' '.join(tech.youtube_keywords)}" 
                       for tech in self.techniques]
        self.tfidf_matrix = self.vectorizer.fit_transform(descriptions)
        self.similarity_matrix = cosine_similarity(self.tfidf_matrix)
    
    def get_similar_techniques(self, technique_id: int, top_n: int = 3) -> List[BJJTechnique]:
        """유사한 기술 추천"""
        if technique_id >= len(self.techniques):
            return []
        
        similarities = self.similarity_matrix[technique_id]
        similar_indices = similarities.argsort()[-top_n-1:-1][::-1]
        
        return [self.techniques[i] for i in similar_indices]
    
    def filter_techniques(self, level: str = None, category: str = None, 
                         gi_preference: str = None, max_difficulty: int = None) -> List[BJJTechnique]:
        """조건에 따른 기술 필터링"""
        filtered = self.techniques.copy()
        
        if max_difficulty:
            filtered = [t for t in filtered if t.difficulty <= max_difficulty]
        
        if category:
            filtered = [t for t in filtered if t.category == category]
        
        if gi_preference and gi_preference != 'both':
            filtered = [t for t in filtered if t.gi_no_gi in [gi_preference, 'both']]
        
        return filtered

# =============================================================================
# NLP 처리기
# =============================================================================

class AdvancedNLPProcessor:
    """고급 NLP 처리기"""
    
    def __init__(self):
        self.level_keywords = {
            'beginner': ['초보', '초급', '새로운', '처음', '기초', 'beginner', 'basic', '입문', '시작'],
            'intermediate': ['중급', '중간', '어느정도', 'intermediate', 'medium', '보통', '경험'],
            'advanced': ['고급', '상급', '고수', '전문', 'advanced', 'expert', '숙련', '마스터']
        }
        
        self.goal_keywords = {
            'competition': ['대회', '시합', '경쟁', '토너먼트', 'competition', 'tournament', '승부', '경기'],
            'fitness': ['체력', '운동', '건강', '피트니스', 'fitness', 'health', '다이어트', '몸만들기'],
            'self_defense': ['호신', '방어', '보호', 'defense', 'protection', '자기방어', '실전'],
            'technique': ['기술', '테크닉', '스킬', 'technique', 'skill', '동작', '폼'],
            'fun': ['재미', '취미', '즐거움', 'fun', 'hobby', '놀이', '스트레스']
        }
        
        self.position_keywords = {
            'guard': ['가드', '가아드', 'guard', '하체', '다리'],
            'mount': ['마운트', 'mount', '올라타기', '압박'],
            'side_control': ['사이드', '사이드컨트롤', 'side', '옆'],
            'back_control': ['백', '등', 'back', '뒤'],
            'submission': ['서브미션', '서브', '조르기', '잠그기', 'submission', 'choke', '관절기'],
            'sweep': ['스윕', '뒤집기', 'sweep', '역전'],
            'guard_pass': ['패스', 'pass', '가드패스', '뚫기'],
            'takedown': ['테이크다운', '넘어뜨리기', 'takedown', '던지기']
        }
        
        self.time_keywords = {
            'short': ['짧은', '빠른', '30분', '짧게', 'short', 'quick', '간단'],
            'medium': ['중간', '1시간', '보통', 'medium', 'normal', '적당'],
            'long': ['긴', '오래', '2시간', '길게', 'long', 'extended', '충분']
        }
        
        self.intensity_keywords = {
            'light': ['가볍게', '여유롭게', 'light', 'easy', '편하게'],
            'moderate': ['보통', '적당히', 'moderate', 'normal', '중간'],
            'intense': ['강하게', '집중적으로', 'intense', 'hard', '빡세게']
        }
    
    def analyze_user_request(self, text: str) -> Dict:
        """사용자 요청 종합 분석"""
        text_lower = text.lower()
        
        analysis = {
            'level': self._detect_level(text_lower),
            'goals': self._detect_goals(text_lower),
            'positions': self._detect_positions(text_lower),
            'duration': self._detect_duration(text_lower),
            'intensity': self._detect_intensity(text_lower),
            'gi_preference': self._detect_gi_preference(text_lower),
            'special_requests': self._extract_special_requests(text_lower)
        }
        
        return analysis
    
    def _detect_level(self, text: str) -> str:
        """레벨 감지"""
        for level, keywords in self.level_keywords.items():
            if any(keyword in text for keyword in keywords):
                return level
        return 'beginner'  # 기본값
    
    def _detect_goals(self, text: str) -> List[str]:
        """목표 감지"""
        detected_goals = []
        for goal, keywords in self.goal_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_goals.append(goal)
        return detected_goals or ['technique']
    
    def _detect_positions(self, text: str) -> List[str]:
        """포지션/기술 영역 감지"""
        detected_positions = []
        for position, keywords in self.position_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_positions.append(position)
        return detected_positions
    
    def _detect_duration(self, text: str) -> str:
        """시간 감지"""
        for duration, keywords in self.time_keywords.items():
            if any(keyword in text for keyword in keywords):
                return duration
        return 'medium'
    
    def _detect_intensity(self, text: str) -> str:
        """강도 감지"""
        for intensity, keywords in self.intensity_keywords.items():
            if any(keyword in text for keyword in keywords):
                return intensity
        return 'moderate'
    
    def _detect_gi_preference(self, text: str) -> str:
        """도복 선호도 감지"""
        if any(word in text for word in ['도복', 'gi', '기']):
            return 'gi'
        elif any(word in text for word in ['노기', 'nogi', 'no-gi', '민소매']):
            return 'no-gi'
        return 'both'
    
    def _extract_special_requests(self, text: str) -> List[str]:
        """특별 요청사항 추출"""
        special_requests = []
        
        if any(word in text for word in ['부상', '아픈', '조심', 'injury', '회복']):
            special_requests.append('injury_consideration')
        
        if any(word in text for word in ['새로운', '다른', '변화', '색다른']):
            special_requests.append('variety_focus')
        
        if any(word in text for word in ['복습', '연습', '반복', 'drill']):
            special_requests.append('drill_focus')
        
        return special_requests

# =============================================================================
# 훈련 프로그램 생성기
# =============================================================================

class SmartTrainingGenerator:
    """지능형 훈련 프로그램 생성기"""
    
    def __init__(self, database: BJJTechniqueDatabase):
        self.db = database
        self.level_difficulty_map = {
            'beginner': 2,
            'intermediate': 3,
            'advanced': 5
        }
        
        self.duration_map = {
            'short': 30,
            'medium': 60,
            'long': 90
        }
        
        self.intensity_multiplier = {
            'light': 0.8,
            'moderate': 1.0,
            'intense': 1.3
        }
    
    def generate_program(self, analysis: Dict, user_profile: UserProfile = None) -> Dict:
        """분석 결과를 바탕으로 스마트 훈련 프로그램 생성"""
        
        # 기본 설정
        max_difficulty = self.level_difficulty_map[analysis['level']]
        total_duration = self.duration_map[analysis['duration']]
        intensity = self.intensity_multiplier[analysis['intensity']]
        
        # 기술 필터링
        available_techniques = self.db.filter_techniques(
            max_difficulty=max_difficulty,
            gi_preference=analysis['gi_preference']
        )
        
        # 포지션별 기술 선별
        if analysis['positions']:
            position_techniques = []
            for position in analysis['positions']:
                position_techniques.extend([
                    t for t in available_techniques if t.category == position
                ])
            if position_techniques:
                available_techniques = position_techniques
        
        # 프로그램 구성
        program = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'user_analysis': analysis,
                'total_duration': total_duration,
                'intensity_level': analysis['intensity'],
                'target_level': analysis['level']
            },
            'warm_up': self._generate_warmup(int(total_duration * 0.2)),
            'main_session': self._generate_main_session(
                available_techniques, 
                int(total_duration * 0.6), 
                analysis
            ),
            'drilling': self._generate_drilling_session(
                available_techniques,
                int(total_duration * 0.15),
                analysis
            ),
            'cool_down': self._generate_cooldown(int(total_duration * 0.05)),
            'recommended_videos': [],
            'progression_notes': self._generate_progression_notes(analysis)
        }
        
        return program
    
    def _generate_warmup(self, duration: int) -> List[Dict]:
        """동적 웜업 생성"""
        warmup_exercises = [
            {'name': '목 돌리기', 'duration': 2, 'reps': '10회씩 양방향', 'description': '목 관절 풀기'},
            {'name': '어깨 돌리기', 'duration': 2, 'reps': '10회씩 양방향', 'description': '어깨 관절 풀기'},
            {'name': '허리 돌리기', 'duration': 2, 'reps': '10회씩 양방향', 'description': '허리 관절 풀기'},
            {'name': '다리 스윙', 'duration': 2, 'reps': '10회씩 양쪽', 'description': '고관절 풀기'},
            {'name': '쉬리핑', 'duration': 3, 'reps': '좌우 10회씩', 'description': '기본 무브먼트'},
            {'name': '브릿지', 'duration': 3, 'reps': '10회', 'description': '척추 유연성'},
            {'name': '테크니컬 스탠드업', 'duration': 2, 'reps': '5회씩', 'description': '일어서기 연습'}
        ]
        
        # 시간에 맞춰 선별
        selected = []
        current_duration = 0
        for exercise in warmup_exercises:
            if current_duration + exercise['duration'] <= duration:
                selected.append(exercise)
                current_duration += exercise['duration']
            if current_duration >= duration:
                break
        
        return selected
    
    def _generate_main_session(self, techniques: List[BJJTechnique], 
                              duration: int, analysis: Dict) -> List[Dict]:
        """메인 세션 기술 선별"""
        if not techniques:
            return []
        
        # 목표에 따른 기술 우선순위 조정
        if 'competition' in analysis['goals']:
            # 대회 준비: 고확률 성공 기술 위주
            techniques = sorted(techniques, key=lambda t: (t.difficulty, -t.id))
        elif 'technique' in analysis['goals']:
            # 기술 향상: 다양한 카테고리 균형
            techniques = self._balance_categories(techniques)
        
        # 시간 배분
        num_techniques = min(len(techniques), max(2, duration // 15))
        time_per_technique = duration // num_techniques
        
        selected_techniques = random.sample(techniques, num_techniques)
        
        main_session = []
        for i, tech in enumerate(selected_techniques):
            session_item = {
                'technique': tech.name,
                'technique_en': tech.name_en,
                'category': tech.category,
                'difficulty': tech.difficulty,
                'duration': time_per_technique,
                'position': tech.position,
                'description': tech.description,
                'focus_points': self._generate_focus_points(tech, analysis['level']),
                'drilling_method': self._suggest_drilling_method(tech, analysis['level']),
                'common_mistakes': self._get_common_mistakes(tech),
                'prerequisites_check': tech.prerequisites
            }
            main_session.append(session_item)
        
        return main_session
    
    def _balance_categories(self, techniques: List[BJJTechnique]) -> List[BJJTechnique]:
        """카테고리 균형 맞추기"""
        categories = {}
        for tech in techniques:
            if tech.category not in categories:
                categories[tech.category] = []
            categories[tech.category].append(tech)
        
        balanced = []
        max_per_category = max(1, len(techniques) // len(categories))
        
        for category_techs in categories.values():
            balanced.extend(category_techs[:max_per_category])
        
        return balanced
    
    def _generate_focus_points(self, technique: BJJTechnique, level: str) -> List[str]:
        """레벨별 기술 포커스 포인트"""
        focus_points = {
            'beginner': [
                f"{technique.name}의 기본 자세와 그립 익히기",
                "천천히 정확한 동작으로 연습",
                "파트너와의 안전한 거리 유지",
                "기본 원리 이해하기"
            ],
            'intermediate': [
                f"{technique.name}의 타이밍과 각도 연습",
                "상대방의 반응에 따른 조절",
                "연결 기술과의 조합 연습",
                "실전 적용 상황 이해"
            ],
            'advanced': [
                f"{technique.name}의 미세한 디테일 완성",
                "다양한 상황에서의 적용",
                "창의적 변형 시도",
                "교육 관점에서 분석"
            ]
        }
        
        return focus_points.get(level, focus_points['beginner'])
    
    def _suggest_drilling_method(self, technique: BJJTechnique, level: str) -> Dict:
        """기술별 드릴 방법 제안"""
        if technique.category == 'submission':
            return {
                'method': 'Position Drilling',
                'description': '포지션 진입 → 셋업 → 서브미션 완성',
                'reps': '각 단계 5회씩 반복',
                'progression': '천천히 → 보통 속도 → 저항 추가'
            }
        elif technique.category in ['guard', 'mount', 'side_control']:
            return {
                'method': 'Position Sparring',
                'description': '특정 포지션에서 시작하여 제한된 룰로 스파링',
                'duration': '2-3분 라운드',
                'progression': '50% → 75% → 100% 강도'
            }
        else:
            return {
                'method': 'Flow Drilling',
                'description': '연결된 동작으로 자연스럽게 흘러가며 연습',
                'reps': '10-15회 반복',
                'progression': '개별 동작 → 연결 동작 → 자유로운 플로우'
            }
    
    def _get_common_mistakes(self, technique: BJJTechnique) -> List[str]:
        """일반적인 실수들"""
        common_mistakes = {
            'submission': [
                "성급하게 서브미션을 시도하기",
                "포지션 컨트롤을 소홀히 하기",
                "상대방의 방어를 예상하지 못하기"
            ],
            'guard': [
                "다리의 텐션 부족",
                "그립 컨트롤 소홀",
                "상체와 하체 움직임 불일치"
            ],
            'mount': [
                "무게 중심이 너무 앞쪽에 위치",
                "다리 포지션 부정확",
                "상대방의 엘보우 이스케이프 허용"
            ]
        }
        
        return common_mistakes.get(technique.category, ["기본 자세 확인 필요"])
    
    def _generate_drilling_session(self, techniques: List[BJJTechnique], 
                                  duration: int, analysis: Dict) -> List[Dict]:
        """드릴링 세션 생성"""
        if duration < 5:
            return []
        
        drilling_exercises = [
            {
                'name': '포지셔널 스파링',
                'duration': duration // 2,
                'description': '특정 포지션에서 시작하는 제한된 스파링',
                'rounds': f"{(duration // 2) // 3}라운드 × 3분",
                'intensity': '70-80%'
            },
            {
                'name': '플로우 드릴',
                'duration': duration // 2,
                'description': '배운 기술들을 연결하여 자연스럽게 연습',
                'focus': '동작의 연결성과 타이밍',
                'intensity': '50-60%'
            }
        ]
        
        return drilling_exercises
    
    def _generate_cooldown(self, duration: int) -> List[Dict]:
        """쿨다운 세션 생성"""
        cooldown_exercises = [
            {
                'name': '정적 스트레칭',
                'duration': max(3, duration // 2),
                'exercises': [
                    '어깨 뒤쪽 스트레칭',
                    '허리 비틀기 스트레칭',
                    '고관절 스트레칭',
                    '목 스트레칭'
                ]
            },
            {
                'name': '호흡 정리',
                'duration': max(2, duration // 2),
                'description': '복식호흡으로 심박수 안정화 및 정신적 정리'
            }
        ]
        
        return cooldown_exercises
    
    def _generate_progression_notes(self, analysis: Dict) -> Dict:
        """진행 상황 노트 생성"""
        return {
            'current_focus': f"{analysis['level']} 레벨 {', '.join(analysis['positions']) if analysis['positions'] else '전체'} 기술",
            'next_milestone': self._suggest_next_milestone(analysis),
            'long_term_goal': self._suggest_long_term_goal(analysis),
            'recommended_frequency': self._recommend_frequency(analysis)
        }
    
    def _suggest_next_milestone(self, analysis: Dict) -> str:
        """다음 마일스톤 제안"""
        level_progression = {
            'beginner': '기본 8개 포지션 숙지 및 기본 에스케이프 마스터',
            'intermediate': '선호 포지션에서의 3-4가지 공격 옵션 개발',
            'advanced': '개인 스타일 완성 및 백업 플랜 구축'
        }
        
        return level_progression.get(analysis['level'], '꾸준한 연습 지속')
    
    def _suggest_long_term_goal(self, analysis: Dict) -> str:
        """장기 목표 제안"""
        if 'competition' in analysis['goals']:
            return '대회 참가 및 메달 획득'
        elif 'self_defense' in analysis['goals']:
            return '실전 상황에서의 자신감 확보'
        elif 'fitness' in analysis['goals']:
            return '꾸준한 체력 관리 및 건강 유지'
        else:
            return '검은띠 달성 및 기술 마스터'
    
    def _recommend_frequency(self, analysis: Dict) -> str:
        """훈련 빈도 추천"""
        level_frequency = {
            'beginner': '주 2-3회, 각 60분',
            'intermediate': '주 3-4회, 각 90분',
            'advanced': '주 4-6회, 각 90-120분'
        }
        
        return level_frequency.get(analysis['level'], '주 2-3회')

# =============================================================================
# 유튜브 추천 시스템
# =============================================================================

class YouTubeRecommendationSystem:
    """유튜브 영상 추천 시스템"""
    
    def __init__(self):
        # 실제로는 YouTube Data API v3를 사용
        self.api_key = "YOUR_YOUTUBE_API_KEY"  # 실제 API 키로 교체 필요
        self.popular_channels = {
            'beginner': [
                'Gracie Breakdown', 'BJJ Fanatics', 'StephanKesting', 
                'GrappleArts', 'Inverted Gear'
            ],
            'intermediate': [
                'BJJ Scout', 'Lachlan Giles', 'John Danaher', 
                'Gordon Ryan', 'Keenan Online'
            ],
            'advanced': [
                'Marcelo Garcia', 'Andre Galvao', 'Rafael Lovato Jr',
                'Bernardo Faria BJJ', 'Mendes Brothers'
            ]
        }
        
        # 샘플 영상 데이터베이스 (실제로는 API에서 가져옴)
        self.sample_videos = self._load_sample_videos()
    
    def _load_sample_videos(self) -> Dict:
        """샘플 영상 데이터 로드"""
        return {
            'guard': [
                {
                    'title': 'Closed Guard Fundamentals - Complete Guide',
                    'url': 'https://youtube.com/watch?v=sample1',
                    'channel': 'Gracie Breakdown',
                    'duration': '15:32',
                    'level': 'beginner',
                    'views': '1.2M',
                    'description': '클로즈드 가드의 기본 원리와 주요 기술들'
                },
                {
                    'title': 'Open Guard Concepts Every BJJ Player Should Know',
                    'url': 'https://youtube.com/watch?v=sample2',
                    'channel': 'Lachlan Giles',
                    'duration': '22:15',
                    'level': 'intermediate',
                    'views': '800K',
                    'description': '오픈 가드의 핵심 개념과 실전 적용법'
                }
            ],
            'submission': [
                {
                    'title': 'Perfect Rear Naked Choke - Details Matter',
                    'url': 'https://youtube.com/watch?v=sample3',
                    'channel': 'John Danaher',
                    'duration': '18:45',
                    'level': 'intermediate',
                    'views': '2.1M',
                    'description': '리어 네이키드 초크의 세밀한 디테일 분석'
                }
            ],
            'mount': [
                {
                    'title': 'Mount Control and Attacks - Systematic Approach',
                    'url': 'https://youtube.com/watch?v=sample4',
                    'channel': 'Gordon Ryan',
                    'duration': '25:10',
                    'level': 'advanced',
                    'views': '650K',
                    'description': '마운트 포지션에서의 체계적인 공격 시스템'
                }
            ]
        }
    
    def get_recommendations(self, program: Dict) -> List[Dict]:
        """프로그램에 맞는 영상 추천"""
        recommendations = []
        level = program['metadata']['target_level']
        
        for session_item in program['main_session']:
            category = session_item['category']
            technique_name = session_item['technique']
            
            # 카테고리별 영상 검색
            if category in self.sample_videos:
                suitable_videos = [
                    video for video in self.sample_videos[category]
                    if video['level'] == level or video['level'] == 'beginner'
                ]
                
                if suitable_videos:
                    selected_video = suitable_videos[0]  # 실제로는 더 정교한 선별 로직
                    recommendations.append({
                        'technique': technique_name,
                        'video': selected_video,
                        'relevance_score': self._calculate_relevance(technique_name, selected_video),
                        'why_recommended': f"{technique_name} 기술 학습에 적합한 {selected_video['level']} 레벨 영상"
                    })
        
        return recommendations
    
    def _calculate_relevance(self, technique: str, video: Dict) -> float:
        """영상 관련성 점수 계산"""
        # 간단한 키워드 매칭 기반 점수
        technique_words = set(technique.lower().split())
        video_words = set(video['title'].lower().split())
        
        intersection = len(technique_words.intersection(video_words))
        union = len(technique_words.union(video_words))
        
        return intersection / union if union > 0 else 0.0
    
    def search_youtube_videos(self, query: str, level: str = 'beginner') -> List[Dict]:
        """실제 YouTube API 검색 (구현 예시)"""
        # 실제 구현시에는 YouTube Data API v3 사용
        # 지금은 샘플 응답 반환
        return [
            {
                'title': f'{query} - BJJ Tutorial',
                'url': f'https://youtube.com/watch?v=search_{hash(query)}',
                'channel': 'BJJ Tutorial Channel',
                'duration': '12:34',
                'level': level,
                'description': f'{query}에 대한 상세한 설명'
            }
        ]

# =============================================================================
# 피드백 및 진행 추적 시스템
# =============================================================================

class FeedbackAndProgressSystem:
    """피드백 및 진행 추적 시스템"""
    
    def __init__(self):
        self.feedback_database = []
        self.progress_metrics = {}
    
    def generate_session_feedback(self, program: Dict, completion_data: Dict) -> Dict:
        """세션 완료 후 피드백 생성"""
        completion_rate = completion_data.get('completion_rate', 1.0)
        difficulty_rating = completion_data.get('difficulty_rating', 3)
        enjoyment_rating = completion_data.get('enjoyment_rating', 4)
        
        feedback = {
            'session_summary': {
                'completion_rate': f"{completion_rate * 100:.0f}%",
                'techniques_practiced': len(program['main_session']),
                'total_time': program['metadata']['total_duration'],
                'difficulty_felt': difficulty_rating,
                'enjoyment_level': enjoyment_rating
            },
            'performance_analysis': self._analyze_performance(completion_data),
            'encouragement': self._generate_encouragement(completion_data),
            'improvement_tips': self._generate_improvement_tips(program, completion_data),
            'next_session_suggestions': self._suggest_next_session(program, completion_data),
            'progress_tracking': self._update_progress_tracking(program, completion_data)
        }
        
        return feedback
    
    def _analyze_performance(self, completion_data: Dict) -> Dict:
        """성과 분석"""
        completion_rate = completion_data.get('completion_rate', 1.0)
        difficulty_rating = completion_data.get('difficulty_rating', 3)
        
        if completion_rate >= 0.9 and difficulty_rating <= 3:
            performance_level = "Excellent"
            analysis = "완벽한 세션이었습니다! 기술을 잘 소화하고 있어요."
        elif completion_rate >= 0.7 and difficulty_rating <= 4:
            performance_level = "Good"
            analysis = "좋은 진전을 보이고 있습니다. 꾸준히 발전하고 있어요."
        elif completion_rate >= 0.5:
            performance_level = "Satisfactory"
            analysis = "괜찮은 세션이었습니다. 조금 더 집중해보면 더 좋을 것 같아요."
        else:
            performance_level = "Needs Improvement"
            analysis = "다음에는 더 잘할 수 있을 거예요. 포기하지 마세요!"
        
        return {
            'level': performance_level,
            'analysis': analysis,
            'strengths': self._identify_strengths(completion_data),
            'areas_for_improvement': self._identify_improvement_areas(completion_data)
        }
    
    def _identify_strengths(self, completion_data: Dict) -> List[str]:
        """강점 식별"""
        strengths = []
        
        if completion_data.get('completion_rate', 0) >= 0.8:
            strengths.append("높은 집중력과 지구력")
        
        if completion_data.get('technique_accuracy', 0) >= 0.7:
            strengths.append("정확한 기술 실행")
        
        if completion_data.get('enjoyment_rating', 0) >= 4:
            strengths.append("훈련에 대한 긍정적 태도")
        
        return strengths or ["꾸준한 참여 의지"]
    
    def _identify_improvement_areas(self, completion_data: Dict) -> List[str]:
        """개선 영역 식별"""
        improvements = []
        
        if completion_data.get('completion_rate', 1) < 0.7:
            improvements.append("지구력 향상 필요")
        
        if completion_data.get('technique_accuracy', 1) < 0.6:
            improvements.append("기술 정확도 개선 필요")
        
        if completion_data.get('difficulty_rating', 3) >= 4:
            improvements.append("난이도 조절 고려")
        
        return improvements or ["현재 수준 유지"]
    
    def _generate_encouragement(self, completion_data: Dict) -> str:
        """격려 메시지 생성"""
        encouragements = {
            'high_performance': [
                "훌륭합니다! 정말 열심히 하고 있어요! 🥋",
                "완벽한 훈련이었습니다! 이 페이스를 유지하세요! 💪",
                "실력이 눈에 띄게 늘고 있네요! 👏"
            ],
            'good_performance': [
                "좋은 진전이에요! 꾸준히 발전하고 있습니다! 😊",
                "점점 나아지고 있어요! 계속 화이팅! 🔥",
                "훌륭한 노력입니다! 성장이 보여요! 📈"
            ],
            'needs_encouragement': [
                "괜찮아요! 모든 고수들도 이런 과정을 거쳤답니다! 😌",
                "포기하지 마세요! 내일은 더 좋을 거예요! 🌟",
                "한 걸음씩 나아가고 있어요! 꾸준함이 가장 중요해요! 🚶‍♂️"
            ]
        }
        
        completion_rate = completion_data.get('completion_rate', 1.0)
        
        if completion_rate >= 0.8:
            category = 'high_performance'
        elif completion_rate >= 0.6:
            category = 'good_performance'
        else:
            category = 'needs_encouragement'
        
        return random.choice(encouragements[category])
    
    def _generate_improvement_tips(self, program: Dict, completion_data: Dict) -> List[str]:
        """개선 팁 생성"""
        tips = []
        level = program['metadata']['target_level']
        
        # 레벨별 기본 팁
        level_tips = {
            'beginner': [
                "기본자세를 정확히 익히는 것이 가장 중요해요",
                "천천히 하더라도 정확한 동작을 유지하세요",
                "호흡을 잊지 마세요 - 긴장하면 숨을 참게 돼요"
            ],
            'intermediate': [
                "기술의 연결고리를 찾아보세요",
                "상대방의 반응을 예측하고 대비하세요",
                "타이밍이 힘보다 중요합니다"
            ],
            'advanced': [
                "미세한 디테일에 집중해보세요",
                "자신만의 스타일을 개발해보세요",
                "후배들을 가르치며 자신의 이해도를 점검해보세요"
            ]
        }
        
        tips.extend(level_tips.get(level, level_tips['beginner']))
        
        # 성과 기반 추가 팁
        if completion_data.get('completion_rate', 1) < 0.7:
            tips.append("훈련 강도를 조절하여 완주할 수 있는 수준으로 맞춰보세요")
        
        if completion_data.get('difficulty_rating', 3) >= 4:
            tips.append("현재 레벨보다 조금 쉬운 기술부터 차근차근 익혀보세요")
        
        return tips[:3]  # 최대 3개까지
    
    def _suggest_next_session(self, program: Dict, completion_data: Dict) -> Dict:
        """다음 세션 제안"""
        completion_rate = completion_data.get('completion_rate', 1.0)
        difficulty_rating = completion_data.get('difficulty_rating', 3)
        
        suggestions = {
            'focus_areas': [],
            'difficulty_adjustment': 'maintain',
            'duration_recommendation': program['metadata']['total_duration'],
            'specific_suggestions': []
        }
        
        # 완주율 기반 조정
        if completion_rate < 0.6:
            suggestions['difficulty_adjustment'] = 'decrease'
            suggestions['duration_recommendation'] = max(30, program['metadata']['total_duration'] - 15)
            suggestions['specific_suggestions'].append("시간을 줄이고 기본기에 집중해보세요")
        elif completion_rate >= 0.9 and difficulty_rating <= 3:
            suggestions['difficulty_adjustment'] = 'increase'
            suggestions['specific_suggestions'].append("더 도전적인 기술을 시도해볼 준비가 되었습니다")
        
        # 집중 영역 제안
        current_categories = [item['category'] for item in program['main_session']]
        all_categories = ['guard', 'mount', 'side_control', 'back_control', 'submission', 'sweep']
        missing_categories = [cat for cat in all_categories if cat not in current_categories]
        
        if missing_categories:
            suggestions['focus_areas'] = missing_categories[:2]
            suggestions['specific_suggestions'].append(f"다음에는 {', '.join(missing_categories[:2])} 기술도 연습해보세요")
        
        return suggestions
    
    def _update_progress_tracking(self, program: Dict, completion_data: Dict) -> Dict:
        """진행 상황 업데이트"""
        user_id = completion_data.get('user_id', 'default_user')
        
        if user_id not in self.progress_metrics:
            self.progress_metrics[user_id] = {
                'total_sessions': 0,
                'total_hours': 0,
                'techniques_learned': set(),
                'average_completion_rate': 0,
                'progress_trend': []
            }
        
        user_progress = self.progress_metrics[user_id]
        
        # 세션 정보 업데이트
        user_progress['total_sessions'] += 1
        user_progress['total_hours'] += program['metadata']['total_duration'] / 60
        
        # 기술 정보 업데이트
        for session_item in program['main_session']:
            user_progress['techniques_learned'].add(session_item['technique'])
        
        # 완주율 평균 업데이트
        old_avg = user_progress['average_completion_rate']
        new_completion = completion_data.get('completion_rate', 1.0)
        sessions = user_progress['total_sessions']
        user_progress['average_completion_rate'] = (old_avg * (sessions - 1) + new_completion) / sessions
        
        # 트렌드 추가
        user_progress['progress_trend'].append({
            'date': datetime.now().isoformat(),
            'completion_rate': new_completion,
            'difficulty_rating': completion_data.get('difficulty_rating', 3)
        })
        
        # 최근 10개 세션만 유지
        if len(user_progress['progress_trend']) > 10:
            user_progress['progress_trend'] = user_progress['progress_trend'][-10:]
        
        return {
            'total_sessions': user_progress['total_sessions'],
            'total_hours': round(user_progress['total_hours'], 1),
            'techniques_count': len(user_progress['techniques_learned']),
            'average_completion': f"{user_progress['average_completion_rate'] * 100:.1f}%",
            'recent_trend': self._analyze_recent_trend(user_progress['progress_trend'])
        }
    
    def _analyze_recent_trend(self, trend_data: List[Dict]) -> str:
        """최근 트렌드 분석"""
        if len(trend_data) < 3:
            return "데이터 수집 중"
        
        recent_completions = [item['completion_rate'] for item in trend_data[-3:]]
        
        if all(recent_completions[i] >= recent_completions[i-1] for i in range(1, len(recent_completions))):
            return "상승 추세 📈"
        elif all(recent_completions[i] <= recent_completions[i-1] for i in range(1, len(recent_completions))):
            return "하향 추세 📉"
        else:
            return "안정적 유지 ➡️"

# =============================================================================
# Streamlit 웹 인터페이스
# =============================================================================

def create_streamlit_app():
    """Streamlit 웹 애플리케이션 생성"""
    
    st.set_page_config(
        page_title="BJJ 맞춤 훈련 시스템",
        page_icon="🥋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 시스템 초기화
    if 'db' not in st.session_state:
        st.session_state.db = BJJTechniqueDatabase()
        st.session_state.nlp = AdvancedNLPProcessor()
        st.session_state.generator = SmartTrainingGenerator(st.session_state.db)
        st.session_state.youtube = YouTubeRecommendationSystem()
        st.session_state.feedback_system = FeedbackAndProgressSystem()
    
    st.title("🥋 주짓수 맞춤형 훈련 시스템")
    st.markdown("---")
    
    # 사이드바 - 사용자 프로필
    with st.sidebar:
        st.header("👤 사용자 프로필")
        
        user_name = st.text_input("이름", value="BJJ 수련생")
        user_level = st.selectbox("레벨", ["beginner", "intermediate", "advanced"])
        experience_months = st.slider("경험 (개월)", 0, 120, 6)
        gi_preference = st.selectbox("도복 선호도", ["both", "gi", "no-gi"])
        
        st.markdown("---")
        st.header("📊 통계")
        
        # 간단한 통계 표시
        if 'user_stats' not in st.session_state:
            st.session_state.user_stats = {
                'total_sessions': 0,
                'total_hours': 0,
                'techniques_learned': 0
            }
        
        stats = st.session_state.user_stats
        st.metric("총 세션", stats['total_sessions'])
        st.metric("총 훈련 시간", f"{stats['total_hours']}시간")
        st.metric("학습한 기술", f"{stats['techniques_learned']}개")
    
    # 메인 영역
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 훈련 프로그램 생성", "📹 영상 추천", "📊 피드백", "📈 진행 상황"])
    
    with tab1:
        st.header("🎯 맞춤형 훈련 프로그램 생성")
        
        # 사용자 요청 입력
        user_request = st.text_area(
            "훈련 요청사항을 자유롭게 입력하세요:",
            placeholder="예: 초보자인데 가드 기술 위주로 1시간 정도 훈련하고 싶어요",
            height=100
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            generate_button = st.button("🚀 프로그램 생성", type="primary")
        
        if generate_button and user_request:
            with st.spinner("맞춤형 훈련 프로그램을 생성하고 있습니다..."):
                # NLP 분석
                analysis = st.session_state.nlp.analyze_user_request(user_request)
                
                # 프로그램 생성
                program = st.session_state.generator.generate_program(analysis)
                
                # 결과 저장
                st.session_state.current_program = program
                st.session_state.current_analysis = analysis
                
                # 결과 표시
                st.success("✅ 프로그램 생성 완료!")
                
                # 프로그램 요약
                st.subheader("📋 프로그램 요약")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("총 시간", f"{program['metadata']['total_duration']}분")
                with col2:
                    st.metric("난이도", program['metadata']['target_level'])
                with col3:
                    st.metric("주요 기술", len(program['main_session']))
                with col4:
                    st.metric("강도", program['metadata']['intensity_level'])
                
                # 웜업
                st.subheader("🔥 웜업 ({} 분)".format(sum(item['duration'] for item in program['warm_up'])))
                warmup_df = pd.DataFrame(program['warm_up'])
                st.dataframe(warmup_df, use_container_width=True)
                
                # 메인 세션
                st.subheader("💪 메인 훈련")
                for i, session in enumerate(program['main_session'], 1):
                    with st.expander(f"{i}. {session['technique']} ({session['duration']}분) - 난이도: {'⭐' * session['difficulty']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**설명:**", session['description'])
                            st.write("**포지션:**", session['position'])
                            st.write("**카테고리:**", session['category'])
                        
                        with col2:
                            st.write("**집중 포인트:**")
                            for point in session['focus_points'][:3]:
                                st.write(f"• {point}")
                            
                            st.write("**드릴 방법:**", session['drilling_method']['method'])
                
                # 드릴링
                if program['drilling']:
                    st.subheader("🎯 드릴링 세션")
                    for drill in program['drilling']:
                        st.info(f"**{drill['name']}** ({drill['duration']}분): {drill['description']}")
                
                # 쿨다운
                st.subheader("🧘‍♂️ 쿨다운")
                for cooldown in program['cool_down']:
                    st.info(f"**{cooldown['name']}** ({cooldown['duration']}분)")
                
                # 진행 노트
                st.subheader("📝 진행 가이드")
                notes = program['progression_notes']
                st.write(f"**현재 집중 영역:** {notes['current_focus']}")
                st.write(f"**다음 목표:** {notes['next_milestone']}")
                st.write(f"**권장 빈도:** {notes['recommended_frequency']}")
    
    with tab2:
        st.header("📹 추천 학습 영상")
        
        if 'current_program' in st.session_state:
            with st.spinner("관련 영상을 검색하고 있습니다..."):
                video_recommendations = st.session_state.youtube.get_recommendations(st.session_state.current_program)
                
                if video_recommendations:
                    st.success(f"✅ {len(video_recommendations)}개의 추천 영상을 찾았습니다!")
                    
                    for i, rec in enumerate(video_recommendations, 1):
                        with st.expander(f"{i}. {rec['technique']} - 학습 영상"):
                            video = rec['video']
                            col1, col2 = st.columns([2, 3])
                            
                            with col1:
                                st.write(f"**제목:** {video['title']}")
                                st.write(f"**채널:** {video['channel']}")
                                st.write(f"**길이:** {video['duration']}")
                                st.write(f"**레벨:** {video['level']}")
                                if 'views' in video:
                                    st.write(f"**조회수:** {video['views']}")
                            
                            with col2:
                                st.write(f"**추천 이유:** {rec['why_recommended']}")
                                st.write(f"**관련도:** {rec['relevance_score']:.2f}")
                                st.link_button("🔗 영상 보기", video['url'])
                
                else:
                    st.warning("추천할 영상을 찾지 못했습니다. 먼저 훈련 프로그램을 생성해주세요.")
        else:
            st.info("먼저 '훈련 프로그램 생성' 탭에서 프로그램을 만들어주세요.")
    
    with tab3:
        st.header("📊 훈련 완료 피드백")
        
        if 'current_program' in st.session_state:
            st.subheader("훈련 완료 보고")
            
            col1, col2 = st.columns(2)
            
            with col1:
                completion_rate = st.slider("완주율 (%)", 0, 100, 80) / 100
                difficulty_rating = st.slider("체감 난이도 (1-5)", 1, 5, 3)
            
            with col2:
                enjoyment_rating = st.slider("만족도 (1-5)", 1, 5, 4)
                technique_accuracy = st.slider("기술 정확도 (1-5)", 1, 5, 3) / 5
            
            session_notes = st.text_area("추가 메모", placeholder="훈련 중 느낀 점이나 어려웠던 부분을 적어주세요")
            
            if st.button("📝 피드백 제출"):
                completion_data = {
                    'completion_rate': completion_rate,
                    'difficulty_rating': difficulty_rating,
                    'enjoyment_rating': enjoyment_rating,
                    'technique_accuracy': technique_accuracy,
                    'notes': session_notes,
                    'user_id': user_name
                }
                
                feedback = st.session_state.feedback_system.generate_session_feedback(
                    st.session_state.current_program, completion_data
                )
                
                # 피드백 표시
                st.success("✅ 피드백이 저장되었습니다!")
                
                # 성과 분석
                st.subheader("🎯 성과 분석")
                analysis = feedback['performance_analysis']
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("성과 수준", analysis['level'])
                    st.write(analysis['analysis'])
                
                with col2:
                    st.write("**강점:**")
                    for strength in analysis['strengths']:
                        st.write(f"✅ {strength}")
                    
                    if analysis['areas_for_improvement']:
                        st.write("**개선 영역:**")
                        for area in analysis['areas_for_improvement']:
                            st.write(f"🎯 {area}")
                
                # 격려 메시지
                st.info(feedback['encouragement'])
                
                # 개선 팁
                st.subheader("💡 개선 팁")
                for tip in feedback['improvement_tips']:
                    st.write(f"• {tip}")
                
                # 다음 세션 제안
                st.subheader("🔮 다음 세션 제안")
                suggestions = feedback['next_session_suggestions']
                
                if suggestions['focus_areas']:
                    st.write(f"**추천 집중 영역:** {', '.join(suggestions['focus_areas'])}")
                
                st.write(f"**난이도 조정:** {suggestions['difficulty_adjustment']}")
                st.write(f"**권장 시간:** {suggestions['duration_recommendation']}분")
                
                for suggestion in suggestions['specific_suggestions']:
                    st.write(f"• {suggestion}")
                
                # 통계 업데이트
                progress = feedback['progress_tracking']
                st.session_state.user_stats.update({
                    'total_sessions': progress['total_sessions'],
                    'total_hours': progress['total_hours'],
                    'techniques_learned': progress['techniques_count']
                })
        else:
            st.info("먼저 훈련 프로그램을 생성하고 완료해주세요.")
    
    with tab4:
        st.header("📈 진행 상황 및 통계")
        
        if st.session_state.user_stats['total_sessions'] > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("총 훈련 세션", st.session_state.user_stats['total_sessions'])
            with col2:
                st.metric("누적 훈련 시간", f"{st.session_state.user_stats['total_hours']}시간")
            with col3:
                st.metric("학습한 기술", f"{st.session_state.user_stats['techniques_learned']}개")
            
            # 가상의 진행 차트
            st.subheader("📊 실력 진행 차트")
            
            # 샘플 데이터로 차트 생성
            dates = pd.date_range(start='2024-01-01', periods=st.session_state.user_stats['total_sessions'], freq='W')
            progress_data = pd.DataFrame({
                'Date': dates[:st.session_state.user_stats['total_sessions']],
                'Completion Rate': np.random.normal(0.8, 0.1, st.session_state.user_stats['total_sessions']).clip(0, 1),
                'Skill Level': np.linspace(1, 5, st.session_state.user_stats['total_sessions'])
            })
            
            st.line_chart(progress_data.set_index('Date'))
            
            # 기술 분포
            st.subheader("🎯 연습한 기술 분포")
            
            # 샘플 기술 분포 데이터
            technique_categories = ['Guard', 'Mount', 'Side Control', 'Submission', 'Sweep']
            category_counts = np.random.randint(1, 10, len(technique_categories))
            
            chart_data = pd.DataFrame({
                'Category': technique_categories,
                'Count': category_counts
            })
            
            st.bar_chart(chart_data.set_index('Category'))
            
        else:
            st.info("아직 훈련 기록이 없습니다. 첫 번째 훈련을 시작해보세요!")
            
            # 추천 시작 프로그램
            st.subheader("🚀 추천 시작 프로그램")
            
            starter_programs = [
                "초보자를 위한 기본 가드 기술 30분 프로그램",
                "주짓수 입문자 전신 기초 기술 45분 코스",
                "첫 주짓수 체험 - 안전한 기본기 위주 30분"
            ]
            
            for program in starter_programs:
                if st.button(f"📋 {program}"):
                    st.session_state.suggested_request = program
                    st.rerun()
    
    # 하단 정보
    st.markdown("---")
    st.markdown("""
    ### ℹ️ 사용 가이드
    
    1. **훈련 프로그램 생성**: 자연어로 원하는 훈련 내용을 입력하세요
    2. **영상 추천**: 생성된 프로그램에 맞는 YouTube 학습 영상을 확인하세요
    3. **피드백**: 훈련 완료 후 솔직한 피드백을 남겨주세요
    4. **진행 상황**: 개인 발전 과정을 추적하고 분석하세요
    
    **💡 팁**: 구체적인 요청일수록 더 정확한 맞춤 프로그램을 받을 수 있습니다!
    """)

# =============================================================================
# 메인 실행 함수
# =============================================================================

def main():
    """메인 실행 함수"""
    
    # 콘솔 버전 테스트
    print("🥋 주짓수 맞춤형 훈련 시스템 테스트")
    print("=" * 50)
    
    # 시스템 초기화
    db = BJJTechniqueDatabase()
    nlp = AdvancedNLPProcessor()
    generator = SmartTrainingGenerator(db)
    youtube = YouTubeRecommendationSystem()
    feedback_system = FeedbackAndProgressSystem()
    
    # 테스트 케이스
    test_requests = [
        "초보자인데 가드 위주로 1시간 정도 훈련하고 싶어요",
        "중급자입니다. 대회 준비용 서브미션 집중 훈련 30분으로 부탁해요",
        "고급 no-gi 마운트 공격 기술을 2시간 동안 집중적으로 연습하고 싶습니다"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🎯 테스트 케이스 {i}")
        print(f"요청: {request}")
        print("-" * 40)
        
        # 분석
        analysis = nlp.analyze_user_request(request)
        print(f"분석 결과: {analysis}")
        
        # 프로그램 생성
        program = generator.generate_program(analysis)
        
        # 간단한 결과 출력
        print(f"\n📋 생성된 프로그램:")
        print(f"- 총 시간: {program['metadata']['total_duration']}분")
        print(f"- 레벨: {program['metadata']['target_level']}")
        print(f"- 메인 기술 수: {len(program['main_session'])}")
        
        print(f"\n💪 주요 기술들:")
        for j, session in enumerate(program['main_session'], 1):
            print(f"  {j}. {session['technique']} ({session['duration']}분)")
        
        # 유튜브 추천
        videos = youtube.get_recommendations(program)
        if videos:
            print(f"\n📹 추천 영상:")
            for video_rec in videos[:2]:  # 처음 2개만
                print(f"  - {video_rec['video']['title']}")
        
        # 샘플 피드백
        sample_completion = {
            'completion_rate': 0.85,
            'difficulty_rating': 3,
            'enjoyment_rating': 4,
            'technique_accuracy': 0.75,
            'user_id': f'test_user_{i}'
        }
        
        feedback = feedback_system.generate_session_feedback(program, sample_completion)
        print(f"\n📊 피드백 예시:")
        print(f"- 격려: {feedback['encouragement']}")
        print(f"- 성과: {feedback['performance_analysis']['level']}")
        
        print("\n" + "="*80)

# 맨 아래 기존 코드를 이것으로 교체
if __name__ == "__main__":
    # Streamlit 앱 실행
    create_streamlit_app()
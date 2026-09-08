# BJJ Training System - Cloud Optimized Final Version
import streamlit as st
import pandas as pd
import numpy as np
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import random
import urllib.parse

# =============================================================================
# Cloud-Optimized Data Manager
# =============================================================================

class CloudDataManager:
    """Cloud-optimized session-based data management"""
    
    def __init__(self):
        if 'users_data' not in st.session_state:
            st.session_state.users_data = {}
        if 'sessions_data' not in st.session_state:
            st.session_state.sessions_data = {}
        if 'techniques_data' not in st.session_state:
            st.session_state.techniques_data = {}
        
        # Create demo account automatically
        self._ensure_demo_account()
    
    def _ensure_demo_account(self):
        """Ensure demo account exists"""
        demo_exists = False
        for user_data in st.session_state.users_data.values():
            if user_data.get('username') == 'demo':
                demo_exists = True
                break
        
        if not demo_exists:
            user_id = "demo-user-12345"
            password_hash = hashlib.sha256("demo123".encode()).hexdigest()
            
            st.session_state.users_data[user_id] = {
                'id': user_id,
                'username': 'demo',
                'email': 'demo@bjj.com',
                'password_hash': password_hash,
                'current_belt': '🔵 블루 벨트',
                'current_stripes': 1,
                'experience_months': 18,
                'gi_preference': 'both',
                'created_at': datetime.now().isoformat(),
                'total_sessions': 3,
                'total_hours': 4.5
            }
    
    def create_user(self, username: str, email: str, password: str, belt: str) -> str:
        """Create new user"""
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Check for duplicate username
        for existing_user in st.session_state.users_data.values():
            if existing_user['username'] == username:
                raise ValueError("이미 존재하는 사용자명입니다")
        
        st.session_state.users_data[user_id] = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'current_belt': belt,
            'current_stripes': 0,
            'experience_months': 0,
            'gi_preference': 'both',
            'created_at': datetime.now().isoformat(),
            'total_sessions': 0,
            'total_hours': 0.0
        }
        
        return user_id
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        for user_data in st.session_state.users_data.values():
            if (user_data.get('username') == username and 
                user_data.get('password_hash') == password_hash):
                return user_data
        
        return None
    
    def save_training_session(self, session_data: Dict) -> str:
        """Save training session"""
        session_id = str(uuid.uuid4())
        
        st.session_state.sessions_data[session_id] = {
            'id': session_id,
            'user_id': session_data['user_id'],
            'session_date': datetime.now().isoformat(),
            'belt_level': session_data['belt_level'],
            'total_duration': session_data['total_duration'],
            'completion_rate': session_data['completion_rate'],
            'difficulty_rating': session_data.get('difficulty_rating'),
            'enjoyment_rating': session_data.get('enjoyment_rating'),
            'techniques_practiced': session_data.get('techniques_practiced', []),
            'program_data': session_data.get('program_data', {}),
            'notes': session_data.get('notes', '')
        }
        
        # Update user total sessions and hours
        user_id = session_data['user_id']
        if user_id in st.session_state.users_data:
            st.session_state.users_data[user_id]['total_sessions'] += 1
            st.session_state.users_data[user_id]['total_hours'] += session_data['total_duration'] / 60.0
        
        return session_id
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics"""
        if user_id not in st.session_state.users_data:
            return {}
        
        user_info = st.session_state.users_data[user_id]
        
        # Get user sessions
        user_sessions = [
            session for session in st.session_state.sessions_data.values() 
            if session['user_id'] == user_id
        ]
        
        # Recent 10 sessions
        recent_sessions = sorted(user_sessions, key=lambda x: x['session_date'], reverse=True)[:10]
        
        return {
            'current_belt': user_info['current_belt'],
            'total_sessions': user_info['total_sessions'],
            'total_hours': user_info['total_hours'],
            'experience_months': user_info['experience_months'],
            'recent_sessions': [
                (s['session_date'], s['completion_rate'], s['difficulty_rating'], s['enjoyment_rating'])
                for s in recent_sessions
            ],
            'top_techniques': [],  # Simplified for cloud version
            'avg_completion_rate': np.mean([s['completion_rate'] for s in recent_sessions]) if recent_sessions else 0,
            'avg_difficulty': np.mean([s['difficulty_rating'] for s in recent_sessions if s['difficulty_rating']]) if recent_sessions else 0
        }

# =============================================================================
# BJJ Belt System Definition
# =============================================================================

BJJ_BELTS = {
    "🤍 화이트 벨트": {
        "level": "beginner",
        "experience_months": "0-12개월",
        "max_difficulty": 2,
        "description": "기본기 위주, 안전한 훈련",
        "emoji": "🤍"
    },
    "🔵 블루 벨트": {
        "level": "intermediate", 
        "experience_months": "12-36개월",
        "max_difficulty": 3,
        "description": "기초 기술 숙련, 연결 기술 학습",
        "emoji": "🔵"
    },
    "🟣 퍼플 벨트": {
        "level": "intermediate",
        "experience_months": "36-60개월", 
        "max_difficulty": 4,
        "description": "중급 기술, 개인 스타일 개발",
        "emoji": "🟣"
    },
    "🟤 브라운 벨트": {
        "level": "advanced",
        "experience_months": "60-84개월",
        "max_difficulty": 5,
        "description": "고급 기술, 교육 역할",
        "emoji": "🟤"
    },
    "⚫ 블랙 벨트": {
        "level": "advanced",
        "experience_months": "84개월+",
        "max_difficulty": 5,
        "description": "마스터 레벨, 창의적 응용",
        "emoji": "⚫"
    }
}

# =============================================================================
# Technique Database
# =============================================================================

class BJJTechniqueDatabase:
    def __init__(self):
        self.techniques = self._load_techniques()
    
    def _load_techniques(self) -> List[Dict]:
        return [
            # Guard techniques
            {
                'id': 1, 'name': '클로즈드 가드', 'name_en': 'Closed Guard',
                'category': 'guard', 'difficulty': 1, 'position': 'bottom', 'duration': 10,
                'description': '다리로 상대방의 허리를 감싸 컨트롤하는 기본 가드',
                'gi_no_gi': 'both'
            },
            {
                'id': 2, 'name': '오픈 가드', 'name_en': 'Open Guard',
                'category': 'guard', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '다리를 열어 다양한 각도에서 상대방을 컨트롤',
                'gi_no_gi': 'both'
            },
            {
                'id': 23, 'name': '하프 가드', 'name_en': 'Half Guard',
                'category': 'guard', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '한쪽 다리만 감싸는 가드 포지션, 방어와 공격 모두 가능',
                'gi_no_gi': 'both'
            },
            {
                'id': 24, 'name': '딥 하프 가드', 'name_en': 'Deep Half Guard',
                'category': 'guard', 'difficulty': 3, 'position': 'bottom', 'duration': 15,
                'description': '상대방의 다리 깊숙이 들어가는 고급 하프 가드',
                'gi_no_gi': 'both'
            },
            # Guard passes
            {
                'id': 6, 'name': '토리안도 패스', 'name_en': 'Toreando Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '상대방의 다리를 옆으로 밀어내며 패스하는 기술',
                'gi_no_gi': 'both'
            },
            {
                'id': 30, 'name': '하프 가드 패스', 'name_en': 'Half Guard Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '하프 가드를 무력화하고 사이드 컨트롤로 패스',
                'gi_no_gi': 'both'
            },
            # Mount
            {
                'id': 8, 'name': '마운트 컨트롤', 'name_en': 'Mount Control',
                'category': 'mount', 'difficulty': 1, 'position': 'top', 'duration': 8,
                'description': '마운트 포지션에서 안정적으로 컨트롤 유지',
                'gi_no_gi': 'both'
            },
            # Side control
            {
                'id': 11, 'name': '사이드 컨트롤', 'name_en': 'Side Control',
                'category': 'side_control', 'difficulty': 1, 'position': 'top', 'duration': 8,
                'description': '상대방의 옆에서 컨트롤하는 기본 포지션',
                'gi_no_gi': 'both'
            },
            # Submissions
            {
                'id': 15, 'name': '리어 네이키드 초크', 'name_en': 'Rear Naked Choke',
                'category': 'submission', 'difficulty': 2, 'position': 'back', 'duration': 8,
                'description': '뒤에서 목을 조르는 기본 초크',
                'gi_no_gi': 'both'
            },
            {
                'id': 16, 'name': '마운트 암바', 'name_en': 'Armbar from Mount',
                'category': 'submission', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '마운트에서 팔을 꺾는 관절기',
                'gi_no_gi': 'both'
            },
            {
                'id': 17, 'name': '트라이앵글 초크', 'name_en': 'Triangle Choke',
                'category': 'submission', 'difficulty': 3, 'position': 'bottom', 'duration': 12,
                'description': '다리로 삼각형을 만들어 목을 조르는 기술',
                'gi_no_gi': 'both'
            },
            # Sweeps
            {
                'id': 20, 'name': '시저 스윕', 'name_en': 'Scissor Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 10,
                'description': '다리를 가위처럼 사용하는 스윕',
                'gi_no_gi': 'both'
            },
            {
                'id': 26, 'name': '하프 가드 스윕', 'name_en': 'Half Guard Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 10,
                'description': '하프 가드에서 언더훅을 이용한 기본 스윕',
                'gi_no_gi': 'both'
            }
        ]
    
    def filter_techniques(self, max_difficulty: int = None, category: str = None, 
                         gi_preference: str = None) -> List[Dict]:
        filtered = self.techniques.copy()
        
        if max_difficulty:
            filtered = [t for t in filtered if t['difficulty'] <= max_difficulty]
        
        if category:
            filtered = [t for t in filtered if t['category'] == category]
        
        if gi_preference and gi_preference != 'both':
            filtered = [t for t in filtered if t['gi_no_gi'] in [gi_preference, 'both']]
        
        return filtered

# =============================================================================
# NLP Processor
# =============================================================================

class AdvancedNLPProcessor:
    def __init__(self):
        self.level_keywords = {
            'beginner': ['초보', '초급', '새로운', '처음', '기초', '화이트'],
            'intermediate': ['중급', '중간', '어느정도', '보통', '경험', '블루', '퍼플', '하프'],
            'advanced': ['고급', '상급', '고수', '전문', '숙련', '마스터', '브라운', '블랙']
        }
        
        self.position_keywords = {
            'guard': ['가드', '하체', '다리', '하프', 'half', '하프가드'],
            'mount': ['마운트', 'mount', '올라타기', '압박'],
            'side_control': ['사이드', '사이드컨트롤', 'side', '옆'],
            'submission': ['서브미션', '서브', '조르기', '잠그기', '관절기'],
            'sweep': ['스윕', '뒤집기', 'sweep', '역전'],
            'guard_pass': ['패스', 'pass', '가드패스', '뚫기']
        }
        
        self.time_keywords = {
            'short': ['짧은', '빠른', '30분', '짧게'],
            'medium': ['중간', '1시간', '보통'],
            'long': ['긴', '오래', '2시간', '길게']
        }
    
    def analyze_user_request(self, text: str) -> Dict:
        text_lower = text.lower()
        
        return {
            'level': self._detect_level(text_lower),
            'positions': self._detect_positions(text_lower),
            'duration': self._detect_duration(text_lower),
            'gi_preference': self._detect_gi_preference(text_lower)
        }
    
    def _detect_level(self, text: str) -> str:
        for level, keywords in self.level_keywords.items():
            if any(keyword in text for keyword in keywords):
                return level
        return 'beginner'
    
    def _detect_positions(self, text: str) -> List[str]:
        detected_positions = []
        for position, keywords in self.position_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected_positions.append(position)
        return detected_positions
    
    def _detect_duration(self, text: str) -> str:
        for duration, keywords in self.time_keywords.items():
            if any(keyword in text for keyword in keywords):
                return duration
        return 'medium'
    
    def _detect_gi_preference(self, text: str) -> str:
        if any(word in text for word in ['도복', 'gi', '기']):
            return 'gi'
        elif any(word in text for word in ['노기', 'nogi', 'no-gi']):
            return 'no-gi'
        return 'both'

# =============================================================================
# Training Program Generator
# =============================================================================

class SmartTrainingGenerator:
    def __init__(self, database: BJJTechniqueDatabase):
        self.db = database
        self.duration_map = {'short': 30, 'medium': 60, 'long': 90}
    
    def generate_program(self, analysis: Dict, belt_info: Dict) -> Dict:
        max_difficulty = belt_info['max_difficulty']
        total_duration = self.duration_map[analysis['duration']]
        
        available_techniques = self.db.filter_techniques(
            max_difficulty=max_difficulty,
            gi_preference=analysis['gi_preference']
        )
        
        # Filter by position if specified
        if analysis['positions']:
            position_techniques = []
            for position in analysis['positions']:
                position_techniques.extend([
                    t for t in available_techniques if t['category'] == position
                ])
            if position_techniques:
                available_techniques = position_techniques
        
        program = {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'total_duration': total_duration,
                'belt': belt_info['emoji'] + ' ' + [k for k, v in BJJ_BELTS.items() if v == belt_info][0].split()[1],
                'max_difficulty': max_difficulty
            },
            'warm_up': self._generate_warmup(int(total_duration * 0.2)),
            'main_session': self._generate_main_session(available_techniques, int(total_duration * 0.6)),
            'cool_down': self._generate_cooldown(int(total_duration * 0.2))
        }
        
        return program
    
    def _generate_warmup(self, duration: int) -> List[Dict]:
        warmup_exercises = [
            {'name': '관절 돌리기', 'duration': 3, 'description': '목, 어깨, 허리 관절 풀기'},
            {'name': '동적 스트레칭', 'duration': 4, 'description': '다리 벌리기, 허리 돌리기'},
            {'name': '기본 무브먼트', 'duration': 3, 'description': '쉬림프, 브릿지 연습'}
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
    
    def _generate_main_session(self, techniques: List[Dict], duration: int) -> List[Dict]:
        if not techniques:
            return []
        
        num_techniques = min(len(techniques), max(3, duration // 12))
        selected_techniques = random.sample(techniques, num_techniques)
        time_per_technique = duration // len(selected_techniques)
        
        main_session = []
        for tech in selected_techniques:
            session_item = {
                'technique': tech['name'],
                'category': tech['category'],
                'difficulty': tech['difficulty'],
                'duration': time_per_technique,
                'description': tech['description'],
                'difficulty_stars': '⭐' * tech['difficulty']
            }
            main_session.append(session_item)
        
        return main_session
    
    def _generate_cooldown(self, duration: int) -> List[Dict]:
        return [
            {'name': '정적 스트레칭', 'duration': duration // 2, 'description': '어깨, 허리, 다리 스트레칭'},
            {'name': '호흡 정리', 'duration': duration // 2, 'description': '복식호흡으로 심박수 안정화'}
        ]

# =============================================================================
# YouTube Recommendation System
# =============================================================================

class YouTubeRecommendationSystem:
    def __init__(self):
        self.bjj_instructors = {
            'beginner': ['Gracie Breakdown', 'StephanKesting', 'GrappleArts'],
            'intermediate': ['BJJ Fanatics', 'Keenan Online', 'JiuJitsuX'],
            'advanced': ['John Danaher', 'Gordon Ryan', 'Lachlan Giles']
        }
    
    def create_youtube_search_url(self, query: str) -> str:
        """Create YouTube search URL"""
        encoded_query = urllib.parse.quote(query)
        return f"https://www.youtube.com/results?search_query={encoded_query}"
    
    def get_recommendations(self, program: Dict) -> List[Dict]:
        """Get video recommendations for program"""
        recommendations = []
        belt_level = program['metadata'].get('belt', '🤍 화이트')
        
        for session_item in program['main_session']:
            technique_name = session_item['technique']
            difficulty = session_item.get('difficulty', 1)
            
            # Basic tutorial search
            basic_query = f"{technique_name} BJJ tutorial"
            search_url = self.create_youtube_search_url(basic_query)
            
            recommendation = {
                'technique': technique_name,
                'video': {
                    'title': f'{technique_name} - 기본 튜토리얼',
                    'channel': 'YouTube 실시간 검색',
                    'url': search_url,
                    'query': basic_query
                },
                'why_recommended': f"{belt_level} 수준에 맞는 {technique_name} 학습 영상을 찾아드립니다",
                'quality_indicator': '🎯 추천',
                'search_tips': '💡 팁: 영상 길이가 10분 이상인 상세한 설명을 선택하세요'
            }
            
            recommendations.append(recommendation)
        
        return recommendations

# =============================================================================
# Feedback System
# =============================================================================

class FeedbackSystem:
    def __init__(self):
        self.encouragements = {
            'high': ["훌륭합니다! 정말 열심히 하고 있어요!", "완벽한 훈련이었습니다!"],
            'good': ["좋은 진전이에요! 꾸준히 발전하고 있습니다!", "점점 나아지고 있어요!"],
            'needs_work': ["괜찮아요! 모든 고수들도 이런 과정을 거쳤답니다!", "꾸준함이 가장 중요해요!"]
        }
    
    def generate_feedback(self, completion_rate: float, belt_name: str) -> Dict:
        if completion_rate >= 0.8:
            category = 'high'
            performance = "Excellent"
        elif completion_rate >= 0.6:
            category = 'good'  
            performance = "Good"
        else:
            category = 'needs_work'
            performance = "Keep Trying"
        
        return {
            'performance': performance,
            'completion_rate': f"{completion_rate * 100:.0f}%",
            'encouragement': random.choice(self.encouragements[category]),
            'belt_specific_tip': self._get_belt_tip(belt_name)
        }
    
    def _get_belt_tip(self, belt_name: str) -> str:
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

# =============================================================================
# Main Application
# =============================================================================

def create_login_system():
    """Enhanced login system with demo account"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_data = None
    
    if not st.session_state.authenticated:
        st.title("🥋 BJJ 맞춤 훈련 시스템")
        st.markdown("### 온라인 버전 - 개인화된 주짓수 훈련")
        
        # Demo account info
        st.info("💡 **데모 계정으로 빠른 체험**: \n"
                "- 사용자명: `demo` \n" 
                "- 비밀번호: `demo123`")
        
        tab1, tab2 = st.tabs(["🔐 로그인", "📝 회원가입"])
        
        with tab1:
            st.subheader("로그인")
            username = st.text_input("사용자명", key="login_username")
            password = st.text_input("비밀번호", type="password", key="login_password")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("로그인", type="primary"):
                    if username and password:
                        db = st.session_state.cloud_db
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
            
            with col2:
                if st.button("데모 계정으로 로그인"):
                    db = st.session_state.cloud_db
                    demo_user = db.authenticate_user("demo", "demo123")
                    if demo_user:
                        st.session_state.authenticated = True
                        st.session_state.user_data = demo_user
                        st.success("데모 계정으로 로그인!")
                        st.rerun()
                    else:
                        st.error("데모 계정 로그인 실패")
        
        with tab2:
            st.subheader("회원가입")
            new_username = st.text_input("사용자명", key="signup_username")
            new_email = st.text_input("이메일", key="signup_email")
            new_password = st.text_input("비밀번호", type="password", key="signup_password")
            confirm_password = st.text_input("비밀번호 확인", type="password", key="confirm_password")
            
            belt_options = list(BJJ_BELTS.keys())
            selected_belt = st.selectbox("현재 띠", belt_options, key="signup_belt")
            
            st.warning("⚠️ **클라우드 버전 주의사항**: 브라우저를 완전히 닫으면 데이터가 초기화됩니다.")
            
            if st.button("회원가입"):
                if new_username and new_email and new_password:
                    if new_password != confirm_password:
                        st.error("비밀번호가 일치하지 않습니다.")
                    elif len(new_password) < 6:
                        st.error("비밀번호는 6자 이상이어야 합니다.")
                    else:
                        try:
                            db = st.session_state.cloud_db
                            user_id = db.create_user(new_username, new_email, new_password, selected_belt)
                            st.success("회원가입 성공! 로그인해주세요.")
                        except ValueError as e:
                            st.error(str(e))
                else:
                    st.warning("모든 필드를 입력하세요.")
        
        return False
    
    return True

def create_training_program_tab(user_data):
    """Training program generation tab"""
    st.header("🎯 맞춤형 훈련 프로그램 생성")
    
    # User belt info
    belt_info = BJJ_BELTS[user_data['current_belt']]
    
    st.info(f"**{belt_info['emoji']} {user_data['current_belt']} 수련생**\n"
            f"권장 난이도: {belt_info['max_difficulty']}/5 | "
            f"특징: {belt_info['description']}")
    
    # Training request input
    user_request = st.text_area(
        "오늘의 훈련 목표를 입력하세요:",
        placeholder="예: 하프 가드 기술 위주로 1시간 집중 훈련하고 싶어요",
        height=100
    )
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 프로그램 생성", type="primary"):
            if user_request:
                with st.spinner("개인 맞춤 훈련 프로그램 생성 중..."):
                    # NLP analysis
                    analysis = st.session_state.nlp.analyze_user_request(user_request)
                    
                    # Generate program
                    program = st.session_state.generator.generate_program(analysis, belt_info)
                    program['metadata']['user_id'] = user_data['id']
                    program['metadata']['belt'] = user_data['current_belt']
                    
                    st.session_state.current_program = program
                    
                    st.success("✅ 개인 맞춤 프로그램 생성 완료!")
                    display_training_program(program, belt_info)
            else:
                st.warning("훈련 목표를 입력해주세요.")

def display_training_program(program, belt_info):
    """Display training program"""
    # Program summary
    st.subheader(f"📋 {belt_info['emoji']} 프로그램 요약")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("총 시간", f"{program['metadata']['total_duration']}분")
    with col2:
        st.metric("띠 수준", program['metadata']['belt'])
    with col3:
        st.metric("주요 기술", len(program['main_session']))
    with col4:
        st.metric("최대 난이도", f"{program['metadata']['max_difficulty']}/5")
    
    # Warm-up
    st.subheader("🔥 워밍업")
    for warmup in program['warm_up']:
        st.write(f"• {warmup['name']} ({warmup['duration']}분) - {warmup['description']}")
    
    # Main session
    st.subheader("💪 메인 기술 연습")
    for i, session in enumerate(program['main_session'], 1):
        with st.expander(f"{i}. {session['technique']} ({session['duration']}분) - {session['difficulty_stars']}"):
            st.write(f"**카테고리:** {session['category']}")
            st.write(f"**설명:** {session['description']}")
            st.write(f"**난이도:** {session['difficulty']}/5")
    
    # Cool-down
    st.subheader("🧘‍♂️ 쿨다운")
    for cooldown in program['cool_down']:
        st.write(f"• {cooldown['name']} ({cooldown['duration']}분) - {cooldown['description']}")

def create_video_recommendations_tab():
    """Video recommendations tab"""
    st.header("📹 추천 학습 영상")
    
    if 'current_program' in st.session_state:
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
                        st.write(f"**품질:** {rec['quality_indicator']}")
                    
                    with col2:
                        st.write(f"**추천 이유:** {rec['why_recommended']}")
                        st.write(f"{rec['search_tips']}")
                        st.link_button("🔗 영상 보기", video['url'])
        else:
            st.warning("추천할 영상을 찾지 못했습니다.")
    else:
        st.info("먼저 '훈련 프로그램 생성' 탭에서 프로그램을 만들어주세요.")

def create_feedback_tab(user_data):
    """Feedback and recording tab"""
    st.header("📊 훈련 완료 및 기록")
    
    if 'current_program' in st.session_state:
        program = st.session_state.current_program
        
        st.subheader("훈련 완료 보고")
        
        col1, col2 = st.columns(2)
        with col1:
            completion_rate = st.slider("완주율 (%)", 0, 100, 80) / 100
            difficulty_rating = st.slider("체감 난이도 (1-5)", 1, 5, 3)
        
        with col2:
            enjoyment_rating = st.slider("만족도 (1-5)", 1, 5, 4)
            notes = st.text_area("훈련 노트", placeholder="오늘 훈련에서 배운 점, 어려웠던 점 등을 기록하세요")
        
        # Technique success tracking
        st.subheader("기술별 연습 결과")
        technique_results = {}
        for i, session in enumerate(program['main_session']):
            technique_results[session['technique']] = st.checkbox(
                f"{session['technique']} - 성공적으로 연습함",
                key=f"tech_{i}"
            )
        
        if st.button("📝 훈련 기록 저장", type="primary"):
            # Save to database
            session_data = {
                'user_id': user_data['id'],
                'belt_level': user_data['current_belt'],
                'total_duration': program['metadata']['total_duration'],
                'completion_rate': completion_rate,
                'difficulty_rating': difficulty_rating,
                'enjoyment_rating': enjoyment_rating,
                'techniques_practiced': [s['technique'] for s in program['main_session']],
                'program_data': program,
                'notes': notes
            }
            
            session_id = st.session_state.cloud_db.save_training_session(session_data)
            
            st.success("✅ 훈련 기록이 저장되었습니다!")
            st.balloons()
    else:
        st.info("먼저 훈련 프로그램을 생성해주세요.")

def create_personal_stats_tab(user_data):
    """Personal statistics tab"""
    st.header("📈 개인 훈련 통계")
    
    # Get user statistics
    stats = st.session_state.cloud_db.get_user_stats(user_data['id'])
    
    if stats and stats['total_sessions'] > 0:
        # Basic statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 훈련 세션", stats['total_sessions'])
        with col2:
            st.metric("총 훈련 시간", f"{stats['total_hours']:.1f}시간")
        with col3:
            st.metric("평균 완주율", f"{stats['avg_completion_rate'] * 100:.1f}%")
        with col4:
            st.metric("평균 난이도", f"{stats['avg_difficulty']:.1f}/5")
        
        # Recent sessions chart
        if stats['recent_sessions']:
            st.subheader("📊 최근 훈련 기록")
            sessions_df = pd.DataFrame(stats['recent_sessions'], 
                                     columns=['날짜', '완주율', '난이도', '만족도'])
            sessions_df['날짜'] = pd.to_datetime(sessions_df['날짜'])
            st.line_chart(sessions_df.set_index('날짜')[['완주율', '만족도']])
    else:
        st.info("아직 훈련 기록이 없습니다. 첫 번째 훈련을 시작해보세요!")

def create_settings_tab(user_data):
    """Settings tab"""
    st.header("⚙️ 계정 설정")
    
    st.subheader("사용자 정보")
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("사용자명", value=user_data['username'], disabled=True)
        st.text_input("이메일", value=user_data.get('email', ''), disabled=True)
    
    with col2:
        st.selectbox("현재 띠", 
                    list(BJJ_BELTS.keys()), 
                    index=list(BJJ_BELTS.keys()).index(user_data['current_belt']))
        st.selectbox("도복 선호도", 
                    ["both", "gi", "no-gi"], 
                    index=["both", "gi", "no-gi"].index(user_data.get('gi_preference', 'both')))
    
    if st.button("설정 저장"):
        st.success("설정이 저장되었습니다!")

def create_bjj_app():
    """Main BJJ Training Application"""
    st.set_page_config(
        page_title="BJJ 훈련 시스템",
        page_icon="🥋",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Initialize cloud data manager
    if 'cloud_db' not in st.session_state:
        st.session_state.cloud_db = CloudDataManager()
    
    # Check login
    if not create_login_system():
        return
    
    # Initialize other components
    if 'nlp' not in st.session_state:
        st.session_state.tech_db = BJJTechniqueDatabase()
        st.session_state.nlp = AdvancedNLPProcessor()
        st.session_state.generator = SmartTrainingGenerator(st.session_state.tech_db)
        st.session_state.youtube = YouTubeRecommendationSystem()
        st.session_state.feedback = FeedbackSystem()
    
    # Main app
    user_data = st.session_state.user_data
    
    # Top navigation
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.title(f"🥋 {user_data['username']}님의 BJJ 훈련 시스템")
        st.caption("🌐 온라인 버전 (세션 기반 저장)")
    with col2:
        st.metric("현재 띠", user_data['current_belt'])
    with col3:
        if st.button("로그아웃"):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()
    
    st.markdown("---")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 훈련 프로그램", 
        "📹 영상 추천", 
        "📊 피드백 및 기록", 
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
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    create_bjj_app()

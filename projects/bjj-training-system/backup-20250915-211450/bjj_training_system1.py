# 주짓수 띠별 맞춤 훈련 시스템 - 최종 완전판
# 필수 패키지: pip install streamlit pandas numpy scikit-learn requests
import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import re
import random
import sys

# =============================================================================
# 데이터베이스 관리 클래스
# =============================================================================

class BJJDatabase:
    """BJJ 훈련 시스템 데이터베이스 관리"""
    
    def __init__(self, db_path: str = "bjj_training.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 사용자 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT,
                current_belt TEXT NOT NULL,
                current_stripes INTEGER DEFAULT 0,
                experience_months INTEGER DEFAULT 0,
                gi_preference TEXT DEFAULT 'both',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                total_sessions INTEGER DEFAULT 0,
                total_hours REAL DEFAULT 0.0
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
                FOREIGN KEY (user_id) REFERENCES users (id)
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
                FOREIGN KEY (user_id) REFERENCES users (id)
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
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, technique_name)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, username: str, email: str, password: str, belt: str) -> str:
        """새 사용자 생성"""
        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
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
            return user_id
        except sqlite3.IntegrityError as e:
            conn.rollback()
            raise ValueError(f"사용자 생성 실패: {str(e)}")
        finally:
            conn.close()
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """사용자 인증"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, current_belt, current_stripes, 
                   experience_months, gi_preference, total_sessions, total_hours
            FROM users 
            WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'user_id': result[0],
                'username': result[1],
                'email': result[2],
                'current_belt': result[3],
                'current_stripes': result[4],
                'experience_months': result[5],
                'gi_preference': result[6],
                'total_sessions': result[7],
                'total_hours': result[8]
            }
        return None
    
    def save_training_session(self, session_data: Dict) -> str:
        """훈련 세션 저장"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO training_sessions (
                id, user_id, belt_level, total_duration, completion_rate,
                difficulty_rating, enjoyment_rating, techniques_practiced,
                program_data, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            session_data.get('notes', '')
        ))
        
        # 사용자 총 세션 수와 시간 업데이트
        cursor.execute('''
            UPDATE users 
            SET total_sessions = total_sessions + 1,
                total_hours = total_hours + ?,
                last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session_data['total_duration'] / 60.0, session_data['user_id']))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def get_user_stats(self, user_id: str) -> Dict:
        """사용자 통계 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기본 사용자 정보
        cursor.execute('''
            SELECT current_belt, total_sessions, total_hours, experience_months
            FROM users WHERE id = ?
        ''', (user_id,))
        user_info = cursor.fetchone()
        
        # 최근 세션들
        cursor.execute('''
            SELECT session_date, completion_rate, difficulty_rating, enjoyment_rating
            FROM training_sessions 
            WHERE user_id = ? 
            ORDER BY session_date DESC 
            LIMIT 10
        ''', (user_id,))
        recent_sessions = cursor.fetchall()
        
        # 기술 마스터리
        cursor.execute('''
            SELECT technique_name, category, practice_count, mastery_level
            FROM technique_mastery 
            WHERE user_id = ? 
            ORDER BY mastery_level DESC
            LIMIT 20
        ''', (user_id,))
        top_techniques = cursor.fetchall()
        
        conn.close()
        
        if user_info:
            return {
                'current_belt': user_info[0],
                'total_sessions': user_info[1],
                'total_hours': user_info[2],
                'experience_months': user_info[3],
                'recent_sessions': recent_sessions,
                'top_techniques': top_techniques,
                'avg_completion_rate': np.mean([s[1] for s in recent_sessions]) if recent_sessions else 0,
                'avg_difficulty': np.mean([s[2] for s in recent_sessions if s[2]]) if recent_sessions else 0
            }
        return {}
    
    def update_technique_mastery(self, user_id: str, technique_name: str, 
                               category: str, difficulty: int, success: bool):
        """기술 마스터리 업데이트"""
        conn = sqlite3.connect(self.db_path)
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
            practice_count, mastery_level, success_rate = result
            new_practice_count = practice_count + 1
            new_success_rate = ((success_rate * practice_count) + (1.0 if success else 0.0)) / new_practice_count
            new_mastery_level = min(1.0, mastery_level + (0.1 if success else 0.05))
            
            cursor.execute('''
                UPDATE technique_mastery 
                SET practice_count = ?, mastery_level = ?, success_rate = ?, last_practiced = CURRENT_TIMESTAMP
                WHERE user_id = ? AND technique_name = ?
            ''', (new_practice_count, new_mastery_level, new_success_rate, user_id, technique_name))
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
        conn.close()

# =============================================================================
# 개선된 사용자 인터페이스
# =============================================================================

def create_login_system():
    """로그인/회원가입 시스템"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_data = None
    
    if not st.session_state.authenticated:
        st.title("BJJ 맞춤 훈련 시스템")
        st.markdown("개인화된 주짓수 훈련을 위해 로그인하세요")
        
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
            new_username = st.text_input("사용자명", key="signup_username")
            new_email = st.text_input("이메일", key="signup_email")
            new_password = st.text_input("비밀번호", type="password", key="signup_password")
            confirm_password = st.text_input("비밀번호 확인", type="password", key="confirm_password")
            
            belt_options = ["🤍 화이트 벨트", "🔵 블루 벨트", "🟣 퍼플 벨트", "🟤 브라운 벨트", "⚫ 블랙 벨트"]
            selected_belt = st.selectbox("현재 띠", belt_options, key="signup_belt")
            
            if st.button("회원가입"):
                if new_username and new_email and new_password:
                    if new_password != confirm_password:
                        st.error("비밀번호가 일치하지 않습니다.")
                    elif len(new_password) < 6:
                        st.error("비밀번호는 6자 이상이어야 합니다.")
                    else:
                        try:
                            db = BJJDatabase()
                            user_id = db.create_user(new_username, new_email, new_password, selected_belt)
                            st.success("회원가입 성공! 로그인해주세요.")
                        except ValueError as e:
                            st.error(str(e))
                else:
                    st.warning("모든 필드를 입력하세요.")
        
        return False
    
    return True

def create_enhanced_streamlit_app():
    """개선된 Streamlit 애플리케이션"""
    st.set_page_config(
        page_title="BJJ 개인 훈련 시스템",
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
        st.title(f"🥋 {user_data['username']}님의 BJJ 훈련 시스템")
    with col2:
        st.metric("현재 띠", user_data['current_belt'])
    with col3:
        if st.button("로그아웃"):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.rerun()
    
    st.markdown("---")
    
    # 데이터베이스 초기화
    if 'db' not in st.session_state:
        st.session_state.db_manager = BJJDatabase()
        st.session_state.tech_db = BJJTechniqueDatabase()
        st.session_state.nlp = AdvancedNLPProcessor()
        st.session_state.generator = SmartTrainingGenerator(st.session_state.tech_db)
        st.session_state.youtube = YouTubeRecommendationSystem()
        st.session_state.feedback = FeedbackSystem()
    
    # 메인 탭들
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

def create_training_program_tab(user_data):
    """훈련 프로그램 생성 탭"""
    st.header("🎯 맞춤형 훈련 프로그램 생성")
    
    # 사용자 벨트 정보
    belt_info = BJJ_BELTS[user_data['current_belt']]
    
    st.info(f"**{belt_info['emoji']} {user_data['current_belt']} 수련생**\n"
            f"권장 난이도: {belt_info['max_difficulty']}/5 | "
            f"특징: {belt_info['description']}")
    
    # 훈련 요청 입력
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
                    # NLP 분석
                    analysis = st.session_state.nlp.analyze_user_request(user_request)
                    
                    # 프로그램 생성
                    program = st.session_state.generator.generate_program(analysis, belt_info)
                    program['metadata']['user_id'] = user_data['user_id']
                    program['metadata']['belt'] = user_data['current_belt']
                    
                    st.session_state.current_program = program
                    
                    st.success("✅ 개인 맞춤 프로그램 생성 완료!")
                    display_training_program(program, belt_info)
            else:
                st.warning("훈련 목표를 입력해주세요.")

def create_feedback_tab(user_data):
    """피드백 및 기록 탭"""
    st.header("📊 훈련 완료 및 기록")
    
    if 'current_program' in st.session_state:
        program = st.session_state.current_program
        
        st.subheader(f"훈련 완료 보고")
        
        col1, col2 = st.columns(2)
        with col1:
            completion_rate = st.slider("완주율 (%)", 0, 100, 80) / 100
            difficulty_rating = st.slider("체감 난이도 (1-5)", 1, 5, 3)
        
        with col2:
            enjoyment_rating = st.slider("만족도 (1-5)", 1, 5, 4)
            notes = st.text_area("훈련 노트", placeholder="오늘 훈련에서 배운 점, 어려웠던 점 등을 기록하세요")
        
        # 기술별 성공 여부
        st.subheader("기술별 연습 결과")
        technique_results = {}
        for i, session in enumerate(program['main_session']):
            technique_results[session['technique']] = st.checkbox(
                f"{session['technique']} - 성공적으로 연습함",
                key=f"tech_{i}"
            )
        
        if st.button("📝 훈련 기록 저장", type="primary"):
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
                'notes': notes
            }
            
            session_id = st.session_state.db_manager.save_training_session(session_data)
            
            # 기술 마스터리 업데이트
            for technique, success in technique_results.items():
                tech_data = next((s for s in program['main_session'] if s['technique'] == technique), None)
                if tech_data:
                    st.session_state.db_manager.update_technique_mastery(
                        user_data['user_id'],
                        technique,
                        tech_data['category'],
                        tech_data['difficulty'],
                        success
                    )
            
            st.success("✅ 훈련 기록이 저장되었습니다!")
            st.balloons()
    else:
        st.info("먼저 훈련 프로그램을 생성해주세요.")

def create_personal_stats_tab(user_data):
    """개인 통계 탭"""
    st.header("📈 개인 훈련 통계")
    
    # 사용자 통계 조회
    stats = st.session_state.db_manager.get_user_stats(user_data['user_id'])
    
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
        st.selectbox("현재 띠", 
                    list(BJJ_BELTS.keys()), 
                    index=list(BJJ_BELTS.keys()).index(user_data['current_belt']))
        st.selectbox("도복 선호도", 
                    ["both", "gi", "no-gi"], 
                    index=["both", "gi", "no-gi"].index(user_data['gi_preference']))
    
    if st.button("설정 저장"):
        st.success("설정이 저장되었습니다!")

# =============================================================================
# 주짓수 띠 시스템 정의
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
# 기술 데이터베이스
# =============================================================================

class BJJTechniqueDatabase:
    def __init__(self):
        self.techniques = self._load_techniques()
    
    def _load_techniques(self) -> List[Dict]:
        techniques_data = [
            # 가드 기술들
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
                'id': 3, 'name': '델라리바 가드', 'name_en': 'De La Riva Guard',
                'category': 'guard', 'difficulty': 4, 'position': 'bottom', 'duration': 15,
                'description': '상대방의 다리 뒤쪽에 후킹하는 고급 오픈 가드',
                'gi_no_gi': 'both'
            },
            {
                'id': 4, 'name': '스파이더 가드', 'name_en': 'Spider Guard',
                'category': 'guard', 'difficulty': 3, 'position': 'bottom', 'duration': 15,
                'description': '상대방의 소매를 잡고 발로 팔을 컨트롤하는 가드',
                'gi_no_gi': 'gi'
            },
            {
                'id': 5, 'name': '버터플라이 가드', 'name_en': 'Butterfly Guard',
                'category': 'guard', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '앉은 상태에서 발로 상대방의 다리를 후킹',
                'gi_no_gi': 'both'
            },
            
            # 패스 가드
            {
                'id': 6, 'name': '토리안도 패스', 'name_en': 'Toreando Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '상대방의 다리를 옆으로 밀어내며 패스하는 기술',
                'gi_no_gi': 'both'
            },
            {
                'id': 7, 'name': '더블 언더 패스', 'name_en': 'Double Under Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 12,
                'description': '양손으로 상대방의 다리 밑을 감싸며 압박하는 패스',
                'gi_no_gi': 'both'
            },
            
            # 마운트
            {
                'id': 8, 'name': '마운트 컨트롤', 'name_en': 'Mount Control',
                'category': 'mount', 'difficulty': 1, 'position': 'top', 'duration': 8,
                'description': '마운트 포지션에서 안정적으로 컨트롤 유지',
                'gi_no_gi': 'both'
            },
            {
                'id': 9, 'name': '하이 마운트', 'name_en': 'High Mount',
                'category': 'mount', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '상대방의 겨드랑이 쪽으로 올라가는 마운트',
                'gi_no_gi': 'both'
            },
            {
                'id': 10, 'name': 'S-마운트', 'name_en': 'S-Mount',
                'category': 'mount', 'difficulty': 3, 'position': 'top', 'duration': 12,
                'description': 'S자 형태로 다리를 배치하는 마운트 변형',
                'gi_no_gi': 'both'
            },
            
            # 사이드 컨트롤
            {
                'id': 11, 'name': '사이드 컨트롤', 'name_en': 'Side Control',
                'category': 'side_control', 'difficulty': 1, 'position': 'top', 'duration': 8,
                'description': '상대방의 옆에서 컨트롤하는 기본 포지션',
                'gi_no_gi': 'both'
            },
            {
                'id': 12, 'name': '니 온 벨리', 'name_en': 'Knee on Belly',
                'category': 'side_control', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '무릎으로 상대방의 배를 압박하는 포지션',
                'gi_no_gi': 'both'
            },
            
            # 백 컨트롤
            {
                'id': 13, 'name': '백 컨트롤', 'name_en': 'Back Control',
                'category': 'back_control', 'difficulty': 2, 'position': 'back', 'duration': 12,
                'description': '상대방의 등 뒤에서 후크로 컨트롤',
                'gi_no_gi': 'both'
            },
            {
                'id': 14, 'name': '바디 트라이앵글', 'name_en': 'Body Triangle',
                'category': 'back_control', 'difficulty': 3, 'position': 'back', 'duration': 15,
                'description': '다리로 삼각형을 만들어 더 강하게 컨트롤',
                'gi_no_gi': 'both'
            },
            
            # 서브미션
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
            {
                'id': 18, 'name': '키무라', 'name_en': 'Kimura',
                'category': 'submission', 'difficulty': 2, 'position': 'various', 'duration': 10,
                'description': '어깨 관절을 공격하는 관절기',
                'gi_no_gi': 'both'
            },
            {
                'id': 19, 'name': '기요틴 초크', 'name_en': 'Guillotine Choke',
                'category': 'submission', 'difficulty': 2, 'position': 'various', 'duration': 10,
                'description': '앞에서 목을 감싸 조르는 초크',
                'gi_no_gi': 'both'
            },
            
            # 스윕
            {
                'id': 20, 'name': '시저 스윕', 'name_en': 'Scissor Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 10,
                'description': '다리를 가위처럼 사용하는 스윕',
                'gi_no_gi': 'both'
            },
            {
                'id': 21, 'name': '힙 범프 스윕', 'name_en': 'Hip Bump Sweep',
                'category': 'sweep', 'difficulty': 1, 'position': 'bottom', 'duration': 8,
                'description': '엉덩이로 밀어내는 기본 스윕',
                'gi_no_gi': 'both'
            },
            {
                'id': 22, 'name': '플라워 스윕', 'name_en': 'Flower Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 12,
                'description': '상대방의 팔과 다리를 동시에 컨트롤하는 스윕',
                'gi_no_gi': 'gi'
            }
            ,
            
            # 하프 가드 기본
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
            {
                'id': 25, 'name': 'Z 가드', 'name_en': 'Z Guard',
                'category': 'guard', 'difficulty': 3, 'position': 'bottom', 'duration': 12,
                'description': '무릎 방패를 만드는 하프 가드 변형',
                'gi_no_gi': 'both'
            },
            
            # 하프 가드 스윕들
            {
                'id': 26, 'name': '하프 가드 스윕', 'name_en': 'Half Guard Sweep',
                'category': 'sweep', 'difficulty': 2, 'position': 'bottom', 'duration': 10,
                'description': '하프 가드에서 언더훅을 이용한 기본 스윕',
                'gi_no_gi': 'both'
            },
            {
                'id': 27, 'name': '올드 스쿨 스윕', 'name_en': 'Old School Sweep',
                'category': 'sweep', 'difficulty': 3, 'position': 'bottom', 'duration': 12,
                'description': '하프 가드에서 상대방의 발목을 잡는 클래식 스윕',
                'gi_no_gi': 'both'
            },
            {
                'id': 28, 'name': '딥 하프 스윕', 'name_en': 'Deep Half Sweep',
                'category': 'sweep', 'difficulty': 4, 'position': 'bottom', 'duration': 15,
                'description': '딥 하프 가드에서 실행하는 고급 스윕',
                'gi_no_gi': 'both'
            },
            
            # 하프 가드 서브미션
            {
                'id': 29, 'name': '하프 가드 김플렉스', 'name_en': 'Half Guard Kimplex',
                'category': 'submission', 'difficulty': 4, 'position': 'bottom', 'duration': 12,
                'description': '하프 가드에서 다리를 이용한 키무라 변형',
                'gi_no_gi': 'both'
            },
            
            # 하프 가드 패스 (상대방 관점)
            {
                'id': 30, 'name': '하프 가드 패스', 'name_en': 'Half Guard Pass',
                'category': 'guard_pass', 'difficulty': 2, 'position': 'top', 'duration': 10,
                'description': '하프 가드를 무력화하고 사이드 컨트롤로 패스',
                'gi_no_gi': 'both'
            },
            {
                'id': 31, 'name': '크로스페이스 패스', 'name_en': 'Crossface Pass',
                'category': 'guard_pass', 'difficulty': 3, 'position': 'top', 'duration': 12,
                'description': '크로스페이스 압박으로 하프 가드 패스',
                'gi_no_gi': 'both'
            }
        ]
        
        return techniques_data
    
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
# NLP 처리기
# =============================================================================

class AdvancedNLPProcessor:
    def __init__(self):
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
    
    def analyze_user_request(self, text: str) -> Dict:
        text_lower = text.lower()
        
        analysis = {
            'level': self._detect_level(text_lower),
            'positions': self._detect_positions(text_lower),
            'duration': self._detect_duration(text_lower),
            'gi_preference': self._detect_gi_preference(text_lower)
        }
        
        return analysis
    
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
# 훈련 프로그램 생성기
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
    
    # 포지션별 기술 선별 (이 부분 수정!)
        if analysis['positions']:
            position_techniques = []
            for position in analysis['positions']:
            # 'guard' 요청시 모든 가드 기술 포함하도록 수정
                if position == 'guard':
                    position_techniques.extend([
                        t for t in available_techniques if t['category'] == 'guard'
                    ])
                else:
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
            {'name': '기본 무브먼트', 'duration': 3, 'description': '쉬리핑, 브릿지 연습'}
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
        cooldown_exercises = [
            {'name': '정적 스트레칭', 'duration': duration // 2, 'description': '어깨, 허리, 다리 스트레칭'},
            {'name': '호흡 정리', 'duration': duration // 2, 'description': '복식호흡으로 심박수 안정화'}
        ]
        
        return cooldown_exercises

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
    
    def create_optimized_search_queries(self, technique_name: str, category: str, difficulty: int) -> List[Dict]:
        """최적화된 검색 쿼리들 생성"""
        queries = []
        
        # 1. 기본 BJJ 튜토리얼 검색
        basic_query = f"{technique_name} BJJ tutorial"
        queries.append({
            'title': f'{technique_name} - 기본 튜토리얼',
            'search_query': basic_query,
            'type': '기본 학습',
            'priority': 1
        })
        
        # 2. 카테고리별 특화 검색
        if category in self.technique_keywords:
            category_keywords = ' '.join(self.technique_keywords[category][:2])
            category_query = f"{technique_name} {category_keywords} BJJ"
            queries.append({
                'title': f'{technique_name} - 전문 기술',
                'search_query': category_query,
                'type': '기술 특화',
                'priority': 2
            })
        
        # 3. 레벨별 강사 검색
        level_map = {1: 'beginner', 2: 'beginner', 3: 'intermediate', 4: 'advanced', 5: 'advanced'}
        instructor_level = level_map.get(difficulty, 'beginner')
        
        # 대표 강사 2명 선택
        top_instructors = self.bjj_instructors[instructor_level][:2]
        
        for i, instructor in enumerate(top_instructors):
            instructor_query = f"{instructor} {technique_name} BJJ"
            queries.append({
                'title': f'{technique_name} - {instructor}',
                'search_query': instructor_query,
                'type': f'{instructor} 강의',
                'priority': 3 + i
            })
        
        # 4. 상세 분석 검색 (난이도 3 이상)
        if difficulty >= 3:
            details_query = f"{technique_name} details breakdown BJJ analysis"
            queries.append({
                'title': f'{technique_name} - 상세 분석',
                'search_query': details_query,
                'type': '디테일 분석',
                'priority': 6
            })
        
        # 5. 일반 검색 (백업용)
        general_query = f"{technique_name} brazilian jiu jitsu"
        queries.append({
            'title': f'{technique_name} - 일반 검색',
            'search_query': general_query,
            'type': '일반 검색',
            'priority': 7
        })
        
        return queries
    
    def get_recommendations(self, program: Dict) -> List[Dict]:
        """완전 실시간 검색 기반 추천 시스템"""
        recommendations = []
        belt_level = program['metadata'].get('belt', '🤍 화이트')
        
        for session_item in program['main_session']:
            technique_name = session_item['technique']
            category = session_item['category']
            difficulty = session_item.get('difficulty', 1)
            
            # 최적화된 검색 쿼리들 생성
            search_queries = self.create_optimized_search_queries(technique_name, category, difficulty)
            
            # 우선순위 높은 검색 결과들만 선택 (최대 3개)
            top_queries = sorted(search_queries, key=lambda x: x['priority'])[:3]
            
            for i, query_info in enumerate(top_queries):
                search_url = self.create_youtube_search_url(query_info['search_query'])
                
                # 추천 이유 생성
                why_recommended = self._generate_recommendation_reason(
                    technique_name, query_info['type'], difficulty, belt_level
                )
                
                recommendation = {
                    'technique': technique_name,
                    'video': {
                        'title': query_info['title'],
                        'channel': 'YouTube 실시간 검색',
                        'url': search_url,
                        'search_type': query_info['type'],
                        'query': query_info['search_query']
                    },
                    'why_recommended': why_recommended,
                    'quality_indicator': self._get_quality_indicator(query_info['type'], i),
                    'search_tips': self._get_search_tips(query_info['type'])
                }
                
                recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_recommendation_reason(self, technique: str, search_type: str, difficulty: int, belt: str) -> str:
        """추천 이유 생성"""
        reasons = {
            '기본 학습': f"{belt} 수준에 맞는 {technique} 기본 학습 영상을 찾아드립니다",
            '기술 특화': f"{technique}의 전문적인 기술 포인트를 다룬 영상들을 검색합니다",
            '디테일 분석': f"{technique}의 세밀한 디테일과 고급 팁을 제공하는 영상들입니다",
            '일반 검색': f"{technique}에 대한 다양한 관점의 영상들을 폭넓게 검색합니다"
        }
        
        # 강사별 맞춤 메시지
        if any(instructor in search_type for instructor in ['John Danaher', 'Gordon Ryan', 'Lachlan Giles']):
            return f"세계적인 BJJ 전문가의 {technique} 강의를 검색합니다"
        elif any(instructor in search_type for instructor in ['Gracie', 'StephanKesting']):
            return f"검증된 BJJ 교육자의 {technique} 기초 강의를 찾아드립니다"
        
        return reasons.get(search_type, f"{technique} 관련 고품질 영상을 검색합니다")
    
    def _get_quality_indicator(self, search_type: str, index: int) -> str:
        """품질 지표 생성"""
        if index == 0:  # 첫 번째 추천
            return "🎯 최고 추천"
        elif 'John Danaher' in search_type or 'Gordon Ryan' in search_type:
            return "⭐ 전문가 강의"
        elif '기본 학습' in search_type:
            return "📚 기초 학습"
        elif '디테일 분석' in search_type:
            return "🔍 상세 분석"
        else:
            return "✅ 추천"
    
    def _get_search_tips(self, search_type: str) -> str:
        """검색 팁 제공"""
        tips = {
            '기본 학습': "💡 팁: 'beginner', 'fundamentals' 키워드가 포함된 영상을 우선 시청하세요",
            '기술 특화': "💡 팁: 영상 길이가 10분 이상인 상세한 설명 영상을 선택하세요", 
            '디테일 분석': "💡 팁: 'details', 'breakdown', 'analysis' 키워드 영상이 도움됩니다",
            '일반 검색': "💡 팁: 조회수가 높고 최근에 업로드된 영상을 우선 확인하세요"
        }
        
        if 'John Danaher' in search_type:
            return "💡 팁: John Danaher의 체계적인 설명 스타일에 집중하세요"
        elif 'Gracie' in search_type:
            return "💡 팁: Gracie 가문의 전통적이고 안전한 접근법을 배워보세요"
        
        return tips.get(search_type, "💡 팁: 여러 영상을 비교해보고 자신에게 맞는 설명을 찾으세요")
    
    def create_custom_search(self, technique: str, instructor: str = "", additional_terms: str = "") -> str:
        """커스텀 검색 URL 생성 (고급 사용자용)"""
        search_terms = [technique, instructor, additional_terms, "BJJ", "brazilian jiu jitsu"]
        clean_terms = [term for term in search_terms if term.strip()]
        search_query = " ".join(clean_terms)
        
        return self.create_youtube_search_url(search_query)
# =============================================================================
# 피드백 시스템
# =============================================================================

class FeedbackSystem:
    def __init__(self):
        self.encouragements = {
            'high': ["훌륭합니다! 정말 열심히 하고 있어요! 🥋", "완벽한 훈련이었습니다! 💪"],
            'good': ["좋은 진전이에요! 꾸준히 발전하고 있습니다! 😊", "점점 나아지고 있어요! 🔥"],
            'needs_work': ["괜찮아요! 모든 고수들도 이런 과정을 거쳤답니다! 😌", "꾸준함이 가장 중요해요! 🌟"]
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
        
        feedback = {
            'performance': performance,
            'completion_rate': f"{completion_rate * 100:.0f}%",
            'encouragement': random.choice(self.encouragements[category]),
            'belt_specific_tip': self._get_belt_tip(belt_name)
        }
        
        return feedback
    
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
# Streamlit 웹 애플리케이션
# =============================================================================

def create_streamlit_app():
    st.set_page_config(
        page_title="BJJ 띠별 훈련 시스템",
        page_icon="🥋",
        layout="wide"
    )
    
    # 시스템 초기화
    if 'db' not in st.session_state:
        st.session_state.db = BJJTechniqueDatabase()
        st.session_state.nlp = AdvancedNLPProcessor()
        st.session_state.generator = SmartTrainingGenerator(st.session_state.db)
        st.session_state.youtube = YouTubeRecommendationSystem()
        st.session_state.feedback = FeedbackSystem()
    
    st.title("🥋 주짓수 띠별 맞춤 훈련 시스템")
    st.markdown("---")
    
    # 사이드바 - 사용자 프로필
    with st.sidebar:
        st.header("👤 수련생 프로필")
        
        user_name = st.text_input("이름", value="BJJ 수련생")
        
        # 띠 선택
        selected_belt = st.selectbox(
            "현재 띠", 
            list(BJJ_BELTS.keys()),
            help="본인의 현재 주짓수 띠를 선택하세요"
        )
        
        belt_info = BJJ_BELTS[selected_belt]
        belt_name = selected_belt.split()[1]  # "화이트", "블루" 등
        
        # 스트라이프 선택 (블랙벨트 제외)
        if belt_info['stripes_available']:
            stripe = st.selectbox("스트라이프", STRIPE_OPTIONS)
        else:
            dan_level = st.selectbox("단 수", ["1단", "2단", "3단", "4단", "5단+"])
        
        # 띠 정보 표시
        st.markdown(f"**{belt_info['emoji']} 띠 정보:**")
        st.write(f"• 경험 수준: {belt_info['experience_months']}")
        st.write(f"• 최대 난이도: {belt_info['max_difficulty']}/5")
        st.write(f"• 특징: {belt_info['description']}")
        
        gi_preference = st.selectbox("도복 선호도", ["both", "gi", "no-gi"])
        
        st.markdown("---")
        st.header("🎯 띠별 추천 집중 영역")
        for area in BELT_FOCUS_AREAS[selected_belt]:
            st.write(f"• {area}")
        
        st.markdown("---")
        st.header("📊 통계")
        
        if 'user_stats' not in st.session_state:
            st.session_state.user_stats = {
                'total_sessions': 0,
                'total_hours': 0,
                'techniques_learned': 0,
                'current_belt': selected_belt
            }
        
        # 띠 변경 감지
        if st.session_state.user_stats['current_belt'] != selected_belt:
            st.session_state.user_stats['current_belt'] = selected_belt
            st.balloons()
            st.success(f"🎉 {selected_belt} 승급을 축하합니다!")
        
        stats = st.session_state.user_stats
        st.metric("총 세션", stats['total_sessions'])
        st.metric("총 훈련 시간", f"{stats['total_hours']}시간")
        st.metric("학습한 기술", f"{stats['techniques_learned']}개")
    
    # 메인 영역
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 훈련 프로그램 생성", "📹 영상 추천", "📊 피드백", "📈 진행 상황"])
    
    with tab1:
        st.header(f"🎯 {belt_info['emoji']} {belt_name}벨트 맞춤 훈련 프로그램")
        
        # 띠별 안내 메시지
        st.info(f"**{belt_info['emoji']} {belt_name}벨트 수련생을 위한 프로그램**\n\n"
                f"경험 수준: {belt_info['experience_months']}\n"
                f"권장 난이도: {belt_info['max_difficulty']}/5\n"
                f"훈련 특징: {belt_info['description']}")
        
        # 사용자 요청 입력
        user_request = st.text_area(
            f"{belt_info['emoji']} {belt_name}벨트 전용 훈련 요청:",
            placeholder=f"예: {belt_name}벨트 수준에서 가드 기술 위주로 1시간 훈련하고 싶어요",
            height=100,
            help="띠 수준에 맞는 구체적인 요청을 입력하세요"
        )
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            generate_button = st.button(f"🚀 {belt_info['emoji']} 프로그램 생성", type="primary")
        
        if generate_button and user_request:
            with st.spinner(f"{belt_name}벨트 수준 맞춤형 훈련 프로그램을 생성하고 있습니다..."):
                # NLP 분석
                analysis = st.session_state.nlp.analyze_user_request(user_request)
                
                # 프로그램 생성
                program = st.session_state.generator.generate_program(analysis, belt_info)
                
                # 결과 저장
                st.session_state.current_program = program
                st.session_state.current_analysis = analysis
                
                # 결과 표시
                st.success(f"✅ {belt_info['emoji']} {belt_name}벨트 맞춤 프로그램 생성 완료!")
                
                # 띠별 특별 메시지
                belt_messages = {
                    "화이트": "🔰 안전하고 기본기 위주의 프로그램입니다. 천천히 정확하게 연습하세요!",
                    "블루": "🔄 기초를 다지면서 연결 기술을 배우는 단계입니다. 꾸준히 하세요!",
                    "퍼플": "🎯 자신만의 스타일을 찾아가는 시기입니다. 다양하게 시도해보세요!",
                    "브라운": "🏆 고급 기술과 교육 역할을 준비하는 단계입니다. 디테일에 집중하세요!",
                    "블랙": "🥋 마스터 레벨입니다. 창의적 응용과 후배 지도에도 신경 써주세요!"
                }
                
                st.info(belt_messages.get(belt_name, "열심히 연습하세요!"))
                
                # 프로그램 요약
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
                
                # 웜업
                st.subheader("🔥 웜업")
                for warmup in program['warm_up']:
                    st.write(f"• {warmup['name']} ({warmup['duration']}분) - {warmup['description']}")
                
                # 메인 세션
                st.subheader("💪 메인 기술 연습")
                for i, session in enumerate(program['main_session'], 1):
                    with st.expander(f"{i}. {session['technique']} ({session['duration']}분) - {session['difficulty_stars']}"):
                        st.write(f"**카테고리:** {session['category']}")
                        st.write(f"**설명:** {session['description']}")
                        st.write(f"**난이도:** {session['difficulty']}/5")
                
                # 쿨다운
                st.subheader("🧘‍♂️ 쿨다운")
                for cooldown in program['cool_down']:
                    st.write(f"• {cooldown['name']} ({cooldown['duration']}분) - {cooldown['description']}")
    
    with tab2:
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
                        
                        with col2:
                            st.write(f"**추천 이유:** {rec['why_recommended']}")
                            st.link_button("🔗 영상 보기", video['url'])
            else:
                st.warning("추천할 영상을 찾지 못했습니다.")
        else:
            st.info("먼저 '훈련 프로그램 생성' 탭에서 프로그램을 만들어주세요.")
    
    with tab3:
        st.header("📊 훈련 완료 피드백")
        
        if 'current_program' in st.session_state:
            current_belt_name = belt_name
            
            st.subheader(f"{belt_info['emoji']} {current_belt_name}벨트 훈련 완료 보고")
            
            col1, col2 = st.columns(2)
            
            with col1:
                completion_rate = st.slider("완주율 (%)", 0, 100, 80) / 100
                difficulty_rating = st.slider("체감 난이도 (1-5)", 1, 5, 3)
            
            with col2:
                enjoyment_rating = st.slider("만족도 (1-5)", 1, 5, 4)
                notes = st.text_area("추가 메모", placeholder="훈련 중 느낀 점을 적어주세요")
            
            if st.button("📝 피드백 제출"):
                feedback = st.session_state.feedback.generate_feedback(completion_rate, current_belt_name)
                
                st.success(f"✅ {belt_info['emoji']} {current_belt_name}벨트 피드백이 저장되었습니다!")
                
                # 성과 분석
                st.subheader("🎯 성과 분석")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("성과 수준", feedback['performance'])
                    st.metric("완주율", feedback['completion_rate'])
                
                with col2:
                    st.write("**격려 메시지:**")
                    st.info(feedback['encouragement'])
                
                # 띠별 맞춤 팁
                st.subheader(f"💡 {belt_info['emoji']} {current_belt_name}벨트 맞춤 팁")
                st.write(feedback['belt_specific_tip'])
                
                # 통계 업데이트
                st.session_state.user_stats['total_sessions'] += 1
                st.session_state.user_stats['total_hours'] += st.session_state.current_program['metadata']['total_duration'] / 60
                st.session_state.user_stats['techniques_learned'] += len(st.session_state.current_program['main_session'])
                
                if completion_rate >= 0.8:
                    st.balloons()
        else:
            st.info("먼저 훈련 프로그램을 생성하고 완료해주세요.")
    
    with tab4:
        st.header("📈 진행 상황 및 통계")
        
        current_user_belt = st.session_state.user_stats.get('current_belt', selected_belt)
        current_belt_info = BJJ_BELTS[current_user_belt]
        
        st.subheader(f"{current_belt_info['emoji']} {current_user_belt} 수련생 통계")
        
        if st.session_state.user_stats['total_sessions'] > 0:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("현재 띠", f"{current_belt_info['emoji']} {current_user_belt.split()[1]}")
            with col2:
                st.metric("총 훈련 세션", st.session_state.user_stats['total_sessions'])
            with col3:
                st.metric("누적 훈련 시간", f"{st.session_state.user_stats['total_hours']:.1f}시간")
            with col4:
                st.metric("학습한 기술", f"{st.session_state.user_stats['techniques_learned']}개")
            
            # 띠별 진행도
            st.subheader(f"🎯 {current_belt_info['emoji']} 띠 진행도")
            
            # 가상의 진행도 계산
            sessions = st.session_state.user_stats['total_sessions']
            hours = st.session_state.user_stats['total_hours']
            
            belt_progress_thresholds = {
                "🤍 화이트 벨트": {"sessions": 100, "hours": 150},
                "🔵 블루 벨트": {"sessions": 200, "hours": 300},
                "🟣 퍼플 벨트": {"sessions": 300, "hours": 450},
                "🟤 브라운 벨트": {"sessions": 400, "hours": 600},
                "⚫ 블랙 벨트": {"sessions": 500, "hours": 750}
            }
            
            threshold = belt_progress_thresholds[current_user_belt]
            session_progress = min(100, (sessions / threshold["sessions"]) * 100)
            hours_progress = min(100, (hours / threshold["hours"]) * 100)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("세션 진행도", f"{session_progress:.1f}%")
                st.progress(session_progress / 100)
            
            with col2:
                st.metric("시간 진행도", f"{hours_progress:.1f}%")
                st.progress(hours_progress / 100)
            
            # 다음 띠까지의 목표
            belt_order = list(BJJ_BELTS.keys())
            current_belt_index = belt_order.index(current_user_belt)
            
            if current_belt_index < len(belt_order) - 1:
                next_belt = belt_order[current_belt_index + 1]
                next_belt_info = BJJ_BELTS[next_belt]
                
                st.subheader(f"🎯 다음 목표: {next_belt_info['emoji']} {next_belt}")
                
                avg_progress = (session_progress + hours_progress) / 2
                if avg_progress >= 80:
                    st.success(f"🎉 {next_belt} 승급이 가까워지고 있습니다!")
                elif avg_progress >= 50:
                    st.info(f"💪 {next_belt} 향해 꾸준히 나아가고 있습니다!")
                else:
                    st.write(f"📚 {next_belt}을 위해 계속 노력하세요!")
            else:
                st.success("🏆 최고 단계인 블랙벨트입니다! 평생 학습을 이어가세요!")
        
        else:
            st.info("아직 훈련 기록이 없습니다. 첫 번째 훈련을 시작해보세요!")
            
            # 띠별 추천 시작 프로그램
            st.subheader(f"🚀 {belt_info['emoji']} {belt_name}벨트 추천 시작 프로그램")
            
            belt_starter_programs = {
                "화이트": [
                    "화이트벨트 기본기 30분 - 안전한 첫 시작",
                    "기본 자세와 움직임 45분 - 화이트벨트 필수",
                    "화이트벨트 에스케이프 위주 30분"
                ],
                "블루": [
                    "블루벨트 가드 플레이 60분 - 연결 기술 중심",
                    "블루벨트 패스 가드 45분 - 기초 다지기", 
                    "블루벨트 포지션 트랜지션 60분"
                ],
                "퍼플": [
                    "퍼플벨트 고급 가드 75분 - 개인 스타일 개발",
                    "퍼플벨트 연결 기술 60분 - 플로우 중심",
                    "퍼플벨트 다양한 서브미션 90분"
                ],
                "브라운": [
                    "브라운벨트 개인 스타일 완성 90분",
                    "브라운벨트 고급 연결 기술 75분",
                    "브라운벨트 카운터 기술 60분"
                ],
                "블랙": [
                    "블랙벨트 완성도 향상 90분",
                    "블랙벨트 창의적 응용 75분", 
                    "블랙벨트 교육 기술 연습 60분"
                ]
            }
            
            programs = belt_starter_programs.get(belt_name, ["기본 훈련 프로그램 60분"])
            
            for program in programs:
                if st.button(f"📋 {program}"):
                    # 자동으로 첫 번째 탭의 입력창에 내용 설정
                    st.session_state.suggested_request = program
                    st.rerun()
    
    # 하단 정보
    st.markdown("---")
    st.markdown(f"""
    ### ℹ️ {belt_info['emoji']} {belt_name}벨트 수련생 가이드
    
    **현재 띠 특징:**
    - 경험 수준: {belt_info['experience_months']}
    - 권장 최대 난이도: {belt_info['max_difficulty']}/5
    - 훈련 초점: {belt_info['description']}
    
    **추천 집중 영역:** {', '.join(BELT_FOCUS_AREAS[selected_belt])}
    
    1. **훈련 프로그램 생성**: 띠 수준에 맞는 자연어 요청을 입력하세요
    2. **영상 추천**: 생성된 프로그램에 맞는 YouTube 학습 영상을 확인하세요  
    3. **피드백**: 훈련 완료 후 솔직한 피드백을 남겨주세요
    4. **진행 상황**: 띠별 진행도를 추적하고 다음 단계를 준비하세요
    
    **💡 {belt_name}벨트 팁**: {belt_info['description']} - 이 단계에 맞는 훈련에 집중하세요!
    """)

# =============================================================================
# 메인 실행 함수
# =============================================================================

def main():
    """콘솔 버전 테스트"""
    print("🥋 주짓수 띠별 맞춤 훈련 시스템 테스트")
    print("=" * 50)
    
    # 시스템 초기화
    db = BJJTechniqueDatabase()
    nlp = AdvancedNLPProcessor()
    generator = SmartTrainingGenerator(db)
    youtube = YouTubeRecommendationSystem()
    feedback = FeedbackSystem()
    
    # 띠별 테스트 케이스
    test_requests = [
        ("🤍 화이트 벨트", "화이트벨트 초보자인데 기본 에스케이프 위주로 30분 훈련하고 싶어요"),
        ("🔵 블루 벨트", "블루벨트입니다. 가드 플레이 연결 기술 1시간 집중 훈련 부탁해요"),
        ("🟣 퍼플 벨트", "퍼플벨트 고급 가드에서 다양한 서브미션 90분 프로그램"),
        ("🟤 브라운 벨트", "브라운벨트 개인 스타일 완성을 위한 고급 연결 기술 75분"),
        ("⚫ 블랙 벨트", "블랙벨트 마스터 레벨 창의적 응용 기술 2시간 집중")
    ]
    
    for i, (belt, request) in enumerate(test_requests, 1):
        print(f"\n🥋 테스트 케이스 {i}: {belt}")
        print(f"요청: {request}")
        print("-" * 40)
        
        # 띠 정보 가져오기
        belt_info = BJJ_BELTS[belt]
        
        # 분석
        analysis = nlp.analyze_user_request(request)
        
        # 프로그램 생성
        program = generator.generate_program(analysis, belt_info)
        
        # 결과 출력
        print(f"📋 {belt_info['emoji']} {belt} 맞춤 프로그램:")
        print(f"- 총 시간: {program['metadata']['total_duration']}분")
        print(f"- 최대 난이도: {program['metadata']['max_difficulty']}/5")
        print(f"- 메인 기술 수: {len(program['main_session'])}")
        
        print(f"\n💪 주요 기술들:")
        for j, session in enumerate(program['main_session'], 1):
            print(f"  {j}. {session['technique']} ({session['duration']}분) {session['difficulty_stars']}")
        
        # 유튜브 추천
        videos = youtube.get_recommendations(program)
        if videos:
            print(f"\n📹 추천 영상:")
            for video_rec in videos[:2]:
                print(f"  - {video_rec['video']['title']}")
        
        # 샘플 피드백
        sample_feedback = feedback.generate_feedback(0.85, belt.split()[1])
        print(f"\n📊 피드백 예시:")
        print(f"- 성과: {sample_feedback['performance']}")
        print(f"- 격려: {sample_feedback['encouragement']}")
        print(f"- 팁: {sample_feedback['belt_specific_tip']}")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    # 콘솔에서 실행시 테스트
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        main()
    else:
        # Streamlit 앱 실행
        create_streamlit_app()
# 실행코드 = py -m streamlit run bjj_training_system1.py
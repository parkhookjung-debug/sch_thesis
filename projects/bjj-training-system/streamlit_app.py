# -*- coding: utf-8 -*-
"""
BJJ Training System V2 - Main Streamlit App
V2 시스템 통합 버전
"""
import streamlit as st
import sys
import os
from pathlib import Path

def main():
    """메인 애플리케이션 진입점"""
    
    # Streamlit 페이지 설정
    st.set_page_config(
        page_title="BJJ AI Training System V2",
        page_icon="🥋",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 프로젝트 루트 경로 설정
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # src 폴더도 경로에 추가
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    # V2 시스템 로드 시도
    try:
        # 첫 번째 시도: 새 구조에서 로드
        try:
            from bjj_system_v2 import create_enhanced_streamlit_app
            st.success("V2 시스템이 성공적으로 로드되었습니다!")
        except ImportError:
            # 두 번째 시도: 원본 파일에서 로드
            from bjj_advanced_system_v2 import create_enhanced_streamlit_app
            st.info("원본 V2 파일에서 로드되었습니다.")
        
        # V2 시스템 실행
        create_enhanced_streamlit_app()
        
    except ImportError as e:
        # V2 시스템을 찾을 수 없는 경우
        st.error("BJJ V2 시스템을 로드할 수 없습니다.")
        
        with st.expander("문제 해결 방법", expanded=True):
            st.markdown("""
            **다음 중 하나를 시도해보세요:**
            
            1. **파일 복사**: 
               ```
               copy bjj_advanced_system_v2.py src\\bjj_system_v2.py
               ```
            
            2. **경로 확인**: 다음 파일이 존재하는지 확인
               - `bjj_advanced_system_v2.py` (프로젝트 루트)
               - `src/bjj_system_v2.py` (새 구조)
            
            3. **의존성 설치**:
               ```
               pip install streamlit pandas numpy scikit-learn
               ```
            """)
        
        # 디버그 정보
        with st.expander("디버그 정보"):
            st.write("**현재 작업 디렉토리:**", os.getcwd())
            st.write("**Python 경로:**", sys.path[:3])
            st.write("**프로젝트 루트:**", str(project_root))
            
            # 파일 존재 여부 확인
            files_to_check = [
                "bjj_advanced_system_v2.py",
                "src/bjj_system_v2.py",
                "src/bjj_advanced_system_v2.py"
            ]
            
            st.write("**파일 존재 여부:**")
            for file_path in files_to_check:
                full_path = project_root / file_path
                exists = full_path.exists()
                st.write(f"- {file_path}: {'✅ 존재' if exists else '❌ 없음'}")
        
        # 기본 데모 인터페이스
        st.markdown("---")
        st.subheader("임시 데모 인터페이스")
        
        user_input = st.text_area(
            "훈련 요청을 입력하세요:", 
            placeholder="예: 하프가드에서 자꾸 당하는데 도움이 필요해요",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("분석하기", type="primary"):
                if user_input:
                    st.success("V2 시스템이 설치되면 다음 기능을 제공합니다:")
                    st.markdown("""
                    - 🧠 고도화된 NLP 분석
                    - 🎯 의도별 맞춤 프로그램
                    - 💡 개인화 학습
                    - 📊 실시간 피드백
                    """)
                else:
                    st.warning("내용을 입력해주세요.")
        
        with col2:
            if st.button("시스템 상태 확인"):
                st.info("V2 시스템 로드를 다시 시도합니다...")
                st.rerun()

if __name__ == "__main__":
    main()
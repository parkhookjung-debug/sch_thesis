# BJJ Training System V2 - AI 기반 맞춤형 주짓수 훈련 시스템

**고도화된 NLP 분석으로 개인화된 주짓수 훈련을 제공합니다**

## 주요 기능

- **지능형 자연어 처리**: 한국어 훈련 요청을 정확히 이해
- **의도별 맞춤 프로그램**: 학습, 약점 보완, 경기 준비 등
- **개인화 학습**: 사용자별 패턴 기억 및 적응  
- **실시간 피드백**: AI 분석 정확도 지속 개선
- **YouTube 영상 추천**: 기술별 맞춤 학습 자료

## 사용법

간단한 자연어로 훈련 목표를 입력하세요:

```
"하프가드에서 자꾸 당하는데, 방어하는 방법부터 차근차근 배우고 싶어요"
"경기 준비 중인데 공격적인 가드 패스 기술들을 집중적으로 연습하고 싶습니다"
"트라이앵글 말고 다른 서브미션들을 배워보고 싶어요"
```

AI가 자동으로 분석하여 맞춤형 훈련 프로그램을 생성합니다.

## 기술 스택

- **Frontend**: Streamlit
- **Backend**: Python
- **AI/NLP**: scikit-learn, 커스텀 패턴 분석
- **Database**: SQLite
- **Deployment**: Streamlit Cloud

## 로컬 실행

```bash
git clone https://github.com/parkhookjung-debug/bjj-training-system.git
cd bjj-training-system
pip install -r requirements.txt
streamlit run src/web/app.py
```

## 라이선스

MIT License

---

**"AI가 당신의 주짓수 여정을 더 스마트하게 만들어드립니다"**
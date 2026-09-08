# bjj_nlp_evaluator.py
"""
BJJ V2 NLP 시스템 성능 평가 전용 모듈
사용법: python bjj_nlp_evaluator.py
"""

import sys
import time
import statistics
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pandas as pd

# 메인 시스템에서 필요한 클래스들을 import
try:
    from bjj_advanced_system_v2 import (
        EnhancedNLPProcessor,
        ImprovedBJJDatabase,
        BJJ_BELTS
    )
except ImportError:
    print("오류: bjj_advanced_system_v2.py 파일을 찾을 수 없습니다.")
    print("이 파일이 같은 디렉토리에 있는지 확인해주세요.")
    sys.exit(1)

class BJJNLPEvaluator:
    """BJJ NLP 시스템 성능 평가 클래스"""
    
    def __init__(self):
        """평가기 초기화"""
        self.nlp = EnhancedNLPProcessor()
        self.test_cases = self._load_test_cases()
        self.results = []
        
    def _load_test_cases(self) -> List[Dict]:
        """테스트 케이스 정의"""
        return [
            {
                "id": "weakness_beginner",
                "text": "하프가드에서 자꾸 당하는데, 너무 어려워서 못하겠어요",
                "expected": {
                    "intent": "improve_weakness",
                    "difficulty_preference": "easy",
                    "level": "beginner",
                    "positions": ["guard"],
                    "emotional_state": ["frustration"],
                    "specific_techniques": ["하프가드"]
                },
                "priority": "high"
            },
            {
                "id": "negation_learning",
                "text": "트라이앵글은 말고 다른 서브미션들을 차근차근 배우고 싶어요",
                "expected": {
                    "intent": "learn",
                    "difficulty_preference": "normal",
                    "negation_analysis": {"has_negation": True},
                    "positions": ["submission"]
                },
                "priority": "high"
            },
            {
                "id": "competition_prep",
                "text": "경기 준비 중인데 공격적인 가드 패스를 집중적으로 연습하고 싶습니다",
                "expected": {
                    "intent": "compete",
                    "difficulty_preference": "challenging",
                    "positions": ["guard_pass"],
                    "intensity_analysis": {"level": "high"}
                },
                "priority": "high"
            },
            {
                "id": "safety_concern",
                "text": "무릎 부상이 있어서 안전한 기술 위주로 30분만 가볍게 하고 싶어요",
                "expected": {
                    "intent": "practice",
                    "duration": "short",
                    "safety_priority": "high",
                    "concerns_or_limitations": "무릎"
                },
                "priority": "high"
            },
            {
                "id": "mastery_focused",
                "text": "딥하프가드에서 완전히 마스터하고 싶습니다",
                "expected": {
                    "intent": "strengthen",
                    "specific_techniques": ["딥하프가드"],
                    "intensity_analysis": {"level": "very_high"}
                },
                "priority": "medium"
            },
            {
                "id": "synonym_test",
                "text": "하프가드에서 아무바를 배우고 싶어요",
                "expected": {
                    "intent": "learn",
                    "specific_techniques": ["하프가드", "아무바"],
                    "synonym_matches": {"하프가드": True, "아무바": True}
                },
                "priority": "medium"
            },
            {
                "id": "complex_negation",
                "text": "스파이더 가드 빼고 다른 오픈 가드들을 배워보고 싶어요",
                "expected": {
                    "intent": "learn",
                    "negation_analysis": {"has_negation": True},
                    "positions": ["guard"]
                },
                "priority": "medium"
            },
            {
                "id": "emotional_intensity",
                "text": "정말 너무너무 답답해서 완전히 새로운 기술을 살짝 배워보고 싶어요",
                "expected": {
                    "intent": "learn",
                    "emotional_state": ["frustration"],
                    "intensity_analysis": {"level": "very_high"}
                },
                "priority": "low"
            }
        ]
    
    def evaluate_single_case(self, test_case: Dict) -> Dict:
        """단일 테스트 케이스 평가"""
        text = test_case["text"]
        expected = test_case["expected"]
        test_id = test_case["id"]
        
        print(f"테스트 중: {test_id}")
        print(f"입력: {text}")
        
        # 성능 측정
        start_time = time.time()
        result = self.nlp.analyze_user_request(text, f"eval_user_{test_id}")
        analysis_time = time.time() - start_time
        
        # 평가 결과 계산
        scores = self._calculate_scores(result, expected)
        
        # 결과 구성
        evaluation = {
            "test_id": test_id,
            "text": text,
            "analysis_time": analysis_time,
            "confidence": result.get('confidence_score', 0),
            "scores": scores,
            "result": result,
            "expected": expected,
            "priority": test_case.get("priority", "medium")
        }
        
        # 결과 출력
        self._print_case_result(evaluation)
        
        return evaluation
    
    def _calculate_scores(self, result: Dict, expected: Dict) -> Dict:
        """개별 항목별 점수 계산"""
        scores = {}
        
        # 의도 분석
        scores['intent'] = 1.0 if result.get('intent') == expected.get('intent') else 0.0
        
        # 난이도 선호도
        scores['difficulty'] = 1.0 if result.get('difficulty_preference') == expected.get('difficulty_preference') else 0.0
        
        # 레벨 분석
        scores['level'] = 1.0 if result.get('level') == expected.get('level') else 0.0
        
        # 포지션 매칭 (부분 점수 허용)
        result_positions = set(result.get('positions', []))
        expected_positions = set(expected.get('positions', []))
        if not expected_positions:
            scores['positions'] = 1.0  # 기대값이 없으면 정확한 것으로 간주
        elif result_positions & expected_positions:
            scores['positions'] = len(result_positions & expected_positions) / len(expected_positions)
        else:
            scores['positions'] = 0.0
        
        # 특정 기술 추출
        result_techniques = set(result.get('specific_techniques', []))
        expected_techniques = set(expected.get('specific_techniques', []))
        if not expected_techniques:
            scores['techniques'] = 1.0
        elif result_techniques & expected_techniques:
            scores['techniques'] = len(result_techniques & expected_techniques) / len(expected_techniques)
        else:
            scores['techniques'] = 0.0
        
        # V2 고급 기능들
        # 부정문 처리
        if 'negation_analysis' in expected:
            result_negation = result.get('negation_analysis', {}).get('has_negation', False)
            expected_negation = expected['negation_analysis'].get('has_negation', False)
            scores['negation'] = 1.0 if result_negation == expected_negation else 0.0
        else:
            scores['negation'] = 1.0  # 부정문이 기대되지 않는 경우
        
        # 강도 분석
        if 'intensity_analysis' in expected:
            result_intensity = result.get('intensity_analysis', {}).get('level', 'medium')
            expected_intensity = expected['intensity_analysis'].get('level', 'medium')
            scores['intensity'] = 1.0 if result_intensity == expected_intensity else 0.0
        else:
            scores['intensity'] = 1.0
        
        # 감정 상태 (부분 점수)
        if 'emotional_state' in expected:
            result_emotions = set(result.get('emotional_state', []))
            expected_emotions = set(expected['emotional_state'])
            if result_emotions & expected_emotions:
                scores['emotions'] = len(result_emotions & expected_emotions) / len(expected_emotions)
            else:
                scores['emotions'] = 0.0
        else:
            scores['emotions'] = 1.0
        
        # 안전 고려사항
        if 'safety_priority' in expected:
            scores['safety'] = 1.0 if result.get('safety_priority') == expected['safety_priority'] else 0.0
        else:
            scores['safety'] = 1.0
        
        # 지속시간
        if 'duration' in expected:
            scores['duration'] = 1.0 if result.get('duration') == expected['duration'] else 0.0
        else:
            scores['duration'] = 1.0
        
        return scores
    
    def _print_case_result(self, evaluation: Dict):
        """개별 테스트 결과 출력"""
        scores = evaluation['scores']
        test_id = evaluation['test_id']
        
        print(f"   분석 시간: {evaluation['analysis_time']:.3f}초")
        print(f"   신뢰도: {evaluation['confidence']:.1%}")
        
        # 점수별 표시
        for metric, score in scores.items():
            status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
            print(f"   {status} {metric}: {score:.1%}")
        
        overall = sum(scores.values()) / len(scores)
        print(f"   📊 종합 점수: {overall:.1%}")
        print()
    
    def run_full_evaluation(self) -> Dict:
        """전체 평가 실행"""
        print("🤖 BJJ V2 NLP 시스템 종합 성능 평가")
        print("=" * 60)
        
        # 개별 테스트 실행
        for test_case in self.test_cases:
            evaluation = self.evaluate_single_case(test_case)
            self.results.append(evaluation)
        
        # 종합 결과 계산
        return self._generate_summary_report()
    
    def _generate_summary_report(self) -> Dict:
        """종합 보고서 생성"""
        print("📊 종합 성능 평가 결과")
        print("=" * 60)
        
        # 메트릭별 평균 계산
        all_scores = {}
        for result in self.results:
            for metric, score in result['scores'].items():
                if metric not in all_scores:
                    all_scores[metric] = []
                all_scores[metric].append(score)
        
        metric_averages = {metric: statistics.mean(scores) for metric, scores in all_scores.items()}
        
        # 정확도 메트릭 출력
        print("🎯 정확도 메트릭:")
        for metric, avg_score in metric_averages.items():
            status = "✅" if avg_score >= 0.8 else "⚠️" if avg_score >= 0.6 else "❌"
            print(f"   {status} {metric.capitalize()}: {avg_score:.1%}")
        
        # 성능 메트릭
        analysis_times = [r['analysis_time'] for r in self.results]
        confidences = [r['confidence'] for r in self.results]
        
        print(f"\n⚡ 성능 메트릭:")
        print(f"   • 평균 분석 시간: {statistics.mean(analysis_times):.3f}초")
        print(f"   • 최대 분석 시간: {max(analysis_times):.3f}초")
        print(f"   • 최소 분석 시간: {min(analysis_times):.3f}초")
        print(f"   • 평균 신뢰도: {statistics.mean(confidences):.1%}")
        
        # 우선순위별 성능
        priority_scores = {}
        for result in self.results:
            priority = result['priority']
            if priority not in priority_scores:
                priority_scores[priority] = []
            
            overall_score = sum(result['scores'].values()) / len(result['scores'])
            priority_scores[priority].append(overall_score)
        
        print(f"\n🎯 우선순위별 성능:")
        for priority, scores in priority_scores.items():
            avg_score = statistics.mean(scores)
            print(f"   • {priority.capitalize()} priority: {avg_score:.1%} ({len(scores)}개 테스트)")
        
        # 전체 종합 점수
        overall_accuracy = statistics.mean([
            sum(result['scores'].values()) / len(result['scores']) 
            for result in self.results
        ])
        
        print(f"\n🏆 V2 종합 성능 점수: {overall_accuracy:.1%}")
        
        # 성능 등급 판정
        if overall_accuracy >= 0.9:
            grade = "A+"
            comment = "탁월한 성능! 상용 수준의 정확도입니다."
        elif overall_accuracy >= 0.8:
            grade = "A"
            comment = "우수한 성능! 실용적인 수준입니다."
        elif overall_accuracy >= 0.7:
            grade = "B"
            comment = "양호한 성능! 일부 개선이 필요합니다."
        elif overall_accuracy >= 0.6:
            grade = "C"
            comment = "보통 성능. 알고리즘 튜닝을 권장합니다."
        else:
            grade = "D"
            comment = "성능 개선이 시급합니다."
        
        print(f"📈 성능 등급: {grade}")
        print(f"💬 {comment}")
        
        # 상세 분석
        self._detailed_analysis()
        
        return {
            'overall_accuracy': overall_accuracy,
            'metric_averages': metric_averages,
            'performance_stats': {
                'avg_analysis_time': statistics.mean(analysis_times),
                'avg_confidence': statistics.mean(confidences)
            },
            'priority_performance': priority_scores,
            'grade': grade,
            'detailed_results': self.results
        }
    
    def _detailed_analysis(self):
        """상세 분석 및 개선 제안"""
        print(f"\n🔍 상세 분석 및 개선 제안:")
        
        # 가장 낮은 점수의 메트릭 찾기
        all_scores = {}
        for result in self.results:
            for metric, score in result['scores'].items():
                if metric not in all_scores:
                    all_scores[metric] = []
                all_scores[metric].append(score)
        
        metric_averages = {metric: statistics.mean(scores) for metric, scores in all_scores.items()}
        worst_metric = min(metric_averages.keys(), key=lambda k: metric_averages[k])
        
        print(f"   ⚠️ 개선 필요 영역: {worst_metric} ({metric_averages[worst_metric]:.1%})")
        
        # 실패 케이스 분석
        failed_cases = [r for r in self.results if sum(r['scores'].values()) / len(r['scores']) < 0.7]
        if failed_cases:
            print(f"   ❌ 저성능 케이스 ({len(failed_cases)}개):")
            for case in failed_cases:
                print(f"      • {case['test_id']}: {sum(case['scores'].values()) / len(case['scores']):.1%}")
    
    def save_results(self, filename: str = None):
        """결과를 JSON 파일로 저장"""
        if filename is None:
            filename = f"nlp_evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"📁 결과가 {filename}에 저장되었습니다.")
        return filename
    
    def generate_csv_report(self, filename: str = None):
        """CSV 형태의 요약 보고서 생성"""
        if filename is None:
            filename = f"nlp_evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 데이터 준비
        data = []
        for result in self.results:
            row = {
                'test_id': result['test_id'],
                'text': result['text'],
                'analysis_time': result['analysis_time'],
                'confidence': result['confidence'],
                'priority': result['priority'],
                'overall_score': sum(result['scores'].values()) / len(result['scores'])
            }
            row.update(result['scores'])
            data.append(row)
        
        # CSV 저장
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"📊 CSV 보고서가 {filename}에 저장되었습니다.")
        return filename

def main():
    """메인 실행 함수"""
    print("🥋 BJJ V2 NLP 성능 평가기 시작")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 평가기 초기화 및 실행
        evaluator = BJJNLPEvaluator()
        summary = evaluator.run_full_evaluation()
        
        # 결과 저장
        json_file = evaluator.save_results()
        csv_file = evaluator.generate_csv_report()
        
        print(f"\n✅ 평가 완료!")
        print(f"📋 JSON 상세 결과: {json_file}")
        print(f"📊 CSV 요약 보고서: {csv_file}")
        
        return summary
        
    except Exception as e:
        print(f"❌ 평가 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()

    
    
# 실행코드 py bjj_nlp_evaluator.py
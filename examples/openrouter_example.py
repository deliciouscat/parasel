"""OpenRouter API를 사용한 실제 LLM 파이프라인 예제"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parasel import Run
from parasel.registry import TaskRegistry
from tasks.search import search_pipeline


def main():
    """OpenRouter API를 사용한 검색 파이프라인 실행"""
    
    print("=" * 70)
    print("Parasel + OpenRouter 검색 파이프라인 예제")
    print("=" * 70)
    print()
    print("이 예제는 실제 OpenRouter API를 호출합니다.")
    print(".env 파일에 OPENROUTER_API_KEY가 설정되어 있어야 합니다.")
    print()
    
    # 레지스트리에 태스크 등록
    registry = TaskRegistry()
    registry.register(
        task_id="search",
        version="0.1.0",
        node=search_pipeline,
        description="키워드 추출 → 병렬 요약 → 병합 → 검색 파이프라인",
        requires=["query", "page"],
        produces=["keywords", "summary", "search-result"],
        tags=["search", "llm", "openrouter"],
    )
    
    # 입력 데이터
    user_input = {
        "task": "search",
        "requester_type": "user",
        "id": "USER_001",
        "query": "이 페이지에서 '절차적 생성'이 의미하는 바는?",
        "page": """
절차적 생성(Procedural Generation)은 컴퓨터 알고리즘을 통해 자동으로 콘텐츠를 생성하는 기법입니다.
게임 개발에서 특히 많이 사용되며, 맵, 던전, 아이템, 캐릭터 등을 무작위 또는 규칙 기반으로 생성합니다.

주요 장점:
1. 개발 비용 절감: 수작업으로 만들어야 할 콘텐츠를 자동 생성
2. 무한한 재생 가능성: 매번 다른 경험 제공
3. 파일 크기 감소: 알고리즘만 저장하면 되므로 용량 절약

대표적인 사용 예시:
- 마인크래프트: 무한한 세계 생성
- No Man's Sky: 1800경 개의 행성 생성
- 로그라이크 게임: 매번 다른 던전 레이아웃

기술적으로는 펄린 노이즈(Perlin Noise), 보로노이 다이어그램(Voronoi Diagram), 
L-시스템(L-System) 등의 알고리즘이 활용됩니다.
        """.strip(),
    }
    
    print("[입력 데이터]")
    print(f"Query: {user_input['query']}")
    print(f"Page: {user_input['page'][:100]}...")
    print()
    print("-" * 70)
    print("파이프라인 실행 중...")
    print("-" * 70)
    print()
    
    # Run 함수로 실행
    try:
        result = Run(
            user_input=user_input,
            task="search",
            version="0.1.0",
            registry=registry,
        )
        
        print()
        print("=" * 70)
        print("[실행 결과]")
        print("=" * 70)
        print(f"✓ Success: {result['success']}")
        print(f"✓ Duration: {result['duration']:.2f}초")
        print(f"✓ Task: {result['task_id']} v{result['version']}")
        print()
        
        if result['success']:
            data = result['data']
            
            print("[1. 추출된 키워드]")
            keywords = data.get('keywords', [])
            print(f"   {', '.join(keywords)}")
            print()
            
            print("[2. Gemini 요약]")
            gem_summary = data.get('gemini-summary', '')
            print(f"   {gem_summary}")
            print()
            
            print("[3. Claude 요약]")
            hai_summary = data.get('haiku-summary', '')
            print(f"   {hai_summary}")
            print()
            
            print("[4. 병합된 최종 요약]")
            final_summary = data.get('summary', '')
            print(f"   {final_summary}")
            print()
            
            print("[5. 검색 결과]")
            search_results = data.get('search-result', [])
            print(f"   총 {len(search_results)}건")
            for i, res in enumerate(search_results, 1):
                print(f"   {i}. {res.get('title')}")
                print(f"      {res.get('url')}")
        else:
            print()
            print("[에러 발생]")
            for error in result['errors']:
                print(f"  ✗ {error}")
    
    except Exception as e:
        print()
        print("=" * 70)
        print(f"[실행 실패]: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        print()
        print("문제 해결 방법:")
        print("1. .env 파일에 OPENROUTER_API_KEY가 설정되어 있는지 확인")
        print("2. API 키가 유효한지 확인")
        print("3. 인터넷 연결 상태 확인")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()


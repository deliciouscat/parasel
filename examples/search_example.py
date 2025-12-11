"""검색 파이프라인 실행 예제"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parasel import Run
from parasel.registry import TaskRegistry
from tasks.search import search_pipeline


def main():
    """검색 파이프라인 실행 예제"""
    
    print("=" * 60)
    print("Parasel 검색 파이프라인 예제")
    print("=" * 60)
    
    # 레지스트리에 태스크 등록
    registry = TaskRegistry()
    registry.register(
        task_id="search",
        version="0.1.0",
        node=search_pipeline,
        description="키워드 추출 → 병렬 요약 → 병합 → 검색 파이프라인",
        requires=["query", "page"],
        produces=["keywords", "summary", "search-result"],
        tags=["search", "llm", "example"],
    )
    
    # 입력 데이터
    user_input = {
        "task": "search",
        "requester_type": "user",
        "id": "USER_001",
        "query": "이 페이지에서 '절차적 생성'이 의미하는 바는?",
        "page": (
            "절차적 생성(procedural generation)은 알고리즘을 통해 콘텐츠를 자동으로 생성하는 기법입니다. "
            "게임 개발에서 맵, 던전, 아이템 등을 무작위로 생성하는데 많이 사용됩니다. "
            "이를 통해 개발자는 적은 노력으로 방대한 콘텐츠를 만들 수 있고, "
            "플레이어는 매번 새로운 경험을 할 수 있습니다."
        ),
    }
    
    print("\n[입력 데이터]")
    print(f"Query: {user_input['query']}")
    print(f"Page: {user_input['page'][:80]}...")
    print()
    
    # Run 함수로 실행
    try:
        result = Run(
            user_input=user_input,
            task="search",
            version="0.1.0",
            registry=registry,
        )
        
        print("\n[실행 결과]")
        print(f"Success: {result['success']}")
        print(f"Duration: {result['duration']:.3f}초")
        print(f"Task: {result['task_id']} v{result['version']}")
        print()
        
        if result['success']:
            data = result['data']
            print("[출력 데이터]")
            print(f"Keywords: {data.get('keywords', [])}")
            print(f"Summary: {data.get('summary', '')[:100]}...")
            print(f"Search Results: {len(data.get('search-result', []))} 건")
            
            for i, res in enumerate(data.get('search-result', []), 1):
                print(f"  {i}. {res.get('title')} - {res.get('url')}")
        else:
            print("[에러]")
            for error in result['errors']:
                print(f"  - {error}")
    
    except Exception as e:
        print(f"\n[실행 실패]: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()


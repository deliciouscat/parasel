"""ByArgs와 ByKeys 사용 예제"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parasel import Serial, Parallel, ModuleAdapter, ByArgs, ByKeys, Executor, Context


def query_expansion_by_language(context: Context, language: str, out_name: str = None, **kwargs):
    """
    언어별 쿼리 확장 시뮬레이션
    
    실제 구현에서는 LLM을 사용하여 쿼리를 확장할 수 있습니다.
    """
    base_query = context.get("query", "파이썬")
    
    print(f"[Query Expansion] language={language}, base_query={base_query}")
    
    if language == "en":
        expanded = [
            "python programming",
            "python tutorial",
            "learn python",
            "python examples"
        ]
    elif language == "ko":
        expanded = [
            "파이썬 프로그래밍",
            "파이썬 튜토리얼",
            "파이썬 배우기",
            "파이썬 예제",
            "파이썬 강좌"
        ]
    else:
        expanded = [base_query]
    
    print(f"  → Expanded to {len(expanded)} queries")
    return expanded


def duckduckgo_search(context: Context, input: str, out_name: str = None, **kwargs):
    """
    DuckDuckGo 검색 시뮬레이션
    
    실제 구현에서는 API를 호출합니다.
    """
    print(f"[Search] query='{input}'")
    
    # 시뮬레이션: 각 쿼리마다 3개 결과 반환
    results = {
        "query": input,
        "items": [
            {"title": f"Result 1 for {input}", "score": 0.9},
            {"title": f"Result 2 for {input}", "score": 0.7},
            {"title": f"Result 3 for {input}", "score": 0.5},
        ]
    }
    
    print(f"  → Found {len(results['items'])} results")
    return results


def exponential_weighted_gaussian(context: Context, out_name: str = None, **kwargs):
    """
    검색 결과 정렬 시뮬레이션
    
    실제 구현에서는 복잡한 랭킹 알고리즘을 사용합니다.
    """
    search_results = context.get("search_results", [])
    
    print(f"\n[Sorting] Processing {len(search_results)} search results...")
    
    # 모든 아이템 수집
    all_items = []
    for result in search_results:
        if isinstance(result, dict) and "items" in result:
            for item in result["items"]:
                all_items.append({
                    "query": result["query"],
                    "title": item["title"],
                    "score": item["score"]
                })
    
    # 점수로 정렬
    sorted_items = sorted(all_items, key=lambda x: x["score"], reverse=True)
    
    print(f"  → Sorted {len(sorted_items)} items")
    print(f"  → Top result: {sorted_items[0]['title'] if sorted_items else 'N/A'}")
    
    return sorted_items


def main():
    """ByArgs와 ByKeys를 사용한 웹 추천 파이프라인"""
    
    print("=" * 80)
    print("ByArgs와 ByKeys 예제: 다국어 웹 검색 파이프라인")
    print("=" * 80)
    print()
    
    # 노드 정의
    query_expansion = ModuleAdapter(
        query_expansion_by_language,
        out_name="expanded_queries",
    )
    
    search = ModuleAdapter(
        duckduckgo_search,
        out_name="search_results",
    )
    
    sorting = ModuleAdapter(
        exponential_weighted_gaussian,
        out_name="sorted_results",
    )
    
    # 파이프라인 구성
    web_recommend = Serial([
        # Step 1: 언어별 쿼리 확장 (병렬)
        Parallel([
            ByArgs(query_expansion, args={"language": ["en", "ko"]})
        ], name="QueryExpansion"),
        
        # Step 2: 각 확장된 쿼리로 검색 (병렬)
        Parallel([
            ByKeys(search, keys=["expanded_queries"], input_key_name="input"),
        ], name="ParallelSearch"),
        
        # Step 3: 결과 정렬
        sorting,
    ], name="WebRecommendPipeline")
    
    # 실행
    print("Starting pipeline...")
    print()
    
    executor = Executor()
    result = executor.run(
        web_recommend,
        initial_data={"query": "machine learning"}
    )
    
    # 결과 출력
    print()
    print("=" * 80)
    print("실행 결과")
    print("=" * 80)
    print(f"Success: {result.success}")
    print(f"Duration: {result.duration:.3f}초")
    print()
    
    # 쿼리 확장 결과
    expanded = result.context.get("expanded_queries", [])
    print(f"확장된 쿼리: {len(expanded)}개 언어")
    for i, queries in enumerate(expanded):
        print(f"  Language {i+1}: {len(queries)}개 쿼리")
        for q in queries[:2]:  # 처음 2개만 출력
            print(f"    - {q}")
        if len(queries) > 2:
            print(f"    ... and {len(queries)-2} more")
    print()
    
    # 검색 결과
    search_results = result.context.get("search_results", [])
    total_queries = len(expanded[0]) + len(expanded[1]) if len(expanded) == 2 else 0
    print(f"검색 실행: {len(search_results)}개 쿼리 (총 {total_queries}개)")
    print()
    
    # 정렬된 최종 결과
    sorted_results = result.context.get("sorted_results", [])
    print(f"최종 결과: {len(sorted_results)}개 아이템")
    print("\nTop 5 결과:")
    for i, item in enumerate(sorted_results[:5], 1):
        print(f"  {i}. [{item['score']:.2f}] {item['title']}")
        print(f"     (query: {item['query']})")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()


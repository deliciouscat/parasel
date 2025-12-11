"""FastAPI 서버 실행 예제"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from parasel import create_app
from parasel.registry import TaskRegistry
from tasks.search import search_pipeline


def create_demo_app():
    """데모 FastAPI 앱 생성"""
    
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
        mark_stable=True,
    )
    
    # FastAPI 앱 생성
    app = create_app(
        registry=registry,
        title="Parasel Demo API",
        description="검색 파이프라인 데모 API",
    )
    
    return app


# 앱 인스턴스 생성 (uvicorn이 이것을 import)
app = create_demo_app()


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Parasel FastAPI 서버 시작")
    print("=" * 60)
    print("\n사용 가능한 엔드포인트:")
    print("  - GET  /           : API 정보")
    print("  - GET  /tasks      : 등록된 태스크 목록")
    print("  - GET  /tasks/{id} : 특정 태스크 정보")
    print("  - POST /run/{id}   : 태스크 실행")
    print("  - GET  /health     : 헬스 체크")
    print("\n서버 주소: http://127.0.0.1:8000")
    print("API 문서: http://127.0.0.1:8000/docs")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="127.0.0.1", port=8000)


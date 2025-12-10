# Parasel 사용 가이드

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 또는 개발 모드로 설치
pip install -e .
```

## 환경 설정

OpenRouter API를 사용하려면 `.env` 파일을 생성하고 API 키를 설정하세요:

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
# OPENROUTER_API_KEY=your_api_key_here
```

API 키는 [OpenRouter](https://openrouter.ai/)에서 발급받을 수 있습니다.

## 빠른 시작

### 1. 간단한 예제 실행

```bash
python examples/simple_example.py
```

이 예제는 병렬/직렬 파이프라인의 기본 동작을 보여줍니다.

### 2. 검색 파이프라인 예제 (더미 데이터)

```bash
python examples/search_example.py
```

더미 데이터로 검색 파이프라인을 실행합니다.

### 3. OpenRouter API 사용 예제 (실제 LLM)

```bash
python examples/openrouter_example.py
```

실제 OpenRouter API를 호출하여 LLM으로 키워드 추출과 요약을 수행합니다.
`.env` 파일에 `OPENROUTER_API_KEY`가 설정되어 있어야 합니다.

### 3. FastAPI 서버 실행

```bash
python examples/api_example.py
```

또는

```bash
uvicorn examples.api_example:app --reload
```

서버가 실행되면 다음 URL에서 API 문서를 확인할 수 있습니다:
- http://127.0.0.1:8000/docs (Swagger UI)
- http://127.0.0.1:8000/redoc (ReDoc)

### 4. API 사용 예시 (curl)

```bash
# 태스크 목록 조회
curl http://127.0.0.1:8000/tasks

# 특정 태스크 정보 조회
curl http://127.0.0.1:8000/tasks/search

# 태스크 실행
curl -X POST http://127.0.0.1:8000/run/search \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "query": "절차적 생성이란?",
      "page": "절차적 생성은 알고리즘으로 콘텐츠를 자동 생성하는 기법입니다."
    },
    "version": "latest"
  }'
```

## 테스트 실행

```bash
# 단위 테스트만 실행 (통합 테스트 제외)
pytest -m "not integration"

# 모든 테스트 실행 (통합 테스트 포함, API 키 필요)
pytest

# 특정 테스트 파일 실행
pytest tests/test_core.py

# OpenRouter 통합 테스트 실행 (API 키 필요)
pytest tests/test_openrouter.py -m integration -v

# 커버리지 포함
pytest --cov=parasel -m "not integration"
```

**참고**: 통합 테스트(`-m integration`)는 실제 OpenRouter API를 호출하므로 `.env` 파일에 `OPENROUTER_API_KEY`가 필요합니다.

## 프로젝트 구조

```
parasel/
├── parasel/           # 프레임워크 코어 (배포 패키지)
│   ├── core/         # Node, Context, Executor 등
│   ├── registry/     # TaskRegistry, 스키마 검증
│   └── api/          # FastAPI 통합
├── modules/          # 사용자 정의 모듈 예제
│   ├── llm/         # LLM 관련 모듈
│   └── search/      # 검색 관련 모듈
├── tasks/            # 사용자 정의 태스크 파이프라인
│   └── search.py    # 검색 태스크 예제
├── examples/         # 실행 가능한 예제들
├── tests/            # 테스트 코드
└── docs/             # 설계 문서
```

## 다음 단계

1. `modules/`에 자신의 도메인 모듈 구현
2. `tasks/`에 파이프라인 정의
3. 레지스트리에 등록하고 Run 함수로 실행
4. 필요시 FastAPI로 배포

자세한 내용은 `docs/architecture.md`와 예제 코드를 참고하세요.


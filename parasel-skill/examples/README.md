# Example Scripts

이 디렉토리의 모든 파일은 **학습용 예제**입니다.

실제 프로젝트에서는 이 파일들을 직접 복사하지 않고, 패턴과 구조를 참고하여 자신의 코드를 작성하세요.

## 예제 목록

### simple_pipeline.py
**Demonstrates**: Serial and Parallel node composition  
**Use when**: Learning pipeline basics, understanding execution order  
**Patterns**: Sequential execution, parallel branching, result combination  
**Key concepts**: Context data flow, ModuleAdapter wrapping

```bash
python examples/simple_pipeline.py
```

---

### multi_language.py
**Demonstrates**: ByArgs for dynamic parallel execution  
**Use when**: Need to run same function with different arguments in parallel  
**Patterns**: Cartesian product execution, result accumulation  
**Key concepts**: ByArgs iterator, parallel parameter expansion  
**Common use cases**: Multi-language processing, multi-model inference, A/B testing

```bash
python examples/multi_language.py
```

---

### web_recommend.py
**Demonstrates**: Complete multi-stage pipeline with ByArgs and ByKeys  
**Use when**: Building search, recommendation, or RAG systems  
**Patterns**: Query expansion → parallel search → aggregation  
**Pipeline stages**:
1. Query expansion (multi-language via ByArgs)
2. Dynamic search (per expanded query via ByKeys)
3. Result deduplication and scoring  

**Key concepts**: Nested parallel execution, list flattening, dynamic fanout  
**Common use cases**: Search engines, recommendation systems, multi-source aggregation

```bash
python examples/web_recommend.py
```

---

### fastapi_deploy.py
**Demonstrates**: FastAPI deployment with TaskRegistry  
**Use when**: Deploying pipelines as REST API services  
**Patterns**: Task registration, version management, API exposure  
**Key concepts**: TaskRegistry, expose(), API endpoints  
**Common use cases**: Production deployment, microservices, API integration

```bash
python examples/fastapi_deploy.py
# Visit http://localhost:8000/docs for API documentation
```

## Quick Reference

**For basic pipeline structure** → `simple_pipeline.py`  
**For parallel parameter execution** → `multi_language.py`  
**For dynamic list processing** → `web_recommend.py` (see ByKeys usage)  
**For production deployment** → `fastapi_deploy.py`  

**For multi-LLM ensemble** → See `web_recommend.py` pattern, replace with LLM calls  
**For RAG pipeline** → Use `web_recommend.py` as template (expand → retrieve → rank → generate)

## 실제 프로젝트 예제

더 복잡한 실전 예제는 다음 프로젝트를 참고하세요:
```
/Users/deliciouscat/projects/WizPerch-ai-pipeline/
```

## 주의사항

⚠️ 이 예제들은 **교육 목적**입니다:
- Mock 함수를 사용 (실제 API 호출 없음)
- 에러 핸들링 간소화
- 프로덕션 수준의 로깅/모니터링 생략

실제 프로젝트에서는:
- ✅ 실제 API 키와 엔드포인트 사용
- ✅ 적절한 에러 핸들링 추가
- ✅ 로깅과 모니터링 구현
- ✅ 환경 변수로 설정 관리
- ✅ 테스트 코드 작성

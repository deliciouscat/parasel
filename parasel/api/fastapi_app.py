"""FastAPI 통합: 태스크를 HTTP 엔드포인트로 노출"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import time

from parasel.core.context import Context
from parasel.core.executor import Executor, ExecutionPolicy
from parasel.registry.task_registry import (
    TaskRegistry,
    TaskNotFoundError,
    get_global_registry,
)
from parasel.registry.schemas import validate_schema, SchemaValidationError


class RunRequest(BaseModel):
    """실행 요청"""
    data: Dict[str, Any] = Field(..., description="입력 데이터")
    task: Optional[str] = Field(None, description="태스크 ID (data.task를 오버라이드)")
    version: str = Field("latest", description="버전 (latest, stable, 또는 semver)")


class RunResponse(BaseModel):
    """실행 응답"""
    success: bool
    duration: float
    data: Dict[str, Any]
    errors: list[str] = []
    task_id: str
    version: str
    metadata: Dict[str, Any] = {}


def Run(
    user_input: Dict[str, Any],
    task: Optional[str] = None,
    version: str = "latest",
    registry: Optional[TaskRegistry] = None,
    policy: Optional[ExecutionPolicy] = None,
) -> Dict[str, Any]:
    """
    태스크를 실행하는 편의 함수.
    
    Args:
        user_input: 입력 데이터 딕셔너리
        task: 태스크 ID (None이면 user_input["task"] 사용)
        version: 버전 (기본값 "latest")
        registry: TaskRegistry 인스턴스 (None이면 전역 레지스트리 사용)
        policy: ExecutionPolicy (None이면 기본 정책 사용)
    
    Returns:
        실행 결과 딕셔너리
    
    Raises:
        ValueError: task가 지정되지 않았거나 task를 찾을 수 없을 때
        SchemaValidationError: 스키마 검증 실패 시
    
    Example:
        result = Run(
            {"query": "search term", "task": "search"},
            version="0.1.0"
        )
    """
    # 레지스트리 결정
    if registry is None:
        registry = get_global_registry()
    
    # task_id 결정
    task_id = task or user_input.get("task")
    if not task_id:
        raise ValueError(
            "task must be specified either as argument or in user_input['task']"
        )
    
    # 태스크 스펙 가져오기
    try:
        task_spec = registry.get(task_id, version=version)
    except TaskNotFoundError as e:
        raise ValueError(str(e))
    
    # 입력 스키마 검증
    if task_spec.schema_in:
        try:
            validate_schema(user_input, task_spec.schema_in, f"Input validation for {task_id}")
        except SchemaValidationError as e:
            raise ValueError(str(e))
    
    # Context 생성
    context = Context(user_input, thread_safe=True)
    
    # Executor로 실행
    executor = Executor(policy=policy)
    result = executor.run(task_spec.node, context=context)
    
    # 출력 데이터 추출
    output_data = context.to_dict()
    
    # 출력 스키마 검증
    if task_spec.schema_out and result.success:
        try:
            validate_schema(output_data, task_spec.schema_out, f"Output validation for {task_id}")
        except SchemaValidationError as e:
            raise ValueError(str(e))
    
    return {
        "success": result.success,
        "duration": result.duration,
        "data": output_data,
        "errors": [str(e) for e in result.errors],
        "task_id": task_id,
        "version": task_spec.version,
    }


def create_app(
    registry: Optional[TaskRegistry] = None,
    title: str = "Parasel API",
    description: str = "AI 파이프라인 실행 API",
    version: str = "0.1.0",
) -> FastAPI:
    """
    FastAPI 앱을 생성합니다.
    
    Args:
        registry: TaskRegistry 인스턴스 (None이면 전역 레지스트리)
        title: API 타이틀
        description: API 설명
        version: API 버전
    
    Returns:
        FastAPI 앱 인스턴스
    
    Example:
        app = create_app()
        # uvicorn으로 실행: uvicorn module:app
    """
    if registry is None:
        registry = get_global_registry()
    
    app = FastAPI(
        title=title,
        description=description,
        version=version,
    )
    
    @app.get("/")
    def root():
        """루트 엔드포인트"""
        return {
            "message": "Parasel API",
            "version": version,
            "endpoints": {
                "tasks": "/tasks",
                "run": "/run/{task_id}",
            }
        }
    
    @app.get("/tasks")
    def list_tasks():
        """등록된 모든 태스크 목록"""
        tasks_info = []
        for task_id in registry.list_tasks():
            versions = registry.list_versions(task_id)
            latest_spec = registry.get(task_id, "latest")
            tasks_info.append({
                "task_id": task_id,
                "versions": versions,
                "latest": versions[-1] if versions else None,
                "description": latest_spec.description,
                "tags": latest_spec.tags,
            })
        return {"tasks": tasks_info}
    
    @app.get("/tasks/{task_id}")
    def get_task_info(task_id: str, version: str = Query("latest")):
        """특정 태스크 정보"""
        try:
            spec = registry.get(task_id, version=version)
            return {
                "task_id": spec.task_id,
                "version": spec.version,
                "description": spec.description,
                "requires": spec.requires,
                "produces": spec.produces,
                "tags": spec.tags,
                "metadata": spec.metadata,
            }
        except TaskNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    @app.post("/run/{task_id}", response_model=RunResponse)
    def run_task(
        task_id: str,
        request: RunRequest,
    ):
        """태스크 실행"""
        try:
            # version은 request에서 가져옴
            version = request.version
            
            # task는 path parameter를 우선하고, 없으면 request.task, 그것도 없으면 data.task
            final_task_id = task_id or request.task or request.data.get("task")
            if not final_task_id:
                raise HTTPException(
                    status_code=400,
                    detail="task_id must be provided in path or request"
                )
            
            # Run 함수로 실행
            result = Run(
                user_input=request.data,
                task=final_task_id,
                version=version,
                registry=registry,
            )
            
            return RunResponse(**result)
        
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {e}")
    
    @app.get("/health")
    def health():
        """헬스 체크"""
        return {"status": "healthy", "timestamp": time.time()}
    
    return app


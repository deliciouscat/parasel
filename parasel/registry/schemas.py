"""스키마 및 의존성 검증 유틸리티"""

from typing import Any, Dict, List, Optional, Set, Type
from pydantic import BaseModel, ValidationError

from parasel.core.context import Context


class SchemaValidationError(Exception):
    """스키마 검증 실패 시 발생하는 에러"""
    pass


def requires_keys(keys: List[str]):
    """
    데코레이터: 함수 실행 전 context에 필수 키가 있는지 검증
    
    Args:
        keys: 필수 키 리스트
    
    Example:
        @requires_keys(["query", "page"])
        def search(context, out_name):
            ...
    """
    def decorator(func):
        def wrapper(context: Context, *args, **kwargs):
            missing = [k for k in keys if k not in context]
            if missing:
                raise SchemaValidationError(
                    f"Required keys missing in context: {missing}"
                )
            return func(context, *args, **kwargs)
        
        # 비동기 함수 지원
        if hasattr(func, '__await__'):
            async def async_wrapper(context: Context, *args, **kwargs):
                missing = [k for k in keys if k not in context]
                if missing:
                    raise SchemaValidationError(
                        f"Required keys missing in context: {missing}"
                    )
                return await func(context, *args, **kwargs)
            return async_wrapper
        
        return wrapper
    return decorator


def produces_keys(keys: List[str]):
    """
    데코레이터: 함수 실행 후 context에 약속한 키가 있는지 검증
    
    Args:
        keys: 생성해야 하는 키 리스트
    
    Example:
        @produces_keys(["summary", "keywords"])
        def analyze(context):
            context["summary"] = "..."
            context["keywords"] = [...]
    """
    def decorator(func):
        def wrapper(context: Context, *args, **kwargs):
            result = func(context, *args, **kwargs)
            missing = [k for k in keys if k not in context]
            if missing:
                raise SchemaValidationError(
                    f"Function did not produce required keys: {missing}"
                )
            return result
        
        # 비동기 함수 지원
        if hasattr(func, '__await__'):
            async def async_wrapper(context: Context, *args, **kwargs):
                result = await func(context, *args, **kwargs)
                missing = [k for k in keys if k not in context]
                if missing:
                    raise SchemaValidationError(
                        f"Function did not produce required keys: {missing}"
                    )
                return result
            return async_wrapper
        
        return wrapper
    return decorator


def validate_schema(
    data: Dict[str, Any],
    schema: Type[BaseModel],
    error_prefix: str = "Validation error",
) -> BaseModel:
    """
    Pydantic 스키마로 데이터 검증
    
    Args:
        data: 검증할 데이터
        schema: Pydantic BaseModel 클래스
        error_prefix: 에러 메시지 접두사
    
    Returns:
        검증된 Pydantic 모델 인스턴스
    
    Raises:
        SchemaValidationError: 검증 실패 시
    """
    try:
        return schema(**data)
    except ValidationError as e:
        raise SchemaValidationError(f"{error_prefix}: {e}")


def validate_requires(context: Context, requires: List[str]) -> None:
    """
    Context에 필수 키들이 있는지 검증
    
    Args:
        context: 검증할 컨텍스트
        requires: 필수 키 리스트
    
    Raises:
        SchemaValidationError: 필수 키가 없을 때
    """
    missing = [k for k in requires if k not in context]
    if missing:
        raise SchemaValidationError(f"Required keys missing in context: {missing}")


def validate_produces(context: Context, produces: List[str]) -> None:
    """
    Context에 약속한 키들이 생성되었는지 검증
    
    Args:
        context: 검증할 컨텍스트
        produces: 생성해야 하는 키 리스트
    
    Raises:
        SchemaValidationError: 키가 생성되지 않았을 때
    """
    missing = [k for k in produces if k not in context]
    if missing:
        raise SchemaValidationError(f"Expected keys not produced: {missing}")


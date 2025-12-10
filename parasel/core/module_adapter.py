"""ModuleAdapter: 사용자 정의 함수를 Node로 래핑하는 Strategy 패턴"""

import asyncio
import inspect
from typing import Any, Callable, Dict, Optional
from parasel.core.node import Node, ExecutionError
from parasel.core.context import Context


class ModuleAdapter(Node):
    """
    사용자 정의 함수를 Node 인터페이스로 래핑합니다.
    
    지원하는 함수 시그니처:
    1. func(context, out_name, **kwargs) -> None  # context에 out_name 키로 결과 저장
    2. func(context, **kwargs) -> None             # context를 직접 수정
    3. func(context, out_name, **kwargs) -> Any    # 반환값을 out_name 키로 저장
    4. func(context, **kwargs) -> Any              # 반환값을 무시 (경고)
    
    동기/비동기 함수 모두 지원합니다.
    """
    
    def __init__(
        self,
        func: Callable,
        out_name: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Args:
            func: 래핑할 함수 (동기 또는 비동기)
            out_name: 결과를 저장할 context 키 이름
            name: 노드 이름 (기본값은 함수 이름)
            **kwargs: 함수에 전달할 추가 인자 및 Node 기본 인자들
        """
        # Node 기본 인자 분리
        node_kwargs = {}
        func_kwargs = {}
        
        for key, value in kwargs.items():
            if key in ["timeout", "retries", "metadata"]:
                node_kwargs[key] = value
            else:
                func_kwargs[key] = value
        
        super().__init__(name=name or func.__name__, **node_kwargs)
        self.func = func
        self.out_name = out_name
        self.func_kwargs = func_kwargs
        self.is_async = asyncio.iscoroutinefunction(func)
    
    def run(self, context: Context) -> None:
        """동기 실행"""
        if self.is_async:
            # 비동기 함수를 동기 컨텍스트에서 실행
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(self._run_async_impl(context))
        else:
            self._run_sync_impl(context)
    
    async def run_async(self, context: Context) -> None:
        """비동기 실행"""
        if self.is_async:
            await self._run_async_impl(context)
        else:
            # 동기 함수를 비동기 컨텍스트에서 실행
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._run_sync_impl, context)
    
    def _run_sync_impl(self, context: Context) -> None:
        """동기 함수 실행 구현"""
        try:
            # 함수 시그니처 분석
            sig = inspect.signature(self.func)
            params = sig.parameters
            
            # context 인자 준비
            call_kwargs = {"context": context}
            
            # out_name이 파라미터에 있으면 추가
            if "out_name" in params and self.out_name:
                call_kwargs["out_name"] = self.out_name
            
            # 추가 kwargs 병합
            call_kwargs.update(self.func_kwargs)
            
            # 함수 호출
            result = self.func(**call_kwargs)
            
            # 반환값이 있고 out_name이 지정되었으면 저장
            if result is not None and self.out_name:
                context[self.out_name] = result
        
        except Exception as e:
            raise ExecutionError(
                f"ModuleAdapter '{self.name}' execution failed: {e}",
                node_name=self.name,
                cause=e,
            )
    
    async def _run_async_impl(self, context: Context) -> None:
        """비동기 함수 실행 구현"""
        try:
            # 함수 시그니처 분석
            sig = inspect.signature(self.func)
            params = sig.parameters
            
            # context 인자 준비
            call_kwargs = {"context": context}
            
            # out_name이 파라미터에 있으면 추가
            if "out_name" in params and self.out_name:
                call_kwargs["out_name"] = self.out_name
            
            # 추가 kwargs 병합
            call_kwargs.update(self.func_kwargs)
            
            # 비동기 함수 호출
            result = await self.func(**call_kwargs)
            
            # 반환값이 있고 out_name이 지정되었으면 저장
            if result is not None and self.out_name:
                context[self.out_name] = result
        
        except Exception as e:
            raise ExecutionError(
                f"ModuleAdapter '{self.name}' async execution failed: {e}",
                node_name=self.name,
                cause=e,
            )
    
    def __repr__(self) -> str:
        return (
            f"ModuleAdapter(name='{self.name}', func={self.func.__name__}, "
            f"out_name={self.out_name}, async={self.is_async})"
        )


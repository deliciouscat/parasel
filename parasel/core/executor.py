"""Executor: 노드 실행 엔진 (타임아웃, 리트라이, 에러 핸들링)"""

import time
import asyncio
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

from parasel.core.node import Node, ExecutionError
from parasel.core.context import Context


class ErrorMode(Enum):
    """에러 처리 모드"""
    FAIL_FAST = "fail_fast"  # 첫 에러 발생 시 즉시 중단
    COLLECT = "collect"      # 모든 에러 수집 후 반환


@dataclass
class ExecutionPolicy:
    """실행 정책 설정"""
    timeout: Optional[float] = None  # 전체 실행 타임아웃 (초)
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])  # 재시도할 예외 타입
    retry_backoff: float = 1.0  # 재시도 간격 (초)
    parallel_max_workers: Optional[int] = None  # 병렬 실행 최대 워커 수
    error_mode: ErrorMode = ErrorMode.FAIL_FAST  # 에러 처리 모드
    
    # 훅 함수들 (옵셔널)
    before_node: Optional[Callable[[Node, Context], None]] = None
    after_node: Optional[Callable[[Node, Context, Optional[Exception]], None]] = None
    on_error: Optional[Callable[[Node, Context, Exception], None]] = None


class ExecutionResult:
    """실행 결과"""
    
    def __init__(
        self,
        context: Context,
        success: bool,
        duration: float,
        errors: Optional[List[ExecutionError]] = None,
        node_timings: Optional[Dict[str, float]] = None,
    ):
        self.context = context
        self.success = success
        self.duration = duration
        self.errors = errors or []
        self.node_timings = node_timings or {}


class Executor:
    """
    노드 실행 엔진.
    
    타임아웃, 리트라이, 에러 핸들링, 훅 등을 관리합니다.
    """
    
    def __init__(self, policy: Optional[ExecutionPolicy] = None):
        """
        Args:
            policy: 실행 정책 (None이면 기본 정책 사용)
        """
        self.policy = policy or ExecutionPolicy()
    
    def run(
        self,
        node: Node,
        context: Optional[Context] = None,
        initial_data: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        노드를 동기 실행합니다.
        
        Args:
            node: 실행할 노드
            context: 기존 컨텍스트 (None이면 새로 생성)
            initial_data: 초기 데이터 (context가 None일 때만 사용)
        
        Returns:
            ExecutionResult: 실행 결과
        """
        if context is None:
            context = Context(initial_data or {}, thread_safe=True)
        
        start_time = time.time()
        errors = []
        
        try:
            self._run_with_retry(node, context)
        except ExecutionError as e:
            errors.append(e)
            if self.policy.error_mode == ErrorMode.FAIL_FAST:
                duration = time.time() - start_time
                return ExecutionResult(
                    context=context,
                    success=False,
                    duration=duration,
                    errors=errors,
                )
        
        duration = time.time() - start_time
        return ExecutionResult(
            context=context,
            success=len(errors) == 0,
            duration=duration,
            errors=errors,
        )
    
    async def run_async(
        self,
        node: Node,
        context: Optional[Context] = None,
        initial_data: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        노드를 비동기 실행합니다.
        
        Args:
            node: 실행할 노드
            context: 기존 컨텍스트 (None이면 새로 생성)
            initial_data: 초기 데이터 (context가 None일 때만 사용)
        
        Returns:
            ExecutionResult: 실행 결과
        """
        if context is None:
            context = Context(initial_data or {}, thread_safe=True)
        
        start_time = time.time()
        errors = []
        
        try:
            await self._run_with_retry_async(node, context)
        except ExecutionError as e:
            errors.append(e)
            if self.policy.error_mode == ErrorMode.FAIL_FAST:
                duration = time.time() - start_time
                return ExecutionResult(
                    context=context,
                    success=False,
                    duration=duration,
                    errors=errors,
                )
        
        duration = time.time() - start_time
        return ExecutionResult(
            context=context,
            success=len(errors) == 0,
            duration=duration,
            errors=errors,
        )
    
    def _run_with_retry(self, node: Node, context: Context) -> None:
        """재시도 로직이 포함된 동기 실행"""
        retries = node.retries if node.retries > 0 else 0
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                # before_node 훅
                if self.policy.before_node:
                    self.policy.before_node(node, context)
                
                # 노드 실행
                node_start = time.time()
                node.run(context)
                node_duration = time.time() - node_start
                
                # after_node 훅
                if self.policy.after_node:
                    self.policy.after_node(node, context, None)
                
                return  # 성공
            
            except Exception as e:
                last_error = e
                
                # on_error 훅
                if self.policy.on_error:
                    self.policy.on_error(node, context, e)
                
                # after_node 훅 (에러 포함)
                if self.policy.after_node:
                    self.policy.after_node(node, context, e)
                
                # 재시도 가능 여부 확인
                should_retry = any(isinstance(e, exc_type) for exc_type in self.policy.retry_on)
                
                if attempt < retries and should_retry:
                    time.sleep(self.policy.retry_backoff * (attempt + 1))
                    continue
                else:
                    # 더 이상 재시도하지 않음
                    if isinstance(e, ExecutionError):
                        raise
                    else:
                        raise ExecutionError(
                            f"Node '{node.name}' failed after {attempt + 1} attempt(s): {e}",
                            node_name=node.name,
                            cause=e,
                        )
        
        # 모든 재시도 실패
        if last_error:
            if isinstance(last_error, ExecutionError):
                raise last_error
            else:
                raise ExecutionError(
                    f"Node '{node.name}' failed after {retries + 1} attempt(s): {last_error}",
                    node_name=node.name,
                    cause=last_error,
                )
    
    async def _run_with_retry_async(self, node: Node, context: Context) -> None:
        """재시도 로직이 포함된 비동기 실행"""
        retries = node.retries if node.retries > 0 else 0
        last_error = None
        
        for attempt in range(retries + 1):
            try:
                # before_node 훅
                if self.policy.before_node:
                    self.policy.before_node(node, context)
                
                # 노드 실행
                node_start = time.time()
                await node.run_async(context)
                node_duration = time.time() - node_start
                
                # after_node 훅
                if self.policy.after_node:
                    self.policy.after_node(node, context, None)
                
                return  # 성공
            
            except Exception as e:
                last_error = e
                
                # on_error 훅
                if self.policy.on_error:
                    self.policy.on_error(node, context, e)
                
                # after_node 훅 (에러 포함)
                if self.policy.after_node:
                    self.policy.after_node(node, context, e)
                
                # 재시도 가능 여부 확인
                should_retry = any(isinstance(e, exc_type) for exc_type in self.policy.retry_on)
                
                if attempt < retries and should_retry:
                    await asyncio.sleep(self.policy.retry_backoff * (attempt + 1))
                    continue
                else:
                    # 더 이상 재시도하지 않음
                    if isinstance(e, ExecutionError):
                        raise
                    else:
                        raise ExecutionError(
                            f"Node '{node.name}' failed after {attempt + 1} attempt(s): {e}",
                            node_name=node.name,
                            cause=e,
                        )
        
        # 모든 재시도 실패
        if last_error:
            if isinstance(last_error, ExecutionError):
                raise last_error
            else:
                raise ExecutionError(
                    f"Node '{node.name}' failed after {retries + 1} attempt(s): {last_error}",
                    node_name=node.name,
                    cause=last_error,
                )


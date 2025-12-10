"""Node 추상화: Composite 패턴으로 Serial/Parallel 파이프라인 정의"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from parasel.core.context import Context


class ExecutionError(Exception):
    """노드 실행 중 발생한 에러"""
    
    def __init__(self, message: str, node_name: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.node_name = node_name
        self.cause = cause


class Node(ABC):
    """
    파이프라인 노드의 기본 추상 클래스.
    
    모든 노드는 run(context) 메서드를 구현해야 합니다.
    """
    
    def __init__(
        self,
        name: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            name: 노드 이름 (디버깅/로깅용)
            timeout: 실행 타임아웃 (초)
            retries: 재시도 횟수
            metadata: 추가 메타데이터
        """
        self.name = name or self.__class__.__name__
        self.timeout = timeout
        self.retries = retries
        self.metadata = metadata or {}
    
    @abstractmethod
    def run(self, context: Context) -> None:
        """
        노드를 실행합니다.
        
        Args:
            context: 실행 컨텍스트 (입력을 읽고 출력을 씁니다)
        
        Raises:
            ExecutionError: 실행 중 에러 발생 시
        """
        pass
    
    async def run_async(self, context: Context) -> None:
        """
        비동기 실행 (기본 구현은 동기 run을 래핑)
        
        서브클래스에서 네이티브 async 구현을 제공할 수 있습니다.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.run, context)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class Serial(Node):
    """
    순차 실행 노드.
    
    자식 노드들을 순서대로 실행합니다. 한 노드가 실패하면 기본적으로 중단합니다.
    """
    
    def __init__(
        self,
        children: List[Node],
        name: Optional[str] = None,
        continue_on_error: bool = False,
        **kwargs,
    ):
        """
        Args:
            children: 순차 실행할 자식 노드 리스트
            name: 노드 이름
            continue_on_error: True면 에러가 발생해도 다음 노드 계속 실행
            **kwargs: Node 기본 인자들
        """
        super().__init__(name=name or "Serial", **kwargs)
        self.children = children
        self.continue_on_error = continue_on_error
    
    def run(self, context: Context) -> None:
        """자식 노드들을 순차 실행"""
        errors = []
        
        for i, child in enumerate(self.children):
            try:
                child.run(context)
            except Exception as e:
                error = ExecutionError(
                    f"Serial node '{self.name}' child {i} ('{child.name}') failed: {e}",
                    node_name=child.name,
                    cause=e,
                )
                
                if self.continue_on_error:
                    errors.append(error)
                else:
                    raise error
        
        if errors and not self.continue_on_error:
            raise ExecutionError(
                f"Serial node '{self.name}' completed with {len(errors)} error(s)",
                node_name=self.name,
            )
    
    async def run_async(self, context: Context) -> None:
        """자식 노드들을 순차 비동기 실행"""
        errors = []
        
        for i, child in enumerate(self.children):
            try:
                await child.run_async(context)
            except Exception as e:
                error = ExecutionError(
                    f"Serial node '{self.name}' child {i} ('{child.name}') failed: {e}",
                    node_name=child.name,
                    cause=e,
                )
                
                if self.continue_on_error:
                    errors.append(error)
                else:
                    raise error
        
        if errors and not self.continue_on_error:
            raise ExecutionError(
                f"Serial node '{self.name}' completed with {len(errors)} error(s)",
                node_name=self.name,
            )


class Parallel(Node):
    """
    병렬 실행 노드.
    
    자식 노드들을 동시에 실행합니다. 에러 처리 정책을 설정할 수 있습니다.
    """
    
    def __init__(
        self,
        children: List[Node],
        name: Optional[str] = None,
        max_workers: Optional[int] = None,
        fail_fast: bool = True,
        **kwargs,
    ):
        """
        Args:
            children: 병렬 실행할 자식 노드 리스트
            name: 노드 이름
            max_workers: 최대 워커 수 (None이면 자식 수만큼)
            fail_fast: True면 첫 에러 발생 시 즉시 중단, False면 모든 노드 완료 후 에러 수집
            **kwargs: Node 기본 인자들
        """
        super().__init__(name=name or "Parallel", **kwargs)
        self.children = children
        self.max_workers = max_workers or len(children)
        self.fail_fast = fail_fast
    
    def run(self, context: Context) -> None:
        """자식 노드들을 병렬 실행 (ThreadPoolExecutor 사용)"""
        if not self.children:
            return
        
        errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            if self.fail_fast:
                # 첫 에러 발생 시 즉시 중단
                futures = {executor.submit(child.run, context): child for child in self.children}
                
                for future in as_completed(futures):
                    child = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        # 첫 에러 발생 시 나머지 취소하고 즉시 raise
                        for f in futures:
                            f.cancel()
                        raise ExecutionError(
                            f"Parallel node '{self.name}' child '{child.name}' failed: {e}",
                            node_name=child.name,
                            cause=e,
                        )
            else:
                # 모든 노드 완료 후 에러 수집
                futures = {executor.submit(child.run, context): child for child in self.children}
                
                for future in as_completed(futures):
                    child = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        errors.append(
                            ExecutionError(
                                f"Parallel node '{self.name}' child '{child.name}' failed: {e}",
                                node_name=child.name,
                                cause=e,
                            )
                        )
        
        if errors:
            raise ExecutionError(
                f"Parallel node '{self.name}' completed with {len(errors)} error(s): "
                + ", ".join(str(e) for e in errors),
                node_name=self.name,
            )
    
    async def run_async(self, context: Context) -> None:
        """자식 노드들을 병렬 비동기 실행"""
        if not self.children:
            return
        
        errors = []
        
        if self.fail_fast:
            # 첫 에러 발생 시 즉시 중단
            tasks = [child.run_async(context) for child in self.children]
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                # gather는 첫 에러를 raise하고 나머지는 취소됨
                raise ExecutionError(
                    f"Parallel node '{self.name}' failed: {e}",
                    node_name=self.name,
                    cause=e,
                )
        else:
            # 모든 노드 완료 후 에러 수집
            tasks = [child.run_async(context) for child in self.children]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    errors.append(
                        ExecutionError(
                            f"Parallel node '{self.name}' child '{self.children[i].name}' failed: {result}",
                            node_name=self.children[i].name,
                            cause=result,
                        )
                    )
        
        if errors:
            raise ExecutionError(
                f"Parallel node '{self.name}' completed with {len(errors)} error(s): "
                + ", ".join(str(e) for e in errors),
                node_name=self.name,
            )


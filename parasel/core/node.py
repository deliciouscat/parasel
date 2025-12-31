"""Node 추상화: Composite 패턴으로 Serial/Parallel 파이프라인 정의"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Iterator, Union, Iterable
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from parasel.core.context import Context
import copy


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
        children: List[Union[Node, Iterable[Node]]],
        name: Optional[str] = None,
        max_workers: Optional[int] = None,
        fail_fast: bool = True,
        **kwargs,
    ):
        """
        Args:
            children: 병렬 실행할 자식 노드 리스트 (Iterable을 포함할 수 있음)
            name: 노드 이름
            max_workers: 최대 워커 수 (None이면 자식 수만큼)
            fail_fast: True면 첫 에러 발생 시 즉시 중단, False면 모든 노드 완료 후 에러 수집
            **kwargs: Node 기본 인자들
        """
        super().__init__(name=name or "Parallel", **kwargs)
        
        # children을 flatten (ByArgs 등의 iterable 지원)
        flattened_children = []
        for child in children:
            if isinstance(child, Node):
                flattened_children.append(child)
            elif hasattr(child, '__iter__') and not isinstance(child, (str, bytes)):
                # Iterable이면 펼침
                flattened_children.extend(child)
            else:
                flattened_children.append(child)
        
        self.children = flattened_children
        self.max_workers = max_workers or len(self.children) if self.children else 1
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


class ByArgs:
    """
    주어진 args의 각 값에 대해 노드를 복제하여 생성하는 헬퍼 클래스.
    
    Parallel과 함께 사용하여 동일한 함수를 다른 인자로 여러 번 실행할 수 있습니다.
    각 실행 결과는 지정된 out_name에 리스트로 누적됩니다.
    
    예제:
        ```python
        Parallel([
            ByArgs(query_expansion, args={"language": ["en", "ko"]})
        ])
        ```
        
        이는 query_expansion을 language="en"과 language="ko"로 각각 실행합니다.
    """
    
    def __init__(self, base_node, args: Dict[str, List[Any]]):
        """
        Args:
            base_node: 복제할 기본 노드 (보통 ModuleAdapter)
            args: 파라미터 이름과 값 리스트의 딕셔너리
                  예: {"language": ["en", "ko"], "max_results": [10, 20]}
        """
        from parasel.core.module_adapter import ModuleAdapter
        
        if not isinstance(base_node, ModuleAdapter):
            raise TypeError("ByArgs는 ModuleAdapter와 함께 사용해야 합니다")
        
        self.base_node = base_node
        self.args = args
    
    def __iter__(self) -> Iterator[Node]:
        """
        각 arg 조합에 대해 노드를 생성합니다.
        
        cartesian product를 사용하여 모든 파라미터 조합을 생성합니다.
        """
        from parasel.core.module_adapter import ModuleAdapter
        
        # 모든 파라미터에 대해 cartesian product 생성
        import itertools
        
        param_names = list(self.args.keys())
        param_values = [self.args[name] for name in param_names]
        
        # 각 조합에 대해 노드 생성
        for combination in itertools.product(*param_values):
            # 새로운 kwargs 생성
            new_kwargs = dict(zip(param_names, combination))
            
            # 기존 func_kwargs와 병합
            merged_kwargs = {**self.base_node.func_kwargs, **new_kwargs}
            
            # 새로운 ModuleAdapter 생성
            node = ModuleAdapter(
                func=self.base_node.func,
                out_name=self.base_node.out_name,
                name=f"{self.base_node.name}[{','.join(f'{k}={v}' for k, v in new_kwargs.items())}]",
                **merged_kwargs
            )
            
            # _accumulate_result 플래그 설정 (나중에 ModuleAdapter에서 처리)
            node._accumulate_result = True
            
            yield node
    
    def __repr__(self) -> str:
        return f"ByArgs(node={self.base_node.name}, args={self.args})"


class ByKeys(Node):
    """
    Context의 특정 키에 저장된 리스트의 각 아이템에 대해 노드를 실행하는 클래스.
    
    실행 시점에 Context를 읽어 동적으로 여러 노드를 생성하고 병렬 실행합니다.
    
    예제:
        ```python
        # context["query_expansion"] = ["query1", "query2", "query3"]
        Parallel([
            ByKeys(duckduckgo_search, keys=["query_expansion"])
        ])
        ```
        
        이는 query_expansion의 각 쿼리에 대해 duckduckgo_search를 실행합니다.
    """
    
    def __init__(
        self,
        base_node,
        keys: List[str],
        input_key_name: str = "input",
        name: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            base_node: 복제할 기본 노드 (보통 ModuleAdapter)
            keys: Context에서 읽을 키 리스트 (각 키는 리스트여야 함)
            input_key_name: base_node 함수에 각 아이템을 전달할 파라미터 이름
            name: 노드 이름
            **kwargs: Node 기본 인자들
        """
        from parasel.core.module_adapter import ModuleAdapter
        
        if not isinstance(base_node, ModuleAdapter):
            raise TypeError("ByKeys는 ModuleAdapter와 함께 사용해야 합니다")
        
        super().__init__(name=name or f"ByKeys[{','.join(keys)}]", **kwargs)
        self.base_node = base_node
        self.keys = keys
        self.input_key_name = input_key_name
    
    def run(self, context: Context) -> None:
        """
        Context에서 키를 읽고 각 아이템에 대해 노드를 실행합니다.
        """
        from parasel.core.module_adapter import ModuleAdapter
        
        # 모든 키에서 아이템 수집
        all_items = []
        for key in self.keys:
            if key not in context:
                raise ExecutionError(
                    f"ByKeys: key '{key}' not found in context",
                    node_name=self.name
                )
            
            value = context[key]
            if not isinstance(value, (list, tuple)):
                raise ExecutionError(
                    f"ByKeys: key '{key}' must be a list or tuple, got {type(value)}",
                    node_name=self.name
                )
            
            # 중첩 리스트를 flatten
            for item in value:
                if isinstance(item, (list, tuple)):
                    all_items.extend(item)
                else:
                    all_items.append(item)
        
        if not all_items:
            # 아이템이 없으면 아무것도 하지 않음
            return
        
        # 각 아이템에 대해 노드 생성
        nodes = []
        for i, item in enumerate(all_items):
            # 새로운 kwargs 생성
            new_kwargs = {**self.base_node.func_kwargs, self.input_key_name: item}
            
            # 새로운 ModuleAdapter 생성
            node = ModuleAdapter(
                func=self.base_node.func,
                out_name=self.base_node.out_name,
                name=f"{self.base_node.name}[{i}]",
                **new_kwargs
            )
            
            # _accumulate_result 플래그 설정
            node._accumulate_result = True
            
            nodes.append(node)
        
        # 병렬 실행
        parallel = Parallel(nodes, name=f"{self.name}_parallel")
        parallel.run(context)
    
    async def run_async(self, context: Context) -> None:
        """비동기 실행"""
        from parasel.core.module_adapter import ModuleAdapter
        
        # 모든 키에서 아이템 수집
        all_items = []
        for key in self.keys:
            if key not in context:
                raise ExecutionError(
                    f"ByKeys: key '{key}' not found in context",
                    node_name=self.name
                )
            
            value = context[key]
            if not isinstance(value, (list, tuple)):
                raise ExecutionError(
                    f"ByKeys: key '{key}' must be a list or tuple, got {type(value)}",
                    node_name=self.name
                )
            
            # 중첩 리스트를 flatten
            for item in value:
                if isinstance(item, (list, tuple)):
                    all_items.extend(item)
                else:
                    all_items.append(item)
        
        if not all_items:
            return
        
        # 각 아이템에 대해 노드 생성
        nodes = []
        for i, item in enumerate(all_items):
            new_kwargs = {**self.base_node.func_kwargs, self.input_key_name: item}
            
            node = ModuleAdapter(
                func=self.base_node.func,
                out_name=self.base_node.out_name,
                name=f"{self.base_node.name}[{i}]",
                **new_kwargs
            )
            
            node._accumulate_result = True
            nodes.append(node)
        
        # 병렬 비동기 실행
        parallel = Parallel(nodes, name=f"{self.name}_parallel")
        await parallel.run_async(context)
    
    def __repr__(self) -> str:
        return f"ByKeys(node={self.base_node.name}, keys={self.keys})"

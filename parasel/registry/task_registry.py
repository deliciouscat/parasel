"""Task Registry: 태스크 버전 관리 및 검색"""

from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from packaging import version as version_parser
from pydantic import BaseModel

from parasel.core.node import Node


class TaskNotFoundError(Exception):
    """태스크를 찾을 수 없을 때 발생하는 에러"""
    pass


class VersionConflictError(Exception):
    """버전 충돌 시 발생하는 에러"""
    pass


@dataclass
class TaskSpec:
    """태스크 명세"""
    task_id: str
    version: str
    node: Node
    description: Optional[str] = None
    requires: List[str] = field(default_factory=list)  # 입력 키 의존성
    produces: List[str] = field(default_factory=list)  # 출력 키
    schema_in: Optional[Type[BaseModel]] = None
    schema_out: Optional[Type[BaseModel]] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """버전 형식 검증"""
        try:
            version_parser.parse(self.version)
        except Exception as e:
            raise ValueError(f"Invalid version format '{self.version}': {e}")


class TaskRegistry:
    """
    태스크 레지스트리: 버전별 태스크를 등록하고 검색합니다.
    
    Example:
        registry = TaskRegistry()
        registry.register(
            task_id="search",
            version="0.1.0",
            node=search_pipeline,
            requires=["query"],
            produces=["results"],
        )
        
        task_spec = registry.get("search", version="latest")
    """
    
    def __init__(self):
        # {task_id: {version: TaskSpec}}
        self._tasks: Dict[str, Dict[str, TaskSpec]] = {}
        # {task_id: stable_version}
        self._stable_versions: Dict[str, str] = {}
    
    def register(
        self,
        task_id: str,
        version: str,
        node: Node,
        description: Optional[str] = None,
        requires: Optional[List[str]] = None,
        produces: Optional[List[str]] = None,
        schema_in: Optional[Type[BaseModel]] = None,
        schema_out: Optional[Type[BaseModel]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
        mark_stable: bool = False,
    ) -> TaskSpec:
        """
        태스크를 레지스트리에 등록합니다.
        
        Args:
            task_id: 태스크 고유 ID
            version: 버전 (semver 형식)
            node: 실행할 노드
            description: 설명
            requires: 필수 입력 키 리스트
            produces: 출력 키 리스트
            schema_in: 입력 Pydantic 스키마
            schema_out: 출력 Pydantic 스키마
            tags: 태그 리스트
            metadata: 추가 메타데이터
            overwrite: True면 기존 버전 덮어쓰기 허용
            mark_stable: True면 이 버전을 stable로 표시
        
        Returns:
            등록된 TaskSpec
        
        Raises:
            VersionConflictError: 이미 존재하는 버전이고 overwrite=False
        """
        # 중복 확인
        if task_id in self._tasks and version in self._tasks[task_id]:
            if not overwrite:
                raise VersionConflictError(
                    f"Task '{task_id}' version '{version}' already exists. "
                    "Use overwrite=True to replace."
                )
        
        # TaskSpec 생성
        spec = TaskSpec(
            task_id=task_id,
            version=version,
            node=node,
            description=description,
            requires=requires or [],
            produces=produces or [],
            schema_in=schema_in,
            schema_out=schema_out,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        # 등록
        if task_id not in self._tasks:
            self._tasks[task_id] = {}
        self._tasks[task_id][version] = spec
        
        # stable 버전 표시
        if mark_stable:
            self._stable_versions[task_id] = version
        
        return spec
    
    def get(self, task_id: str, version: str = "latest") -> TaskSpec:
        """
        태스크를 검색합니다.
        
        Args:
            task_id: 태스크 ID
            version: 버전 ("latest", "stable", 또는 semver 문자열)
        
        Returns:
            TaskSpec
        
        Raises:
            TaskNotFoundError: 태스크를 찾을 수 없을 때
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task '{task_id}' not found in registry")
        
        versions = self._tasks[task_id]
        
        if version == "latest":
            # 가장 최신 버전 반환
            latest_ver = max(versions.keys(), key=lambda v: version_parser.parse(v))
            return versions[latest_ver]
        
        elif version == "stable":
            # stable로 표시된 버전 반환
            if task_id not in self._stable_versions:
                raise TaskNotFoundError(
                    f"No stable version marked for task '{task_id}'"
                )
            stable_ver = self._stable_versions[task_id]
            return versions[stable_ver]
        
        else:
            # 특정 버전 반환
            if version not in versions:
                available = ", ".join(versions.keys())
                raise TaskNotFoundError(
                    f"Task '{task_id}' version '{version}' not found. "
                    f"Available versions: {available}"
                )
            return versions[version]
    
    def list_versions(self, task_id: str) -> List[str]:
        """
        태스크의 모든 버전 리스트를 반환합니다.
        
        Args:
            task_id: 태스크 ID
        
        Returns:
            버전 리스트 (semver 순서로 정렬)
        
        Raises:
            TaskNotFoundError: 태스크를 찾을 수 없을 때
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task '{task_id}' not found in registry")
        
        versions = list(self._tasks[task_id].keys())
        return sorted(versions, key=lambda v: version_parser.parse(v))
    
    def list_tasks(self) -> List[str]:
        """모든 태스크 ID 리스트를 반환합니다."""
        return list(self._tasks.keys())
    
    def get_by_tag(self, tag: str) -> List[TaskSpec]:
        """
        특정 태그를 가진 모든 태스크를 반환합니다.
        
        Args:
            tag: 검색할 태그
        
        Returns:
            TaskSpec 리스트
        """
        results = []
        for task_versions in self._tasks.values():
            for spec in task_versions.values():
                if tag in spec.tags:
                    results.append(spec)
        return results
    
    def mark_stable(self, task_id: str, version: str) -> None:
        """
        특정 버전을 stable로 표시합니다.
        
        Args:
            task_id: 태스크 ID
            version: stable로 표시할 버전
        
        Raises:
            TaskNotFoundError: 태스크 또는 버전을 찾을 수 없을 때
        """
        if task_id not in self._tasks or version not in self._tasks[task_id]:
            raise TaskNotFoundError(
                f"Task '{task_id}' version '{version}' not found"
            )
        self._stable_versions[task_id] = version
    
    def unregister(self, task_id: str, version: Optional[str] = None) -> None:
        """
        태스크를 레지스트리에서 제거합니다.
        
        Args:
            task_id: 태스크 ID
            version: 제거할 버전 (None이면 모든 버전 제거)
        
        Raises:
            TaskNotFoundError: 태스크를 찾을 수 없을 때
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(f"Task '{task_id}' not found in registry")
        
        if version is None:
            # 모든 버전 제거
            del self._tasks[task_id]
            if task_id in self._stable_versions:
                del self._stable_versions[task_id]
        else:
            # 특정 버전만 제거
            if version not in self._tasks[task_id]:
                raise TaskNotFoundError(
                    f"Task '{task_id}' version '{version}' not found"
                )
            del self._tasks[task_id][version]
            
            # 버전이 하나도 없으면 task_id도 제거
            if not self._tasks[task_id]:
                del self._tasks[task_id]
                if task_id in self._stable_versions:
                    del self._stable_versions[task_id]
            
            # stable 버전이었다면 제거
            elif task_id in self._stable_versions and self._stable_versions[task_id] == version:
                del self._stable_versions[task_id]


# 전역 레지스트리 인스턴스
_global_registry = TaskRegistry()


def get_global_registry() -> TaskRegistry:
    """전역 레지스트리 인스턴스를 반환합니다."""
    return _global_registry


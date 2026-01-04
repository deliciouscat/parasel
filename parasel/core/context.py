"""Context 객체: 파이프라인 실행 중 args/context를 공유하는 딕셔너리 래퍼"""

from typing import Any, Dict, Optional, Set
from threading import RLock


class Context:
    """
    파이프라인 실행 중 공유되는 컨텍스트 객체.
    
    dict 유사 인터페이스를 제공하며, 병렬 실행 시 thread-safe 옵션을 지원합니다.
    각 모듈은 context에 입력을 읽고 출력을 씁니다.
    """
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None, thread_safe: bool = False):
        """
        Args:
            initial_data: 초기 데이터 딕셔너리
            thread_safe: True면 RLock으로 thread-safe 보장
        """
        self._data: Dict[str, Any] = initial_data.copy() if initial_data else {}
        self._thread_safe = thread_safe
        self._lock = RLock() if thread_safe else None
        self._accessed_keys: Set[str] = set()
        self._written_keys: Set[str] = set()
    
    def get(self, key: str, default: Any = None) -> Any:
        """키에 해당하는 값을 반환합니다."""
        if self._thread_safe and self._lock:
            with self._lock:
                self._accessed_keys.add(key)
                return self._data.get(key, default)
        else:
            self._accessed_keys.add(key)
            return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """키에 값을 설정합니다."""
        if self._thread_safe and self._lock:
            with self._lock:
                self._data[key] = value
                self._written_keys.add(key)
        else:
            self._data[key] = value
            self._written_keys.add(key)
    
    def __getitem__(self, key: str) -> Any:
        """딕셔너리 스타일 읽기"""
        if self._thread_safe and self._lock:
            with self._lock:
                self._accessed_keys.add(key)
                return self._data[key]
        else:
            self._accessed_keys.add(key)
            return self._data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """딕셔너리 스타일 쓰기"""
        if self._thread_safe and self._lock:
            with self._lock:
                self._data[key] = value
                self._written_keys.add(key)
        else:
            self._data[key] = value
            self._written_keys.add(key)
    
    def __contains__(self, key: str) -> bool:
        """in 연산자 지원"""
        if self._thread_safe and self._lock:
            with self._lock:
                return key in self._data
        else:
            return key in self._data
    
    def keys(self):
        """모든 키 반환"""
        if self._thread_safe and self._lock:
            with self._lock:
                return self._data.keys()
        else:
            return self._data.keys()
    
    def values(self):
        """모든 값 반환"""
        if self._thread_safe and self._lock:
            with self._lock:
                return self._data.values()
        else:
            return self._data.values()
    
    def items(self):
        """모든 키-값 쌍 반환"""
        if self._thread_safe and self._lock:
            with self._lock:
                return self._data.items()
        else:
            return self._data.items()
    
    def update(self, other: Dict[str, Any]) -> None:
        """다른 딕셔너리로 업데이트"""
        if self._thread_safe and self._lock:
            with self._lock:
                self._data.update(other)
                self._written_keys.update(other.keys())
        else:
            self._data.update(other)
            self._written_keys.update(other.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """내부 데이터를 딕셔너리로 복사해 반환"""
        if self._thread_safe and self._lock:
            with self._lock:
                return self._data.copy()
        else:
            return self._data.copy()
    
    def accumulate(self, key: str, value: Any) -> None:
        """
        키에 값을 누적합니다 (원자적 연산).
        
        - 키가 없으면 [value]로 초기화
        - 키가 있고 리스트면 value를 추가
        - 키가 있고 리스트가 아니면 [기존값, value]로 변환
        
        병렬 실행에서 결과를 안전하게 누적할 때 사용합니다.
        """
        if self._thread_safe and self._lock:
            with self._lock:
                self._accumulate_impl(key, value)
        else:
            self._accumulate_impl(key, value)
    
    def _accumulate_impl(self, key: str, value: Any) -> None:
        """누적 연산의 실제 구현"""
        current = self._data.get(key)
        if current is None:
            self._data[key] = [value]
        elif isinstance(current, list):
            current.append(value)
        else:
            self._data[key] = [current, value]
        self._written_keys.add(key)
    
    def get_accessed_keys(self) -> Set[str]:
        """실행 중 접근된 키들 반환 (디버깅/검증용)"""
        return self._accessed_keys.copy()
    
    def get_written_keys(self) -> Set[str]:
        """실행 중 쓰여진 키들 반환 (디버깅/검증용)"""
        return self._written_keys.copy()
    
    def __repr__(self) -> str:
        return f"Context(keys={list(self._data.keys())}, thread_safe={self._thread_safe})"


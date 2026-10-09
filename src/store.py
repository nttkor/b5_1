"""LRU 캐시 축출 및 TTL 만료를 지원하는 인메모리 Key-Value 저장소 엔진.

본 모듈은 세 가지 핵심 자료구조(HashMap, DoublyLinkedList, MinHeap)를 유기적으로 결합하여
Redis의 핵심 기능인 인메모리 Key-Value 캐시 저장소를 구현합니다.

자료구조 시너지 및 아키텍처:
    1. HashMap:
       - `key -> Entry` 매핑을 평균 O(1) 시간에 조회/삽입/삭제합니다.
    2. DoublyLinkedList (LRU 순서 관리):
       - 캐시의 접근 순서를 기록합니다.
       - 리스트의 맨 앞(_head 직후)은 가장 최근에 참조된(MRU: Most Recently Used) 키를 배치합니다.
       - 리스트의 맨 뒤(_tail 직전)는 가장 오랫동안 참조되지 않은(LRU: Least Recently Used) 키가 위치합니다.
       - Entry 객체가 자신의 LRU Node 참조(`entry.lru_node`)를 직접 보유하므로,
         노드 재배치(`move_to_front`) 및 임의 노드 삭제(`remove_node`)가 O(1)에 완료됩니다.
    3. MinHeap (TTL 만료 우선순위 큐):
       - `(expire_at, key, version)` 튜플을 첫 번째 원소인 만료 타임스탬프 기준으로 정렬합니다.
       - 힙은 임의 인덱스 삭제가 O(n)으로 비효율적이므로, 지연 삭제(Lazy Deletion) 기법을 사용합니다.
       - 키의 TTL이 변경되거나 덮어쓰여질 때 `entry.ttl_version`을 1씩 증가시켜 이전 힙 예약을 무효화하고,
         `_sweep_expired` 호출 시 만료 타임스탬프와 버전이 일치하는 항목만 실제로 제거합니다.
    4. 메모리 관리 및 LRU 축출 (Eviction):
       - `used_memory = sum( len(utf8(key)) + len(utf8(value)) )` 공식을 엄격히 준수합니다.
       - `maxmemory > 0` 설정 시, 단일 항목의 크기가 `maxmemory`를 초과하면 즉시 OOMError를 발생시킵니다.
       - 신규 저장 후 `used_memory > maxmemory`인 경우 `used_memory <= maxmemory`가 될 때까지
         LRU 꼬리(tail.prev)의 키를 순차적으로 추출하여 메모리를 확보하고 `evicted_keys`를 카운트합니다.
"""

import time	# 고해상도 단조 시계(monotonic clock) 측정을 위한 time 모듈 임포트

from .doubly_linked_list import DoublyLinkedList	# LRU 순서 추적용 이중 연결 리스트 클래스 임포트
from .hashmap import HashMap	# O(1) Key-Value 조회를 위한 체이닝 해시맵 클래스 임포트
from .heap import MinHeap	# 빠른 만료 시각 탐색을 위한 최소 힙 클래스 임포트


class OOMError(Exception):	# 메모리 한도 초과 예외 클래스 정의
    """단일 엔트리 자체의 크기가 maxmemory 한도를 초과할 때 발생하는 Out-Of-Memory 예외."""

    pass	# 예외 식별을 위한 패스 선언


class Entry:	# 개별 키에 매핑되는 메타데이터 엔트리 클래스 정의
    """저장소 내 개별 키의 값과 LRU/TTL 메타데이터를 보관하는 엔트리 클래스.

    Attributes:
        value (str): 키에 매핑된 실제 문자열 값.
        size (int): 키와 값의 UTF-8 바이트 크기 총합.
        lru_node (Node or None): LRU 이중 연결 리스트에서 해당 키를 담고 있는 노드 객체.
        expire_at (float or None): 만료 시각(time.monotonic 기준), 미설정 시 None.
        ttl_version (int): TTL 변경/갱신/무효화 여부를 추적하기 위한 버전 카운터.
    """

    __slots__ = ("value", "size", "lru_node", "expire_at", "ttl_version")	# 메모리 최적화를 위한 슬롯 속성 지정

    def __init__(self, value, size):	# 엔트리 초기화 생성자 정의
        """Entry 인스턴스를 초기화합니다.

        Args:
            value (str): 저장할 문자열 값.
            size (int): 키와 값의 UTF-8 바이트 합계 크기.
        """
        self.value = value	# 문자열 값 저장
        self.size = size	# 바이트 크기 저장
        self.lru_node = None	# LRU 노드 참조를 None으로 초기화
        self.expire_at = None	# 만료 시각을 None으로 초기화 (기본 영구 보관)
        self.ttl_version = 0	# 지연 삭제 판별용 TTL 버전을 0으로 초기화


class MiniRedisStore:	# 미니 레디스 인메모리 저장소 핵심 엔진 클래스 정의
    """해시맵, 이중 연결 리스트, 최소 힙을 결합한 통합 Mini Redis 저장소 엔진.

    Attributes:
        _map (HashMap): 키 문자열을 Entry 객체로 매핑하는 체이닝 해시맵.
        _lru (DoublyLinkedList): 최근 사용(MRU)부터 오래된(LRU) 순서로 키를 관리하는 연결 리스트.
        _ttl_heap (MinHeap): (expire_at, key, version) 튜플을 정렬 보관하는 최소 힙 우선순위 큐.
        used_memory (int): 현재 저장된 키와 값들의 UTF-8 바이트 총합 (메모리 사용량).
        maxmemory (int): 허용된 최대 메모리 용량 (0인 경우 무제한).
        evicted_keys (int): 메모리 초과로 인해 LRU 정책에 의해 축출된 키의 누적 개수.
    """

    def __init__(self):	# 저장소 엔진 초기화 생성자 정의
        """저장소의 각 자료구조와 상태 변수를 초기화합니다."""
        self._map = HashMap()	# O(1) Key-Entry 조회를 위한 해시맵 인스턴스 생성
        self._lru = DoublyLinkedList()	# O(1) LRU 순서 갱신을 위한 이중 연결 리스트 인스턴스 생성
        self._ttl_heap = MinHeap()	# 빠른 만료 키 조회를 위한 최소 힙 인스턴스 생성
        self.used_memory = 0	# 현재 사용 중인 바이트 메모리 총량을 0으로 초기화
        self.maxmemory = 0	# 최대 메모리 제한(0: 무제한)을 0으로 초기화
        self.evicted_keys = 0	# LRU로 축출된 누적 키 개수를 0으로 초기화

    @staticmethod	# 정적 메서드 데코레이터 지정
    def _entry_size(key, value):	# 키와 값의 UTF-8 바이트 총합을 계산하는 정적 메서드 정의
        """키와 값의 UTF-8 바이트 크기 총합을 계산합니다.

        공식: len(utf8(key)) + len(utf8(value))

        Args:
            key (str): 키 문자열.
            value (str): 값 문자열.

        Returns:
            int: 두 문자열의 UTF-8 인코딩 바이트 합계 크기.
        """
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))	# UTF-8 인코딩 바이트 길이들의 합 반환

    def _get_entry(self, key):	# 해시맵에서 키에 매핑된 Entry 객체를 안전하게 조회하는 내부 메서드 정의
        """해시맵에서 key에 매핑된 Entry를 조회하며, 미존재 시 None을 반환합니다.

        Args:
            key (str): 조회할 키 문자열.

        Returns:
            Entry or None: 매핑된 Entry 객체 또는 미존재 시 None.
        """
        try:	# 해시맵 get 시도 예외 블록 시작
            return self._map.get(key)	# 해시맵에서 키에 해당하는 Entry 조회 및 반환
        except KeyError:	# 키가 존재하지 않아 KeyError가 발생한 경우
            return None	# None 반환

    def _sweep_expired(self, now):	# 힙을 기반으로 만료 시각이 경과한 키들을 실제로 정리하는 내부 메서드 정의
        """현재 시각(now) 이전에 만료된 항목들을 힙에서 꺼내어 실제로 삭제합니다 (지연 삭제).

        힙 top의 expire_at이 현재 시각 이하인 동안 반복해서 꺼내며,
        엔트리의 expire_at 및 ttl_version이 일치하는 경우에만 유효한 만료로 간주하여 _purge합니다.

        Args:
            now (float): 현재 단조 시계 타임스탬프.
        """
        while self._ttl_heap.size() > 0 and self._ttl_heap.peek()[0] <= now:	# 힙에 원소가 있고 최상단 항목이 현재 시각 이하인 동안 반복
            expire_at, key, version = self._ttl_heap.pop()	# 최상단 만료 예약 튜플 추출
            entry = self._get_entry(key)	# 해당 키의 실제 엔트리 객체 조회
            if entry is not None and entry.expire_at == expire_at and entry.ttl_version == version:	# 엔트리가 존재하고 타임스탬프와 버전이 일치하는 경우
                self._purge(key, entry)	# 해당 키와 엔트리를 모든 자료구조에서 영구 정리

    def _purge(self, key, entry):	# 키와 엔트리를 HashMap, LRU, 메모리 통계에서 완전히 제거하는 내부 메서드 정의
        """키와 엔트리를 모든 자료구조(해시맵, LRU 리스트) 및 메모리 카운트에서 완전히 제거합니다.

        Args:
            key (str): 제거할 키 문자열.
            entry (Entry): 제거할 엔트리 객체.
        """
        self._map.remove(key)	# 해시맵에서 키-값 엔트리 제거
        self._lru.remove_node(entry.lru_node)	# LRU 이중 연결 리스트에서 해당 노드 분리 제거
        self.used_memory -= entry.size	# 현재 메모리 사용량에서 엔트리 크기 차감

    def _touch_lru(self, entry, key):	# 엔트리를 LRU 리스트의 맨 앞(MRU)으로 이동시키는 내부 메서드 정의
        """엔트리를 LRU 리스트의 맨 앞(_head 직후)으로 이동시켜 최신 사용 상태로 갱신합니다.

        Args:
            entry (Entry): LRU 노드를 갱신할 엔트리 객체.
            key (str): 엔트리에 대응하는 키 문자열.
        """
        if entry.lru_node is None:	# 최초 삽입되어 LRU 노드가 연결되지 않은 경우
            entry.lru_node = self._lru.insert_front(key)	# LRU 리스트 맨 앞에 노드를 생성하여 연결
        else:	# 이미 LRU 노드가 존재하는 경우
            self._lru.move_to_front(entry.lru_node)	# 기존 노드를 리스트 맨 앞으로 O(1) 이동

    def set(self, key, value):	# 키와 값을 저장하고 LRU 및 메모리를 갱신하는 메서드 정의
        """키에 값을 저장하고 LRU 위치를 최신화하며 메모리 한도 초과 시 LRU 축출을 수행합니다.

        기존 키를 덮어쓰는 경우 기존 TTL은 초기화(삭제)되며 버전이 올라갑니다.
        단일 엔트리 크기가 maxmemory를 초과하면 저장을 취소하고 OOMError를 발생시킵니다.

        Args:
            key (str): 저장할 대상 키.
            value (str): 저장할 대상 문자열 값.

        Raises:
            OOMError: maxmemory > 0 상태에서 단일 엔트리 크기 자체가 maxmemory를 초과할 경우 발생.
        """
        now = time.monotonic()	# 현재 단조 시계 타임스탬프 측정
        self._sweep_expired(now)	# 이미 만료된 항목들을 사전에 정리하여 메모리 확보
        size = self._entry_size(key, value)	# 새 엔트리의 키+값 UTF-8 바이트 크기 계산
        if self.maxmemory > 0 and size > self.maxmemory:	# 단일 엔트리 크기 자체가 maxmemory 제한을 초과하는지 검사
            raise OOMError()	# 메모리 한도 초과 예외 발생

        entry = self._get_entry(key)	# 동일한 키가 이미 존재하는지 해시맵에서 조회
        if entry is not None:	# 이미 키가 존재하는 경우 (덮어쓰기)
            self.used_memory -= entry.size	# 기존 엔트리의 바이트 크기를 메모리 사용량에서 차감
            entry.value = value	# 새 값으로 교체
            entry.size = size	# 새 크기로 교체
            entry.expire_at = None	# 덮어쓰기 시 기존 TTL 정보 초기화
            entry.ttl_version += 1	# 기존 힙 예약을 무효화하기 위해 TTL 버전 증가
            self.used_memory += size	# 새 엔트리의 바이트 크기를 메모리 사용량에 가산
            self._touch_lru(entry, key)	# LRU 리스트의 맨 앞으로 이동하여 최신 사용 갱신
        else:	# 새로운 키인 경우
            entry = Entry(value, size)	# 새 Entry 인스턴스 생성
            self._map.put(key, entry)	# 해시맵에 키와 새 Entry 등록
            self.used_memory += size	# 새 엔트리의 바이트 크기를 메모리 사용량에 가산
            self._touch_lru(entry, key)	# LRU 리스트의 맨 앞에 노드 삽입 및 연결

        self._evict_if_needed()	# maxmemory 초과 여부를 확인하고 필요시 LRU 축출 수행

    def _evict_if_needed(self):	# 메모리 초과 시 가장 오래된 키들을 LRU 순서로 축출하는 내부 메서드 정의
        """maxmemory 초과 시 used_memory <= maxmemory가 될 때까지 가장 오래된 키를 축출합니다.

        축출된 키는 LRU 리스트의 tail.prev에서 제거되며,
        해시맵에서 제거되고 evicted_keys 카운트가 1 증가합니다.
        """
        while self.maxmemory > 0 and self.used_memory > self.maxmemory and len(self._lru) > 0:	# 메모리가 초과되고 축출 가능한 키가 남아있는 동안 반복
            victim_key = self._lru.remove_back()	# LRU 리스트의 맨 뒤(가장 오래 사용되지 않은 키) 노드 제거 및 키 취득
            victim = self._get_entry(victim_key)	# 축출 대상 키의 엔트리 객체 조회
            if victim is None:	# 만약 엔트리가 존재하지 않는 경우 (예외 방어)
                continue	# 다음 반복으로 진행
            self._map.remove(victim_key)	# 해시맵에서 축출 대상 키 제거
            self.used_memory -= victim.size	# 축출된 엔트리의 크기만큼 메모리 사용량 차감
            self.evicted_keys += 1	# 누적 축출 키 개수 1 증가

    def get(self, key):	# 키의 값을 조회하고 성공 시 LRU를 갱신하는 메서드 정의
        """키에 매핑된 값을 조회합니다.

        키가 만료된 경우 먼저 삭제 처리 후 None을 반환하며 LRU를 갱신하지 않습니다.
        키가 유효하게 존재하는 경우에만 LRU 위치를 최신화하고 값을 반환합니다.

        Args:
            key (str): 조회할 키 문자열.

        Returns:
            str or None: 저장된 문자열 값 또는 미존재/만료 시 None.
        """
        now = time.monotonic()	# 현재 단조 시계 타임스탬프 측정
        self._sweep_expired(now)	# 만료된 키들을 정리
        entry = self._get_entry(key)	# 해시맵에서 엔트리 객체 조회
        if entry is None:	# 키가 존재하지 않거나 만료되어 삭제된 경우
            return None	# None 반환
        self._touch_lru(entry, key)	# 조회가 성공한 경우에만 LRU 리스트 맨 앞으로 이동
        return entry.value	# 보관 중인 문자열 값 반환

    def delete(self, key):	# 키와 연관된 모든 데이터를 삭제하는 메서드 정의
        """지정된 키를 데이터, LRU 리스트, 메모리 통계에서 완전히 삭제합니다.

        Args:
            key (str): 삭제할 대상 키 문자열.

        Returns:
            bool: 키가 존재하여 성공적으로 삭제되었으면 True, 없었으면 False.
        """
        now = time.monotonic()	# 현재 단조 시계 타임스탬프 측정
        self._sweep_expired(now)	# 만료된 키들을 먼저 정리
        entry = self._get_entry(key)	# 해시맵에서 엔트리 객체 조회
        if entry is None:	# 삭제할 키가 존재하지 않는 경우
            return False	# 삭제 실패(False) 반환
        self._purge(key, entry)	# 키와 엔트리를 모든 자료구조에서 영구 정리
        return True	# 삭제 성공(True) 반환

    def exists(self, key):	# 키의 존재 여부를 확인하는 메서드 정의
        """키가 현재 저장소에 유효하게 존재하는지 여부를 확인합니다.

        만료된 키는 사전에 sweep 처리되어 존재하지 않는 것으로 판별됩니다.

        Args:
            key (str): 존재 여부를 확인할 키 문자열.

        Returns:
            bool: 키가 존재하면 True, 없으면 False.
        """
        self._sweep_expired(time.monotonic())	# 만료된 키들을 먼저 정리
        return self._map.contains(key)	# 해시맵 내 키 존재 여부 반환

    def dbsize(self):	# 유효한 총 키 개수를 반환하는 메서드 정의
        """저장소에 보관된 현재 유효한 총 키의 개수를 반환합니다.

        Returns:
            int: 유효한 키의 개수.
        """
        self._sweep_expired(time.monotonic())	# 만료된 키들을 먼저 정리
        return self._map.size()	# 해시맵의 총 엔트리 크기 반환

    def keys(self):	# 모든 유효한 키의 목록을 반환하는 메서드 정의
        """현재 저장소에 존재하는 모든 키들의 목록을 반환합니다.

        Returns:
            list[str]: 저장된 전체 키 문자열의 리스트.
        """
        self._sweep_expired(time.monotonic())	# 만료된 키들을 먼저 정리
        return self._map.keys()	# 해시맵의 전체 키 리스트 반환

    def expire(self, key, seconds):	# 키의 만료 시각(TTL)을 설정하는 메서드 정의
        """키의 만료 시간(초 단위)을 설정합니다.

        키가 없으면 False를 반환합니다.
        seconds가 0 이하이면 즉시 만료로 처리하여 즉시 삭제하고 True를 반환합니다.
        양수이면 expire_at을 계산하고 버전을 증가시킨 뒤 최소 힙에 예약합니다.

        Args:
            key (str): 만료 시간을 설정할 대상 키.
            seconds (int): 남은 유효 시간 (초 단위).

        Returns:
            bool: 만료 시간 설정 또는 즉시 삭제에 성공하면 True, 키가 없으면 False.
        """
        now = time.monotonic()	# 현재 단조 시계 타임스탬프 측정
        self._sweep_expired(now)	# 이미 만료된 키들을 먼저 정리
        entry = self._get_entry(key)	# 대상 키의 엔트리 객체 조회
        if entry is None:	# 대상 키가 존재하지 않는 경우
            return False	# 설정 실패(False) 반환
        if seconds <= 0:	# 만료 시간이 0 이하인 경우 (즉시 만료)
            self._purge(key, entry)	# 해당 키를 즉시 저장소에서 영구 삭제
            return True	# 성공(True) 반환
        entry.expire_at = now + seconds	# 만료 절대 시각(현재 시각 + 초) 계산 및 엔트리에 기록
        entry.ttl_version += 1	# 이전 힙 예약을 무효화하기 위해 TTL 버전 1 증가
        self._ttl_heap.push((entry.expire_at, key, entry.ttl_version))	# (만료시각, 키, 버전) 튜플을 최소 힙에 추가
        return True	# 성공(True) 반환

    def ttl(self, key):	# 키의 남은 유효 시간(초)을 조회하는 메서드 정의
        """키의 남은 만료 시간(초 단위 정수)을 조회합니다.

        규칙:
            - 키가 존재하지 않거나 만료된 경우: -2
            - 키는 존재하지만 만료 시간이 설정되지 않은 경우: -1
            - 만료 시간이 설정된 경우: 남은 초(int) 반환

        Args:
            key (str): TTL을 조회할 대상 키.

        Returns:
            int: -2 (키 없음), -1 (만료시간 없음), 또는 남은 초 (>= 0).
        """
        now = time.monotonic()	# 현재 단조 시계 타임스탬프 측정
        self._sweep_expired(now)	# 만료된 키들을 먼저 정리
        entry = self._get_entry(key)	# 대상 키의 엔트리 객체 조회
        if entry is None:	# 키가 존재하지 않는 경우
            return -2	# -2 반환
        if entry.expire_at is None:	# 키는 존재하나 만료 시간이 설정되지 않은 경우
            return -1	# -1 반환
        return int(entry.expire_at - now)	# 남은 초를 정수형으로 반환

"""체이닝 방식 해시맵 (Chaining Hash Map) 모듈.

본 모듈은 Python의 내장 딕셔너리(`dict`), 집합(`set`), 컬렉션(`collections`) 모듈을
일체 사용하지 않고 밑바닥부터 직접 구현한 순수 체이닝 해시맵입니다.

주요 특징 및 아키텍처:
    1. 고정 인덱스 버킷 배열:
       - 고정 길이의 파이썬 리스트(`list`)를 버킷 배열로 사용하며, 각 버킷은 고유 인덱스로 접근합니다.
    2. 체이닝(Separate Chaining) 충돌 해결:
       - 동일 버킷 인덱스로 해시 충돌이 발생하는 경우, 앞서 구현한 `DoublyLinkedList`를 버킷 체인으로
         재사용하여 충돌된 `_Pair(key, value)` 노드들을 연결 관리합니다.
    3. djb2 다항 롤링 해시 함수:
       - 소수 5381과 비트 시프트 연산(`(h * 33) + ord(ch)`)을 활용하여 문자열 키의 해시 분포를
         균등하게 분산시키고 32비트 정수 마스킹(`0xFFFFFFFF`)을 적용합니다.
    4. 동적 리사이징 (Dynamic Resizing & Rehashing):
       - 로드 팩터(Load Factor = 저장된 항목 수 / 버킷 수)가 임계값 0.75를 초과하면
         버킷 용량을 2배로 확장하고 기존 모든 키-값 쌍을 새 버킷 배열에 재해싱하여 재배치합니다.
         이를 통해 평균 O(1) 시간 복잡도를 지속적으로 유지합니다.
"""

from .doubly_linked_list import DoublyLinkedList	# 체이닝 버킷 구현을 위한 이중 연결 리스트 모듈 임포트

_LOAD_FACTOR_LIMIT = 0.75	# 버킷 리사이징 임계 로드 팩터 (75% 도달 시 2배 확장)
_MISSING = object()	# get 메서드 호출 시 기본값 미지정 여부를 판별하기 위한 고유 센티넬 객체


def _hash_key(key, capacity):	# 문자열 키와 버킷 크기를 입력받아 버킷 인덱스를 계산하는 함수 정의
    """djb2 알고리즘 기반으로 문자열 키의 버킷 인덱스를 계산합니다.

    문자열의 각 문자를 순회하며 이전 해시값에 33을 곱하고 유니코드 코드포인트를 더합니다.
    결과를 32비트 부호 없는 정수 범위로 제한한 후, 현재 버킷 용량(capacity)으로
    나눈 나머지를 반환하여 균등한 분포를 형성합니다.

    Args:
        key (str): 해시할 문자열 키.
        capacity (int): 현재 해시맵의 버킷 배열 크기.

    Returns:
        int: 0 이상 capacity 미만의 유효한 버킷 배열 인덱스.
    """
    h = 5381	# djb2 알고리즘의 표준 초기 소수값(매직 넘버) 설정
    for ch in key:	# 키 문자열의 각 문자를 순차적으로 순회
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF	# 33을 곱하고 문자 아스키 코드를 더한 뒤 32비트로 마스킹
    return h % capacity	# 버킷 개수로 모듈러 연산하여 0 ~ (capacity - 1) 범위의 인덱스 반환


class _Pair:	# 해시맵 버킷 체인 내에 키와 값을 함께 보관하기 위한 내부 쌍 클래스 정의
    """해시맵의 개별 버킷 내 체인에 저장되는 키-값 쌍 구조체.

    Attributes:
        key: 저장할 키 식별자.
        value: 키에 매핑되는 실제 데이터 객체.
    """

    __slots__ = ("key", "value")	# 메모리 오버헤드 최소화를 위한 슬롯 정의

    def __init__(self, key, value):	# 키-값 쌍 생성자 정의
        """_Pair 인스턴스를 초기화합니다.

        Args:
            key: 매핑할 키 객체.
            value: 매핑할 값 객체.
        """
        self.key = key	# 키 속성 저장
        self.value = value	# 값 속성 저장


class HashMap:	# 체이닝 및 동적 2배 확장을 지원하는 해시맵 클래스 정의
    """체이닝 방식과 동적 리사이징을 구현한 고성능 인메모리 해시맵.

    내장 딕셔너리 없이 리스트 버킷과 DoublyLinkedList 체인을 결합하여
    평균 O(1) 시간 복잡도로 put, get, remove, contains 연산을 지원합니다.

    Attributes:
        _capacity (int): 현재 할당된 총 버킷 배열의 크기.
        _buckets (list[DoublyLinkedList]): 각 버킷마다 생성된 이중 연결 리스트 체인들의 배열.
        _size (int): 해시맵에 저장된 총 키-값 쌍의 개수.
    """

    def __init__(self, capacity=8):	# 해시맵 생성자 정의 (기본 용량: 8)
        """해시맵을 초기화하고 지정된 용량의 버킷 배열을 할당합니다.

        Args:
            capacity (int): 초기 버킷 배열의 크기 (기본값: 8).
        """
        self._capacity = capacity	# 초기 버킷 수 저장
        self._buckets = [DoublyLinkedList() for _ in range(capacity)]	# 각 버킷마다 독립된 이중 연결 리스트 객체 생성
        self._size = 0	# 저장된 총 키-값 엔트리 개수 0으로 초기화

    def put(self, key, value):	# 키-값 쌍을 저장하거나 기존 키의 값을 갱신하는 메서드 정의
        """지정된 키에 값을 매핑하여 저장합니다.

        이미 키가 존재하는 경우 기존 값을 새 값으로 덮어쓰고,
        키가 없으면 체인의 끝에 새 _Pair를 추가합니다.
        삽입 후 로드 팩터가 0.75를 초과하면 버킷 용량을 2배로 자동 확장합니다.

        Args:
            key (str): 저장할 대상 키.
            value: 키에 연결하여 저장할 대상 값.
        """
        idx = _hash_key(key, self._capacity)	# 키에 대한 버킷 인덱스 계산
        for pair in self._buckets[idx]:	# 해당 버킷 체인의 모든 키-값 쌍을 순회
            if pair.key == key:	# 동일한 키가 이미 존재하는 경우
                pair.value = value	# 기존 값을 새 값으로 업데이트
                return	# 메서드 종료
        self._buckets[idx].insert_back(_Pair(key, value))	# 체인의 맨 뒤에 새로운 키-값 Pair 노드 삽입
        self._size += 1	# 저장된 총 엔트리 개수 1 증가
        if self._size / self._capacity > _LOAD_FACTOR_LIMIT:	# 현재 로드 팩터가 임계값 0.75를 초과하는지 검사
            self._resize(self._capacity * 2)	# 버킷 용량을 2배로 확장하고 전체 재해싱 수행

    def get(self, key, default=_MISSING):	# 키에 매핑된 값을 조회하는 메서드 정의
        """지정된 키에 매핑된 값을 조회하여 반환합니다.

        Args:
            key (str): 조회할 대상 키.
            default: 키가 존재하지 않을 때 반환할 기본값. 지정하지 않으면 KeyError 발생.

        Returns:
            Any: 키에 매핑된 값 또는 default 값.

        Raises:
            KeyError: 키가 존재하지 않고 default가 지정되지 않은 경우 발생.
        """
        idx = _hash_key(key, self._capacity)	# 키에 대한 버킷 인덱스 계산
        for pair in self._buckets[idx]:	# 해당 버킷 체인 내의 항목 순회
            if pair.key == key:	# 일치하는 키를 발견한 경우
                return pair.value	# 매핑된 값 반환
        if default is _MISSING:	# 일치하는 키가 없고 default가 지정되지 않은 경우
            raise KeyError(key)	# KeyError 예외 발생
        return default	# 지정된 기본값 반환

    def contains(self, key):	# 키의 존재 여부를 확인하는 메서드 정의
        """지정된 키가 해시맵 내에 존재하는지 여부를 O(1) 평균 시간으로 검사합니다.

        Args:
            key (str): 존재 여부를 확인할 키.

        Returns:
            bool: 키가 존재하면 True, 없으면 False.
        """
        idx = _hash_key(key, self._capacity)	# 키에 대한 버킷 인덱스 계산
        for pair in self._buckets[idx]:	# 해당 버킷 체인 순회
            if pair.key == key:	# 일치하는 키를 발견한 경우
                return True	# 존재함(True) 반환
        return False	# 존재하지 않음(False) 반환

    def remove(self, key):	# 키-값 엔트리를 해시맵에서 삭제하는 메서드 정의
        """지정된 키와 연결된 엔트리를 해시맵에서 제거합니다.

        버킷의 DoublyLinkedList에서 nodes() 제너레이터를 사용하여
        일치하는 노드를 찾아 O(1)로 제거합니다.

        Args:
            key (str): 삭제할 대상 키.

        Returns:
            bool: 삭제에 성공하면 True, 키가 없었으면 False.
        """
        idx = _hash_key(key, self._capacity)	# 키에 대한 버킷 인덱스 계산
        bucket = self._buckets[idx]	# 해당 인덱스의 버킷(DoublyLinkedList) 참조 취득
        for node in bucket.nodes():	# 버킷 체인 내의 Node 객체들을 안전하게 순회
            if node.data.key == key:	# 노드의 데이터 키가 삭제 대상 키와 일치하는 경우
                bucket.remove_node(node)	# 이중 연결 리스트에서 해당 노드를 O(1)로 분리 제거
                self._size -= 1	# 저장된 총 엔트리 개수 1 감소
                return True	# 삭제 성공(True) 반환
        return False	# 삭제 대상 키 없음(False) 반환

    def keys(self):	# 저장된 모든 키를 리스트로 수집하여 반환하는 메서드 정의
        """해시맵에 저장된 모든 키의 목록을 리스트로 반환합니다.

        Returns:
            list[str]: 저장된 전체 키들의 리스트 (순서는 보장되지 않음).
        """
        result = []	# 키를 담을 새 결과 리스트 생성
        for bucket in self._buckets:	# 모든 버킷을 순차적으로 순회
            for pair in bucket:	# 각 버킷 체인 내의 모든 키-값 쌍 순회
                result.append(pair.key)	# 키 값을 결과 리스트에 추가
        return result	# 전체 키 목록 리스트 반환

    def size(self):	# 저장된 총 엔트리 개수를 반환하는 메서드 정의
        """현재 해시맵에 저장된 키-값 쌍의 총 개수를 O(1)로 반환합니다.

        Returns:
            int: 저장된 총 엔트리 개수.
        """
        return self._size	# 유지 중인 크기 변수 반환

    def _resize(self, new_capacity):	# 버킷 배열을 새 용량으로 확장하고 전체 재해싱을 수행하는 내부 메서드 정의
        """버킷 배열 크기를 new_capacity로 확장하고 모든 기존 데이터를 재해싱하여 재배치합니다.

        로드 팩터가 임계값을 넘을 때 호출되어 체인 길이를 짧게 유지함으로써
        해시맵의 조회/삽입 성능이 O(1)을 유지하도록 보장합니다.

        Args:
            new_capacity (int): 새로 확장할 버킷 배열의 크기.
        """
        old_buckets = self._buckets	# 기존 버킷 배열에 대한 참조 보관
        self._buckets = [DoublyLinkedList() for _ in range(new_capacity)]	# 새 용량 크기의 빈 버킷 배열 새로 생성
        self._capacity = new_capacity	# 버킷 용량 변수 갱신
        for bucket in old_buckets:	# 기존의 모든 버킷을 순회
            for pair in bucket:	# 기존 버킷 체인 내의 각 키-값 쌍 순회
                idx = _hash_key(pair.key, new_capacity)	# 새로운 버킷 크기를 기준으로 새 버킷 인덱스 계산
                self._buckets[idx].insert_back(pair)	# 새 버킷 체인의 맨 뒤에 키-값 쌍 재배치

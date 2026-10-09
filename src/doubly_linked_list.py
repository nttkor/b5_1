"""이중 연결 리스트 (Doubly Linked List) 모듈.

본 모듈은 양방향 노드 참조(prev, next)와 센티넬(더미) head/tail 노드를 활용하여
경계 조건(None 검사) 없이 모든 노드의 삽입, 삭제, 이동 연산을 O(1) 시간 복잡도로
수행하는 순수 이중 연결 리스트를 구현합니다.

주요 특징 및 활용:
    1. 센티넬 더미 노드: _head와 _tail 더미 노드를 두어 빈 리스트나 첫 번째/마지막 노드
       처리 시 분기문 없이 균일한 포인터 조작을 보장합니다.
    2. LRU(Least Recently Used) 캐시 순서 추적:
       - 최신 사용 항목은 insert_front 또는 move_to_front를 통해 리스트의 맨 앞(_head 뒤)으로 배치합니다.
       - 가장 오래된 항목은 tail.prev에서 O(1)로 조회하여 remove_back으로 축출(eviction)합니다.
    3. HashMap 체이닝 충돌 해결:
       - 동일 해시 버킷에 매핑된 키-값 쌍(Pair)들을 체인 형태로 보관하고 노드 단위 순회(nodes)를 지원합니다.
"""


class Node:	# 이중 연결 리스트의 기본 단위 노드 클래스 정의
    """이중 연결 리스트의 개별 노드를 표현하는 클래스.

    Attributes:
        data: 노드가 저장하는 실제 데이터 객체 (예: 키 문자열 또는 키-값 Pair).
        prev (Node or None): 리스트 상의 이전 노드를 가리키는 참조 포인터.
        next (Node or None): 리스트 상의 다음 노드를 가리키는 참조 포인터.
    """

    __slots__ = ("data", "prev", "next")	# 속성 접근 속도 향상 및 메모리 최적화를 위해 슬롯 고정

    def __init__(self, data=None):	# 노드 초기화 생성자 정의
        """Node 인스턴스를 초기화합니다.

        Args:
            data: 노드에 보관할 데이터 값 (기본값: None).
        """
        self.data = data	# 전달받은 데이터 객체 저장
        self.prev = None	# 이전 노드에 대한 참조를 None으로 초기화
        self.next = None	# 다음 노드에 대한 참조를 None으로 초기화


class DoublyLinkedList:	# O(1) 양방향 연결 리스트 클래스 정의
    """더미 센티넬 노드를 기반으로 O(1) 삽입/삭제/이동을 보장하는 이중 연결 리스트.

    내부적으로 _head와 _tail 더미 노드를 상시 유지하여,
    헤드 삽입, 테일 삽입, 임의 노드 삭제 및 헤드 이동 연산 시
    별도의 null 분기 처리 없이 일관되게 O(1)에 수행합니다.

    Attributes:
        _head (Node): 리스트의 시작을 나타내는 더미 센티넬 노드.
        _tail (Node): 리스트의 끝을 나타내는 더미 센티넬 노드.
        _size (int): 리스트 내에 저장된 실제 유효 노드의 총 개수.
    """

    def __init__(self):	# 이중 연결 리스트 초기화 생성자 정의
        """센티넬 head와 tail 노드를 연결하고 빈 리스트 상태로 초기화합니다."""
        self._head = Node()	# 더미 head 센티넬 노드 인스턴스 생성
        self._tail = Node()	# 더미 tail 센티넬 노드 인스턴스 생성
        self._head.next = self._tail	# head의 다음 포인터를 tail로 연결
        self._tail.prev = self._head	# tail의 이전 포인터를 head로 연결
        self._size = 0	# 유효 데이터 노드 개수를 0으로 초기화

    def insert_front(self, data):	# 리스트의 맨 앞(head 직후)에 새 데이터를 삽입하는 메서드 정의
        """리스트의 가장 앞부분(_head 직후)에 새 데이터를 담은 노드를 O(1)로 삽입합니다.

        LRU 캐시에서 새로운 키가 삽입되거나 최신 사용 상태로 갱신될 때 호출됩니다.

        Args:
            data: 리스트 맨 앞에 저장할 데이터 객체.

        Returns:
            Node: 새롭게 생성되어 리스트에 연결된 노드 인스턴스.
        """
        node = Node(data)	# 입력받은 데이터를 보관하는 새 노드 객체 생성
        self._link_after(self._head, node)	# 더미 head 노드 바로 뒤에 새 노드를 O(1)로 링크
        self._size += 1	# 리스트의 노드 개수 1 증가
        return node	# 생성 및 삽입된 노드 객체 반환

    def insert_back(self, data):	# 리스트의 맨 뒤(tail 직전)에 새 데이터를 삽입하는 메서드 정의
        """리스트의 가장 뒷부분(_tail 직전)에 새 데이터를 담은 노드를 O(1)로 삽입합니다.

        Args:
            data: 리스트 맨 뒤에 저장할 데이터 객체.

        Returns:
            Node: 새롭게 생성되어 리스트에 연결된 노드 인스턴스.
        """
        node = Node(data)	# 입력받은 데이터를 보관하는 새 노드 객체 생성
        self._link_after(self._tail.prev, node)	# 현재 tail 직전 노드 뒤(즉 tail 앞)에 새 노드를 O(1)로 링크
        self._size += 1	# 리스트의 노드 개수 1 증가
        return node	# 생성 및 삽입된 노드 객체 반환

    def remove_front(self):	# 리스트의 맨 앞(head 직후) 노드를 제거하고 데이터를 반환하는 메서드 정의
        """리스트의 맨 앞 노드를 O(1)로 제거하고 보관된 데이터를 반환합니다.

        Returns:
            Any or None: 제거된 노드의 데이터 객체. 리스트가 비어 있는 경우 None 반환.
        """
        if self._size == 0:	# 리스트가 비어 있는지 확인
            return None	# 비어 있으면 None 반환
        node = self._head.next	# 더미 head 바로 뒤의 첫 번째 실제 노드 참조 취득
        self.remove_node(node)	# 해당 노드를 연결 리스트에서 안전하게 분리 및 제거
        return node.data	# 제거된 노드에 보관되어 있던 데이터 값 반환

    def remove_back(self):	# 리스트의 맨 뒤(tail 직전) 노드를 제거하고 데이터를 반환하는 메서드 정의
        """리스트의 맨 뒤 노드를 O(1)로 제거하고 보관된 데이터를 반환합니다.

        LRU 캐시에서 메모리 초과 시 가장 오래된 항목(victim)을 축출할 때 사용됩니다.

        Returns:
            Any or None: 제거된 노드의 데이터 객체. 리스트가 비어 있는 경우 None 반환.
        """
        if self._size == 0:	# 리스트가 비어 있는지 확인
            return None	# 비어 있으면 None 반환
        node = self._tail.prev	# 더미 tail 바로 앞의 마지막 실제 노드 참조 취득
        self.remove_node(node)	# 해당 노드를 연결 리스트에서 안전하게 분리 및 제거
        return node.data	# 제거된 노드에 보관되어 있던 데이터 값 반환

    def remove_node(self, node):	# 지정된 임의의 노드를 O(1)로 리스트에서 분리하는 메서드 정의
        """주어진 임의의 노드를 리스트에서 O(1)로 분리하여 제거합니다.

        센티넬 노드 구조 덕분에 앞뒤 노드가 항상 존재하므로 경계 조건 검사가 불필요합니다.

        Args:
            node (Node): 리스트에서 제거할 대상 노드 인스턴스.
        """
        node.prev.next = node.next	# 이전 노드의 다음 포인터를 현재 노드의 다음 노드로 연결
        node.next.prev = node.prev	# 다음 노드의 이전 포인터를 현재 노드의 이전 노드로 연결
        node.prev = None	# 참조 해제를 위해 현재 노드의 이전 포인터를 None으로 초기화
        node.next = None	# 참조 해제를 위해 현재 노드의 다음 포인터를 None으로 초기화
        self._size -= 1	# 리스트의 노드 개수 1 감소

    def move_to_front(self, node):	# 지정된 노드를 리스트의 맨 앞(head 직후)으로 이동시키는 메서드 정의
        """기존 노드를 현재 위치에서 분리하여 _head 바로 뒤(맨 앞)로 O(1)에 이동시킵니다.

        LRU 캐시에서 기존 키에 대한 GET 또는 SET 접근이 발생했을 때 최신 사용으로 갱신합니다.

        Args:
            node (Node): 맨 앞으로 이동시킬 대상 노드 인스턴스.
        """
        node.prev.next = node.next	# 노드의 이전 노드와 다음 노드를 직접 맞닿도록 연결
        node.next.prev = node.prev	# 노드의 다음 노드와 이전 노드를 직접 맞닿도록 연결
        self._link_after(self._head, node)	# 센티넬 _head 바로 뒤에 해당 노드를 O(1)로 재연결

    def _link_after(self, anchor, node):	# 기준 노드(anchor) 바로 뒤에 새 노드를 삽입하는 내부 헬퍼 메서드 정의
        """기준 노드(anchor) 바로 뒤에 대상 노드(node)를 O(1)로 연결합니다.

        Args:
            anchor (Node): 기준이 되는 이전 노드.
            node (Node): anchor 뒤에 새로 삽입할 대상 노드.
        """
        node.next = anchor.next	# 대상 노드의 next를 기준 노드의 기존 next로 설정
        node.prev = anchor	# 대상 노드의 prev를 기준 노드로 설정
        anchor.next.prev = node	# 기존 다음 노드의 prev를 새 대상 노드로 연결
        anchor.next = node	# 기준 노드의 next를 새 대상 노드로 연결

    def __len__(self):	# 리스트에 포함된 유효 노드의 총 개수를 반환하는 매직 메서드 정의
        """리스트에 보관된 실제 유효 노드의 총 개수를 반환합니다.

        Returns:
            int: 현재 리스트의 노드 개수 (O(1)).
        """
        return self._size	# 유지 중인 노드 개수 변수 반환

    def __iter__(self):	# 리스트 내 데이터를 순회하기 위한 이터레이터 매직 메서드 정의
        """리스트의 첫 번째 유효 노드부터 마지막 유효 노드까지의 데이터(data)를 순회합니다.

        Yields:
            Any: 각 노드가 보관하고 있는 데이터 객체.
        """
        node = self._head.next	# 첫 번째 실제 유효 노드부터 순회 시작
        while node is not self._tail:	# 더미 tail 센티넬 노드에 도달할 때까지 반복
            yield node.data	# 현재 노드의 데이터 값을 제너레이터로 양도
            node = node.next	# 다음 노드로 포인터 전진

    def nodes(self):	# 리스트 내 Node 객체 자체를 안전하게 순회하는 제너레이터 메서드 정의
        """리스트의 첫 번째 유효 노드부터 마지막 유효 노드까지 Node 객체 자체를 순회합니다.

        순회 도중 노드 제거(remove_node)가 발생해도 다음 노드 추적이 끊기지 않도록
        다음 노드 포인터(nxt)를 사전에 미리 확보한 후 yield합니다.
        (해시맵 버킷 체이닝에서 특정 키의 노드를 찾아 삭제할 때 필수적으로 사용됩니다.)

        Yields:
            Node: 리스트의 개별 노드 인스턴스.
        """
        node = self._head.next	# 첫 번째 실제 유효 노드부터 순회 시작
        while node is not self._tail:	# 더미 tail 센티넬 노드에 도달할 때까지 반복
            nxt = node.next	# 순회 중 노드가 삭제되더라도 순회가 이어지도록 다음 노드 미리 캐싱
            yield node	# 현재 Node 인스턴스 자체를 양도
            node = nxt	# 캐싱해 둔 다음 노드로 포인터 전진

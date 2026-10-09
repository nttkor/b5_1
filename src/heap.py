"""최소 힙 (Min-Heap) 모듈.

본 모듈은 파이썬 표준 라이브러리(`heapq`)나 외부 모듈을 사용하지 않고,
배열(list)을 기반으로 한 완전 이진 트리(Complete Binary Tree) 구조로
직접 구현한 최소 힙(Min-Heap) 우선순위 큐입니다.

주요 특징 및 활용:
    1. 완전 이진 트리의 1차원 배열 매핑:
       - 0번 인덱스를 루트로 사용하며, 임의의 노드 인덱스 `idx`에 대해:
         * 부모 노드 인덱스: `(idx - 1) // 2`
         * 좌측 자식 노드 인덱스: `2 * idx + 1`
         * 우측 자식 노드 인덱스: `2 * idx + 2`
    2. 최소 힙 불변성(Heap Invariant) 유지:
       - 부모 노드의 값은 항상 두 자식 노드의 값보다 작거나 같습니다 (`data[parent] <= data[child]`).
       - 삽입 시 `_heapify_up`을 통해 리프에서 루트 방향으로 O(log n) 상향 이동.
       - 추출 시 `_heapify_down`을 통해 루트에서 리프 방향으로 O(log n) 하향 이동.
    3. TTL(Time-To-Live) 만료 시간 우선순위 관리:
       - `(expire_at, key, version)` 튜플을 요소로 저장하며, 튜플의 첫 번째 원소인
         만료 타임스탬프(`expire_at`)를 기준으로 최소 힙을 정렬합니다.
       - 이를 통해 가장 먼저 만료되는 키를 O(1)에 확인(peek)하고 O(log n)에 제거(pop)할 수 있습니다.
"""


class MinHeap:	# 배열 기반 완전 이진 트리 최소 힙 클래스 정의
    """첫 번째 원소를 기준으로 정렬되는 최소 힙(Min-Heap) 클래스.

    TTL 관리에서 가장 빠른 만료 시각을 가진 항목을 즉시 조회(peek)하고
    순차적으로 추출(pop)하기 위한 우선순위 큐 역할을 담당합니다.

    Attributes:
        _data (list): 힙 트리를 구성하는 1차원 배열 저장소.
    """

    def __init__(self):	# 최소 힙 인스턴스 초기화 생성자 정의
        """빈 리스트를 내부 저장소로 할당하여 최소 힙을 초기화합니다."""
        self._data = []	# 힙 요소를 저장할 내부 리스트 배열 초기화

    def push(self, item):	# 새 요소를 힙에 삽입하고 정렬하는 메서드 정의
        """힙에 새 항목을 추가하고 최소 힙 속성을 유지하도록 정렬합니다.

        항목을 배열의 끝에 추가한 후, 상향 힙화(_heapify_up)를 통해 O(log n)에 제자리를 찾습니다.

        Args:
            item (tuple): 힙에 삽입할 원소 (예: (expire_at, key, version)).
        """
        self._data.append(item)	# 배열의 맨 끝(트리의 마지막 리프 위치)에 새 요소 추가
        self._heapify_up(len(self._data) - 1)	# 새로 추가된 마지막 원소에 대해 상향 힙화 수행

    def pop(self):	# 루트 최솟값을 꺼내고 재정렬하는 메서드 정의
        """힙의 루트(최솟값) 항목을 추출하여 반환하고 남은 요소를 재정렬합니다.

        루트 원소를 꺼낸 뒤 마지막 원소를 루트로 이동시키고,
        하향 힙화(_heapify_down)를 통해 O(log n)에 최소 힙 속성을 복원합니다.

        Returns:
            Any or None: 힙에서 가장 작은 첫 번째 원소를 가진 항목. 힙이 비어 있으면 None 반환.
        """
        if not self._data:	# 힙 배열이 비어 있는지 확인
            return None	# 비어 있으면 None 반환
        top = self._data[0]	# 루트 노드의 최솟값 원소 임시 저장
        last = self._data.pop()	# 배열의 가장 마지막 원소를 추출
        if self._data:	# 아직 배열에 원소가 남아있는 경우
            self._data[0] = last	# 마지막 원소를 루트 위치(0번 인덱스)로 이동
            self._heapify_down(0)	# 루트 위치부터 하향 힙화 수행
        return top	# 추출해 둔 최솟값 원소 반환

    def peek(self):	# 최솟값을 제거하지 않고 단순 조회하는 메서드 정의
        """힙의 최솟값(루트 항목)을 제거하지 않고 확인합니다.

        현재 만료되어 제거 대상인 키가 존재하는지 판단하기 위해 O(1) 시간으로 조회합니다.

        Returns:
            Any or None: 루트 항목. 힙이 비어 있으면 None 반환.
        """
        return self._data[0] if self._data else None	# 데이터가 존재하면 0번 인덱스 반환, 비어있으면 None 반환

    def size(self):	# 힙에 저장된 총 요소 개수를 반환하는 메서드 정의
        """힙에 보관된 총 항목 개수를 반환합니다.

        Returns:
            int: 힙 배열 내의 요소 개수 (O(1)).
        """
        return len(self._data)	# 내부 배열의 길이 반환

    def _heapify_up(self, idx):	# 자식에서 부모 방향으로 거슬러 올라가며 정렬하는 내부 메서드 정의
        """지정된 인덱스의 노드를 부모 노드와 비교하며 상향 이동시킵니다.

        새 항목이 삽입되었을 때 부모 노드의 첫 번째 원소보다 작으면 교환하는 과정을
        루트에 도달하거나 부모가 더 작을 때까지 반복합니다 (O(log n)).

        Args:
            idx (int): 상향 힙화를 시작할 대상 노드의 인덱스.
        """
        while idx > 0:	# 루트 노드(0번 인덱스)에 도달할 때까지 반복
            parent = (idx - 1) // 2	# 부모 노드의 배열 인덱스 계산
            if self._data[idx][0] < self._data[parent][0]:	# 현재 노드의 값이 부모 노드의 값보다 작은 경우
                self._data[idx], self._data[parent] = self._data[parent], self._data[idx]	# 두 노드의 위치 교환 (스왑)
                idx = parent	# 검사 위치를 부모 노드 인덱스로 이동
            else:	# 부모 노드가 더 작거나 같아서 최소 힙 불변성을 만족하는 경우
                break	# 상향 힙화 종료

    def _heapify_down(self, idx):	# 부모에서 자식 방향으로 내려가며 정렬하는 내부 메서드 정의
        """지정된 인덱스의 노드를 자식 노드들과 비교하며 하향 이동시킵니다.

        루트 노드가 추출된 후 대체된 노드가 두 자식 중 더 작은 자식보다 크면 교환하는 과정을
        리프에 도달하거나 자식들보다 작을 때까지 반복합니다 (O(log n)).

        Args:
            idx (int): 하향 힙화를 시작할 대상 노드의 인덱스.
        """
        n = len(self._data)	# 현재 힙 배열의 총 원소 개수 측정
        while True:	# 제자리를 찾을 때까지 무한 반복 루프
            left, right = 2 * idx + 1, 2 * idx + 2	# 좌측 자식과 우측 자식의 인덱스 계산
            smallest = idx	# 현재 인덱스를 가장 작은 원소의 위치로 가정
            if left < n and self._data[left][0] < self._data[smallest][0]:	# 좌측 자식이 존재하고 현재 값보다 작은 경우
                smallest = left	# 최솟값 인덱스를 좌측 자식으로 갱신
            if right < n and self._data[right][0] < self._data[smallest][0]:	# 우측 자식이 존재하고 현재 최솟값보다 더 작은 경우
                smallest = right	# 최솟값 인덱스를 우측 자식으로 갱신
            if smallest == idx:	# 자신이 두 자식보다 모두 작거나 같아 교환이 불필요한 경우
                break	# 하향 힙화 종료
            self._data[idx], self._data[smallest] = self._data[smallest], self._data[idx]	# 더 작은 자식 노드와 위치 교환 (스왑)
            idx = smallest	# 검사 위치를 자식 노드 인덱스로 이동

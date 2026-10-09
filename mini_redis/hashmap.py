"""체이닝 방식 해시맵.

dict/set/collections를 사용하지 않고 직접 구현한다. 버킷 배열은 파이썬
list(고정 인덱스 접근용 저장소)를 사용하고, 각 버킷의 충돌 체인은
DoublyLinkedList를 재사용한다. 로드 팩터가 0.75를 넘으면 버킷을 2배로
확장하고 전체 항목을 재해싱한다.
"""

from .doubly_linked_list import DoublyLinkedList

_LOAD_FACTOR_LIMIT = 0.75
_MISSING = object()


def _hash_key(key, capacity):
    """djb2 계열 다항 해시. 문자열을 32비트 정수로 누적한 뒤 버킷 개수로 나눈 나머지를 쓴다."""
    h = 5381
    for ch in key:
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
    return h % capacity


class _Pair:
    __slots__ = ("key", "value")

    def __init__(self, key, value):
        self.key = key
        self.value = value


class HashMap:
    def __init__(self, capacity=8):
        self._capacity = capacity
        self._buckets = [DoublyLinkedList() for _ in range(capacity)]
        self._size = 0

    def put(self, key, value):
        idx = _hash_key(key, self._capacity)
        for pair in self._buckets[idx]:
            if pair.key == key:
                pair.value = value
                return
        self._buckets[idx].insert_back(_Pair(key, value))
        self._size += 1
        if self._size / self._capacity > _LOAD_FACTOR_LIMIT:
            self._resize(self._capacity * 2)

    def get(self, key, default=_MISSING):
        idx = _hash_key(key, self._capacity)
        for pair in self._buckets[idx]:
            if pair.key == key:
                return pair.value
        if default is _MISSING:
            raise KeyError(key)
        return default

    def contains(self, key):
        idx = _hash_key(key, self._capacity)
        for pair in self._buckets[idx]:
            if pair.key == key:
                return True
        return False

    def remove(self, key):
        idx = _hash_key(key, self._capacity)
        bucket = self._buckets[idx]
        for node in bucket.nodes():
            if node.data.key == key:
                bucket.remove_node(node)
                self._size -= 1
                return True
        return False

    def keys(self):
        result = []
        for bucket in self._buckets:
            for pair in bucket:
                result.append(pair.key)
        return result

    def size(self):
        return self._size

    def _resize(self, new_capacity):
        old_buckets = self._buckets
        self._buckets = [DoublyLinkedList() for _ in range(new_capacity)]
        self._capacity = new_capacity
        for bucket in old_buckets:
            for pair in bucket:
                idx = _hash_key(pair.key, new_capacity)
                self._buckets[idx].insert_back(pair)

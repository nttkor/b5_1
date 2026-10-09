"""최소 힙(min-heap).

배열(list) 기반 완전 이진 트리로 구현한다. TTL 관리에서 "가장 빨리
만료되는 키"를 O(log n)에 찾기 위해 사용한다. 항목은 (expire_at, key, version)
형태의 튜플이며, 정렬 기준은 항상 첫 원소(expire_at)다.
"""


class MinHeap:
    def __init__(self):
        self._data = []

    def push(self, item):
        self._data.append(item)
        self._heapify_up(len(self._data) - 1)

    def pop(self):
        if not self._data:
            return None
        top = self._data[0]
        last = self._data.pop()
        if self._data:
            self._data[0] = last
            self._heapify_down(0)
        return top

    def peek(self):
        return self._data[0] if self._data else None

    def size(self):
        return len(self._data)

    def _heapify_up(self, idx):
        while idx > 0:
            parent = (idx - 1) // 2
            if self._data[idx][0] < self._data[parent][0]:
                self._data[idx], self._data[parent] = self._data[parent], self._data[idx]
                idx = parent
            else:
                break

    def _heapify_down(self, idx):
        n = len(self._data)
        while True:
            left, right = 2 * idx + 1, 2 * idx + 2
            smallest = idx
            if left < n and self._data[left][0] < self._data[smallest][0]:
                smallest = left
            if right < n and self._data[right][0] < self._data[smallest][0]:
                smallest = right
            if smallest == idx:
                break
            self._data[idx], self._data[smallest] = self._data[smallest], self._data[idx]
            idx = smallest

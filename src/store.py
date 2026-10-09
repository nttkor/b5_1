"""LRU + TTL를 지원하는 인메모리 Key-Value 저장소.

세 자료구조를 조합한다.
- HashMap: key -> Entry, O(1) 평균 조회.
- DoublyLinkedList(LRU): 최근 사용 순서. front=최근 사용, back=가장 오래됨.
  Entry가 자신의 lru_node를 들고 있어 move_to_front/remove_node가 O(1)이다.
- MinHeap(TTL): (expire_at, key, version) 튜플. 가장 빨리 만료될 항목을 O(log n)에 찾는다.
  힙은 임의 위치 삭제를 지원하지 않으므로, key를 덮어쓰거나 지울 때 ttl_version을
  올려 예약된 힙 항목을 "무효화"하고, pop 시점에 버전이 안 맞으면 버린다(lazy deletion).
"""

import time

from .doubly_linked_list import DoublyLinkedList
from .hashmap import HashMap
from .heap import MinHeap


class OOMError(Exception):
    """단일 엔트리가 maxmemory 자체를 초과할 때 발생."""


class Entry:
    __slots__ = ("value", "size", "lru_node", "expire_at", "ttl_version")

    def __init__(self, value, size):
        self.value = value
        self.size = size
        self.lru_node = None
        self.expire_at = None
        self.ttl_version = 0


class MiniRedisStore:
    def __init__(self):
        self._map = HashMap()
        self._lru = DoublyLinkedList()
        self._ttl_heap = MinHeap()
        self.used_memory = 0
        self.maxmemory = 0
        self.evicted_keys = 0

    @staticmethod
    def _entry_size(key, value):
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _get_entry(self, key):
        try:
            return self._map.get(key)
        except KeyError:
            return None

    def _sweep_expired(self, now):
        """힙 top이 now를 넘을 때까지 만료 항목을 꺼내 실제로 지운다(lazy deletion)."""
        while self._ttl_heap.size() > 0 and self._ttl_heap.peek()[0] <= now:
            expire_at, key, version = self._ttl_heap.pop()
            entry = self._get_entry(key)
            if entry is not None and entry.expire_at == expire_at and entry.ttl_version == version:
                self._purge(key, entry)

    def _purge(self, key, entry):
        self._map.remove(key)
        self._lru.remove_node(entry.lru_node)
        self.used_memory -= entry.size

    def _touch_lru(self, entry, key):
        if entry.lru_node is None:
            entry.lru_node = self._lru.insert_front(key)
        else:
            self._lru.move_to_front(entry.lru_node)

    def set(self, key, value):
        now = time.monotonic()
        self._sweep_expired(now)
        size = self._entry_size(key, value)
        if self.maxmemory > 0 and size > self.maxmemory:
            raise OOMError()

        entry = self._get_entry(key)
        if entry is not None:
            self.used_memory -= entry.size
            entry.value = value
            entry.size = size
            entry.expire_at = None  # 덮어쓰면 기존 TTL은 초기화한다
            entry.ttl_version += 1
            self.used_memory += size
            self._touch_lru(entry, key)
        else:
            entry = Entry(value, size)
            self._map.put(key, entry)
            self.used_memory += size
            self._touch_lru(entry, key)

        self._evict_if_needed()

    def _evict_if_needed(self):
        while self.maxmemory > 0 and self.used_memory > self.maxmemory and len(self._lru) > 0:
            victim_key = self._lru.remove_back()
            victim = self._get_entry(victim_key)
            if victim is None:
                continue
            self._map.remove(victim_key)
            self.used_memory -= victim.size
            self.evicted_keys += 1

    def get(self, key):
        now = time.monotonic()
        self._sweep_expired(now)
        entry = self._get_entry(key)
        if entry is None:
            return None
        self._touch_lru(entry, key)
        return entry.value

    def delete(self, key):
        now = time.monotonic()
        self._sweep_expired(now)
        entry = self._get_entry(key)
        if entry is None:
            return False
        self._purge(key, entry)
        return True

    def exists(self, key):
        self._sweep_expired(time.monotonic())
        return self._map.contains(key)

    def dbsize(self):
        self._sweep_expired(time.monotonic())
        return self._map.size()

    def keys(self):
        self._sweep_expired(time.monotonic())
        return self._map.keys()

    def expire(self, key, seconds):
        now = time.monotonic()
        self._sweep_expired(now)
        entry = self._get_entry(key)
        if entry is None:
            return False
        if seconds <= 0:
            self._purge(key, entry)
            return True
        entry.expire_at = now + seconds
        entry.ttl_version += 1
        self._ttl_heap.push((entry.expire_at, key, entry.ttl_version))
        return True

    def ttl(self, key):
        now = time.monotonic()
        self._sweep_expired(now)
        entry = self._get_entry(key)
        if entry is None:
            return -2
        if entry.expire_at is None:
            return -1
        return int(entry.expire_at - now)

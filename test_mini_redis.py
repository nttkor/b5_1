"""assert 기반 자체 검증 스크립트. `python test_mini_redis.py`로 실행한다."""

import time

from mini_redis.doubly_linked_list import DoublyLinkedList
from mini_redis.hashmap import HashMap
from mini_redis.heap import MinHeap
from mini_redis.store import MiniRedisStore, OOMError
from mini_redis.cli import execute_command


def test_doubly_linked_list():
    dll = DoublyLinkedList()
    a = dll.insert_front("a")
    b = dll.insert_front("b")  # [b, a]
    dll.insert_back("c")  # [b, a, c]
    assert list(dll) == ["b", "a", "c"]
    dll.move_to_front(a)  # [a, b, c]
    assert list(dll) == ["a", "b", "c"]
    assert dll.remove_back() == "c"
    assert dll.remove_front() == "a"
    assert list(dll) == ["b"]
    assert len(dll) == 1


def test_hashmap_chaining_and_resize():
    hm = HashMap(capacity=4)
    keys = [f"key-{i}" for i in range(50)]
    for k in keys:
        hm.put(k, k.upper())
    assert hm.size() == 50
    for k in keys:
        assert hm.get(k) == k.upper()
    assert hm.remove("key-0") is True
    assert hm.contains("key-0") is False
    assert hm.remove("key-0") is False
    hm.put("key-1", "UPDATED")
    assert hm.get("key-1") == "UPDATED"
    assert hm.size() == 49


def test_min_heap_orders_by_first_element():
    heap = MinHeap()
    for item in [(5, "e"), (1, "a"), (3, "c"), (2, "b"), (4, "d")]:
        heap.push(item)
    popped = [heap.pop()[1] for _ in range(5)]
    assert popped == ["a", "b", "c", "d", "e"]
    assert heap.pop() is None


def test_lru_eviction_matches_requirements_example():
    store = MiniRedisStore()
    store.maxmemory = 30
    store.set("user:1", "Alice")  # size 11
    store.set("user:2", "Bob")  # size 9, used=20
    store.set("user:3", "Charlie")  # size 13, used=33 -> evict user:1 -> used=22
    assert store.get("user:1") is None
    assert store.used_memory == 22
    assert store.evicted_keys == 1
    assert sorted(store.keys()) == ["user:2", "user:3"]


def test_single_entry_oom():
    store = MiniRedisStore()
    store.maxmemory = 5
    try:
        store.set("k", "toolongvalue")
        assert False, "OOMError expected"
    except OOMError:
        pass
    assert store.dbsize() == 0


def test_ttl_expiry_and_overwrite_clears_ttl():
    store = MiniRedisStore()
    store.set("a", "1")
    assert store.expire("a", 1) is True
    assert store.ttl("a") in (0, 1)
    time.sleep(1.1)
    assert store.get("a") is None
    assert store.ttl("a") == -2

    store.set("b", "1")
    store.expire("b", 100)
    store.set("b", "2")  # overwrite clears TTL
    assert store.ttl("b") == -1

    assert store.expire("missing", 10) is False
    assert store.expire("b", 0) is True  # immediate expire
    assert store.exists("b") is False


def test_delete_removes_from_all_structures():
    store = MiniRedisStore()
    store.set("x", "1")
    store.expire("x", 100)
    assert store.delete("x") is True
    assert store.delete("x") is False
    assert store.dbsize() == 0
    assert store.ttl("x") == -2


def test_cli_error_paths():
    store = MiniRedisStore()
    assert execute_command(store, "GET") == "(error) ERR wrong number of arguments for 'GET' command"
    assert execute_command(store, "HELLO") == "(error) ERR unknown command 'HELLO'"
    assert execute_command(store, "CONFIG SET maxmemory abc") == "(error) ERR value is not an integer or out of range"
    assert execute_command(store, 'SET user:1 "Alice"') == "OK"
    assert execute_command(store, "GET user:1") == '"Alice"'
    assert execute_command(store, "DBSIZE") == "(integer) 1"
    assert execute_command(store, "KEYS") == '1. "user:1"'
    execute_command(store, "CONFIG SET maxmemory 5")
    assert execute_command(store, "SET k toolongvalue") == "(error) OOM command not allowed when used_memory > 'maxmemory'"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok - {t.__name__}")
    print(f"All {len(tests)} tests passed.")

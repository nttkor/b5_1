"""assert 기반 자체 검증 스크립트. `python test_mini_redis.py`로 실행한다."""

import time

from src.doubly_linked_list import DoublyLinkedList, NodePool
from src.hashmap import HashMap
from src.heap import MinHeap
from src.store import MiniRedisStore, OOMError
from src.cli import execute_command


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


def test_quoted_and_whitespace_values():
    store = MiniRedisStore()
    assert execute_command(store, 'SET "my key" "hello world with spaces"') == "OK"
    assert execute_command(store, 'GET "my key"') == '"hello world with spaces"'
    assert execute_command(store, "SET single 'quoted value'") == "OK"
    assert execute_command(store, "GET single") == '"quoted value"'
    assert execute_command(store, 'SET empty ""') == "OK"
    assert execute_command(store, "GET empty") == '""'
    assert execute_command(store, 'SET bad "unclosed') == "(error) ERR unbalanced quotes"


def test_node_pool_reuse():
    pool = NodePool(max_size=5)
    dll = DoublyLinkedList(pool=pool)
    n1 = dll.insert_front("data1")
    n2 = dll.insert_back("data2")
    assert pool.size() == 0
    dll.remove_node(n1)
    assert pool.size() == 1
    dll.remove_node(n2)
    assert pool.size() == 2
    n3 = dll.insert_front("data3")
    assert pool.size() == 1
    assert n3.data == "data3"

    hm = HashMap(capacity=4, use_node_pool=True)
    hm.put("k1", "v1")
    hm.put("k2", "v2")
    assert hm.remove("k1") is True
    assert hm._pool.size() >= 1


def test_hashmap_chain_distribution():
    hm = HashMap(capacity=4)
    for i in range(10):
        hm.put(f"key-{i}", f"val-{i}")
    dist = hm.get_chain_distribution()
    stats = hm.get_chain_stats()
    assert len(dist) == stats[0]
    assert stats[1] == 10
    assert len(hm.rehash_history) > 0
    old_cap, new_cap, pre, post = hm.rehash_history[0]
    assert new_cap > old_cap
    assert len(pre) == 5
    assert len(post) == 5


def test_min_heap_dump_top():
    heap = MinHeap()
    for item in [(10, "ten"), (2, "two"), (5, "five"), (1, "one")]:
        heap.push(item)
    dumped = heap.dump_top(3)
    assert len(dumped) == 3
    assert [d[1] for d in dumped] == ["one", "two", "five"]
    assert heap.size() == 4

    store = MiniRedisStore()
    store.set("k1", "v1")
    store.expire("k1", 50)
    store.set("k2", "v2")
    store.expire("k2", 10)
    store_dump = store.dump_ttl_heap_top(2)
    assert len(store_dump) == 2
    assert store_dump[0][1] == "k2"


def test_eviction_logging_and_callback():
    store = MiniRedisStore()
    store.maxmemory = 20
    logged = []
    store.eviction_callback = lambda key, reclaimed: logged.append((key, reclaimed))
    store.eviction_log_enabled = True

    store.set("k1", "12345678")  # size 10
    store.set("k2", "12345678")  # size 10, used 20
    store.set("k3", "12345678")  # size 10, used 30 -> evict k1
    assert len(logged) == 1
    assert logged[0] == ("k1", 10)
    assert store.eviction_logs == [("k1", 10)]


def test_heap_compaction():
    store = MiniRedisStore()
    store.set("a", "1")
    store.expire("a", 100)
    assert store._ttl_heap.size() == 1
    store.set("a", "2")  # overwrite invalidates old heap tuple
    assert store._ttl_heap.size() == 1
    store.set("b", "1")
    store.expire("b", 200)
    assert store._ttl_heap.size() == 2

    purged = store.compact_ttl_heap()
    assert purged == 1
    assert store._ttl_heap.size() == 1


def test_memory_overhead_correction():
    store = MiniRedisStore()
    store.include_overhead = True
    store.entry_overhead_bytes = 64
    store.set("k", "v")
    assert store.used_memory == 2 + 64
    store.maxmemory = 65
    try:
        store.set("k2", "v2")
        assert False, "OOM expected"
    except OOMError:
        pass


def test_cli_verbose_info_and_error_context():
    store = MiniRedisStore()
    store.set("user:1", "Alice")
    normal_info = execute_command(store, "INFO memory")
    assert "valid_keys" not in normal_info

    verbose_info = execute_command(store, "INFO memory verbose")
    assert "valid_keys:1" in verbose_info
    assert "heap_size:" in verbose_info

    execute_command(store, "CONFIG SET maxmemory 5")
    err_msg = execute_command(store, "SET key toolongvalue", verbose_error=True)
    assert "used_memory=" in err_msg
    assert "maxmemory=5" in err_msg



if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok - {t.__name__}")
    print(f"All {len(tests)} tests passed.")

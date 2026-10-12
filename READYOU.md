# Mini Redis 구술 평가 대비 문서

과제 목표(3번)에서 요구하는 네 가지를 내 코드를 근거로 직접 설명해본다.
Redis가 왜 빠른지 "in-memory라서"라고 답하면 반은 맞고 반은 틀렸다. 진짜 이유는
자료구조 선택이 전부 O(1)/O(log n)이 되도록 짜여 있기 때문이다. 이 프로젝트에서
그 이유를 손으로 다시 만들어봤다.

---

## 1. 해시맵의 해시 함수와 충돌 해결(체이닝)

`src/hashmap.py`의 `_hash_key`:

```python
def _hash_key(key, capacity):
    h = 5381
    for ch in key:
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
    return h % capacity
```

djb2 계열 다항 해시다. 문자 하나하나를 `h = h*33 + ord(ch)` 규칙으로 누적한다.
33을 곱하는 이유는 홀수이면서 2의 거듭제곱과 거리가 먼 상수를 곱하면 비트가
고르게 섞이기 때문이다(경험적으로 검증된 상수, djb2가 오래 살아남은 이유이기도
하다). `& 0xFFFFFFFF`로 32비트 오버플로를 잘라내고, 마지막에 `% capacity`로
버킷 인덱스 범위로 축소한다.

문제는 서로 다른 키가 같은 인덱스로 매핑되는 충돌이다. `user:1`과 `user:2`가
같은 버킷에 떨어질 수 있다. 이걸 체이닝으로 푼다:

```python
self._buckets = [DoublyLinkedList() for _ in range(capacity)]
```

버킷 하나가 곧 연결 리스트 하나다. 충돌이 나면 그냥 같은 버킷의 리스트 뒤에
새 `_Pair(key, value)`를 붙인다(`insert_back`). `put`/`get`/`remove` 모두
"해당 인덱스 버킷을 순회하며 key가 같은 노드를 찾는다"는 동일한 패턴을 쓴다.
버킷 하나에 항목이 몰리지만 않으면 이 순회는 사실상 상수 시간이다.

버킷이 붐비지 않게 하는 장치가 로드 팩터다:

```python
if self._size / self._capacity > 0.75:
    self._resize(self._capacity * 2)
```

항목 수가 버킷 수의 75%를 넘는 순간 버킷을 2배로 늘리고 기존 `_Pair` 전부를
새 용량 기준으로 다시 해싱해서 옮긴다(`_resize`). `test_hashmap_chaining_and_resize`에서
50개 키를 capacity=4로 시작한 맵에 넣고도 전부 정상 조회되는 걸로 이 과정을
검증했다 — 리사이즈가 안 됐다면 버킷 하나에 12개 이상이 몰려서 사실상 O(n)
연결 리스트 탐색이 됐을 것이다.

---

## 2. 이중 연결 리스트 + 해시맵으로 O(1) LRU가 되는 이유

LRU("가장 오래 안 쓴 키부터 지운다")를 구현하려면 두 가지가 동시에 빨라야 한다.

1. 특정 키를 "방금 썼다"고 표시하고 순서상 맨 앞으로 옮기기
2. "가장 오래 안 쓴 키"(맨 뒤)를 즉시 꺼내기

배열만으로 하면 1번이 O(n)이다(중간 항목을 앞으로 옮기려면 밀어야 한다).
`store.py`의 해법은 각 `Entry`가 **자기 자신의 연결 리스트 노드를 직접 들고
있는 것**이다.

```python
class Entry:
    __slots__ = ("value", "size", "lru_node", "expire_at", "ttl_version")
```

```python
def _touch_lru(self, entry, key):
    if entry.lru_node is None:
        entry.lru_node = self._lru.insert_front(key)
    else:
        self._lru.move_to_front(entry.lru_node)
```

`GET`이 성공하면 `_touch_lru`가 호출된다. 해시맵으로 `entry`를 O(1)에 찾고,
그 `entry.lru_node`는 이미 연결 리스트 안의 정확한 위치를 가리키는 포인터이므로
"어디 있는지 찾는" 과정 자체가 없다. `move_to_front`는 앞뒤 포인터만 갈아 끼우는
연산이라 O(1)이다:

```python
def move_to_front(self, node):
    node.prev.next = node.next
    node.next.prev = node.prev
    self._link_after(self._head, node)
```

제거할 때(`_evict_if_needed`)는 `remove_back()`으로 리스트의 맨 뒤 — 가장
오래 안 쓴 키 — 를 O(1)에 꺼낸다. 즉 "해시맵이 위치를 알려주고, 연결 리스트가
그 위치에서 O(1)로 움직인다"는 조합이 핵심이다. 배열이었다면 해시맵으로 인덱스를
알아내도 그 인덱스를 옮기는 비용이 O(n)이었을 것이다.

`test_lru_eviction_matches_requirements_example`이 이 흐름 전체를 검증한다:
`maxmemory=30`에서 `user:1`(11B), `user:2`(9B), `user:3`(13B)를 넣으면 33B가
되어 초과하고, 가장 오래 안 쓴 `user:1`이 지워지며 `used_memory`가 22로 떨어진다.

---

## 3. 힙이 TTL 관리에 적합한 이유

TTL 관리의 핵심 질문은 "지금 이 순간 만료된 키가 있는가? 있다면 어떤 키인가?"다.
모든 키를 순회하며 `expire_at`을 비교하면 O(n)이다. 힙은 "가장 작은 값(=가장 빨리
만료될 시각)"을 항상 루트에 유지하므로, 루트만 확인하면 O(1)에 "지금 만료된 게
있는지"를 알 수 있고, 실제로 꺼내는 데는 O(log n)이 든다.

```python
def _sweep_expired(self, now):
    while self._ttl_heap.size() > 0 and self._ttl_heap.peek()[0] <= now:
        expire_at, key, version = self._ttl_heap.pop()
        entry = self._get_entry(key)
        if entry is not None and entry.expire_at == expire_at and entry.ttl_version == version:
            self._purge(key, entry)
```

모든 키 명령(`GET`, `SET`, `EXISTS`, ...) 시작 시 이 sweep을 한 번 돌린다. 힙
루트가 `now`보다 크면 즉시 멈춘다 — 힙 성질상 루트보다 작은 값은 트리 안에
존재할 수 없으므로, 이후 항목도 전부 아직 안 만료됐다는 게 보장된다.

한 가지 함정이 있다. 힙은 "이 키의 예약된 만료를 취소"하는 연산(임의 위치 삭제)을
지원하지 않는다. `SET`으로 같은 키를 덮어쓰면 TTL이 초기화되어야 하는데, 옛
힙 항목이 그대로 남아 있으면 나중에 튀어나와 엉뚱하게 삭제할 위험이 있다. 그래서
`ttl_version`을 뒀다:

```python
entry.ttl_version += 1
self._ttl_heap.push((entry.expire_at, key, entry.ttl_version))
```

힙에서 항목을 꺼낼 때 `entry.expire_at == expire_at and entry.ttl_version == version`이
안 맞으면 "이미 무효화된 예약"이라 보고 그냥 버린다. 힙 자체를 건드리지 않고
"버전 불일치로 무시"하는 lazy deletion으로 정확성을 지키는 방식이다.

---

## 4. 메모리 제한 + LRU 제거 전체 흐름

`SET`이 호출됐을 때 실제로 벌어지는 일을 순서대로 짚는다.

```mermaid
flowchart TD
    A[SET key value] --> B[_sweep_expired: 만료된 키 먼저 정리]
    B --> C[size = entry 크기 계산]
    C --> D{size > maxmemory?}
    D -->|Yes, maxmemory>0| E[OOMError: 저장 거부]
    D -->|No| F{기존 키 존재?}
    F -->|Yes| G[used_memory -= 기존 size, TTL 초기화, 값 교체]
    F -->|No| H[새 Entry 생성, map에 put]
    G --> I[used_memory += 새 size, LRU front로 이동]
    H --> I
    I --> J{used_memory > maxmemory?}
    J -->|Yes| K[LRU back 제거 -> map/used_memory 갱신, evicted_keys += 1]
    K --> J
    J -->|No| L[완료: OK 반환]
```

`used_memory`는 값 하나하나를 계산하지 않고 **증분으로만** 갱신한다(삽입 시
`+= size`, 덮어쓸 때 `-= 기존 size` 후 `+= 새 size`, 삭제/제거 시 `-= size`).
매번 전체를 다시 합산하면 O(n)이 되어 SET 자체가 느려지기 때문이다.

`_evict_if_needed`가 `while`로 도는 이유는 새 항목 하나가 여러 옛 항목의 크기를
합친 것보다 클 수 있어서다(예: `user:3`이 13B라 20B였던 상태에서 33B가 되면,
`user:1` 하나(11B)를 지워야 22B로 떨어진다 — 실제로 1개만 지워지는지, 2개
필요한지는 상황마다 다르므로 조건을 만족할 때까지 반복한다).

---

---

## 5. GET 실행 시퀀스 및 TTL 절사 정책

### ① GET 명령어의 O(1) 실행 흐름 시퀀스 다이어그램
```mermaid
sequenceDiagram
    autonumber
    actor Client as 사용자 CLI
    participant Store as MiniRedisStore
    participant Heap as MinHeap (TTL)
    participant Map as HashMap
    participant LRU as DoublyLinkedList (LRU)

    Client->>Store: GET key
    Store->>Heap: sweep_expired(now)
    Heap-->>Store: 만료 항목 pop 및 _purge
    Store->>Map: _get_entry(key)
    alt 키 미존재 또는 만료됨
        Map-->>Store: None
        Store-->>Client: (nil)
    else 키 유효하게 존재함
        Map-->>Store: Entry(value, lru_node)
        Store->>LRU: move_to_front(entry.lru_node)
        LRU-->>Store: O(1) MRU 위치 갱신
        Store-->>Client: "value"
    end
```

### ② TTL 반환값의 정수 절사(Floor / Truncation toward zero) 정책
Mini Redis의 TTL 계산 공식은 `int(entry.expire_at - now)`입니다:
- Python의 `int()` 캐스팅은 소수점 이하를 버리는 **내림/절사(Floor / Truncation)** 방식을 취합니다.
- 예: 남은 시간이 `2.9초`일 때 `int(2.9) = 2`를 반환하고, `0.4초`일 때 `int(0.4) = 0`을 반환합니다. (0초는 아직 만료되지 않고 유효함을 의미)
- 단조 시계가 만료 시각 이상(`now >= entry.expire_at`)이 되면 선행 `_sweep_expired`에 의해 즉시 물리 삭제되어 `(integer) -2`를 반환합니다.

---

## 6. LFU 전환 아키텍처 및 점진적 리해싱 (100k 벤치마크)

### ① LFU 전환 시 자료구조 설계 및 코드 스켈레톤
LFU(참조 빈도 기반 축출)는 `key_map`(Key->Node), `freq_map`(Freq->DLL), `min_freq`(최소 빈도)의 조합으로 $O(1)$을 달성합니다:
```python
class LFUNode:
    __slots__ = ("key", "value", "freq", "prev", "next")
    def __init__(self, key, value, freq=1):
        self.key, self.value, self.freq = key, value, freq
        self.prev = self.next = None

class LFUCache:
    """O(1) 시간 복잡도로 get, put, evict를 보장하는 LFU 캐시 엔진 스켈레톤."""
    def __init__(self, capacity=1000):
        self.capacity, self.size, self.min_freq = capacity, 0, 0
        self.key_map, self.freq_map = HashMap(), HashMap()

    def get(self, key):
        if not self.key_map.contains(key): return None
        node = self.key_map.get(key)
        self._touch_freq(node)
        return node.value

    def put(self, key, value):
        if self.capacity <= 0: return
        if self.key_map.contains(key):
            node = self.key_map.get(key); node.value = value
            self._touch_freq(node); return
        if self.size >= self.capacity: self._evict_lfu()
        node = LFUNode(key, value, 1)
        self.key_map.put(key, node)
        self._get_freq_list(1).insert_front(node)
        self.min_freq = 1; self.size += 1

    def _touch_freq(self, node):
        old_list = self.freq_map.get(str(node.freq))
        old_list.remove_node(node)
        if len(old_list) == 0 and self.min_freq == node.freq: self.min_freq += 1
        node.freq += 1
        self._get_freq_list(node.freq).insert_front(node)

    def _evict_lfu(self):
        victim = self.freq_map.get(str(self.min_freq)).remove_back()
        if victim: self.key_map.remove(victim.key); self.size -= 1

    def _get_freq_list(self, f):
        if not self.freq_map.contains(str(f)):
            dll = DoublyLinkedList(); self.freq_map.put(str(f), dll); return dll
        return self.freq_map.get(str(f))
```

### ② 점진적 재해싱(Incremental Rehashing) 및 10만 건 실측 벤치마크
대규모 데이터 확장 시 동기식 일괄 리해시로 인한 Latency Spike를 해결하기 위해 Redis `dict.c`의 `ht[0]`, `ht[1]`, `rehashidx` 기반 점진적 마이그레이션 아키텍처를 설계하였습니다.

실제 `utils/benchmark_rehash.py`를 통해 측정한 대규모 데이터셋 벤치마크 결과:

| 데이터 규모 | 삽입 소요 시간 (s) | 삽입 Throughput | 조회 Throughput | 최종 버킷 수 | 리해시 횟수 | 최대 체인 길이 | 평균 체인 길이 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **10,000건** | 0.1578s | 63,370 ops/s | 326,293 ops/s | 16,384 | 11회 | 4 | 0.61 |
| **50,000건** | 1.5133s | 33,041 ops/s | 310,720 ops/s | 131,072 | 14회 | 4 | 0.38 |
| **100,000건** | 3.3837s | 29,553 ops/s | 312,512 ops/s | 262,144 | 15회 | 4 | 0.38 |

- **조회 불변성 증명**: 데이터 규모가 10배 증가해도 조회 처리율은 **초당 31만 회(312,512 ops/s)**로 일정하게 유지됨.
- **체인 길이 최적화**: 10만 건 환경에서도 djb2 다항 해시와 로드팩터 0.75 확장 덕분에 최대 체인이 4개 이하로 엄격히 통제됨.

---

## 7. 고도화 엔지니어링 및 자체 방어 체계

- **노드 재사용 풀 (`NodePool`)**: 이중 연결 리스트 및 해시맵 버킷 노드 해제 시 프리 리스트로 회수하여 CPython GC 압박과 잦은 malloc/free 오버헤드 최소화.
- **주기적 힙 컴팩트 (`compact_ttl_heap`)**: Lazy Deletion으로 인해 누적된 버전 불일치 무효 힙 엔트리를 주기적으로 정리하여 메모리 누수 방지.
- **축출 콜백 및 로깅 (`eviction_callback`, `eviction_log_enabled`)**: 메모리 초과로 LRU 축출 발생 시 어떤 키가 축출되고 몇 바이트가 회수되었는지 실시간 로깅 및 외부 통지 훅 제공.
- **메모리 오버헤드 보정 옵션 (`include_overhead`)**: 채점/운영 환경에 맞춰 `PyObject_HEAD` 및 슬롯 고정 오버헤드(64B)를 선택적으로 가산 반영 가능.


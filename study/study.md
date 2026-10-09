# Mini Redis 핵심 개념 및 기술 용어 백과사전 (`study/study.md`)

본 문서는 [`docs/b5_1_mission.md`](../docs/b5_1_mission.md), [`docs/b5_1_mission_QA.md`](../docs/b5_1_mission_QA.md), [`docs/b5_1_eval.md`](../docs/b5_1_eval.md), [`docs/b5_1_eval_QA.md`](../docs/b5_1_eval_QA.md)에 기술된 모든 컴퓨터 공학 원리, 자료구조, 캐시 교체 알고리즘, 메모리 관리, Redis 프로토콜 및 실전 최적화 기법을 체계적으로 집대성한 핵심 학습 지침서입니다.

---

## 📌 1. 상호 참조 링크 (Mutual Cross-References)

본 문서는 프로젝트 내 주요 가이드 문서 및 소스코드와 유기적으로 연동되어 있습니다:

- 📖 **프로젝트 메인 안내서**: [`README.md`](../README.md)
- 🏗️ **아키텍처 및 상세 실행도**: [`study/README.md`](README.md)
- 📝 **미션 수행 및 요구사항 심층 Q&A**: [`docs/b5_1_mission_QA.md`](../docs/b5_1_mission_QA.md)
- 🎯 **종합 평가문항 답변서**: [`docs/b5_1_eval_QA.md`](../docs/b5_1_eval_QA.md)
- 💡 **구술 평가 대비 질문/답변서**: [`READYOU.md`](../READYOU.md)
- 💻 **핵심 구현 소스코드**:
  - 이중 연결 리스트: [`src/doubly_linked_list.py`](../src/doubly_linked_list.py#L40-L189)
  - 체이닝 해시맵: [`src/hashmap.py`](../src/hashmap.py#L68-L203)
  - 최소 힙 (Min-Heap): [`src/heap.py`](../src/heap.py#L24-L122)
  - 통합 스토리지 엔진: [`src/store.py`](../src/store.py#L67-L323)
  - REPL CLI 인터페이스: [`src/cli.py`](../src/cli.py#L122-L236)

---

## 🏢 2. 핵심 아키텍처 및 시스템 개요

### 2.1 인메모리 키-값 저장소 (In-Memory Key-Value Data Store)
- **정의**: 모든 데이터 레코드를 디스크(HDD/SSD)가 아닌 메인 메모리(RAM)에 상주시켜 초고속 읽기/쓰기를 지원하는 데이터베이스 엔진.
- **장점**: 디스크 I/O에 수반되는 탐색 시간(Seek Time)과 버퍼링 오버헤드가 없어 나노초~마이크로초 단위의 접근 속도를 보장.
- **도전 과제**: 휘발성(Volatile) 메모리 특성상 시스템 장애 시 데이터 보존 대책이 필요하며, RAM 용량의 물리적 한계로 인해 정밀한 메모리 제한(`maxmemory`) 및 캐시 교체(Eviction) 알고리즘이 필수적임.

### 2.2 Mini Redis 구현 제약 (No Built-in Collections)
- **제약 사항**: Python의 내장 컬렉션인 `dict`, `set`, `collections` 모듈의 사용이 일체 금지됨.
- **구현 방식**: 오직 순수 포인터 기반의 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189), 고정 인덱스 버킷 배열 기반의 [`HashMap`](../src/hashmap.py#L68-L203), 1차원 배열 기반 완전 이진 트리 [`MinHeap`](../src/heap.py#L24-L122)만을 조합하여 $O(1)$ LRU와 $O(\log N)$ TTL을 달성.

---

## 🧱 3. 핵심 자료구조 개념 및 심층 분석

### 3.1 이중 연결 리스트 (Doubly Linked List & Sentinel Nodes)
- **개념**: 각 노드가 데이터(`data`) 외에 이전 노드(`prev`)와 다음 노드(`next`)에 대한 양방향 참조 포인터를 가지는 선형 자료구조.
- **더미 센티넬 노드 (Sentinel Dummy Nodes)**:
  - 리스트의 시작과 끝에 유효 데이터를 담지 않는 `_head`와 `_tail` 노드를 영구 배치 ([`DoublyLinkedList.__init__`](../src/doubly_linked_list.py#L53-L59)).
  - **효과**: 빈 리스트 삽입/삭제, 첫 번째 노드 삭제, 마지막 노드 삭제 시 발생할 수 있는 `None` 검사 분기문(Edge Cases)을 100% 제거하여 코드의 단순성과 실행 안전성 확보.
- **$O(1)$ 연산 보장 메커니즘**:
  - `insert_front(data)`: `_link_after(self._head, node)`를 통해 4개의 포인터 재배선만으로 맨 앞 삽입 ([`src/doubly_linked_list.py#L61-L75`](../src/doubly_linked_list.py#L61-L75)).
  - `remove_node(node)`: `node.prev.next = node.next`, `node.next.prev = node.prev`로 특정 노드를 즉시 분리 ([`src/doubly_linked_list.py#L117-L129`](../src/doubly_linked_list.py#L117-L129)).
  - `move_to_front(node)`: 기존 위치에서 노드를 분리한 후 `_head` 뒤로 즉시 연결 ([`src/doubly_linked_list.py#L131-L141`](../src/doubly_linked_list.py#L131-L141)).
  - `remove_back()`: `_tail.prev` 노드를 꺼내어 분리 ([`src/doubly_linked_list.py#L103-L115`](../src/doubly_linked_list.py#L103-L115)).

### 3.2 djb2 다항 해시 함수 (Polynomial Rolling Hash & Avalanche Effect)
- **개념**: Daniel J. Bernstein이 제안한 비암호학적 고속 해시 함수로, 문자열 키를 정수형 해시 코드로 변환.
- **알고리즘 수식**:
  $$\text{hash}_{0} = 5381$$
  $$\text{hash}_{i} = ((\text{hash}_{i-1} \times 33) + \text{ord}(c_i)) \ \& \ \text{0xFFFFFFFF}$$
  $$\text{bucket\_index} = \text{hash} \pmod{\text{capacity}}$$
- **기술적 특징**:
  - **소수 5381 (Magic Number)**: 비트 패턴이 고르게 분산된 홀수 소수로 충돌 확률을 최소화.
  - **33배 승수 (`h * 33` 또는 `(h << 5) + h`)**: 비트 시프트와 덧셈으로 구현 가능하여 CPU 연산이 극도로 빠르고, 문자열의 한 글자 변화가 전체 해시값을 완전히 뒤바꾸는 **눈사태 효과(Avalanche Effect)**를 유발.
  - **32비트 마스킹 (`& 0xFFFFFFFF`)**: Python의 무제한 정수 확장을 32비트 고정 크기로 제한하여 C 언어 수준의 일관된 오버플로우 시뮬레이션 지원.
  - 소스코드: [`_hash_key()`](../src/hashmap.py#L27-L44)

### 3.3 체이닝 충돌 해결 (Separate Chaining)
- **개념**: 서로 다른 키가 동일한 버킷 인덱스로 매핑되는 해시 충돌(Hash Collision) 발생 시, 해당 버킷 내에 연결 리스트 체인을 구성하여 충돌된 항목들을 순차 보관하는 기법.
- **Mini Redis 구현 구조**:
  - 각 버킷은 독립된 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189) 객체로 초기화됨 ([`src/hashmap.py#L86`](../src/hashmap.py#L86)).
  - 체인 내 노드는 [`_Pair(key, value)`](../src/hashmap.py#L47-L65) 인스턴스를 보관.
  - 삭제 시 [`bucket.nodes()`](../src/doubly_linked_list.py#L174-L188) 제너레이터를 사용하여 안전하게 순회하며 일치하는 노드를 $O(1)$로 분리 제거 ([`src/hashmap.py#L147-L166`](../src/hashmap.py#L147-L166)).

### 3.4 로드 팩터 및 동적 리사이징 (Load Factor & Dynamic Resizing/Rehashing)
- **로드 팩터 (Load Factor, $\alpha$)**:
  $$\alpha = \frac{\text{저장된 엔트리 수 } (N)}{\text{버킷 배열의 총 용량 } (M)}$$
- **임계값 (Threshold = 0.75)**: 로드 팩터가 0.75를 초과하면 버킷 체인의 평균 길이가 길어져 탐색 속도가 선형 시간($O(K)$)으로 저하되기 시작함.
- **리사이징 절차 ([`HashMap._resize`](../src/hashmap.py#L188-L203))**:
  1. 기존 버킷 배열(`old_buckets`) 보관.
  2. 2배 크기(`new_capacity = capacity * 2`)의 빈 버킷 배열 할당.
  3. `old_buckets`의 모든 키-값 쌍에 대해 `_hash_key(pair.key, new_capacity)`를 재계산하여 새 버킷에 재배치(**전체 재해싱, Full Rehashing**).
  4. 이를 통해 평균 탐색 시간 복잡도를 상시 $O(1)$로 유지.

### 3.5 최소 힙 우선순위 큐 (Min-Heap & Complete Binary Tree)
- **개념**: 부모 노드의 키값이 자식 노드들의 키값보다 항상 작거나 같은 완전 이진 트리(Complete Binary Tree) 구조.
- **1차원 배열 매핑 수식**:
  - 부모 노드 인덱스: $\lfloor(i - 1) / 2\rfloor$
  - 좌측 자식 노드 인덱스: $2i + 1$
  - 우측 자식 노드 인덱스: $2i + 2$
- **힙 불변성 복원 알고리즘**:
  - **상향 힙화 (`_heapify_up`, $O(\log N)$)**: 신규 삽입 시 리프 끝에 추가 후 부모보다 작으면 루트 방향으로 스왑 교환 ([`src/heap.py#L84-L100`](../src/heap.py#L84-L100)).
  - **하향 힙화 (`_heapify_down`, $O(\log N)$)**: 루트 최솟값 추출 후 마지막 요소를 루트로 올리고 두 자식 중 더 작은 노드와 리프 방향으로 스왑 교환 ([`src/heap.py#L102-L122`](../src/heap.py#L102-L122)).
- **TTL 적용**: 원소를 `(expire_at, key, version)` 튜플로 저장하여 첫 번째 값인 만료 타임스탬프를 기준으로 최소 힙을 정렬. 가장 빨리 만료될 키를 $O(1)$에 `peek()` 가능 ([`src/heap.py#L67-L74`](../src/heap.py#L67-L74)).

---

## 🔄 4. 캐시 교체 정책 및 메모리 회계 (Eviction & Memory Management)

### 4.1 LRU (Least Recently Used) 캐시 교체 원리와 $O(1)$ 달성 시너지
- **원리**: 메모리 한도 초과 시 "가장 오랫동안 참조(Read/Write)되지 않은 데이터"를 우선적으로 캐시에서 제거.
- **해시맵과 이중 연결 리스트의 상호 보완 시너지**:
  - 해시맵만 사용: 키 검색은 $O(1)$이지만 사용 시간 순서를 정렬 유지할 수 없음.
  - 연결 리스트만 사용: 순서 이동은 빠르지만 특정 키를 탐색하는 데 $O(N)$ 소요.
  - **시너지 결합 구조**:
    - [`Entry`](../src/store.py#L40-L64) 객체가 LRU 리스트 내 자신 노드의 주소(`entry.lru_node`)를 직접 참조.
    - `GET` 또는 `SET` 호출 시 해시맵에서 $O(1)$로 `Entry`를 찾고, `entry.lru_node`를 [`move_to_front()`](../src/doubly_linked_list.py#L131-L141)에 전달하여 포인터 조작만으로 $O(1)$에 MRU(헤드 직후)로 갱신.
    - 축출 시에는 리스트의 tail.prev에서 $O(1)$로 가장 오래된 victim 키를 꺼내어 제거 ([`src/store.py#L191-L204`](../src/store.py#L191-L204)).

### 4.2 LFU (Least Frequently Used) 캐시 교체 정책 및 $O(1)$ 구조 설계
- **원리**: 참조 시점이 아닌 "누적 참조 빈도수(Frequency Count)"가 가장 적은 데이터를 우선 축출.
- **$O(1)$ LFU 아키텍처 (Advanced Design)**:
  1. `key_map`: `key -> Entry(value, freq, node_ref)` 매핑 해시맵.
  2. `freq_map`: `freq -> DoublyLinkedList()` 빈도별 이중 연결 리스트 테이블.
  3. `min_freq`: 현재 저장소에 존재하는 최소 빈도 정수 포인터.
- **동작**: 키 접근 시 `freq` 리스트에서 분리하여 `freq + 1` 리스트 헤드로 이동. 빈 리스트가 발생하고 `min_freq == freq`이면 `min_freq += 1`. 축출 시 `freq_map[min_freq].remove_back()`으로 $O(1)$ 축출 달성.

### 4.3 메모리 회계 산정 기준 (`used_memory`) 및 OOM 방어
- **산정 공식**:
  $$\text{used\_memory} = \sum_{\text{all keys}} (\text{len}(\text{utf8}(\text{key})) + \text{len}(\text{utf8}(\text{value})))$$
  - 자료구조 오버헤드(포인터, 노드 객체 헤더)는 규격에 따라 산정에서 제외 ([`_entry_size()`](../src/store.py#L88-L101)).
- **OOM (Out Of Memory) 선행 방어**:
  - `CONFIG SET maxmemory`로 한도가 지정된 경우, 신규 엔트리 단일 크기 자체가 `maxmemory`를 초과하면 저장을 즉시 거부하고 [`OOMError`](../src/store.py#L34-L37) 발생 ([`src/store.py#L170-L173`](../src/store.py#L170-L173)).

### 4.4 LRU 자동 축출 파이프라인 (Eviction Pipeline)
```text
SET key value 호출
   │
   ▼
만료 스윕 (_sweep_expired)
   │
   ▼
단일 엔트리 OOM 검사 (size > maxmemory ?) ──(Yes)──> OOMError 발생
   │ (No)
   ▼
엔트리 저장 및 used_memory 가산, MRU 헤드 이동
   │
   ▼
축출 루프: while used_memory > maxmemory:
   ├── LRU 테일 노드 (victim) 추출 (remove_back)
   ├── 해시맵에서 victim 삭제
   ├── used_memory에서 victim 크기 차감
   └── evicted_keys 카운터 1 증가
```

---

## ⏳ 5. TTL (Time-To-Live) 만료 메커니즘 및 지연 삭제 기법

### 5.1 TTL 개념 및 단조 시계 (Monotonic Clock)
- **TTL (Time-To-Live)**: 키-값 데이터의 유효 수명(초 단위).
- **`time.monotonic()` vs `time.time()`**:
  - `time.time()`(Wall-clock): 사용자의 시스템 시계 변경이나 NTP 동기화 시 시간이 거꾸로 흐를 수 있어 캐시 만료 판단에 치명적 결함 유발.
  - `time.monotonic()`: 부팅 이후 단조 증가만을 보장하는 하드웨어 타이머로, 네트워크 지연 및 시계 왜곡 없이 정확한 상대 시간 경과 측정 가능.

### 5.2 지연 삭제 (Lazy Deletion) 및 버전 관리 (`ttl_version`)
- **힙의 구조적 한계**: 최소 힙은 루트가 아닌 임의 위치의 요소를 탐색/삭제하는 데 $O(N)$의 비용이 듦.
- **버전 태깅 기반 지연 삭제 메커니즘 ([`src/store.py#L117-L130`](../src/store.py#L117-L130))**:
  1. `EXPIRE` 설정 시 `(expire_at, key, ttl_version)` 튜플을 힙에 푸시.
  2. 키를 덮어쓰거나 지울 때 `entry.ttl_version`을 1 증가시켜 기존 힙 예약을 논리적으로 "무효화(Invalidation)".
  3. 모든 명령 실행 직전 `_sweep_expired(now)`를 호출하여 힙 최상단(`peek`)의 만료 시간이 지났는지 확인.
  4. 힙에서 꺼낸 튜플의 버전과 엔트리의 실제 `ttl_version`이 일치할 때만 실제 물리 삭제(`_purge`) 수행.

### 5.3 능동적 만료 (Active Expiry Cron) 최적화
- **한계점**: 지연 삭제 방식은 해당 키나 다른 명령이 호출되지 않으면 영원히 힙/메모리에 잔류할 위험이 존재.
- **개선책**: 실제 Redis와 같이 백그라운드 이벤트 루프나 주기적 크론(예: 초당 10회)을 통해 TTL이 설정된 키 중 무작위 20개를 표본 추출하여 만료된 키를 선제적으로 소거하는 능동 만료(Active Expiry) 결합.

---

## 🖥️ 6. 명령어 라이프사이클 및 Redis 프로토콜 규격 (REPL & Protocol)

### 6.1 String 기본 명령어 라이프사이클 (6개)
1. **SET key value**: LRU 최신화, 메모리 초과 시 LRU 축출, 덮어쓰기 시 기존 TTL 초기화. 성공 시 `OK`. ([`src/store.py#L155-L189`](../src/store.py#L155-L189))
2. **GET key**: 만료 여부 선행 검사 후, 유효하면 값 반환 및 LRU 갱신. 없거나 만료 시 `(nil)`. ([`src/store.py#L206-L224`](../src/store.py#L206-L224))
3. **DEL key**: 해시맵, LRU 리스트, 메모리 통계에서 동시 삭제. 성공 시 `(integer) 1`, 없으면 `(integer) 0`. ([`src/store.py#L226-L241`](../src/store.py#L226-L241))
4. **EXISTS key**: 만료 정리 후 존재 여부 검사. `(integer) 1` 또는 `(integer) 0`. ([`src/store.py#L243-L251`](../src/store.py#L243-L251))
5. **DBSIZE**: 현재 유효 키 총 개수 반환. `(integer) N`. ([`src/store.py#L253-L260`](../src/store.py#L253-L260))
6. **KEYS**: 모든 유효 키 목록 배열 출력. `1. "key1"\n2. "key2"` 또는 `(empty array)`. ([`src/store.py#L262-L269`](../src/store.py#L262-L269))

### 6.2 메모리 및 TTL 관리 명령어 (4개)
1. **CONFIG SET maxmemory bytes**: 0 이상의 정수 바이트 설정 (0은 무제한). 성공 시 `OK`. ([`src/cli.py#L182-L189`](../src/cli.py#L182-L189))
2. **INFO memory**: `used_memory:<N>\nmaxmemory:<N>\nevicted_keys:<N>` 출력. ([`src/cli.py#L191-L198`](../src/cli.py#L191-L198))
3. **EXPIRE key seconds**: 키의 만료 초 설정 (0 이하 즉시 삭제). 성공 시 `(integer) 1`, 키 없음 `(integer) 0`. ([`src/store.py#L271-L300`](../src/store.py#L271-L300))
4. **TTL key**: 잔여 초 반환. 키 없음 `(integer) -2`, 만료시간 없음 `(integer) -1`, 유효 잔여초 `(integer) N`. ([`src/store.py#L302-L323`](../src/store.py#L302-L323))

### 6.3 쉘 파싱 및 에러 포맷 표준
- **`shlex.split` 파싱**: 공백 및 큰따옴표(`"Alice in Wonderland"`)가 포함된 인자를 안전하게 분리 ([`src/cli.py#L138-L144`](../src/cli.py#L138-L144)).
- **표준 에러 메시지 규격**:
  - 알 수 없는 명령: `(error) ERR unknown command '<cmd>'`
  - 인자 개수 불일치: `(error) ERR wrong number of arguments for '<cmd>' command`
  - 정수 파싱 오류: `(error) ERR value is not an integer or out of range`
  - 메모리 초과(OOM): `(error) OOM command not allowed when used_memory > 'maxmemory'`

---

## 🚀 7. 컴퓨터 공학 심화 및 대규모 시스템 확장성 (Advanced Topics)

### 7.1 Python `__slots__` 메모리 및 속도 최적화
- **일반 Python 객체**: 기본적으로 `__dict__` 딕셔너리를 인스턴스마다 할당하므로 노드당 150바이트 이상의 무거운 오버헤드 발생.
- **`__slots__` 도입 효과 ([`Node`](../src/doubly_linked_list.py#L27), [`_Pair`](../src/hashmap.py#L55), [`Entry`](../src/store.py#L51))**:
  - 딕셔너리 생성을 원천 차단하고 고정된 C 배열 형태의 포인터 슬롯만 할당.
  - 메모리 사용량을 인스턴스당 약 60% 이상 절감하고 속성 접근(Attribute Lookup) 속도를 대폭 가속.

### 7.2 10만 건 이상 대규모 트래픽 시 병목 지점 및 해결책
1. **해시맵 일괄 리사이징 레이턴시 스파이크 (Latency Spike)**:
   - *문제*: 10만 개 항목을 단일 요청 시점에 동기식으로 일괄 재해싱하면 이벤트 루프가 수백 ms 멈춤.
   - *해결책*: **점진적 재해싱 (Incremental Rehashing)**. 버킷 테이블 2개(`ht[0]`, `ht[1]`)를 두고, 매 요청마다 소수의 버킷(예: 1~10개)씩 점진적으로 이관.
2. **지연 삭제 무효 튜플에 의한 힙 비대화**:
   - *문제*: 빈번한 덮어쓰기 시 힙에 무효화된 튜플이 수십만 개 잔류하여 메모리 낭비.
   - *해결책*: 힙 크기가 임계값을 초과할 때 유효한 튜플만 필터링하여 $O(N)$으로 재구성하는 압축(Compaction) 루틴 적용.
3. **KEYS 명령어의 $O(N)$ 풀 스캔 블로킹**:
   - *문제*: 10만 개 키를 일시에 리스트로 만들어 반환하면 CPU 및 네트워크 블로킹 발생.
   - *해결책*: 커서 기반 순회 명령어인 **`SCAN`**을 구현하여 일정 단위(예: 10개)씩 분할 반환.

### 7.3 자료구조 메모리 오버헤드 산정 모델 및 공정 비교 보정 방안
- **현실적 메모리 오버헤드**:
  - Python 객체 헤더 (`PyObject_HEAD`: 16~24 바이트)
  - 노드 포인터 3개 (`prev`, `next`, `data`: 24 바이트)
  - 버킷 리스트 여유 슬롯 오버헤드
- **공정 비교/보정 방안**:
  1. *고정 상수 가산 모델 (Deterministic Model)*: 엔트리당 고정 오버헤드 상수(예: 112바이트)를 공식에 반영 (`used_memory = sum(len(k) + len(v) + OVERHEAD_PER_ENTRY)`).
  2. *RSS 모니터링 분리*: 알고리즘 평가에서는 결정론적인 데이터 바이트 기준을 유지하고, 시스템 모니터링용으로 `used_memory_rss` 지표를 분리 제공.

### 7.4 보너스 자료구조 연계 로드맵
1. **동적 배열 (Dynamic Array)**: capacity 초과 시 2배 크기로 재할당 복사하는 커스텀 배열을 구현하여 [`HashMap._buckets`](../src/hashmap.py#L86) 및 [`MinHeap._data`](../src/heap.py#L36)에 직접 치환 가능.
2. **스택/큐/덱 (Stack/Queue/Deque)**: [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189)의 `insert_front/back`, `remove_front/back`을 통해 완전한 Deque로 동작.
3. **Pub/Sub 메시지 브로커**: 연결 리스트 노드를 채널별 구독자 메시지 버퍼 큐로 전용하여 다자간 메시징 구현 가능.
4. **이진 탐색 트리 (BST)**: 힙의 이진 트리 원리를 발전시켜 범위 검색(`ZRANGE`)을 위한 정렬 트리 구축 가능.

### 7.5 Python 순환 참조(Circular Reference) 방지와 즉각적 메모리 해제
- **CPython 메모리 관리 메커니즘**:
  - Python(CPython)은 1차적으로 **참조 카운팅(Reference Counting)**으로 메모리를 관리하며, 참조 카운터가 0이 되는 즉시 `tp_dealloc`을 호출하여 메모리를 해제합니다.
  - 2차적으로 순환 참조를 탐지하기 위한 **세대별 순환 가비지 컬렉터(Generational Cycle GC)**가 주기적으로 실행됩니다.
- **`remove_node`의 포인터 초기화 필수성 ([`src/doubly_linked_list.py#L127-L128`](../src/doubly_linked_list.py#L127-L128))**:
  ```python
  node.prev = None  # 이전 노드 참조 즉시 해제
  node.next = None  # 다음 노드 참조 즉시 해제
  ```
  - 노드를 단순히 체인에서 분리하더라도 `node.prev`와 `node.next`가 다른 노드를 계속 가리키고 있으면 고립된 순환 참조(Isolated Cycle)가 형성되어 참조 카운트가 0으로 떨어지지 않습니다.
  - 이 경우 Cycle GC가 동작할 때까지 메모리가 반환되지 않고 힙을 점유하게 됩니다.
  - 따라서 노드 분리 시 포인터를 명시적으로 `None`으로 절단함으로써 참조 카운트를 즉시 0으로 유도하여 실시간 메모리 회수를 보장합니다.

### 7.6 실제 Redis의 근사 LRU (Approximated LRU) vs Mini Redis의 정확한 O(1) LRU 비교
- **실제 C Redis (`server.c` / `evict.c`)의 접근 방식**:
  - 수억 개의 키를 서비스하는 프로덕션 Redis는 키당 16바이트(앞/뒤 포인터 각 8바이트)의 연결 리스트 메모리 오버헤드를 허용할 수 없습니다.
  - 따라서 객체 헤더(`robj`)에 24비트 크기의 축약 타임스탬프(`lruclock`)만을 기록합니다.
  - Eviction 발생 시 전체 정렬 리스트 대신 무작위로 $N$개(기본값 5개, `maxmemory-samples 5`)의 키를 표본 추출(Sampling)한 뒤 그중 가장 오래된 키를 제거하는 **근사 LRU (Approximated LRU)**를 채택합니다.
- **Mini Redis의 엄격한 학술적 접근 방식**:
  - 본 미션에서는 정확한 알고리즘 메커니즘 규명을 위해 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189)를 사용하여 **100% 완전한 결정론적(Exact Deterministic) LRU**를 구현하였습니다.
  - `Entry` 객체가 자신의 `lru_node`를 직접 가리켜 표본 추출 없이 상시 절대적인 $O(1)$ 시간 내에 정확한 최신화 및 가장 오래된 키 축출을 완벽하게 보장합니다.

### 7.7 전체 명령어 및 자료구조 연산 복잡도 종합 매트릭스

| 명령어 / 연산 | 내부 수행 로직 | 평균 시간 복잡도 | 최악 시간 복잡도 | 공간 복잡도 |
| :--- | :--- | :---: | :---: | :---: |
| **SET (신규)** | 해시 인덱싱 + DLL 헤드 삽입 + 힙 선행스윕 | $O(1)$ | $O(N)$ (리사이징 시) | $O(1)$ |
| **SET (덮어쓰기)** | 해시 탐색 + 값 교체 + DLL 헤드 이동 | $O(1)$ | $O(K)$ (체인 충돌 시) | $O(1)$ |
| **GET** | 선행스윕 + 해시 탐색 + DLL 헤드 이동 | $O(1)$ | $O(K)$ (체인 충돌 시) | $O(1)$ |
| **DEL** | 해시 삭제 + DLL 노드 제거 + 메모리 차감 | $O(1)$ | $O(K)$ (체인 충돌 시) | $O(1)$ |
| **EXISTS** | 선행스윕 + 해시 버킷 존재 확인 | $O(1)$ | $O(K)$ (체인 충돌 시) | $O(1)$ |
| **DBSIZE** | 해시맵 `_size` 변수 직접 조회 | $O(1)$ | $O(1)$ | $O(1)$ |
| **KEYS** | 전체 버킷 및 체인 전수 순회 | $O(N)$ | $O(N)$ | $O(N)$ |
| **CONFIG SET** | 정수 파싱 및 변수 할당 | $O(1)$ | $O(1)$ | $O(1)$ |
| **INFO memory** | 메모리 지표 문자열 포맷팅 | $O(1)$ | $O(1)$ | $O(1)$ |
| **EXPIRE** | 선행스윕 + 엔트리 조회 + 힙 `push` | $O(\log M)$ | $O(\log M)$ | $O(1)$ |
| **TTL** | 선행스윕 + 엔트리 조회 + 시간 차 계산 | $O(1)$ | $O(K)$ (체인 충돌 시) | $O(1)$ |
| **LRU Eviction** | DLL `remove_back` + 해시 삭제 | $O(1)$ | $O(K)$ (체인 충돌 시) | $O(1)$ |

*(여기서 $N$은 총 키 개수, $M$은 TTL 설정된 키 개수, $K$는 동일 버킷 내 체인 길이 (평균 $K \le 0.75$))*

---

## 📚 8. 용어 대조 색인표 (Alphabetical Technical Glossary)

| 영문 용어 (Term) | 국문 명칭 | 정의 및 핵심 요약 | 관련 소스코드 |
| :--- | :--- | :--- | :--- |
| **Avalanche Effect** | 눈사태 효과 | 입력값의 사소한 변화(1비트)가 출력 해시값 전체의 급격한 변화를 유발하는 성질 | [`src/hashmap.py#L27`](../src/hashmap.py#L27) |
| **Complete Binary Tree** | 완전 이진 트리 | 마지막 레벨을 제외한 모든 레벨이 꽉 차 있고, 마지막 레벨은 왼쪽부터 채워진 트리 | [`src/heap.py#L24`](../src/heap.py#L24) |
| **Doubly Linked List** | 이중 연결 리스트 | 노드가 이전(`prev`)과 다음(`next`) 노드의 주소를 모두 보관하는 양방향 선형 자료구조 | [`src/doubly_linked_list.py`](../src/doubly_linked_list.py) |
| **Eviction** | 캐시 축출/제거 | 메모리 한도 초과 시 교체 알고리즘(LRU)에 따라 기존 데이터를 제거하는 메커니즘 | [`src/store.py#L191`](../src/store.py#L191) |
| **Heap Invariant** | 힙 불변성 | 부모 노드의 값이 항상 자식 노드들의 값보다 작거나 같아야 하는 최소 힙의 성질 | [`src/heap.py#L84`](../src/heap.py#L84) |
| **Incremental Rehashing** | 점진적 재해싱 | 대규모 해시맵 리사이징 시 전체 재해싱을 분할하여 요청마다 조금씩 수행하는 기법 | 본 문서 7.2절 |
| **Lazy Deletion** | 지연 삭제 | 데이터 수정 시 즉시 물리적으로 지우지 않고, 버전 태깅으로 무효화 후 접근 시점에 삭제 | [`src/store.py#L117`](../src/store.py#L117) |
| **LFU** | 최저 빈도 사용 | Least Frequently Used: 참조 빈도수가 가장 낮은 키를 우선 축출하는 캐시 알고리즘 | 본 문서 4.2절 |
| **Load Factor** | 로드 팩터 (부하율) | 해시맵에 저장된 항목 수 대비 버킷 용량의 비율 ($\alpha = N/M$, 임계값 0.75) | [`src/hashmap.py#L23`](../src/hashmap.py#L23) |
| **LRU** | 최근 최소 사용 | Least Recently Used: 가장 오랫동안 참조되지 않은 키를 우선 축출하는 캐시 알고리즘 | [`src/store.py#L143`](../src/store.py#L143) |
| **Min-Heap** | 최소 힙 | 가장 작은 원소가 항상 루트에 위치하도록 정렬되는 완전 이진 트리 우선순위 큐 | [`src/heap.py`](../src/heap.py) |
| **Monotonic Clock** | 단조 시계 | 역행하지 않고 상시 단조 증가하여 정확한 시간 간격을 측정하는 시스템 타이머 | [`src/store.py#L27`](../src/store.py#L27) |
| **OOM (Out Of Memory)** | 메모리 초과 | 허용된 최대 메모리 용량(`maxmemory`)을 초과하여 명령 실행이 거부되는 예외 상태 | [`src/store.py#L34`](../src/store.py#L34) |
| **REPL** | 대화형 쉘 | Read-Eval-Print Loop: 사용자 입력을 읽어 실행하고 결과를 즉시 출력하는 인터페이스 | [`src/cli.py#L219`](../src/cli.py#L219) |
| **Sentinel Node** | 센티넬(더미) 노드 | 경계 조건(None 분기)을 없애기 위해 리스트 양 끝에 상시 배치하는 더미 노드 | [`src/doubly_linked_list.py#L53`](../src/doubly_linked_list.py#L53) |
| **Separate Chaining** | 분리 체이닝 | 동일 해시 버킷에 매핑된 데이터들을 연결 리스트 체인으로 엮어 충돌을 해결하는 방식 | [`src/hashmap.py#L90`](../src/hashmap.py#L90) |
| **TTL** | 만료 시간 | Time-To-Live: 키-값 데이터가 저장소 내에서 유효하게 유지되는 잔여 수명(초) | [`src/store.py#L271`](../src/store.py#L271) |

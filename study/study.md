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

---

## 🎯 9. 미션 심층 스터디 및 핵심 질의응답 (Mission Deep-Dive Study & Technical Q&A)

본 장은 [`docs/b5_1_mission.md`](../docs/b5_1_mission.md) 및 [`docs/b5_1_eval.md`](../docs/b5_1_eval.md)에 제시된 핵심 구현 과제, 자료구조 설계 제약, CPython 내부 동작 메커니즘, $O(1)$ LRU 및 $O(\log N)$ TTL 달성 기믹, 그리고 10만 건 이상 대규모 확장 시의 최적화 방안을 심층 질의응답(Q&A) 형식으로 체계화하여 정리한 완전 학습 해설서입니다.

---

### 9.1 미션 개요 및 3대 핵심 구현 과제 (Mission Overview & Core Tasks)

Mini Redis 미션은 Python의 내장 해시/집합 컬렉션(`dict`, `set`, `collections`)을 일체 사용하지 않고, 오직 저수준 배열과 수작업 자료구조만을 활용하여 경량 인메모리 Key-Value 데이터 저장소를 밑바닥부터 직접 구현하는 과제입니다.

#### 1. 3대 핵심 자료구조 밑바닥 구현
- **센티넬 기반 이중 연결 리스트 ([`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189))**: 더미 센티넬 노드(`_head`, `_tail`)를 두어 경계 조건 분기를 제거하고, $O(1)$ 시간 복잡도로 노드 삽입, 삭제 및 순서 이동을 수행.
- **체이닝 해시맵 ([`HashMap`](../src/hashmap.py#L68-L203))**: `djb2` 다항 해시 함수와 이중 연결 리스트 기반의 분리 체이닝(Separate Chaining) 충돌 해결, 로드 팩터($\alpha > 0.75$) 초과 시 2배 동적 리사이징을 적용하여 평균 $O(1)$ 탐색 보장.
- **배열 기반 최소 힙 ([`MinHeap`](../src/heap.py#L24-L122))**: 파이썬 `list` 버퍼 위에 완전 이진 트리 인덱스 공식을 적용하여, 가장 먼저 만료되는 키를 $O(1)$에 확인(`peek`)하고 $O(\log N)$에 처리하는 TTL 우선순위 큐 구축.

#### 2. 핵심 기능 및 10대 명령어 세트
1. **String 기본 연산 (6개)**: `SET`, `GET`, `DEL`, `EXISTS`, `DBSIZE`, `KEYS`
2. **메모리 관리 연산 (2개)**: `CONFIG SET maxmemory <bytes>`, `INFO memory`
3. **TTL 만료 관리 연산 (2개)**: `EXPIRE <key> <seconds>`, `TTL <key>`

#### 3. 고급 캐시 정책 및 파이프라인
- **$O(1)$ LRU 자동 축출 (Eviction)**: `used_memory > maxmemory` 초과 시 가장 오래 참조되지 않은 키(LRU)부터 순차 자동 방출.
- **버전 기반 지연 삭제 (Lazy Deletion with Versioning)**: 키 덮어쓰기 시 `ttl_version`을 증가시켜 이전 힙 예약을 무효화함으로써 $O(N)$ 힙 탐색 없이 $O(\log N)$ 만료 파이프라인 완성.
- **대화형 CLI REPL**: `mini-redis>` 프롬프트와 `shlex` 기반 따옴표 파싱, Redis 표준 출력 규격(`OK`, `(nil)`, `(integer) N`, `(error) ...`) 완비.

---

### 9.2 Python List를 활용한 $O(1)$ 달성 원리와 CPython 아키텍처 심층 분석

#### Q. "내장 컬렉션(`dict`, `set`)을 쓰지 않고 직접 구현해야 한다면, 파이썬 `list`로 $O(1)$ 시간 복잡도를 달성하는 것이 가능한가요?"

> **결론**: 파이썬 `list`에서 전체 원소를 순회하는 검색(`x in list`, `list.index(x)`)은 $O(N)$이지만, 본 프로젝트에서는 `list`를 탐색용이 아닌 **고정 크기 1차원 버퍼(포인터 테이블)**로만 한정 사용하여 **$O(1)$ 접근**을 완벽하게 달성합니다.

#### 1. 인덱스 직행 접근 ($O(1)$ Indexing)
- C 언어의 1차원 배열과 마찬가지로, 파이썬 `list`에서 정수 인덱스로 원소에 접근하는 연산(`array[idx]`)은 메모리 주소 계산 산술 연산만 수행하므로 **순수 $O(1)$**입니다.
- 문자열 키를 `djb2` 해시 함수를 통해 $0 \le \text{idx} < \text{capacity}$ 범위의 정수 인덱스로 변환한 뒤, `self._buckets[idx]`로 $O(1)$ 시간에 해당 버킷으로 직행합니다.

#### 2. 해시 충돌과 분리 체이닝의 결합
- 서로 다른 키가 동일한 버킷 인덱스로 충돌하면, 각 버킷 슬롯에 할당된 직접 구현 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189) 체인에 노드를 연결합니다.
- 로드 팩터가 0.75를 초과하면 버킷 용량을 2배로 확장(`_resize`)하여 체인의 평균 길이를 0.75 이하로 짧게 유지하므로, 체인 순회 비용 또한 평균 $O(1)$로 수렴합니다.

#### 3. LRU 순서 갱신의 비밀: 포인터 역참조 (Pointer Dereferencing)
- 캐시 접근(`GET`/`SET`) 시 최근 참조된 키를 맨 앞으로 옮겨야 합니다.
- 일반적인 리스트 순회($O(N)$)를 피하기 위해, 해시맵의 [`Entry`](../src/store.py#L40-L64) 객체가 자신이 속한 연결 리스트 노드의 메모리 참조(`entry.lru_node`)를 직접 소유합니다.
- 해시맵 조회 즉시 `entry.lru_node`를 [`move_to_front()`](../src/doubly_linked_list.py#L131-L141)에 넘겨 앞뒤 포인터 4개만 재배선하므로 순수 $O(1)$에 최신화가 완료됩니다.

#### 4. CPython 내부 아키텍처 관점의 한계와 극복 방안
컴퓨터 아키텍처 및 CPython 레벨에서 C 언어 값 배열과 파이썬 `list`의 차이점 및 극복 방식은 다음과 같습니다:

```text
[ C 언어의 값 배열 (Array of Values) ]
┌─────────────────┬─────────────────┬─────────────────┐
│ Value 1 (정수)  │ Value 2 (정수)  │ Value 3 (정수)  │  <── 연속된 물리 메모리 (캐시 지역성 극대화)
└─────────────────┴─────────────────┴─────────────────┘

[ 파이썬 list의 포인터 배열 (Array of Pointers: PyListObject) ]
┌─────────────────┬─────────────────┬─────────────────┐
│ Pointer 0       │ Pointer 1       │ Pointer 2       │  <── ob_item 포인터 배열 (8바이트 주소값들)
└────────┬────────┴────────┬────────┴────────┬────────┘
         │                 │                 │
         ▼                 ▼                 ▼
     [PyObject 0]      [PyObject 1]      [PyObject 2]    <── 힙(Heap) 공간에 흩어진 객체들
     (헤더 + 데이터)   (헤더 + 데이터)   (헤더 + 데이터)
```

1. **시간 복잡도**: CPython의 `list`는 내부적으로 C 언어 구조체 `PyListObject`로 구현되어 있으며, `PyObject** ob_item`이라는 C 포인터 배열을 유지합니다. `list[i]` 접근 시 `ob_item + (i * sizeof(PyObject*))` 연산을 통해 $O(1)$ 시간에 해당 객체의 주소를 가져오므로 시간 복잡도상 하자는 전혀 없습니다.
2. **메모리 오버헤드와 캐시 미스 (Cache Miss)**:
   - C 언어 배열은 데이터 값이 연속된 메모리에 밀착되어 L1/L2 CPU 캐시 적중률이 극도로 높습니다.
   - 반면 파이썬 `list`는 힙 영역에 흩어진 객체를 포인터를 타고 역참조해야 하므로 캐시 지역성(Spatial Locality)이 떨어지고 객체 헤더(`PyObject_HEAD`: 16~24바이트) 오버헤드가 발생합니다.
3. **Mini Redis의 설계적 극복 방안**:
   - **`__slots__` 도입**: [`Node`](../src/doubly_linked_list.py#L27), [`_Pair`](../src/hashmap.py#L55), [`Entry`](../src/store.py#L51) 클래스에 `__slots__`를 선언하여 인스턴스별 `__dict__` 생성을 차단하고 C 언어 구조체 형태로 메모리를 약 60% 절감.
   - **정밀한 `used_memory` 표준 공식 적용**: 환경마다 다른 객체 헤더 크기 왜곡을 제거하기 위해 `used_memory = sum(len(utf8(key)) + len(utf8(value)))` 순수 바이트 합산 기준을 엄격히 고수.

---

### 9.3 별도 인덱스 파일 없이 인메모리 포인터로 데이터를 직행 탐색하는 원리

#### Q. "파이썬 `list`는 포인터만 가지고 있는데 어떻게 데이터를 찾아가나요? 별도의 인덱스 파일이 존재하는 건가요?"

> **결론**: Mini Redis는 디스크 파일 I/O 없이 100% RAM 메인 메모리 위에서 구동되는 순수 인메모리 데이터베이스입니다. 별도의 인덱스 파일이 존재하는 것이 아니라, **파이썬 `list` 자체가 메모리 상의 '버킷 색인 테이블'**이며 포인터 주소를 타고 힙 영역의 노드 객체로 직행합니다.

```text
[ 해시맵의 self._buckets 배열 (RAM 포인터 테이블) ]
  Slot 0: [ Pointer ] ──> DoublyLinkedList (Empty)
  Slot 1: [ Pointer ] ──> DoublyLinkedList (Empty)
  Slot 2: [ Pointer ] ──> DoublyLinkedList (Empty)
  Slot 3: [ Pointer ] ──> DoublyLinkedList (버킷 체인)
                             │
                             ▼
                      [ Node (MRU) ] <═══════════> [ Node (LRU) ]
                      data: _Pair                  data: _Pair
                      - key: "user:1"              - key: "user:2"
                      - value: "Alice"             - value: "Bob"
```

1. **인덱스 계산**: `SET user:1 "Alice"` 명령이 유입되면, `djb2` 해시 함수가 `"user:1"` 키를 정수 인덱스(예: `idx = 3`)로 변환합니다.
2. **포인터 직행 ($O(1)$)**: `self._buckets[3]`을 호출하면, CPython 내부에서 `ob_item + (3 * 8)` 메모리 오선(Offset)을 즉시 산출하여 3번 슬롯의 메모리 주소를 반환합니다.
3. **실제 데이터 도달**: 3번 슬롯의 포인터를 타고 가면 해당 위치에 할당된 `DoublyLinkedList` 인스턴스가 존재하며, 연결 리스트 체인 안의 `Node` $\rightarrow$ `_Pair(key="user:1", value="Alice")`를 즉시 참조하게 됩니다.

---

### 9.4 문자열 키의 정수 인덱스 변환 3단계 및 djb2 알고리즘 심층 분석

#### Q. "문자열 키(`'user:1'`)는 구체적으로 어떤 연산을 거쳐 버킷 배열의 정수 인덱스로 변환되나요?"

```text
[ 문자열 키: "user:1" ]
       │
       ▼  1단계: djb2 다항 해시 연산
[ 32비트 고유 정수 해시 코드: 2083492811 ]
       │
       ▼  2단계: 모듈로 압축 (% capacity, 예: capacity = 16)
[ 버킷 배열 정수 인덱스: 11 ] ──> buckets[11] $O(1)$ 직행
       │
       ▼  3단계: 분리 체이닝 노드 순회 및 키 일치 검증
[ Node._Pair.key == "user:1" 비교 확인 ]
```

#### djb2 해시 함수의 4대 핵심 원리

```python
def _hash_key(key: str, capacity: int) -> int:
    h = 5381  # 1. 초깃값 소수 (Magic Number)
    for ch in key:
        h = ((h << 5) + h) + ord(ch)  # 2. 33배 승수와 비트 시프트: (h * 33) + ord(ch)
    h = h & 0xFFFFFFFF  # 3. 32비트 마스킹 (부호 없는 32비트 정수화)
    return h % capacity  # 4. 버킷 용량으로 모듈로 인덱스 압축
```

1. **초깃값 소수 5381 (Magic Number)**:
   - 해시 초기값을 0이나 1이 아닌 홀수 소수 5381로 시작하여 비트 패턴을 초기에 넓게 분산시키고 충돌을 방지합니다.
2. **33배 승수 연산과 비트 시프트 `(h << 5) + h`**:
   - 문자열의 각 문자를 순회하며 이전 값에 33을 곱하고 문자 코드값(`ord(ch)`)을 더합니다.
   - CPU 차원에서 곱셈기 대신 비트 좌측 시프트(`h << 5`, 즉 $h \times 32$)와 덧셈(`+ h`)을 결합하여 극도로 빠르게 연산합니다.
   - 단 1글자만 바뀌어도 결과 비트가 폭포수처럼 무작위로 섞이는 **눈사태 효과(Avalanche Effect)**를 발생시킵니다.
3. **`& 0xFFFFFFFF` (32비트 마스킹)**:
   - 파이썬의 무제한 가변 정수(`int`) 상위 비트를 절단하여 C 언어의 32비트 부호 없는 정수(`uint32_t`) 오버플로우를 동일하게 재현합니다.
4. **`% capacity` (버킷 인덱스 압축)**:
   - 32비트 정수를 현재 버킷 배열 크기로 나눈 나머지를 취해 $0 \le \text{idx} < \text{capacity}$ 범위의 유효 인덱스를 확정합니다.

---

### 9.5 Separate Chaining 충돌 해결 및 동적 리사이징 5단계 파이프라인

#### Q. "해시 충돌이 발생했을 때의 CRUD 동작 과정과 로드 팩터 0.75 초과 시의 리사이징 과정을 상세히 설명해 주세요."

#### 1. 충돌 상황에서의 CRUD 동작 메커니즘
- **삽입 (`put`)**: `_hash_key`로 인덱스를 찾고 해당 버킷 리스트를 순회합니다. 기존 키가 있으면 `pair.value = value`로 값을 갱신하고, 없으면 체인 맨 뒤에 `insert_back(_Pair(key, value))`를 수행하여 $O(1)$에 노드를 추가합니다.
- **조회 (`get`)**: 버킷 인덱스로 직행 후 체인 리스트를 순회하며 `pair.key == key`인 노드를 찾아 값을 반환합니다.
- **삭제 (`remove`)**: [`bucket.nodes()`](../src/doubly_linked_list.py#L174-L188) 제너레이터로 순회 도중 일치하는 노드를 찾으면 [`bucket.remove_node(node)`](../src/doubly_linked_list.py#L117-L129)를 호출하여 포인터를 $O(1)$로 분리 제거합니다.

#### 2. 동적 리사이징 (Dynamic Resizing & Full Rehashing) 5단계

$$\text{로드 팩터 } (\alpha) = \frac{\text{저장된 엔트리 수 } (\text{size})}{\text{버킷 배열 크기 } (\text{capacity})}$$

로드 팩터가 임계값 **0.75**를 초과하면 버킷 체인의 평균 길이가 길어져 탐색 속도가 저하되므로, 즉시 2배 크기로 확장하는 리사이징을 수행합니다.

```text
[ HashMap.put(key, value) ]
           │
           ▼
1. 로드 팩터 검사: if size / capacity > 0.75:
           │
           ▼  (초과 시 _resize(capacity * 2) 구동)
2. 기존 버킷 배열 임시 보관: old_buckets = self._buckets
           │
           ▼
3. 2배 크기의 새로운 빈 DoublyLinkedList 배열 할당
           │
           ▼
4. 용량 갱신: self._capacity = new_capacity
           │
           ▼
5. 전수 재해싱 (Full Rehashing):
   old_buckets의 모든 _Pair에 대해 new_idx = _hash_key(pair.key, new_capacity) 재계산 후
   새 버킷 체인의 맨 뒤에 insert_back 재배치
           │
           ▼
[ 체인 평균 길이가 0.75 이하로 단축되어 상시 평균 O(1) 복원 완료 ]
```

---

### 9.6 $O(1)$ LRU 캐시 아키텍처와 포인터 역참조 (Pointer Dereference)

#### Q. "LRU 캐시 구현에서 왜 해시맵과 이중 연결 리스트를 결합해야 하며, 어떻게 $O(1)$ 갱신이 가능한가요?"

#### 1. 두 자료구조 결합의 필연성
- **해시맵 단독**: 키 조회가 $O(1)$로 빠르지만, 데이터의 시간적 사용 순서(Temporal Order)를 추적하거나 정렬할 수 없습니다.
- **연결 리스트 단독**: 맨 앞 삽입과 맨 뒤 삭제는 빠르지만, 특정 키가 어디 있는지 탐색하려면 $O(N)$ 전수 순회가 발생합니다.
- **결합 시너지**: 해시맵의 $O(1)$ 탐색과 연결 리스트의 $O(1)$ 포인터 이동을 결합하여 두 장점을 모두 취합니다.

#### 2. $O(1)$ 순서 최신화의 핵심: `Entry.lru_node` 포인터 역참조

```text
[ HashMap (키-엔트리 색인) ]
  "user:1" ──> Entry 객체 ──(lru_node 역참조 포인터)──┐
                                                        │ Direct Pointer O(1)
                                                        ▼
[ DoublyLinkedList (LRU 순서 큐) ]
  _head (센티넬) <───> [ Node("user:1") ] <───> [ Node("user:2") ] <───> _tail (센티넬)
  (MRU: 방금 참조됨)                                                      (LRU: 가장 오래 미사용)
```

- [`Entry`](../src/store.py#L40-L64) 객체가 `lru_node` 필드로 자신이 속한 `Node`의 주소를 직접 보유합니다.
- `GET` 또는 `SET` 호출 시 연결 리스트를 처음부터 검색하지 않고, `entry.lru_node`로 해당 노드의 물리 주소로 직행합니다.
- 노드의 앞뒤 포인터 4개만 재배선하는 [`move_to_front(node)`](../src/doubly_linked_list.py#L131-L141)를 호출하여 순수 $O(1)$에 `_head` 센티넬 바로 뒤(MRU)로 이동시킵니다.

#### 3. 더미 센티넬 노드(`_head`, `_tail`)의 경계 조건 제거 효과
- 리스트의 양 끝에 데이터가 없는 더미 센티넬 노드를 상시 유지하므로, 리스트가 비어 있거나 첫 번째 노드, 마지막 노드를 삭제할 때 `if node.prev is None:` 같은 예외 분기문이 일체 필요하지 않습니다.

#### 4. CRUD 및 Eviction 복잡도 매트릭스

| 연산 | 해시맵 역할 | 이중 연결 리스트 역할 | 최종 복잡도 |
| :--- | :--- | :--- | :---: |
| **`GET key`** | $O(1)$ 키 검색 및 `Entry` 반환 | `entry.lru_node`를 맨 앞(MRU)으로 이동 | **$O(1)$** |
| **`SET key val` (신규)** | $O(1)$ 키-엔트리 매핑 등록 | 맨 앞에 노드 삽입 후 `entry.lru_node` 연결 | **$O(1)$** |
| **`SET key val` (갱신)** | $O(1)$ 엔트리 값 덮어쓰기 | 기존 노드를 맨 앞으로 이동 | **$O(1)$** |
| **LRU 축출 (`_evict_if_needed`)** | 적출된 키를 $O(1)$로 해시맵에서 삭제 | `_tail.prev` 노드를 $O(1)$로 추출 및 분리 | **$O(1)$** |

---

### 9.7 최소 힙 TTL 만료 관리와 버전 기반 지연 삭제 (Lazy Deletion)

#### Q. "최소 힙을 사용할 때 특정 키의 TTL이 변경되거나 덮어써지면 $O(N)$ 힙 탐색이 발생하지 않나요? 이를 어떻게 해결했나요?"

#### 1. 최소 힙(Min-Heap)을 선택한 이유
- 매 명령어 실행마다 전체 키를 전수 순회($O(N)$)하며 만료 여부를 검사하면 극심한 병목이 발생합니다.
- 최소 힙은 가장 작은 만료 시각을 가진 원소를 항상 루트 노드(인덱스 0)에 유지하므로, **$O(1)$에 만료 여부를 확인(`peek`)**하고 **$O(\log N)$에 항목을 추출(`pop`)**할 수 있습니다.

#### 2. 버전 기반 지연 삭제 (Lazy Deletion with `ttl_version`) 메커니즘
최소 힙은 루트가 아닌 임의 위치의 노드를 탐색하여 삭제하는 연산이 $O(N)$이라는 태생적 한계가 있습니다. Mini Redis는 **버전 태깅(Versioning)**을 통해 이를 해결했습니다.

```text
[ 1. 최초 EXPIRE 설정 시 ]
  Entry("Alice", ttl_version=0, expire_at=100.0)
  MinHeap.push((100.0, "user:1", version=0))

[ 2. SET으로 키 덮어쓰기 또는 EXPIRE 재설정 시 ]
  Entry("Bob", ttl_version=1, expire_at=None)  <── ttl_version 1 증가!
  (옛 힙 노드 (100.0, "user:1", 0)은 찾아서 지우지 않고 그대로 방치)

[ 3. 선행 만료 스윕 (_sweep_expired) 시점 ]
  MinHeap.pop() ──> (100.0, "user:1", version=0) 추출
  검증: entry.ttl_version(1) != heap_version(0) 불일치!
  판정: 이미 무효화된 옛 예약이므로 O(1)에 무시하고 버림 (데이터 유지)
```

1. **버전 증가**: 키의 만료 시각이 변경되거나 값이 덮어써지면 `entry.ttl_version` 카운터를 1 증가시킵니다.
2. **신규 튜플 푸시**: 새로운 `(expire_at, key, ttl_version)` 튜플만 힙에 푸시하고, 이전 힙 노드는 $O(N)$으로 찾지 않고 그대로 둡니다.
3. **논리적 무효화 검증**: 선행 만료 스윕([`_sweep_expired`](../src/store.py#L117-L130)) 시 힙에서 꺼낸 튜플의 `version`과 실제 엔트리의 `ttl_version`이 일치할 때만 실제 물리 삭제([`_purge`](../src/store.py#L132-L141))를 수행합니다.

#### 3. 선행 만료 스윕의 $O(1)$ 즉시 탈출
- 최소 힙 불변성에 의해 "루트보다 만료 시각이 늦은 항목은 트리 내부에 존재할 수 없음"이 수학적으로 보장됩니다.
- 따라서 `self._ttl_heap.peek()[0] > now`이면 트리 전체의 모든 키가 유효함을 단 한 번의 검사로 확인하고 **$O(1)$에 즉시 루프를 탈출**합니다.

#### 4. 단조 시계 (`time.monotonic()`) 필수성
- `time.time()`(Wall-clock)은 사용자의 시스템 시계 수동 변경이나 NTP 시간 동기화 시 시간이 거꾸로 흐를 위험이 있습니다.
- `time.monotonic()`은 시스템 부팅 후 항상 단조 증가하는 하드웨어 타이머로, 왜곡 없이 정확한 상대 시간 경과를 측정합니다.

---

### 9.8 10만 건 이상 대규모 트래픽 대비 3대 성능 병목 및 실전 고도화 방안

10만 건 이상의 대규모 데이터셋 환경으로 확장할 때 예상되는 3대 병목 지점과 실전 해결책입니다.

#### 1. 해시맵 일괄 재해싱 레이턴시 스파이크 $\rightarrow$ 점진적 재해싱 (Incremental Rehashing)
- **병목**: 로드 팩터(0.75) 초과 시 10만 개 항목을 단일 요청 시점에 동기식으로 일괄 재해싱하면 이벤트 루프가 수백 ms 정지하는 Stop-the-World 현상이 발생합니다.
- **해결책**: 2개의 버킷 테이블(`ht0`, `ht1`)과 `rehashidx` 상태 변수를 유지하며, 클라이언트 요청(CRUD)이 유입될 때마다 소수의 버킷(예: 1~10개)씩 분할 이관합니다.

```python
class IncrementalHashMap:
    def __init__(self, capacity=8):
        self.ht0 = [DoublyLinkedList() for _ in range(capacity)]  # 기존 메인 버킷 테이블
        self.ht1 = None                                          # 리사이징 시 할당되는 신규 2배 버킷 테이블
        self.rehashidx = -1                                      # -1: 미진행, >=0: 현재 이관 중인 버킷 인덱스
        self.size0 = 0
        self.size1 = 0

    def _rehash_step(self, steps=1):
        """클라이언트 요청 시마다 1개 이상의 버킷을 분할 이관."""
        if self.rehashidx == -1:
            return

        while steps > 0 and self.size0 > 0:
            while len(self.ht0[self.rehashidx]) == 0:
                self.rehashidx += 1
                if self.rehashidx >= len(self.ht0):
                    self.ht0, self.ht1, self.rehashidx = self.ht1, None, -1
                    return

            bucket = self.ht0[self.rehashidx]
            while len(bucket) > 0:
                pair = bucket.remove_front()
                self.size0 -= 1
                new_idx = _hash_key(pair.key, len(self.ht1))
                self.ht1[new_idx].insert_back(pair)
                self.size1 += 1

            self.rehashidx += 1
            steps -= 1

            if self.rehashidx >= len(self.ht0):
                self.ht0, self.ht1, self.rehashidx = self.ht1, None, -1
```

- **CRUD 라우팅 규칙**:
  - `SET`: 무조건 `ht1`에만 신규 저장하여 `ht0`의 데이터 수를 지속 감소시킴.
  - `GET` / `DEL`: 먼저 `ht0`을 조회하고 없으면 `ht1`을 연속 검색하여 상시 $O(1)$ 속도 유지.

---

#### 2. KEYS 명령어의 풀 스캔 블로킹 $\rightarrow$ 커서 기반 비블로킹 순회 (`SCAN`)
- **병목**: 10만 건 이상의 키가 저장된 상태에서 `KEYS`를 실행하면 전체 버킷 체인을 $O(N)$ 풀 스캔하면서 CPU/네트워크 병목과 함께 서버 전체가 블로킹됩니다.
- **해결책**: 커서(Cursor)와 목표 개수(COUNT)를 기반으로 청크(Chunk) 단위로 분할 반환하는 `SCAN` 명령어를 도입합니다.

```python
def scan(self, cursor: int, count: int = 10):
    """커서 기반 분할 순회: (next_cursor, [keys...]) 반환."""
    if cursor >= self._capacity or cursor < 0:
        cursor = 0

    result_keys = []
    current_idx = cursor
    scanned = 0

    while len(result_keys) < count and scanned < self._capacity:
        bucket = self._buckets[current_idx]
        for pair in bucket:
            if not self._is_expired(pair.key):
                result_keys.append(pair.key)
                if len(result_keys) >= count:
                    break

        current_idx = (current_idx + 1) % self._capacity
        scanned += 1
        if current_idx == 0:
            break

    next_cursor = 0 if current_idx == 0 or scanned >= self._capacity else current_idx
    return next_cursor, result_keys
```

- **실제 Redis의 고급 기법: 비트 반전 커서 (Bit-Reversed Cursor)**:
  - 순회 도중 해시맵 리사이징이 발생하면 버킷이 분할되면서 키가 중복되거나 누락될 수 있습니다.
  - 실제 Redis는 최상위 비트(MSB)부터 증가시키는 **비트 반전 순회(Bit-Reversed Counting)**를 적용하여, 순회 도중 2배 확장이 일어나더라도 분할된 자식 버킷들이 연속으로 방문되도록 보장합니다.

---

#### 3. 무효 튜플 누적 및 미참조 키 메모리 누수 $\rightarrow$ 백그라운드 능동 만료 (Active Expiry Cron)
- **병목**: 지연 만료(Lazy Expiry)는 클라이언트가 접근할 때만 만료를 검사하므로, 클라이언트가 다시는 찾지 않는 키(Cold Key)가 있으면 영원히 메모리를 점유하는 메모리 누수가 발생합니다. 빈번한 덮어쓰기 시 힙 내부에 무효화된 튜플이 누적되는 문제도 있습니다.
- **해결책**: 백그라운드 타이머(Cron)를 통해 주기적으로 만료 키를 선제 소거하는 **확률적 능동 만료 (Probabilistic Active Expiry)**를 결합합니다.

```text
[ 백그라운드 능동 만료 주기 실행 (예: 초당 10회) ]
                   │
                   ▼
1. TTL 설정 키 공간에서 무작위 20개 표본 추출 (Sampling)
                   │
                   ▼
2. 표본 중 이미 만료된 키(expire_at <= now) 즉시 소거
                   │
                   ▼
3. 삭제된 키 비율 검사 (25% 임계 규칙)
         ┌─────────┴─────────┐
         ▼                   ▼
 [ 삭제 비율 > 25% ]   [ 삭제 비율 <= 25% ]
 (5개 초과 만료됨)     (5개 이하 만료됨)
         │                   │
         ▼                   ▼
  즉시 1단계부터        이번 주기 검사 종료
  반복 루프 재실행       (다음 주기까지 대기)
```

- **CPU 타임아웃 보호 (CPU Protection)**: 능동 만료 루프가 메인 스레드를 블로킹하지 않도록, **단일 실행 주기당 최대 실행 시간(예: 25ms 상한, CPU 성능의 25% 상한)**을 엄격히 제한하여 메인 요청 처리를 방해하지 않습니다.
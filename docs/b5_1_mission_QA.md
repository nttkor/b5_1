# Mini Redis 미션 구현 및 기술 분석 Q&A (b5_1_mission_QA)

본 문서는 [`docs/b5_1_mission.md`](file:///Users/mpeg46551/b5_1/docs/b5_1_mission.md)의 미션 요구사항, 과제 목표, 기능 명세에 대한 심층 기술 답변서입니다.  
모든 구현 항목은 Python 내장 컬렉션(`dict`, `set`, `collections`)을 일체 배제하고 밑바닥부터 직접 구현되었으며, 각 답변에는 해당 소스코드의 상대 경로 링크가 포함되어 있습니다.

> 💡 **연관 핵심 문서 상호 링크**:
> - 📚 **핵심 개념 및 기술 용어 백과사전**: [`study/study.md`](../study/study.md)
> - 🎯 **종합 평가문항 답변서**: [`docs/b5_1_eval_QA.md`](b5_1_eval_QA.md)
> - 📖 **프로젝트 메인 안내서**: [`README.md`](../README.md)
> - 🏗️ **아키텍처 및 상세 실행도**: [`study/README.md`](../study/README.md)

---

## 1. 미션 목적 및 개요

- **미션 목적**:  
  Redis가 고성능 In-Memory Key-Value 저장소로서 어떻게 O(1) 속도로 동작하는지, 내부 핵심 자료구조(이중 연결 리스트, 해시맵, 최소 힙)를 밑바닥부터 직접 구현하여 동작 원리를 깊이 체득하는 데 있습니다.  
  메모리 제한(`maxmemory`) 환경에서 발생하는 LRU 캐시 교체 정책과 TTL(Time-To-Live) 기반의 지연 만료 삭제 메커니즘을 완성도 높은 CLI 인터페이스로 구축합니다.

- **핵심 기술적 원칙**:
  1. **내장 컬렉션 금지**: Python `dict`, `set`, `collections` 사용을 엄격히 배제하고, 순수 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189), [`HashMap`](../src/hashmap.py#L68-L203), [`MinHeap`](../src/heap.py#L24-L122)을 결합합니다.
  2. **O(1) 시간 복잡도 보장**: LRU 추적 및 해시맵 키 조회가 평균 O(1) 시간 내에 수행됩니다.
  3. **메모리 회계 및 축출**: UTF-8 바이트 크기 기준의 메모리 사용량 계산 및 LRU 자동 축출(Eviction)을 지원합니다.

---

## 2. 구현 실현 항목 (Implemented Features)

### 2.1 String 타입 기본 명령어 (6개)
1. **SET key value**:  
   키와 값을 저장소에 저장하고 메모리 초과 시 LRU 축출을 수행하며, 기존 키 덮어쓰기 시 TTL을 초기화합니다.  
   - 구현 코드: [`MiniRedisStore.set()`](../src/store.py#L155-L189)
2. **GET key**:  
   만료 시각을 선행 검사(`_sweep_expired`)한 후, 유효한 경우 값을 반환하고 LRU 맨 앞(MRU)으로 위치를 갱신합니다.  
   - 구현 코드: [`MiniRedisStore.get()`](../src/store.py#L206-L224)
3. **DEL key**:  
   키를 해시맵, LRU 리스트, 메모리 사용량 카운트에서 완전히 제거합니다.  
   - 구현 코드: [`MiniRedisStore.delete()`](../src/store.py#L226-L241), [`MiniRedisStore._purge()`](../src/store.py#L132-L141)
4. **EXISTS key**:  
   만료 정리 후 키가 해시맵 내에 유효하게 존재하는지 여부를 1 또는 0으로 반환합니다.  
   - 구현 코드: [`MiniRedisStore.exists()`](../src/store.py#L243-L251)
5. **DBSIZE**:  
   현재 저장소에 저장된 유효한 키의 총 개수를 반환합니다.  
   - 구현 코드: [`MiniRedisStore.dbsize()`](../src/store.py#L253-L260)
6. **KEYS**:  
   저장소 내 모든 유효한 키의 목록을 배열 형식으로 수집하여 반환합니다.  
   - 구현 코드: [`MiniRedisStore.keys()`](../src/store.py#L262-L269)

### 2.2 메모리 관리 명령어 (2개)
1. **CONFIG SET maxmemory bytes**:  
   최대 메모리 제한 바이트를 설정(0은 무제한)합니다.  
   - 구현 코드: [`execute_command() CONFIG 분기`](../src/cli.py#L182-L189)
2. **INFO memory**:  
   현재 `used_memory`, `maxmemory`, `evicted_keys` 통계를 출력합니다.  
   - 구현 코드: [`execute_command() INFO 분기`](../src/cli.py#L191-L198)

### 2.3 TTL 관리 명령어 (2개)
1. **EXPIRE key seconds**:  
   키의 만료 시간(초)을 설정하며, 0 이하인 경우 즉시 만료 삭제합니다.  
   - 구현 코드: [`MiniRedisStore.expire()`](../src/store.py#L271-L300)
2. **TTL key**:  
   남은 만료 시간을 초 단위 정수로 반환합니다 (미존재 시 `-2`, 만료시간 미설정 시 `-1`).  
   - 구현 코드: [`MiniRedisStore.ttl()`](../src/store.py#L302-L323)

### 2.4 CLI REPL 인터페이스
- `shlex` 모듈을 활용하여 큰따옴표가 포함된 값(`"Alice in Wonderland"`)을 안전하게 파싱하고, Redis 표준 형식(`OK`, `(nil)`, `(integer) N`, `"(bulk)"`, `(error) ...`)으로 출력합니다.  
- 구현 코드: [`execute_command()`](../src/cli.py#L122-L216), [`run_repl()`](../src/cli.py#L219-L236)

---

## 3. 기능 요구사항 심층 Q&A 및 기술 분석

### Q1. 이중 연결 리스트는 어떻게 구현되었으며 왜 모든 연산이 O(1)인가?
- **답변**:  
  [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189)는 `_head`와 `_tail`이라는 2개의 센티넬(더미) 노드를 생성자에서 미리 연결해 둡니다([`__init__`](../src/doubly_linked_list.py#L53-L59)).  
  이로 인해 첫 번째 노드 삽입이나 마지막 노드 삭제 시 `None` 여부를 검사하는 분기문이 완전히 배제됩니다.  
  - 맨 앞 삽입: [`insert_front()`](../src/doubly_linked_list.py#L61-L75) 및 [`_link_after()`](../src/doubly_linked_list.py#L143-L153)를 통해 4개의 포인터 재배선만으로 O(1)에 수행됩니다.
  - 임의 노드 제거: [`remove_node()`](../src/doubly_linked_list.py#L117-L129)는 노드의 `prev`와 `next` 포인터를 직접 연결하여 O(1)에 리스트에서 분리합니다.
  - 맨 앞 이동: [`move_to_front()`](../src/doubly_linked_list.py#L131-L141)는 `node.prev.next = node.next`로 노드를 떼어낸 후 `_head` 뒤로 즉시 링크하여 O(1)에 완료됩니다.

### Q2. 해시맵의 해시 함수와 체이닝 충돌 해결, 리사이징은 어떻게 동작하는가?
- **답변**:  
  - **해시 함수**: [`_hash_key()`](../src/hashmap.py#L27-L44)는 Bernstein의 djb2 알고리즘을 사용합니다. 초기값 5381에서 시작하여 각 문자에 대해 `((h * 33) + ord(ch)) & 0xFFFFFFFF` 연산을 수행하고 최종적으로 `h % capacity`로 인덱스를 균등하게 분산합니다.
  - **체이닝 충돌 해결**: 각 버킷은 독립적인 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189) 인스턴스로 구성됩니다([`HashMap.__init__`](../src/hashmap.py#L80-L88)). 충돌 발생 시 [`_Pair(key, value)`](../src/hashmap.py#L47-L65) 노드를 체인 뒤에 추가합니다([`put()`](../src/hashmap.py#L90-L109)).
  - **동적 2배 리사이징**: 저장된 엔트리 수 `_size` 대비 버킷 수 `_capacity`의 비율이 로드 팩터 임계값 0.75를 넘으면 [`_resize()`](../src/hashmap.py#L188-L203)가 호출되어 버킷 배열을 2배로 확장하고 전체 키-값 쌍을 새 버킷 배열에 재해싱하여 재배치합니다.

### Q3. TTL 만료 관리에 최소 힙(Min-Heap)이 적합한 이유와 지연 삭제(Lazy Deletion) 전략은 무엇인가?
- **답변**:  
  - **최소 힙의 적합성**: 전체 키 중 "가장 먼저 만료될 키"를 매번 전체 탐색(O(N))하지 않고 루트 노드에서 O(1)에 확인([`MinHeap.peek()`](../src/heap.py#L67-L74))하고 O(log N)에 추출([`MinHeap.pop()`](../src/heap.py#L49-L65))할 수 있기 때문입니다.
  - **지연 삭제 및 버전 관리**: 힙 중간에 있는 임의 요소를 삭제하는 것은 O(N) 비용이 듭니다. 따라서 키의 TTL이 갱신되거나 덮어쓰여질 때 [`entry.ttl_version`](../src/store.py#L64)을 1 증가시켜 기존 힙 예약을 무효화합니다. 이후 [`_sweep_expired()`](../src/store.py#L117-L130)에서 힙 루트를 꺼낼 때 엔트리의 만료 시각 및 버전이 정확히 일치하는 경우에만 실제 삭제([`_purge()`](../src/store.py#L132-L141))를 수행합니다.

### Q4. 메모리 제한(maxmemory)과 LRU 축출 흐름은 어떻게 동작하는가?
- **답변**:  
  - **메모리 회계 공식**: [`_entry_size()`](../src/store.py#L88-L101)에서 `len(utf8(key)) + len(utf8(value))`로 순수 데이터 바이트만 누적하여 [`used_memory`](../src/store.py#L84)를 유지합니다.
  - **OOM 선행 방어**: 단일 엔트리 크기 자체가 `maxmemory`를 초과하면 저장을 즉시 거부하고 [`OOMError`](../src/store.py#L34-L37)를 발생시킵니다([`MiniRedisStore.set()`](../src/store.py#L170-L173)).
  - **LRU 축출 루프**: 새 엔트리 삽입 후 `used_memory > maxmemory`인 경우, [`_evict_if_needed()`](../src/store.py#L191-L204)가 실행되어 LRU 리스트의 맨 뒤([`remove_back()`](../src/doubly_linked_list.py#L103-L115))에서 가장 오래된 키를 꺼내어 해시맵과 메모리에서 제거하고 [`evicted_keys`](../src/store.py#L86)를 1씩 증가시킵니다.

### Q5. 에러 처리 표준은 어떻게 구현되었는가?
- **답변**:  
  [`src/cli.py`](../src/cli.py#L29-L32)에 정의된 표준 메시지 형식을 준수합니다:
  - 알 수 없는 명령: `(error) ERR unknown command '<cmd>'` ([`_fmt_err`](../src/cli.py#L77-L87))
  - 인자 개수 오류: `(error) ERR wrong number of arguments for '<cmd>' command`
  - 정수 파싱 실패: `(error) ERR value is not an integer or out of range`
  - 메모리 초과: `(error) OOM command not allowed when used_memory > 'maxmemory'`

---

## 4. 보너스 과제 대비 및 확장 아키텍처

1. **동적 배열 직접 구현**: 파이썬 리스트 슬라이싱 대신 capacity와 size를 관리하는 DynamicArray 클래스를 구현하여 [`HashMap`](../src/hashmap.py#L68-L203)의 버킷 테이블과 [`MinHeap`](../src/heap.py#L24-L122) 저장소에 100% 동일한 인터페이스로 교체 가능합니다.
2. **스택/큐/덱 활용**: 본 프로젝트의 [`DoublyLinkedList`](../src/doubly_linked_list.py#L40-L189)는 `insert_front`, `insert_back`, `remove_front`, `remove_back`을 모두 O(1)로 제공하므로 그 자체로 완전한 데크(Deque), 스택, 큐의 역할을 수행합니다.
3. **이진 트리 / BST / Pub/Sub**: 연결 리스트 노드를 채널 구독자 큐로 확장하여 메시지 브로커 기능을 손쉽게 결합할 수 있습니다.

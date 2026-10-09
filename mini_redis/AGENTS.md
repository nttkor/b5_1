# mini_redis 모듈 전용 규칙 (Always-On Rules: GEMINI.md / AGENTS.md)

- **파일 위치**: `mini_redis/` 디렉터리 (`GEMINI.md`, `AGENTS.md`)
- **역할**: Mini Redis 핵심 자료구조 및 스토리지 엔진 구현을 위한 모듈 레벨 지침.

---

## 1. 핵심 제약 및 구현 원칙

### ① 내장 컬렉션 절대 사용 금지
- Python 내장 자료형인 `dict`, `set`, `collections` 모듈의 일체 사용을 금지합니다.
- 버킷 및 힙 내부 저장소로 사용하는 `list`는 고정 인덱스 접근용 배열 목적으로만 제한적으로 사용합니다.

### ② 시간 복잡도 준수
- **이중 연결 리스트 (`doubly_linked_list.py`)**:
  - `insert_front`, `insert_back`, `remove_front`, `remove_back`, `remove_node`, `move_to_front` 모두 $O(1)$ 유지.
  - Sentinel(더미 노드) 구조 유지.
- **해시맵 (`hashmap.py`)**:
  - `djb2` 다항 해시 함수 적용.
  - 체이닝(이중 연결 리스트 재사용)을 통한 충돌 처리.
  - 로드 팩터 $0.75$ 초과 시 2배 리사이즈 및 전체 재해싱.
- **최소 힙 (`heap.py`)**:
  - 완전 이진 트리 기반 배열 저장소.
  - 삽입/삭제 시 `_heapify_up`, `_heapify_down`으로 $O(\log N)$ 힙 속성 유지.
  - TTL 만료 관리를 위한 `(expire_at, key, version)` 구조.
- **스토어 및 LRU/TTL (`store.py`)**:
  - LRU 갱신 $O(1)$: 해시맵으로 노드 포인터 조회 후 리스트 front로 이동.
  - 만료 키 처리: Lazy deletion(버전 검증) 기법 사용.
  - `used_memory` 계산: $\sum(\text{len}(\text{utf8}(key)) + \text{len}(\text{utf8}(value)))$.
  - 단일 키+값 크기가 `maxmemory` 초과 시 OOM 에러 처리.

### ③ 주석 및 코드 보존
- 기존 주석 및 설계 로직 100% 보존.
- 모든 함수와 메서드에 `Args`, `Returns`, `Raises` 상세 docstring 유지.

### ④ 상호 동기화 관리
- `mini_redis/GEMINI.md`와 `mini_redis/AGENTS.md`는 항상 100% 동일하게 유지합니다.

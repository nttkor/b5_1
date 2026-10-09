# b5-1 Mini Redis

CLI 기반 Mini Redis. 해시맵/이중 연결 리스트/힙을 밑바닥부터 구현하고, 이걸 조합해
LRU 캐시 제거와 TTL 만료를 동작시킨다. `dict`, `set`, `collections`는 코드 전체에서
쓰지 않는다.

## 개발 환경

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.12 (요구사항: 3.8 이상) |
| 외부 의존성 | 없음 (표준 라이브러리만 사용: `time`, `shlex`) |

## 실행 방법

```bash
python main.py
```

```
mini-redis> SET user:1 "Alice"
OK
mini-redis> GET user:1
"Alice"
mini-redis> exit
```

자체 검증 스크립트:

```bash
python test_mini_redis.py
```

## 폴더 구조

```
codyssey-b5-1/
├── main.py                     # 엔트리 포인트
├── test_mini_redis.py          # assert 기반 자체 테스트
└── mini_redis/
    ├── doubly_linked_list.py   # 이중 연결 리스트 (sentinel 기반, O(1) 삽입/삭제/이동)
    ├── hashmap.py               # 체이닝 해시맵 (직접 설계한 해시 함수 + 로드팩터 0.75 리사이즈)
    ├── heap.py                  # 최소 힙 (배열 기반, TTL 만료 관리용)
    ├── store.py                 # 위 세 자료구조를 조합한 LRU+TTL 저장소
    └── cli.py                   # 명령 파싱/실행/Redis 스타일 출력
```

## 자료구조 설계

### 이중 연결 리스트 (`doubly_linked_list.py`)

head/tail에 더미(sentinel) 노드를 둬서 "리스트가 비었을 때" 같은 None 분기를 없앴다.
`insert_front`, `insert_back`, `remove_front`, `remove_back`, `remove_node`, `move_to_front`
전부 노드 포인터만 조작하므로 O(1)이다. 이 구조는 두 곳에서 재사용된다:

1. 해시맵 버킷의 충돌 체인
2. LRU 사용 순서 추적 (front = 최근 사용, back = 가장 오래됨)

### 해시맵 (`hashmap.py`)

해시 함수는 djb2 계열 다항 해시를 직접 짰다: `h = h*33 + ord(ch)`를 각 문자에 대해
누적하고 버킷 개수로 나눈 나머지를 인덱스로 쓴다. 충돌은 체이닝(버킷마다 연결 리스트)으로
푼다. `size / capacity > 0.75`가 되는 순간 버킷 수를 2배로 늘리고 전체 항목을 재해싱한다.

### 최소 힙 (`heap.py`)

배열(list) 기반 완전 이진 트리. `(expire_at, key, version)` 튜플을 담고 `expire_at`
기준으로 정렬한다. `_heapify_up`/`_heapify_down`으로 삽입/삭제 시 힙 성질을 유지한다.

### LRU + TTL 저장소 (`store.py`)

세 구조를 묶는 조립 계층이다. 힙은 임의 위치의 항목을 지울 수 없다는 한계가 있어서,
키를 덮어쓰거나 지울 때는 `ttl_version`을 올려 "예약된 힙 항목을 무효화"하고, 힙에서
꺼낼 때 버전이 안 맞으면 그냥 버리는 lazy deletion 전략을 썼다.

## 명령어

| 분류 | 명령어 |
|---|---|
| String | `SET key value`, `GET key`, `DEL key`, `EXISTS key`, `DBSIZE`, `KEYS` |
| 메모리 | `CONFIG SET maxmemory bytes`, `INFO memory` |
| TTL | `EXPIRE key seconds`, `TTL key` |
| 종료 | `exit` / `quit` |

`used_memory`는 `Σ(len(utf8(key)) + len(utf8(value)))`로 계산하며, 자료구조 오버헤드는
포함하지 않는다. `maxmemory > 0`이고 SET 이후 초과하면 LRU 순서(가장 오래 안 쓴 키)부터
`used_memory <= maxmemory`가 될 때까지 제거하고 `evicted_keys`를 누적한다. 단일
key+value 자체가 maxmemory보다 크면 저장하지 않고 OOM 에러를 낸다.

## 제약 준수

`dict`, `set`, `collections`는 프로젝트 전체에서 사용하지 않는다. 버킷 배열/힙 내부
저장소로 쓰인 파이썬 `list`는 "고정 인덱스 접근 저장소"로만 쓰였고, 해시맵/캐시 로직
자체는 전부 직접 구현했다.

## 보너스

이번 제출에는 보너스 과제(동적 배열, 스택/큐/덱 문서화, 이진 트리, BST, Pub/Sub)는
포함하지 않았다. 필수 요구사항 구현과 검증에 집중했다.

## 구술 평가 대비 문서

`READYOU.md`에 과제 목표(3번 항목)에서 요구하는 설명들을 코드 근거와 함께 정리했다.

"""Mini Redis 핵심 패키지 (src).

본 패키지는 Python 내장 컬렉션(dict, set, collections)을 일체 사용하지 않고
밑바닥부터 직접 구현한 자료구조(이중 연결 리스트, 체이닝 해시맵, 최소 힙)를 기반으로
LRU 캐시 교체 알고리즘과 TTL 만료 정책을 지원하는 In-Memory Key-Value 저장소 엔진입니다.

모듈 구성:
    - doubly_linked_list: 더미 센티넬 노드를 활용한 O(1) 이중 연결 리스트
    - hashmap: djb2 해시 함수와 체이닝 및 동적 2배 리사이징을 지원하는 해시맵
    - heap: 배열 기반 완전 이진 트리 최소 힙 (TTL 만료 시간 우선순위 큐)
    - store: HashMap + LRU List + TTL MinHeap을 결합한 통합 저장소 엔진 (MiniRedisStore)
    - cli: Redis 프로토콜 스타일의 입출력을 지원하는 대화형 REPL 인터페이스
"""

from .doubly_linked_list import DoublyLinkedList, Node	# O(1) 연산을 지원하는 이중 연결 리스트 및 노드 클래스 임포트
from .hashmap import HashMap	# 체이닝 및 동적 확장을 지원하는 순수 해시맵 클래스 임포트
from .heap import MinHeap	# TTL 만료 시각 관리를 위한 배열 기반 최소 힙 클래스 임포트
from .store import Entry, MiniRedisStore, OOMError	# 핵심 인메모리 저장소 엔진, 엔트리 및 OOM 예외 클래스 임포트
from .cli import execute_command, run_repl	# CLI 커맨드 파서/실행기 및 REPL 루프 함수 임포트

__all__ = [	# 외부 공개 심볼 목록 정의
    "DoublyLinkedList",	# 이중 연결 리스트 클래스
    "Node",	# 연결 리스트 노드 클래스
    "HashMap",	# 해시맵 클래스
    "MinHeap",	# 최소 힙 클래스
    "MiniRedisStore",	# 미니 레디스 통합 저장소 클래스
    "Entry",	# 저장소 엔트리 클래스
    "OOMError",	# 메모리 초과 예외 클래스
    "execute_command",	# 단일 명령어 실행 함수
    "run_repl",	# REPL 대화형 쉘 실행 함수
]	# 모듈 공개 심볼 목록 종료

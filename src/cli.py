"""대화형 REPL CLI 및 Redis 명령 파서/포맷터 모듈.

본 모듈은 사용자의 터미널 입력을 받아 `shlex` 기반으로 토큰화하고,
Redis 프로토콜 명세에 부합하는 응답 형식(OK, nil, integer, bulk, array, error)으로
출력하는 CLI 인터페이스를 제공합니다.

지원 명령어 세트:
    1. String 기본 연산 (6개):
       - SET <key> <value>  : 키에 값 저장 (LRU 최신화 및 메모리 초과 시 LRU 축출)
       - GET <key>          : 키의 값 조회 (만료 확인 후 성공 시 LRU 갱신)
       - DEL <key>          : 키 삭제 (모든 자료구조에서 제거)
       - EXISTS <key>       : 키 존재 여부 확인 (1 또는 0)
       - DBSIZE             : 유효 키의 총 개수 반환
       - KEYS               : 모든 유효 키 목록 출력
    2. 메모리 관리 (2개):
       - CONFIG SET maxmemory <bytes> : 최대 메모리 한도 설정 (0: 무제한)
       - INFO memory                  : used_memory, maxmemory, evicted_keys 출력
    3. TTL 관리 (2개):
       - EXPIRE <key> <seconds> : 만료 시간 설정 (초 단위)
       - TTL <key>              : 남은 만료 시간 조회 (-2, -1, 또는 잔여 초)
    4. 세션 제어:
       - EXIT / QUIT : REPL 세션 정상 종료
"""

import shlex	# 공백 및 따옴표(큰따옴표)를 올바르게 처리하기 위한 쉘 파싱 모듈 임포트

from .store import MiniRedisStore, OOMError	# 핵심 저장소 엔진 및 OOM 예외 클래스 임포트

ERR_UNKNOWN = "ERR unknown command '{0}'"	# 미지원/알 수 없는 명령어에 대한 Redis 표준 에러 메시지 템플릿
ERR_ARGS = "ERR wrong number of arguments for '{0}' command"	# 인자 개수 불일치 에러 메시지 템플릿
ERR_NOT_INT = "ERR value is not an integer or out of range"	# 정수 파싱 실패 또는 범위 초과 에러 메시지
ERR_OOM = "OOM command not allowed when used_memory > 'maxmemory'"	# 메모리 한도 초과 시 출력하는 OOM 에러 메시지

EXIT_SENTINEL = "__EXIT__"	# REPL 종료를 감지하기 위한 내부 센티넬 문자열 상수 정의


def _fmt_ok():	# Redis 표준 OK 응답 문자열 포맷터 함수 정의
    """성공 시 반환하는 Redis 표준 'OK' 문자열을 생성합니다.

    Returns:
        str: "OK"
    """
    return "OK"	# OK 문자열 반환


def _fmt_nil():	# Redis 표준 nil 응답 문자열 포맷터 함수 정의
    """존재하지 않거나 만료된 키 조회 시 반환하는 Redis 표준 '(nil)' 문자열을 생성합니다.

    Returns:
        str: "(nil)"
    """
    return "(nil)"	# (nil) 문자열 반환


def _fmt_int(n):	# Redis 정수형 응답 문자열 포맷터 함수 정의
    """정수형 결과를 Redis 표준 형식으로 포맷팅합니다.

    Args:
        n (int): 출력할 정수값.

    Returns:
        str: "(integer) {n}"
    """
    return f"(integer) {n}"	# (integer) 형식 문자열 반환


def _fmt_bulk(s):	# Redis 문자열(Bulk String) 응답 포맷터 함수 정의
    """문자열 값을 따옴표로 감싼 Redis Bulk String 형식으로 포맷팅합니다.

    Args:
        s (str): 출력할 문자열 값.

    Returns:
        str: '"{s}"'
    """
    return f'"{s}"'	# 쌍따옴표로 감싼 문자열 반환


def _fmt_err(msg):	# Redis 에러 응답 포맷터 함수 정의
    """에러 메시지를 Redis 표준 형식으로 포맷팅합니다.

    Args:
        msg (str): 에러 본문 메시지.

    Returns:
        str: "(error) {msg}"
    """
    return f"(error) {msg}"	# (error) 접두사가 붙은 에러 문자열 반환


def _fmt_array(items):	# Redis 배열(Array) 응답 포맷터 함수 정의
    """키 목록 배열을 순번이 매겨진 Redis 스타일 형식으로 포맷팅합니다.

    배열이 비어 있으면 "(empty array)"를 반환합니다.

    Args:
        items (list[str]): 출력할 문자열 항목들의 리스트.

    Returns:
        str: 1부터 시작하는 순번 목록 또는 "(empty array)".
    """
    if not items:	# 항목 목록이 비어 있는지 확인
        return "(empty array)"	# 비어 있으면 (empty array) 반환
    return "\n".join(f'{i}. "{item}"' for i, item in enumerate(items, start=1))	# 1부터 번호를 매겨 줄바꿈 결합 반환


def _parse_int(token):	# 문자열 토큰을 안전하게 정수로 변환하는 내부 헬퍼 함수 정의
    """문자열 토큰을 정수로 파싱하며, 실패 시 None을 반환합니다.

    Args:
        token (str): 파싱할 문자열.

    Returns:
        int or None: 파싱된 정수값 또는 실패 시 None.
    """
    try:	# 정수 변환 시도 예외 블록 시작
        return int(token)	# 정수형으로 변환하여 반환
    except ValueError:	# 숫자가 아닌 문자열인 경우
        return None	# None 반환


def execute_command(store, line):	# 단일 명령어 라인을 파싱하고 실행하여 결과를 포맷팅하는 함수 정의
    """한 줄의 명령어를 파싱하여 저장소에서 실행하고 결과 문자열을 반환합니다.

    REPL 환경과 테스트 스위트 양쪽에서 공통으로 호출되는 진입점 함수입니다.
    빈 줄인 경우 None을 반환하며, 종료 명령인 경우 EXIT_SENTINEL을 반환합니다.

    Args:
        store (MiniRedisStore): 명령을 실행할 저장소 엔진 인스턴스.
        line (str): 사용자가 입력한 명령어 문자열.

    Returns:
        str or None: 실행 결과 문자열, 종료 센티넬, 또는 빈 줄일 경우 None.
    """
    line = line.strip()	# 입력 문자열 앞뒤의 불필요한 공백 제거
    if not line:	# 빈 문자열인 경우
        return None	# None 반환
    try:	# 쉘 토큰화 시도 예외 블록 시작
        tokens = shlex.split(line)	# 따옴표를 고려하여 공백 기준으로 명령어 토큰 분리
    except ValueError:	# 따옴표가 닫히지 않은 비정상 입력인 경우
        return _fmt_err("ERR unbalanced quotes")	# 따옴표 오류 에러 메시지 반환
    if not tokens:	# 토큰 분리 결과가 비어있는 경우
        return None	# None 반환

    cmd = tokens[0].upper()	# 대소문자 구분을 없애기 위해 명령어 식별자를 대문자로 변환

    if cmd == "SET":	# SET 명령어 처리 분기
        if len(tokens) != 3:	# 인자 개수가 정확히 2개(총 토큰 3개)가 아닌 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        try:	# 엔트리 저장 시도 예외 블록 시작
            store.set(tokens[1], tokens[2])	# 키와 값을 저장소에 저장 (LRU 및 OOM 검사 포함)
        except OOMError:	# 단일 엔트리 크기가 maxmemory를 초과한 경우
            return _fmt_err(ERR_OOM)	# OOM 에러 메시지 반환
        return _fmt_ok()	# 성공 시 OK 응답 반환

    if cmd == "GET":	# GET 명령어 처리 분기
        if len(tokens) != 2:	# 인자 개수가 1개가 아닌 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        value = store.get(tokens[1])	# 저장소에서 키의 값 조회 (만료 확인 및 LRU 갱신 포함)
        return _fmt_nil() if value is None else _fmt_bulk(value)	# 미존재 시 (nil), 존재 시 따옴표 감싼 값 반환

    if cmd == "DEL":	# DEL 명령어 처리 분기
        if len(tokens) != 2:	# 인자 개수가 1개가 아닌 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        return _fmt_int(1 if store.delete(tokens[1]) else 0)	# 삭제 성공 시 1, 없었으면 0을 정수 형식으로 반환

    if cmd == "EXISTS":	# EXISTS 명령어 처리 분기
        if len(tokens) != 2:	# 인자 개수가 1개가 아닌 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        return _fmt_int(1 if store.exists(tokens[1]) else 0)	# 존재하면 1, 없으면 0을 정수 형식으로 반환

    if cmd == "DBSIZE":	# DBSIZE 명령어 처리 분기
        if len(tokens) != 1:	# 인자가 추가로 전달된 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        return _fmt_int(store.dbsize())	# 현재 유효한 총 키 개수를 정수 형식으로 반환

    if cmd == "KEYS":	# KEYS 명령어 처리 분기
        if len(tokens) != 1:	# 인자가 추가로 전달된 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        return _fmt_array(store.keys())	# 전체 키 목록을 배열 형식으로 포맷팅하여 반환

    if cmd == "CONFIG":	# CONFIG 명령어 처리 분기
        if len(tokens) != 4 or tokens[1].upper() != "SET" or tokens[2].lower() != "maxmemory":	# CONFIG SET maxmemory 형식 일치 검사
            return _fmt_err(ERR_UNKNOWN.format(cmd))	# 일치하지 않으면 알 수 없는 명령 에러 반환
        bytes_value = _parse_int(tokens[3])	# 설정할 바이트 크기 토큰을 정수로 파싱
        if bytes_value is None or bytes_value < 0:	# 정수가 아니거나 음수인 경우
            return _fmt_err(ERR_NOT_INT)	# 정수 범위 오류 에러 반환
        store.maxmemory = bytes_value	# 저장소의 maxmemory 제한값 설정
        return _fmt_ok()	# 성공 시 OK 응답 반환

    if cmd == "INFO":	# INFO 명령어 처리 분기
        if len(tokens) != 2 or tokens[1].lower() != "memory":	# INFO memory 인자 형식 일치 검사
            return _fmt_err(ERR_UNKNOWN.format(cmd))	# 일치하지 않으면 알 수 없는 명령 에러 반환
        return (	# 3개 메모리 통계 지표를 지정된 형식으로 포맷팅하여 반환
            f"used_memory:{store.used_memory}\n"	# 현재 사용 중인 총 바이트 메모리
            f"maxmemory:{store.maxmemory}\n"	# 설정된 최대 메모리 한도
            f"evicted_keys:{store.evicted_keys}"	# LRU로 축출된 총 키 개수
        )	# 문자열 결합 반환 종료

    if cmd == "EXPIRE":	# EXPIRE 명령어 처리 분기
        if len(tokens) != 3:	# 인자 개수가 2개가 아닌 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        seconds = _parse_int(tokens[2])	# 만료 초 토큰을 정수로 파싱
        if seconds is None:	# 정수가 아닌 경우
            return _fmt_err(ERR_NOT_INT)	# 정수 오류 에러 반환
        return _fmt_int(1 if store.expire(tokens[1], seconds) else 0)	# 만료 설정 성공 시 1, 키 없음 시 0 반환

    if cmd == "TTL":	# TTL 명령어 처리 분기
        if len(tokens) != 2:	# 인자 개수가 1개가 아닌 경우
            return _fmt_err(ERR_ARGS.format(cmd))	# 인자 개수 불일치 에러 반환
        return _fmt_int(store.ttl(tokens[1]))	# 키의 남은 만료 시간(-2, -1, 잔여초)을 정수 형식으로 반환

    if cmd in ("EXIT", "QUIT"):	# 종료 명령어 처리 분기
        return EXIT_SENTINEL	# REPL 루프 종료를 알리는 센티넬 문자열 반환

    return _fmt_err(ERR_UNKNOWN.format(cmd))	# 일치하는 명령어가 없는 경우 unknown command 에러 반환


def run_repl():	# 사용자와의 대화형 REPL 루프를 실행하는 함수 정의
    """Mini Redis 대화형 CLI REPL 세션을 시작합니다.

    'mini-redis> ' 프롬프트를 표시하고 사용자 입력을 받아 명령을 실행한 후
    결과를 출력하는 루프를 exit/quit 또는 Ctrl+D(EOF) 입력 시까지 반복합니다.
    """
    store = MiniRedisStore()	# 새 MiniRedisStore 저장소 인스턴스 생성
    while True:	# 무한 REPL 인터랙티브 루프 시작
        try:	# 사용자 입력 수신 예외 블록 시작
            line = input("mini-redis> ")	# mini-redis> 프롬프트 표시 및 사용자 입력 대기
        except (EOFError, KeyboardInterrupt):	# Ctrl+D 또는 Ctrl+C 신호 수신 시
            print()	# 깔끔한 터미널 줄바꿈 출력
            break	# 루프 탈출
        result = execute_command(store, line)	# 사용자 입력을 파싱하고 명령 실행
        if result == EXIT_SENTINEL:	# 종료 센티넬이 반환된 경우
            break	# REPL 세션 종료
        if result is not None:	# 실행 결과가 존재하는 경우 (빈 줄이 아닌 경우)
            print(result)	# 포맷팅된 결과 출력

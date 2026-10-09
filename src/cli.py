"""REPL CLI. 명령 파싱, 실행, Redis 스타일 출력 포맷을 담당한다."""

import shlex

from .store import MiniRedisStore, OOMError

ERR_UNKNOWN = "ERR unknown command '{0}'"
ERR_ARGS = "ERR wrong number of arguments for '{0}' command"
ERR_NOT_INT = "ERR value is not an integer or out of range"
ERR_OOM = "OOM command not allowed when used_memory > 'maxmemory'"

EXIT_SENTINEL = "__EXIT__"


def _fmt_ok():
    return "OK"


def _fmt_nil():
    return "(nil)"


def _fmt_int(n):
    return f"(integer) {n}"


def _fmt_bulk(s):
    return f'"{s}"'


def _fmt_err(msg):
    return f"(error) {msg}"


def _fmt_array(items):
    if not items:
        return "(empty array)"
    return "\n".join(f'{i}. "{item}"' for i, item in enumerate(items, start=1))


def _parse_int(token):
    try:
        return int(token)
    except ValueError:
        return None


def execute_command(store, line):
    """한 줄 명령을 실행하고 출력 문자열을 반환한다(빈 줄이면 None).

    REPL과 테스트 스크립트 양쪽에서 이 함수를 공용으로 사용한다.
    """
    line = line.strip()
    if not line:
        return None
    try:
        tokens = shlex.split(line)
    except ValueError:
        return _fmt_err("ERR unbalanced quotes")
    if not tokens:
        return None

    cmd = tokens[0].upper()

    if cmd == "SET":
        if len(tokens) != 3:
            return _fmt_err(ERR_ARGS.format(cmd))
        try:
            store.set(tokens[1], tokens[2])
        except OOMError:
            return _fmt_err(ERR_OOM)
        return _fmt_ok()

    if cmd == "GET":
        if len(tokens) != 2:
            return _fmt_err(ERR_ARGS.format(cmd))
        value = store.get(tokens[1])
        return _fmt_nil() if value is None else _fmt_bulk(value)

    if cmd == "DEL":
        if len(tokens) != 2:
            return _fmt_err(ERR_ARGS.format(cmd))
        return _fmt_int(1 if store.delete(tokens[1]) else 0)

    if cmd == "EXISTS":
        if len(tokens) != 2:
            return _fmt_err(ERR_ARGS.format(cmd))
        return _fmt_int(1 if store.exists(tokens[1]) else 0)

    if cmd == "DBSIZE":
        if len(tokens) != 1:
            return _fmt_err(ERR_ARGS.format(cmd))
        return _fmt_int(store.dbsize())

    if cmd == "KEYS":
        if len(tokens) != 1:
            return _fmt_err(ERR_ARGS.format(cmd))
        return _fmt_array(store.keys())

    if cmd == "CONFIG":
        if len(tokens) != 4 or tokens[1].upper() != "SET" or tokens[2].lower() != "maxmemory":
            return _fmt_err(ERR_UNKNOWN.format(cmd))
        bytes_value = _parse_int(tokens[3])
        if bytes_value is None or bytes_value < 0:
            return _fmt_err(ERR_NOT_INT)
        store.maxmemory = bytes_value
        return _fmt_ok()

    if cmd == "INFO":
        if len(tokens) != 2 or tokens[1].lower() != "memory":
            return _fmt_err(ERR_UNKNOWN.format(cmd))
        return (
            f"used_memory:{store.used_memory}\n"
            f"maxmemory:{store.maxmemory}\n"
            f"evicted_keys:{store.evicted_keys}"
        )

    if cmd == "EXPIRE":
        if len(tokens) != 3:
            return _fmt_err(ERR_ARGS.format(cmd))
        seconds = _parse_int(tokens[2])
        if seconds is None:
            return _fmt_err(ERR_NOT_INT)
        return _fmt_int(1 if store.expire(tokens[1], seconds) else 0)

    if cmd == "TTL":
        if len(tokens) != 2:
            return _fmt_err(ERR_ARGS.format(cmd))
        return _fmt_int(store.ttl(tokens[1]))

    if cmd in ("EXIT", "QUIT"):
        return EXIT_SENTINEL

    return _fmt_err(ERR_UNKNOWN.format(cmd))


def run_repl():
    store = MiniRedisStore()
    while True:
        try:
            line = input("mini-redis> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        result = execute_command(store, line)
        if result == EXIT_SENTINEL:
            break
        if result is not None:
            print(result)

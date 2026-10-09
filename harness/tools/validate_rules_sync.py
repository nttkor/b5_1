"""규칙 파일 듀얼 동기화(GEMINI.md <-> AGENTS.md) 자동 검수 및 동기화 도구.

프로젝트 전역 및 각 폴더별 GEMINI.md와 AGENTS.md 파일의 100% 일치 여부를 검증하고,
불일치 시 상세 diff를 출력하거나 자동 동기화(--fix)를 수행합니다.
"""

import sys
import filecmp
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_rule_pairs(root: Path = PROJECT_ROOT):
    """프로젝트 내 모든 디렉터리를 스캔하여 존재하는 GEMINI.md 및 AGENTS.md 쌍을 반환합니다.

    Args:
        root (Path): 스캔할 루트 경로

    Returns:
        list of tuple[Path, Path]: (gemini_path, agents_path) 목록
    """
    pairs = []
    # 루트 및 1단계/2단계 하위 디렉터리 검사
    target_dirs = [root] + [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]

    for d in target_dirs:
        g = d / "GEMINI.md"
        a = d / "AGENTS.md"
        if g.exists() or a.exists():
            pairs.append((g, a))

    return pairs


def validate_sync(auto_fix: bool = False) -> bool:
    """모든 규칙 파일 쌍의 동기화 상태를 검증합니다.

    Args:
        auto_fix (bool): 불일치 시 GEMINI.md 기준으로 AGENTS.md를 자동 덮어쓰기할지 여부

    Returns:
        bool: 모든 파일이 정상 동기화되어 있으면 True, 아니면 False
    """
    pairs = find_rule_pairs()
    all_ok = True

    print(f"[Rules Sync Validator] 총 {len(pairs)}개 규칙 파일 쌍 검사 시작...")

    for g_path, a_path in pairs:
        rel_dir = g_path.parent.relative_to(PROJECT_ROOT)
        dir_name = str(rel_dir) if str(rel_dir) != "." else "(root)"

        if not g_path.exists() and a_path.exists():
            print(f"  ❌ [{dir_name}] GEMINI.md 누락! (AGENTS.md만 존재)")
            all_ok = False
            if auto_fix:
                g_path.write_text(a_path.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"     ➔ [FIX] AGENTS.md 내용으로 GEMINI.md 생성 완료")
            continue

        if g_path.exists() and not a_path.exists():
            print(f"  ❌ [{dir_name}] AGENTS.md 누락! (GEMINI.md만 존재)")
            all_ok = False
            if auto_fix:
                a_path.write_text(g_path.read_text(encoding="utf-8"), encoding="utf-8")
                print(f"     ➔ [FIX] GEMINI.md 내용으로 AGENTS.md 생성 완료")
            continue

        # 둘 다 존재하는 경우 내용 일치 검사
        g_content = g_path.read_text(encoding="utf-8")
        a_content = a_path.read_text(encoding="utf-8")

        if g_content == a_content:
            print(f"  ✅ [{dir_name}] GEMINI.md <--> AGENTS.md 100% 동기화 일치 (Match: OK)")
        else:
            print(f"  ❌ [{dir_name}] 내용 불일치 감지! (Byte/Content Mismatch)")
            all_ok = False
            if auto_fix:
                a_path.write_text(g_content, encoding="utf-8")
                print(f"     ➔ [FIX] GEMINI.md 기준으로 AGENTS.md 동기화 완료")

    if all_ok:
        print("[SUCCESS] 모든 규칙 파일이 100% 완벽하게 상호 동기화되어 있습니다.")
    else:
        print("[FAIL] 일부 규칙 파일이 동기화되지 않았습니다. --fix 옵션을 사용하여 자동 동기화할 수 있습니다.")

    return all_ok


if __name__ == "__main__":
    fix_mode = "--fix" in sys.argv
    success = validate_sync(auto_fix=fix_mode)
    sys.exit(0 if success else 1)

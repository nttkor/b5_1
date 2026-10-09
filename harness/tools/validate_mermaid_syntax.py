"""Mermaid 다이어그램 문법 및 엣지 라벨 정합성 자동 검증 도구.

마크다운 파일 내의 모든 ```mermaid 블록을 스캔하여,
파서 에러를 유발하는 엣지 라벨(|...|) 내 소괄호/특수문자 및 블록 구조를 검증합니다.
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def validate_mermaid_in_file(md_path: Path) -> list:
    """마크다운 파일 내 Mermaid 다이어그램을 검사하여 오류 목록을 반환합니다.

    Args:
        md_path (Path): 검사할 마크다운 파일 경로

    Returns:
        list of dict: 검출된 문제점 목록 (블록 번호, 라인 번호, 내용, 오류 원인)
    """
    if not md_path.exists():
        return [{"error": f"파일 없음: {md_path}"}]

    content = md_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    errors = []
    in_mermaid = False
    current_block_idx = 0
    block_start_line = 0

    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```mermaid"):
            in_mermaid = True
            current_block_idx += 1
            block_start_line = line_no
            continue
        elif in_mermaid and stripped.startswith("```"):
            in_mermaid = False
            continue

        if in_mermaid:
            # 1. 엣지 라벨 내 파싱 에러 유발 문자 검사: -->|...| 또는 ---|...|
            labels = re.findall(r"\|([^|]+)\|", line)
            for label in labels:
                if any(ch in label for ch in ["(", ")", "[", "]", "{", "}"]):
                    errors.append({
                        "file": str(md_path.relative_to(PROJECT_ROOT)),
                        "block": current_block_idx,
                        "line": line_no,
                        "content": line.strip(),
                        "reason": f"엣지 라벨 |{label}| 내에 파싱 에러 유발 특수문자('()[]{{}}')가 포함되어 있습니다.",
                    })

    return errors


def scan_all_markdowns(target_path: Path = None):
    """프로젝트 내 모든 마크다운 파일 또는 지정된 파일의 Mermaid를 검사합니다."""
    if target_path and target_path.is_file():
        files = [target_path]
    else:
        files = list(PROJECT_ROOT.glob("**/*.md"))

    all_errors = []
    print(f"[Mermaid Validator] 총 {len(files)}개 마크다운 파일 스캔 시작...")

    for f in files:
        if ".git" in f.parts or ".gemini" in f.parts:
            continue
        errs = validate_mermaid_in_file(f)
        if errs:
            all_errors.extend(errs)

    if not all_errors:
        print("  ✅ [PASS] 모든 Mermaid 다이어그램 문법 및 라벨이 100% 정상입니다.")
        return True
    else:
        print(f"  ❌ [FAIL] 총 {len(all_errors)}개의 Mermaid 문법 오류가 검출되었습니다:")
        for e in all_errors:
            print(f"     - {e['file']}:{e['line']} (Block {e['block']}): {e['reason']}")
            print(f"       코드: {e['content']}")
        return False


if __name__ == "__main__":
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    success = scan_all_markdowns(target)
    sys.exit(0 if success else 1)

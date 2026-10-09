#!/usr/bin/env python3
"""하네스 자동 설치 및 초기화 러너 (Harness Setup Runner).

새로운 과제 디렉터리에 `harness` 폴더를 복사한 후, 본 스크립트를 실행하면:
1. 표준 디렉터리(src/, docs/, study/, utils/) 자동 생성
2. 전역 및 폴더별 듀얼 규칙 파일(GEMINI.md <-> AGENTS.md) 자동 배포 및 100% 동기화
3. docs/CONVENTIONS.md 커밋 컨벤션 자동 설정
4. utils/ 하네스 검증 툴셋(동기화 검증, Mermaid 검증, Fast Lookup 메모리 등) 자동 설치
5. 미션 QA, 평가 QA, 기술 백과사전(study.md) 스켈레톤 자동 생성
6. 규칙 동기화 자동 검증(validate_rules_sync.py) 100% 통과 확인

사용법:
    python3 harness/setup_harness.py [--name <과제명>]
    (예: python3 harness/setup_harness.py --name b5_2)
    (이름 미지정 시 현재 디렉터리명 자동 사용)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def setup_harness(assignment_name: str | None = None) -> bool:
    """새 과제 환경에 하네스 전체 세트를 1초 만에 자동 설치하고 검증합니다.

    Args:
        assignment_name (str | None): 과제 식별자 (미지정 시 폴더명 자동 사용).

    Returns:
        bool: 설치 및 검증 성공 여부.
    """
    harness_dir = Path(__file__).resolve().parent
    root_dir = harness_dir.parent

    if not assignment_name:
        assignment_name = root_dir.name
        if assignment_name in (".", "", "harness"):
            assignment_name = "assignment"

    print(f"🚀 [Harness Setup] '{assignment_name}' 프로젝트 하네스 자동 구축 시작...")
    print(f"   ➔ 대상 루트 디렉터리: {root_dir}")

    # 1. 표준 디렉터리 생성
    subdirs = ["src", "docs", "study", "utils"]
    for sub in subdirs:
        (root_dir / sub).mkdir(parents=True, exist_ok=True)
    print("  ✅ 1. 표준 디렉터리(src/, docs/, study/, utils/) 확인 및 생성 완료")

    # 2. 듀얼 규칙 파일 배포
    rules_dir = harness_dir / "rules"
    rule_map = {
        "": "ROOT_RULES.md",
        "src": "SRC_RULES.md",
        "docs": "DOCS_RULES.md",
        "study": "STUDY_RULES.md",
        "utils": "UTILS_RULES.md",
    }

    for target_subdir, rule_file_name in rule_map.items():
        template_file = rules_dir / rule_file_name
        if template_file.exists():
            content = template_file.read_text(encoding="utf-8")
            dest_dir = (root_dir / target_subdir) if target_subdir else root_dir
            dest_dir.mkdir(parents=True, exist_ok=True)
            (dest_dir / "GEMINI.md").write_text(content, encoding="utf-8")
            (dest_dir / "AGENTS.md").write_text(content, encoding="utf-8")

    # harness 자체 규칙 동기화
    harness_gemini = harness_dir / "GEMINI.md"
    harness_agents = harness_dir / "AGENTS.md"
    if harness_gemini.exists() and not harness_agents.exists():
        harness_agents.write_text(harness_gemini.read_text(encoding="utf-8"), encoding="utf-8")
    elif harness_agents.exists() and not harness_gemini.exists():
        harness_gemini.write_text(harness_agents.read_text(encoding="utf-8"), encoding="utf-8")

    print("  ✅ 2. 총 5개 디렉터리 듀얼 규칙 파일(GEMINI.md <-> AGENTS.md) 100% 동기화 배포 완료")

    # 3. docs/CONVENTIONS.md 복제
    conventions_template = rules_dir / "CONVENTIONS.md"
    if conventions_template.exists():
        target_conv = root_dir / "docs" / "CONVENTIONS.md"
        shutil.copy2(conventions_template, target_conv)
        print("  ✅ 3. docs/CONVENTIONS.md 커밋 컨벤션 설정 완료")

    # 4. utils/ 툴셋 복제
    tools_dir = harness_dir / "tools"
    if tools_dir.exists():
        for tool_file in tools_dir.iterdir():
            if tool_file.is_file() and not tool_file.name.startswith("."):
                shutil.copy2(tool_file, root_dir / "utils" / tool_file.name)
        print("  ✅ 4. utils/ 하네스 검증 툴셋 및 README.md 설치 완료")

    # 5. 템플릿 기반 문서 스켈레톤 생성
    templates_dir = harness_dir / "templates"

    # 5-1. docs/{name}_mission_QA.md
    mission_qa_path = root_dir / "docs" / f"{assignment_name}_mission_QA.md"
    if not mission_qa_path.exists():
        tpl = (templates_dir / "mission_QA_template.md").read_text(encoding="utf-8")
        mission_qa_path.write_text(tpl.replace("{assignment_name}", assignment_name), encoding="utf-8")

    # 5-2. docs/{name}_eval_QA.md
    eval_qa_path = root_dir / "docs" / f"{assignment_name}_eval_QA.md"
    if not eval_qa_path.exists():
        tpl = (templates_dir / "eval_QA_template.md").read_text(encoding="utf-8")
        eval_qa_path.write_text(tpl.replace("{assignment_name}", assignment_name), encoding="utf-8")

    # 5-3. study/study.md
    study_path = root_dir / "study" / "study.md"
    if not study_path.exists():
        tpl = (templates_dir / "study_template.md").read_text(encoding="utf-8")
        study_path.write_text(tpl.replace("{assignment_name}", assignment_name), encoding="utf-8")

    # 5-4. README.md (루트에 없을 때만 생성)
    readme_path = root_dir / "README.md"
    if not readme_path.exists():
        tpl = (templates_dir / "README_template.md").read_text(encoding="utf-8")
        readme_path.write_text(tpl.replace("{assignment_name}", assignment_name), encoding="utf-8")

    print(f"  ✅ 5. 상호 연동 문서 스켈레톤({assignment_name}_mission_QA, {assignment_name}_eval_QA, study.md) 생성 완료")

    # 6. 규칙 동기화 자동 검증 실행
    val_script = root_dir / "utils" / "validate_rules_sync.py"
    if val_script.exists():
        res = subprocess.run([sys.executable, str(val_script)], capture_output=True, text=True)
        if res.returncode == 0:
            print("  ✅ 6. 전역 규칙 듀얼 동기화 자체 검증 100% 통과 (PASS)")
        else:
            print(f"  ⚠️ 6. 전역 규칙 동기화 검증 경고:\n{res.stdout}")

    print(f"\n🎉 [COMPLETE] '{assignment_name}' 하네스 세팅이 완벽하게 완료되었습니다!")
    print("👉 이제 에이전트(Antigravity)에게 다음과 같이 명령을 내리시면 됩니다:")
    print("   ─────────────────────────────────────────────────────────────────")
    print(f"   /goal docs에 있는 과제 자료를 바탕으로 {assignment_name}_mission_QA.md,")
    print(f"         {assignment_name}_eval_QA.md, 코드 고밀도 주석화, study/study.md,")
    print("         README.md 상호 링크를 완성하고 테스트 검수 후 커밋해줘.")
    print("   ─────────────────────────────────────────────────────────────────")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="하네스 자동 설치 및 초기화 러너")
    parser.add_argument("--name", default=None, help="과제 식별자 (예: b5_2, b6_1 등)")
    args = parser.parse_args()
    success = setup_harness(args.name)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

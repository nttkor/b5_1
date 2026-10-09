"""과제 자동화 및 하네스 엔지니어링 스캐폴더 (Assignment Harness Scaffolder).

본 도구는 새로운 과제나 프로젝트 시작 시, 본 프로젝트에서 완성한
'7대 핵심 운영 규칙', '듀얼 규칙 동기화(GEMINI.md <-> AGENTS.md)',
'하네스 검증 툴셋(동기화 검증, Mermaid 검증, Fast Lookup 메모리)',
'표준 폴더 구조(src, docs, study, utils)' 및 '상호 연동 QA/학습 문서 템플릿'을
단 한 번의 명령으로 대상 디렉터리에 자동 생성(Scaffolding)하는 범용 자동화 도구입니다.

사용법:
    python3 utils/scaffold_assignment_harness.py --target-dir <경로> --name <과제식별자>
    (예: python3 utils/scaffold_assignment_harness.py --target-dir ../b5_2 --name b5_2)
"""

import argparse
import shutil
import sys
from pathlib import Path


def scaffold_project(target_dir: Path, assignment_name: str) -> None:
    """새로운 과제 디렉터리에 표준 하네스 엔지니어링 환경을 자동 구축합니다.

    Args:
        target_dir (Path): 하네스를 구축할 대상 프로젝트 루트 디렉터리.
        assignment_name (str): 과제 식별자 (예: b5_2, b6_1 등).
    """
    source_root = Path(__file__).resolve().parent.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 [Harness Scaffolder] '{assignment_name}' 프로젝트 하네스 구축 시작: {target_dir}")

    # 1. 표준 디렉터리 생성
    subdirs = ["src", "docs", "study", "utils"]
    for sub in subdirs:
        (target_dir / sub).mkdir(parents=True, exist_ok=True)
    print("  ✅ 1. 표준 디렉터리(src/, docs/, study/, utils/) 생성 완료")

    # 2. 듀얼 규칙 파일 복제 및 맞춤 생성 (root, src, docs, study, utils)
    rule_dirs = ["", "src", "docs", "study", "utils"]
    for rdir in rule_dirs:
        src_rule = source_root / rdir / "AGENTS.md" if rdir else source_root / "AGENTS.md"
        if src_rule.exists():
            content = src_rule.read_text(encoding="utf-8")
            # 대상 디렉터리에 GEMINI.md와 AGENTS.md 동일하게 작성
            target_agents = (target_dir / rdir / "AGENTS.md") if rdir else (target_dir / "AGENTS.md")
            target_gemini = (target_dir / rdir / "GEMINI.md") if rdir else (target_dir / "GEMINI.md")
            target_agents.write_text(content, encoding="utf-8")
            target_gemini.write_text(content, encoding="utf-8")
    print("  ✅ 2. 총 5개 디렉터리 듀얼 규칙 파일(GEMINI.md <-> AGENTS.md) 100% 동기화 생성 완료")

    # 3. docs/CONVENTIONS.md 복제
    conventions_src = source_root / "docs" / "CONVENTIONS.md"
    if conventions_src.exists():
        shutil.copy2(conventions_src, target_dir / "docs" / "CONVENTIONS.md")
    print("  ✅ 3. docs/CONVENTIONS.md 커밋 및 코드 컨벤션 생성 완료")

    # 4. utils/ 하네스 도구 복제 (validate_rules_sync, validate_mermaid_syntax, time_utils, inspect_codebase_memory)
    utils_files = [
        "__init__.py",
        "validate_rules_sync.py",
        "validate_mermaid_syntax.py",
        "time_utils.py",
        "inspect_codebase_memory.py",
        "README.md",
    ]
    for uf in utils_files:
        src_uf = source_root / "utils" / uf
        if src_uf.exists():
            shutil.copy2(src_uf, target_dir / "utils" / uf)
    print("  ✅ 4. utils/ 하네스 검증 툴셋 및 README.md 자산화 복제 완료")

    # 5. 상호 연동 문서 스켈레톤 생성
    # 5-1. docs/{assignment_name}_mission_QA.md
    mission_qa_file = target_dir / "docs" / f"{assignment_name}_mission_QA.md"
    if not mission_qa_file.exists():
        mission_qa_content = f"""# {assignment_name} 미션 구현 및 기술 분석 Q&A ({assignment_name}_mission_QA)

본 문서는 `{assignment_name}` 미션 요구사항, 과제 목표, 기능 명세에 대한 심층 기술 답변서입니다.

> 💡 **연관 핵심 문서 상호 링크**:
> - 📚 **핵심 개념 및 기술 용어 백과사전**: [`study/study.md`](../study/study.md)
> - 🎯 **종합 평가문항 답변서**: [`docs/{assignment_name}_eval_QA.md`]({assignment_name}_eval_QA.md)
> - 📖 **프로젝트 메인 안내서**: [`README.md`](../README.md)
> - 🏗️ **아키텍처 및 상세 실행도**: [`study/README.md`](../study/README.md)

---

## 1. 미션 목적 및 개요
- **미션 목적**: (과제 목적 서술)
- **핵심 기술적 원칙**: (제약조건 및 핵심 알고리즘 서술)

---

## 2. 구현 실현 항목
(구현 기능 및 소스코드 상대 링크 매핑 서술)
"""
        mission_qa_file.write_text(mission_qa_content, encoding="utf-8")

    # 5-2. docs/{assignment_name}_eval_QA.md
    eval_qa_file = target_dir / "docs" / f"{assignment_name}_eval_QA.md"
    if not eval_qa_file.exists():
        eval_qa_content = f"""# {assignment_name} 종합 평가문항 답변서 ({assignment_name}_eval_QA)

본 문서는 `{assignment_name}` 평가 기준 및 5대 평가문항에 대한 심층 기술 답변서입니다.

> 💡 **연관 핵심 문서 상호 링크**:
> - 📚 **핵심 개념 및 기술 용어 백과사전**: [`study/study.md`](../study/study.md)
> - 📝 **미션 수행 및 요구사항 심층 Q&A**: [`docs/{assignment_name}_mission_QA.md`]({assignment_name}_mission_QA.md)
> - 📖 **프로젝트 메인 안내서**: [`README.md`](../README.md)
> - 🏗️ **아키텍처 및 상세 실행도**: [`study/README.md`](../study/README.md)

---

## 1. 과제 목표 및 구현 개요
(과제 목표 및 모듈별 소스코드 매핑)

---

## 2. 5대 평가문항 심층 답변
(항목 1~5 정답 및 소스코드 상대 링크 매핑)
"""
        eval_qa_file.write_text(eval_qa_content, encoding="utf-8")

    # 5-3. study/study.md
    study_file = target_dir / "study" / "study.md"
    if not study_file.exists():
        study_content = f"""# {assignment_name} 핵심 개념 및 기술 용어 백과사전 (`study/study.md`)

본 문서는 `{assignment_name}` 과제 수행 중 도출된 모든 컴퓨터 공학 원리, 자료구조, 알고리즘, 시스템 설계 최적화 지식을 집대성한 기술 백과사전입니다.

> 💡 **연관 핵심 문서 상호 링크**:
> - 📖 **프로젝트 메인 안내서**: [`README.md`](../README.md)
> - 🏗️ **아키텍처 및 상세 실행도**: [`study/README.md`](README.md)
> - 📝 **미션 심층 Q&A**: [`docs/{assignment_name}_mission_QA.md`](../docs/{assignment_name}_mission_QA.md)
> - 🎯 **종합 평가문항 답변서**: [`docs/{assignment_name}_eval_QA.md`](../docs/{assignment_name}_eval_QA.md)

---

## 1. 핵심 아키텍처 및 시스템 개요
(아키텍처 및 핵심 원리)

---

## 2. 핵심 개념 및 기술 용어 색인
(알파벳/가나다 순 용어 정리)
"""
        study_file.write_text(study_content, encoding="utf-8")

    print(f"  ✅ 5. 상호 연동 문서 스켈레톤(mission_QA.md, eval_QA.md, study.md) 생성 완료")

    print(f"\n🎉 [COMPLETE] '{assignment_name}' 프로젝트 하네스 엔지니어링 구축이 성공적으로 완료되었습니다!")
    print(f"👉 이동 후 작업 시작: cd {target_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="새로운 과제 디렉터리에 표준 하네스 엔지니어링 환경을 자동 구축합니다.")
    parser.add_argument("--target-dir", required=True, help="하네스를 구축할 대상 디렉터리 경로")
    parser.add_argument("--name", default="assignment", help="과제 식별자 (예: b5_2, b6_1 등)")
    args = parser.parse_args()

    target_path = Path(args.target_dir).resolve()
    scaffold_project(target_path, args.name)


if __name__ == "__main__":
    main()

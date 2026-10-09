"""하네스 엔지니어링 전용 코드베이스 색인 및 작업 메모리 생성기.

프로젝트 전역을 고속 스캔하여 Fast Lookup Map(빠른 조회 색인표)을 생성합니다.
매 프롬프트마다 전체 디렉터리를 반복 스캔(Full Scan)하는 비효율을 방지하고,
목적 파일로 0초 만에 직행할 수 있도록 구조화된 색인 데이터를 제공합니다.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 주요 파일별 설명 및 역할 메타데이터
FILE_METADATA = {
    "main.py": ("CLI 진입점", "run_repl() 실행 및 Mini Redis REPL 구동"),
    "test_mini_redis.py": ("전체 자체 검증 테스트", "8개 단위/통합 테스트 (자료구조, LRU, TTL, OOM, CLI 에러)"),
    "src/doubly_linked_list.py": ("이중 연결 리스트", "DoublyLinkedList, Node (Sentinel 기반 O(1) 삽입/삭제/이동)"),
    "src/hashmap.py": ("체이닝 해시맵", "HashMap, _Pair (djb2 해시, 로드팩터 0.75 리사이즈)"),
    "src/heap.py": ("최소 힙", "MinHeap (_heapify_up, _heapify_down, TTL 만료 관리용)"),
    "src/store.py": ("핵심 스토리지 엔진", "MiniRedisStore (LRU 제거, Lazy deletion TTL, used_memory 계산)"),
    "src/cli.py": ("CLI 인터페이스", "MiniRedisCLI, execute_command (shlex 파싱, Redis 스타일 포맷 출력)"),
    "docs/b5_1_mission.md": ("미션 명세서 (MD 변환본)", "기본 명령어, LRU, TTL, 제약사항 요구사항 정의"),
    "docs/b5_1_mission_QA.md": ("미션 심층 질의응답서", "미션 목적, 구현항목, 기능요구사항 Q&A 및 상대 링크"),
    "docs/b5_1_mission.pdf": ("미션 명세서 (원본 PDF)", "원본 보존 (절대 삭제 금지)"),
    "docs/b5_1_eval.md": ("구술/실기 평가표 (MD 변환본)", "5대 평가 항목, 채점 기준표"),
    "docs/b5_1_eval_QA.md": ("종합 평가문항 답변서", "과제목표, 요구사항, 5대 평가문항 심층답변 및 상대 링크"),
    "docs/b5_1_eval.pdf": ("구술/실기 평가표 (원본 PDF)", "원본 보존 (절대 삭제 금지)"),
    "docs/CONVENTIONS.md": ("커밋 및 코드 컨벤션", "Conventional Commits 규칙, 코드 스타일 정의"),
    "README.md": ("프로젝트 메인 안내서", "프로젝트 아키텍처, 실행 방법, 자료구조 설계 요약"),
    "READYOU.md": ("구술 평가 대비 상세 문서", "해시맵/LRU/힙/Eviction 핵심 원리 심층 설명"),
    "study/README.md": ("프로젝트 종합 가이드", "프로젝트 개요, 상세, 구현 기능 목록, 폴더 트리, 단독 분리형 머메이드 실행도"),
    "study/study.md": ("핵심 개념 백과사전", "자료구조, djb2 해시, 체이닝, 힙, LRU/LFU, TTL 기술 용어 총정리"),
    "GEMINI.md": ("프로젝트 전역 규칙 파일", "7대 핵심 운영 규칙 (AGENTS.md와 100% 동기화)"),
    "AGENTS.md": ("프로젝트 전역 규칙 파일", "7대 핵심 운영 규칙 (GEMINI.md와 100% 동기화)"),
    "src/GEMINI.md": ("src 모듈 전용 규칙", "자료구조 제약, 시간 복잡도, 주석 보존 (AGENTS.md와 동기화)"),
    "src/AGENTS.md": ("src 모듈 전용 규칙", "자료구조 제약, 시간 복잡도, 주석 보존 (GEMINI.md와 동기화)"),
    "docs/GEMINI.md": ("docs 전용 규칙", "PDF 불변, 정합성, 컨벤션 준수 (AGENTS.md와 동기화)"),
    "docs/AGENTS.md": ("docs 전용 규칙", "PDF 불변, 정합성, 컨벤션 준수 (GEMINI.md와 동기화)"),
    "study/GEMINI.md": ("study 전용 규칙", "실구현 일치, 마크다운 표준, 상호 동기화 (AGENTS.md와 동기화)"),
    "study/AGENTS.md": ("study 전용 규칙", "실구현 일치, 마크다운 표준, 상호 동기화 (GEMINI.md와 동기화)"),
    "utils/validate_rules_sync.py": ("규칙 동기화 검증기", "GEMINI.md와 AGENTS.md 100% 일치 자동 검수/동기화"),
    "utils/validate_mermaid_syntax.py": ("Mermaid 문법 검증기", "엣지 라벨 괄호 등 파싱 에러 방지 자동 검사"),
    "utils/inspect_codebase_memory.py": ("하네스 색인 생성기", "Fast Lookup Map 생성 및 파일 트리 색인 자동화"),
    "utils/time_utils.py": ("시간 유틸리티", "KST 타임스탬프 생성 및 ISO 포맷 변환"),
    "utils/README.md": ("유틸리티 패키지 안내서", "재사용 툴 및 하네스 엔지니어링 스크립트 가이드"),
    "utils/scaffold_assignment_harness.py": ("하네스 스캐폴더", "새 과제 디렉터리에 듀얼 규칙, 하네스 도구, 표준 폴더, QA/학습 문서 일괄 구축"),
    "utils/GEMINI.md": ("utils 전용 규칙", "공통 툴 관리 및 듀얼 동기화 규칙 (AGENTS.md와 동기화)"),
    "utils/AGENTS.md": ("utils 전용 규칙", "공통 툴 관리 및 듀얼 동기화 규칙 (GEMINI.md와 동기화)"),
}


def generate_fast_lookup_table() -> str:
    """Fast Lookup Map 마크다운 테이블 문자열을 생성합니다."""
    lines = [
        "| 파일 경로 | 설명 | 주요 심볼 / 책임 |",
        "| :--- | :--- | :--- |",
    ]

    for rel_path, (desc, symbols) in sorted(FILE_METADATA.items()):
        full_path = PROJECT_ROOT / rel_path
        status = "✅" if full_path.exists() else "⚠️(미생성)"
        lines.append(f"| `{rel_path}` | {desc} {status} | {symbols} |")

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== [Harness Engineering] Fast Lookup Map ===")
    print(generate_fast_lookup_table())

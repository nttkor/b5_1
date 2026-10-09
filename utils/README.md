# 재사용 공통 유틸리티 모음 (Utils & Harness Tools)

본 디렉터리는 프롬프트 수행 과정에서 작성된 검증 스크립트, 하네스 엔지니어링 도구, 공통 유틸리티를 한곳에 모아 체계적으로 관리하고 재사용하기 위한 전용 패키지입니다.

---

## 🚀 1. 하네스 엔지니어링 (Harness Engineering) 개요

- **도입 목적**: 프롬프트 실행 시마다 리포지토리 전체 디렉터리를 `find`, `grep` 등으로 전수 스캔(Full Scan)하는 비효율과 토큰 낭비를 원천 차단합니다.
- **핵심 메커니즘**:
  - `inspect_codebase_memory.py`가 관리하는 **Fast Lookup Map(색인 맵)**을 에이전트 작업 메모리(`activity_log.md`)와 연동하여 목적 파일로 즉각(0초) 직행합니다.
  - 일회성 검증 스크립트를 즉석 작성 후 버리지 않고, 본 패키지에 모듈화하여 지속 가능한 자동화 자산으로 재활용합니다.

---

## 🛠️ 2. 제공 유틸리티 도구 목록

| 도구 파일명 | 역할 및 기능 | 실행 명령어 |
| :--- | :--- | :--- |
| [`validate_rules_sync.py`](file:///Users/mpeg46551/b5_1/utils/validate_rules_sync.py) | `GEMINI.md`와 `AGENTS.md` 파일 쌍(총 5개 디렉터리)의 100% 동일 동기화 여부를 자동 검수하고 필요 시 자동 복구(`--fix`) | `python3 utils/validate_rules_sync.py [--fix]` |
| [`validate_mermaid_syntax.py`](file:///Users/mpeg46551/b5_1/utils/validate_mermaid_syntax.py) | 마크다운 내 Mermaid 다이어그램에서 엣지 라벨(`\|...\|`) 괄호 등 파서 오류 유발 문법을 전수 자동 검사 | `python3 utils/validate_mermaid_syntax.py [path]` |
| [`inspect_codebase_memory.py`](file:///Users/mpeg46551/b5_1/utils/inspect_codebase_memory.py) | 전체 코드베이스의 구조와 책임 심볼을 색인화하여 Fast Lookup Map 마크다운 테이블 자동 생성 | `python3 utils/inspect_codebase_memory.py` |
| [`time_utils.py`](file:///Users/mpeg46551/b5_1/utils/time_utils.py) | KST(한국 표준시) 포맷팅 문자열 생성 (`YYYY-MM-DD HH:MM:SS KST`) | `python3 utils/time_utils.py` |

---

## 📖 3. 상세 사용 가이드

### ① 규칙 파일 상호 동기화 검수 (`validate_rules_sync.py`)
전체 디렉터리(`root`, `src/`, `docs/`, `study/`, `utils/`)의 `GEMINI.md`와 `AGENTS.md` 일치 여부를 검사합니다:
```bash
# 동기화 상태 검사만 수행
python3 utils/validate_rules_sync.py

# 불일치 발견 시 GEMINI.md 기준으로 AGENTS.md 자동 동기화 적용
python3 utils/validate_rules_sync.py --fix
```

### ② Mermaid 다이어그램 문법 검사 (`validate_mermaid_syntax.py`)
마크다운 문서 내의 Mermaid 다이어그램 렌더링 에러를 사전에 방지합니다:
```bash
# 전체 마크다운 파일 일괄 검사
python3 utils/validate_mermaid_syntax.py

# 특정 문서 단독 검사 (예: study/README.md)
python3 utils/validate_mermaid_syntax.py study/README.md
```

### ③ 하네스 색인 맵 생성 (`inspect_codebase_memory.py`)
작업 메모리(`activity_log.md`) 갱신 시 최신 코드베이스 색인 표를 출력합니다:
```bash
python3 utils/inspect_codebase_memory.py
```

### ④ 현재 로컬 시각(KST) 확인 (`time_utils.py`)
보고 표준에 필요한 KST 타임스탬프를 출력합니다:
```bash
python3 utils/time_utils.py
```

---

## 📌 4. 유틸리티 개발 및 등록 규칙

1. **단일 진실 공급원(Single Source of Truth)**: 프롬프트 수행 중 반복 사용되는 검증/변환 코드는 인라인으로 남겨두지 않고 반드시 `utils/`에 모듈화합니다.
2. **독립 실행 가능(CLI Runnable)**: 모든 스크립트는 `if __name__ == "__main__":` 블록을 포함하여 터미널에서 즉시 실행 및 테스트가 가능하도록 작성합니다.
3. **상세 Docstring**: 각 함수 및 클래스에 `Args`, `Returns`를 포함한 상세 설명을 유지합니다.

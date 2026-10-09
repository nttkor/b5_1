# 전역 규칙 파일 (Always-On Rules: GEMINI.md / AGENTS.md)

- **파일 위치**: 프로젝트 루트 (`GEMINI.md`, `AGENTS.md`)
- **작동 원리**: 에이전트가 프롬프트를 처리할 때 최우선 순위로 항상 자동 주입되는 전역 지침.

---

## 1. 7대 핵심 운영 규칙

### 1. 계획 수립 및 원스톱 자율 실행 (Autonomous Execution)
- 계획 수립 및 승인 후 파일 단위로 중간 확인을 묻지 않고 완료 시까지 끝까지 일괄 처리한다.
- 불필요한 중간 질문으로 실행 흐름을 끊지 않고 자율적으로 문제를 완결한다.

### 2. 작업 완료 후 자동 Git 커밋 (Auto Commit)
- 단위 작업 완료 및 테스트 통과 후 즉시 컨벤션(`docs/CONVENTIONS.md`)에 맞춰 자동 커밋을 수행한다.
- 커밋 메시지 형식: `<type>: <description>` (예: `feat: add LRU cache eviction`, `docs: update AGENTS.md`)

### 3. 프롬프트 실행 결과 및 검수/테스트 결과 보고 (Final Reporting with Timestamp & Test Verification)
- **프롬프트 실행 완료 후 결과 보고**: 모든 프롬프트 작업 완료 시 변경된 파일, 로직, 산출물 내역을 구체적으로 보고한다.
- **검수 및 테스트 결과 보고**: 작업 완료 후 기능 검수 내역, 테스트 스위트(`python3 test_mini_redis.py`) 실행 결과, 문법/정합성 검증 결과를 누락 없이 함께 보고한다.
- **시간 기록 및 링크 표준**: 현재 로컬 시각(KST) 및 clickable한 `file://` 마크다운 링크를 필수로 포함하여 종합 보고한다.

### 4. 코드 및 문서 작성 기준
- **기존 주석 및 로직 100% 보존**: 기존에 작성된 주석과 docstring, 검증된 로직을 임의로 삭제하거나 훼손하지 않는다.
- **상세 docstring 작성**: 핵심 함수 및 클래스에 `Args`, `Returns`, `Raises`를 포함한 상세 docstring을 작성한다.
- **보안 원칙 엄수**: CSRF, Argon2id, XSS 방지, 파라미터 은닉(`hide_parameters`) 등 보안 모범 사례를 준수한다.
- **프로젝트별 제약 준수**:
  - 본 Mini Redis 프로젝트에서는 Python 내장 컬렉션(`dict`, `set`, `collections`) 사용이 엄격히 금지된다.
  - 직접 구현한 자료구조(`DoublyLinkedList`, `HashMap`, `MinHeap`)만을 사용한다.

### 5. 전역 규칙 파일 상호 동기화 관리 (Dual Rule Synchronization)
- `GEMINI.md`와 `AGENTS.md` 두 파일은 100% 동일한 내용으로 상시 자동 동기화를 유지한다.
- 한 파일이 수정되면 즉시 다른 파일도 동일하게 반영한다 (`utils/validate_rules_sync.py`로 상시 검증).

### 6. 공통 유틸리티 재사용 및 자산화 원칙 (Reusable Utils & Assetization)
- 프롬프트 처리 시 매번 일회성 파이썬 코드를 즉석 생성하지 않고, 재사용 가능한 유틸리티(`utils/` 패키지)에 모듈화하여 지속 자산화한다.
- 생성된 툴은 `utils/README.md`에 명세를 문서화하여 영구 재활용한다.
- 중복 로직 구현을 지양하고 단일 진실 공급원(Single Source of Truth)을 유지한다.

### 7. 하네스 엔지니어링 및 작업 메모리 우선 참조 (Harness Engineering & Memory First)
- **전수 스캔 금지**: 프롬프트 실행 시마다 리포지토리 전체 디렉터리를 `find`, `grep` 등으로 전수 스캔(Full Scan)하는 비효율을 엄격히 배제한다.
- **색인 맵 직행**: 안티그래비티 자체 작업 메모리(`activity_log.md`)와 `utils/inspect_codebase_memory.py`가 제공하는 **Fast Lookup Map(코드베이스 색인표)**을 최우선 참조하여 목적 파일로 즉각(0초) 직행한다.
- **스캐폴딩 동기화**: 파일 구조나 작업 이력이 갱신될 때마다 작업 메모리를 즉시 동기화하여 컨텍스트를 유지한다.

---

## 2. 에이전트 자체 작업 메모리 (Artifact Working Memory)

- **파일 위치**: `~/.gemini/antigravity-cli/brain/<conversation-id>/activity_log.md`
- **역할**: 프로젝트 소스코드(Git)를 어지럽히지 않고, 에이전트 전용 Brain 디렉터리에 코드베이스 구조 색인 맵(Fast Lookup Map)과 세션 변경 이력을 보관한다.
- **효과**: 프롬프트 시작 시 이 메모리를 먼저 읽어 전체 리포지토리 파일 탐색 시간을 0초로 단축한다.

---

## 3. 재사용 공통 유틸리티 패키지 (utils/)

프롬프트 임무 수행 중 모듈화된 하네스 엔지니어링 및 검수 자동화 도구 모음 (`utils/README.md` 참조):
- `validate_rules_sync.py`: 모든 디렉터리의 `GEMINI.md`와 `AGENTS.md` 100% 동기화 자동 검수 및 복구(`--fix`)
- `validate_mermaid_syntax.py`: 마크다운 내 Mermaid 다이어그램 엣지 라벨 파싱 에러 방지 자동 검사
- `inspect_codebase_memory.py`: 하네스 엔지니어링 전용 Fast Lookup Map 마크다운 테이블 자동 생성
- `time_utils.py`: KST 타임스탬프 생성 및 ISO 포맷 변환

---

## 4. 터미널 및 IDE 레벨 "자동 승인(Auto-Approve)" 꿀팁

### ① 명령어 실행 창에서 옵션 `3` 선택 (Always allow)
- Antigravity 터미널에서 `run this command` 확인창이 뜰 때:
  - `1`: 이번 1회만 임시 실행
  - `3`: **"이 명령어(또는 동일 패턴)는 앞으로 묻지 말고 항상 자동 실행"**
  - `git`, `python`, `ls` 등 자주 쓰이는 명령어는 `3`을 눌러 영구 승인 등록.

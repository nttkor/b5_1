# utils 디렉터리 전용 규칙 (Always-On Rules: GEMINI.md / AGENTS.md)

- **파일 위치**: `utils/` 디렉터리 (`GEMINI.md`, `AGENTS.md`)
- **역할**: 하네스 엔지니어링 도구, 재사용 유틸리티 및 자동화 검증 스크립트 관리 지침.

---

## 1. 유틸리티 개발 및 관리 원칙

### ① 하네스 엔지니어링 원칙 (Harness Engineering)
- 프롬프트 수행 시 전체 폴더를 매번 뒤지는 비효율(Full Scan)을 배제하고, `utils/inspect_codebase_memory.py` 및 Fast Lookup Map을 최우선 활용합니다.
- 새로운 반복 검증 로직이 발생할 경우 일회성 코드로 남기지 않고 본 패키지에 모듈화하여 `utils/README.md`에 등재합니다.

### ② 독립 실행성 (CLI Usability)
- 모든 유틸리티 파일은 CLI에서 단독 실행이 가능해야 하며, 적절한 exit code(성공 시 0, 실패 시 1)를 반환해야 합니다.

### ③ 프롬프트 실행 완료 후 결과 및 검수 보고 (Mandatory)
- 유틸리티 코드 추가 및 수정 시 실행 결과와 단위 테스트/검증 결과를 보고합니다.
- 보고 시 KST 로컬 시각 및 수정된 파일의 `file://` 마크다운 링크를 포함합니다.

### ④ 상호 동기화 관리
- `utils/GEMINI.md`와 `utils/AGENTS.md` 두 파일은 100% 동일한 내용으로 상시 자동 동기화합니다.

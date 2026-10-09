# harness 디렉터리 전용 규칙 (Always-On Rules: GEMINI.md / AGENTS.md)

- **파일 위치**: `harness/` 디렉터리 (`GEMINI.md`, `AGENTS.md`)
- **역할**: 과제 이식용 하네스 엔지니어링 패키지, 템플릿, 자동화 도구 및 셋업 스크립트 관리 지침.

---

## 1. 하네스 패키지 관리 원칙

### ① 독립 배포성 (Self-Contained Portability)
- `harness/` 폴더는 다른 과제 리포지토리로 단독 복사되어도 `python3 harness/setup_harness.py` 실행 한 번으로 모든 규칙, 검증 도구, 폴더 구조, 템플릿을 온전히 구축할 수 있어야 합니다.

### ② 단일 진실 공급원 (Single Source of Truth)
- 규칙 템플릿(`harness/rules/`) 및 도구(`harness/tools/`)는 프로젝트 루트의 규칙 및 `utils/` 도구와 동일한 기능 정합성을 유지합니다.

### ③ 프롬프트 실행 완료 후 결과 및 검수 보고 (Mandatory)
- 하네스 구성 변경 시 도구 동작 검증 및 규칙 동기화 여부를 보고합니다.
- 보고 시 KST 로컬 시각 및 수정된 파일의 `file://` 마크다운 링크를 포함합니다.

### ④ 상호 동기화 관리
- `harness/GEMINI.md`와 `harness/AGENTS.md` 두 파일은 100% 동일한 내용으로 상시 자동 동기화합니다.

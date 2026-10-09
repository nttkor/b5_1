# docs 디렉터리 전용 규칙 (Always-On Rules: GEMINI.md / AGENTS.md)

- **파일 위치**: `docs/` 디렉터리 (`GEMINI.md`, `AGENTS.md`)
- **역할**: 미션 문서, 평가 기준서, 컨벤션 문서 관리 및 서식 표준 지침.

---

## 1. 문서 작성 및 관리 원칙

### ① 원본 PDF 불변 원칙
- `b5_1_mission.pdf`, `b5_2_Redis_eval.pdf` 등 원본 평가 및 미션 PDF 파일은 절대 삭제하거나 덮어쓰지 않습니다.

### ② 마크다운 정합성
- PDF 기반 변환 문서(`b5_1_mission.md`, `b5_2_Redis_eval.md`)는 원본 문서의 항목, 표, 서식 구조를 온전하게 보존합니다.
- 평가 항목(항목 1~5, 체크박스) 및 배점/평가 기준과의 1:1 정합성을 유지합니다.

### ③ 컨벤션 준수
- 프로젝트 변경 사항은 `docs/CONVENTIONS.md`에 명시된 커밋 메시지 및 코드 작성 규칙을 따릅니다.

### ④ 상호 동기화 관리
- `docs/GEMINI.md`와 `docs/AGENTS.md` 두 파일은 100% 동일한 내용으로 상시 동기화합니다.

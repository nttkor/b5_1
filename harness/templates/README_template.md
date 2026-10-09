# {assignment_name} 프로젝트 대시보드

본 리포지토리는 `{assignment_name}` 과제 구현 및 하네스 엔지니어링, 상호 연동 기술 문서, 검증 테스트 스위트를 포함하는 통합 프로젝트입니다.

---

## 🧭 빠른 문서 탐색기 (Quick Navigation)

| 범주 | 문서명 | 경로 | 설명 |
| :--- | :--- | :--- | :--- |
| **미션 분석** | `{assignment_name}_mission_QA.md` | [`docs/{assignment_name}_mission_QA.md`](docs/{assignment_name}_mission_QA.md) | 미션 목표, 기능 명세 및 코드 매핑 심층 Q&A |
| **평가 분석** | `{assignment_name}_eval_QA.md` | [`docs/{assignment_name}_eval_QA.md`](docs/{assignment_name}_eval_QA.md) | 평가 기준표 및 5대 평가문항 정답 해설 |
| **기술 백과** | `study.md` | [`study/study.md`](study/study.md) | 핵심 CS 개념, 자료구조/알고리즘 기술 백과사전 |
| **실행도/구조**| `study/README.md` | [`study/README.md`](study/README.md) | 모듈별 분리 Mermaid 실행도 및 폴더 구조 가이드 |
| **규칙/컨벤션**| `CONVENTIONS.md` | [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) | 커밋 컨벤션 및 클린 코드 표준 |
| **유틸리티** | `utils/README.md` | [`utils/README.md`](utils/README.md) | 하네스 검증 도구 및 재사용 스크립트 명세 |

---

## 🚀 빠른 시작 (Quick Start)

### 테스트 실행
```bash
python3 test_{assignment_name}.py
```

### 하네스 정합성 검증
```bash
# 듀얼 규칙 동기화 검사
python3 utils/validate_rules_sync.py

# Mermaid 다이어그램 린트 검사
python3 utils/validate_mermaid_syntax.py
```

# 📋 다음 과제 원클릭 프롬프트 템플릿 모음 (`harness/PROMPT_TEMPLATE.md`)

새로운 과제를 시작할 때, `harness` 폴더를 복사해 두고 Antigravity에게 아래 프롬프트 중 하나를 복사하여 전송하시면 됩니다.

---

## ⚡ 1. 원클릭 풀코스 완결 프롬프트 (가장 추천: `/goal` 모드)

> **사용 방법**: 새 프로젝트 디렉터리(`docs/`에 과제 PDF나 명세서 배치 후)에서 아래 내용을 그대로 전송합니다.

```markdown
/goal harness 세팅 및 과제 종합 완성 파이프라인을 원스톱으로 완결해줘:

1. 하네스 자동 세팅:
   - python3 harness/setup_harness.py 실행하여 표준 디렉터리, 5쌍 듀얼 규칙, 하네스 검증 도구, 컨벤션을 세팅해.

2. 문서 분석 및 심층 QA 작성:
   - docs/ 디렉터리에 있는 과제 미션 및 평가 자료(PDF/md)를 정독해.
   - docs/<과제명>_mission_QA.md: 미션 목적, 구현 항목, 기능 요구사항, 아키텍처를 소스코드 상대경로 링크와 함께 작성해.
   - docs/<과제명>_eval_QA.md: 과제 목표, 기능 검증 매트릭스, 5대 평가문항 심층 답변을 소스코드 상대경로 링크와 함께 작성해.

3. 코드베이스 전수 고밀도 주석화:
   - src/ 내 모든 모듈 맨 위에 파일 개요(아키텍처, 역할, 심볼, 시간복잡도)를 상세히 작성해.
   - 모든 함수와 클래스에 Google Style docstring(Args, Returns, Raises)을 작성해.
   - 모든 코드 라인 우측에 탭 하나(\t#)를 띄고 친절한 인라인 주석을 작성해.

4. 기술 용어집 및 학습 백과사전 집대성:
   - 코드와 QA 문서에 사용된 모든 핵심 CS 개념, 알고리즘, 자료구조, 수학적 증명, 엣지 케이스를 총정리하여 study/study.md에 집대성해.

5. 메인 대시보드 및 상호 연동 링크 직조:
   - README.md, docs QA 문서들, study.md, src 코드 간에 100% 클릭 가능한 상호 링크 체계를 완성해.
   - 모듈별 핵심 흐름을 단일 책임 Mermaid 다이어그램으로 시각화해.

6. 자체 검수 및 자동 Git 커밋:
   - 단위 테스트 스위트(test_*.py)를 실행해 100% 통과하는지 검증해.
   - utils/validate_rules_sync.py와 utils/validate_mermaid_syntax.py를 실행해 규칙과 문법을 검증해.
   - 통과 시 docs/CONVENTIONS.md 규격에 맞춰 자동 커밋하고, 현재 KST 시각과 clickable file:// 링크를 포함해 최종 보고해.
```

---

## 🚀 2. 초간결 한 줄 프롬프트 (간단 입력용)

```markdown
/goal harness 세팅(python3 harness/setup_harness.py)하고, docs 자료 분석해서 b5_1처럼 mission_QA, eval_QA, 코드 전수 고밀도 주석화, study.md, README 상호 링크 완성하고 테스트 검수 후 커밋까지 원스톱으로 끝내줘.
```

---

## 🛠️ 3. 단계별 개별 진행 프롬프트 (원하는 단계만 수행 시)

### [A] 하네스 환경 세팅만 수행할 때
```markdown
harness 폴더를 복사해뒀어. python3 harness/setup_harness.py를 실행해서 새 과제에 필요한 규칙과 도구들을 세팅하고 동기화 상태를 검증해줘.
```

### [B] 코드 주석화만 집중 수행할 때
```markdown
src/ 내 모든 파이썬 파일 상단에 상세 파일 개요 docstring을 달고, 모든 함수/메서드에 Args/Returns를 포함한 docstring을 달고, 모든 코드 라인 우측에 탭(\t#) 인라인 주석을 달아줘. 기존 주석과 로직은 100% 보존해.
```

### [C] 학습 백과사전(study.md) 및 README만 작성할 때
```markdown
현재 구현된 코드와 docs 문서를 분석해서 study/study.md에 컴퓨터 공학 개념 백과사전을 상세히 작성하고, README.md에 프로젝트 대시보드 및 상호 링크를 완성해줘.
```

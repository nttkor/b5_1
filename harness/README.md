# 🧰 과제 자동화 하네스 키트 (`harness/`)

본 디렉터리는 새로운 과제나 프로젝트를 시작할 때 **단 1개의 폴더 복사만으로 완벽한 하네스 엔지니어링 환경을 이식**할 수 있도록 준비된 **올인원 턴키(Turnkey) 패키지**입니다.

---

## ❓ 다음 과제할 때 무엇을 복사하고 어떻게 말하면 되나요?

### 1️⃣ 복사할 것: 오직 `harness` 폴더 1개만 복사하세요!
새 과제 프로젝트 디렉터리로 `harness` 폴더를 통째로 복사합니다:
```bash
# 예시: b5_1의 harness 폴더를 새 과제 b5_2로 복사
cp -r /Users/mpeg46551/b5_1/harness /path/to/새_과제_디렉터리/
```

### 2️⃣ 준비할 것: `docs/`에 과제 자료 넣어두기
새 과제의 미션 PDF/md 파일 또는 평가 기준서 PDF/md 파일을 `docs/` 폴더에 넣어둡니다.
(폴더가 없더라도 하네스 스크립트가 자동 생성해 줍니다.)

### 3️⃣ 에이전트에게 할 말: 프롬프트 딱 한 줄 전송하기
새 프로젝트 창에서 Antigravity에게 아래 프롬프트를 전송하면 끝납니다:

```markdown
/goal harness 세팅(python3 harness/setup_harness.py)하고, docs 자료 분석해서 b5_1처럼 mission_QA, eval_QA, 코드 전수 고밀도 주석화, study.md, README 상호 링크 완성하고 테스트 검수 후 커밋까지 원스톱으로 끝내줘.
```
*(더 상세한 프롬프트 옵션은 [`harness/PROMPT_TEMPLATE.md`](PROMPT_TEMPLATE.md)를 참고하세요.)*

---

## 📁 `harness/` 내부 디렉터리 및 파일 구조

```
harness/
├── setup_harness.py            # 🚀 하네스 자동 설치 러너 (1초 만에 전체 환경 구축)
├── README.md                   # 📖 본 하네스 패키지 총괄 안내서
├── PROMPT_TEMPLATE.md          # 📋 에이전트 전송용 복사용 프롬프트 템플릿 모음
├── GEMINI.md                   # 🛡️ harness 디렉터리 전용 규칙
├── AGENTS.md                   # 🛡️ GEMINI.md 100% 동기화 쌍
│
├── rules/                      # 📜 듀얼 규칙 파일 원본 템플릿
│   ├── ROOT_RULES.md           # 7대 핵심 운영 규칙 (루트 GEMINI.md / AGENTS.md)
│   ├── CONVENTIONS.md          # Git 커밋 규격 및 코드 컨벤션
│   ├── SRC_RULES.md            # src 모듈 구현 및 제약 규칙
│   ├── DOCS_RULES.md           # docs 문서 불변성 및 서식 규칙
│   ├── STUDY_RULES.md          # study 기술 백과 및 다이어그램 규칙
│   ├── UTILS_RULES.md          # utils 하네스 툴셋 관리 규칙
│   └── HARNESS_RULES.md        # harness 턴키 패키지 관리 규칙
│
├── tools/                      # 🛠️ 재사용 하네스 검증 툴셋
│   ├── validate_rules_sync.py  # 듀얼 규칙(GEMINI.md <-> AGENTS.md) 100% 동기화 자동 검증기
│   ├── validate_mermaid_syntax.py # Mermaid 다이어그램 문법/엣지라벨 오류 자동 검사기
│   ├── inspect_codebase_memory.py # 하네스 Fast Lookup Map 자동 색인 생성기
│   ├── time_utils.py           # KST 타임스탬프 유틸리티
│   ├── scaffold_assignment_harness.py # 외부 디렉터리 대상 원격 스캐폴더
│   └── README.md               # utils 패키지 명세서
│
└── templates/                  # 📝 상호 연동 표준 마크다운 템플릿
    ├── mission_QA_template.md  # 미션 요구사항 및 구현 매핑 심층 Q&A 템플릿
    ├── eval_QA_template.md     # 평가 기준표 및 5대 평가문항 답변서 템플릿
    ├── study_template.md       # 핵심 CS 개념 및 기술 백과사전 템플릿
    └── README_template.md      # 프로젝트 메인 대시보드 템플릿
```

---

## ⚙️ `setup_harness.py`가 자동으로 해주는 일 (수동 작업 제로)

터미널에서 `python3 harness/setup_harness.py`를 실행하거나 에이전트가 호출하면:

1. **표준 디렉터리 자동 구축**: `src/`, `docs/`, `study/`, `utils/`를 즉시 생성합니다.
2. **5쌍 듀얼 규칙 자동 배포**: 루트 및 4개 서브디렉터리에 `GEMINI.md`와 `AGENTS.md`를 100% 일치하도록 배치합니다.
3. **커밋 컨벤션 설정**: `docs/CONVENTIONS.md`를 배치합니다.
4. **검증 도구 자동 설치**: `utils/`에 5종의 핵심 자동화 검증 도구를 복사합니다.
5. **상호 연동 문서 스켈레톤 생성**: 해당 과제명에 맞는 `docs/<과제명>_mission_QA.md`, `docs/<과제명>_eval_QA.md`, `study/study.md`, `README.md`를 즉시 생성합니다.
6. **자가 검증(Self-Verification)**: `python3 utils/validate_rules_sync.py`를 자동 실행하여 모든 규칙 파일이 100% 동기화되었는지 즉석 검증합니다.

---

## 🎯 하네스 엔지니어링의 3대 핵심 효과

1. **탐색 시간 0초 (No Full-Scan)**:
   에이전트가 매 프롬프트마다 수십 개의 폴더를 뒤지는 비효율(`find`, `grep`)을 원천 차단하고, Fast Lookup Map 색인표로 목적 파일에 즉시 직행합니다.
2. **품질 균일성 100% 보장**:
   어떤 과제를 진행하더라도 동일한 고품질 서식(Google Style docstring, 우측 탭 인라인 주석, 상호 하이퍼링크, 단일 책임 Mermaid 다이어그램)을 일관되게 산출합니다.
3. **중간 멈춤 없는 자율 완결 (Autonomous Execution)**:
   에이전트가 사용자에게 사소한 확인을 되묻지 않고, 계획 수립부터 테스트 통과, Git 커밋, 최종 KST 보고까지 끝까지 일괄 처리합니다.

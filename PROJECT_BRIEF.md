# Project Brief

## Project Name
**Opiter**

이름 어원: `Open` + `Editor` 합성. 동시에 게임 슬랭 `OP`(overpowered)에서 "최강 에디터"의 이중 의미.
부수적으로 고대 로마 praenomen `Opiter`(기원전 5세기 집정관 Opiter Verginius Tricostus)와 동일 형태이나 직접 차용은 아님.

## Final Goal
무료 오픈소스 통합 문서 편집기 **Opiter**의 **MVP 프로토타입(Phase 1~3)** 구현.

- **장기 비전**: PDF, DOCX, HWP 등 다중 문서 포맷을 하나의 프로그램에서 편집할 수 있는 통합 에디터
- **본 PROJECT_BRIEF.md 범위**: PDF 뷰어 + 페이지 조작 + 주석 기능까지 갖춘 사용 가능한 PDF 에디터 프로토타입
- **본 범위 외 (별도 PROJECT_BRIEF.md로 분리)**: Phase 4(고급 기능), Phase 5(다중 포맷 확장), 멀티 OS 패키징

## Tech Stack & Environment
- **언어**: Python 3.11+
- **GUI 프레임워크**: PySide6 (Qt for Python)
- **PDF 처리 라이브러리**:
  - `PyMuPDF` (fitz) — 렌더링/편집 핵심
  - `pypdf` — 페이지 조작 (합치기/나누기/회전)
  - `pdfplumber` — 텍스트/표 추출
- **패키지 관리**: `uv`
- **테스트**: `pytest`
- **빌드 타겟 (본 범위)**: 단일 OS - Linux (개발 환경 WSL2). 멀티 OS 빌드는 본 범위 외.
- **GUI 실행 환경 가정**: WSLg (Windows 11) 또는 X11 forwarding 설정된 WSL2

## Main Features

### Phase 1: 기본 뷰어
- PDF 파일 열기, 렌더링, 페이지 넘기기
- 줌 인/아웃, 페이지 맞춤 (fit-to-page, fit-to-width)
- 사이드바 썸네일 네비게이션
- 텍스트 검색
- 다크 모드 / 라이트 모드 토글

### Phase 2: 페이지 조작
- 페이지 추가 / 삭제 / 순서 변경
- 페이지 회전 (90도 단위)
- PDF 합치기 (여러 파일 → 하나)
- PDF 나누기 (범위 / 낱장별)
- PDF 추출 (특정 페이지만 새 파일로)

### Phase 3: 주석 및 편집
- 텍스트 하이라이트 / 밑줄 / 취소선
- 스티키 노트(댓글) 추가
- 자유 그리기 (펜 도구)
- 도형 삽입 (사각형, 원, 화살표)
- 텍스트 박스 추가

## Directory Structure
```
opiter/
├── README.md
├── PROJECT.md              # 프로젝트 철학/비전
├── PROJECT_BRIEF.md        # 본 파일 (작업 기준 문서)
├── FEATURES.md             # 기능 스펙 + 전체 로드맵 (Phase 1~5)
├── ARCHITECTURE.md         # 아키텍처 문서
├── CONTRIBUTING.md         # 기여 가이드
├── LICENSE                 # MIT License
├── pyproject.toml          # 메타데이터 + 의존성
├── .gitignore
├── src/
│   └── opiter/
│       ├── __init__.py
│       ├── __main__.py     # python -m opiter 진입점
│       ├── main.py         # 앱 진입 함수
│       ├── ui/             # GUI 컴포넌트 (윈도우, 다이얼로그, 위젯)
│       ├── core/           # PDF 처리 로직 (모델, 뷰어, 편집)
│       ├── utils/          # 유틸리티
│       └── resources/      # 아이콘, 스타일시트, i18n 번역
├── tests/                  # pytest 테스트
├── docs/                   # 추가 문서
├── samples/                # 테스트용 샘플 PDF
└── build/                  # 빌드 스크립트 (본 범위 외, 자리만 마련)
```

## Completion Criteria

본 프로젝트는 다음 모든 조건을 만족할 때 완료로 선언한다.

### 기능 검증
- [ ] **Phase 1**: 모든 6개 기능이 실제 PDF 파일로 동작 확인
  - 예시 검증: `samples/small.pdf`(~10페이지)를 열어 다음을 확인
    - 첫 페이지 렌더링 후 마우스/키보드로 마지막 페이지까지 네비게이션
    - 줌 50% / 100% / 200% / fit-to-width 각각 동작
    - 썸네일 클릭으로 임의 페이지 점프
    - "the" 같은 단어 검색 시 모든 매칭 위치 하이라이트
    - 다크모드 토글 시 UI 색상 즉시 전환
- [ ] **Phase 2**: 모든 5개 기능이 PDF 파일을 생성/변경하여 결과물 검증
  - 예시 검증:
    - 10페이지 PDF에서 5번 페이지 삭제 → 9페이지 결과 PDF 생성, 다른 뷰어로 열어 확인
    - 2개 PDF 합치기 → 페이지 수 합산 일치
    - 10페이지 PDF를 3+3+4로 나누기 → 3개 파일 생성, 페이지 수 일치
- [ ] **Phase 3**: 모든 5개 주석 기능이 저장 후 다른 PDF 뷰어(예: 시스템 기본 뷰어, evince)에서도 보임

### 기술적 검증
- [ ] 단일 OS(Linux/WSL2)에서 `uv run opiter` 실행 성공
- [ ] `pytest` 전체 테스트 통과
- [ ] 최소 3종류 샘플 PDF로 검증
  - 소용량 (< 1MB, ~10페이지)
  - 대용량 (> 50MB, > 500페이지) — 메모리/응답성 확인
  - 엣지 케이스 (한글 폰트 포함, 이미지 위주, 스캔 PDF)
- [ ] 손상된 PDF, 암호화된 PDF에 대한 graceful handling (크래시 없이 에러 다이얼로그)

### 문서/품질
- [ ] README.md에 설치/실행 가이드 명확히 작성
- [ ] LICENSE 파일 (MIT)
- [ ] 모든 `[ASSUMPTION]` 항목이 사용자에게 보고됨
- [ ] Self-Verification Report 작성 (각 Phase 완료 시 1회씩, 총 3회 + 최종 1회)

## Notes

### 법적/윤리적 제약 (절대 준수)
- 리버스 엔지니어링 금지: Adobe Acrobat, 한컴오피스 등 기존 프로그램 디컴파일/내부 분석 금지
- 모든 구현은 공개 포맷 스펙(ISO 32000 등)과 오픈소스 라이브러리만 기반
- 상표권 회피: "Adobe", "Acrobat", "한글", "Office", "Word" 등 사용 금지
- DRM 우회 기능 금지 (암호 PDF의 보안 해제 등)
- 라이선스: MIT 또는 Apache 2.0
- 모든 의존성 라이선스가 상업 배포 호환되는지 확인 (GPL 계열은 신중)

### 설계 고려사항
- **국제화(i18n)**: 한국어/영어 지원 구조를 처음부터 설계 (Qt Linguist 또는 gettext)
- **접근성**: 스크린리더, 키보드 네비게이션 고려
- **성능**: 대용량 PDF(수백 MB, 수천 페이지) 처리 가능 설계 (lazy 페이지 로딩, 썸네일 캐싱)
- **에러 처리**: 손상/암호화된 PDF graceful handling

### 코드 스타일
- 기본 영어 주석. 한국 사용자 특화 부분(예: 한글 폰트 처리)은 한글 주석 가능
- 의미 단위 잦은 git 커밋

### 환경 가정
- 개발: WSL2 Linux (현재 사용자 환경)
- PySide6 GUI 표시는 WSLg(Win11) 또는 X11 forwarding 필요 — 환경 미충족 시 셋업 단계에서 사용자에게 보고

## Task Progress

- [x] **Step 1**: 프로젝트 초기 셋업 (디렉터리, `pyproject.toml`, `.gitignore`, 의존성 설치)
- [x] **Step 2**: 핵심 문서 작성 (`README.md`, `PROJECT.md`, `FEATURES.md`, `ARCHITECTURE.md`, `LICENSE`, `CONTRIBUTING.md`)
- [x] **Step 3**: 기본 애플리케이션 프레임 (메인 윈도우, 메뉴/툴바, PDF 열기 다이얼로그, 첫 페이지 렌더링)
- [x] **Step 4-1**: 페이지 네비게이션 (Prev/Next/First/Last/GoTo + 단축키 + 인디케이터 + 휠 edge-trigger 페이지 전환)
- [x] **Step 4-2**: 줌 컨트롤 (Zoom In/Out, fit-to-width, fit-to-page, 프리셋, Ctrl+휠)
- [x] **Step 4-3**: 썸네일 사이드바 (좌측 도크, 클릭 점프, 양방향 동기화, F4 토글)
- [x] **Step 4-4**: 텍스트 검색 (Ctrl+F 검색바, F3/Shift+F3 다음/이전, 매치 카운터, 노란색 오버레이)
- [x] **Step 4-5**: 다크/라이트 모드 토글 (View 메뉴 + QPalette + QSS, Ctrl+Shift+D)
- [x] **Step 5**: Phase 1 Self-Verification Report ([docs/phase1_self_verification.md](docs/phase1_self_verification.md))
- [x] **Step 6-1**: Save / Save As 인프라 + 페이지 회전 (90° 누적, modified 마커, 저장 확인)
- [x] **Step 6-2**: 페이지 삭제 (확인 다이얼로그) + 빈 페이지 삽입 (이웃 페이지 크기 상속)
- [x] **Step 6-3**: 페이지 순서 변경 (썸네일 드래그, 뷰어 follow 로직, fitz.select 기반)
- [x] **Step 6-4**: PDF 추출 (단일 범위→1파일) + 나누기 (다중 범위→N파일 / 낱장→N파일)
- [ ] **Step 6-5**: PDF 합치기 (다중 파일 선택, 순서 지정)
- [ ] (Undo/Redo는 폴리싱 단계로 deferral — ARCHITECTURE.md의 QUndoStack 도입은 Phase 2~3 완료 후 일괄)
- [ ] **Step 7**: Phase 2 Self-Verification Report
- [ ] **Step 8**: Phase 3 구현 (하이라이트/밑줄/취소선, 스티키 노트, 자유 그리기, 도형, 텍스트 박스)
- [ ] **Step 9**: Phase 3 Self-Verification Report
- [ ] **Step 10**: 최종 통합 테스트 + 완료 선언

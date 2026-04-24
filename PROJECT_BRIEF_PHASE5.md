# Project Brief — Phase 5 (Multi-Format Tabs + Cross-Format Export)

> Phase 1~4 + Polish 완료 후 진행. 기존 brief 중 가장 큰 단계.
> 다음 단계: 통합 테스트 → 멀티 OS 패키징 → GitHub 공개.

## Project Name
Opiter — Phase 5: Universal Document Workbench

## Final Goal
"한 프로그램 안에서 PDF + DOCX + HWP를 모두 다룬다"는 비전을 **탭 기반 UI**로 달성. MVP 수준: 각 포맷을 열 수 있고(뷰 + 필요한 경우 제한적 편집), **PDF → DOCX 변환이 강력**하게 동작.

## 핵심 포지셔닝
> "One free/open-source app to open PDF, DOCX, and HWP — with Acrobat-class PDF annotation and one-click PDF→DOCX conversion."

시장에 이 조합 없음. 특히 **한국어 HWP 뷰어** + **오픈소스 PDF→DOCX**가 결합된 상용/OSS 대안이 사실상 부재.

## Tech Stack 추가
- `pdf2docx` — PDF → DOCX 변환 (순수 Python, PyMuPDF 기반)
- `python-docx` — DOCX 읽기/쓰기
- `pyhwp` — HWP 텍스트 추출 (최신 호환성 확인 필요)
- LibreOffice (`soffice` CLI) — 선택적, HWP export best-effort용

## Main Features (7 sub-steps)

### Tab Infrastructure
- **11-1**: `MainWindow`를 `QTabWidget` 기반 shell로 리팩터. `AbstractEditor` 인터페이스 도입. 기존 PDF UI를 `PDFEditor` 위젯으로 캡슐화 (ViewerWidget + 썸네일 + 북마크 + 검색바)

### 새 포맷 탭
- **11-2**: `DOCXEditor` — `python-docx` 파싱 → `QTextEdit` 리치텍스트 표시. MVP에서는 **읽기 전용 뷰어** (편집은 후속 brief)
- **11-3**: `HWPEditor` — `pyhwp`로 텍스트 추출 → 표시. 레이아웃 복원 제한적

### 통합 워크플로우
- **11-4**: Open 다이얼로그에서 PDF/DOCX/HWP 확장자 자동 라우팅. 파일 선택 시 해당 포맷의 탭 생성

### Cross-Format Export
- **11-5**: PDF → DOCX (`pdf2docx` 사용). File > Export as DOCX… 메뉴. 다이얼로그에 "Include annotations" 체크박스
- **11-6**: PDF → HWP (best-effort). LibreOffice + `h2orestart` 확장 감지 → 있으면 DOCX 경유 변환, 없으면 메뉴 비활성 + 안내

### 마무리
- **11-7**: Phase 5 SVR + 통합 검증

## Directory Structure (추가)
```
src/opiter/
├── ui/
│   ├── editors/
│   │   ├── __init__.py
│   │   ├── abstract_editor.py  # 공통 인터페이스
│   │   ├── pdf_editor.py       # 기존 PDF UI 캡슐화
│   │   ├── docx_editor.py      # 11-2
│   │   └── hwp_editor.py       # 11-3
│   └── export_dialog.py        # PDF→DOCX/HWP 옵션 (주석 포함 체크박스 등)
└── core/
    ├── pdf_to_docx.py          # 11-5
    └── pdf_to_hwp.py           # 11-6
```

## Completion Criteria
- [ ] PDF 탭 기존 기능 무회귀 (Phase 1~4 + Polish 모든 기능)
- [ ] DOCX 파일 열기 → 내용 표시 (텍스트/서식 기본)
- [ ] HWP 파일 열기 → 텍스트 내용 표시
- [ ] Open 다이얼로그에서 포맷 감지 및 정확한 탭 생성
- [ ] PDF → DOCX 변환: 3페이지 샘플에서 텍스트/이미지/표 보존 확인 (Word/LO에서 열어 검증)
- [ ] PDF → HWP: LO + h2orestart 있는 환경에서 시도 성공 또는 없을 때 친절한 안내
- [ ] 기존 183 테스트 무회귀, 신규 테스트 ≥ 20개
- [ ] Phase 5 SVR 작성

## Notes
- **사용자 검증 주기**: 이전 phase들보다 크므로 **각 sub-step별로 배치 모드**. 11-1 끝나면 한 번 검증, 11-2/11-3 묶어 한 번, 11-5/11-6 묶어 한 번
- **라이브러리 품질 리스크**:
  - `pdf2docx`: 간단/중간 복잡도 PDF에서 양호. 매우 복잡한 레이아웃은 손실 가능
  - `pyhwp`: 오래된 라이브러리, 최신 HWP 포맷 부분 지원
- **탭 간 공유/분리 상태**: preferences는 전역, undo stack은 탭별, recent files는 전역, 도구 선택은 PDF 탭 내부

## Task Progress
- [x] **11-1**: Tab infrastructure (QTabWidget 중앙 위젯, PDF 탭 고정, DOCX/HWP 동적 탭)
- [x] **11-2**: DOCXEditor 뷰어 (python-docx → HTML → QTextEdit)
- [x] **11-3**: HWPEditor 뷰어 (pyhwp 텍스트 추출)
- [x] **11-4**: Format-aware Open 라우팅 (확장자 기반 탭 생성)
- [x] **11-5**: PDF → DOCX export (pdf2docx + ExportOptionsDialog)
- [x] **11-6**: PDF → HWP export best-effort (soffice + h2orestart, 부재 시 안내)
- [x] **11-7**: Phase 5 SVR ([docs/phase5_self_verification.md](docs/phase5_self_verification.md))

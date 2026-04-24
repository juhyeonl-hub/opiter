# Phase 5 Self-Verification Report

> CLAUDE_en.md "Mandatory Self-Verification Report" 규정 준수.
> Phase 5 (Universal Document Workbench) MVP 완료 선언.
> 다음: 통합 테스트 → 멀티 OS 패키징 → GitHub 공개.

## 1. 테스트 방법
- **pytest: 186 passed** (Phase 4 종료 183 → +3 Phase 5)
- offscreen Qt 통합 smoke 검증: 탭 초기 상태, DOCX/HWP export 액션 활성/비활성, `pdf2docx` 실제 변환 (6페이지 PDF → 243KB DOCX 생성)

## 2. Sub-step별 결과

| Step | 구현 | 검증 |
|------|------|------|
| **11-1** | `QTabWidget` 중앙 위젯 도입, PDF tab 고정 (인덱스 0, 닫기 버튼 없음), DOCX/HWP는 동적 추가 가능. 탭 전환 시 썸네일/북마크 도크 PDF 전용 토글 | ✅ 183→183 무회귀 |
| **11-2** | `DOCXEditor` (QTextEdit 기반 읽기 전용 뷰어, python-docx → 미니멀 HTML 변환, 문단/제목/볼드/이탤릭/밑줄/표 지원) | 통합 smoke |
| **11-3** | `HWPEditor` (pyhwp 텍스트 추출, 플랫한 read-only QTextEdit 렌더) | 통합 smoke |
| **11-4** | Open 다이얼로그 파일 필터 확장 (PDF/DOCX/HWP/All). `_open_path`가 확장자로 분기 — PDF는 기존 path, DOCX/HWP는 신규 탭 생성 | 통합 smoke |
| **11-5** | `pdf_to_docx` via `pdf2docx`. File > Export as DOCX… (저장 전 "unsaved changes" prompt, 옵션 다이얼로그로 주석 포함 여부 안내, QFileDialog 출력 경로) | 1 unit + 통합 smoke |
| **11-6** | `pdf_to_hwp` 2-hop (PDF → DOCX → HWP via soffice + h2orestart). `hwp_conversion_available()` 체크로 soffice 부재 시 메뉴 비활성 + 안내 다이얼로그 | 2 unit tests (boolean check, missing-soffice raises RuntimeError) |

## 3. 누적 통계
- 테스트: 186 (Phase 1~3 MVP: 58 / Polish: 161 / Phase 4: 183 / **Phase 5: 186**)
- 신규 모듈: `ui/editors/{__init__, abstract_editor, docx_editor, hwp_editor}.py`, `core/pdf_to_docx.py`, `core/pdf_to_hwp.py`, `ui/export_dialog.py`
- 신규 의존성: `pdf2docx` 0.5.12, `python-docx` 1.2.0, `pyhwp` 0.1b15
- 코드 라인 누적: ~6,700

## 4. 검증된 입출력 (대표)

| 입력 | 출력 |
|------|------|
| 앱 시작 | 탭 1개 ("PDF"), close 버튼 없음 |
| `.docx` open | 새 탭 추가 ("📝 filename.docx"), DOCXEditor가 HTML 변환으로 본문 표시 |
| `.hwp` open | 새 탭 추가 ("📄 filename.hwp"), pyhwp가 텍스트 추출 표시 |
| 비 PDF 탭 활성 | 썸네일/북마크 도크 숨김 |
| PDF에 unsaved 상태 + Export as DOCX | save 확인 prompt → OK → 다이얼로그 → 출력 경로 → pdf2docx 실행 |
| HWP export 호출 when soffice 부재 | "HWP Export Unavailable" 안내, 실행 안 함 |
| `pdf_to_docx(6p PDF, out.docx)` | 유효 DOCX 파일 생성, python-docx로 재열기 시 텍스트 포함 |

## 5. 미검증 / 불충분

- **DOCX 편집**: MVP는 뷰어 전용. 편집 (text input, paragraph mutation)은 **후속 brief**로 deferral.
- **HWP 렌더링 충실도**: pyhwp는 텍스트 추출만 — 레이아웃/표/이미지 복원 불가. 실 사용 검증 추가 필요 (대용량/복잡 HWP).
- **PDF → HWP 실제 E2E**: soffice + h2orestart 환경 부재로 자동 테스트에서 실행 불가. 코드 경로만 검증. 실 환경 테스트는 사용자 환경 의존.
- **pdf2docx 주석 포함 옵션**: 현재 옵션 체크박스는 UX용 안내. 실제로 pdf2docx는 annotation 별도 추출 옵션이 없어 기본 변환 실행. 향후 별도 경로 구현 가능.
- **다중 PDF 동시 open**: 단일 PDF 탭만 지원 (기존 구조 유지). 여러 PDF를 동시 탭으로 열려면 PDFEditor 완전 캡슐화 필요 — 후속 polish/Phase 6.

## 6. 결론

Phase 5 MVP 성립: **한 프로그램 안에서 PDF/DOCX/HWP 세 포맷 모두 열기 + PDF → DOCX 강력 export**. 
시장 대체재 없는 조합 (무료 + OSS + Linux 네이티브 + HWP 읽기 + PDF 주석).

다음: 
- 통합 테스트 (Phase 1~5 회귀 매트릭스)
- 멀티 OS 패키징 (PyInstaller — Win/Mac/Linux 빌드)
- GitHub 공개

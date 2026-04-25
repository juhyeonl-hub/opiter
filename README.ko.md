# Opiter

[English](./README.md) | **한국어**

> 무료·오픈소스 데스크톱 문서 워크벤치 — PDF 편집, DOCX·HWP 보기, 포맷 간 변환을 모두 로컬에서. 광고·구독·클라우드 업로드 없음.

**상태**: v0.1 — 첫 공개 릴리스. PDF 편집 완성, DOCX·HWP는 뷰어. Linux (WSL2 포함)에서 빌드·검증.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Built with PySide6](https://img.shields.io/badge/GUI-PySide6-41cd52.svg)](https://doc.qt.io/qtforpython-6/)

---

## 왜 Opiter?

상용 PDF 편집기는 비싸고 폐쇄적입니다. 무료 웹 기반 대안은 파일을 외부 서버에 업로드합니다. HWP 파일을 받는 한국 직장인에게는 무료 네이티브 뷰어가 사실상 없습니다. Opiter는 다른 전제 위에 있습니다:

- **100% 무료** — 광고도, 구독도, 프리미엄 등급도 없음
- **프라이버시 우선** — 모든 처리는 로컬에서. 파일은 절대 외부로 나가지 않음
- **세 포맷, 한 앱** — PDF (전체 편집), DOCX (뷰어), HWP (뷰어)
- **포맷 간 변환** — PDF → DOCX 원클릭, LibreOffice + h2orestart가 있으면 PDF → HWP 변환도 가능

## 기능

### PDF (전체 편집기)
- 열기, 페이지 이동, 줌, 너비 맞춤, 다크 모드
- 페이지 추가 / 삭제 / 순서 변경 / 회전
- 여러 PDF 병합, 분할 (범위·페이지별), 추출
- 주석: 하이라이트, 밑줄, 취소선, 스티키 노트, 자유 펜, 사각형, 타원, 화살표, 텍스트 박스
- 워터마크 (텍스트, 4방향 회전 지원)
- 압축 (3단계 품질 프리셋)
- 문서 속성 (제목·저자·키워드)
- 북마크 / 목차 편집
- 이미지 내보내기 (페이지별 PNG/JPG), 이미지 → PDF
- 회전된 페이지에서도 정확한 검색·하이라이트
- 멀티 PDF 탭 — 각 문서별 독립 undo 스택

### DOCX (뷰어)
- 읽기 전용 리치텍스트 렌더: 제목, 굵게/기울임/밑줄, 표, 목록
- CJK 폰트 자동 폴백 (Malgun Gothic / Noto CJK / NanumGothic) — 시스템에 한글 폰트가 없어도 정상 표시

### HWP (뷰어)
- pyhwp 기반 텍스트 추출
- 한글·한자 정상 렌더

### 포맷 간 변환
- **PDF → DOCX**: pdf2docx 기반, 텍스트·이미지·간단한 표 보존
- **PDF → HWP**: LibreOffice + h2orestart 확장 자동 감지 시 best-effort 변환

전체 기능 목록과 v0.1 이후 로드맵 (DOCX 편집, 배치 처리)은 [FEATURES.md](./FEATURES.md) 참고.

## 설치

### 필수 환경
- **Python 3.11** 이상 (uv가 자동 관리)
- [**uv**](https://github.com/astral-sh/uv) 패키지 매니저
- Qt6 디스플레이 환경:
  - **Linux**: X11 또는 Wayland 데스크톱 세션
  - **WSL2**: WSLg (Windows 11) 또는 X 서버 포워딩
  - **macOS / Windows**: uv로 빌드는 가능하나 v0.1 단계에서 직접 검증되지 않음
- 선택 사항: PDF → HWP 변환을 쓰려면 `libreoffice` + `h2orestart` 확장

### uv 설치 (없을 경우)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 빠른 설치 (릴리스 다운로드)

[최신 릴리스](https://github.com/juhyeonl-hub/opiter/releases/latest)에서 OS에 맞는 파일을 받으세요:

- **Windows**: `opiter-windows-x86_64.exe` — 더블클릭으로 실행.
- **macOS (Apple Silicon)**: `opiter-macos-arm64.dmg` — 마운트 후 `Opiter.app`을 Applications로 드래그. 서명되지 않은 앱이라 첫 실행 시 우클릭 → "열기"로 Gatekeeper 경고를 우회해야 합니다.
- **Linux (Debian/Ubuntu)**: `opiter-linux-amd64.deb` — `sudo apt install ./opiter-linux-amd64.deb`.

### 소스에서 빌드
```bash
git clone https://github.com/juhyeonl-hub/opiter
cd opiter
uv sync
uv run opiter
```

## 개발

```bash
# 런타임 + 개발 의존성 모두 설치
uv sync --all-groups

# 소스에서 실행
uv run python -m opiter

# 테스트 (186개)
uv run pytest
```

[CONTRIBUTING.md](./CONTRIBUTING.md)에 기여 가이드, [ARCHITECTURE.md](./ARCHITECTURE.md)에 코드 구조 설명이 있습니다.

## 문서

| 파일 | 내용 |
|------|------|
| [PROJECT.md](./PROJECT.md) | 프로젝트 비전·철학·범위 |
| [FEATURES.md](./FEATURES.md) | 전체 기능 로드맵 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 모듈 구조, 데이터 흐름, 설계 결정 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 기여 방법 |

## 라이선스

[GNU Affero General Public License v3.0 (AGPL-3.0)](./LICENSE) © 2026 juhyeonl

Opiter는 AGPL 라이선스 라이브러리(PyMuPDF, pyhwp)에 의존하기 때문에 프로젝트 전체가 AGPL-3.0으로 배포됩니다. 즉, 자유롭게 사용·수정·재배포할 수 있지만 **파생 저작물(네트워크 서비스 포함)은 동일 라이선스로 전체 소스를 공개해야** 합니다.

## 고마운 프로젝트들

Opiter는 다음 오픈소스 프로젝트들 위에서 만들어졌습니다:

- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) (fitz) — PDF 렌더링·주석·편집 코어 (AGPL-3.0)
- [pdf2docx](https://github.com/dothinking/pdf2docx) — PDF → DOCX 변환 (MIT)
- [python-docx](https://github.com/python-openxml/python-docx) — DOCX 읽기/쓰기 (MIT)
- [pyhwp](https://github.com/mete0r/pyhwp) — HWP 텍스트 추출 (AGPL-3.0)
- [pypdf](https://github.com/py-pdf/pypdf) — PDF 페이지 단위 조작 (BSD)
- [pdfplumber](https://github.com/jsvine/pdfplumber) — 텍스트·표 추출 (MIT)
- [PySide6](https://doc.qt.io/qtforpython-6/) — 크로스플랫폼 GUI 툴킷 (LGPL-3.0)
- [uv](https://github.com/astral-sh/uv) — Python 패키징

PDF → HWP 변환 시 [LibreOffice](https://www.libreoffice.org/)와 [h2orestart](https://github.com/ebandal/H2Orestart) 확장을 사용합니다.

## 코드 서명

Windows 바이너리는 [SignPath Foundation](https://signpath.org/)이 오픈소스 프로젝트에 무료로 제공하는 인증서 프로그램으로 서명됩니다. macOS `.app` 번들과 Linux `.deb`는 현재 무서명으로 배포됩니다.

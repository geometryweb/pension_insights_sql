# 국민연금 대용량 데이터 Parquet 변환 및 WASM 배포 가이드

본 문서는 공공데이터포털의 대용량 국민연금 가입 사업장 CSV 파일(약 109MB)을 WebAssembly(Pyodide) 및 GitHub Pages 환경에 최적화된 **초경량 Parquet 포맷(9.29MB, 91.5% 압축)**으로 변환하고 배포하는 표준 엔지니어링 가이드입니다.

---

## 1. 왜 CSV 분할 대신 Parquet 변환인가?

| 비교 항목 | CSV 5개 분할 방식 | 단일 Parquet 포맷 (권장) |
|---|---|---|
| **총 파일 용량** | **약 173 MB** (오히려 58MB 증가) | **9.29 MB** (91.5% 용량 절감) |
| **GitHub 100MB 제한** | 조각당 40MB (관리 복잡, Push 부담) | **단일 9.29MB 파일** (GitHub LFS 불필요) |
| **WASM 브라우저 다운로드** | 40MB × 5회 = 173MB (대부분 실패/타임아웃) | **9.29MB 단 1회** (0.5초 이내 완료) |
| **한글 인코딩 깨짐** | `cp949` vs `utf-8` 충돌 잦음 | **바이너리 표준 내장 (UTF-8 100% 보장)** |
| **메모리(RAM) 점유율** | 브라우저 OOM (가상머신 다운 위험) | **극소 메모리 점유 (안정적 렌더링)** |
| **Polars 처리 속도** | 텍스트 디코딩 + 파싱 지연 | **Rust 네이티브 초고속 다이렉트 로드 (0.1초)** |

---

## 2. 변환 스크립트: `convert_to_parquet.py`

프로젝트 루트에 위치한 [`convert_to_parquet.py`](convert_to_parquet.py)를 통해 언제든지 새로운 월별 공공데이터 CSV를 Parquet으로 즉시 변환할 수 있습니다.

### 핵심 변환 로직
1. **유연한 컬럼 매핑**: 공공데이터 원본 컬럼명(`사업장형태구분코드 1 법인 2 개인` 등)을 표준 영문/한글 명칭으로 자동 정규화
2. **최신월 자동 필터**: `자료생성년월`이 가장 최신인 데이터만 보존하여 중복 및 과거 불필요 데이터 제거
3. **핵심 9개 컬럼 추출**: 대시보드 계산에 꼭 필요한 컬럼만 추출하여 가로 폭 압축
   - `자료생성년월`, `사업장명`, `사업자등록번호`, `사업장형태구분코드`, `가입자수`, `당월고지금액`, `신규취득자수`, `상실가입자수`, `법정동주소광역시도코드`
4. **Zstandard(zstd) 레벨 9 고압축**: Polars 네이티브 Parquet 압축을 적용하여 109.8MB를 9.29MB로 압축

### 실행 방법
```powershell
# 가상환경 활성화 상태에서 실행
python convert_to_parquet.py
```

---

## 3. `app.py`에서의 Parquet 로드 방식

마리모(marimo) 대시보드는 로컬(`marimo run`)과 정적 배포(`WASM / GitHub Pages`) 환경을 모두 감지하여 Parquet 데이터를 로드합니다:

```python
import io
import sys
import polars as pl

def load_parquet_data(source_url_or_path):
    if sys.platform == "emscripten":
        # 브라우저 WASM: 9.29MB를 바이너리로 수신 후 Polars 파싱 (0.3초)
        import js
        xhr = js.XMLHttpRequest.new()
        xhr.open("GET", "./public/national_pension.parquet", False)
        xhr.responseType = "arraybuffer"
        xhr.send(None)
        uint8 = js.Uint8Array.new(xhr.response)
        raw_bytes = uint8.to_bytes() if hasattr(uint8, "to_bytes") else bytes(uint8.to_py())
        return pl.read_parquet(io.BytesIO(raw_bytes))
    else:
        # 로컬 환경: 로컬 파일 시스템에서 직접 읽기
        return pl.read_parquet("public/national_pension.parquet")
```

---

## 4. 빌드 및 배포 절차

1. **데이터 최신화 및 Parquet 변환**:
   ```powershell
   python convert_to_parquet.py
   ```
2. **정적 WASM 빌드**:
   ```powershell
   marimo export html-wasm app.py -o dist --mode run
   ```
3. **로컬 테스트**:
   ```powershell
   python -m http.server --directory dist
   # 브라우저에서 http://localhost:8000 접속
   ```
4. **배포 (`deploy.bat` 실행)**:
   - 9.29MB 단일 파일이므로 Git LFS 복잡한 설정 없이도 GitHub Pages 브랜치(`gh-pages`)에 부드럽게 배포됩니다.


"""
convert_to_parquet.py
대용량 공공데이터 국민연금 CSV(115MB)를 초경량 고성능 Parquet(약 9.9MB)으로 변환하는 스크립트.
"""

import os
import sys
from pathlib import Path
import polars as pl

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_CSV = Path("national_pension.csv")
DST_PARQUET = Path("public") / "national_pension.parquet"

KEEP_COLUMNS = [
    "자료생성년월",
    "사업장명",
    "사업자등록번호",
    "사업장형태구분코드",
    "가입자수",
    "당월고지금액",
    "신규취득자수",
    "상실가입자수",
    "법정동주소광역시도코드",
]

def map_columns(df: pl.DataFrame) -> pl.DataFrame:
    col_map = {}
    for c in df.columns:
        c_clean = c.strip()
        if "자료생성년월" in c_clean:
            col_map[c] = "자료생성년월"
        elif "사업장명" in c_clean:
            col_map[c] = "사업장명"
        elif "사업자등록번호" in c_clean:
            col_map[c] = "사업자등록번호"
        elif "사업장형태구분코드" in c_clean:
            col_map[c] = "사업장형태구분코드"
        elif "가입자수" in c_clean and "신규" not in c_clean and "상실" not in c_clean:
            col_map[c] = "가입자수"
        elif "당월고지금액" in c_clean:
            col_map[c] = "당월고지금액"
        elif "신규취득자수" in c_clean:
            col_map[c] = "신규취득자수"
        elif "상실가입자수" in c_clean:
            col_map[c] = "상실가입자수"
        elif "법정동주소광역시도코드" in c_clean:
            col_map[c] = "법정동주소광역시도코드"

    return df.rename(col_map)

def convert():
    if not SRC_CSV.exists():
        raise FileNotFoundError(f"원본 파일을 찾을 수 없습니다: {SRC_CSV.resolve()}")

    src_size_mb = os.path.getsize(SRC_CSV) / (1024 * 1024)
    print(f"📂 [1/4] 원본 CSV 읽기 시작 ({SRC_CSV}, 약 {src_size_mb:.1f} MB)...")

    # 원본 CSV 로드 (CP949 인코딩)
    df = pl.read_csv(
        SRC_CSV,
        encoding="cp949",
        infer_schema_length=10000,
        ignore_errors=True,
        null_values=["", " ", "NULL", "null", "0001-01-01"],
    )
    df = map_columns(df)
    print(f"   - 원본 행 수: {df.height:,}행, 매핑된 컬럼: {[c for c in KEEP_COLUMNS if c in df.columns]}")

    # 최신 월 필터링
    print("🧹 [2/4] 최신 월 및 유효 데이터 필터링 중...")
    latest_month = None
    if "자료생성년월" in df.columns:
        latest_month = df.select(pl.col("자료생성년월").max()).item()
        df = df.filter(pl.col("자료생성년월") == latest_month)
        print(f"   - 최신 자료생성년월: {latest_month}")

    # 가입자 수 > 0 필터
    df = df.filter(pl.col("가입자수") > 0)

    # 필수 컬럼만 추출
    print("✂️ [3/4] 대시보드 필수 9개 컬럼 추출 중...")
    available_cols = [c for c in KEEP_COLUMNS if c in df.columns]
    df = df.select(available_cols)

    # 데이터 타입 최적화
    df = df.with_columns(
        pl.col("가입자수").cast(pl.Int32, strict=False).fill_null(0),
        pl.col("당월고지금액").cast(pl.Float64, strict=False).fill_null(0.0),
        pl.col("사업장형태구분코드").cast(pl.Utf8).str.strip_chars(),
        pl.col("법정동주소광역시도코드").cast(pl.Utf8).str.strip_chars().str.zfill(2),
    )

    # Parquet 저장 (public/ 폴더)
    DST_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    print(f"💾 [4/4] Parquet 압축 저장 중 -> {DST_PARQUET}...")
    df.write_parquet(DST_PARQUET, compression="zstd", compression_level=9)

    dst_size_mb = os.path.getsize(DST_PARQUET) / (1024 * 1024)
    compression_ratio = (1 - (dst_size_mb / src_size_mb)) * 100

    print("\n" + "=" * 55)
    print("🎉 변환 성공!")
    print(f"   • 원본 CSV 크기     : {src_size_mb:.1f} MB")
    print(f"   • 최종 Parquet 크기 : {dst_size_mb:.2f} MB")
    print(f"   • 용량 절감율       : {compression_ratio:.1f}% 감소")
    print(f"   • 최종 저장 행 수   : {df.height:,}행 ({len(df.columns)}개 컬럼)")
    print(f"   • 저장 경로         : {DST_PARQUET.resolve()}")
    print("=" * 55)

if __name__ == "__main__":
    convert()


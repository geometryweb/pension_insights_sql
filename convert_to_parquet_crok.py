

# 결과 확인  ls -lh public/*.parquet
"""
국민연금 분할 CSV → Parquet 변환 스크립트
사용법:
    python convert_to_parquet.py
"""

from pathlib import Path
import polars as pl

# 설정
INPUT_DIR = Path("public")          # CSV가 있는 폴더
OUTPUT_DIR = Path("public")         # 같은 폴더에 저장 (원하면 변경)
PATTERN = "national_pension_part*.csv"
COMPRESSION = "zstd"                # "zstd" | "snappy" | "lz4" | "uncompressed"
# zstd가 압축률과 속도 균형이 가장 좋음

def convert_one(csv_path: Path) -> Path:
    print(f"변환 중: {csv_path.name} ...", end=" ", flush=True)

    # 여러 인코딩 시도 (기존 CSV 문제 대응)
    df = None
    for enc in ("cp949", "utf-8-sig", "utf-8", "euc-kr"):
        try:
            df = pl.read_csv(
                csv_path,
                encoding=enc,
                infer_schema_length=10000,
                ignore_errors=True,
                null_values=["", " ", "NULL", "null", "0001-01-01"],
            )
            # 핵심 컬럼이 있으면 성공으로 간주
            if any(k in "".join(df.columns) for k in ("사업장명", "가입자수", "당월고지금액")):
                print(f"(encoding={enc})", end=" ")
                break
        except Exception:
            continue

    if df is None or df.is_empty():
        raise ValueError(f"읽을 수 없는 파일: {csv_path}")

    # 컬럼명 정리
    df = df.rename({c: c.strip() for c in df.columns})

    out_path = OUTPUT_DIR / (csv_path.stem + ".parquet")
    df.write_parquet(out_path, compression=COMPRESSION)

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"→ {out_path.name}  ({size_mb:.1f} MB)")
    return out_path


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(INPUT_DIR.glob(PATTERN))
    if not csv_files:
        # 단일 파일도 지원
        single = INPUT_DIR / "national_pension.csv"
        if single.exists():
            csv_files = [single]
        else:
            print("변환할 CSV 파일이 없습니다.")
            return

    print(f"총 {len(csv_files)}개 파일 변환 시작...\n")

    for csv_path in csv_files:
        try:
            convert_one(csv_path)
        except Exception as e:
            print(f"실패: {e}")

    print("\n완료!")
    print("생성된 Parquet 파일:")
    for p in sorted(OUTPUT_DIR.glob("national_pension_part*.parquet")):
        print(f"  - {p.name}  ({p.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
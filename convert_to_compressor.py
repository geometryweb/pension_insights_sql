# reduce_pension_csv.py
# 사용법: python reduce_pension_csv.py
# (실행하는 폴더에 public/national_pension.csv 가 있어야 함)

from pathlib import Path
import polars as pl

SRC = Path("public") / "national_pension.csv"
DST = SRC  # 같은 파일에 덮어쓰기

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

def find_column(df: pl.DataFrame, candidates: list[str]) -> str | None:
    cols = {c.strip(): c for c in df.columns}
    for cand in candidates:
        if cand in cols:
            return cols[cand]
        for real in df.columns:
            if cand in real or real.strip() == cand:
                return real
    return None

def reduce_csv(src: Path, dst: Path, only_latest: bool = True):
    if not src.exists():
        raise FileNotFoundError(f"파일 없음: {src.resolve()}")

    print(f"원본: {src.resolve()}")
    print(f"원본 크기: {src.stat().st_size / 1024 / 1024:.1f} MB")

    encodings = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
    df = None
    last_err = None

    for enc in encodings:
        try:
            df = pl.read_csv(
                src,
                encoding=enc,
                infer_schema_length=10000,
                ignore_errors=True,
                null_values=["", " ", "NULL", "null", "0001-01-01"],
            )
            print(f"인코딩 성공: {enc}")
            break
        except Exception as e:
            last_err = e
            continue

    if df is None:
        raise RuntimeError(f"CSV 읽기 실패: {last_err}")

    print(f"원본 행 수: {df.height:,} / 컬럼 수: {len(df.columns)}")

    col_map = {}
    for want in KEEP_COLUMNS:
        found = find_column(df, [want])
        if found:
            col_map[found] = want

    missing = [
        c
        for c in [
            "사업장명",
            "사업장형태구분코드",
            "가입자수",
            "당월고지금액",
            "법정동주소광역시도코드",
        ]
        if c not in col_map.values()
    ]
    if missing:
        print("현재 컬럼 목록:", df.columns)
        raise ValueError(f"필수 컬럼을 찾지 못함: {missing}")

    df = df.select(list(col_map.keys())).rename(col_map)

    df = (
        df.with_columns(
            pl.col("가입자수").cast(pl.Int64, strict=False).fill_null(0),
            pl.col("당월고지금액").cast(pl.Float64, strict=False).fill_null(0.0),
            pl.col("사업장형태구분코드").cast(pl.Utf8).str.strip_chars(),
            pl.col("법정동주소광역시도코드")
            .cast(pl.Utf8)
            .str.strip_chars()
            .str.zfill(2),
        )
        .filter(pl.col("가입자수") > 0)
    )

    if only_latest and "자료생성년월" in df.columns:
        latest = df.select(pl.col("자료생성년월").max()).item()
        before = df.height
        df = df.filter(pl.col("자료생성년월") == latest)
        print(f"최신 월({latest})만 유지: {before:,} → {df.height:,} 행")

    # 선택 컬럼까지 더 줄이고 싶으면 아래 주석 해제
    # df = df.drop(["사업자등록번호", "신규취득자수", "상실가입자수"], strict=False)

    # 임시 파일에 쓴 뒤 원자적으로 교체 (중간에 깨지는 것 방지)
    tmp = dst.with_suffix(".csv.tmp")
    df.write_csv(tmp)
    tmp.replace(dst)

    size_mb = dst.stat().st_size / (1024 * 1024)
    print(f"덮어쓰기 완료: {dst}")
    print(f"최종 행 수: {df.height:,} / 컬럼 수: {len(df.columns)}")
    print(f"파일 크기: {size_mb:.1f} MB")

if __name__ == "__main__":
    reduce_csv(SRC, DST, only_latest=True)
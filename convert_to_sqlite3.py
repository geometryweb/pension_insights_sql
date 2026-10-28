import os
import polars as pl
import sqlite3

csv_file = "public/national_pension.csv"
db_file = "public/national_pension.db"
table_name = "pension"

# 기존 DB 파일이 존재하면 삭제하여 찌꺼기 공간 및 용량 팽창 방지
if os.path.exists(db_file):
    os.remove(db_file)
    print(f"기존 DB 파일 삭제 완료: {db_file}")

print("1. CSV 파일 읽는 중...")
encodings = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
df = None

for enc in encodings:
    try:
        df = pl.read_csv(
            csv_file,
            encoding=enc,
            infer_schema_length=10000,
            ignore_errors=True,
            null_values=["", " ", "NULL", "null", "0001-01-01"],
        )
        print(f"인코딩 성공: {enc}")
        break
    except Exception:
        continue

if df is None:
    raise ValueError("CSV 파일 로드 실패")

# 컬럼명 공백 제거
df = df.rename({c: c.strip() for c in df.columns})

# 필요한 컬럼만 매핑 및 추출
col_map = {}
for c in df.columns:
    if c == "자료생성년월" or c.startswith("자료생성년월"):
        col_map[c] = "자료생성년월"
    elif c == "사업장명":
        col_map[c] = "사업장명"
    elif c == "사업자등록번호":
        col_map[c] = "사업자등록번호"
    elif "사업장형태구분코드" in c:
        col_map[c] = "사업장형태구분코드"
    elif c == "가입자수":
        col_map[c] = "가입자수"
    elif c == "당월고지금액":
        col_map[c] = "당월고지금액"
    elif c == "법정동주소광역시도코드" or "법정동주소광역시도코드" in c:
        col_map[c] = "법정동주소광역시도코드"

df = df.rename(col_map)

# 대시보드에 필요한 컬럼만 선택
keep_cols = list(col_map.values())
df = df.select([c for c in keep_cols if c in df.columns])

# 타입 정제 및 최신 월 데이터만 필터링
df = (
    df.with_columns(
        pl.col("가입자수").cast(pl.Int64, strict=False).fill_null(0),
        pl.col("당월고지금액").cast(pl.Float64, strict=False).fill_null(0.0),
        pl.col("사업장형태구분코드").cast(pl.Utf8).str.strip_chars(),
        pl.col("법정동주소광역시도코드").cast(pl.Utf8).str.strip_chars().str.zfill(2),
    )
    .filter(pl.col("가입자수") > 0)
)

if "자료생성년월" in df.columns:
    latest = df.select(pl.col("자료생성년월").max()).item()
    df = df.filter(pl.col("자료생성년월") == latest)
    print(f"최신 데이터 기준월 적용: {latest}")

print(f"정제된 데이터 행 수: {df.height}행. SQLite로 저장 중...")

# SQLite에 저장
conn = sqlite3.connect(db_file)
df.to_pandas().to_sql(table_name, conn, if_exists="replace", index=False)
conn.close()

print(f"완료! 가벼워진 DB 파일 크기를 확인해보세요: {db_file}")
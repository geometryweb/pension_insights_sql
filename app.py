import marimo as mo
# first
__generated_with = "0.10.0"
app = mo.App(width="medium")


@app.cell
def _import_modules():
    import marimo as mo
    import polars as pl
    import sqlite3
    from pathlib import Path
    from collections import Counter
    import io
    import tempfile
    import urllib.request
    return Counter, Path, io, mo, pl, sqlite3, tempfile, urllib.request


@app.cell
def _font_style(mo):
    # 전역 폰트 설정 (Noto Sans KR)
    font_style = mo.md(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root, body, .markdown, .mo, button, input, select, table, th, td, div, span, p, h1, h2, h3, h4 {
                font-family: "Noto Sans KR", -apple-system, BlinkMacSystemFont, "Segoe UI",
                             "Apple SD Gothic Neo", "Malgun Gothic", "맑은 고딕",
                             "Helvetica Neue", Arial, sans-serif !important;
            }
        </style>
        """
    )
    return (font_style,)


@app.cell
def _title_md(mo):
    title_md = mo.md(
        r"""
        <div style="margin-bottom: 8px;">
            <h1 style="margin:0; font-size:1.8rem; font-weight:700; color:#1a1a2e;">
                국민연금 가입 사업장 대시보드 (SQLite)
            </h1>
            <p style="margin:6px 0 0 0; color:#666; font-size:0.95rem;">
                공공데이터포털 「국민연금공단_국민연금 가입 사업장 내역」 SQLite 기반 반응형 대시보드
                <span title="참고&#10;&#10;• 당월고지금액은 국민연금법 시행령에 따른 기준소득월액 상한액이 적용되어 실제 소득과 차이가 있을 수 있습니다.&#10;• 추정 월평균 소득 = 당월고지금액 ÷ 가입자수 ÷ 0.09 (보험료율 9% 가정)&#10;• 자료생성년월 기준으로 최신 월 데이터만 사용합니다.&#10;• 가입자 수 3인 이상 법인 / 10인 이상 개인 사업장만 포함됩니다." 
                      style="cursor:help; font-size:1.05em; color:#888; margin-left:6px;">
                    ❓
                </span>
            </p>
        </div>
        """
    )
    return (title_md,)


@app.cell
def _load_database(Counter, Path, mo, pl, sqlite3, tempfile, urllib):
    data_path = mo.notebook_location() / "public" / "national_pension.db"

    SIDO_MAP = {
        "11": "서울특별시",
        "26": "부산광역시",
        "27": "대구광역시",
        "28": "인천광역시",
        "29": "광주광역시",
        "30": "대전광역시",
        "31": "울산광역시",
        "36": "세종특별자치시",
        "41": "경기도",
        "42": "강원특별자치도",
        "43": "충청북도",
        "44": "충청남도",
        "45": "전북특별자치도",
        "46": "전라남도",
        "47": "경상북도",
        "48": "경상남도",
        "50": "제주특별자치도",
    }

    def _read_sqlite_from_source(source):
        if isinstance(source, (bytes, bytearray)):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                tmp.write(source)
                tmp_path = tmp.name
            conn = sqlite3.connect(tmp_path)
        else:
            source_str = str(source)
            if source_str.startswith("http://") or source_str.startswith("https://"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                    urllib.request.urlretrieve(source_str, tmp.name)
                    tmp_path = tmp.name
                conn = sqlite3.connect(tmp_path)
            else:
                conn = sqlite3.connect(source_str)
        
        try:
            df = pl.read_database("SELECT * FROM pension", conn)
        except Exception as e:
            conn.close()
            raise ValueError(f"SQLite DB 읽기 실패 (pension 테이블 확인 필요): {e}")
        
        conn.close()
        return df

    def load_data(path, uploaded_bytes=None):
        if uploaded_bytes is not None:
            try:
                df = _read_sqlite_from_source(uploaded_bytes)
            except Exception as e:
                mo.md(
                    f"""
                    ⚠️ **업로드 파일 파싱 실패**
                    오류: `{e}`
                    올바른 SQLite(.db) 파일인지 확인해 주세요.
                    """
                ).callout(kind="warn")
                return pl.DataFrame(), None
        else:
            try:
                df = _read_sqlite_from_source(path)
            except Exception:
                return pl.DataFrame(), None

        df = df.rename({c: c.strip() for c in df.columns})

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
            elif c == "신규취득자수":
                col_map[c] = "신규취득자수"
            elif c == "상실가입자수":
                col_map[c] = "상실가입자수"
            elif c == "법정동주소광역시도코드" or "법정동주소광역시도코드" in c:
                col_map[c] = "법정동주소광역시도코드"

        targets = list(col_map.values())
        if len(targets) != len(set(targets)):
            duplicates = [k for k, v in Counter(targets).items() if v > 1]
            raise ValueError(f"중복 매핑된 컬럼: {duplicates}\n현재 매핑: {col_map}")

        df = df.rename(col_map)

        required = [
            "사업장명",
            "사업장형태구분코드",
            "가입자수",
            "당월고지금액",
            "법정동주소광역시도코드",
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}\n현재 컬럼: {df.columns}")

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
            .with_columns(
                pl.col("법정동주소광역시도코드")
                .replace_strict(SIDO_MAP, default="기타")
                .alias("시도명"),
                pl.when(pl.col("사업장형태구분코드") == "1")
                .then(pl.lit("법인"))
                .when(pl.col("사업장형태구분코드") == "2")
                .then(pl.lit("개인"))
                .otherwise(pl.lit("기타"))
                .alias("사업장형태"),
            )
            .filter(pl.col("가입자수") > 0)
        )

        data_period = None
        if "자료생성년월" in df.columns:
            latest = df.select(pl.col("자료생성년월").max()).item()
            df = df.filter(pl.col("자료생성년월") == latest)

            if latest is not None:
                s = str(latest).strip()
                if "-" in s:
                    year, month = s.split("-")[:2]
                    data_period = f"{year}년 {int(month)}월"
                elif len(s) == 6 and s.isdigit():
                    data_period = f"{s[:4]}년 {int(s[4:6])}월"
                else:
                    data_period = s

        return df, data_period

    df_raw, data_period = load_data(data_path)
    return SIDO_MAP, data_path, df_raw, data_period, load_data


@app.cell
def _file_upload_ui(df_raw, mo):
    file_upload = mo.ui.file(
        filetypes=[".db"],
        label="SQLite DB 파일 업로드 (public 로드 실패 시 사용)",
        kind="area",
    )

    upload_hint = None
    if df_raw.is_empty():
        upload_hint = mo.md(
            """
            <div style="
                background:#fff7ed;
                border:1px solid #fed7aa;
                border-radius:12px;
                padding:16px 18px;
                margin: 8px 0 12px 0;
                color:#9a3412;
                font-size:0.9rem;
            ">
                <strong>데이터베이스 파일을 찾을 수 없습니다.</strong><br>
                • 파일을 해당 경로에 두고 실행하세요.<br>
                • 또는 아래 업로드 영역을 통해 SQLite 파일을 업로드해 주세요.
            </div>
            """
        )
    return file_upload, upload_hint


@app.cell
def _handle_uploaded_file(data_path, data_period, df_raw, file_upload, load_data):
    uploaded_bytes = None
    if file_upload.value:
        try:
            uploaded_bytes = file_upload.value[0].contents
        except Exception:
            uploaded_bytes = None

    if uploaded_bytes is not None:
        df_raw2, data_period2 = load_data(data_path, uploaded_bytes=uploaded_bytes)
        df_final = df_raw2
        period_final = data_period2
    else:
        df_final = df_raw
        period_final = data_period

    return df_final, period_final


@app.cell
def _create_filter_widgets(df_final, mo):
    if df_final.is_empty():
        sido_options = ["전체"]
        type_options = ["전체", "법인", "개인"]
    else:
        sido_list = (
            df_final.select("시도명")
            .unique()
            .sort("시도명")
            .to_series()
            .to_list()
        )
        sido_options = (
            ["전체"]
            + [s for s in sido_list if s != "기타"]
            + (["기타"] if "기타" in sido_list else [])
        )
        type_options = ["전체", "법인", "개인"]

    size_range_options = {
        "전체": (None, None),
        "3인 이상 ~ 5인 미만": (3, 5),
        "5인 이상 ~ 30인 미만": (5, 30),
        "30인 이상 ~ 100인 미만": (30, 100),
        "100인 이상 ~ 300인 미만": (100, 300),
        "300인 이상 ~ 500인 미만": (300, 500),
        "500인 이상": (500, None),
        "5인 미만": (None, 5),
        "30인 미만": (None, 30),
        "100인 미만": (None, 100),
        "300인 미만": (None, 300),
    }

    top_n_options = {
        "상위 10개": 10,
        "상위 50개": 50,
        "상위 100개": 100,
        "상위 500개": 500,
        "전체": None,
    }

    sido_dropdown = mo.ui.dropdown(
        options=sido_options,
        value="전체",
        label="시도명",
    )
    type_dropdown = mo.ui.dropdown(
        options=type_options,
        value="전체",
        label="사업장형태",
    )
    size_range_dropdown = mo.ui.dropdown(
        options=list(size_range_options.keys()),
        value="전체",
        label="가입자수 범위",
    )
    top_n_dropdown = mo.ui.dropdown(
        options=list(top_n_options.keys()),
        value="상위 10개",
        label="표시 개수",
    )

    filters = mo.hstack(
        [sido_dropdown, type_dropdown, size_range_dropdown, top_n_dropdown],
        gap=1.2,
        justify="start",
        wrap=True,
    )
    return (
        filters,
        size_range_dropdown,
        size_range_options,
        sido_dropdown,
        type_dropdown,
        top_n_dropdown,
        top_n_options,
    )


@app.cell
def _render_layout(file_upload, filters, font_style, mo, title_md, upload_hint):
    elements = [
        font_style,
        title_md,
    ]
    if upload_hint is not None:
        elements.append(upload_hint)
        elements.append(file_upload)
    elements.extend(
        [
            mo.md(
                """
                <div style="
                    background: #f8f9fc;
                    border-radius: 12px;
                    padding: 14px 18px;
                    margin: 12px 0 8px 0;
                    border: 1px solid #eef0f5;
                ">
                """
            ),
            filters,
            mo.md("</div>"),
        ]
    )
    mo.vstack(elements, gap=0.4)
    return


@app.cell
def _filter_dataset(
    df_final,
    size_range_dropdown,
    size_range_options,
    sido_dropdown,
    type_dropdown,
    top_n_dropdown,
    top_n_options,
    pl,
):
    df = df_final
    min_size, max_size = size_range_options.get(
        size_range_dropdown.value, (None, None)
    )
    top_n = top_n_options.get(top_n_dropdown.value, 10)

    if not df.is_empty():
        if sido_dropdown.value != "전체":
            df = df.filter(pl.col("시도명") == sido_dropdown.value)
        if type_dropdown.value != "전체":
            df = df.filter(pl.col("사업장형태") == type_dropdown.value)

        if min_size is not None:
            df = df.filter(pl.col("가입자수") >= min_size)
        if max_size is not None:
            df = df.filter(pl.col("가입자수") < max_size)

        df_kpi = df
        df_table = df
    else:
        df_kpi = df
        df_table = df

    return df, df_kpi, df_table, max_size, min_size, top_n


@app.cell
def _render_kpi_section(df_kpi, max_size, min_size, mo, period_final, pl):
    if min_size is None and max_size is None:
        _range_text = "전체"
    elif min_size is not None and max_size is None:
        _range_text = f"{min_size}인 이상"
    elif min_size is None and max_size is not None:
        _range_text = f"{max_size}인 미만"
    else:
        _range_text = f"{min_size}인 이상 ~ {max_size}인 미만"

    _period_text = f"기준: {period_final}" if period_final else ""

    def fmt_won(v: float) -> str:
        if v >= 1e8:
            return f"{v / 1e8:,.1f}억 원"
        if v >= 1e4:
            return f"{v / 1e4:,.0f}만 원"
        return f"{v:,.0f} 원"

    def fmt_num(v: float) -> str:
        return f"{v:,.0f}"

    if df_kpi.is_empty():
        kpi_section = mo.md(
            f"""
            <div style="
                background:#fff5f5;
                border:1px solid #fecaca;
                border-radius:12px;
                padding:20px;
                color:#991b1b;
                text-align:center;
            ">
                선택한 조건에 해당하는 사업장이 없습니다. ({_range_text})
            </div>
            """
        )
    else:
        n_workplaces = df_kpi.height
        total_amount = df_kpi.select(pl.col("당월고지금액").sum()).item()
        avg_members = df_kpi.select(pl.col("가입자수").mean()).item()

        est_income = (
            df_kpi.with_columns(
                (pl.col("당월고지금액") / pl.col("가입자수") / 0.09).alias(
                    "추정월평균소득"
                )
            )
            .select(pl.col("추정월평균소득").mean())
            .item()
        )

        cards_html = f"""
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:14px; margin-top:8px;">
            <div style="
                background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
                border-radius: 16px;
                padding: 18px 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            ">
                <div style="font-size:0.8rem; color:#065f46; font-weight:600; margin-bottom:6px;">추정 월평균 소득</div>
                <div style="font-size:1.55rem; font-weight:700; color:#064e3b;">{fmt_won(est_income)}</div>
                <div style="font-size:0.72rem; color:#047857; margin-top:6px;">당월고지금액 ÷ 가입자수 ÷ 0.09</div>
            </div>

            <div style="
                background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
                border-radius: 16px;
                padding: 18px 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            ">
                <div style="font-size:0.8rem; color:#3730a3; font-weight:600; margin-bottom:6px;">사업장 수</div>
                <div style="font-size:1.55rem; font-weight:700; color:#312e81;">{fmt_num(n_workplaces)}</div>
                <div style="font-size:0.72rem; color:#4338ca; margin-top:6px;">조건: {_range_text}</div>
            </div>

            <div style="
                background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
                border-radius: 16px;
                padding: 18px 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            ">
                <div style="font-size:0.8rem; color:#92400e; font-weight:600; margin-bottom:6px;">평균 가입자수</div>
                <div style="font-size:1.55rem; font-weight:700; color:#78350f;">{fmt_num(avg_members)}</div>
                <div style="font-size:0.72rem; color:#b45309; margin-top:6px;">조건 해당 사업장 평균</div>
            </div>

            <div style="
                background: linear-gradient(135deg, #fce7f3 0%, #fbcfe8 100%);
                border-radius: 16px;
                padding: 18px 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            ">
                <div style="font-size:0.8rem; color:#9d174d; font-weight:600; margin-bottom:6px;">총 당월고지금액</div>
                <div style="font-size:1.55rem; font-weight:700; color:#831843;">{fmt_won(total_amount)}</div>
                <div style="font-size:0.72rem; color:#be185d; margin-top:6px;">조건 해당 사업장 합계</div>
            </div>
        </div>
        """

        kpi_section = mo.md(cards_html)

    _header = mo.md(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin:18px 0 6px 0;">
            <h2 style="margin:0; font-size:1.15rem; font-weight:650; color:#1a1a2e;">
                KPI · {_range_text}
            </h2>
            <span style="
                background:#f1f5f9;
                color:#475569;
                font-size:0.8rem;
                padding:4px 12px;
                border-radius:20px;
                font-weight:500;
            ">{_period_text}</span>
        </div>
        """
    )

    mo.vstack([_header, kpi_section], gap=0.3)
    return


@app.cell
def _render_table_section(df_table, mo, top_n, pl):
    if not df_table.is_empty():
        _sorted_df = df_table.sort("당월고지금액", descending=True)
        if top_n is not None:
            preview = _sorted_df.head(top_n)
        else:
            preview = _sorted_df

        preview = (
            preview.with_columns(
                (pl.col("당월고지금액") / pl.col("가입자수") / 0.09)
                .round(0)
                .alias("추정월평균소득")
            )
            .with_row_index("번호", offset=1)
            .with_columns(pl.col("번호").cast(pl.Utf8).str.zfill(2))
            .select(
                "번호",
                "사업장명",
                "시도명",
                "사업장형태",
                "가입자수",
                "당월고지금액",
                "추정월평균소득",
            )
        )
        table = mo.ui.table(preview, pagination=True, selection=None)
    else:
        table = mo.md("")

    _top_n_text = "전체" if top_n is None else f"상위 {top_n}개"

    _header = mo.md(
        f"""
        <div style="margin:22px 0 10px 0;">
            <h2 style="margin:0; font-size:1.15rem; font-weight:650; color:#1a1a2e;">
                {_top_n_text} 사업장 상세
            </h2>
        </div>
        """
    )

    mo.vstack([_header, table], gap=0.3)
    return


@app.cell
def _render_footer(mo):
    footer = mo.md(
        """
        <div style="
            margin-top: 2.8rem;
            padding-top: 1rem;
            border-top: 1px solid #e2e8f0;
            font-size: 0.82rem;
            color: #64748b;
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <span>
                데이터 출처:
                <a href="https://www.data.go.kr/data/15083277/fileData.do" target="_blank"
                   style="color:#4f46e5; text-decoration:none;">
                    공공데이터포털 파일데이터
                </a>
            </span>
            <span style="color:#94a3b8;">National Pension Workplace Dashboard · SQLite-ready</span>
        </div>
        """
    )
    footer
    return


if __name__ == "__main__":
    app.run()
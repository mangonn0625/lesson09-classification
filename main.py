import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# 기본 설정 (브라우저 탭 제목과 아이콘)
# ------------------------------------------------------------------
APP_TITLE = "뇌졸중 예측 실습실"
APP_ICON = "🧠"

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")

DATA_URL = (
    "https://raw.githubusercontent.com/mangonn0625/data/"
    "refs/heads/main/stroke.csv"
)
RECORD_DIR = Path(__file__).resolve().parent / "내_기록"
RECORD_FILE = RECORD_DIR / "기록.json"

# 큰 숫자 카드 스타일
st.markdown(
    """
    <style>
    [data-testid="stMetricValue"] { font-size: 2.8rem; font-weight: 700; }
    [data-testid="stMetricLabel"] p { font-size: 1.05rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# 데이터 불러오기
# ------------------------------------------------------------------
@st.cache_data(show_spinner="데이터를 불러오는 중입니다...")
def load_data(url: str) -> pd.DataFrame:
    return pd.read_csv(url, encoding="utf-8")


def describe_values(s: pd.Series) -> str:
    """열의 '값의 종류'를 짧은 글로 설명한다."""
    kinds = s.nunique(dropna=True)
    if kinds <= 10:
        values = sorted(s.dropna().unique(), key=str)
        return f"{kinds}가지: " + ", ".join(str(v) for v in values)
    if pd.api.types.is_numeric_dtype(s):
        return f"숫자 (최소 {s.min():g} ~ 최대 {s.max():g})"
    return f"{kinds}가지"


# ------------------------------------------------------------------
# 내 기록 (json) 불러오기 / 저장하기
# ------------------------------------------------------------------
def load_records() -> dict:
    try:
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        meanings = data.get("meanings", {})
        source = data.get("source", "")
        if isinstance(meanings, dict) and isinstance(source, str):
            return {"meanings": meanings, "source": source}
    except (FileNotFoundError, json.JSONDecodeError, OSError, AttributeError):
        pass
    return {"meanings": {}, "source": ""}


def save_records(records: dict) -> bool:
    try:
        RECORD_DIR.mkdir(parents=True, exist_ok=True)
        with open(RECORD_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


# ------------------------------------------------------------------
# 화면 시작
# ------------------------------------------------------------------
st.title(f"{APP_ICON} {APP_TITLE}")
st.caption("뇌졸중 환자 데이터가 어떤 데이터인지 먼저 살펴봅니다.")

try:
    df = load_data(DATA_URL)
except Exception as e:  # 네트워크 오류 등
    st.error("데이터를 불러오지 못했습니다. 인터넷 연결을 확인하고 새로고침해 주세요.")
    st.exception(e)
    st.stop()

# 처음 한 번만 저장된 기록을 불러온다
if "records_loaded" not in st.session_state:
    saved = load_records()
    st.session_state["initial_meanings"] = saved["meanings"]
    st.session_state["source_text"] = saved["source"]
    st.session_state["last_saved"] = saved
    st.session_state["records_loaded"] = True

# ------------------------------------------------------------------
# 1) 큰 숫자 카드 네 개
# ------------------------------------------------------------------
total_people = len(df)
total_cols = df.shape[1]
stroke_count = int((df["stroke"] == 1).sum())
stroke_rate = stroke_count / total_people * 100 if total_people else 0.0

c1, c2, c3, c4 = st.columns(4)
with c1:
    with st.container(border=True):
        st.metric("전체 사람 수", f"{total_people:,}명")
with c2:
    with st.container(border=True):
        st.metric("열 개수", f"{total_cols}개")
with c3:
    with st.container(border=True):
        st.metric("stroke가 1인 사람 수", f"{stroke_count:,}명")
with c4:
    with st.container(border=True):
        st.metric("stroke가 1인 비율", f"{stroke_rate:.2f}%")

# ------------------------------------------------------------------
# 2) 열 설명 표 (우리말 뜻은 직접 입력)
# ------------------------------------------------------------------
st.subheader("열 설명 표")
st.write("**우리말 뜻** 칸을 더블클릭해서 교재를 보고 직접 적어 보세요.")

initial = st.session_state["initial_meanings"]
info_df = pd.DataFrame(
    {
        "열 이름": df.columns,
        "우리말 뜻": [initial.get(col, "") for col in df.columns],
        "값의 종류": [describe_values(df[col]) for col in df.columns],
        "빈 값 개수": [int(df[col].isna().sum()) for col in df.columns],
    }
)

edited_df = st.data_editor(
    info_df,
    key="info_editor",
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    disabled=["열 이름", "값의 종류", "빈 값 개수"],
    column_config={
        "열 이름": st.column_config.TextColumn("열 이름", width="small"),
        "우리말 뜻": st.column_config.TextColumn(
            "우리말 뜻", help="직접 적어 넣는 칸입니다.", width="medium"
        ),
        "값의 종류": st.column_config.TextColumn("값의 종류", width="large"),
        "빈 값 개수": st.column_config.NumberColumn("빈 값 개수", format="%d"),
    },
)

# ------------------------------------------------------------------
# 3) 데이터 처음 다섯 줄
# ------------------------------------------------------------------
st.subheader("데이터 처음 다섯 줄")
st.dataframe(df.head(5), use_container_width=True, hide_index=True)

# ------------------------------------------------------------------
# 4) 데이터 출처
# ------------------------------------------------------------------
st.subheader("데이터 출처")
st.text_area(
    "교재에 나온 출처를 적어 주세요.",
    key="source_text",
    height=120,
    placeholder="여기에 데이터 출처를 적어 주세요.",
)

# ------------------------------------------------------------------
# 자동 저장 (내_기록/기록.json)
# ------------------------------------------------------------------
current = {
    "meanings": {
        row["열 이름"]: (row["우리말 뜻"] or "")
        for _, row in edited_df.iterrows()
    },
    "source": st.session_state["source_text"],
}

if current != st.session_state["last_saved"]:
    if save_records(current):
        st.session_state["last_saved"] = current
        st.toast("내 기록을 저장했어요.", icon="💾")
    else:
        st.warning("기록을 파일에 저장하지 못했습니다. 폴더 쓰기 권한을 확인해 주세요.")

st.caption(
    "✏️ 적은 내용은 자동으로 `내_기록/기록.json`에 저장되고, "
    "새로고침해도 다시 불러옵니다. (글상자는 바깥을 클릭하면 저장돼요.)"
)

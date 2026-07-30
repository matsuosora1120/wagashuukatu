import os
import sys
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st

# ==========================================
# 1. ページ設定 & ユーザー認証情報
# ==========================================
st.set_page_config(
    page_title="就活エントリー管理", page_icon="💼", layout="wide"
)

# ログイン用ユーザー情報 (ユーザー名: パスワード)
USERS = {"sora": "112358"}

SPREADSHEET_NAME = "就活管理"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")

INDUSTRY_LIST = [
    "未設定",
    "IT・通信",
    "メーカー",
    "商社",
    "金融・保険",
    "コンサル・専門サービス",
    "広告・メディア",
    "不動産・建設",
    "小売・流通",
    "インフラ・交通",
    "公務・団体",
    "その他",
]

STATUS_LIST = [
    "検討中",
    "エントリー済",
    "一次面接",
    "二次面接",
    "最終面接",
    "内定",
    "お見送り",
]


# ==========================================
# 2. スプレッドシート接続（Cloud / ローカル自動判定）
# ==========================================
@st.cache_resource
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    try:
        # ① クラウド環境（Streamlit Secrets）の鍵を使う
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(
                creds_dict, scopes=scopes
            )
        # ② 自分のPC環境の credentials.json を使う
        elif os.path.exists(CREDENTIALS_FILE):
            creds = Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=scopes
            )
        else:
            st.error(
                "認証情報が見つかりません。Streamlit Secrets または credentials.json を配置してください。"
            )
            st.stop()

        client = gspread.authorize(creds)
        spreadsheet = client.open(SPREADSHEET_NAME)
        return spreadsheet.sheet1
    except Exception as e:
        st.error(f"スプレッドシートへの接続に失敗しました: {e}")
        st.stop()


sheet = get_sheet()


def load_data_from_sheet():
    """スプレッドシートからデータを取得しDataFrameとして返す"""
    data = sheet.get_all_values()
    if len(data) <= 1:
        return pd.DataFrame(
            columns=[
                "企業名",
                "業界",
                "ログインID",
                "パスワード",
                "ステータス",
                "メモ",
                "URL",
            ]
        )

    df = pd.DataFrame(data[1:], columns=data[0])
    expected_cols = [
        "企業名",
        "業界",
        "ログインID",
        "パスワード",
        "ステータス",
        "メモ",
        "URL",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    return df[expected_cols]


# ==========================================
# 3. ログイン画面
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

if not st.session_state["logged_in"]:
    st.title("🔒 就活管理システム ログイン")

    with st.form("login_form"):
        username = st.text_input("ユーザーID")
        password = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン")

        if submit:
            if username in USERS and USERS[username] == password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success("ログインに成功しました！")
                st.rerun()
            else:
                st.error("ユーザーIDまたはパスワードが正しくありません。")

    st.stop()


# ==========================================
# 4. メイン画面（ログイン後）
# ==========================================
st.sidebar.write(f"👤 **ログイン中:** `{st.session_state['username']}`")
if st.sidebar.button("🚪 ログアウト"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.rerun()

st.title("💼 就活エントリー管理 Webアプリ")

df = load_data_from_sheet()

st.subheader("📝 データの登録 / 編集")

with st.expander("企業情報の追加・更新・削除", expanded=True):
    col_a, col_b = st.columns(2)

    company_options = ["【新規登録】"] + list(df["企業名"].values)
    selected_company = col_a.selectbox("編集する企業を選択", company_options)

    if selected_company != "【新規登録】":
        row = df[df["企業名"] == selected_company].iloc[0]
        init_company = row["企業名"]
        init_industry = (
            row["業界"] if row["業界"] in INDUSTRY_LIST else "未設定"
        )
        init_my_id = row["ログインID"]
        init_password = row["パスワード"]
        init_status = (
            row["ステータス"] if row["ステータス"] in STATUS_LIST else "エントリー済"
        )
        init_memo = row["メモ"]
        init_url = row["URL"]
    else:
        init_company, init_industry, init_my_id, init_password = (
            "",
            "未設定",
            "",
            "",
        )
        init_status, init_memo, init_url = "エントリー済", "", ""

    # ★ 確実にコピーできる表示エリア
    if selected_company != "【新規登録】" and (init_my_id or init_password):
        st.markdown("**📋 コピー用エリア（右端のコピーボタンを押してください）**")
        cp_col1, cp_col2 = st.columns(2)

        if init_my_id:
            cp_col1.caption("▼ ログインID")
            cp_col1.code(init_my_id, language=None)

        if init_password:
            cp_col2.caption("▼ パスワード")
            cp_col2.code(init_password, language=None)

    with st.form("entry_form"):
        c1, c2 = st.columns(2)
        company = c1.text_input("企業名*", value=init_company)
        industry = c2.selectbox(
            "業界・ジャンル",
            INDUSTRY_LIST,
            index=INDUSTRY_LIST.index(init_industry),
        )

        my_id = c1.text_input("ログインID*", value=init_my_id)
        password = c2.text_input("パスワード", value=init_password)

        status = c1.selectbox(
            "ステータス", STATUS_LIST, index=STATUS_LIST.index(init_status)
        )
        url = c2.text_input("マイページURL", value=init_url)

        memo = st.text_input("メモ", value=init_memo)

        btn_save = st.form_submit_button("💾 保存（新規追加 / 上書き）")

        if btn_save:
            if not company or not my_id:
                st.error("企業名とログインIDは必須項目です。")
            else:
                new_row = [
                    company,
                    industry,
                    my_id,
                    password,
                    status,
                    memo,
                    url,
                ]

                if (
                    selected_company != "【新規登録】"
                    and selected_company in df["企業名"].values
                ):
                    row_idx = (
                        df[df["企業名"] == selected_company].index[0] + 2
                    )
                    sheet.update(f"A{row_idx}:G{row_idx}", [new_row])
                    st.success(f"「{company}」を更新しました！")
                else:
                    sheet.append_row(new_row)
                    st.success(f"「{company}」を新規登録しました！")
                st.rerun()

    if selected_company != "【新規登録】":
        if st.button("🗑️ 選択中の企業を削除", type="primary"):
            row_idx = df[df["企業名"] == selected_company].index[0] + 2
            sheet.delete_rows(row_idx)
            st.success(f"「{selected_company}」を削除しました。")
            st.rerun()

st.divider()

# --- 一覧表示・ソート・絞り込み ---
st.subheader("📊 登録企業一覧")

col_f1, col_f2 = st.columns([1, 2])
filter_ind = col_f1.selectbox(
    "🔍 業界で絞り込み", ["すべて"] + INDUSTRY_LIST
)

display_df = df.copy()
if filter_ind != "すべて":
    display_df = display_df[display_df["業界"] == filter_ind]

display_df = display_df.sort_values(by="業界", ascending=True)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "URL": st.column_config.LinkColumn("マイページURL"),
    },
)

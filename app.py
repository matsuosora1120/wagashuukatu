import os
import sys
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# 1. ページ設定
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
# 2. キーボードが出ない Native Select 関数
# ==========================================
def native_select(label, options, key_name, default_value=None):
    """
    Androidのキーボードを絶対に起動させないHTML標準の<select>タグコンポーネント
    """
    st.markdown(f"**{label}**")

    # 初期値の設定
    if default_value in options:
        current_val = default_value
    else:
        current_val = options[0]

    if key_name not in st.session_state:
        st.session_state[key_name] = current_val

    # HTMLの作成 (inputタグが無いためキーボードが起動しない)
    options_html = ""
    for opt in options:
        selected = "selected" if opt == st.session_state[key_name] else ""
        options_html += f'<option value="{opt}" {selected}>{opt}</option>'

    html_code = f"""
    <div style="margin-bottom: 5px;">
        <select id="{key_name}" onchange="sendMessage(this.value)" style="
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border-radius: 8px;
            border: 1px solid #d3d3d3;
            background-color: #ffffff;
            color: #333333;
            outline: none;
            cursor: pointer;
            -webkit-appearance: menulist;
        ">
            {options_html}
        </select>
    </div>
    <script>
    function sendMessage(val) {{
        // Streamlitへ選択された値を送信
        window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: val
        }}, '*');
    }}
    </script>
    """

    # コンポーネント呼び出し（高さをフィットさせる）
    selected_value = components.html(html_code, height=50)

    # ユーザーが選択肢を変更した場合、session_stateを更新
    if selected_value is not None and selected_value != st.session_state[key_name]:
        st.session_state[key_name] = selected_value
        st.rerun()

    return st.session_state[key_name]


# ==========================================
# 3. スプレッドシート接続（Cloud / ローカル自動判定）
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
# 4. ログイン画面
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
# 5. メイン画面（ログイン後）
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
    # 業界順にソートした選択肢の作成
    df_sorted = df.copy()
    industry_order = {ind: idx for idx, ind in enumerate(INDUSTRY_LIST)}
    df_sorted["industry_rank"] = df_sorted["業界"].map(
        lambda x: industry_order.get(x, 999)
    )
    df_sorted = df_sorted.sort_values(
        by=["industry_rank", "企業名"]
    ).reset_index(drop=True)

    options_map = {"【新規登録】": "【新規登録】"}
    for _, r in df_sorted.iterrows():
        label = f"【{r['業界'] if r['業界'] else '未設定'}】 {r['企業名']}"
        options_map[label] = r["企業名"]

    # 1. 企業選択 (native_select)
    company_labels = list(options_map.keys())
    selected_label = native_select(
        "編集する企業を選択（業界別順）",
        company_labels,
        key_name="select_company_native",
    )
    selected_company = options_map.get(selected_label, "【新規登録】")

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

    # コピー用エリア ＆ サイトを開くボタン
    if selected_company != "【新規登録】":
        st.markdown("**📋 コピー用情報 ＆ マイページリンク**")
        cp_col1, cp_col2, cp_col3 = st.columns([2, 2, 1.5])

        if init_my_id:
            cp_col1.caption("▼ ログインID")
            cp_col1.code(init_my_id, language=None)

        if init_password:
            cp_col2.caption("▼ パスワード")
            cp_col2.code(init_password, language=None)

        cp_col3.caption("▼ マイページ")
        if init_url and init_url.startswith("http"):
            cp_col3.link_button(
                "🌐 サイトを開く", init_url, use_container_width=True
            )
        elif init_url:
            cp_col3.link_button(
                "🌐 サイトを開く",
                f"https://{init_url}",
                use_container_width=True,
            )
        else:
            cp_col3.info("URL未登録")

    st.markdown("---")
    
    # HTMLコンポーネント(native_select)の値漏れを防ぐため、form枠は外して直接入力エリアを設置
    col1, col2 = st.columns(2)
    company = col1.text_input("企業名*", value=init_company, key="input_company")

    # 2. 業界選択 (native_select)
    industry = native_select(
        "業界・ジャンル",
        INDUSTRY_LIST,
        key_name="industry_native",
        default_value=init_industry,
    )

    my_id = col1.text_input("ログインID*", value=init_my_id, key="input_my_id")
    password = col2.text_input("パスワード", value=init_password, key="input_password")

    # 3. ステータス選択 (native_select)
    status = native_select(
        "ステータス",
        STATUS_LIST,
        key_name="status_native",
        default_value=init_status,
    )

    url = col2.text_input("マイページURL", value=init_url, key="input_url")
    memo = st.text_input("メモ", value=init_memo, key="input_memo")

    st.write("")
    btn_save = st.button("💾 保存（新規追加 / 上書き）", type="primary")

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
                row_idx = df[df["企業名"] == selected_company].index[0] + 2
                sheet.update(f"A{row_idx}:G{row_idx}", [new_row])
                st.success(f"「{company}」を更新しました！")
            else:
                sheet.append_row(new_row)
                st.success(f"「{company}」を新規登録しました！")
            st.rerun()

    if selected_company != "【新規登録】":
        if st.button("🗑️ 選択中の企業を削除"):
            row_idx = df[df["企業名"] == selected_company].index[0] + 2
            sheet.delete_rows(row_idx)
            st.success(f"「{selected_company}」を削除しました。")
            st.rerun()

st.divider()

# --- 一覧表示・ソート・絞り込み ---
st.subheader("📊 登録企業一覧")

col_f1, col_f2 = st.columns([1, 2])

with col_f1:
    # 4. 業界絞り込み (native_select)
    filter_ind = native_select(
        "🔍 業界で絞り込み",
        ["すべて"] + INDUSTRY_LIST,
        key_name="filter_industry_native",
        default_value="すべて",
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

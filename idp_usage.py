import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta
import json
import os
import re


# 메인 컨텐츠 최대 너비 제한 (우측 영역)
st.markdown(
    """
    <style>
    .main .block-container {
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

USERS_DATA = {
    "01012345678": {
        "password": "tjdwls21",
        "name": "홍길동",
        "email": "gildong.hong@sk.com",
        "role": "user",
        "timestamp": "2025. 10. 2 오후 9:31:36",
        "display": "대상",
    },
    "01064161169": {
        "password": "tjdwls21",
        "name": "박성진",
        "email": "sungjin.park@sk.com",
        "role": "admin",
        "timestamp": "2025. 9. 23 오후 6:08:28",
        "display": "대상",
    },
    "01091238611": {
        "password": "1007",
        "name": "권정미",
        "email": "jungmi.kwon@sk.com",
        "role": "user",
        "timestamp": "2025. 9. 23 오후 6:05:20",
        "display": "대상",
    },
    "01025385744": {
        "password": "scent1223",
        "name": "배주리",
        "email": "cre744@sk.com",
        "role": "user",
        "timestamp": "2025. 9. 23 오후 6:05:20",
        "display": "대상",
    },
    "01062861020": {
        "password": "Tjwldnjs1020!",
        "name": "서지원",
        "email": "jiwon.seo.1020@sk.com",
        "role": "user",
        "timestamp": "2025. 9. 23 오후 6:05:20",
        "display": "대상",
    },
    "01031153665": {
        "password": "090820",
        "name": "황용철",
        "email": "chorin@sk.com",
        "role": "user",
        "timestamp": "2025. 9. 23 오후 6:05:20",
        "display": "대상",
    },
}


SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# IDP 사용 내역 구글시트
# https://docs.google.com/spreadsheets/d/1ufWiqLPPxdmt95jqnJ2sTRy_nmsGASRQnZWmAEmI1C4/edit
IDP_SPREADSHEET_ID = (
    (st.secrets.get("google", {}).get("idp_spreadsheet_id") if hasattr(st, "secrets") else None)
    or "1ufWiqLPPxdmt95jqnJ2sTRy_nmsGASRQnZWmAEmI1C4"
)


def get_google_sheets_client():
    try:
        try:
            google_sec = st.secrets.get("google") if hasattr(st, "secrets") else None
        except Exception:
            google_sec = None

        if google_sec:
            if "credentials_json" in google_sec and google_sec["credentials_json"]:
                raw = google_sec["credentials_json"]
                creds_info = json.loads(raw) if isinstance(raw, str) else dict(raw)
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                return gspread.authorize(creds)
            if "service_account" in google_sec and google_sec["service_account"]:
                creds_info = dict(google_sec["service_account"])  # MappingProxyType 대응
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                return gspread.authorize(creds)

        # Streamlit secrets에서 직접 읽기 (추가 위치 확인)
        try:
            if hasattr(st, "secrets"):
                direct_creds = st.secrets.get("GOOGLE_CREDENTIALS_JSON") or st.secrets.get("google_credentials_json")
                if direct_creds:
                    try:
                        creds_info = json.loads(direct_creds) if isinstance(direct_creds, str) else dict(direct_creds)
                        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                        return gspread.authorize(creds)
                    except json.JSONDecodeError:
                        st.error("Streamlit secrets의 GOOGLE_CREDENTIALS_JSON이 올바른 JSON 형식이 아닙니다.")
                        return None
        except Exception:
            pass

        service_account_file = "service_account.json"
        if os.path.exists(service_account_file):
            creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPE)
            return gspread.authorize(creds)

        if "google_credentials" in st.session_state and st.session_state.google_credentials:
            try:
                creds_info = json.loads(st.session_state.google_credentials)
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                return gspread.authorize(creds)
            except json.JSONDecodeError:
                st.error("저장된 서비스 계정 정보가 올바른 JSON 형식이 아닙니다.")
                return None

        st.warning("Google Sheets 연동을 위해 서비스 계정 인증 정보가 필요합니다.")
        return None
    except (ValueError, KeyError, AttributeError) as e:
        st.error(f"Google Sheets 연동 설정 오류: {e}")
        return None
    except Exception as e:
        st.error(f"Google Sheets 연동 오류: {e}")
        return None


def ensure_session():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    if "google_credentials" not in st.session_state:
        st.session_state.google_credentials = None
    if "show_idp_form" not in st.session_state:
        st.session_state.show_idp_form = False


def login_user(phone: str, password: str):
    if phone in USERS_DATA and USERS_DATA[phone]["password"] == password:
        return USERS_DATA[phone]
    return None


def parse_currency(value: str) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value)
    s = s.replace("₩", "").replace(",", "").strip()
    m = re.search(r"-?\d+", s)
    return int(m.group(0)) if m else 0


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    s = str(value).strip()
    # 지원 포맷: '2025. 9. 22', '2025-09-22', '2025/09/22', 'YYYY. M. D 오후 6:41:57'
    fmts = [
        "%Y. %m. %d",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y. %m. %d %p %I:%M:%S",
        "%Y.%m.%d",
    ]
    for f in fmts:
        try:
            dt = datetime.strptime(s.replace("AM", "오전").replace("PM", "오후"), f)
            return dt
        except Exception:
            pass
    # 구글시트가 날짜를 숫자로 반환하는 경우는 gspread에서 보통 문자열로 포맷됨. 실패시 None
    return None


def fetch_idp_dataframe() -> pd.DataFrame | None:
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        ss = client.open_by_key(IDP_SPREADSHEET_ID)
        ws = ss.sheet1
        records = ws.get_all_records()
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"IDP 시트 로드 오류: {e}")
        return None


def render_login():
    # 비밀번호 필드의 "Show password" 버튼 제거
    st.markdown(
        """
        <style>
        /* 비밀번호 필드의 "Show password" 버튼 완전히 숨김 */
        button[title*="password" i],
        button[title*="Password" i],
        button[aria-label*="password" i],
        button[aria-label*="Password" i],
        input[type="password"] ~ button,
        input[type="password"] + * button,
        div[data-testid="stTextInput"] input[type="password"] ~ button,
        div[data-testid="stTextInput"]:has(input[type="password"]) button {
            display: none !important;
            visibility: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.title("🔐 로그인")
    st.markdown("---")
    with st.form("login_form"):
        phone = st.text_input("휴대폰번호", placeholder="01012345678")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        submitted = st.form_submit_button("로그인", use_container_width=True)
        if submitted:
            if phone and password:
                user = login_user(phone, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.error("휴대폰번호 또는 비밀번호가 올바르지 않습니다.")
            else:
                st.warning("휴대폰번호와 비밀번호를 모두 입력해주세요.")


def render_metric_and_cards(df: pd.DataFrame, user_name: str):
    # 사용자 필터
    if "이름" in df.columns:
        df_user = df[df["이름"] == user_name].copy()
    else:
        df_user = df.copy()

    # 날짜 컬럼 선택: 결제일 우선, 없으면 타임스탬프
    date_col = "결제일" if "결제일" in df_user.columns else ("타임스탬프" if "타임스탬프" in df_user.columns else None)
    if date_col is None:
        st.info("날짜 컬럼을 찾을 수 없습니다. 데이터 구조를 확인해주세요.")
        return

    # 비용 컬럼
    cost_col = "신청비용" if "신청비용" in df_user.columns else None

    # 파싱
    df_user["_parsed_dt"] = df_user[date_col].apply(parse_date)
    if cost_col:
        df_user["_cost"] = df_user[cost_col].apply(parse_currency)
    else:
        df_user["_cost"] = 0

    # 올해 누적 금액 (서울 시간 기준)
    kst = timezone(timedelta(hours=9))
    current_year = datetime.now(kst).year
    df_this_year = df_user[df_user["_parsed_dt"].apply(lambda x: x.year == current_year if isinstance(x, datetime) else False)]
    total_cost = int(df_this_year["_cost"].sum()) if not df_this_year.empty else 0

    # 상단 메트릭
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.metric("올해 IDP 누적 사용금액", f"₩{total_cost:,.0f}")

    st.markdown("---")

    if df_user.empty:
        st.info("해당 사용자의 IDP 사용 내역이 없습니다.")
        return

    # 최신순 정렬
    df_user = df_user.sort_values(by="_parsed_dt", ascending=False)

    # 한 줄 요약 + 클릭 시 상세(Expander) 렌더링
    for _, row in df_user.iterrows():
        dt = row.get("_parsed_dt")
        date_str = dt.strftime("%Y-%m-%d") if isinstance(dt, datetime) else str(row.get(date_col, "-"))
        title = str(row.get("신청명", "-"))
        cost_val = int(row.get("_cost", 0) or 0)

        summary_label = f"{date_str} · {title} · ₩{cost_val:,.0f}"
        with st.expander(summary_label):
            type_str = str(row.get("유형", ""))
            org = str(row.get("주관기관", ""))
            detail = str(row.get("세부내용", ""))
            purpose = str(row.get("신청목적", ""))
            start = str(row.get("과정시작일", ""))
            end = str(row.get("과정종료일", ""))
            hours = str(row.get("총교육시간", ""))
            url = str(row.get("안내사이트URL", "")).strip()

            col1, col2 = st.columns([2, 1])
            with col1:
                if type_str or org:
                    st.markdown(f"**유형/기관**: {type_str}{' · ' if type_str and org else ''}{org}")
                if purpose:
                    st.markdown(f"**신청목적**: {purpose}")
                if detail:
                    st.markdown(f"**세부내용**: {detail}")
            with col2:
                if start or end:
                    st.markdown(f"**기간**: {start or '-'} ~ {end or '-'}")
                if hours:
                    st.markdown(f"**총교육시간**: {hours}h")
                st.markdown(f"**금액**: ₩{cost_val:,.0f}")

            if url and url.lower().startswith(("http://", "https://")):
                st.markdown(f"[안내사이트 바로가기]({url})")


def _is_retryable_error(error_msg: str) -> bool:
    """재시도 가능한 오류인지 확인합니다."""
    msg_lower = error_msg.lower()
    return ('429' in msg_lower) or ('quota' in msg_lower) or ('rate' in msg_lower and 'limit' in msg_lower)

def _sheets_call_with_retry(callable_fn, *args, **kwargs):
    """Google Sheets API 호출을 지수 백오프로 재시도합니다."""
    import time
    import random
    delays = [0, 1, 2, 4, 8, 16]
    last_error = None
    for delay in delays:
        if delay > 0:
            time.sleep(delay + random.uniform(0, 0.5))
        try:
            return callable_fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            error_msg = str(e)
            if _is_retryable_error(error_msg):
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Google Sheets API 호출이 실패했습니다.")

def save_idp_to_google_sheets(data):
    """IDP 데이터를 Google Sheets에 저장합니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        def _append_row():
            spreadsheet = client.open_by_key(IDP_SPREADSHEET_ID)
            worksheet = spreadsheet.sheet1
            worksheet.append_row(data)
            return True
        
        return _sheets_call_with_retry(_append_row)
    except Exception as e:
        error_msg = str(e).lower()
        if _is_retryable_error(error_msg):
            st.warning("IDP 저장 중 호출 제한이 발생했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.error(f"Google Sheets 저장 오류: {e}")
        return False


def render_idp_registration_form(user_name: str):
    """IDP 신규 등록 양식을 렌더링합니다."""
    st.markdown("### 📝 IDP 신규 등록")
    st.markdown("**<span style='color: #d32f2f; font-weight: 600;'>* 필수 항목</span>**", unsafe_allow_html=True)
    st.markdown("---")
    
    with st.form("idp_registration_form"):
        # 이름 (자동 입력, 변경 불가)
        st.text_input("이름", value=user_name, disabled=True, help="로그인된 사용자 이름 (변경 불가)")
        
        # 필수 필드 - 빨간색으로 강조
        st.markdown("**<span style='color: #d32f2f;'>*</span> 신청명**", unsafe_allow_html=True)
        신청명 = st.text_input("신청명", key="idp_신청명", label_visibility="collapsed", help="필수 항목")
        신청명 = 신청명 if isinstance(신청명, str) else ""
        
        st.markdown("**<span style='color: #d32f2f;'>*</span> 유형**", unsafe_allow_html=True)
        유형_옵션 = [
            "교육/포럼/컨퍼런스 참가",
            "자격 응시 및 취득",
            "AI Tool 구독",
            "직무 관련 도서 구매",
            "기타"
        ]
        유형 = st.selectbox("유형", 유형_옵션, key="idp_유형", label_visibility="collapsed", help="필수 항목")
        
        st.markdown("**<span style='color: #d32f2f;'>*</span> 세부내용**", unsafe_allow_html=True)
        세부내용 = st.text_area("세부내용", key="idp_세부내용", label_visibility="collapsed", help="필수 항목", height=100)
        세부내용 = 세부내용 if isinstance(세부내용, str) else ""
        
        st.markdown("**<span style='color: #d32f2f;'>*</span> 신청목적**", unsafe_allow_html=True)
        신청목적 = st.text_input("신청목적", key="idp_신청목적", label_visibility="collapsed", help="필수 항목")
        신청목적 = 신청목적 if isinstance(신청목적, str) else ""
        
        st.markdown("**<span style='color: #d32f2f;'>*</span> 신청비용**", unsafe_allow_html=True)
        신청비용 = st.text_input("신청비용", key="idp_신청비용", label_visibility="collapsed", placeholder="예: ₩500,000 또는 500000", help="필수 항목")
        신청비용 = 신청비용 if isinstance(신청비용, str) else ""
        
        st.markdown("**<span style='color: #d32f2f;'>*</span> 결제일**", unsafe_allow_html=True)
        결제일 = st.date_input("결제일", key="idp_결제일", label_visibility="collapsed", help="필수 항목")
        
        # 선택 필드
        주관기관 = st.text_input("주관기관", key="idp_주관기관", help="선택 항목")
        
        안내사이트URL = st.text_input("안내사이트URL", key="idp_안내사이트URL", help="선택 항목")
        
        과정시작일 = st.date_input("과정시작일", key="idp_과정시작일", value=None, help="선택 항목")
        
        과정종료일 = st.date_input("과정종료일", key="idp_과정종료일", value=None, help="선택 항목")
        
        총교육시간 = st.number_input("총교육시간", key="idp_총교육시간", min_value=0, value=0, step=1, help="선택 항목")
        
        # 저장 중 상태 확인
        is_saving = st.session_state.get("idp_saving", False)
        
        submitted = st.form_submit_button(
            "등록하기" if not is_saving else "등록 중...",
            type="primary",
            use_container_width=True,
            disabled=is_saving
        )
        
        if submitted:
            # 중복 클릭 방지 - 이미 저장 중이면 바로 리턴
            if is_saving:
                st.warning("이미 등록 중입니다. 잠시만 기다려주세요.")
                st.stop()
            
            # 필수 필드 검증
            if not 신청명.strip():
                st.error("신청명을 입력해주세요.")
                st.session_state.idp_saving = False
                return
            if not 세부내용.strip():
                st.error("세부내용을 입력해주세요.")
                st.session_state.idp_saving = False
                return
            if not 신청목적.strip():
                st.error("신청목적을 입력해주세요.")
                st.session_state.idp_saving = False
                return
            if not 신청비용.strip():
                st.error("신청비용을 입력해주세요.")
                st.session_state.idp_saving = False
                return
            
            # 저장 시작
            st.session_state.idp_saving = True
            
            # 타임스탬프 생성 (서울 시간 기준)
            kst = timezone(timedelta(hours=9))
            now = datetime.now(kst)
            timestamp = now.strftime("%Y. %m. %d %p %I:%M:%S").replace("AM", "오전").replace("PM", "오후")
            
            # 결제일 포맷팅
            결제일_str = 결제일.strftime("%Y. %m. %d") if 결제일 else ""
            
            # 과정시작일/종료일 포맷팅
            과정시작일_str = 과정시작일.strftime("%Y. %m. %d") if 과정시작일 else ""
            과정종료일_str = 과정종료일.strftime("%Y. %m. %d") if 과정종료일 else ""
            
            # 데이터 준비 (시트 컬럼 순서에 맞춤)
            data = [
                timestamp,           # 타임스탬프
                user_name,           # 이름
                신청명.strip(),       # 신청명
                유형,                 # 유형
                세부내용.strip(),     # 세부내용
                신청목적.strip(),     # 신청목적
                신청비용.strip(),     # 신청비용
                결제일_str,          # 결제일
                주관기관.strip() if 주관기관 else "",  # 주관기관
                과정시작일_str,       # 과정시작일
                과정종료일_str,       # 과정종료일
                str(총교육시간) if 총교육시간 > 0 else "",  # 총교육시간
                안내사이트URL.strip() if 안내사이트URL else ""  # 안내사이트URL
            ]
            
            # Google Sheets에 저장
            try:
                if save_idp_to_google_sheets(data):
                    # 저장 성공 시 IDP 캐시 갱신
                    try:
                        user_name_val = user_name if user_name else (st.session_state.user_info.get('name') if st.session_state.get('user_info') else None)
                        if user_name_val:
                            # prefetch_cache 초기화
                            if 'prefetch_cache' not in st.session_state:
                                st.session_state.prefetch_cache = {}
                            
                            # 최신 IDP 데이터 가져오기
                            idp_df = fetch_idp_dataframe()
                            if idp_df is not None and not idp_df.empty:
                                # 사용자 데이터만 필터링
                                if '이름' in idp_df.columns:
                                    user_idp = idp_df[idp_df['이름'] == user_name_val]
                                    st.session_state.prefetch_cache['idp'] = user_idp.to_dict('records') if not user_idp.empty else []
                                else:
                                    st.session_state.prefetch_cache['idp'] = idp_df.to_dict('records')
                            else:
                                st.session_state.prefetch_cache['idp'] = []
                            
                            # 캐시 파일에 저장 (main.py의 touch_session_active 함수 사용 시도)
                            try:
                                if hasattr(st.session_state, 'last_active'):
                                    # main.py의 구조를 참고하여 캐시 갱신
                                    CACHE_FILE = "user_cache.json"
                                    if st.session_state.get('logged_in'):
                                        cache_data = {
                                            'logged_in': True,
                                            'user_phone': st.session_state.get('user_phone'),
                                            'user_info': st.session_state.get('user_info'),
                                            'last_active': st.session_state.get('last_active'),
                                            'idle_timeout_minutes': st.session_state.get('idle_timeout_minutes', 30),
                                        }
                                        if 'prefetch_cache' in st.session_state:
                                            cache_data['prefetch_data'] = st.session_state.prefetch_cache
                                            kst = timezone(timedelta(hours=9))
                                            cache_data['prefetch_timestamp'] = datetime.now(kst).isoformat()
                                        try:
                                            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                                                json.dump(cache_data, f, ensure_ascii=False)
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                    except Exception:
                        # 캐시 갱신 실패해도 저장은 계속 진행
                        pass
                    
                    st.session_state.show_idp_form = False
                    st.session_state.idp_saving = False
                    st.success("✅ IDP 신규 등록이 완료되었습니다!")
                    st.rerun()
                else:
                    st.error("❌ 저장 중 오류가 발생했습니다. 다시 시도해주세요.")
                    st.session_state.idp_saving = False
            except Exception as e:
                st.error(f"❌ 저장 중 오류가 발생했습니다: {e}")
                st.session_state.idp_saving = False


def get_current_viewing_user():
    """현재 조회 중인 사용자 정보를 반환합니다.
    관리자가 다른 사용자를 선택한 경우 viewing_user_info를 반환하고,
    그렇지 않으면 현재 로그인한 user_info를 반환합니다.
    """
    if 'viewing_user_info' in st.session_state:
        return st.session_state.viewing_user_info
    return st.session_state.user_info

def render_idp_usage_embedded():
    """메인 앱(main.py)에서 임베드 호출용 렌더러 (page_config/로그인 UI 없음)."""
    if not st.session_state.get("logged_in"):
        st.info("로그인 후 이용해주세요.")
        return
    user = get_current_viewing_user() or {}
    user_name = user.get("name", "")
    
    # 양식 표시 여부 확인
    if st.session_state.get("show_idp_form", False):
        # 취소 버튼
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.show_idp_form = False
            st.rerun()
        # 양식만 표시 (사용 내역은 숨김)
        render_idp_registration_form(user_name)
        return  # 양식이 열려있으면 여기서 종료하여 사용 내역을 표시하지 않음
    
    # 양식이 닫혀있을 때만 사용 내역 표시
    st.subheader(f"{user_name} 님의 IDP")
    with st.spinner("구글시트에서 데이터를 불러오는 중..."):
        df = fetch_idp_dataframe()
    if df is None:
        st.error("데이터를 불러오지 못했습니다. Google 인증 정보를 확인해주세요.")
        return
    if df.empty:
        st.info("시트에 데이터가 없습니다.")
        return
    render_metric_and_cards(df, user_name)
    
    # IDP 신규 등록 버튼 (하단에 위치)
    st.markdown("---")
    if st.button("➕ IDP 신규 등록", type="primary", use_container_width=True):
        st.session_state.show_idp_form = True
        st.rerun()


def main():
    # 단독 실행 시에만 페이지 설정
    try:
        st.set_page_config(page_title="IDP 사용 내역", page_icon="🎯", layout="wide")
    except Exception:
        # 이미 설정되었을 수 있음
        pass
    ensure_session()

    if not st.session_state.logged_in:
        render_login()
        return

    user = st.session_state.user_info
    st.title("🎯 IDP 사용 내역")
    st.caption("로그인한 사용자의 IDP 사용 내역을 날짜별 카드로 보여줍니다.")

    with st.sidebar:
        st.success(f"안녕하세요, {user['name']}님!")
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.rerun()

    with st.spinner("구글시트에서 데이터를 불러오는 중..."):
        df = fetch_idp_dataframe()

    if df is None:
        st.error("데이터를 불러오지 못했습니다. Google 인증 정보를 확인해주세요.")
        return

    if df.empty:
        st.info("시트에 데이터가 없습니다.")
        return

    render_metric_and_cards(df, user.get("name", ""))


if __name__ == "__main__":
    main()



import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import time
import random
import json
import os
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="Daily Snippets",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 메인 컨테이너 최대 너비 제한 및 중앙 정렬 CSS (강제 적용)
st.markdown(
    """
    <style>
    /* 사이드바 폭 설정 */
    [data-testid="stSidebar"] {
        min-width: 250px !important;
        max-width: 250px !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        width: 250px !important;
    }
    
    /* 사이드바 제목 폰트 사이즈 줄이기 (줄바꿈 방지) */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] .element-container h1,
    [data-testid="stSidebar"] [class*="stTitle"] h1,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        font-size: 1.2rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    
    /* Streamlit 메인 뷰 컨테이너를 직접 타겟팅 */
    [data-testid="stAppViewContainer"] > .main, 
    [data-testid="stAppViewContainer"] .main, 
    .block-container {
        max-width: 900px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* 넓은 화면에서도 동일하게 유지 */
    @media (min-width: 1920px) {
        [data-testid="stAppViewContainer"] > .main, 
        [data-testid="stAppViewContainer"] .main, 
        .block-container {
            max-width: 900px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 사용자 데이터는 더 이상 코드에 하드코딩하지 않습니다. 구글시트에서 조회합니다.

# Google Sheets 연동을 위한 설정
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 스프레드시트 ID (secrets 우선)
SPREADSHEET_ID = (
    (st.secrets.get("google", {}).get("spreadsheet_id") if hasattr(st, "secrets") else None)
    or "1THmwStR6p0_SUyLEV6-edT0kigANvTCPOkAzN7NaEQE"
)

# 사용자 정보 시트 ID (secrets 우선) - 기본값은 제공된 시트 사용
USERS_SPREADSHEET_ID = (
    (st.secrets.get("google", {}).get("users_spreadsheet_id") if hasattr(st, "secrets") else None)
    or "1fHSCgg6_97Z3JzOvrk3ElXQWhOWhVhl5IaITeA9pXmY"
)

# 캐시 파일 설정
CACHE_FILE = "user_cache.json"

def _is_retryable_error(error_msg: str) -> bool:
    """재시도 가능한 오류인지 확인합니다."""
    msg_lower = error_msg.lower()
    return ('429' in msg_lower) or ('quota' in msg_lower) or ('rate' in msg_lower and 'limit' in msg_lower)

def _sheets_call_with_retry(callable_fn, *args, **kwargs):
    """Google Sheets API 호출을 지수 백오프로 재시도합니다."""
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

def get_google_sheets_client():
    """Google Sheets 클라이언트를 반환합니다."""
    try:
        # 방법 0: Streamlit secrets에서 서비스 계정 정보 읽기 (최우선)
        try:
            google_sec = st.secrets.get("google") if hasattr(st, "secrets") else None
        except Exception:
            google_sec = None

        if google_sec:
            # 0-a) 전체 JSON 문자열 저장한 경우: google.credentials_json
            if "credentials_json" in google_sec and google_sec["credentials_json"]:
                raw = google_sec["credentials_json"]
                creds_info = json.loads(raw) if isinstance(raw, str) else dict(raw)
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                return gspread.authorize(creds)

            # 0-b) TOML로 키를 중첩(dict) 저장한 경우: google.service_account = { ... }
            if "service_account" in google_sec and google_sec["service_account"]:
                creds_info = dict(google_sec["service_account"])  # MappingProxyType 대응
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                return gspread.authorize(creds)

        # 방법 1: Streamlit secrets에서 직접 읽기 (추가 위치 확인)
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
        
        # 방법 2: 서비스 계정 JSON 파일 읽기
        service_account_file = "service_account.json"
        if os.path.exists(service_account_file):
            creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPE)
            return gspread.authorize(creds)
        
        # 방법 3: 세션 상태에서 서비스 계정 정보 읽기
        if 'google_credentials' in st.session_state and st.session_state.google_credentials:
            try:
                creds_info = json.loads(st.session_state.google_credentials)
                creds = Credentials.from_service_account_info(creds_info, scopes=SCOPE)
                return gspread.authorize(creds)
            except json.JSONDecodeError:
                st.error("저장된 서비스 계정 정보가 올바른 JSON 형식이 아닙니다.")
                return None
        
        # 인증 정보가 없는 경우
        st.warning("Google Sheets 연동을 위해 서비스 계정 인증 정보가 필요합니다.")
        return None
        
    except Exception as e:
        st.error(f"Google Sheets 연동 오류: {e}")
        return None

def save_to_google_sheets(data):
    """데이터를 Google Sheets에 저장합니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        # 재시도 로직 적용
        def _append_row():
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.sheet1
            worksheet.append_row(data)
            return True
        
        return _sheets_call_with_retry(_append_row)
    except Exception as e:
        error_msg = str(e).lower()
        if _is_retryable_error(error_msg):
            st.warning("Google Sheets 저장 중 호출 제한이 발생했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.error(f"Google Sheets 저장 오류: {e}")
        return False

def save_data_with_fallback(data):
    """데이터를 저장합니다. Google Sheets 실패 시 로컬 CSV로 저장."""
    # Google Sheets에 저장 시도
    if st.session_state.google_sheets_connected:
        if save_to_google_sheets(data):
            # 저장 성공 시 아카이브 캐시 갱신
            refresh_archive_cache()
            return True
    
    # Google Sheets 실패 시 로컬 CSV로 저장
    st.warning("Google Sheets 저장에 실패했습니다. 로컬 CSV 파일로 저장합니다.")
    result = save_to_local_csv(data)
    if result:
        # 로컬 CSV 저장 성공 시에도 아카이브 캐시 갱신
        refresh_archive_cache()
    return result

def fetch_users_records():
    """사용자 정보 시트의 모든 레코드를 반환합니다. (캐시 사용)"""
    try:
        return _users_records_cached(USERS_SPREADSHEET_ID)
    except Exception as e:
        st.error(f"사용자 데이터 로드 오류: {e}")
        return []

# 앱 레벨 캐시: 사용자 시트 전체 레코드 (다중 세션 공유)
@st.cache_data(ttl=300, show_spinner=False)
def _users_records_cached(spreadsheet_id: str):
    client = get_google_sheets_client()
    if not client:
        return []
    
    def _fetch_records():
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.sheet1
        records = worksheet.get_all_records()
        return records or []
    
    try:
        return _sheets_call_with_retry(_fetch_records)
    except Exception as e:
        # 재시도 실패 시 빈 리스트 반환 (에러 메시지는 상위에서 처리)
        return []

def _digits_only(value: str | int | None) -> str:
    s = str(value or "")
    return "".join(ch for ch in s if ch.isdigit())

def _phones_equal(a: str | None, b: str | None) -> bool:
    da = _digits_only(a).lstrip('0')
    db = _digits_only(b).lstrip('0')
    return bool(da and db and da == db)

def _choose_display_phone(login_phone: str | None, sheet_phone: str | None) -> str:
    # 표시 우선순위: 로그인 입력값(0 보존) > 시트값 > 기타
    if login_phone:
        lp = str(login_phone)
        if lp.startswith('0'):
            return lp
    if sheet_phone:
        sp = str(sheet_phone)
        if sp.startswith('0'):
            return sp
    return str(login_phone or sheet_phone or 'N/A')

def find_user_by_phone_and_password(phone: str, password: str):
    """휴대폰번호와 비밀번호로 사용자를 찾습니다."""
    records = fetch_users_records()
    for row in records:
        row_phone = str(row.get('휴대폰번호', '')).strip()
        row_pw = str(row.get('비밀번호', '')).strip()
        if _phones_equal(row_phone, phone) and row_pw == str(password).strip():
            # 통일된 키로 변환
            return {
                'phone': str(row.get('휴대폰번호', '')).strip(),
                'password': str(row.get('비밀번호', '')).strip(),
                'name': str(row.get('이름(본명)', '')).strip(),
                'email': str(row.get('회사메일', '')).strip(),
                'role': str(row.get('권한', 'user')).strip() or 'user',
                'timestamp': str(row.get('타임스탬프', '')).strip(),
                'display': str(row.get('표시여부', '')).strip(),
            }
    return None

def get_user_info_by_phone(phone: str):
    records = fetch_users_records()
    for row in records:
        if _phones_equal(str(row.get('휴대폰번호', '')).strip(), phone):
            return {
                'phone': str(row.get('휴대폰번호', '')).strip(),
                'password': str(row.get('비밀번호', '')).strip(),
                'name': str(row.get('이름(본명)', '')).strip(),
                'email': str(row.get('회사메일', '')).strip(),
                'role': str(row.get('권한', 'user')).strip() or 'user',
                'timestamp': str(row.get('타임스탬프', '')).strip(),
                'display': str(row.get('표시여부', '')).strip(),
            }
    return None

def update_user_in_sheet(phone: str, new_email: str | None = None, new_password: str | None = None) -> bool:
    """구글시트에서 해당 휴대폰번호 행을 찾아 이메일/비밀번호를 업데이트합니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        def _update_user():
            spreadsheet = client.open_by_key(USERS_SPREADSHEET_ID)
            worksheet = spreadsheet.sheet1
            # 헤더와 행 전체를 가져와 인덱스 탐색
            all_values = worksheet.get_all_values()
            if not all_values:
                return False
            header = all_values[0]
            phone_col = header.index('휴대폰번호') + 1 if '휴대폰번호' in header else None
            email_col = header.index('회사메일') + 1 if '회사메일' in header else None
            pw_col = header.index('비밀번호') + 1 if '비밀번호' in header else None
            if not phone_col:
                return False
            target_row = None
            for i in range(2, len(all_values) + 1):
                if worksheet.cell(i, phone_col).value == str(phone):
                    target_row = i
                    break
            if not target_row:
                return False
            updates = []
            if new_email is not None and email_col:
                updates.append({'range': f"R{target_row}C{email_col}", 'values': [[new_email]]})
            if new_password is not None and pw_col:
                updates.append({'range': f"R{target_row}C{pw_col}", 'values': [[new_password]]})
            if not updates:
                return True
            worksheet.batch_update([{
                'range': u['range'],
                'values': u['values']
            } for u in updates])
            return True
        
        return _sheets_call_with_retry(_update_user)
    except Exception as e:
        error_msg = str(e).lower()
        if _is_retryable_error(error_msg):
            st.warning("사용자 정보 업데이트 중 호출 제한이 발생했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.error(f"사용자 정보 업데이트 오류: {e}")
        return False

def get_user_phone_from_google_sheet(email: str | None = None, name: str | None = None):
    """사용자 정보 시트에서 휴대폰번호를 조회합니다. 이메일 우선 매칭, 없으면 이름 매칭.

    시트 컬럼 헤더 예시:
    - 휴대폰번호, 비밀번호, 이름(본명), 회사메일, 권한, 타임스탬프, 표시여부
    """
    try:
        # 캐시된 사용자 목록 사용
        records = _users_records_cached(USERS_SPREADSHEET_ID)
        # 이메일로 우선 매칭
        if email:
            for row in records:
                if str(row.get('회사메일', '')).strip() == str(email).strip():
                    return str(row.get('휴대폰번호', '')).strip() or None
        # 이름으로 보조 매칭
        if name:
            for row in records:
                if str(row.get('이름(본명)', '')).strip() == str(name).strip():
                    return str(row.get('휴대폰번호', '')).strip() or None
        return None
    except Exception as e:
        st.warning(f"사용자 시트 조회 실패: {e}")
        return None

def login_user(phone, password):
    """사용자 로그인 검증: 구글시트에서 사용자 확인"""
    return find_user_by_phone_and_password(phone, password)

def has_unsaved_inputs() -> bool:
    """현재 페이지에 저장되지 않은 입력 정보가 있는지 확인합니다."""
    current_page = st.session_state.get("current_page", "main")
    
    # IDP 페이지: 등록 양식이 열려있거나 입력 중인 경우
    if current_page == "idp":
        if st.session_state.get("show_idp_form", False):
            return True
    
    # CDP 페이지: 수정 모드인 경우
    if current_page == "cdp":
        if st.session_state.get("cdp_edit_mode", False):
            return True
    
    # Profile Edit 페이지: 저장 중인 경우는 제외 (이미 처리 중)
    # 입력 필드가 변경된 경우는 경고 필요 없음 (저장 버튼이 있으므로)
    
    return False

def reset_page_state(target_page: str):
    """특정 페이지의 상태를 초기화합니다."""
    if target_page == "daily_snippet":
        st.session_state.current_step = 1
        st.session_state.form_data = {
            'name': '',
            'physical_state': 0,
            'mental_state': 0,
            'state_reason': '',
            'improvement_plan': '',
            'yesterday_work': '',
            'yesterday_satisfaction': 0,
            'liked': '',
            'lacked': '',
            'learned': '',
            'looked_forward': '',
            'longed_for': '',
            'colleague_praise': '',
            'today_plans': ''
        }
        st.session_state.saving_snippet = False
    
    elif target_page == "idp":
        st.session_state.show_idp_form = False
        st.session_state.idp_saving = False
    
    elif target_page == "cdp":
        st.session_state.cdp_edit_mode = False
        st.session_state.cdp_saving = False
    
    elif target_page == "profile_edit":
        # profile_edit 페이지의 모든 상태 초기화 (페이지 진입 시 또는 나갈 때)
        st.session_state.is_saving_profile = False
        # 입력 필드 상태 초기화
        if st.session_state.logged_in and st.session_state.user_info:
            user = st.session_state.user_info
            st.session_state.profile_edit_new_email = user.get('email', '')
        else:
            st.session_state.profile_edit_new_email = ''
        # 모든 비밀번호 필드 값 초기화
        st.session_state.profile_edit_new_password = ''
        st.session_state.profile_edit_confirm_password = ''
        st.session_state.profile_edit_current_password = ''
        # 성공 메시지 플래그도 초기화
        if 'profile_update_success' in st.session_state:
            st.session_state.profile_update_success = False
        # 입력 필드 위젯 키 초기화 (필드값이 삭제되도록)
        if 'profile_edit_email_input' in st.session_state:
            del st.session_state.profile_edit_email_input
        if 'profile_edit_password_input' in st.session_state:
            del st.session_state.profile_edit_password_input
        if 'profile_edit_confirm_input' in st.session_state:
            del st.session_state.profile_edit_confirm_input
        if 'profile_edit_current_input' in st.session_state:
            del st.session_state.profile_edit_current_input

def navigate_to_page(target_page: str, force: bool = False):
    """페이지 이동 시 입력 정보 확인 및 초기화를 처리합니다."""
    # 강제 이동이 아닌 경우에만 확인
    if not force:
        # 현재 페이지와 동일하면 리셋만 수행
        if st.session_state.get("current_page") == target_page:
            reset_page_state(target_page)
            st.session_state.last_page = target_page
            # 페이지 이동 시 스크롤 초기화
            st.session_state.scroll_to_top = True
            st.rerun()
            return
        
        # 입력 정보가 있는지 확인
        if has_unsaved_inputs():
            # 경고 상태 설정 (메인 콘텐츠 영역에서 표시하도록)
            st.session_state["pending_navigation"] = target_page
            st.session_state["show_navigation_warning"] = True
            st.rerun()
            return
    
    # 경고 없이 바로 이동
    # 모든 경고 상태 정리
    if "pending_navigation" in st.session_state:
        del st.session_state["pending_navigation"]
    if "show_navigation_warning" in st.session_state:
        del st.session_state["show_navigation_warning"]
    
    # 현재 페이지 상태 초기화
    reset_page_state(st.session_state.get("current_page"))
    
    # 페이지 이동
    st.session_state.current_page = target_page
    st.session_state.last_page = target_page
    
    # 타겟 페이지 상태 초기화
    reset_page_state(target_page)
    
    # 페이지 이동 시 스크롤 초기화
    st.session_state.scroll_to_top = True
    
    st.rerun()

def render_navigation_warning():
    """페이지 이동 경고를 메인 콘텐츠 영역에 표시합니다."""
    if st.session_state.get("show_navigation_warning") and st.session_state.get("pending_navigation"):
        target_page = st.session_state["pending_navigation"]
        
        # 경고 메시지 표시
        st.warning("⚠️ 입력 중인 정보가 있습니다. 페이지를 이동하면 모든 입력 정보가 초기화됩니다.")
        
        # 확인 버튼
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 이동하기 (정보 초기화)", use_container_width=True, type="primary", key="confirm_nav_main"):
                # 이동 확인
                if "pending_navigation" in st.session_state:
                    target = st.session_state["pending_navigation"]
                    del st.session_state["pending_navigation"]
                else:
                    target = target_page
                
                if "show_navigation_warning" in st.session_state:
                    del st.session_state["show_navigation_warning"]
                
                # 현재 페이지 상태 초기화
                reset_page_state(st.session_state.get("current_page"))
                
                # 페이지 이동
                st.session_state.current_page = target
                st.session_state.last_page = target
                
                # 타겟 페이지 상태 초기화
                reset_page_state(target)
                
                # 페이지 이동 시 스크롤 초기화
                st.session_state.scroll_to_top = True
                
                st.rerun()
        with col2:
            if st.button("❌ 취소", use_container_width=True, key="cancel_nav_main"):
                # 취소
                if "pending_navigation" in st.session_state:
                    del st.session_state["pending_navigation"]
                if "show_navigation_warning" in st.session_state:
                    del st.session_state["show_navigation_warning"]
                st.rerun()
        
        # 경고 표시 중에는 다른 콘텐츠를 표시하지 않음
        st.stop()

def initialize_session_state():
    """세션 상태를 초기화합니다."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'user_phone' not in st.session_state:
        st.session_state.user_phone = None
    if 'last_active' not in st.session_state:
        st.session_state.last_active = None
    if 'idle_timeout_minutes' not in st.session_state:
        st.session_state.idle_timeout_minutes = 30
    if 'last_page' not in st.session_state:
        st.session_state.last_page = None
    if 'is_saving_profile' not in st.session_state:
        st.session_state.is_saving_profile = False
    if 'logging_in' not in st.session_state:
        st.session_state.logging_in = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "daily_snippet"
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'google_credentials' not in st.session_state:
        st.session_state.google_credentials = None
    if 'google_sheets_connected' not in st.session_state:
        st.session_state.google_sheets_connected = False
    if 'scroll_to_top' not in st.session_state:
        st.session_state.scroll_to_top = False
    if 'prefetch_cache' not in st.session_state:
        st.session_state.prefetch_cache = None
    if 'prefetch_trigger' not in st.session_state:
        st.session_state.prefetch_trigger = False
    if 'prefetch_pending' not in st.session_state:
        st.session_state.prefetch_pending = False
    
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {
            'name': '',
            'physical_state': 0,
            'mental_state': 0,
            'state_reason': '',
            'improvement_plan': '',
            'yesterday_work': '',
            'yesterday_satisfaction': 0,
            'liked': '',
            'lacked': '',
            'learned': '',
            'looked_forward': '',
            'longed_for': '',
            'colleague_praise': '',
            'today_plans': ''
        }

def _has_google_secrets() -> bool:
    """Streamlit secrets에 Google 설정이 있는지 확인합니다."""
    try:
        if not hasattr(st, "secrets"):
            return False
        google_sec = st.secrets.get("google", {})
        return bool(google_sec and (google_sec.get("service_account") or google_sec.get("credentials_json")))
    except Exception:
        return False

def ensure_google_sheets_connection():
    """secrets가 있으면 앱 시작 시 연결을 미리 점검합니다."""
    if st.session_state.google_sheets_connected:
        return
    if not _has_google_secrets():
        return
    client = get_google_sheets_client()
    if not client:
        st.session_state.google_sheets_connected = False
        return
    
    def _test_connection():
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        _ = spreadsheet.sheet1
        return True
    
    try:
        _sheets_call_with_retry(_test_connection)
        st.session_state.google_sheets_connected = True
    except Exception:
        st.session_state.google_sheets_connected = False

def _load_cache():
    """캐시 파일에서 사용자 세션을 로드합니다."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception:
        return None

def _save_cache(data: dict):
    """현재 사용자 세션을 캐시 파일에 저장합니다."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        st.warning(f"캐시 저장 실패: {e}")

def _clear_cache():
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
    except Exception as e:
        st.warning(f"캐시 삭제 실패: {e}")

def _now_iso():
    """서울 시간(KST, UTC+9) 기준으로 현재 시간을 ISO 형식으로 반환합니다."""
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).isoformat()

def _is_idle_expired(last_active_iso: str | None, timeout_minutes: int) -> bool:
    """서울 시간(KST, UTC+9) 기준으로 유휴 시간이 초과되었는지 확인합니다."""
    if not last_active_iso:
        return False
    try:
        kst = timezone(timedelta(hours=9))
        last = datetime.fromisoformat(last_active_iso)
        # last_active_iso가 timezone 정보가 없으면 KST로 간주
        if last.tzinfo is None:
            last = last.replace(tzinfo=kst)
        return datetime.now(kst) - last > timedelta(minutes=timeout_minutes)
    except Exception:
        return False

def try_restore_session_from_cache():
    """앱 시작 시 캐시에서 로그인 상태를 복구합니다 (유휴 초과 시 파기)."""
    cached = _load_cache()
    if not cached:
        return
    if _is_idle_expired(cached.get('last_active'), cached.get('idle_timeout_minutes', 30)):
        _clear_cache()
        return
    st.session_state.logged_in = bool(cached.get('logged_in'))
    st.session_state.user_phone = cached.get('user_phone')
    st.session_state.user_info = cached.get('user_info')
    st.session_state.last_active = cached.get('last_active')
    st.session_state.idle_timeout_minutes = cached.get('idle_timeout_minutes', 30)
    
    # Pre-fetching 데이터 복구
    if cached.get('prefetch_data'):
        st.session_state.prefetch_cache = cached.get('prefetch_data')

def get_current_viewing_user():
    """현재 조회 중인 사용자 정보를 반환합니다.
    관리자가 다른 사용자를 선택한 경우 viewing_user_info를 반환하고,
    그렇지 않으면 현재 로그인한 user_info를 반환합니다.
    """
    if 'viewing_user_info' in st.session_state:
        return st.session_state.viewing_user_info
    return st.session_state.user_info

def touch_session_active():
    """마지막 활동 시간을 갱신하고 캐시에 즉시 반영합니다."""
    st.session_state.last_active = _now_iso()
    if st.session_state.logged_in:
        cache_data = {
            'logged_in': True,
            'user_phone': st.session_state.user_phone,
            'user_info': st.session_state.user_info,
            'last_active': st.session_state.last_active,
            'idle_timeout_minutes': st.session_state.idle_timeout_minutes,
        }
        # Pre-fetching 데이터가 있으면 함께 저장
        if 'prefetch_cache' in st.session_state:
            cache_data['prefetch_data'] = st.session_state.prefetch_cache
            cache_data['prefetch_timestamp'] = _now_iso()
        _save_cache(cache_data)

def logout_and_clear_cache():
    """로그아웃 시 모든 캐시와 세션 상태를 초기화합니다."""
    # 로그인 관련 상태 초기화
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.user_phone = None
    st.session_state.last_active = None
    
    # 관리자 사용자 선택 관련 상태 초기화
    if 'viewing_user_info' in st.session_state:
        del st.session_state.viewing_user_info
    if 'selected_user_name' in st.session_state:
        del st.session_state.selected_user_name
    if 'admin_target_users' in st.session_state:
        del st.session_state.admin_target_users
    
    # Pre-fetching 캐시 삭제 (일반 캐시와 사용자별 캐시 모두)
    if 'prefetch_cache' in st.session_state:
        del st.session_state.prefetch_cache
    if 'prefetch_cache_by_user' in st.session_state:
        del st.session_state.prefetch_cache_by_user
    
    # 페이지 상태 초기화
    st.session_state.current_page = "main"
    st.session_state.current_step = 1
    
    # 폼 데이터 초기화
    st.session_state.form_data = {
        'name': '',
        'physical_state': 0,
        'mental_state': 0,
        'state_reason': '',
        'improvement_plan': '',
        'yesterday_work': '',
        'yesterday_satisfaction': 0,
        'liked': '',
        'lacked': '',
        'learned': '',
        'looked_forward': '',
        'longed_for': '',
        'colleague_praise': '',
        'today_plans': ''
    }
    
    # IDP 관련 상태 초기화
    if 'show_idp_form' in st.session_state:
        st.session_state.show_idp_form = False
    if 'idp_saving' in st.session_state:
        st.session_state.idp_saving = False
    
    # CDP 관련 상태 초기화
    if 'cdp_edit_mode' in st.session_state:
        st.session_state.cdp_edit_mode = False
    if 'cdp_saving' in st.session_state:
        st.session_state.cdp_saving = False
    if 'cdp_pending_data' in st.session_state:
        del st.session_state.cdp_pending_data
    
    # 프로필 수정 관련 상태 초기화
    if 'is_saving_profile' in st.session_state:
        st.session_state.is_saving_profile = False
    if 'profile_edit_new_email' in st.session_state:
        del st.session_state.profile_edit_new_email
    if 'profile_edit_new_password' in st.session_state:
        del st.session_state.profile_edit_new_password
    if 'profile_edit_confirm_password' in st.session_state:
        del st.session_state.profile_edit_confirm_password
    if 'profile_edit_current_password' in st.session_state:
        del st.session_state.profile_edit_current_password
    
    # Snippet 저장 관련 상태 초기화
    if 'saving_snippet' in st.session_state:
        st.session_state.saving_snippet = False
    
    # 캐시 파일 삭제
    _clear_cache()

def _filter_user_archive(df, user_name):
    """DataFrame에서 사용자 데이터만 필터링합니다."""
    if df is None or df.empty:
        return []
    if '이름' in df.columns:
        user_archive = df[df['이름'] == user_name]
        return user_archive.to_dict('records') if not user_archive.empty else []
    return df.to_dict('records')

def refresh_archive_cache():
    """Snippet 아카이브 캐시를 갱신합니다."""
    try:
        viewing_user = get_current_viewing_user()
        user_name = viewing_user.get('name') if viewing_user else None
        if not user_name:
            return
        
        # prefetch_cache 초기화
        if 'prefetch_cache' not in st.session_state:
            st.session_state.prefetch_cache = {}
        
        # Snippet 아카이브 데이터 갱신
        try:
            import Archive
            archive_df = None
            
            # Google Sheets에서 가져오기 시도
            if st.session_state.get('google_sheets_connected', False):
                try:
                    archive_df = Archive.get_snippets_from_google_sheets(get_google_sheets_client, SPREADSHEET_ID)
                except Exception:
                    archive_df = None
            
            # 로컬 CSV에서 가져오기 (Google Sheets 실패 시 또는 미연결 시)
            if archive_df is None or (hasattr(archive_df, 'empty') and archive_df.empty):
                try:
                    archive_df = Archive.get_snippets_from_local_csv()
                except Exception:
                    archive_df = None
            
            st.session_state.prefetch_cache['archive'] = _filter_user_archive(archive_df, user_name)
        except Exception:
            st.session_state.prefetch_cache['archive'] = []
        
        # 캐시 파일에 저장
        touch_session_active()
    except Exception:
        # 아카이브 캐시 갱신 실패해도 계속 진행
        pass

def refresh_cdp_cache():
    """CDP 캐시를 갱신합니다."""
    try:
        viewing_user = get_current_viewing_user()
        user_name = viewing_user.get('name') if viewing_user else None
        if not user_name:
            return
        
        # prefetch_cache 초기화
        if 'prefetch_cache' not in st.session_state:
            st.session_state.prefetch_cache = {}
        
        # CDP 데이터 갱신
        try:
            import cdp
            cdp_df = cdp._fetch_cdp_dataframe()
            if cdp_df is not None and not cdp_df.empty:
                normalized = {c.strip(): c for c in cdp_df.columns}
                name_col = normalized.get("이름") or normalized.get("name") or list(cdp_df.columns)[0]
                user_cdp = cdp_df[cdp_df[name_col] == user_name]
                st.session_state.prefetch_cache['cdp'] = user_cdp.to_dict('records') if not user_cdp.empty else []
            else:
                st.session_state.prefetch_cache['cdp'] = []
        except Exception:
            st.session_state.prefetch_cache['cdp'] = []
        
        # 캐시 파일에 저장
        touch_session_active()
    except Exception:
        # CDP 캐시 갱신 실패해도 계속 진행
        pass

def refresh_idp_cache():
    """IDP 캐시를 갱신합니다."""
    try:
        viewing_user = get_current_viewing_user()
        user_name = viewing_user.get('name') if viewing_user else None
        if not user_name:
            return
        
        # prefetch_cache 초기화
        if 'prefetch_cache' not in st.session_state:
            st.session_state.prefetch_cache = {}
        
        # IDP 데이터 갱신
        try:
            import idp_usage
            idp_df = idp_usage.fetch_idp_dataframe()
            if idp_df is not None and not idp_df.empty:
                if '이름' in idp_df.columns:
                    user_idp = idp_df[idp_df['이름'] == user_name]
                    st.session_state.prefetch_cache['idp'] = user_idp.to_dict('records') if not user_idp.empty else []
                else:
                    st.session_state.prefetch_cache['idp'] = idp_df.to_dict('records')
            else:
                st.session_state.prefetch_cache['idp'] = []
        except Exception:
            st.session_state.prefetch_cache['idp'] = []
        
        # 캐시 파일에 저장
        touch_session_active()
    except Exception:
        # IDP 캐시 갱신 실패해도 계속 진행
        pass

def prefetch_user_data():
    """로그인 성공 시 사용자 데이터를 Pre-fetching하여 캐시에 저장합니다."""
    try:
        viewing_user = get_current_viewing_user()
        user_name = viewing_user.get('name') if viewing_user else None
        if not user_name:
            return
        
        prefetch_data = {}
        
        # 1. Snippet 아카이브 데이터 Pre-fetching
        try:
            import Archive
            archive_df = None
            
            # Google Sheets에서 가져오기 시도
            if st.session_state.get('google_sheets_connected', False):
                try:
                    archive_df = Archive.get_snippets_from_google_sheets(get_google_sheets_client, SPREADSHEET_ID)
                except Exception:
                    archive_df = None
            
            # 로컬 CSV에서 가져오기 (Google Sheets 실패 시 또는 미연결 시)
            if archive_df is None or (hasattr(archive_df, 'empty') and archive_df.empty):
                try:
                    archive_df = Archive.get_snippets_from_local_csv()
                except Exception:
                    archive_df = None
            
            prefetch_data['archive'] = _filter_user_archive(archive_df, user_name)
        except Exception:
            prefetch_data['archive'] = []
        
        # 2. CDP 데이터 Pre-fetching
        try:
            import cdp
            cdp_df = cdp._fetch_cdp_dataframe()
            if cdp_df is not None and not cdp_df.empty:
                # 사용자 데이터만 필터링
                normalized = {c.strip(): c for c in cdp_df.columns}
                name_col = normalized.get("이름") or normalized.get("name") or list(cdp_df.columns)[0]
                user_cdp = cdp_df[cdp_df[name_col] == user_name]
                prefetch_data['cdp'] = user_cdp.to_dict('records') if not user_cdp.empty else []
            else:
                prefetch_data['cdp'] = []
        except Exception as e:
            prefetch_data['cdp'] = []
        
        # 3. IDP 데이터 Pre-fetching
        try:
            import idp_usage
            idp_df = idp_usage.fetch_idp_dataframe()
            if idp_df is not None and not idp_df.empty:
                # 사용자 데이터만 필터링
                if '이름' in idp_df.columns:
                    user_idp = idp_df[idp_df['이름'] == user_name]
                    prefetch_data['idp'] = user_idp.to_dict('records') if not user_idp.empty else []
                else:
                    prefetch_data['idp'] = idp_df.to_dict('records')
            else:
                prefetch_data['idp'] = []
        except Exception as e:
            prefetch_data['idp'] = []
        
        # 4. Mission & KPI 데이터 Pre-fetching
        try:
            import organization
            mission_kpi_df = organization.get_sheet_data(organization.MISSION_KPI_SHEET_ID)
            if mission_kpi_df is not None and not mission_kpi_df.empty:
                prefetch_data['mission_kpi'] = mission_kpi_df.to_dict('records')
            else:
                prefetch_data['mission_kpi'] = []
        except Exception as e:
            prefetch_data['mission_kpi'] = []
        
        # 5. Team Ground Rule 데이터 Pre-fetching
        try:
            import organization
            ground_rule_df = organization.get_sheet_data(organization.GROUND_RULE_SHEET_ID)
            if ground_rule_df is not None and not ground_rule_df.empty:
                prefetch_data['ground_rule'] = ground_rule_df.to_dict('records')
            else:
                prefetch_data['ground_rule'] = []
        except Exception as e:
            prefetch_data['ground_rule'] = []
        
        # 세션 상태에 저장
        st.session_state.prefetch_cache = prefetch_data
        
    except Exception as e:
        # Pre-fetching 실패해도 로그인은 계속 진행
        pass
def render_login():
    """로그인 화면 렌더링"""
    # 비밀번호 필드의 "Show password" 버튼 제거 및 로그인 버튼 중복 클릭 방지
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
        <script>
        // 로그인 버튼 클릭 시 즉시 비활성화하여 중복 클릭 방지
        (function() {
            function disableLoginButton() {
                // form_submit_button 찾기
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    const buttons = form.querySelectorAll('button[type="submit"]');
                    buttons.forEach(button => {
                        const buttonText = button.textContent.trim();
                        // 로그인 버튼 찾기
                        if (buttonText === '로그인' || buttonText === '로그인 중...') {
                            // 버튼이 이미 비활성화되지 않은 경우에만 처리
                            if (!button.disabled) {
                                button.disabled = true;
                                button.style.opacity = '0.6';
                                button.style.cursor = 'not-allowed';
                                button.textContent = '로그인 중...';
                            }
                        }
                    });
                });
            }
            
            // form 제출 이벤트 리스너 추가
            document.addEventListener('submit', function(e) {
                const form = e.target;
                if (form && form.querySelector('button[type="submit"]')) {
                    // 약간의 지연을 두어 버튼이 클릭 이벤트를 받은 후 비활성화
                    setTimeout(disableLoginButton, 0);
                }
            }, true);
            
            // 버튼 클릭 이벤트 리스너 추가
            document.addEventListener('click', function(e) {
                const button = e.target.closest('button[type="submit"]');
                if (button) {
                    const buttonText = button.textContent.trim();
                    if (buttonText === '로그인') {
                        // 즉시 비활성화
                        button.disabled = true;
                        button.style.opacity = '0.6';
                        button.style.cursor = 'not-allowed';
                        button.textContent = '로그인 중...';
                    }
                }
            }, true);
            
            // 페이지 로드 후 초기 실행
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', disableLoginButton);
            } else {
                disableLoginButton();
            }
            
            // Streamlit의 동적 렌더링 대응
            const observer = new MutationObserver(function(mutations) {
                disableLoginButton();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
        """,
        unsafe_allow_html=True
    )
    
    st.title("🔐 Daily Snippets 로그인")
    st.markdown("Daily Snippets를 사용하려면 먼저 로그인해주세요.")
    st.markdown("---")
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 계정 정보를 입력해주세요")
            
            with st.form("login_form"):
                phone = st.text_input(
                    "휴대폰번호", 
                    placeholder="01012345678",
                    help="휴대폰번호를 입력하세요"
                )
                password = st.text_input(
                    "비밀번호", 
                    type="password",
                    placeholder="비밀번호를 입력하세요"
                )
                
                is_logging_in = st.session_state.get("logging_in", False)
                
                submitted = st.form_submit_button(
                    "로그인 중..." if is_logging_in else "로그인",
                    use_container_width=True
                )
                
                if submitted:
                    # 중복 클릭 방지 - 버튼 클릭 시 즉시 상태 설정
                    if is_logging_in:
                        st.warning("이미 로그인 처리 중입니다. 잠시만 기다려주세요.")
                        st.stop()
                    
                    # 버튼 클릭 즉시 로그인 상태로 설정 (중복 클릭 방지)
                    st.session_state.logging_in = True
                    
                    if phone and password:
                        user_info = login_user(phone, password)
                        if user_info:
                            st.session_state.logged_in = True
                            st.session_state.user_info = user_info
                            st.session_state.user_phone = phone
                            # 세션 user_info에 phone 키 보강
                            try:
                                st.session_state.user_info['phone'] = phone
                            except Exception:
                                pass
                            
                            # 로그인 시 viewing_user_info를 현재 사용자로 초기화
                            st.session_state.viewing_user_info = user_info.copy()
                            st.session_state.selected_user_name = user_info.get('name', '')
                            
                            # 관리자 대량 프리페치는 비활성화 (선택 기반으로 지연 로딩)
                            # 관리자 로그인 즉시 전체 사용자 캐시 생성을 하지 않습니다.
                            
                            # 로그인 성공 시 즉시 Daily Snippet 기록 페이지로 이동 (사이드바 버튼 효과)
                            st.session_state.logging_in = False
                            # Daily Snippet 페이지로 이동 (사이드바 버튼을 누른 것과 동일한 효과)
                            st.session_state.current_page = "daily_snippet"
                            st.session_state.last_page = "daily_snippet"
                            reset_page_state("daily_snippet")
                            st.session_state.scroll_to_top = True
                            # 백그라운드 prefetch 트리거 설정 (관리자는 지연)
                            st.session_state.prefetch_trigger = user_info.get('role', '').strip() != 'admin'
                            
                            # 최소한의 캐시만 저장 (빠른 응답을 위해)
                            st.session_state.last_active = _now_iso()
                            try:
                                cache_data = {
                                    'logged_in': True,
                                    'user_phone': phone,
                                    'user_info': user_info,
                                    'last_active': st.session_state.last_active,
                                    'idle_timeout_minutes': st.session_state.get('idle_timeout_minutes', 30),
                                }
                                _save_cache(cache_data)
                            except Exception:
                                pass
                            
                            st.rerun()
                        else:
                            st.session_state.logging_in = False
                            st.error("휴대폰번호 또는 비밀번호가 올바르지 않습니다.")
                    else:
                        st.warning("휴대폰번호와 비밀번호를 모두 입력해주세요.")
                        st.session_state.logging_in = False
    

def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        # 사이드바 제목 스타일 강제 적용 (CSS 직접 삽입)
        st.markdown(
            """
            <style>
            /* 사이드바 제목 폰트 사이즈 강제 적용 - 최우선순위 */
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] .element-container h1,
            [data-testid="stSidebar"] [class*="stTitle"] h1,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
            [data-testid="stSidebar"] h1[class],
            [data-testid="stSidebar"] * h1 {
                font-size: 1.2rem !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            </style>
            <script>
            (function() {
                function forceTitleStyle() {
                    const contexts = [window.parent.document, document];
                    contexts.forEach(function(doc) {
                        try {
                            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                            if (sidebar) {
                                const h1Elements = sidebar.querySelectorAll('h1');
                                h1Elements.forEach(function(h1) {
                                    h1.style.cssText = 'font-size: 1.2rem !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;';
                                });
                            }
                        } catch(e) {}
                    });
                }
                forceTitleStyle();
                setTimeout(forceTitleStyle, 0);
                setTimeout(forceTitleStyle, 10);
            })();
            </script>
            """,
            unsafe_allow_html=True
        )
        
        st.title("📝 Daily Snippets")
        
        # 제목 렌더링 직후 스타일 재적용
        st.markdown(
            """
            <script>
            (function() {
                function forceTitleStyle() {
                    const contexts = [window.parent.document, document];
                    contexts.forEach(function(doc) {
                        try {
                            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                            if (sidebar) {
                                const h1Elements = sidebar.querySelectorAll('h1');
                                h1Elements.forEach(function(h1) {
                                    h1.style.cssText = 'font-size: 1.2rem !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;';
                                });
                            }
                        } catch(e) {}
                    });
                }
                setTimeout(forceTitleStyle, 0);
                setTimeout(forceTitleStyle, 50);
            })();
            </script>
            """,
            unsafe_allow_html=True
        )

        
        # 로그인된 사용자 정보
        if st.session_state.logged_in and st.session_state.user_info:
            user = st.session_state.user_info
            st.success(f"안녕하세요, {user['name']}님!")
            
            # 관리자인 경우 사용자 선택 드롭박스 추가
            if user.get('role', '').strip() == 'admin':
                # 표시여부가 '대상'인 사용자 목록 가져오기 (캐시 사용)
                if 'admin_target_users' not in st.session_state:
                    records = fetch_users_records()
                    target_users = [
                        row for row in records 
                        if str(row.get('표시여부', '')).strip() == '대상'
                    ]
                    st.session_state.admin_target_users = target_users
                else:
                    target_users = st.session_state.admin_target_users
                
                if target_users:
                    # 사용자 이름 리스트 생성 (현재 로그인한 사용자를 기본값으로)
                    user_names = [str(row.get('이름(본명)', '')).strip() for row in target_users]
                    
                    # 세션 상태에 선택된 사용자 정보 저장
                    if 'selected_user_name' not in st.session_state:
                        st.session_state.selected_user_name = user['name']
                    
                    # 현재 선택된 사용자의 인덱스 찾기
                    try:
                        current_index = user_names.index(st.session_state.selected_user_name)
                    except ValueError:
                        current_index = user_names.index(user['name']) if user['name'] in user_names else 0
                        st.session_state.selected_user_name = user_names[current_index]
                    
                    # 드롭박스와 새로고침 버튼을 나란히 배치
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        selected_name = st.selectbox(
                            "📋 사용자 선택",
                            options=user_names,
                            index=current_index,
                            key="admin_user_select"
                        )
                    with col2:
                        st.markdown("<div style='margin-top: 1.8rem;'></div>", unsafe_allow_html=True)
                        if st.button("🔄", key="refresh_user_list", help="사용자 목록 새로고침"):
                            if 'admin_target_users' in st.session_state:
                                del st.session_state.admin_target_users
                            st.rerun()
                    
                    # 선택된 사용자가 변경되면 세션 업데이트 및 즉시 아카이브 열기
                    if selected_name != st.session_state.selected_user_name:
                        st.session_state.selected_user_name = selected_name
                        # 선택된 사용자의 전체 정보 가져오기
                        for row in target_users:
                            if str(row.get('이름(본명)', '')).strip() == selected_name:
                                # 현재 보고 있는 사용자 정보를 세션에 저장 (원본 로그인 정보는 유지)
                                st.session_state.viewing_user_info = {
                                    'phone': str(row.get('휴대폰번호', '')).strip(),
                                    'password': str(row.get('비밀번호', '')).strip(),
                                    'name': str(row.get('이름(본명)', '')).strip(),
                                    'email': str(row.get('회사메일', '')).strip(),
                                    'role': str(row.get('권한', 'user')).strip() or 'user',
                                    'timestamp': str(row.get('타임스탬프', '')).strip(),
                                    'display': str(row.get('표시여부', '')).strip(),
                                }
                                # 사용자 전환 시 해당 사용자의 캐시를 사용
                                if 'prefetch_cache_by_user' in st.session_state:
                                    prefetch_cache_by_user = st.session_state.prefetch_cache_by_user
                                    if selected_name in prefetch_cache_by_user:
                                        # 해당 사용자의 캐시를 prefetch_cache로 설정
                                        st.session_state.prefetch_cache = prefetch_cache_by_user[selected_name].copy()
                                    else:
                                        # 캐시가 없으면 초기화
                                        if 'prefetch_cache' in st.session_state:
                                            del st.session_state.prefetch_cache
                                else:
                                    # 사용자별 캐시가 없으면 일반 캐시 초기화
                                    if 'prefetch_cache' in st.session_state:
                                        del st.session_state.prefetch_cache
                                # 선택 즉시 아카이브 캐시 준비 및 페이지 열기
                                try:
                                    refresh_archive_cache()
                                except Exception:
                                    pass
                                navigate_to_page("archive")
                                st.rerun()
                                break
                    
                    # viewing_user_info가 없으면 현재 로그인한 사용자 정보로 초기화
                    if 'viewing_user_info' not in st.session_state:
                        st.session_state.viewing_user_info = user.copy()
                    
                    # 선택된 사용자가 현재 로그인 사용자와 다를 경우 표시
                    if selected_name != user['name']:
                        st.info(f"👁️ 현재 조회 중: {selected_name}")
            
            # 개인 정보 수정 버튼
            if st.button("✏️ 개인 정보 수정", use_container_width=True):
                navigate_to_page("profile_edit")
        
        st.markdown("---")

        # 메뉴
        if st.button("📝 Daily Snippet 기록", use_container_width=True):
            navigate_to_page("daily_snippet")
          
        if st.button("📚 Snippet 아카이브", use_container_width=True):
            # 관리자 선택 사용자 기준으로 viewing_user 설정
            target_name = None
            try:
                if 'selected_user_name' in st.session_state and str(st.session_state.selected_user_name).strip():
                    target_name = str(st.session_state.selected_user_name).strip()
            except Exception:
                target_name = None
            if not target_name and st.session_state.get('user_info'):
                target_name = str(st.session_state.user_info.get('name', '')).strip()
            if target_name:
                st.session_state.viewing_user_info = {'name': target_name}
                # 선택 사용자 아카이브 캐시 선준비
                try:
                    refresh_archive_cache()
                except Exception:
                    pass
            navigate_to_page("archive")
        
        if st.button("📊 CDP", use_container_width=True):
            navigate_to_page("cdp")
        
        if st.button("🎯 IDP", use_container_width=True):
            navigate_to_page("idp")
        
        if st.button("🎯 Goal & Policy", use_container_width=True):
            navigate_to_page("goal_policy")
        
        # 동일 계위 메뉴: Goal & Policy 다음 - 1on1 코칭
        if st.button("👥 1on1 코칭", use_container_width=True):
            # 현재 선택된 사용자 기준으로 viewing_user 설정
            target_name = None
            try:
                if 'selected_user_name' in st.session_state and str(st.session_state.selected_user_name).strip():
                    target_name = str(st.session_state.selected_user_name).strip()
            except Exception:
                target_name = None
            if not target_name and st.session_state.get('user_info'):
                target_name = str(st.session_state.user_info.get('name', '')).strip()
            if target_name:
                st.session_state.viewing_user_info = {'name': target_name}
                # 캐시는 메인 화면에서 로딩 (사이드바에서는 호출하지 않음)
            navigate_to_page("one_on_one_coaching")
       
        
        st.markdown("---")
        
        # 로그아웃 버튼
        if st.session_state.logged_in:
            if st.button("🚪 로그아웃", use_container_width=True):
                logout_and_clear_cache()
                st.session_state.scroll_to_top = True
                st.rerun()

def render_main_page():
    """메인 페이지 렌더링"""
    st.title("🏠 Daily Snippets 메인")
    st.markdown("---")
    
    # 환영 메시지
    if st.session_state.logged_in and st.session_state.user_info:
        user = st.session_state.user_info
        st.success(f"안녕하세요, **{user['name']}**님! 오늘도 좋은 하루 되세요! 😊")
    
    # 기능 소개
    st.markdown("### 🚀 주요 기능")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📚 Snippet 아카이브
        그동안 작성한 Snippet 기록들을 확인해보세요!
        """)
        if st.button("아카이브 보기", use_container_width=True):
            navigate_to_page("archive")
    
    with col2:
        st.markdown("""
        #### 🎯 IDP/CDP
        개인/경력 개발 계획을 관리해보세요!
        """)
        if st.button("개발 계획", use_container_width=True):
            navigate_to_page("idp")
    
    # 최근 활동 (추후 구현)
    st.markdown("### 📊 최근 활동")
    st.info("최근 활동 내역이 여기에 표시됩니다.")

def render_daily_snippet():
    """Daily Snippet 기록 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "daily_snippet":
        # 다른 페이지에서 돌아온 경우 초기 상태로 리셋
        reset_page_state("daily_snippet")
        st.session_state.last_page = "daily_snippet"
    
    st.title("📝 Daily Snippet 기록")
    st.markdown("매일의 상태와 업무를 기록하고 팀과 공유해보세요!")
    st.markdown("---")
    
    # Daily Snippet 기록은 항상 로그인한 본인만 가능
    # (관리자가 다른 사용자를 선택해도 기록은 본인 것만)
    logged_in_user = st.session_state.user_info
    user_name = logged_in_user.get('name', '') if logged_in_user else ''
    st.subheader(f"{user_name} 님의 Daily Snippet")
    
    # 관리자가 다른 사용자를 선택한 경우 안내 메시지 표시
    viewing_user = get_current_viewing_user()
    if viewing_user and logged_in_user and viewing_user.get('name') != logged_in_user.get('name'):
        st.info(f"💡 Daily Snippet 기록은 로그인한 본인({user_name})만 작성할 수 있습니다. 다른 사용자의 Snippet은 '📚 Snippet 아카이브' 페이지에서 조회하실 수 있습니다.")
    
    # daily_snippet.py의 임베드 함수 사용
    try:
        import daily_snippet
        daily_snippet.render_daily_snippet_embedded(save_data_callback=save_data_with_fallback)
    except Exception as e:
        st.error(f"Daily Snippet 렌더링 중 오류가 발생했습니다: {e}")
        st.info("🚧 Daily Snippet 기능을 불러올 수 없습니다.")

def render_archive():
    """Snippet 아카이브 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "archive":
        st.session_state.last_page = "archive"
    
    try:
        import Archive
        # 메인 앱 컨텍스트에서 아카이브 렌더링 (page_config/로그인 UI 없음)
        Archive.render_archive_embedded(get_google_sheets_client, SPREADSHEET_ID)
    except Exception as e:
        st.error(f"Snippet 아카이브 렌더링 중 오류가 발생했습니다: {e}")
        st.info("🚧 Snippet 아카이브 기능을 불러올 수 없습니다.")

def render_idp():
    """IDP 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "idp":
        # 다른 페이지에서 돌아온 경우 초기 상태로 리셋
        reset_page_state("idp")
        st.session_state.last_page = "idp"
    
    st.title("🎯 IDP (Individual Development Plan)")
    st.markdown("개인 개발 계획을 관리해보세요!")
    st.markdown("---")
    try:
        import idp_usage
        # 메인 앱 컨텍스트에서 카드 렌더링 (page_config/로그인 UI 없음)
        idp_usage.render_idp_usage_embedded()
    except Exception as e:
        st.error(f"IDP 사용 내역 렌더링 중 오류가 발생했습니다: {e}")

def render_cdp():
    """CDP 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "cdp":
        # 다른 페이지에서 돌아온 경우 초기 상태로 리셋
        reset_page_state("cdp")
        st.session_state.last_page = "cdp"
    
    st.title("📊 CDP (Career Development Plan)")
    st.markdown("경력 개발 계획을 관리해보세요!")
    st.markdown("---")
    try:
        import cdp
        cdp.render_cdp_embedded()
    except Exception as e:
        st.error(f"CDP 렌더링 중 오류가 발생했습니다: {e}")

def render_goal_policy():
    """Goal & Policy 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "goal_policy":
        st.session_state.last_page = "goal_policy"
    
    try:
        import organization
        # 메인 앱 컨텍스트에서 조직 정보 렌더링 (page_config/로그인 UI 없음)
        organization.render_organization_embedded()
    except Exception as e:
        st.error(f"조직 정보 렌더링 중 오류가 발생했습니다: {e}")
        st.info("🚧 Goal & Policy 기능을 불러올 수 없습니다.")
        st.markdown("""
        ### 계획된 기능:
        - 팀/개인 목표 설정
        - 정책 문서 관리
        - 목표 달성 추적
        - 피드백 시스템
        """)

def render_one_on_one_coaching():
    """1on1 코칭 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "one_on_one_coaching":
        st.session_state.last_page = "one_on_one_coaching"
    
    try:
        import importlib.util
        import sys
        import traceback
        
        # Python 식별자로는 숫자로 시작할 수 없으므로 파일명을 직접 import
        module_name = "oneon1_module"
        file_path = "1on1.py"
        
        # 이미 로드된 모듈이면 캐시에서 제거 (재로드를 위해)
        if module_name in sys.modules:
            del sys.modules[module_name]
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            st.error(f"1on1 모듈을 로드할 수 없습니다: {file_path} 파일을 찾을 수 없습니다.")
            return
        
        oneon1_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oneon1_module)
        
        # 메인 앱 컨텍스트에서 1on1 렌더링 (page_config/로그인 UI 없음)
        oneon1_module.render_oneon1_embedded()
    except ImportError as e:
        st.error(f"1on1 코칭 모듈 import 오류: {e}")
        st.code(traceback.format_exc())
        st.info("🚧 1on1 코칭 기능을 불러올 수 없습니다. 필요한 라이브러리가 설치되었는지 확인해주세요.")
    except AttributeError as e:
        st.error(f"1on1 코칭 모듈 속성 오류: {e}")
        st.code(traceback.format_exc())
        st.info("🚧 1on1 코칭 기능을 불러올 수 없습니다.")
    except Exception as e:
        st.error(f"1on1 코칭 렌더링 중 오류가 발생했습니다: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
        st.info("🚧 1on1 코칭 기능을 불러올 수 없습니다.")

def render_profile_edit():
    """개인 정보 수정 페이지 렌더링"""
    # 페이지 진입 시 이전 상태 확인 및 초기화
    # 다른 페이지에서 온 경우 초기 상태로 리셋
    if "last_page" not in st.session_state or st.session_state.get("last_page") != "profile_edit":
        reset_page_state("profile_edit")
        st.session_state.last_page = "profile_edit"
        # 강제 초기화 플래그 설정
        st.session_state.profile_edit_force_reset = True
    
    # 비밀번호 필드의 "Show password" 버튼 제거 및 변경하기 버튼 중복 클릭 방지
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
        /* "변경 중..." 버튼 완전히 숨김 */
        button.profile-button-disabled {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        </style>
        <script>
        // 변경하기 버튼 클릭 시 즉시 비활성화하여 중복 클릭 방지
        (function() {
            function disableSaveButton() {
                // key="profile_save_button"인 버튼 찾기
                const buttons = document.querySelectorAll('button[data-testid*="profile_save_button"], button');
                buttons.forEach(button => {
                    const buttonText = button.textContent.trim();
                    // 변경하기 버튼 찾기
                    if (buttonText === '✏️ 변경하기' || buttonText === '✏️ 변경 중...') {
                        // "변경 중..." 텍스트일 때는 버튼을 완전히 숨김
                        if (buttonText === '✏️ 변경 중...') {
                            button.disabled = true;
                            button.classList.add('profile-button-disabled');
                            button.style.display = 'none';
                            button.style.visibility = 'hidden';
                            button.style.opacity = '0';
                            button.style.pointerEvents = 'none';
                        } else if (!button.disabled && !button.classList.contains('profile-button-disabled')) {
                            // "변경하기" 텍스트일 때는 정상적으로 표시
                            button.style.display = '';
                            button.style.visibility = '';
                            button.style.opacity = '';
                        }
                    }
                });
            }
            
            // 버튼 클릭 이벤트 리스너 추가
            document.addEventListener('click', function(e) {
                const button = e.target.closest('button');
                if (button) {
                    const buttonText = button.textContent.trim();
                    if (buttonText === '✏️ 변경하기') {
                        // 즉시 비활성화 및 숨김
                        button.disabled = true;
                        button.classList.add('profile-button-disabled');
                        button.textContent = '✏️ 변경 중...';
                        button.style.display = 'none';
                        button.style.visibility = 'hidden';
                        button.style.opacity = '0';
                        button.style.pointerEvents = 'none';
                        // 이벤트 전파 중단 (추가 클릭 방지)
                        e.stopPropagation();
                        e.preventDefault();
                    }
                }
            }, true);
            
            // 페이지 로드 후 초기 실행
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', disableSaveButton);
            } else {
                disableSaveButton();
            }
            
            // Streamlit의 동적 렌더링 대응 - 주기적으로 체크
            setInterval(disableSaveButton, 100);
            
            // MutationObserver로 DOM 변경 감지
            const observer = new MutationObserver(function(mutations) {
                disableSaveButton();
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        </script>
        """,
        unsafe_allow_html=True
    )
    
    st.title("✏️ 개인 정보 수정")
    st.markdown("---")
    
    if st.session_state.logged_in and st.session_state.user_info:
        user = st.session_state.user_info
        # 구글시트 우선 조회 → 세션 저장값 → 유저 객체 순으로 폴백
        sheet_phone = get_user_phone_from_google_sheet(email=user.get('email'), name=user.get('name'))
        phone = _choose_display_phone(st.session_state.get('user_phone'), sheet_phone)

        st.markdown("### 현재 정보")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**이름:** {user['name']}")
            st.markdown(f"**휴대폰번호:** {phone}")

        with col2:
            st.markdown(f"**이메일:** {user['email']}")


        st.markdown("---")
        st.subheader("이메일 또는 비밀번호 변경")
        
        # 업데이트 성공 메시지 표시 (rerun 후)
        if st.session_state.get('profile_update_success', False):
            st.success("개인 정보가 업데이트되었습니다.")
            # 메시지 표시 후 플래그 제거
            st.session_state.profile_update_success = False

        # 세션 상태 초기화 (강제 리셋 또는 초기 진입 시)
        force_reset = st.session_state.get('profile_edit_force_reset', False)
        if force_reset or 'profile_edit_new_email' not in st.session_state:
            # 최신 사용자 정보로 강제 초기화
            st.session_state.profile_edit_new_email = user.get('email', '')
            st.session_state.profile_edit_new_password = ''
            st.session_state.profile_edit_confirm_password = ''
            st.session_state.profile_edit_current_password = ''
            # 위젯 키도 강제 삭제
            widget_keys = [
                'profile_edit_email_input',
                'profile_edit_password_input',
                'profile_edit_confirm_input',
                'profile_edit_current_input'
            ]
            for key in widget_keys:
                if key in st.session_state:
                    del st.session_state[key]
            # 플래그 제거
            if force_reset:
                st.session_state.profile_edit_force_reset = False

        # 입력 필드를 form 밖에 배치하여 즉시 반영되도록 수정
        def update_email():
            st.session_state.profile_edit_new_email = st.session_state.profile_edit_email_input
        
        def update_password():
            st.session_state.profile_edit_new_password = st.session_state.profile_edit_password_input
        
        def update_confirm_password():
            st.session_state.profile_edit_confirm_password = st.session_state.profile_edit_confirm_input
        
        def update_current_password():
            st.session_state.profile_edit_current_password = st.session_state.profile_edit_current_input
        
        new_email = st.text_input(
            "이메일", 
            value=st.session_state.profile_edit_new_email, 
            help="변경할 이메일을 입력하세요",
            key="profile_edit_email_input",
            on_change=update_email
        )
        
        new_password = st.text_input(
            "새 비밀번호", 
            type="password", 
            placeholder="변경 시에만 입력",
            value=st.session_state.profile_edit_new_password,
            key="profile_edit_password_input",
            on_change=update_password
        )
        
        confirm_password = st.text_input(
            "새 비밀번호 확인", 
            type="password", 
            placeholder="변경 시에만 입력",
            value=st.session_state.profile_edit_confirm_password,
            key="profile_edit_confirm_input",
            on_change=update_confirm_password
        )
        
        current_password = st.text_input(
            "현재 비밀번호", 
            type="password", 
            placeholder="변경 적용을 위해 현재 비밀번호 입력",
            value=st.session_state.profile_edit_current_password,
            key="profile_edit_current_input",
            on_change=update_current_password
        )
        
        # 세션 상태에서 최신 값 가져오기
        current_new_email = st.session_state.profile_edit_new_email
        current_new_password = st.session_state.profile_edit_new_password
        current_confirm_password = st.session_state.profile_edit_confirm_password
        current_current_password = st.session_state.profile_edit_current_password
            
        email_changed = (current_new_email or "").strip() != (user.get('email') or "").strip()
        password_entered = bool((current_new_password or "").strip() or (current_confirm_password or "").strip())
        current_entered = bool((current_current_password or "").strip())

        # 저장 중 상태 처리
        if st.session_state.is_saving_profile:
            # 저장 중일 때는 버튼 대신 로딩 메시지 표시
            st.info("⏳ 변경 처리 중입니다...")
            
            # 변경 조건 검증
            validation_errors = []
            
            # 변경할 내용이 있는지 확인
            if not email_changed and not password_entered:
                validation_errors.append("변경할 내용이 없습니다. 이메일 또는 비밀번호를 변경해주세요.")
            
            # 현재 비밀번호 입력 확인
            if not current_entered:
                validation_errors.append("현재 비밀번호를 입력해주세요.")
            
            # 현재 비밀번호 검증
            if current_entered and (current_current_password or "") != (user.get('password') or ""):
                validation_errors.append("현재 비밀번호가 일치하지 않습니다.")
            
            # 비밀번호 변경 시 추가 검증
            if password_entered:
                if not current_new_password or not current_confirm_password:
                    validation_errors.append("새 비밀번호와 확인을 모두 입력해주세요.")
                elif current_new_password != current_confirm_password:
                    validation_errors.append("새 비밀번호와 확인이 일치하지 않습니다.")
                elif len(current_new_password) < 4:
                    validation_errors.append("비밀번호는 최소 4자 이상이어야 합니다.")
            
            # 검증 오류가 있으면 경고 표시하고 페이지 초기화
            if validation_errors:
                st.session_state.is_saving_profile = False  # 검증 실패 시 상태 복원
                for error in validation_errors:
                    st.warning(f"⚠️ {error}")
                
                # 검증 실패 시에도 페이지 초기화
                reset_page_state("profile_edit")
                # 강제 리셋 플래그 설정
                st.session_state.profile_edit_force_reset = True
                st.session_state.last_page = None
                st.rerun()
            
            # 검증 통과 시 변경 처리
            updated = False
            with st.spinner("변경 중..."):
                # 이메일 변경
                if email_changed and current_new_email:
                    if update_user_in_sheet(phone, new_email=current_new_email):
                        st.session_state.user_info['email'] = current_new_email
                        updated = True

                # 비밀번호 변경
                if password_entered and current_new_password:
                    if update_user_in_sheet(phone, new_password=current_new_password):
                        # 세션의 비밀번호도 업데이트하여 이후 검증에 사용
                        st.session_state.user_info['password'] = current_new_password
                        updated = True

            st.session_state.is_saving_profile = False
            
            # 저장 성공 시 처리
            if updated:
                # 사용자 정보가 업데이트되었으므로 캐시 갱신
                touch_session_active()
                
                # 변경 성공 시 자동 로그아웃
                logout_and_clear_cache()
                
                # 성공 메시지 표시
                st.success("✅ 개인 정보가 성공적으로 변경되었습니다. 다시 로그인해주세요.")
                st.info("보안을 위해 자동으로 로그아웃되었습니다.")
                
                # 로그인 화면으로 이동
                st.rerun()
            else:
                # 저장 실패 또는 변경 내용 없음
                st.info("변경된 내용이 없습니다.")
                
                # 페이지 상태 초기화
                reset_page_state("profile_edit")
                # 강제 리셋 플래그 설정하여 다음 렌더링에서 확실히 초기화되도록 함
                st.session_state.profile_edit_force_reset = True
                st.session_state.last_page = None
                
                # 페이지를 다시 렌더링하여 초기화된 상태 표시
                st.rerun()
        else:
            # 변경하기 버튼 표시 (저장 중이 아닐 때만)
            submitted = st.button(
                "✏️ 변경하기",
                use_container_width=True,
                key="profile_save_button"
            )
            
            if submitted:
                # 버튼 클릭 즉시 저장 상태로 설정 (버튼이 사라지도록 함)
                st.session_state.is_saving_profile = True
                # 즉시 rerun하여 버튼을 숨기고 검증/저장 로직 실행
                st.rerun()
    else:
        st.error("로그인이 필요합니다.")

def render_google_settings():
    """Google Sheets 설정 페이지 렌더링"""
    st.title("⚙️ Google Sheets 설정")
    st.markdown("Google Sheets 연동을 위한 인증 정보를 설정해주세요.")
    st.markdown("---")
    
    # 현재 연결 상태
    if st.session_state.google_sheets_connected:
        st.success("✅ Google Sheets가 연결되어 있습니다!")
    else:
        st.warning("⚠️ Google Sheets가 연결되지 않았습니다.")
    
    st.markdown("### 📋 설정 방법")
    
    # 방법 1: 서비스 계정 JSON 파일 업로드
    st.markdown("#### 방법 1: 서비스 계정 JSON 파일 업로드")
    uploaded_file = st.file_uploader(
        "Google 서비스 계정 JSON 파일을 업로드하세요",
        type=['json'],
        help="Google Cloud Console에서 생성한 서비스 계정 키 파일을 업로드하세요"
    )
    
    if uploaded_file is not None:
        try:
            # 파일 내용 읽기
            file_contents = uploaded_file.read().decode('utf-8')
            creds_info = json.loads(file_contents)
            
            # 필수 필드 확인
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id', 'auth_uri', 'token_uri']
            missing_fields = [field for field in required_fields if field not in creds_info]
            
            if missing_fields:
                st.error(f"서비스 계정 파일에 필수 필드가 누락되었습니다: {', '.join(missing_fields)}")
            else:
                # 세션 상태에 저장
                st.session_state.google_credentials = file_contents
                st.session_state.google_sheets_connected = True
                st.success("✅ 서비스 계정 정보가 성공적으로 설정되었습니다!")
                st.rerun()
                
        except json.JSONDecodeError:
            st.error("올바른 JSON 파일이 아닙니다.")
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
    
    # 방법 2: Streamlit secrets 설정 안내
    st.markdown("#### 방법 2: Streamlit secrets 설정")
    st.markdown("""
    Streamlit secrets를 통해 서비스 계정 JSON 내용을 설정할 수 있습니다.
    
    Streamlit Cloud의 경우: Settings > Secrets에서 설정하거나, `.streamlit/secrets.toml` 파일에 다음 형식으로 추가하세요:
    
    ```toml
    [google]
    credentials_json = '{"type": "service_account", ...}'
    
    # 또는
    
    [google.service_account]
    type = "service_account"
    project_id = "..."
    # ... 나머지 키들
    ```
    """)
    
    # 방법 3: 서비스 계정 JSON 파일 생성 안내
    st.markdown("#### 방법 3: 서비스 계정 JSON 파일 생성")
    st.markdown("""
    1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
    2. 프로젝트 선택 또는 새 프로젝트 생성
    3. "API 및 서비스" > "사용 설정된 API" > "Google Sheets API" 활성화
    4. "API 및 서비스" > "사용자 인증 정보" > "사용자 인증 정보 만들기" > "서비스 계정"
    5. 서비스 계정 생성 후 "키" 탭에서 "키 추가" > "JSON" 다운로드
    6. 다운로드한 JSON 파일을 위의 방법 1로 업로드
    """)
    
    # 연결 테스트
    if st.button("🔗 연결 테스트", use_container_width=True):
        client = get_google_sheets_client()
        if client:
            try:
                spreadsheet = client.open_by_key(SPREADSHEET_ID)
                worksheet = spreadsheet.sheet1
                # 간단한 테스트
                test_data = worksheet.get_all_values()
                st.success("✅ Google Sheets 연결이 성공적으로 확인되었습니다!")
                st.session_state.google_sheets_connected = True
            except Exception as e:
                st.error(f"❌ 연결 테스트 실패: {e}")
                st.session_state.google_sheets_connected = False
        else:
            st.error("❌ Google Sheets 클라이언트를 생성할 수 없습니다.")
    
    # 로컬 저장 기능 안내
    st.markdown("---")
    st.markdown("### 💾 로컬 저장 기능")
    st.info("Google Sheets 연동이 어려운 경우, 로컬 CSV 파일로 저장할 수도 있습니다.")
    
    if st.button("📁 로컬 CSV 저장으로 전환", use_container_width=True):
        st.session_state.use_local_storage = True
        st.success("로컬 CSV 저장 모드로 전환되었습니다!")
        st.rerun()

def save_to_local_csv(data):
    """데이터를 로컬 CSV 파일에 저장합니다."""
    try:
        import csv
        from datetime import datetime
        
        # CSV 파일 경로
        csv_file = "daily_snippets.csv"
        
        # 헤더 정의
        headers = [
            "타임스탬프", "이름", "몸상태", "마음상태", "상태이유", "개선방안",
            "전일업무", "전일만족도", "좋았던점", "아쉬웠던점", "배웠던점",
            "향후시도", "바라는점", "동료칭찬", "오늘할일"
        ]
        
        # 파일이 존재하지 않으면 헤더 작성
        file_exists = os.path.exists(csv_file)
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(data)
        
        return True
    except Exception as e:
        st.error(f"로컬 CSV 저장 오류: {e}")
        return False

def main():
    """메인 함수"""
    # 세션 상태 초기화
    initialize_session_state()
    # 캐시에서 세션 복구 시도 (유휴시간 초과 시 캐시 파기)
    try_restore_session_from_cache()
    # 유휴 시간 체크: 초과 시 자동 로그아웃
    if st.session_state.logged_in and _is_idle_expired(st.session_state.last_active, st.session_state.idle_timeout_minutes):
        logout_and_clear_cache()
        st.warning("오랜 시간 활동이 없어 자동 로그아웃되었습니다.")
    elif st.session_state.logged_in:
        # 로그인되어 있으면 활동 시간만 빠르게 갱신 (prefetch 전에)
        st.session_state.last_active = _now_iso()
    
    # secrets가 있으면 자동 연결 시도 (필요한 경우에만)
    if st.session_state.logged_in and not st.session_state.get('google_sheets_connected', False):
        ensure_google_sheets_connection()
    
    # 백그라운드 prefetch 처리 (로그인 후 한 번만 실행, 페이지 렌더링 후)
    if st.session_state.get('prefetch_trigger', False) and st.session_state.logged_in:
        st.session_state.prefetch_trigger = False
        # 페이지 렌더링 후 prefetch 실행을 위해 플래그만 설정
        st.session_state.prefetch_pending = True
    
    # 로그인 상태 확인
    if not st.session_state.logged_in:
        render_login()
    else:
        # 사이드바 스타일 재적용 (리프레시 시에도 유지되도록)
        st.markdown(
            """
            <style>
            /* 사이드바 제목 폰트 사이즈 강제 적용 (리프레시 대응) */
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] .element-container h1,
            [data-testid="stSidebar"] [class*="stTitle"] h1,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
            [data-testid="stSidebar"] h1[class],
            [data-testid="stSidebar"] * h1 {
                font-size: 1.2rem !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            }
            </style>
            <script>
            // 사이드바 제목 폰트 사이즈 초기 적용
            (function() {
                function applySidebarTitleStyle() {
                    // Streamlit은 iframe 내에서 실행되므로 두 가지 방법 모두 시도
                    const contexts = [
                        window.parent.document,
                        document
                    ];
                    
                    contexts.forEach(function(doc) {
                        try {
                            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                            if (sidebar) {
                                const h1Elements = sidebar.querySelectorAll('h1');
                                h1Elements.forEach(function(h1) {
                                    h1.style.setProperty('font-size', '1.2rem', 'important');
                                    h1.style.setProperty('white-space', 'nowrap', 'important');
                                    h1.style.setProperty('overflow', 'hidden', 'important');
                                    h1.style.setProperty('text-overflow', 'ellipsis', 'important');
                                });
                            }
                        } catch(e) {
                            // iframe 접근 오류 무시
                        }
                    });
                }
                
                // 초기 로드 시에만 적용
                applySidebarTitleStyle();
            })();
            </script>
            """,
            unsafe_allow_html=True
        )
        
        # 사이드바 렌더링
        render_sidebar()
        
        # 사이드바 렌더링 후 스타일 재적용 (버튼 클릭 시에도 유지)
        st.markdown(
            """
            <script>
            // 사이드바 제목 폰트 사이즈 적용 (사용자 선택/변경 및 메뉴 버튼 클릭 시에만)
            (function() {
                function applyTitleStyle() {
                    const contexts = [
                        window.parent.document,
                        document
                    ];
                    
                    contexts.forEach(function(doc) {
                        try {
                            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                            if (sidebar) {
                                const h1Elements = sidebar.querySelectorAll('h1');
                                h1Elements.forEach(function(h1) {
                                    h1.style.setProperty('font-size', '1.2rem', 'important');
                                    h1.style.setProperty('white-space', 'nowrap', 'important');
                                    h1.style.setProperty('overflow', 'hidden', 'important');
                                    h1.style.setProperty('text-overflow', 'ellipsis', 'important');
                                });
                            }
                        } catch(e) {}
                    });
                }
                
                // 모든 버튼과 selectbox에 클릭/변경 이벤트 리스너 추가
                function attachEventListeners() {
                    const contexts = [
                        window.parent.document,
                        document
                    ];
                    
                    contexts.forEach(function(doc) {
                        try {
                            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
                            if (sidebar) {
                                // 모든 버튼에 클릭 이벤트 리스너 (사이드바 메뉴 버튼)
                                const buttons = sidebar.querySelectorAll('button');
                                buttons.forEach(function(btn) {
                                    // 이미 리스너가 추가된 버튼은 제외 (중복 방지)
                                    if (!btn.hasAttribute('data-title-style-listener')) {
                                        btn.setAttribute('data-title-style-listener', 'true');
                                        btn.addEventListener('click', function(e) {
                                            // 즉시 적용
                                            applyTitleStyle();
                                            // 버블링 단계에서도 적용
                                            setTimeout(function() {
                                                applyTitleStyle();
                                            }, 0);
                                            // Streamlit rerun 후에도 스타일 유지
                                            setTimeout(applyTitleStyle, 10);
                                            setTimeout(applyTitleStyle, 50);
                                            setTimeout(applyTitleStyle, 100);
                                            setTimeout(applyTitleStyle, 200);
                                            setTimeout(applyTitleStyle, 300);
                                            setTimeout(applyTitleStyle, 500);
                                            setTimeout(applyTitleStyle, 800);
                                            setTimeout(applyTitleStyle, 1000);
                                            // requestAnimationFrame을 사용하여 렌더링 사이클에 맞춰 적용
                                            requestAnimationFrame(function() {
                                                applyTitleStyle();
                                                setTimeout(applyTitleStyle, 50);
                                                setTimeout(applyTitleStyle, 150);
                                                setTimeout(applyTitleStyle, 300);
                                            });
                                        }, true);
                                    }
                                });
                                
                                // 모든 selectbox에 변경 이벤트 리스너 (사용자 선택)
                                const selectboxes = sidebar.querySelectorAll('select, [role="combobox"]');
                                selectboxes.forEach(function(select) {
                                    // 이미 리스너가 추가된 selectbox는 제외 (중복 방지)
                                    if (!select.hasAttribute('data-title-style-listener')) {
                                        select.setAttribute('data-title-style-listener', 'true');
                                        select.addEventListener('change', function() {
                                            setTimeout(applyTitleStyle, 10);
                                            setTimeout(applyTitleStyle, 50);
                                            setTimeout(applyTitleStyle, 100);
                                        }, true);
                                    }
                                });
                            }
                        } catch(e) {}
                    });
                }
                
                // DOM 로드 후 이벤트 리스너 추가
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function() {
                        attachEventListeners();
                    });
                } else {
                    attachEventListeners();
                }
                
                // MutationObserver로 새로 추가된 버튼/selectbox에도 자동으로 리스너 추가
                const contexts = [
                    { doc: window.parent.document, win: window.parent },
                    { doc: document, win: window }
                ];
                
                contexts.forEach(function(ctx) {
                    try {
                        const sidebar = ctx.doc.querySelector('[data-testid="stSidebar"]');
                        if (sidebar) {
                            const observer = new ctx.win.MutationObserver(function(mutations) {
                                // 새로 추가된 버튼/selectbox에 리스너 추가
                                attachEventListeners();
                                // DOM 변경 시 스타일도 재적용 (Streamlit rerun 대응)
                                applyTitleStyle();
                                // 여러 타이밍에 재적용
                                setTimeout(applyTitleStyle, 0);
                                setTimeout(applyTitleStyle, 10);
                                setTimeout(applyTitleStyle, 50);
                            });
                            observer.observe(sidebar, { childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class'] });
                        }
                    } catch(e) {}
                    });
                
                // Streamlit의 rerun 완료 감지 (iframe 내부의 Streamlit 이벤트)
                try {
                    // Streamlit이 완전히 렌더링된 후 스타일 재적용
                    window.addEventListener('load', function() {
                        setTimeout(applyTitleStyle, 100);
                        setTimeout(applyTitleStyle, 300);
                        setTimeout(applyTitleStyle, 500);
                    });
                    
                    // Streamlit의 메시지 이벤트 감지 (rerun 완료 시)
                    if (window.parent && window.parent.postMessage) {
                        window.addEventListener('message', function(event) {
                            if (event.data && event.data.type === 'streamlit:render') {
                                setTimeout(applyTitleStyle, 10);
                                setTimeout(applyTitleStyle, 50);
                                setTimeout(applyTitleStyle, 100);
                            }
                        });
                    }
                } catch(e) {}
            })();
            </script>
            """,
            unsafe_allow_html=True
        )
        
        # 페이지 이동 경고 표시 (메인 콘텐츠 영역)
        render_navigation_warning()
        
        # 페이지 이동 시 스크롤을 최상단으로 이동 (메인 우측 화면)
        if st.session_state.get('scroll_to_top', False):
            st.session_state.scroll_to_top = False
            # 메인 콘텐츠 영역과 전체 페이지 모두 스크롤 초기화
            st.components.v1.html(
                """
                <script>
                    // 메인 콘텐츠 영역 스크롤 초기화
                    const mainContainer = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                    if (mainContainer) {
                        mainContainer.scrollTop = 0;
                    }
                    // 전체 페이지 스크롤 초기화
                    window.parent.scrollTo(0, 0);
                </script>
                """,
                height=0
            )
        
        # 현재 페이지에 따른 메인 콘텐츠 렌더링
        if st.session_state.current_page == "main":
            render_main_page()
        elif st.session_state.current_page == "daily_snippet":
            render_daily_snippet()
        elif st.session_state.current_page == "archive":
            render_archive()
        elif st.session_state.current_page == "idp":
            render_idp()
        elif st.session_state.current_page == "cdp":
            render_cdp()
        elif st.session_state.current_page == "goal_policy":
            render_goal_policy()
        elif st.session_state.current_page == "one_on_one_coaching":
            render_one_on_one_coaching()
        elif st.session_state.current_page == "profile_edit":
            render_profile_edit()
        elif st.session_state.current_page == "google_settings":
            render_google_settings()
        
        # 페이지 렌더링 후 백그라운드 prefetch 실행
        if st.session_state.get('prefetch_pending', False) and st.session_state.logged_in:
            st.session_state.prefetch_pending = False
            # 백그라운드에서 prefetch 실행
            try:
                prefetch_user_data()
                # prefetch 완료 후 전체 캐시 저장
                touch_session_active()
            except Exception:
                # prefetch 실패해도 계속 진행
                pass

if __name__ == "__main__":
    main()
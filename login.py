import streamlit as st
from datetime import datetime
import hashlib
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# 페이지 설정
st.set_page_config(
    page_title="로그인 시스템",
    page_icon="🔐",
    layout="centered"
)

# Google Sheets 연동을 위한 설정
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 사용자 정보 시트 ID
USERS_SPREADSHEET_ID = (
    (st.secrets.get("google", {}).get("users_spreadsheet_id") if hasattr(st, "secrets") else None)
    or "1fHSCgg6_97Z3JzOvrk3ElXQWhOWhVhl5IaITeA9pXmY"
)

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
        
        # 인증 정보가 없는 경우
        st.warning("Google Sheets 연동을 위해 서비스 계정 인증 정보가 필요합니다.")
        return None
        
    except Exception as e:
        st.error(f"Google Sheets 연동 오류: {e}")
        return None

def _digits_only(value: str | int | None) -> str:
    """숫자만 추출"""
    s = str(value or "")
    return "".join(ch for ch in s if ch.isdigit())

def _phones_equal(a: str | None, b: str | None) -> bool:
    """휴대폰번호 비교 (숫자만 추출하여 비교)"""
    da = _digits_only(a).lstrip('0')
    db = _digits_only(b).lstrip('0')
    return bool(da and db and da == db)

def fetch_users_records():
    """사용자 정보 시트의 모든 레코드를 반환합니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return []
        spreadsheet = client.open_by_key(USERS_SPREADSHEET_ID)
        worksheet = spreadsheet.sheet1
        records = worksheet.get_all_records()
        return records
    except Exception as e:
        st.error(f"사용자 데이터 로드 오류: {e}")
        return []

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

def login_user(phone, password):
    """사용자 로그인 검증: 구글시트에서 사용자 확인"""
    return find_user_by_phone_and_password(phone, password)

def main():
    # 세션 상태 초기화
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None

    if not st.session_state.logged_in:
        # 로그인 페이지
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
                    
                    submitted = st.form_submit_button("로그인", use_container_width=True)
                    
                    if submitted:
                        if phone and password:
                            user_info = login_user(phone, password)
                            if user_info:
                                st.session_state.logged_in = True
                                st.session_state.user_info = user_info
                                st.success("로그인 성공!")
                                st.rerun()
                            else:
                                st.error("휴대폰번호 또는 비밀번호가 올바르지 않습니다.")
                        else:
                            st.warning("휴대폰번호와 비밀번호를 모두 입력해주세요.")
        
        # 등록된 계정 정보 표시 (개발용) - Google Sheets에서 조회
        with st.expander("📋 등록된 계정 정보 (개발용)"):
            st.markdown("**등록된 계정 정보 (Google Sheets에서 조회):**")
            try:
                records = fetch_users_records()
                if records:
                    for row in records:
                        phone = str(row.get('휴대폰번호', '')).strip()
                        name = str(row.get('이름(본명)', '')).strip()
                        password = str(row.get('비밀번호', '')).strip()
                        role = str(row.get('권한', 'user')).strip() or 'user'
                        st.write(f"📱 {phone} | 👤 {name} | 🔑 {password} | 👑 {role}")
                else:
                    st.info("등록된 계정 정보가 없습니다.")
            except Exception as e:
                st.warning(f"계정 정보 조회 실패: {e}")
    
    else:
        # 로그인 후 메인 페이지
        user = st.session_state.user_info
        
        # 상단 네비게이션
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("🚪 로그아웃"):
                st.session_state.logged_in = False
                st.session_state.user_info = None
                st.rerun()
        
        with col2:
            st.title(f"안녕하세요, {user['name']}님!")
        
        st.markdown("---")
        
        # 사용자 정보 카드
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 👤 사용자 정보")
            user_phone = user.get('phone', 'N/A')
            st.info(f"""
            **이름:** {user['name']}  
            **휴대폰번호:** {user_phone}  
            **이메일:** {user['email']}  
            **권한:** {user['role']}  
            **등록일:** {user['timestamp']}  
            **표시여부:** {user['display']}
            """)
        
        with col2:
            st.markdown("### 📊 시스템 상태")
            st.success("✅ 로그인 상태: 활성")
            st.info(f"🕐 현재 시간: {datetime.now().strftime('%Y. %m. %d %p %I:%M:%S')}")
            
            if user['role'] == 'admin':
                st.warning("👑 관리자 권한으로 로그인되었습니다.")
        
        # 권한별 기능 표시
        st.markdown("### 🛠️ 사용 가능한 기능")
        
        if user['role'] == 'admin':
            st.markdown("**관리자 기능:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("👥 사용자 관리", use_container_width=True)
            with col2:
                st.button("📊 시스템 통계", use_container_width=True)
            with col3:
                st.button("⚙️ 시스템 설정", use_container_width=True)
        else:
            st.markdown("**일반 사용자 기능:**")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("📝 내 정보 수정", use_container_width=True)
            with col2:
                st.button("📋 내 활동 내역", use_container_width=True)
            with col3:
                st.button("❓ 도움말", use_container_width=True)

if __name__ == "__main__":
    main()

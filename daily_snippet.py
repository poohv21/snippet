import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import streamlit.components.v1 as components

# 페이지 설정
st.set_page_config(
    page_title="Daily Snippet",
    page_icon="📝",
    layout="wide"
)

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

# 사용자 데이터는 Google Sheets에서 조회합니다 (하드코딩 제거됨)

# Google Sheets 연동을 위한 설정
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 스프레드시트 ID
SPREADSHEET_ID = "1THmwStR6p0_SUyLEV6-edT0kigANvTCPOkAzN7NaEQE"

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

def save_to_google_sheets(data):
    """데이터를 Google Sheets에 저장합니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return False
        
        def _append_row():
            spreadsheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.sheet1
            worksheet.append_row(data)
            return True
        
        return _sheets_call_with_retry(_append_row)
    except Exception as e:
        error_msg = str(e).lower()
        if _is_retryable_error(error_msg):
            st.warning("Daily Snippet 저장 중 호출 제한이 발생했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.error(f"Google Sheets 저장 오류: {e}")
        return False

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

def initialize_session_state():
    """세션 상태를 초기화합니다."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    
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

def render_star_rating(label: str, state_key: str, help_text: str | None = None):
    """심플하고 세련된 별점 레이팅 위젯."""
    st.markdown(f"### {label}", unsafe_allow_html=True)
    if help_text:
        st.caption(help_text)
    
    current_value = int(st.session_state.form_data.get(state_key, 0) or 0)
    
    # 별점 버튼 스타일 설정: 테두리 흰색, 중앙 정렬, 간격 최적화
    st.markdown(
        f"""
        <style>
        /* 별점 컬럼들 간격 조정 (20px로 설정하여 충분한 간격 유지) */
        div.row-widget.stHorizontal {{
            display: flex !important;
            justify-content: flex-start !important;
            align-items: center !important;
            gap: 20px !important;
        }}
        /* 각 별점 컬럼 내부 중앙 정렬 및 폭 최소화 */
        div[data-testid="column"] {{
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            padding-left: 0px !important;
            padding-right: 0px !important;
        }}
        /* 별점 버튼이 있는 컬럼만 폭 제한 (여유 공간 더욱 확보) */
        div[data-testid="column"]:nth-child(-n+5) {{
            min-width: 64px !important;
            max-width: 64px !important;
            width: 64px !important;
            flex: 0 0 64px !important;
            padding: 0 8px !important;
        }}
        /* 버튼 중앙 정렬 및 테두리 흰색 강제 적용 */
        button[data-testid*="star_{state_key}"] {{
            width: 38px !important;
            min-width: 38px !important;
            max-width: 38px !important;
            height: 38px !important;
            padding: 4px !important;
            margin: 0 auto !important;
            font-size: 1.3rem !important;
            line-height: 30px !important;
            border-radius: 4px !important;
            border: 1px solid #ffffff !important;
            border-color: #ffffff !important;
            background-color: transparent !important;
            position: relative !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            box-sizing: border-box !important;
        }}
        /* 버튼 내부 모든 요소 중앙 정렬 */
        button[data-testid*="star_{state_key}"] > *,
        button[data-testid*="star_{state_key}"] > span,
        button[data-testid*="star_{state_key}"] > div {{
            margin: 0 !important;
            padding: 0 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            height: 100% !important;
            line-height: 38px !important;
            text-align: center !important;
        }}
        /* 버튼 내부 텍스트 노드 직접 선택하여 중앙 정렬 */
        button[data-testid*="star_{state_key}"] {{
            text-indent: 0 !important;
            letter-spacing: 0 !important;
        }}
        /* 버튼 내부 텍스트 중앙 정렬 */
        button[data-testid*="star_{state_key}"]::before,
        button[data-testid*="star_{state_key}"]::after {{
            display: none !important;
        }}
        /* 모든 컬럼 내부 버튼 중앙 배치 강화 */
        div[data-testid="column"] {{
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 5개의 별을 버튼으로 표시 (컬럼 비율을 더 크게 조정하여 실제 공간 확보)
    cols = st.columns([0.25, 0.25, 0.25, 0.25, 0.25, 3], gap="small")
    selected_rating = current_value
    
    for i in range(5):
        with cols[i]:
            star_value = i + 1
            # 선택된 별은 채워진 별, 그 외는 빈 별
            star_filled = "⭐" if star_value <= current_value else "☆"
            
            if st.button(
                star_filled,
                key=f"star_{state_key}_{star_value}",
                help=f"{star_value}점 선택",
                use_container_width=False
            ):
                selected_rating = star_value
                st.session_state.form_data[state_key] = selected_rating
                st.rerun()
    
    # 선택된 점수 표시 (마지막 열에 표시)
    with cols[5]:
        if current_value > 0:
            stars_display = "⭐" * current_value
            st.markdown(f"**{stars_display}** ({current_value}/5)")
        else:
            st.caption("선택 안 함")

def render_step_1():
    """1단계: Check-in 렌더링"""
    # 스크롤 최상단으로 이동 (메인 우측 화면)
    if st.session_state.get('scroll_to_top', False):
        st.session_state['scroll_to_top'] = False
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
    
    st.header("📊 1단계: Check-in")
    st.markdown("---")
    
    render_star_rating(
        "💪 몸상태 <span style='color: #d32f2f;'>(필수)</span>",
        "physical_state",
        help_text="오늘의 몸상태를 5점 만점으로 평가해주세요"
    )
    
    render_star_rating(
        "😊 마음상태 <span style='color: #d32f2f;'>(필수)</span>",
        "mental_state",
        help_text="오늘의 마음상태를 5점 만점으로 평가해주세요"
    )
    
    st.markdown("### 🤔 상태 이유 <span style='color: #d32f2f;'>(필수)</span>", unsafe_allow_html=True)
    
    # 상태 이유 업데이트 콜백 (입력 필드 변경 시 자동 호출 및 리렌더링)
    def update_state_reason():
        """상태 이유 값이 변경될 때 호출"""
        if 'state_reason_input' in st.session_state:
            st.session_state.form_data['state_reason'] = st.session_state.state_reason_input
            # 값이 변경되면 리렌더링 플래그 설정
            st.session_state['should_rerun'] = True
    
    state_reason = st.text_area(
        "오늘 몸/마음 상태의 이유를 알려주세요",
        value=st.session_state.form_data.get('state_reason', ''),
        placeholder="예: 잠을 잘 못자서 피곤함, 프로젝트가 잘 진행되어서 기분이 좋음 등",
        height=100,
        key="state_reason_input",
        on_change=update_state_reason
    )
    # 세션 상태 즉시 업데이트
    st.session_state.form_data['state_reason'] = state_reason
    
    # 리렌더링 플래그 확인
    if st.session_state.get('should_rerun', False):
        st.session_state['should_rerun'] = False
        st.rerun()
    
    st.subheader("💡 개선 방안")
    improvement_plan = st.text_area(
        "몸/마음 상태를 더 낫게 하기 위한 방안이 있다면 알려주세요 (선택사항)",
        value=st.session_state.form_data.get('improvement_plan', ''),
        placeholder="예: 스트레칭과 차 마시기, 충분한 휴식 등",
        height=100,
        key="improvement_plan_input"
    )
    st.session_state.form_data['improvement_plan'] = improvement_plan
    
    # 다음 단계 버튼 (항상 활성화, 클릭 시 검증)
    if st.button("다음 단계로", type="primary", use_container_width=True):
        # 필수 항목 검증
        missing_fields = []
        if st.session_state.form_data.get('physical_state', 0) == 0:
            missing_fields.append("💪 몸상태")
        if st.session_state.form_data.get('mental_state', 0) == 0:
            missing_fields.append("😊 마음상태")
        if not st.session_state.form_data.get('state_reason', '').strip():
            missing_fields.append("🤔 상태 이유")
        
        if missing_fields:
            # 누락된 항목을 명시적으로 표시
            st.error(f"❌ 다음 필수 항목을 입력해주세요:\n\n" + "\n".join([f"• {field}" for field in missing_fields]))
        else:
            st.session_state.current_step = 2
            st.session_state['scroll_to_top'] = True
            st.rerun()

def render_step_2():
    """2단계: Look-back 렌더링"""
    # 스크롤 최상단으로 이동 (메인 우측 화면)
    if st.session_state.get('scroll_to_top', False):
        st.session_state['scroll_to_top'] = False
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
    
    st.header("🔍 2단계: Look-back")
    st.markdown("---")
    
    st.markdown("### 📋 전일 업무 <span style='color: #d32f2f;'>(필수)</span>", unsafe_allow_html=True)
    
    # 전일 업무 업데이트 콜백
    def update_yesterday_work():
        """전일 업무 값이 변경될 때 호출"""
        if 'yesterday_work_input' in st.session_state:
            st.session_state.form_data['yesterday_work'] = st.session_state.yesterday_work_input
            st.session_state['should_rerun'] = True
    
    yesterday_work = st.text_area(
        "전일(前日)에 완료한 업무는 무엇인가요?",
        value=st.session_state.form_data.get('yesterday_work', ''),
        placeholder="예: * Snippet AI Agent App의 Snippet 입력 및 아카이빙 확인 모듈 개발 완성",
        height=120,
        key="yesterday_work_input",
        on_change=update_yesterday_work
    )
    st.session_state.form_data['yesterday_work'] = yesterday_work
    
    # 리렌더링 플래그 확인
    if st.session_state.get('should_rerun', False):
        st.session_state['should_rerun'] = False
        st.rerun()
    
    # 로그인된 사용자의 이름을 자동으로 설정 (표시하지 않음)
    if st.session_state.logged_in and st.session_state.user_info:
        st.session_state.form_data['name'] = st.session_state.user_info['name']
    
    render_star_rating(
        "⭐ 전일 만족도 <span style='color: #d32f2f;'>(필수)</span>",
        "yesterday_satisfaction",
        help_text="전일 업무에 대한 만족도는?"
    )
    
    st.markdown("### 👍 Liked - 좋았던 점 <span style='color: #d32f2f;'>(필수)</span>", unsafe_allow_html=True)
    
    # 좋았던 점 업데이트 콜백
    def update_liked():
        """좋았던 점 값이 변경될 때 호출"""
        if 'liked_input' in st.session_state:
            st.session_state.form_data['liked'] = st.session_state.liked_input
            st.session_state['should_rerun'] = True
    
    liked = st.text_area(
        "좋았던 점은 무엇인가요?",
        value=st.session_state.form_data.get('liked', ''),
        placeholder="예: Snippet AI Agent App 개발 목표치 달성",
        height=100,
        key="liked_input",
        on_change=update_liked
    )
    st.session_state.form_data['liked'] = liked
    
    st.markdown("### 👎 Lacked - 아쉬웠던 점 <span style='color: #d32f2f;'>(필수)</span>", unsafe_allow_html=True)
    
    # 아쉬웠던 점 업데이트 콜백
    def update_lacked():
        """아쉬웠던 점 값이 변경될 때 호출"""
        if 'lacked_input' in st.session_state:
            st.session_state.form_data['lacked'] = st.session_state.lacked_input
            st.session_state['should_rerun'] = True
    
    lacked = st.text_area(
        "아쉬웠던 점은 무엇인가요?",
        value=st.session_state.form_data.get('lacked', ''),
        placeholder="예: 팀원이 진행하는 1on1 과정에 들러보기로 했는데 가보지 못함",
        height=100,
        key="lacked_input",
        on_change=update_lacked
    )
    st.session_state.form_data['lacked'] = lacked
    
    # 리렌더링 플래그 확인
    if st.session_state.get('should_rerun', False):
        st.session_state['should_rerun'] = False
        st.rerun()
    
    st.subheader("📚 Learned - 배웠던 점 (선택사항)")
    learned = st.text_area(
        "배웠던 점, 성장 포인트는 무엇인가요?",
        value=st.session_state.form_data.get('learned', ''),
        placeholder="예: 구글 AI Studio와 구글시트 구글폼, Apps Script 연동 방법을 배움",
        height=100
    )
    st.session_state.form_data['learned'] = learned
    
    st.subheader("🔮 Looked Forward - 향후 시도해보고 싶은 것 (선택사항)")
    looked_forward = st.text_area(
        "향후 시도해 보고 싶은 것은 무엇인가요?",
        value=st.session_state.form_data.get('looked_forward', ''),
        placeholder="예: Snippet 고도화",
        height=100
    )
    st.session_state.form_data['looked_forward'] = looked_forward
    
    st.subheader("🤝 Longed For - 팀과 리더에게 바라는 점 (선택사항)")
    longed_for = st.text_area(
        "팀과 리더에게 바라는 점, 요청사항이 있나요?",
        value=st.session_state.form_data.get('longed_for', ''),
        placeholder="예: 정기적인 1on1 시행이 필요",
        height=100
    )
    st.session_state.form_data['longed_for'] = longed_for
    
    st.subheader("👏 동료 칭찬 (선택사항)")
    colleague_praise = st.text_area(
        "동료의 이런 점을 칭찬합니다",
        value=st.session_state.form_data.get('colleague_praise', ''),
        placeholder="예: 홍길동님의 오너십을 칭찬함",
        height=100
    )
    st.session_state.form_data['colleague_praise'] = colleague_praise
    
    # 이전/다음 단계 버튼
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("이전 단계", use_container_width=True):
            st.session_state.current_step = 1
            st.session_state['scroll_to_top'] = True
            st.rerun()
    
    with col2:
        # 다음 단계 버튼 (항상 활성화, 클릭 시 검증)
        if st.button("다음 단계로", type="primary", use_container_width=True):
            # 필수 항목 검증
            missing_fields = []
            if not st.session_state.form_data.get('yesterday_work', '').strip():
                missing_fields.append("📋 전일 업무")
            if st.session_state.form_data.get('yesterday_satisfaction', 0) == 0:
                missing_fields.append("⭐ 전일 만족도")
            if not st.session_state.form_data.get('liked', '').strip():
                missing_fields.append("👍 좋았던 점")
            if not st.session_state.form_data.get('lacked', '').strip():
                missing_fields.append("👎 아쉬웠던 점")
            # 이름 체크 (로그인되지 않은 경우만)
            if not st.session_state.logged_in or not st.session_state.user_info:
                if not st.session_state.form_data.get('name', '').strip():
                    missing_fields.append("👥 이름")
            
            if missing_fields:
                # 누락된 항목을 명시적으로 표시
                st.error(f"❌ 다음 필수 항목을 입력해주세요:\n\n" + "\n".join([f"• {field}" for field in missing_fields]))
            else:
                st.session_state.current_step = 3
                st.session_state['scroll_to_top'] = True
                st.rerun()

def render_step_3():
    """3단계: Today's Plans 렌더링"""
    # 스크롤 최상단으로 이동 (메인 우측 화면)
    if st.session_state.get('scroll_to_top', False):
        st.session_state['scroll_to_top'] = False
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
    
    st.header("📅 3단계: Today's Plans")
    st.markdown("---")
    
    st.markdown("### 📝 오늘 할 일 <span style='color: #d32f2f;'>(필수)</span>", unsafe_allow_html=True)
    
    # 오늘 할 일 업데이트 콜백
    def update_today_plans():
        """오늘 할 일 값이 변경될 때 호출"""
        if 'today_plans_input' in st.session_state:
            st.session_state.form_data['today_plans'] = st.session_state.today_plans_input
            st.session_state['should_rerun'] = True
    
    today_plans = st.text_area(
        "오늘 할 일의 목록은 무엇인가요?",
        value=st.session_state.form_data.get('today_plans', ''),
        placeholder="""예: 
* Snippet AI Agent 앱 추가 모듈 기획
* 1on1 과정 둘러보기  
* Weekly 자료 작성""",
        height=150,
        key="today_plans_input",
        on_change=update_today_plans
    )
    st.session_state.form_data['today_plans'] = today_plans
    
    # 리렌더링 플래그 확인
    if st.session_state.get('should_rerun', False):
        st.session_state['should_rerun'] = False
        st.rerun()
    
    # 이전 단계 버튼
    if st.button("이전 단계", use_container_width=True):
        st.session_state.current_step = 2
        st.session_state['scroll_to_top'] = True
        st.rerun()
    
    # 전송 중이면 자동으로 저장 처리
    is_saving = st.session_state.get("saving_snippet", False)
    if is_saving:
        save_data()
    
    # 전송하기 버튼 (항상 활성화, 클릭 시 검증 및 즉시 비활성화)
    if st.button(
        "📤 전송하기" if not is_saving else "📤 전송 중...",
        type="primary",
        use_container_width=True,
        disabled=is_saving
    ):
        if not is_saving:
            # 필수 항목 검증
            today_plans_value = st.session_state.form_data.get('today_plans', '')
            if not today_plans_value.strip():
                st.error("❌ 다음 필수 항목을 입력해주세요:\n\n• 📝 오늘 할 일")
            else:
                # 즉시 버튼 비활성화 및 저장 시작
                st.session_state.saving_snippet = True
                st.rerun()

def save_data():
    """데이터를 저장합니다."""
    try:
        # 현재 시간 생성 (서울 시간 기준)
        kst = timezone(timedelta(hours=9))
        now = datetime.now(kst)
        timestamp = now.strftime("%Y. %m. %d %p %I:%M:%S").replace("AM", "오전").replace("PM", "오후")
        
        # 데이터 준비
        data = [
            timestamp,
            st.session_state.form_data['name'],
            st.session_state.form_data['physical_state'],
            st.session_state.form_data['mental_state'],
            st.session_state.form_data['state_reason'],
            st.session_state.form_data['improvement_plan'],
            st.session_state.form_data['yesterday_work'],
            st.session_state.form_data['yesterday_satisfaction'],
            st.session_state.form_data['liked'],
            st.session_state.form_data['lacked'],
            st.session_state.form_data['learned'],
            st.session_state.form_data['looked_forward'],
            st.session_state.form_data['longed_for'],
            st.session_state.form_data['colleague_praise'],
            st.session_state.form_data['today_plans']
        ]
        
        # Google Sheets에 저장
        if save_to_google_sheets(data):
            st.success("✅ Daily Snippet이 성공적으로 저장되었습니다!")
            
            # 폼 초기화
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
            
            # 아카이브 페이지로 이동 (사이드바 메뉴 효과)
            st.session_state.current_page = "archive"
            st.rerun()
        else:
            st.error("❌ 저장 중 오류가 발생했습니다. 다시 시도해주세요.")
            st.session_state.saving_snippet = False
    except Exception as e:
        st.error(f"❌ 저장 중 오류가 발생했습니다: {e}")
        st.session_state.saving_snippet = False

def render_login():
    """로그인 화면 렌더링"""
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
    
    st.title("🔐 Daily Snippet 로그인")
    st.markdown("Daily Snippet을 사용하려면 먼저 로그인해주세요.")
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
    
    # 등록된 계정 정보 표시 제거 (Google Sheets에서 관리됨)

def save_data_embedded(save_data_callback=None):
    """임베드 모드에서 데이터를 저장합니다. 외부 저장 함수를 사용합니다."""
    try:
        # 현재 시간 생성 (서울 시간 기준)
        kst = timezone(timedelta(hours=9))
        now = datetime.now(kst)
        timestamp = now.strftime("%Y. %m. %d %p %I:%M:%S").replace("AM", "오전").replace("PM", "오후")
        
        # 데이터 준비
        data = [
            timestamp,
            st.session_state.form_data['name'],
            st.session_state.form_data['physical_state'],
            st.session_state.form_data['mental_state'],
            st.session_state.form_data['state_reason'],
            st.session_state.form_data['improvement_plan'],
            st.session_state.form_data['yesterday_work'],
            st.session_state.form_data['yesterday_satisfaction'],
            st.session_state.form_data['liked'],
            st.session_state.form_data['lacked'],
            st.session_state.form_data['learned'],
            st.session_state.form_data['looked_forward'],
            st.session_state.form_data['longed_for'],
            st.session_state.form_data['colleague_praise'],
            st.session_state.form_data['today_plans']
        ]
        
        # 외부 저장 함수 사용
        if save_data_callback:
            if save_data_callback(data):
                st.success("✅ Daily Snippet이 성공적으로 저장되었습니다!")
                # 폼 초기화
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
                
                # 아카이브 페이지로 이동 (사이드바 메뉴 효과)
                st.session_state.current_page = "archive"
                st.rerun()
            else:
                st.error("❌ 저장 중 오류가 발생했습니다. 다시 시도해주세요.")
                st.session_state.saving_snippet = False
        else:
            # 기본 저장 함수 사용
            if save_to_google_sheets(data):
                st.success("✅ Daily Snippet이 성공적으로 저장되었습니다!")
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
                
                # 아카이브 페이지로 이동 (사이드바 메뉴 효과)
                st.session_state.current_page = "archive"
                st.rerun()
            else:
                st.error("❌ 저장 중 오류가 발생했습니다. 다시 시도해주세요.")
                st.session_state.saving_snippet = False
    except Exception as e:
        st.error(f"❌ 저장 중 오류가 발생했습니다: {e}")
        st.session_state.saving_snippet = False

def render_daily_snippet_embedded(save_data_callback=None):
    """Daily Snippet 임베드 모드 렌더링 (main.py에서 사용)"""
    # 페이지 진입 또는 단계 전환 시 스크롤 최상단으로 이동 (메인 우측 화면)
    if st.session_state.get('scroll_to_top', False):
        st.session_state['scroll_to_top'] = False
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
    
    # 진행 상황 표시
    progress = st.session_state.current_step / 3
    st.progress(progress)
    st.caption(f"진행률: {st.session_state.current_step}/3 단계")
    
    # 단계별 렌더링
    if st.session_state.current_step == 1:
        render_step_1_embedded()
    elif st.session_state.current_step == 2:
        render_step_2_embedded()
    elif st.session_state.current_step == 3:
        render_step_3_embedded(save_data_callback)

def render_step_1_embedded():
    """1단계: Check-in 렌더링 (임베드 모드)"""
    render_step_1()

def render_step_2_embedded():
    """2단계: Look-back 렌더링 (임베드 모드)"""
    render_step_2()

def render_step_3_embedded(save_data_callback=None):
    """3단계: Today's Plans 렌더링 (임베드 모드)"""
    render_step_3_with_callback(save_data_callback)

def render_step_3_with_callback(save_data_callback=None):
    """3단계: Today's Plans 렌더링 (저장 콜백 포함)"""
    # 스크롤 최상단으로 이동 (메인 우측 화면)
    if st.session_state.get('scroll_to_top', False):
        st.session_state['scroll_to_top'] = False
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
    
    st.header("📅 3단계: Today's Plans")
    st.markdown("---")
    
    st.markdown("### 📝 오늘 할 일 <span style='color: #d32f2f;'>(필수)</span>", unsafe_allow_html=True)
    
    # 오늘 할 일 업데이트 콜백
    def update_today_plans_embedded():
        """오늘 할 일 값이 변경될 때 호출 (임베드 모드)"""
        if 'today_plans_input_embedded' in st.session_state:
            st.session_state.form_data['today_plans'] = st.session_state.today_plans_input_embedded
            st.session_state['should_rerun'] = True
    
    today_plans = st.text_area(
        "오늘 할 일의 목록은 무엇인가요?",
        value=st.session_state.form_data.get('today_plans', ''),
        placeholder="""예: 
* Snippet AI Agent 앱 추가 모듈 기획
* 1on1 과정 둘러보기  
* Weekly 자료 작성""",
        height=150,
        key="today_plans_input_embedded",
        on_change=update_today_plans_embedded
    )
    st.session_state.form_data['today_plans'] = today_plans
    
    # 리렌더링 플래그 확인
    if st.session_state.get('should_rerun', False):
        st.session_state['should_rerun'] = False
        st.rerun()
    
    # 이전 단계 버튼
    if st.button("이전 단계", use_container_width=True):
        st.session_state.current_step = 2
        st.session_state['scroll_to_top'] = True
        st.rerun()
    
    # 전송 중이면 자동으로 저장 처리
    is_saving = st.session_state.get("saving_snippet", False)
    if is_saving:
        save_data_embedded(save_data_callback)
    
    # 전송하기 버튼 (항상 활성화, 클릭 시 검증 및 즉시 비활성화)
    if st.button(
        "📤 전송하기" if not is_saving else "📤 전송 중...",
        type="primary",
        use_container_width=True,
        disabled=is_saving
    ):
        if not is_saving:
            # 필수 항목 검증
            today_plans_value = st.session_state.form_data.get('today_plans', '')
            if not today_plans_value.strip():
                st.error("❌ 다음 필수 항목을 입력해주세요:\n\n• 📝 오늘 할 일")
            else:
                # 즉시 버튼 비활성화 및 저장 시작
                st.session_state.saving_snippet = True
                st.rerun()

def render_daily_snippet():
    """Daily Snippet 메인 화면 렌더링 (독립 실행 모드)"""
    # 헤더
    st.title("📝 Daily Snippet")
    st.markdown("매일의 상태와 업무를 기록하고 팀과 공유해보세요!")
    
    # 로그인된 사용자 정보 표시
    if st.session_state.logged_in and st.session_state.user_info:
        user = st.session_state.user_info
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("🚪 로그아웃"):
                st.session_state.logged_in = False
                st.session_state.user_info = None
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
                st.rerun()
        with col2:
            st.info(f"안녕하세요, **{user['name']}**님! 오늘도 좋은 하루 되세요! 😊")
    
    # 진행 상황 표시
    progress = st.session_state.current_step / 3
    st.progress(progress)
    st.caption(f"진행률: {st.session_state.current_step}/3 단계")
    
    # 단계별 렌더링
    if st.session_state.current_step == 1:
        render_step_1()
    elif st.session_state.current_step == 2:
        render_step_2()
    elif st.session_state.current_step == 3:
        render_step_3()
    
    # 사이드바에 현재 입력된 데이터 미리보기
    with st.sidebar:
        st.header("📋 입력 미리보기")
        st.markdown("---")
        
        if st.session_state.form_data['name']:
            st.write(f"**이름:** {st.session_state.form_data['name']}")
        
        if st.session_state.form_data['physical_state'] > 0:
            st.write(f"**몸상태:** {st.session_state.form_data['physical_state']}점")
        
        if st.session_state.form_data['mental_state'] > 0:
            st.write(f"**마음상태:** {st.session_state.form_data['mental_state']}점")
        
        if st.session_state.form_data['state_reason']:
            st.write(f"**상태이유:** {st.session_state.form_data['state_reason'][:50]}...")
        
        if st.session_state.form_data['yesterday_work']:
            st.write(f"**전일업무:** {st.session_state.form_data['yesterday_work'][:50]}...")
        
        if st.session_state.form_data['yesterday_satisfaction'] > 0:
            st.write(f"**전일만족도:** {st.session_state.form_data['yesterday_satisfaction']}점")

def main():
    """메인 함수"""
    # 세션 상태 초기화
    initialize_session_state()
    
    # 로그인 상태 확인
    if not st.session_state.logged_in:
        render_login()
    else:
        render_daily_snippet()

if __name__ == "__main__":
    main()

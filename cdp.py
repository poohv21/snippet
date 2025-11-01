import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import pandas as pd

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
    
    /* 비활성화된 버튼 스타일 */
    .stButton > button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# CDP 전용 스프레드시트 ID (우선순위: secrets > 기본값)
CDP_SPREADSHEET_ID = (
    (st.secrets.get("google", {}).get("cdp_spreadsheet_id") if hasattr(st, "secrets") else None)
    or (st.secrets.get("CDP_SPREADSHEET_ID") if hasattr(st, "secrets") else None)
    or "15eTye2j0QiwR6LbgseLhF_9hLxfW3GxVCJcdUUGWgLk"
)

SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_google_sheets_client():
    """CDP용 Google Sheets 클라이언트를 생성합니다.
    main.py의 방식과 동일한 우선순위를 따릅니다.
    """
    try:
        # 0) Streamlit secrets
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

        # 1) Streamlit secrets에서 직접 읽기 (추가 위치 확인)
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

        # 2) 로컬 파일
        service_account_file = "service_account.json"
        if os.path.exists(service_account_file):
            creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPE)
            return gspread.authorize(creds)

        # 3) 세션 상태
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
    except Exception as e:
        st.error(f"Google Sheets 연동 오류: {e}")
        return None


def _fetch_cdp_dataframe() -> pd.DataFrame | None:
    """CDP 구글시트에서 전체 데이터를 DataFrame으로 반환합니다."""
    try:
        client = _get_google_sheets_client()
        if not client:
            return None
        spreadsheet = client.open_by_key(CDP_SPREADSHEET_ID)
        # 첫 번째 시트 사용 (Sheet1)
        worksheet = spreadsheet.sheet1
        records = worksheet.get_all_records()
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"CDP 데이터 가져오기 오류: {e}")
        return None


def render_cdp_embedded():
    """메인 앱 내에서 임베디드 형태로 CDP 화면을 렌더링합니다."""
    # 로그인 확인
    if not st.session_state.get("logged_in") or not st.session_state.get("user_info"):
        st.warning("로그인이 필요합니다.")
        return

    user_name = st.session_state.user_info.get("name")

    with st.spinner("CDP 데이터를 불러오는 중..."):
        df = _fetch_cdp_dataframe()

    if df is None:
        st.warning("CDP 데이터를 불러올 수 없습니다. Google Sheets 연동을 확인해주세요.")
        return

    if df.empty:
        st.info("시트에 데이터가 없습니다.")
        return

    # 열 이름 정규화 (가능한 오타/공백 방지)
    normalized = {c.strip(): c for c in df.columns}
    name_col = normalized.get("이름") or normalized.get("name") or list(df.columns)[0]
    long_col = normalized.get("중장기계획")
    this_col = normalized.get("올해계획")
    next_col = normalized.get("내년계획")

    # 사용자 행 필터링
    user_rows = df[df[name_col] == user_name]
    if user_rows.empty:
        st.info(f"사용자 '{user_name}'에 해당하는 CDP 정보가 없습니다.")
        return

    row = user_rows.iloc[0]
    long_plan = (row.get(long_col) if long_col in row else "") or "(입력 없음)"
    this_plan = (row.get(this_col) if this_col in row else "") or "(입력 없음)"
    next_plan = (row.get(next_col) if next_col in row else "") or "(입력 없음)"

    # 헤더
    st.subheader(f"{user_name} 님의 CDP")

    # 세로로 배열된 카드 스타일 출력
    st.markdown("**🧭 중장기 계획**")
    st.info(long_plan)
    
    st.markdown("")
    st.markdown("**📅 올해 계획**")
    st.success(this_plan)
    
    st.markdown("")
    st.markdown("**🗓️ 내년 계획**")
    st.warning(next_plan)
    
    st.markdown("---")
    
    # 수정 모드가 아닐 때만 수정하기 버튼 표시
    if not st.session_state.get("cdp_edit_mode", False):
        is_processing = st.session_state.get("cdp_saving", False)
        if st.button(
            "✏️ 수정하기",
            use_container_width=True,
            type="primary",
            disabled=is_processing
        ):
            if not is_processing:
                st.session_state.cdp_edit_mode = True
                st.rerun()
    
    # 수정 모드
    if st.session_state.get("cdp_edit_mode", False):
        st.markdown("### 📝 CDP 수정")
        
        # 저장 중 상태 확인 (폼 밖에서 확인)
        is_saving = st.session_state.get("cdp_saving", False)
        
        # 저장 중일 때 안내 메시지 표시
        if is_saving:
            st.info("⏳ CDP 정보를 저장하는 중입니다. 잠시만 기다려주세요...")
        
        # 저장 중 상태가 True이고 저장할 데이터가 세션 상태에 있는 경우 실제 저장 수행
        if is_saving and "cdp_pending_data" in st.session_state:
            pending_data = st.session_state["cdp_pending_data"]
            edited_long_plan = pending_data.get("long_plan", "")
            edited_this_plan = pending_data.get("this_plan", "")
            edited_next_plan = pending_data.get("next_plan", "")
            
            try:
                with st.spinner("CDP 정보를 저장하는 중..."):
                    client = _get_google_sheets_client()
                    if not client:
                        st.error("Google Sheets 연동을 확인해주세요.")
                        st.session_state.cdp_saving = False
                        if "cdp_pending_data" in st.session_state:
                            del st.session_state["cdp_pending_data"]
                    else:
                        spreadsheet = client.open_by_key(CDP_SPREADSHEET_ID)
                        worksheet = spreadsheet.sheet1
                        
                        # 헤더 행 가져오기
                        headers = worksheet.row_values(1)
                        name_idx = None
                        long_idx = None
                        this_idx = None
                        next_idx = None
                        
                        # 컬럼명 정규화 (공백 제거)
                        name_col_stripped = name_col.strip() if name_col else ""
                        long_col_stripped = long_col.strip() if long_col else ""
                        this_col_stripped = this_col.strip() if this_col else ""
                        next_col_stripped = next_col.strip() if next_col else ""
                        
                        for i, header in enumerate(headers, start=1):
                            header_stripped = header.strip() if header else ""
                            if header_stripped == name_col_stripped or header_stripped == name_col:
                                name_idx = i
                            elif header_stripped == long_col_stripped or header_stripped == long_col:
                                long_idx = i
                            elif header_stripped == this_col_stripped or header_stripped == this_col:
                                this_idx = i
                            elif header_stripped == next_col_stripped or header_stripped == next_col:
                                next_idx = i
                        
                        # 사용자 행 찾기
                        all_values = worksheet.get_all_values()
                        user_row_idx = None
                        for idx, row_values in enumerate(all_values[1:], start=2):  # 헤더 제외하고 2부터 시작
                            if len(row_values) > name_idx - 1 and row_values[name_idx - 1] == user_name:
                                user_row_idx = idx
                                break
                        
                        if user_row_idx is None:
                            st.error("사용자 행을 찾을 수 없습니다.")
                            st.session_state.cdp_saving = False
                            if "cdp_pending_data" in st.session_state:
                                del st.session_state["cdp_pending_data"]
                        else:
                            # 값 업데이트
                            if long_idx:
                                worksheet.update_cell(user_row_idx, long_idx, edited_long_plan)
                            if this_idx:
                                worksheet.update_cell(user_row_idx, this_idx, edited_this_plan)
                            if next_idx:
                                worksheet.update_cell(user_row_idx, next_idx, edited_next_plan)
                            
                            # 저장 성공 시 CDP 캐시 갱신
                            try:
                                user_name = st.session_state.user_info.get('name') if st.session_state.get('user_info') else None
                                if user_name:
                                    # prefetch_cache 초기화
                                    if 'prefetch_cache' not in st.session_state:
                                        st.session_state.prefetch_cache = {}
                                    
                                    # 최신 CDP 데이터 가져오기
                                    cdp_df = _fetch_cdp_dataframe()
                                    if cdp_df is not None and not cdp_df.empty:
                                        # 사용자 데이터만 필터링
                                        normalized = {c.strip(): c for c in cdp_df.columns}
                                        name_col = normalized.get("이름") or normalized.get("name") or list(cdp_df.columns)[0]
                                        user_cdp = cdp_df[cdp_df[name_col] == user_name]
                                        st.session_state.prefetch_cache['cdp'] = user_cdp.to_dict('records') if not user_cdp.empty else []
                                    else:
                                        st.session_state.prefetch_cache['cdp'] = []
                                    
                                    # 캐시 파일에 저장 (main.py의 touch_session_active 함수 사용 시도)
                                    try:
                                        if hasattr(st.session_state, 'last_active'):
                                            # main.py의 구조를 참고하여 캐시 갱신
                                            import json
                                            import os
                                            from datetime import datetime
                                            
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
                                                    cache_data['prefetch_timestamp'] = datetime.utcnow().isoformat()
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
                            
                            st.success("CDP 정보가 성공적으로 업데이트되었습니다!")
                            st.session_state.cdp_saving = False
                            st.session_state.cdp_edit_mode = False
                            if "cdp_pending_data" in st.session_state:
                                del st.session_state["cdp_pending_data"]
                            st.rerun()
            except Exception as e:
                st.error(f"업데이트 중 오류가 발생했습니다: {e}")
                st.session_state.cdp_saving = False
                if "cdp_pending_data" in st.session_state:
                    del st.session_state["cdp_pending_data"]
        
        with st.form("cdp_edit_form"):
            # 세션 상태에서 저장할 값이 있으면 그것을 사용, 없으면 원래 값 사용
            default_long = st.session_state.get("cdp_pending_data", {}).get("long_plan") if st.session_state.get("cdp_pending_data") else (long_plan if long_plan != "(입력 없음)" else "")
            default_this = st.session_state.get("cdp_pending_data", {}).get("this_plan") if st.session_state.get("cdp_pending_data") else (this_plan if this_plan != "(입력 없음)" else "")
            default_next = st.session_state.get("cdp_pending_data", {}).get("next_plan") if st.session_state.get("cdp_pending_data") else (next_plan if next_plan != "(입력 없음)" else "")
            
            edited_long_plan = st.text_area(
                "🧭 중장기 계획",
                value=default_long,
                height=300,
                disabled=is_saving
            )
            edited_this_plan = st.text_area(
                "📅 올해 계획",
                value=default_this,
                height=300,
                disabled=is_saving
            )
            edited_next_plan = st.text_area(
                "🗓️ 내년 계획",
                value=default_next,
                height=300,
                disabled=is_saving
            )
            
            col1, col2 = st.columns(2)
            with col1:
                # 저장 버튼 - form_submit_button만 사용
                # 저장 중 상태일 때는 무조건 비활성화
                save_clicked = st.form_submit_button(
                    "💾 저장 중..." if is_saving else "💾 저장하기",
                    use_container_width=True,
                    type="primary",
                    disabled=is_saving
                )
                
                if save_clicked:
                    # 중복 클릭 방지: 이미 저장 중이면 바로 리턴
                    if is_saving:
                        st.warning("이미 저장 중입니다. 잠시만 기다려주세요.")
                        st.stop()
                    
                    # 폼 값을 세션 상태에 저장
                    st.session_state["cdp_pending_data"] = {
                        "long_plan": edited_long_plan,
                        "this_plan": edited_this_plan,
                        "next_plan": edited_next_plan
                    }
                    
                    # 저장 시작 - 상태를 즉시 설정하여 버튼 비활성화
                    st.session_state.cdp_saving = True
                    # 즉시 rerun하여 버튼 비활성화 상태로 화면 업데이트
                    st.rerun()
            
            with col2:
                # 취소 버튼 - form_submit_button만 사용
                if st.form_submit_button(
                    "❌ 취소",
                    use_container_width=True,
                    disabled=is_saving
                ):
                    if not is_saving:
                        st.session_state.cdp_edit_mode = False
                        st.session_state.cdp_saving = False
                        st.rerun()







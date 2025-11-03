import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os

# 메인 컨텐츠 최대 너비 제한 및 아코디언 스타일
st.markdown(
    """
    <style>
    .main .block-container {
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* 아코디언 카드 스타일 - 레벨 1 (최상위) */
    .level1-accordion {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border-radius: 8px;
        margin-bottom: 12px;
        border: 1px solid #90CAF9;
    }
    
    .level1-accordion-header {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        padding: 14px 16px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: pointer;
        font-weight: 600;
        color: #1976D2;
    }
    
    /* 레벨 2 아코디언 스타일 */
    .level2-accordion {
        background: white;
        border-radius: 6px;
        margin: 8px 0;
        padding: 8px;
        border-left: 3px solid #2196F3;
    }
    
    .level2-accordion-header {
        padding: 10px 12px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        cursor: pointer;
        font-weight: 500;
        color: #1976D2;
        background: #F5F5F5;
    }
    
    /* 레벨 3 콘텐츠 스타일 */
    .level3-content {
        padding: 12px 16px;
        margin: 8px 0;
        background: white;
        border-radius: 4px;
        border-left: 2px solid #64B5F6;
    }
    
    .level3-content h4 {
        color: #424242;
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .level3-content ul {
        margin-left: 20px;
        color: #616161;
    }
    
    .level3-content li {
        margin-bottom: 4px;
    }
    
    /* 아이콘 스타일 */
    .accordion-icon {
        margin-right: 8px;
        font-size: 1.1em;
    }
    
    /* 체브론 아이콘 */
    .chevron {
        transition: transform 0.3s ease;
        font-size: 0.9em;
    }
    
    .chevron.expanded {
        transform: rotate(180deg);
    }
    
    /* 레벨별 폰트 색상 스타일 */
    .level1-heading {
        color: #1976D2; /* 파란색 - 레벨 1 */
    }
    
    .level2-heading {
        color: #388E3C; /* 초록색 - 레벨 2 */
    }
    
    .level3-heading {
        color: #F57C00; /* 주황색 - 레벨 3 */
    }
    
    .level4-heading {
        color: #7B1FA2; /* 보라색 - 레벨 4 */
    }
    
    .level4-content {
        color: #616161; /* 회색 - 레벨 4 콘텐츠 */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Google Sheets 연동을 위한 설정
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 스프레드시트 ID들
MISSION_KPI_SHEET_ID = "16RmpF16SylJQe-ThbzA6C8KXzxtAWFDDSbb5mLWqUGI"
GROUND_RULE_SHEET_ID = "1Bnur8Syu92y9aC-9gsEhA7Y97yFiqnnvR-OiODo8Vow"

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

def get_sheet_data(sheet_id, sheet_name=None):
    """Google Sheets에서 데이터를 가져옵니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        
        def _fetch_data():
            spreadsheet = client.open_by_key(sheet_id)
            if sheet_name:
                worksheet = spreadsheet.worksheet(sheet_name)
            else:
                worksheet = spreadsheet.sheet1
            records = worksheet.get_all_records()
            return pd.DataFrame(records)
        
        return _sheets_call_with_retry(_fetch_data)
    except Exception as e:
        error_msg = str(e).lower()
        if _is_retryable_error(error_msg):
            st.warning("조직 데이터 로드 중 호출 제한이 발생했습니다. 잠시 후 다시 시도해주세요.")
        else:
            st.error(f"Google Sheets 데이터 가져오기 오류: {e}")
        return None

def _filter_dataframe(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    if not keyword:
        return df
    keyword_lower = keyword.lower()
    mask = pd.Series([False] * len(df))
    for col in df.columns:
        mask = mask | df[col].astype(str).str.lower().str.contains(keyword_lower, na=False)
    return df[mask]

def _format_text_with_bullets(text):
    """텍스트를 불릿 포인트나 번호 목록으로 포맷팅"""
    if pd.isna(text) or str(text).strip() == "":
        return ""
    
    text_str = str(text).strip()
    
    # 번호 목록 처리 (1., 2., 등으로 시작)
    lines = text_str.split('\n')
    formatted_lines = []
    for line in lines:
        line = line.strip()
        if line:
            # 번호 목록 감지
            if line and (line[0].isdigit() or (len(line) > 1 and line[0].isdigit() and line[1] in ['.', ')', '、'])):
                formatted_lines.append(line)
            # 불릿 포인트 감지
            elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                formatted_lines.append(line)
            else:
                formatted_lines.append(f"• {line}")
    
    return '\n'.join(formatted_lines)

def _render_accordion_level3(title, content):
    """레벨 3 콘텐츠 렌더링 (### 미션, ### KPI 등)"""
    if pd.isna(content) or str(content).strip() == "":
        return
    
    content_str = str(content).strip()
    
    # 제목 표시 (레벨 3) - 주황색 적용, '#' 기호 제거
    st.markdown(f'<h3 style="color: #F57C00; font-weight: 600;">{title}</h3>', unsafe_allow_html=True)
    
    # 줄바꿈을 처리하여 목록으로 표시
    lines = content_str.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 번호 목록 감지 (1., 2., 3. 등)
        if len(line) > 2 and line[0].isdigit() and line[1] in ['.', ')', '、']:
            formatted_lines.append(line)
        # 하이픈이나 불릿으로 시작하는 경우
        elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
            formatted_lines.append(line)
        # 콜론으로 끝나는 경우 (제목처럼 보임)
        elif line.endswith(':'):
            formatted_lines.append(f"**{line}**")
        # 일반 텍스트는 불릿 포인트로 변환
        else:
            formatted_lines.append(f"• {line}")
    
    # 포맷팅된 줄들을 표시
    for line in formatted_lines:
        st.markdown(line)

def _render_detail_principle(content):
    """세부원칙을 텍스트로 직접 표시 (접이식 없이)"""
    if pd.isna(content) or str(content).strip() == "":
        return
    
    content_str = str(content).strip()
    
    # 제목 표시 (레벨 4) - 보라색 적용, '#' 기호 제거
    st.markdown(f'<h4 style="color: #7B1FA2; font-weight: 600;">세부원칙</h4>', unsafe_allow_html=True)
    
    # 줄바꿈을 처리하여 목록으로 표시 (회색 텍스트)
    lines = content_str.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # '-'로 시작하는 경우: 상위 레벨, Bold체로 진하게 표시
        if line.startswith('-'):
            # '-' 제거하고 내용만 가져오기
            content_line = line[1:].strip()
            formatted_lines.append(f'<div style="color: #616161; font-weight: bold; margin-left: 0px;"><strong>• {content_line}</strong></div>')
        # '. '로 시작하는 경우: 하위 레벨
        elif line.startswith('. '):
            # '. ' 제거하고 내용만 가져오기
            content_line = line[2:].strip()
            formatted_lines.append(f'<div style="color: #616161; margin-left: 20px;">  • {content_line}</div>')
        # 번호 목록 감지 (1., 2., 3. 등)
        elif len(line) > 2 and line[0].isdigit() and line[1] in ['.', ')', '、']:
            formatted_lines.append(f'<div style="color: #616161;">{line}</div>')
        # 기존 불릿으로 시작하는 경우
        elif line.startswith('•') or line.startswith('*'):
            formatted_lines.append(f'<div style="color: #616161;">{line}</div>')
        # 콜론으로 끝나는 경우 (제목처럼 보임)
        elif line.endswith(':'):
            formatted_lines.append(f'<div style="color: #616161;"><strong>{line}</strong></div>')
        # 일반 텍스트는 불릿 포인트로 변환
        else:
            formatted_lines.append(f'<div style="color: #616161;">• {line}</div>')
    
    # 포맷팅된 줄들을 표시
    for line in formatted_lines:
        st.markdown(line, unsafe_allow_html=True)
    
def _get_organization_name(row_data, title_fields):
    """조직명을 추출합니다 (레벨 2용)"""
    for field in title_fields:
        if field in row_data and pd.notna(row_data.get(field)) and str(row_data.get(field)).strip():
            return str(row_data.get(field)).strip()
    return None

def _render_mission_kpi_organization(group_name, group_data):
    """Mission & KPI의 조직별 렌더링 (레벨 2: ## 조직명)"""
    with st.expander(group_name, expanded=False):
        # 레벨 2 헤딩 표시 - 초록색 적용, '#' 기호 제거
        st.markdown(f'<h2 style="color: #388E3C; font-weight: 600;">{group_name}</h2>', unsafe_allow_html=True)
        
        for idx, row in group_data.iterrows():
            # Mission 필드 찾기
            mission_content = None
            for col in row.index:
                if col.lower() in ['mission', '미션'] and pd.notna(row.get(col)):
                    mission_content = row.get(col)
                    break
            
            # KPI 필드 찾기
            kpi_content = None
            for col in row.index:
                if col.upper() == 'KPI' and pd.notna(row.get(col)):
                    kpi_content = row.get(col)
                    break
            
            # Mission과 KPI가 모두 없으면 스킵
            if not mission_content and not kpi_content:
                continue
            
            # Mission 표시 (레벨 3: ### 미션)
            if mission_content:
                _render_accordion_level3("미션", mission_content)
                st.markdown("")
            
            # KPI 표시 (레벨 3: ### KPI)
            if kpi_content:
                _render_accordion_level3("KPI", kpi_content)
                st.markdown("")
            
            # 항목 사이 구분선
            if idx < len(group_data) - 1:
                st.markdown("---")

def _render_ground_rule_category(category_name, category_data):
    """Team Ground Rule의 구분별 렌더링 (레벨 2: ## 구분)"""
    # 구분이 'CoC (Code of Conduct)'인 경우 처음부터 펼쳐서 표시
    is_coc = category_name.strip() == 'CoC (Code of Conduct)'
    with st.expander(category_name, expanded=is_coc):
        # 레벨 2 헤딩 표시 - 초록색 적용, '#' 기호 제거
        st.markdown(f'<h2 style="color: #388E3C; font-weight: 600;">{category_name}</h2>', unsafe_allow_html=True)
        
        # 같은 구분 내에서 추구가치별로 그룹화
        # 추구가치 컬럼 찾기
        value_col = None
        detail_col = None
        
        for col in category_data.columns:
            col_lower = col.lower()
            if '추구가치' in col_lower or '추구' in col_lower or '가치' in col_lower:
                value_col = col
            elif '세부원칙' in col_lower or '세부' in col_lower or '원칙' in col_lower:
                detail_col = col
        
        # 추구가치가 없으면 전체 데이터를 그대로 표시
        if not value_col:
            for idx, row in category_data.iterrows():
                # 모든 필드를 표시
                for col in category_data.columns:
                    value = row.get(col)
                    if pd.notna(value) and str(value).strip() != "":
                        st.markdown(f"**{col}**: {value}")
                if idx < len(category_data) - 1:
                    st.markdown("---")
            return
        
        # 추구가치별로 그룹화
        value_groups = {}
        for idx, row in category_data.iterrows():
            value_name = str(row.get(value_col)).strip() if pd.notna(row.get(value_col)) else f"항목 {idx + 1}"
            if value_name == "nan" or value_name == "":
                value_name = f"항목 {idx + 1}"
            
            if value_name not in value_groups:
                value_groups[value_name] = []
            value_groups[value_name].append(row)
        
        # 각 추구가치 렌더링 (레벨 3: ### 추구가치)
        # 구분이 'CoC (Code of Conduct)'인 경우에만 접이식 사용
        is_coc = category_name.strip() == 'CoC (Code of Conduct)'
        
        for value_name, value_rows in value_groups.items():
            # CoC인 경우에만 expander 사용, 아닌 경우 바로 표시
            if is_coc:
                with st.expander(value_name, expanded=False):
                    # 레벨 3 헤딩 표시 - 주황색 적용, '#' 기호 제거
                    st.markdown(f'<h3 style="color: #F57C00; font-weight: 600;">{value_name}</h3>', unsafe_allow_html=True)
                    
                    for row in value_rows:
                        # 세부원칙 표시 (레벨 4: #### 세부원칙) - 접이식 없이 텍스트로 표시
                        if detail_col and pd.notna(row.get(detail_col)):
                            detail_content = row.get(detail_col)
                            _render_detail_principle(detail_content)
                            st.markdown("")
                        
                        # 다른 필드들 표시 (세부원칙 외, 구분 제외)
                        for col in category_data.columns:
                            # 구분, 추구가치, 세부원칙 컬럼은 제외
                            if col == value_col or col == detail_col:
                                continue
                            # '구분' 컬럼 제외
                            col_lower = col.lower()
                            if '구분' in col_lower or '카테고리' in col_lower:
                                continue
                            value = row.get(col)
                            if pd.notna(value) and str(value).strip() != "":
                                st.markdown(f"**{col}**: {value}")
                        
                        if len(value_rows) > 1:
                            st.markdown("---")
            else:
                # CoC가 아닌 경우: 접이식 없이 바로 표시
                # 레벨 3 헤딩 표시 - 주황색 적용, '#' 기호 제거
                st.markdown(f'<h3 style="color: #F57C00; font-weight: 600;">{value_name}</h3>', unsafe_allow_html=True)
                
                for row in value_rows:
                    # 세부원칙 표시 (레벨 4: #### 세부원칙) - 접이식 없이 텍스트로 표시
                    if detail_col and pd.notna(row.get(detail_col)):
                        detail_content = row.get(detail_col)
                        _render_detail_principle(detail_content)
                        st.markdown("")
                    
                    # 다른 필드들 표시 (세부원칙 외, 구분 제외)
                    for col in category_data.columns:
                        # 구분, 추구가치, 세부원칙 컬럼은 제외
                        if col == value_col or col == detail_col:
                            continue
                        # '구분' 컬럼 제외
                        col_lower = col.lower()
                        if '구분' in col_lower or '카테고리' in col_lower:
                            continue
                        value = row.get(col)
                        if pd.notna(value) and str(value).strip() != "":
                            st.markdown(f"**{col}**: {value}")
                    
                    if len(value_rows) > 1:
                        st.markdown("---")
                
                # 추구가치 사이 간격
                st.markdown("")

def _render_card_grid(df: pd.DataFrame, title_fields: list[str]) -> None:
    cols_per_row = 3
    rows = (len(df) + cols_per_row - 1) // cols_per_row
    for r in range(rows):
        cols = st.columns(cols_per_row)
        for c in range(cols_per_row):
            idx = r * cols_per_row + c
            if idx >= len(df):
                continue
            row = df.iloc[idx]
            title = None
            for field in title_fields:
                if field in df.columns and pd.notna(row.get(field)) and str(row.get(field)).strip():
                    title = str(row.get(field)).strip()
                    break
            if not title:
                title = f"항목 {idx + 1}"

            with cols[c].container(border=True):
                st.markdown(f"**{title}**")
                # 주요 필드 하이라이트
                highlight_fields = [
                    'Mission', 'KPI', '설명', '목표', '카테고리', '중요도', '규칙', 'Owner', '담당'
                ]
                for col in df.columns:
                    value = row.get(col)
                    if pd.isna(value) or str(value).strip() == "":
                        continue
                    label = f"{col}"
                    if col in highlight_fields:
                        st.caption(label)
                        st.write(value)
                    else:
                        with st.expander(label, expanded=False):
                            st.write(value)

def render_mission_kpi():
    """조직 Mission 및 KPI 섹션을 계층적 아코디언으로 렌더링합니다."""
    with st.spinner("조직 Mission 및 KPI 데이터를 불러오는 중..."):
        df = get_sheet_data(MISSION_KPI_SHEET_ID)

    # 레벨 1: # Mission & KPI 섹션 (접이식 없이 바로 표시)
    # 레벨 1 헤딩 표시 - 파란색 적용, '#' 기호 제거
    st.markdown('<h1 style="color: #1976D2; font-weight: 600;">📚 Mission & KPI</h1>', unsafe_allow_html=True)
    
    if df is not None and not df.empty:
        # 조직명 컬럼 찾기 (조직, 조직명, 제목, 이름 등)
        org_col = None
        possible_org_cols = ['조직', '조직명', '제목', '이름', '팀', '부서']
        for col in df.columns:
            if col in possible_org_cols:
                org_col = col
                break
        
        # 조직명 컬럼이 없으면 첫 번째 텍스트 컬럼 사용
        if not org_col:
            for col in df.columns:
                if df[col].dtype == 'object':
                    org_col = col
                    break
        
        if org_col:
            # 조직명별로 그룹화
            org_groups = {}
            for idx, row in df.iterrows():
                org_name = str(row.get(org_col)).strip() if pd.notna(row.get(org_col)) else "기타"
                if org_name == "nan" or org_name == "":
                    org_name = "기타"
                
                if org_name not in org_groups:
                    org_groups[org_name] = []
                org_groups[org_name].append(row)
            
            # 각 조직별로 렌더링 (레벨 2: ## 조직명)
            for org_name, org_rows in org_groups.items():
                org_df = pd.DataFrame(org_rows)
                _render_mission_kpi_organization(org_name, org_df)
        else:
            # 그룹화할 컬럼이 없으면 그대로 표시
            for idx, row in df.iterrows():
                org_name = f"항목 {idx + 1}"
                org_df = pd.DataFrame([row])
                _render_mission_kpi_organization(org_name, org_df)
    else:
        st.warning("⚠️ 조직 Mission 및 KPI 데이터를 불러올 수 없습니다.")
        st.info("Google Sheets 연동을 확인하거나 스프레드시트 접근 권한을 확인해주세요.")

def render_ground_rules():
    """팀 Ground Rule 섹션을 계층적 아코디언으로 렌더링합니다."""
    with st.spinner("팀 Ground Rule 데이터를 불러오는 중..."):
        df = get_sheet_data(GROUND_RULE_SHEET_ID)

    # 레벨 1: # Team Ground Rule 섹션 (접이식 없이 바로 표시)
    # 레벨 1 헤딩 표시 - 파란색 적용, '#' 기호 제거
    st.markdown('<h1 style="color: #1976D2; font-weight: 600;">📋 Team Ground Rule</h1>', unsafe_allow_html=True)
    
    if df is not None and not df.empty:
        # 구분 컬럼 찾기 (구분, 카테고리, 분류 등)
        category_col = None
        possible_category_cols = ['구분', '카테고리', '분류', '카테고리명', '구분명']
        for col in df.columns:
            if col in possible_category_cols:
                category_col = col
                break
        
        # 구분 컬럼이 없으면 첫 번째 텍스트 컬럼 사용
        if not category_col:
            for col in df.columns:
                if df[col].dtype == 'object':
                    category_col = col
                    break
        
        if category_col:
            # 구분별로 그룹화 (같은 구분끼리 묶기)
            category_groups = {}
            for idx, row in df.iterrows():
                cat_name = str(row.get(category_col)).strip() if pd.notna(row.get(category_col)) else "기타"
                if cat_name == "nan" or cat_name == "":
                    cat_name = "기타"
                
                if cat_name not in category_groups:
                    category_groups[cat_name] = []
                category_groups[cat_name].append(row)
            
            # 각 구분별로 렌더링 (레벨 2: ## 구분) - 접이식으로 표시
            for cat_name, cat_rows in category_groups.items():
                cat_df = pd.DataFrame(cat_rows)
                _render_ground_rule_category(cat_name, cat_df)
        else:
            # 그룹화할 컬럼이 없으면 그대로 표시
            cat_df = pd.DataFrame([df.iloc[0]]) if len(df) > 0 else pd.DataFrame()
            if not cat_df.empty:
                _render_ground_rule_category("규칙", cat_df)
    else:
        st.warning("⚠️ 팀 Ground Rule 데이터를 불러올 수 없습니다.")
        st.info("Google Sheets 연동을 확인하거나 스프레드시트 접근 권한을 확인해주세요.")

def render_organization_embedded():
    """조직 정보 페이지를 3단계 아코디언 구조로 렌더링합니다."""
    st.title("🎯 Goal & Policy")
    st.markdown("조직의 Mission, KPI, 그리고 팀 Ground Rule을 3단계 아코디언 형태로 확인하세요.")
    st.markdown("---")

    # 레벨 1: Mission & KPI 섹션
    render_mission_kpi()
    
    st.markdown("")
    st.markdown("---")

    # 레벨 1: Team Ground Rule 섹션
    render_ground_rules()

def main():
    """독립 실행용 메인 함수"""
    st.set_page_config(
        page_title="조직 정보",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    render_organization_embedded()

if __name__ == "__main__":
    main()

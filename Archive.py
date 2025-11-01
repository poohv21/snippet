import streamlit as st
import pandas as pd
import os

def _ensure_archive_styles():
    """Archive 페이지의 CSS 스타일을 매번 주입하여 다른 페이지의 CSS가 덮어쓰지 않도록 보장합니다."""
    # 페이지 이동 후 돌아올 때마다 CSS를 재주입 (다른 페이지의 CSS가 덮어쓸 수 있으므로)
    st.markdown(
        """
        <style id="archive-page-styles">
        /* Archive 페이지 전용 스타일 - 매번 재주입하여 덮어쓰기 방지 */
        .main .block-container {
            max-width: 700px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* 별점 스타일링 */
        .star-rating {
            font-size: 1.2em !important;
            letter-spacing: 2px !important;
            font-weight: 600 !important;
        }
        .star-filled {
            color: #FFC107 !important;
        }
        .star-empty {
            color: #CCCCCC !important;
        }
        /* 레벨별 색상 스타일 - 매우 구체적인 선택자로 강제 적용 */
        span.level-1,
        div.level-1,
        .level-1,
        [class*="level-1"] {
            color: #E74C3C !important; /* 빨간색 - 매우 낮음 */
        }
        span.level-2,
        div.level-2,
        .level-2,
        [class*="level-2"] {
            color: #E67E22 !important; /* 주황색 - 낮음 */
        }
        span.level-3,
        div.level-3,
        .level-3,
        [class*="level-3"] {
            color: #F39C12 !important; /* 노란색 - 보통 */
        }
        span.level-4,
        div.level-4,
        .level-4,
        [class*="level-4"] {
            color: #58D68D !important; /* 연두색 - 좋음 */
        }
        span.level-5,
        div.level-5,
        .level-5,
        [class*="level-5"] {
            color: #27AE60 !important; /* 초록색 - 매우 좋음 */
        }
        /* Archive 페이지 헤더 폰트 사이즈 및 색상 조정 - 매우 구체적인 선택자 */
        div[data-testid="stAppViewContainer"] > div > div > div > div h1,
        div[data-testid="stAppViewContainer"] h1 {
            font-size: 1.5em !important;
            font-weight: 600 !important;
            color: #8E44AD !important; /* 보라색 */
        }
        div[data-testid="stAppViewContainer"] > div > div > div > div h2,
        div[data-testid="stAppViewContainer"] h2 {
            font-size: 1.2em !important;
            font-weight: 600 !important;
            color: #5DADE2 !important; /* 밝은 파랑 */
        }
        /* Expander 헤더 스타일링 */
        .streamlit-expanderHeader {
            background-color: #64B5F6 !important; /* 진한 파랑 배경 */
            color: #001f3f !important; /* 남색 텍스트 */
            font-weight: 600 !important;
            padding: 0.75rem 1rem !important;
            border-radius: 0.5rem !important;
        }
        .streamlit-expanderHeader:hover {
            background-color: #42A5F5 !important; /* 호버 시 더 진한 파랑 */
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def get_snippets_from_google_sheets(get_google_sheets_client, spreadsheet_id):
    """Google Sheets에서 Snippet 데이터를 가져옵니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet("Sheet1")
        
        # 모든 데이터 가져오기
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Google Sheets 데이터 가져오기 오류: {e}")
        return None


def get_snippets_from_local_csv():
    """로컬 CSV 파일에서 Snippet 데이터를 가져옵니다."""
    try:
        csv_file = "daily_snippets.csv"
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file, encoding='utf-8')
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"로컬 CSV 파일 읽기 오류: {e}")
        return None


def get_snippets_with_fallback(get_google_sheets_client, spreadsheet_id):
    """Snippet 데이터를 가져옵니다. Google Sheets 실패 시 로컬 CSV에서 가져옵니다."""
    # Google Sheets에서 가져오기 시도
    if st.session_state.google_sheets_connected:
        df = get_snippets_from_google_sheets(get_google_sheets_client, spreadsheet_id)
        if df is not None and not df.empty:
            return df
    
    # Google Sheets 실패 시 로컬 CSV에서 가져오기
    st.warning("Google Sheets에서 데이터를 가져올 수 없습니다. 로컬 CSV 파일에서 데이터를 가져옵니다.")
    return get_snippets_from_local_csv()


def _format_date_display(timestamp_str):
    """타임스탬프를 {YYYY년 MM월 DD일 HH:MM} 형식으로 변환합니다."""
    if not timestamp_str:
        return "날짜 없음", ""
    
    from datetime import datetime
    
    timestamp_str = str(timestamp_str).strip()
    
    # 여러 날짜 형식 시도
    date_formats = [
        "%Y. %m. %d %p %I:%M:%S",  # "2025. 10. 29 오전 09:57:00"
        "%Y. %m. %d %p %I:%M",      # "2025. 10. 29 오전 09:57"
        "%Y-%m-%d %H:%M:%S",        # "2025-10-29 09:57:00"
        "%Y-%m-%d %H:%M",           # "2025-10-29 09:57"
        "%Y/%m/%d %H:%M:%S",        # "2025/10/29 09:57:00"
        "%Y/%m/%d %H:%M",           # "2025/10/29 09:57"
        "%Y.%m.%d %H:%M:%S",        # "2025.10.29 09:57:00"
        "%Y.%m.%d %H:%M",           # "2025.10.29 09:57"
    ]
    
    for fmt in date_formats:
        try:
            # 오전/오후를 AM/PM으로 변환하여 파싱 시도
            test_str = timestamp_str.replace("오전", "AM").replace("오후", "PM")
            dt = datetime.strptime(test_str, fmt)
            # {YYYY년 MM월 DD일 HH:MM} 형식으로 변환
            formatted = f"{dt.year}년 {dt.month:02d}월 {dt.day:02d}일 {dt.hour:02d}:{dt.minute:02d}"
            return formatted, timestamp_str
        except (ValueError, AttributeError):
            continue
    
    # 파싱 실패 시 수동 파싱 시도
    try:
        parts = timestamp_str.split(' ')
        if len(parts) >= 3:
            # 날짜 부분 파싱
            date_part = parts[0]  # "2025. 10. 29" 또는 "2025-10-29" 등
            date_clean = date_part.replace('.', ' ').replace('-', ' ').replace('/', ' ').strip()
            date_numbers = [x for x in date_clean.split() if x]
            
            if len(date_numbers) >= 3:
                year = date_numbers[0].strip()
                month = date_numbers[1].strip().zfill(2)
                day = date_numbers[2].strip().zfill(2)
                
                # 시간 부분 파싱
                hour = 0
                minute = 0
                
                if len(parts) >= 2:
                    # 오전/오후 확인
                    ampm = ""
                    time_part = ""
                    for p in parts[1:]:
                        if p in ["오전", "오후", "AM", "PM"]:
                            ampm = p
                        elif ':' in p:
                            time_part = p
                    
                    if time_part:
                        time_numbers = time_part.split(':')
                        hour = int(time_numbers[0]) if len(time_numbers) > 0 and time_numbers[0].isdigit() else 0
                        minute = int(time_numbers[1]) if len(time_numbers) > 1 and time_numbers[1].isdigit() else 0
                        
                        # 오후 시간 변환
                        if ampm in ["오후", "PM"] and hour < 12:
                            hour += 12
                        elif ampm in ["오전", "AM"] and hour == 12:
                            hour = 0
                
                formatted = f"{year}년 {month}월 {day}일 {hour:02d}:{minute:02d}"
                return formatted, timestamp_str
    except Exception:
        pass
    
    # 모든 파싱 실패 시 원본 반환
    return timestamp_str, timestamp_str

def _get_level_color(level):
    """레벨(1-5)에 따른 색상을 반환합니다."""
    color_map = {
        1: '#E74C3C',  # 빨간색 - 매우 낮음
        2: '#E67E22',  # 주황색 - 낮음
        3: '#F39C12',  # 노란색 - 보통
        4: '#58D68D',  # 연두색 - 좋음
        5: '#27AE60',  # 초록색 - 매우 좋음
    }
    return color_map.get(level, '#95A5A6')  # 기본 회색

def _render_star_rating(value, max_stars=5):
    """별점을 시각적으로 표시합니다 (HTML 포함, 레벨별 색상 적용)."""
    if value is None or pd.isna(value) or value == 0:
        return '<span class="star-rating" style="color: #95A5A6;">☆☆☆☆☆</span>'
    
    try:
        rating = int(float(value))
        level_color = _get_level_color(rating)
        stars_html = ""
        for i in range(max_stars):
            if i < rating:
                stars_html += '<span class="star-filled" style="color: {};">★</span>'.format(level_color)
            else:
                stars_html += '<span class="star-empty">☆</span>'
        return f'<span class="star-rating" style="color: {level_color};">{stars_html}</span>'
    except:
        return '<span class="star-rating" style="color: #95A5A6;">☆☆☆☆☆</span>'

def _is_nonempty(value) -> bool:
    """값이 표시할 의미가 있는지 확인합니다."""
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except Exception:
        pass
    return str(value).strip() != ""

def _get_value_by_aliases(row: pd.Series, aliases: list[str]) -> str:
    """주어진 열 별칭 목록에서 처음으로 값이 있는 항목을 반환합니다."""
    for key in aliases:
        if key in row and _is_nonempty(row.get(key)):
            return str(row.get(key))
    return ""

def render_archive_embedded(get_google_sheets_client, spreadsheet_id):
    """Snippet 아카이브 페이지 렌더링 (메인 앱 컨텍스트에서 사용)"""
    # Archive 페이지 스타일 보장 (한 번만 주입)
    _ensure_archive_styles()
    
    st.title("📚 Snippet 아카이브")
    st.markdown("그동안 작성한 Snippet 기록들을 확인해보세요!")
    st.markdown("---")
    
    # 데이터 가져오기 (Google Sheets 또는 로컬 CSV)
    with st.spinner("데이터를 불러오는 중..."):
        df = get_snippets_with_fallback(get_google_sheets_client, spreadsheet_id)
    
    if df is not None and not df.empty:
        # 로그인된 사용자의 데이터만 필터링
        if st.session_state.logged_in and st.session_state.user_info:
            user_name = st.session_state.user_info['name']
            user_data = df[df['이름'] == user_name] if '이름' in df.columns else df
        else:
            user_data = df
        
        if not user_data.empty:
            # 통계 정보 (상단에 표시)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("총 Snippet 수", len(user_data))
            
            with col2:
                if '몸상태' in user_data.columns:
                    avg_physical = user_data['몸상태'].mean()
                    avg_physical_int = int(round(avg_physical))
                    level_color = _get_level_color(avg_physical_int)
                    st.markdown(
                        f'<div style="color: {level_color}; font-size: 1.5em; font-weight: 700; padding: 0.5rem 0;">평균 몸상태</div>'
                        f'<div style="color: {level_color}; font-size: 1.2em; font-weight: 600;">{avg_physical:.1f}점</div>',
                        unsafe_allow_html=True
                    )
            
            with col3:
                if '마음상태' in user_data.columns:
                    avg_mental = user_data['마음상태'].mean()
                    avg_mental_int = int(round(avg_mental))
                    level_color = _get_level_color(avg_mental_int)
                    st.markdown(
                        f'<div style="color: {level_color}; font-size: 1.5em; font-weight: 700; padding: 0.5rem 0;">평균 마음상태</div>'
                        f'<div style="color: {level_color}; font-size: 1.2em; font-weight: 600;">{avg_mental:.1f}점</div>',
                        unsafe_allow_html=True
                    )
            
            # 날짜 컬럼 찾기 (카드 표시용)
            date_col = '타임스탬프' if '타임스탬프' in user_data.columns else user_data.columns[0]

            st.markdown("---")
            st.success(f"총 {len(user_data)}개의 Snippet을 찾았습니다!")
            
            # 날짜별로 정렬 (최신순) - 타임스탬프 파싱 후 내림차순
            if date_col in user_data.columns:
                try:
                    from datetime import datetime
                    
                    def parse_timestamp(ts_str):
                        """타임스탬프 문자열을 datetime 객체로 변환합니다."""
                        if not ts_str or pd.isna(ts_str):
                            return None
                        
                        ts_str = str(ts_str).strip()
                        if not ts_str:
                            return None
                        
                        # 여러 날짜 형식 시도
                        date_formats = [
                            "%Y. %m. %d %p %I:%M:%S",  # "2025. 10. 29 오전 09:57:00"
                            "%Y. %m. %d %p %I:%M",      # "2025. 10. 29 오전 09:57"
                            "%Y-%m-%d %H:%M:%S",        # "2025-10-29 09:57:00"
                            "%Y-%m-%d %H:%M",           # "2025-10-29 09:57"
                            "%Y/%m/%d %H:%M:%S",        # "2025/10/29 09:57:00"
                            "%Y/%m/%d %H:%M",           # "2025/10/29 09:57"
                            "%Y.%m.%d %H:%M:%S",        # "2025.10.29 09:57:00"
                            "%Y.%m.%d %H:%M",           # "2025.10.29 09:57"
                        ]
                        
                        # 오전/오후를 AM/PM으로 변환
                        test_str = ts_str.replace("오전", "AM").replace("오후", "PM")
                        
                        for fmt in date_formats:
                            try:
                                return datetime.strptime(test_str, fmt)
                            except (ValueError, AttributeError):
                                continue
                        
                        # 추가 시도: pandas to_datetime 사용
                        try:
                            return pd.to_datetime(test_str, errors='coerce')
                        except:
                            pass
                        
                        return None
                    
                    # 타임스탬프를 datetime으로 변환
                    _tmp_sort = user_data.copy()
                    _tmp_sort['__dt'] = _tmp_sort[date_col].apply(parse_timestamp)
                    
                    # datetime이 있는 항목과 없는 항목 분리
                    has_dt = _tmp_sort['__dt'].notna()
                    
                    if has_dt.any():
                        # datetime 기준으로 정렬 (내림차순: 최신순)
                        sorted_df = _tmp_sort.sort_values('__dt', ascending=False, na_position='last')
                        user_data = sorted_df.drop(columns=['__dt']).reset_index(drop=True)
                    else:
                        # datetime 변환 실패 시 원본 문자열 기준 내림차순 정렬
                        user_data = user_data.sort_values(by=date_col, ascending=False, na_position='last').reset_index(drop=True)
                except Exception as e:
                    # 모든 정렬 실패 시 원본 순서 유지 (경고만 출력)
                    st.warning(f"날짜 정렬 중 오류가 발생했습니다: {e}")
                    try:
                        user_data = user_data.sort_values(by=date_col, ascending=False, na_position='last').reset_index(drop=True)
                    except:
                        pass
            
            # 날짜별 카드 형식으로 표시
            for idx, row in user_data.iterrows():
                timestamp = str(row.get(date_col, '')) if date_col in row else ''
                date_display, _ = _format_date_display(timestamp)
                
                # 카드 헤더에 포맷팅된 타임스탬프 표시
                header_title = date_display if date_display != "날짜 없음" else "날짜 없음"
                
                with st.expander(header_title, expanded=False):
                    # [Check-in] 섹션
                    st.markdown("# [Check-in]")
                    
                    # 몸 상태
                    if '몸상태' in row and pd.notna(row.get('몸상태')):
                        physical_value = int(float(row.get('몸상태', 0)))
                        level_color = _get_level_color(physical_value)
                        st.markdown(f'## <span style="color: {level_color};">몸 상태</span>', unsafe_allow_html=True)
                        physical_stars = _render_star_rating(physical_value)
                        st.markdown(physical_stars, unsafe_allow_html=True)
                    else:
                        st.markdown("## 몸 상태")
                        st.markdown("☆☆☆☆☆")
                    
                    # 마음 상태
                    if '마음상태' in row and pd.notna(row.get('마음상태')):
                        mental_value = int(float(row.get('마음상태', 0)))
                        level_color = _get_level_color(mental_value)
                        st.markdown(f'## <span style="color: {level_color};">마음 상태</span>', unsafe_allow_html=True)
                        mental_stars = _render_star_rating(mental_value)
                        st.markdown(mental_stars, unsafe_allow_html=True)
                    else:
                        st.markdown("## 마음 상태")
                        st.markdown("☆☆☆☆☆")
                    
                    # 상태 이유
                    st.markdown("## 상태 이유")
                    state_reason = str(row.get('상태이유', '')) if '상태이유' in row and pd.notna(row.get('상태이유')) else ''
                    st.markdown(state_reason if state_reason.strip() else "-")
                    
                    # 개선 방안
                    st.markdown("## 개선 방안")
                    improvement_plan = str(row.get('개선방안', '')) if '개선방안' in row and pd.notna(row.get('개선방안')) else ''
                    st.markdown(improvement_plan if improvement_plan.strip() else "-")
                    
                    st.markdown("---")
                    
                    # [Look-back] 섹션
                    st.markdown("# [Look-back]")
                    
                    # 전날 한 일
                    st.markdown("## 전날 한 일")
                    yesterday_work = _get_value_by_aliases(row, [
                        '전일업무','전일한일','전날 한 일','[Look-back] 전날 한 일','전일 업무','전일 업무 내용'
                    ])
                    st.markdown(yesterday_work if yesterday_work.strip() else "-")
                    
                    # 전날 만족도
                    satisfaction_raw = _get_value_by_aliases(row, [
                        '전일만족도','전날 만족도','[Look-back] 전날 만족도'
                    ])
                    if satisfaction_raw:
                        try:
                            satisfaction_value = int(float(satisfaction_raw))
                            level_color = _get_level_color(satisfaction_value)
                            st.markdown(f'## <span style="color: {level_color};">전날 만족도</span>', unsafe_allow_html=True)
                            satisfaction_stars = _render_star_rating(satisfaction_value)
                            st.markdown(satisfaction_stars, unsafe_allow_html=True)
                        except Exception:
                            st.markdown("## 전날 만족도")
                            st.markdown("☆☆☆☆☆")
                    else:
                        st.markdown("## 전날 만족도")
                        st.markdown("☆☆☆☆☆")
                    
                    # [Liked] 좋았던 점
                    st.markdown("## [Liked] 좋았던 점")
                    liked = _get_value_by_aliases(row, ['좋았던점','[Liked] 좋았던 점','Liked','좋았던 점'])
                    st.markdown(liked if liked.strip() else "-")
                    
                    # [Lacked] 아쉬웠던 점
                    st.markdown("## [Lacked] 아쉬웠던 점")
                    lacked = _get_value_by_aliases(row, ['아쉬웠던점','[Lacked] 아쉬웠던 점','Lacked','아쉬웠던 점'])
                    st.markdown(lacked if lacked.strip() else "-")
                    
                    # [Learned] 배운점/성장포인트
                    st.markdown("## [Learned] 배운점/성장포인트")
                    learned = _get_value_by_aliases(row, ['배웠던점','[Learned] 배운점/성장포인트','Learned','배운 점','배운점'])
                    st.markdown(learned if learned.strip() else "-")
                    
                    # [Looked-Forward] 향후 시도할 점
                    st.markdown("## [Looked-Forward] 향후 시도할 점")
                    looked_forward = _get_value_by_aliases(row, ['향후시도','[Looked-Forward] 향후 시도할 점','Looked-Forward','향후 시도'])
                    st.markdown(looked_forward if looked_forward.strip() else "-")
                    
                    # [Longed-For] 요청사항
                    st.markdown("## [Longed-For] 요청사항")
                    longed_for = _get_value_by_aliases(row, ['바라는점','[Longed-For] 요청사항','Longed-For','요청 사항','요청사항'])
                    st.markdown(longed_for if longed_for.strip() else "-")
                    
                    # 동료 칭찬
                    st.markdown("## 동료 칭찬")
                    colleague_praise = _get_value_by_aliases(row, ['동료칭찬','동료 칭찬','[Praise] 동료 칭찬'])
                    st.markdown(colleague_praise if colleague_praise.strip() else "-")
                    
                    st.markdown("---")
                    
                    # [Today's Plan] 섹션
                    st.markdown("# [Today's Plan]")
                    
                    # 당일 계획
                    st.markdown("## 당일 계획")
                    today_plans = str(row.get('오늘할일', '')) if '오늘할일' in row and pd.notna(row.get('오늘할일')) else ''
                    st.markdown(today_plans if today_plans.strip() else "-")

                    # 기타 누락 항목 자동 표시 (이미 섹션에 매핑된 별칭들도 제외)
                    shown_keys = {
                        date_col,
                        '이름','몸상태','마음상태','상태이유','개선방안','전일업무','전일한일','전일만족도',
                        '좋았던점','아쉬웠던점','배웠던점','향후시도','바라는점','동료칭찬','오늘할일',
                        '전날 한 일','[Look-back] 전날 한 일','전일 업무','전일 업무 내용',
                        '전날 만족도','[Look-back] 전날 만족도',
                        '[Liked] 좋았던 점','Liked','좋았던 점',
                        '[Lacked] 아쉬웠던 점','Lacked','아쉬웠던 점',
                        '[Learned] 배운점/성장포인트','Learned','배운 점','배운점',
                        '[Looked-Forward] 향후 시도할 점','Looked-Forward','향후 시도',
                        '[Longed-For] 요청사항','Longed-For','요청 사항','요청사항',
                        '[Praise] 동료 칭찬','동료 칭찬'
                    }
                    misc_items = []
                    try:
                        for col in row.index:
                            if col not in shown_keys and _is_nonempty(row.get(col)):
                                misc_items.append((col, row.get(col)))
                    except Exception:
                        pass
                    if misc_items:
                        st.markdown("---")
                        st.markdown("### 기타 항목")
                        for label, value in misc_items:
                            st.markdown(f"**{label}**: {value}")
        else:
            st.info("아직 작성한 Snippet이 없습니다. Daily Snippet 기록을 시작해보세요!")
    else:
        st.warning("데이터를 불러올 수 없습니다. Google Sheets 연동을 확인해주세요.")


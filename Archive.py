import streamlit as st
import pandas as pd
import os
import html

def _ensure_archive_styles():
    """Archive 페이지의 CSS 스타일을 매번 주입하여 다른 페이지의 CSS가 덮어쓰지 않도록 보장합니다."""
    # 페이지 이동 후 돌아올 때마다 CSS를 재주입 (다른 페이지의 CSS가 덮어쓸 수 있으므로)
    # CSS를 나중에 로드하여 우선순위를 높임
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
        
        /* ==========================================
           Snippet 아카이브 제목 색상 구분
           ========================================== */
        
        /* Level 1 섹션 제목 ([Check-in], [Look-back], [Today's Plan]) - 보라색 
           (최우선순위로 expander 안의 h1을 먼저 타겟팅) */
        [data-testid="stExpander"] h1,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1 *,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] h1,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] h1 *,
        .section-header-level1,
        h1.section-header-level1,
        h1.section-header-level1 *,
        h1[id^="checkin-header-"],
        h1[id^="lookback-header-"],
        h1[id^="plan-header-"] {
            color: #9B59B6 !important; /* 보라색 - Level 1 */
            font-size: 1.5em !important;
            font-weight: 700 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Level 1 헤더 내부 모든 요소도 보라색 유지 */
        [data-testid="stExpander"] h1 *,
        h1.section-header-level1 *,
        h1[id^="checkin-header-"] *,
        h1[id^="lookback-header-"] *,
        h1[id^="plan-header-"] * {
            color: #9B59B6 !important;
        }
        
        /* Level 2 섹션 항목 (몸 상태, 마음 상태, 상태 이유, 개선 방안, 전날 한 일 등) - 밝은 파랑
           (최우선순위로 expander 안의 h2를 먼저 타겟팅) */
        [data-testid="stExpander"] h2,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2 *,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] h2,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] h2 *,
        .section-header-level2,
        h2.section-header-level2,
        h2.section-header-level2 *,
        h2[id^="physical-state-"],
        h2[id^="physical-empty-"],
        h2[id^="mental-state-"],
        h2[id^="mental-empty-"],
        h2[id^="state-reason-"],
        h2[id^="improvement-"],
        h2[id^="yesterday-"],
        h2[id^="satisfaction-"],
        h2[id^="satisfaction-empty-"],
        h2[id^="liked-"],
        h2[id^="lacked-"],
        h2[id^="learned-"],
        h2[id^="looked-forward-"],
        h2[id^="longed-for-"],
        h2[id^="colleague-praise-"],
        h2[id^="today-plan-"] {
            color: #3498DB !important; /* 밝은 파랑 - Level 2 */
            font-size: 1.3em !important;
            font-weight: 600 !important;
            margin-top: 0.8rem !important;
            margin-bottom: 0 !important;
        }
        
        /* Level 2 섹션 항목 제목에 블릿 추가 */
        [data-testid="stExpander"] h2::before,
        [data-testid="stExpander"] h2[id^="physical-state-"]::before,
        [data-testid="stExpander"] h2[id^="physical-empty-"]::before,
        [data-testid="stExpander"] h2[id^="mental-state-"]::before,
        [data-testid="stExpander"] h2[id^="mental-empty-"]::before,
        [data-testid="stExpander"] h2[id^="state-reason-"]::before,
        [data-testid="stExpander"] h2[id^="improvement-"]::before,
        [data-testid="stExpander"] h2[id^="yesterday-"]::before,
        [data-testid="stExpander"] h2[id^="satisfaction-"]::before,
        [data-testid="stExpander"] h2[id^="satisfaction-empty-"]::before,
        [data-testid="stExpander"] h2[id^="liked-"]::before,
        [data-testid="stExpander"] h2[id^="lacked-"]::before,
        [data-testid="stExpander"] h2[id^="learned-"]::before,
        [data-testid="stExpander"] h2[id^="looked-forward-"]::before,
        [data-testid="stExpander"] h2[id^="longed-for-"]::before,
        [data-testid="stExpander"] h2[id^="colleague-praise-"]::before,
        [data-testid="stExpander"] h2[id^="today-plan-"]::before,
        h2.section-header-level2::before {
            content: "• " !important;
            color: #3498DB !important;
            font-weight: 600 !important;
            margin-right: 0.5em !important;
        }
        
        /* 별점과 헤더를 같은 줄에 배치하는 flexbox 컨테이너 스타일 */
        [data-testid="stExpander"] div[id^="physical-container-"],
        [data-testid="stExpander"] div[id^="physical-empty-container-"],
        [data-testid="stExpander"] div[id^="mental-container-"],
        [data-testid="stExpander"] div[id^="mental-empty-container-"],
        [data-testid="stExpander"] div[id^="satisfaction-container-"],
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] {
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            margin-top: 0.8rem !important;
            margin-bottom: 0 !important;
            gap: 0.5rem !important;
        }
        
        /* 전날 만족도 컨테이너도 왼쪽 정렬 */
        [data-testid="stExpander"] div[id^="satisfaction-container-"],
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] {
            justify-content: flex-start !important;
        }
        
        /* flexbox 컨테이너 내부 헤더 스타일 */
        [data-testid="stExpander"] div[id^="physical-container-"] h2,
        [data-testid="stExpander"] div[id^="physical-empty-container-"] h2,
        [data-testid="stExpander"] div[id^="mental-container-"] h2,
        [data-testid="stExpander"] div[id^="mental-empty-container-"] h2,
        [data-testid="stExpander"] div[id^="satisfaction-container-"] h2,
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] h2 {
            margin: 0 !important;
            padding: 0 !important;
            flex: 0 0 auto !important;
        }
        
        /* flexbox 컨테이너 내부 별점 스타일 */
        [data-testid="stExpander"] div[id^="physical-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="physical-empty-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="mental-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="mental-empty-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="satisfaction-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] div:last-child {
            flex: 0 0 auto !important;
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
            font-size: 1.2em !important;
        }
        
        /* flexbox 컨테이너 내부 모든 헤더 크기 통일 (Level 2) - 최고 우선순위로 설정 */
        [data-testid="stExpander"] div[id^="physical-container-"] h2.section-header-level2,
        [data-testid="stExpander"] div[id^="physical-empty-container-"] h2.section-header-level2,
        [data-testid="stExpander"] div[id^="mental-container-"] h2.section-header-level2,
        [data-testid="stExpander"] div[id^="mental-empty-container-"] h2.section-header-level2,
        [data-testid="stExpander"] div[id^="satisfaction-container-"] h2.section-header-level2,
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] h2.section-header-level2,
        [data-testid="stExpander"] div[id^="physical-container-"] h2[id^="physical-"],
        [data-testid="stExpander"] div[id^="physical-empty-container-"] h2[id^="physical-"],
        [data-testid="stExpander"] div[id^="mental-container-"] h2[id^="mental-"],
        [data-testid="stExpander"] div[id^="mental-empty-container-"] h2[id^="mental-"],
        [data-testid="stExpander"] div[id^="satisfaction-container-"] h2[id^="satisfaction-"],
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] h2[id^="satisfaction-"] {
            font-size: 1.3em !important;
        }
        
        /* flexbox 컨테이너 내부 모든 별점 크기 통일 */
        [data-testid="stExpander"] div[id^="physical-container-"] .star-rating,
        [data-testid="stExpander"] div[id^="physical-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="physical-empty-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="mental-container-"] .star-rating,
        [data-testid="stExpander"] div[id^="mental-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="mental-empty-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="satisfaction-container-"] .star-rating,
        [data-testid="stExpander"] div[id^="satisfaction-container-"] div:last-child,
        [data-testid="stExpander"] div[id^="satisfaction-empty-container-"] div:last-child {
            font-size: 1.2em !important;
        }
        
        /* Level 2 헤더 내부 모든 요소도 밝은 파랑 유지 */
        [data-testid="stExpander"] h2 *,
        h2.section-header-level2 *,
        h2[id^="physical-state-"] *,
        h2[id^="physical-empty-"] *,
        h2[id^="mental-state-"] *,
        h2[id^="mental-empty-"] *,
        h2[id^="state-reason-"] *,
        h2[id^="improvement-"] *,
        h2[id^="yesterday-"] *,
        h2[id^="satisfaction-"] *,
        h2[id^="satisfaction-empty-"] *,
        h2[id^="liked-"] *,
        h2[id^="lacked-"] *,
        h2[id^="learned-"] *,
        h2[id^="looked-forward-"] *,
        h2[id^="longed-for-"] *,
        h2[id^="colleague-praise-"] *,
        h2[id^="today-plan-"] * {
            color: #3498DB !important;
        }
        
        /* 최상단 헤더 (페이지 제목: "📚 Snippet 아카이브") - 검정색 
           (expander 밖에만 적용 - expander가 포함되지 않은 컨테이너 내의 첫 번째 h1만) */
        [data-testid="stAppViewContainer"] .main .element-container:not(:has([data-testid="stExpander"])) h1:first-child,
        [data-testid="stAppViewContainer"] .main > *:not([data-testid="stExpander"]) h1,
        [data-testid="stMarkdownContainer"]:not([data-testid="stExpander"] *) h1:first-of-type {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: #000000 !important; /* 검정색 */
            margin-top: 0.5rem !important;
            margin-bottom: 1rem !important;
        }
        
        /* expander 밖의 h1에만 검정색 적용 (expander 안의 h1은 제외) */
        h1:not([data-testid="stExpander"] h1):not(.section-header-level1):not([id^="checkin-header-"]):not([id^="lookback-header-"]):not([id^="plan-header-"]) {
            color: #000000 !important;
        }
        
        /* 최상단 헤더 내부 모든 요소도 검정색 유지 (expander 밖에만) */
        [data-testid="stAppViewContainer"] .main .element-container:not(:has([data-testid="stExpander"])) h1:first-child *,
        [data-testid="stAppViewContainer"] .main > *:not([data-testid="stExpander"]) h1 *,
        h1:not([data-testid="stExpander"] h1):not(.section-header-level1):not([id^="checkin-header-"]):not([id^="lookback-header-"]):not([id^="plan-header-"]) * {
            color: #000000 !important;
        }
        
        /* 서브 헤더 (사용자 정보: "XXX 님의 Snippet 아카이브") - 회색 
           (expander 밖에만 적용 - expander가 포함되지 않은 컨테이너 내의 첫 번째 h2만) */
        [data-testid="stAppViewContainer"] .main .element-container:not(:has([data-testid="stExpander"])) h2:first-child,
        [data-testid="stAppViewContainer"] .main > *:not([data-testid="stExpander"]) h2,
        [data-testid="stMarkdownContainer"]:not([data-testid="stExpander"] *) h2:first-of-type {
            font-size: 1.5rem !important;
            font-weight: 600 !important;
            color: #666666 !important; /* 회색 */
            margin-top: 0.5rem !important;
            margin-bottom: 1.5rem !important;
        }
        
        /* expander 밖의 h2에만 회색 적용 (expander 안의 h2는 Level 2로 처리되어 제외됨) */
        h2:not([data-testid="stExpander"] h2):not(.section-header-level2):not([id^="physical-state-"]):not([id^="physical-empty-"]):not([id^="mental-state-"]):not([id^="mental-empty-"]):not([id^="state-reason-"]):not([id^="improvement-"]):not([id^="yesterday-"]):not([id^="satisfaction-"]):not([id^="satisfaction-empty-"]):not([id^="liked-"]):not([id^="lacked-"]):not([id^="learned-"]):not([id^="looked-forward-"]):not([id^="longed-for-"]):not([id^="colleague-praise-"]):not([id^="today-plan-"]) {
            color: #666666 !important;
        }
        
        /* 서브 헤더 내부 모든 요소도 회색 유지 (expander 밖에만) */
        [data-testid="stAppViewContainer"] .main .element-container:not(:has([data-testid="stExpander"])) h2:first-child *,
        [data-testid="stAppViewContainer"] .main > *:not([data-testid="stExpander"]) h2 *,
        h2:not([data-testid="stExpander"] h2):not(.section-header-level2):not([id^="physical-state-"]):not([id^="physical-empty-"]):not([id^="mental-state-"]):not([id^="mental-empty-"]):not([id^="state-reason-"]):not([id^="improvement-"]):not([id^="yesterday-"]):not([id^="satisfaction-"]):not([id^="satisfaction-empty-"]):not([id^="liked-"]):not([id^="lacked-"]):not([id^="learned-"]):not([id^="looked-forward-"]):not([id^="longed-for-"]):not([id^="colleague-praise-"]):not([id^="today-plan-"]) * {
            color: #666666 !important;
        }
        
        /* Streamlit 기본 텍스트 색상 강제 덮어쓰기 방지 */
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1.section-header-level1,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2.section-header-level2,
        [data-testid="stExpander"] h1.section-header-level1,
        [data-testid="stExpander"] h2.section-header-level2 {
            /* 색상이 덮어쓰이지 않도록 */
        }
        
        /* Streamlit의 기본 텍스트 색상 규칙 무시 */
        [data-testid="stMarkdownContainer"] h1,
        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2 {
            /* 기본 색상 규칙보다 커스텀 색상이 우선 */
        }
        
        /* 카드 안의 텍스트 줄간격 강제로 줄이기 - 매우 타이트하게 */
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p *,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]) *,
        [data-testid="stExpander"] p,
        [data-testid="stExpander"] p *,
        [data-testid="stExpander"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]):not(h1):not(h2),
        [data-testid="stExpander"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]):not(h1):not(h2) *,
        [data-testid="stExpander"] span,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p * {
            line-height: 1.2 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        
        /* 헤더 다음 텍스트 간격 제거 */
        [data-testid="stExpander"] h1 + *,
        [data-testid="stExpander"] h2 + * {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        /* 섹션 간 간격 최소화 */
        [data-testid="stExpander"] hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* 빈 줄이나 공백 제거 */
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p:empty,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] div:empty {
            display: none !important;
        }
        
        /* Streamlit 기본 마진 및 줄간격 강제 제거 */
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.2 !important;
        }
        
        /* 세부 내용 들여쓰기 - Level 2 헤더 다음에 오는 텍스트 내용 (더 많이 들여쓰기) */
        [data-testid="stExpander"] h2 + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2 ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="state-reason-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="state-reason-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="improvement-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="improvement-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="yesterday-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="yesterday-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="liked-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="liked-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="lacked-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="lacked-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="learned-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="learned-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="looked-forward-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="looked-forward-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="longed-for-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="longed-for-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="colleague-praise-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="colleague-praise-"] ~ [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="today-plan-"] + [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] h2[id^="today-plan-"] ~ [data-testid="stMarkdownContainer"] {
            padding-left: 2rem !important;
            margin-left: 0 !important;
        }
        
        /* 세부 내용 div에 직접 들여쓰기 적용 (ID 기반) */
        [data-testid="stExpander"] div[id^="state-reason-content-"],
        [data-testid="stExpander"] div[id^="improvement-content-"],
        [data-testid="stExpander"] div[id^="yesterday-work-content-"],
        [data-testid="stExpander"] div[id^="liked-content-"],
        [data-testid="stExpander"] div[id^="lacked-content-"],
        [data-testid="stExpander"] div[id^="learned-content-"],
        [data-testid="stExpander"] div[id^="looked-forward-content-"],
        [data-testid="stExpander"] div[id^="longed-for-content-"],
        [data-testid="stExpander"] div[id^="colleague-praise-content-"],
        [data-testid="stExpander"] div[id^="today-plan-content-"] {
            padding-left: 2rem !important;
            margin-left: 0 !important;
            white-space: pre-line !important; /* 줄바꿈 보존 */
        }
        
        /* 세부 내용이 들어있는 MarkdownContainer에도 적용 */
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="state-reason-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="improvement-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="yesterday-work-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="liked-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="lacked-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="learned-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="looked-forward-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="longed-for-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="colleague-praise-content-"]),
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"]:has(div[id^="today-plan-content-"]) {
            padding-left: 2rem !important;
            margin-left: 0 !important;
        }
        
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] * {
            line-height: inherit !important;
        }
        
        /* 별점 스타일링 */
        .star-rating,
        [data-testid="stExpander"] .star-rating,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] .star-rating {
            font-size: 1.2em !important;
            letter-spacing: 2px !important;
            font-weight: 600 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            line-height: 1 !important;
        }
        
        /* 헤더 다음 별점 간격 완전 제거 */
        [data-testid="stExpander"] h2 + [data-testid="stMarkdownContainer"]:has(.star-rating),
        [data-testid="stExpander"] h2 + [data-testid="stMarkdownContainer"] .star-rating,
        [data-testid="stExpander"] h2[id^="physical-state-"] ~ [data-testid="stMarkdownContainer"]:has(.star-rating),
        [data-testid="stExpander"] h2[id^="mental-state-"] ~ [data-testid="stMarkdownContainer"]:has(.star-rating),
        [data-testid="stExpander"] h2[id^="satisfaction-"] ~ [data-testid="stMarkdownContainer"]:has(.star-rating),
        [data-testid="stExpander"] h2[id^="physical-state-"] + div,
        [data-testid="stExpander"] h2[id^="physical-empty-"] + div,
        [data-testid="stExpander"] h2[id^="mental-state-"] + div,
        [data-testid="stExpander"] h2[id^="mental-empty-"] + div,
        [data-testid="stExpander"] h2[id^="satisfaction-"] + div,
        [data-testid="stExpander"] h2[id^="satisfaction-empty-"] + div {
            margin-top: 0 !important;
            padding-top: 0 !important;
            line-height: 1 !important;
        }
        .star-filled {
            color: #FFC107 !important;
        }
        .star-empty {
            color: #CCCCCC !important;
        }
        
        /* ID 기반 직접 스타일 적용 - h2 헤더나 flexbox 컨테이너는 제외 */
        div[id^="physical-state-"]:not(h2),
        div[id^="mental-state-"]:not(h2),
        div[id^="satisfaction-"]:not(h2):not([id^="satisfaction-container-"]):not([id^="satisfaction-empty-container-"]) {
            font-size: 1.2em !important;
            font-weight: bold !important;
            margin-top: 0.5em !important;
            margin-bottom: 0.5em !important;
        }
        
        /* Streamlit 기본 텍스트 색상을 덮어쓰지 않도록 - 레벨별 색상 우선 적용 */
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="physical-state-"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="mental-state-"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-1,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-2,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-3,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-4,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-5 {
            /* 레벨별 색상이 기본 색상보다 우선되도록 */
        }
        
        /* 레벨별 색상 스타일 - 최대한 구체적으로 적용 */
        /* 레벨 1 - 빨간색 */
        div[data-level="1"] {
            color: #E74C3C !important;
        }
        div.level-color-1 {
            color: #E74C3C !important;
        }
        div[id^="physical-state-"].level-color-1,
        div[id^="physical-state-"][data-level="1"] {
            color: #E74C3C !important;
        }
        div[id^="mental-state-"].level-color-1,
        div[id^="mental-state-"][data-level="1"] {
            color: #E74C3C !important;
        }
        div[id^="satisfaction-"].level-color-1,
        div[id^="satisfaction-"][data-level="1"] {
            color: #E74C3C !important;
        }
        [data-testid="stExpander"] div[data-level="1"],
        [data-testid="stExpander"] div.level-color-1,
        [data-testid="stExpander"] div[id^="physical-state-"].level-color-1,
        [data-testid="stExpander"] div[id^="mental-state-"].level-color-1,
        [data-testid="stExpander"] div[id^="satisfaction-"].level-color-1,
        [data-testid="stExpander"] div[id^="physical-state-"][data-level="1"],
        [data-testid="stExpander"] div[id^="mental-state-"][data-level="1"],
        [data-testid="stExpander"] div[id^="satisfaction-"][data-level="1"] {
            color: #E74C3C !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[data-level="1"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-1,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="physical-state-"].level-color-1,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="mental-state-"].level-color-1,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="satisfaction-"].level-color-1 {
            color: #E74C3C !important;
        }
        [data-testid="stMarkdownContainer"] div[data-level="1"],
        [data-testid="stMarkdownContainer"] div.level-color-1,
        [data-testid="stMarkdownContainer"] div[id^="physical-state-"].level-color-1,
        [data-testid="stMarkdownContainer"] div[id^="mental-state-"].level-color-1,
        [data-testid="stMarkdownContainer"] div[id^="satisfaction-"].level-color-1 {
            color: #E74C3C !important;
        }
        /* 레벨 2 - 주황색 */
        div[data-level="2"] {
            color: #E67E22 !important;
        }
        div.level-color-2 {
            color: #E67E22 !important;
        }
        div[id^="physical-state-"].level-color-2,
        div[id^="physical-state-"][data-level="2"] {
            color: #E67E22 !important;
        }
        div[id^="mental-state-"].level-color-2,
        div[id^="mental-state-"][data-level="2"] {
            color: #E67E22 !important;
        }
        div[id^="satisfaction-"].level-color-2,
        div[id^="satisfaction-"][data-level="2"] {
            color: #E67E22 !important;
        }
        [data-testid="stExpander"] div[data-level="2"],
        [data-testid="stExpander"] div.level-color-2,
        [data-testid="stExpander"] div[id^="physical-state-"].level-color-2,
        [data-testid="stExpander"] div[id^="mental-state-"].level-color-2,
        [data-testid="stExpander"] div[id^="satisfaction-"].level-color-2,
        [data-testid="stExpander"] div[id^="physical-state-"][data-level="2"],
        [data-testid="stExpander"] div[id^="mental-state-"][data-level="2"],
        [data-testid="stExpander"] div[id^="satisfaction-"][data-level="2"] {
            color: #E67E22 !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[data-level="2"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-2,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="physical-state-"].level-color-2,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="mental-state-"].level-color-2,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="satisfaction-"].level-color-2 {
            color: #E67E22 !important;
        }
        [data-testid="stMarkdownContainer"] div[data-level="2"],
        [data-testid="stMarkdownContainer"] div.level-color-2,
        [data-testid="stMarkdownContainer"] div[id^="physical-state-"].level-color-2,
        [data-testid="stMarkdownContainer"] div[id^="mental-state-"].level-color-2,
        [data-testid="stMarkdownContainer"] div[id^="satisfaction-"].level-color-2 {
            color: #E67E22 !important;
        }
        /* 레벨 3 - 노란색 */
        div[data-level="3"] {
            color: #F39C12 !important;
        }
        div.level-color-3 {
            color: #F39C12 !important;
        }
        div[id^="physical-state-"].level-color-3,
        div[id^="physical-state-"][data-level="3"] {
            color: #F39C12 !important;
        }
        div[id^="mental-state-"].level-color-3,
        div[id^="mental-state-"][data-level="3"] {
            color: #F39C12 !important;
        }
        div[id^="satisfaction-"].level-color-3,
        div[id^="satisfaction-"][data-level="3"] {
            color: #F39C12 !important;
        }
        [data-testid="stExpander"] div[data-level="3"],
        [data-testid="stExpander"] div.level-color-3,
        [data-testid="stExpander"] div[id^="physical-state-"].level-color-3,
        [data-testid="stExpander"] div[id^="mental-state-"].level-color-3,
        [data-testid="stExpander"] div[id^="satisfaction-"].level-color-3,
        [data-testid="stExpander"] div[id^="physical-state-"][data-level="3"],
        [data-testid="stExpander"] div[id^="mental-state-"][data-level="3"],
        [data-testid="stExpander"] div[id^="satisfaction-"][data-level="3"] {
            color: #F39C12 !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[data-level="3"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-3,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="physical-state-"].level-color-3,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="mental-state-"].level-color-3,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="satisfaction-"].level-color-3 {
            color: #F39C12 !important;
        }
        [data-testid="stMarkdownContainer"] div[data-level="3"],
        [data-testid="stMarkdownContainer"] div.level-color-3,
        [data-testid="stMarkdownContainer"] div[id^="physical-state-"].level-color-3,
        [data-testid="stMarkdownContainer"] div[id^="mental-state-"].level-color-3,
        [data-testid="stMarkdownContainer"] div[id^="satisfaction-"].level-color-3 {
            color: #F39C12 !important;
        }
        /* 레벨 4 - 연두색 */
        div[data-level="4"] {
            color: #58D68D !important;
        }
        div.level-color-4 {
            color: #58D68D !important;
        }
        div[id^="physical-state-"].level-color-4,
        div[id^="physical-state-"][data-level="4"] {
            color: #58D68D !important;
        }
        div[id^="mental-state-"].level-color-4,
        div[id^="mental-state-"][data-level="4"] {
            color: #58D68D !important;
        }
        div[id^="satisfaction-"].level-color-4,
        div[id^="satisfaction-"][data-level="4"] {
            color: #58D68D !important;
        }
        [data-testid="stExpander"] div[data-level="4"],
        [data-testid="stExpander"] div.level-color-4,
        [data-testid="stExpander"] div[id^="physical-state-"].level-color-4,
        [data-testid="stExpander"] div[id^="mental-state-"].level-color-4,
        [data-testid="stExpander"] div[id^="satisfaction-"].level-color-4,
        [data-testid="stExpander"] div[id^="physical-state-"][data-level="4"],
        [data-testid="stExpander"] div[id^="mental-state-"][data-level="4"],
        [data-testid="stExpander"] div[id^="satisfaction-"][data-level="4"] {
            color: #58D68D !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[data-level="4"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-4,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="physical-state-"].level-color-4,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="mental-state-"].level-color-4,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="satisfaction-"].level-color-4 {
            color: #58D68D !important;
        }
        [data-testid="stMarkdownContainer"] div[data-level="4"],
        [data-testid="stMarkdownContainer"] div.level-color-4,
        [data-testid="stMarkdownContainer"] div[id^="physical-state-"].level-color-4,
        [data-testid="stMarkdownContainer"] div[id^="mental-state-"].level-color-4,
        [data-testid="stMarkdownContainer"] div[id^="satisfaction-"].level-color-4 {
            color: #58D68D !important;
        }
        /* 레벨 5 - 초록색 */
        div[data-level="5"] {
            color: #27AE60 !important;
        }
        div.level-color-5 {
            color: #27AE60 !important;
        }
        div[id^="physical-state-"].level-color-5,
        div[id^="physical-state-"][data-level="5"] {
            color: #27AE60 !important;
        }
        div[id^="mental-state-"].level-color-5,
        div[id^="mental-state-"][data-level="5"] {
            color: #27AE60 !important;
        }
        div[id^="satisfaction-"].level-color-5,
        div[id^="satisfaction-"][data-level="5"] {
            color: #27AE60 !important;
        }
        [data-testid="stExpander"] div[data-level="5"],
        [data-testid="stExpander"] div.level-color-5,
        [data-testid="stExpander"] div[id^="physical-state-"].level-color-5,
        [data-testid="stExpander"] div[id^="mental-state-"].level-color-5,
        [data-testid="stExpander"] div[id^="satisfaction-"].level-color-5,
        [data-testid="stExpander"] div[id^="physical-state-"][data-level="5"],
        [data-testid="stExpander"] div[id^="mental-state-"][data-level="5"],
        [data-testid="stExpander"] div[id^="satisfaction-"][data-level="5"] {
            color: #27AE60 !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[data-level="5"],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div.level-color-5,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="physical-state-"].level-color-5,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="mental-state-"].level-color-5,
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[id^="satisfaction-"].level-color-5 {
            color: #27AE60 !important;
        }
        [data-testid="stMarkdownContainer"] div[data-level="5"],
        [data-testid="stMarkdownContainer"] div.level-color-5,
        [data-testid="stMarkdownContainer"] div[id^="physical-state-"].level-color-5,
        [data-testid="stMarkdownContainer"] div[id^="mental-state-"].level-color-5,
        [data-testid="stMarkdownContainer"] div[id^="satisfaction-"].level-color-5 {
            color: #27AE60 !important;
        }
        
        /* 인라인 스타일이 있는 경우 강제 적용 - 가장 높은 우선순위로 */
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#E74C3C" i],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#e74c3c" i],
        [data-testid="stExpander"] div[style*="#E74C3C" i],
        [data-testid="stExpander"] div[style*="#e74c3c" i],
        div[style*="#E74C3C" i],
        div[style*="#e74c3c" i],
        [data-testid="stMarkdownContainer"] div[style*="#E74C3C" i],
        [data-testid="stMarkdownContainer"] div[style*="#e74c3c" i] {
            color: #E74C3C !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#E67E22" i],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#e67e22" i],
        [data-testid="stExpander"] div[style*="#E67E22" i],
        [data-testid="stExpander"] div[style*="#e67e22" i],
        div[style*="#E67E22" i],
        div[style*="#e67e22" i],
        [data-testid="stMarkdownContainer"] div[style*="#E67E22" i],
        [data-testid="stMarkdownContainer"] div[style*="#e67e22" i] {
            color: #E67E22 !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#F39C12" i],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#f39c12" i],
        [data-testid="stExpander"] div[style*="#F39C12" i],
        [data-testid="stExpander"] div[style*="#f39c12" i],
        div[style*="#F39C12" i],
        div[style*="#f39c12" i],
        [data-testid="stMarkdownContainer"] div[style*="#F39C12" i],
        [data-testid="stMarkdownContainer"] div[style*="#f39c12" i] {
            color: #F39C12 !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#58D68D" i],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#58d68d" i],
        [data-testid="stExpander"] div[style*="#58D68D" i],
        [data-testid="stExpander"] div[style*="#58d68d" i],
        div[style*="#58D68D" i],
        div[style*="#58d68d" i],
        [data-testid="stMarkdownContainer"] div[style*="#58D68D" i],
        [data-testid="stMarkdownContainer"] div[style*="#58d68d" i] {
            color: #58D68D !important;
        }
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#27AE60" i],
        [data-testid="stAppViewContainer"] [data-testid="stExpander"] div[style*="#27ae60" i],
        [data-testid="stExpander"] div[style*="#27AE60" i],
        [data-testid="stExpander"] div[style*="#27ae60" i],
        div[style*="#27AE60" i],
        div[style*="#27ae60" i],
        [data-testid="stMarkdownContainer"] div[style*="#27AE60" i],
        [data-testid="stMarkdownContainer"] div[style*="#27ae60" i] {
            color: #27AE60 !important;
        }
        
        /* Streamlit 기본 스타일이 레벨 색상을 덮어쓰지 않도록 방어 */
        [data-testid="stExpander"] div[id^="physical-state-"],
        [data-testid="stExpander"] div[id^="mental-state-"],
        [data-testid="stExpander"] div[id^="satisfaction-"],
        [data-testid="stExpander"] div[class*="level-color"],
        [data-testid="stExpander"] div[style*="color"] {
            /* Streamlit의 기본 텍스트 색상 규칙보다 우선 */
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
    
    # CSS를 다시 주입하여 최신 순서 보장 (Streamlit 기본 스타일보다 나중에 로드)
    st.markdown(
        """
        <script>
        // Archive 페이지 CSS를 다시 주입하여 최신 순서 보장
        (function() {
            const styleId = 'archive-page-styles';
            let styleElement = document.getElementById(styleId);
            if (styleElement) {
                // 기존 스타일 제거 후 재삽입하여 순서 보장
                styleElement.remove();
            }
        })();
        </script>
        """,
        unsafe_allow_html=True
    )


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

def get_snippets_from_google_sheets(get_google_sheets_client, spreadsheet_id):
    """Google Sheets에서 Snippet 데이터를 가져옵니다."""
    try:
        client = get_google_sheets_client()
        if not client:
            return None
        
        def _fetch_records():
            spreadsheet = client.open_by_key(spreadsheet_id)
            worksheet = spreadsheet.worksheet("Sheet1")
            records = worksheet.get_all_records()
            return pd.DataFrame(records) if records else pd.DataFrame()
        
        return _sheets_call_with_retry(_fetch_records)
    except Exception as e:
        error_msg = str(e).lower()
        if _is_retryable_error(error_msg):
            st.warning("Snippet 아카이브 로드 중 호출 제한이 발생했습니다. 잠시 후 다시 시도해주세요.")
        else:
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

def _render_star_rating(value, max_stars=5, star_color=None):
    """별점을 시각적으로 표시합니다 (HTML 포함, 색상 적용).
    
    Args:
        value: 별점 값 (1-5)
        max_stars: 최대 별 개수 (기본값: 5)
        star_color: 별 색상 (기본값: None, 레벨별 색상 사용)
                     None이 아니면 지정된 색상 사용
    """
    if value is None or pd.isna(value) or value == 0:
        return '<span class="star-rating" style="color: #95A5A6 !important;">☆☆☆☆☆</span>'
    
    try:
        rating = int(float(value))
        # star_color가 지정되면 그 색상 사용, 아니면 레벨별 색상 사용
        if star_color:
            color = star_color
        else:
            color = _get_level_color(rating)
        stars_html = ""
        for i in range(max_stars):
            if i < rating:
                stars_html += '<span class="star-filled" style="color: {} !important;">★</span>'.format(color)
            else:
                stars_html += '<span class="star-empty" style="color: #CCCCCC !important;">☆</span>'
        return f'<span class="star-rating" style="color: {color} !important;">{stars_html}</span>'
    except:
        return '<span class="star-rating" style="color: #95A5A6 !important;">☆☆☆☆☆</span>'

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

def get_current_viewing_user():
    """현재 조회 중인 사용자 정보를 반환합니다.
    관리자가 다른 사용자를 선택한 경우 viewing_user_info를 반환하고,
    그렇지 않으면 현재 로그인한 user_info를 반환합니다.
    """
    if 'viewing_user_info' in st.session_state:
        return st.session_state.viewing_user_info
    return st.session_state.user_info

def render_archive_embedded(get_google_sheets_client, spreadsheet_id):
    """Snippet 아카이브 페이지 렌더링 (메인 앱 컨텍스트에서 사용)"""
    st.title("📚 Snippet 아카이브")
    st.markdown("그동안 작성한 Snippet 기록들을 확인해보세요!")
    st.markdown("---")
    
    # 현재 조회 중인 사용자 이름 표시
    viewing_user = get_current_viewing_user()
    user_name = viewing_user.get('name', '') if viewing_user else ''
    st.subheader(f"{user_name} 님의 Snippet 아카이브")
    
    # Archive 페이지 스타일 보장 (제목 이후에 주입하여 우선순위 확보)
    _ensure_archive_styles()
    
    # 데이터 가져오기 (Google Sheets 또는 로컬 CSV)
    with st.spinner("데이터를 불러오는 중..."):
        df = get_snippets_with_fallback(get_google_sheets_client, spreadsheet_id)
    
    if df is not None and not df.empty:
        # 현재 조회 중인 사용자의 데이터만 필터링
        if st.session_state.logged_in:
            viewing_user = get_current_viewing_user()
            if viewing_user:
                user_name = viewing_user['name']
                user_data = df[df['이름'] == user_name] if '이름' in df.columns else df
            else:
                user_data = df
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
                    # [Check-in] 섹션 - Level 1 색상 적용 (보라색)
                    st.markdown(
                        f'<h1 id="checkin-header-{idx}" class="section-header-level1" style="color: #9B59B6 !important; font-size: 1.5em; font-weight: 700; margin-top: 0.5em; margin-bottom: 0.5em;">[Check-in]</h1>'
                        f'<script>(function applyColorCheckin_{idx}(){{'
                        f'var el = document.getElementById("checkin-header-{idx}");'
                        f'if(el) {{ el.style.color = "#9B59B6"; el.style.setProperty("color", "#9B59B6", "important"); }}'
                        f'else {{ setTimeout(applyColorCheckin_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # 몸 상태 - Level 2 색상 적용 (밝은 파랑), 별은 항상 노란색, 같은 줄에 표시
                    if '몸상태' in row and pd.notna(row.get('몸상태')):
                        physical_value = int(float(row.get('몸상태', 0)))
                        # 별은 항상 노란색으로 고정
                        physical_stars = _render_star_rating(physical_value, star_color="#F39C12")
                        # 헤더와 별점을 같은 줄에 배치 (flexbox 사용)
                        st.markdown(
                            f'<div id="physical-container-{idx}" style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                            f'<h2 id="physical-state-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">몸 상태</h2>'
                            f'<div id="physical-stars-{idx}" style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important;">{physical_stars}</div>'
                            f'</div>'
                            f'<script>(function applyColor_{idx}(){{'
                            f'var el = document.getElementById("physical-state-{idx}");'
                            f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                            f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                            f'}})();</script>',
                            unsafe_allow_html=True
                        )
                        # 별도로 CSS 강제 적용을 위한 스크립트 주입
                        st.markdown(
                            f'<style>#physical-state-{idx} {{ color: #3498DB !important; }}</style>',
                            unsafe_allow_html=True
                        )
                    else:
                        # 헤더와 별점을 같은 줄에 배치 (flexbox 사용)
                        st.markdown(
                            f'<div id="physical-empty-container-{idx}" style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                            f'<h2 id="physical-empty-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">몸 상태</h2>'
                            f'<div style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important;">☆☆☆☆☆</div>'
                            f'</div>'
                            f'<script>(function applyColor_{idx}(){{'
                            f'var el = document.getElementById("physical-empty-{idx}");'
                            f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                            f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                            f'}})();</script>',
                            unsafe_allow_html=True
                        )
                    
                    # 마음 상태 - Level 2 색상 적용 (밝은 파랑), 별은 항상 노란색, 같은 줄에 표시
                    if '마음상태' in row and pd.notna(row.get('마음상태')):
                        mental_value = int(float(row.get('마음상태', 0)))
                        # 별은 항상 노란색으로 고정
                        mental_stars = _render_star_rating(mental_value, star_color="#F39C12")
                        # 헤더와 별점을 같은 줄에 배치 (flexbox 사용)
                        st.markdown(
                            f'<div id="mental-container-{idx}" style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                            f'<h2 id="mental-state-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">마음 상태</h2>'
                            f'<div id="mental-stars-{idx}" style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important;">{mental_stars}</div>'
                            f'</div>'
                            f'<script>(function applyColor_{idx}(){{'
                            f'var el = document.getElementById("mental-state-{idx}");'
                            f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                            f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                            f'}})();</script>',
                            unsafe_allow_html=True
                        )
                        # 별도로 CSS 강제 적용을 위한 스크립트 주입
                        st.markdown(
                            f'<style>#mental-state-{idx} {{ color: #3498DB !important; }}</style>',
                            unsafe_allow_html=True
                        )
                    else:
                        # 헤더와 별점을 같은 줄에 배치 (flexbox 사용)
                        st.markdown(
                            f'<div id="mental-empty-container-{idx}" style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                            f'<h2 id="mental-empty-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">마음 상태</h2>'
                            f'<div style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important;">☆☆☆☆☆</div>'
                            f'</div>'
                            f'<script>(function applyColor_{idx}(){{'
                            f'var el = document.getElementById("mental-empty-{idx}");'
                            f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                            f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                            f'}})();</script>',
                            unsafe_allow_html=True
                        )
                    
                    # 상태 이유 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="state-reason-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">상태 이유</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("state-reason-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    state_reason = str(row.get('상태이유', '')) if '상태이유' in row and pd.notna(row.get('상태이유')) else ''
                    state_reason_display = html.escape(state_reason.strip()) if state_reason and state_reason.strip() else "N/A"
                    st.markdown(
                        f'<div id="state-reason-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{state_reason_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("state-reason-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # 개선 방안 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="improvement-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">개선 방안</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("improvement-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    improvement_plan = str(row.get('개선방안', '')) if '개선방안' in row and pd.notna(row.get('개선방안')) else ''
                    improvement_plan_display = html.escape(improvement_plan.strip()) if improvement_plan and improvement_plan.strip() else "N/A"
                    st.markdown(
                        f'<div id="improvement-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{improvement_plan_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("improvement-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    st.markdown("---")
                    
                    # [Look-back] 섹션 - Level 1 색상 적용 (보라색)
                    st.markdown(
                        f'<h1 id="lookback-header-{idx}" class="section-header-level1" style="color: #9B59B6 !important; font-size: 1.5em; font-weight: 700; margin-top: 0.5em; margin-bottom: 0.5em;">[Look-back]</h1>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("lookback-header-{idx}");'
                        f'if(el) {{ el.style.color = "#9B59B6"; el.style.setProperty("color", "#9B59B6", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # 전날 한 일 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="yesterday-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">전날 한 일</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("yesterday-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    yesterday_work = _get_value_by_aliases(row, [
                        '전일업무','전일한일','전날 한 일','[Look-back] 전날 한 일','전일 업무','전일 업무 내용'
                    ])
                    yesterday_work_display = html.escape(yesterday_work.strip()) if yesterday_work and yesterday_work.strip() else "N/A"
                    st.markdown(
                        f'<div id="yesterday-work-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{yesterday_work_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("yesterday-work-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # 전날 만족도 - Level 2 색상 적용 (밝은 파랑), 별은 항상 노란색
                    satisfaction_raw = _get_value_by_aliases(row, [
                        '전일만족도','전날 만족도','[Look-back] 전날 만족도'
                    ])
                    if satisfaction_raw:
                        try:
                            satisfaction_value = int(float(satisfaction_raw))
                            # 별은 항상 노란색으로 고정
                            satisfaction_stars = _render_star_rating(satisfaction_value, star_color="#F39C12")
                            # 헤더와 별점을 같은 줄에 배치 (flexbox 사용, 왼쪽 정렬)
                            st.markdown(
                                f'<div id="satisfaction-container-{idx}" style="display: flex; align-items: center; justify-content: flex-start; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                                f'<h2 id="satisfaction-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">전날 만족도</h2>'
                                f'<div id="satisfaction-stars-{idx}" style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important; font-size: 1.2em !important;">{satisfaction_stars}</div>'
                                f'</div>'
                                f'<script>(function applyColorSat_{idx}(){{'
                                f'var el = document.getElementById("satisfaction-{idx}");'
                                f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); el.style.fontSize = "1.3em"; el.style.setProperty("font-size", "1.3em", "important"); }}'
                                f'var allSatisfactionHeaders = document.querySelectorAll("h2[id^=\\"satisfaction-\\"]");'
                                f'allSatisfactionHeaders.forEach(function(h) {{ h.style.fontSize = "1.3em"; h.style.setProperty("font-size", "1.3em", "important"); }});'
                                f'if(!el) {{ setTimeout(applyColorSat_{idx}, 50); }}'
                                f'}})();</script>',
                                unsafe_allow_html=True
                            )
                            # 별도로 CSS 강제 적용을 위한 스크립트 주입
                            st.markdown(
                                f'<style>#satisfaction-{idx} {{ color: #3498DB !important; font-size: 1.3em !important; }}</style>',
                                unsafe_allow_html=True
                            )
                        except Exception:
                            # 헤더와 별점을 같은 줄에 배치 (flexbox 사용, 왼쪽 정렬)
                            st.markdown(
                                f'<div id="satisfaction-empty-container-{idx}" style="display: flex; align-items: center; justify-content: flex-start; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                                f'<h2 id="satisfaction-empty-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">전날 만족도</h2>'
                                f'<div style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important; font-size: 1.2em !important;">☆☆☆☆☆</div>'
                                f'</div>'
                                f'<script>(function applyColor_{idx}(){{'
                                f'var el = document.getElementById("satisfaction-empty-{idx}");'
                                f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); el.style.fontSize = "1.3em"; el.style.setProperty("font-size", "1.3em", "important"); }}'
                                f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                                f'}})();</script>',
                                unsafe_allow_html=True
                            )
                    else:
                        # 헤더와 별점을 같은 줄에 배치 (flexbox 사용, 왼쪽 정렬)
                        st.markdown(
                            f'<div id="satisfaction-empty-container-{idx}" style="display: flex; align-items: center; justify-content: flex-start; margin-top: 0.8rem; margin-bottom: 0; gap: 0.5rem;">'
                            f'<h2 id="satisfaction-empty-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em !important; font-weight: 600; margin: 0 !important; padding: 0 !important; flex: 0 0 auto;">전날 만족도</h2>'
                            f'<div style="flex: 0 0 auto; margin: 0 !important; padding: 0 !important; line-height: 1 !important; font-size: 1.2em !important;">☆☆☆☆☆</div>'
                            f'</div>'
                            f'<script>(function applyColor_{idx}(){{'
                            f'var el = document.getElementById("satisfaction-empty-{idx}");'
                            f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); el.style.fontSize = "1.3em"; el.style.setProperty("font-size", "1.3em", "important"); }}'
                            f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                            f'}})();</script>',
                            unsafe_allow_html=True
                        )
                    
                    # [Liked] 좋았던 점 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="liked-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">[Liked] 좋았던 점</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("liked-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    liked = _get_value_by_aliases(row, ['좋았던점','[Liked] 좋았던 점','Liked','좋았던 점'])
                    liked_display = html.escape(liked.strip()) if liked and liked.strip() else "N/A"
                    st.markdown(
                        f'<div id="liked-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{liked_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("liked-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # [Lacked] 아쉬웠던 점 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="lacked-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">[Lacked] 아쉬웠던 점</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("lacked-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    lacked = _get_value_by_aliases(row, ['아쉬웠던점','[Lacked] 아쉬웠던 점','Lacked','아쉬웠던 점'])
                    lacked_display = html.escape(lacked.strip()) if lacked and lacked.strip() else "N/A"
                    st.markdown(
                        f'<div id="lacked-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{lacked_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("lacked-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # [Learned] 배운점/성장포인트 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="learned-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">[Learned] 배운점/성장포인트</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("learned-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    learned = _get_value_by_aliases(row, ['배웠던점','[Learned] 배운점/성장포인트','Learned','배운 점','배운점'])
                    learned_display = html.escape(learned.strip()) if learned and learned.strip() else "N/A"
                    st.markdown(
                        f'<div id="learned-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{learned_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("learned-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # [Looked-Forward] 향후 시도할 점 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="looked-forward-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">[Looked-Forward] 향후 시도할 점</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("looked-forward-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    looked_forward = _get_value_by_aliases(row, ['향후시도','[Looked-Forward] 향후 시도할 점','Looked-Forward','LookedForward','향후 시도'])
                    looked_forward_display = html.escape(looked_forward.strip()) if looked_forward and looked_forward.strip() else "N/A"
                    st.markdown(
                        f'<div id="looked-forward-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{looked_forward_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("looked-forward-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # [Longed-For] 요청사항 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="longed-for-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">[Longed-For] 요청사항</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("longed-for-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    longed_for = _get_value_by_aliases(row, ['바라는점','[Longed-For] 요청사항','Longed-For','LongedFor','요청 사항','요청사항'])
                    longed_for_display = html.escape(longed_for.strip()) if longed_for and longed_for.strip() else "N/A"
                    st.markdown(
                        f'<div id="longed-for-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{longed_for_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("longed-for-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # 동료 칭찬 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="colleague-praise-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">동료 칭찬</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("colleague-praise-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    colleague_praise = _get_value_by_aliases(row, ['동료칭찬','동료 칭찬','[Praise] 동료 칭찬'])
                    colleague_praise_display = html.escape(colleague_praise.strip()) if colleague_praise and colleague_praise.strip() else "N/A"
                    st.markdown(
                        f'<div id="colleague-praise-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{colleague_praise_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("colleague-praise-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    st.markdown("---")
                    
                    # [Today's Plan] 섹션 - Level 1 색상 적용 (보라색)
                    st.markdown(
                        f'<h1 id="plan-header-{idx}" class="section-header-level1" style="color: #9B59B6 !important; font-size: 1.5em; font-weight: 700; margin-top: 0.5em; margin-bottom: 0.5em;">[Today\'s Plan]</h1>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("plan-header-{idx}");'
                        f'if(el) {{ el.style.color = "#9B59B6"; el.style.setProperty("color", "#9B59B6", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    
                    # 당일 계획 - Level 2 색상 적용 (밝은 파랑)
                    st.markdown(
                        f'<h2 id="today-plan-{idx}" class="section-header-level2" style="color: #3498DB !important; font-size: 1.3em; font-weight: 600; margin-top: 0.5em; margin-bottom: 0.5em;">당일 계획</h2>'
                        f'<script>(function applyColor_{idx}(){{'
                        f'var el = document.getElementById("today-plan-{idx}");'
                        f'if(el) {{ el.style.color = "#3498DB"; el.style.setProperty("color", "#3498DB", "important"); }}'
                        f'else {{ setTimeout(applyColor_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )
                    today_plans = str(row.get('오늘할일', '')) if '오늘할일' in row and pd.notna(row.get('오늘할일')) else ''
                    today_plans_display = html.escape(today_plans.strip()) if today_plans and today_plans.strip() else "N/A"
                    st.markdown(
                        f'<div id="today-plan-content-{idx}" style="padding-left: 2rem !important; margin-left: 0 !important; white-space: pre-line !important;">{today_plans_display}</div>'
                        f'<script>(function applyIndent_{idx}(){{'
                        f'var el = document.getElementById("today-plan-content-{idx}");'
                        f'if(el) {{ el.style.paddingLeft = "2rem"; el.style.setProperty("padding-left", "2rem", "important"); el.style.marginLeft = "0"; el.style.setProperty("margin-left", "0", "important"); el.style.whiteSpace = "pre-line"; el.style.setProperty("white-space", "pre-line", "important"); }}'
                        f'else {{ setTimeout(applyIndent_{idx}, 50); }}'
                        f'}})();</script>',
                        unsafe_allow_html=True
                    )

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
                        '[Looked-Forward] 향후 시도할 점','Looked-Forward','LookedForward','향후 시도',
                        '[Longed-For] 요청사항','Longed-For','LongedFor','요청 사항','요청사항',
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
                            value_display = str(value).strip() if value and str(value).strip() else "N/A"
                            st.markdown(f"**{label}**: {value_display}")
            
            # 모든 카드 렌더링 후 레벨별 색상 동적 적용 (Streamlit 기본 스타일 덮어쓰기 방지)
            st.markdown(
                """
                <script>
                (function() {
                    // 레벨별 색상 매핑
                    const levelColors = {
                        1: '#E74C3C',  // 빨간색
                        2: '#E67E22',  // 주황색
                        3: '#F39C12',  // 노란색
                        4: '#58D68D',  // 연두색
                        5: '#27AE60'   // 초록색
                    };
                    
                    // 레벨별 색상 적용 함수 - 인라인 스타일을 강제로 덮어쓰기
                    function applyLevelColors() {
                        // 먼저 expander 안의 요소부터 처리 (우선순위 높음)
                        
                        // Level 1 헤더 (보라색) - [Check-in], [Look-back], [Today's Plan]
                        // expander 안의 h1만 타겟팅
                        const level1Headers = document.querySelectorAll('[data-testid="stExpander"] h1, .section-header-level1, h1.section-header-level1, h1[id^="checkin-header-"], h1[id^="lookback-header-"], h1[id^="plan-header-"]');
                        level1Headers.forEach(el => {
                            const text = el.textContent || el.innerText || '';
                            const id = el.id || '';
                            const isInExpander = el.closest('[data-testid="stExpander"]');
                            // expander 안에 있고 Level 1 섹션 헤더인 경우에만 보라색 적용
                            if (isInExpander && (text.includes('[Check-in]') || text.includes('[Look-back]') || text.includes("[Today's Plan]") || 
                                id.includes('checkin-header') || id.includes('lookback-header') || id.includes('plan-header') ||
                                el.classList.contains('section-header-level1'))) {
                                el.style.color = '#9B59B6';
                                el.style.setProperty('color', '#9B59B6', 'important');
                                // 내부 요소도 색상 적용
                                const children = el.querySelectorAll('*');
                                children.forEach(child => {
                                    child.style.color = '#9B59B6';
                                    child.style.setProperty('color', '#9B59B6', 'important');
                                });
                            }
                        });
                        
                        // Level 2 섹션 항목 (밝은 파랑) - expander 안의 h2만 타겟팅
                        const level2Headers = document.querySelectorAll('[data-testid="stExpander"] h2, .section-header-level2, h2.section-header-level2, h2[id^="state-reason-"], h2[id^="improvement-"], h2[id^="yesterday-"], h2[id^="liked-"], h2[id^="lacked-"], h2[id^="learned-"], h2[id^="looked-forward-"], h2[id^="longed-for-"], h2[id^="colleague-praise-"], h2[id^="today-plan-"], h2[id^="physical-state-"], h2[id^="physical-empty-"], h2[id^="mental-state-"], h2[id^="mental-empty-"], h2[id^="satisfaction-"], h2[id^="satisfaction-empty-"]');
                        level2Headers.forEach(el => {
                            const isInExpander = el.closest('[data-testid="stExpander"]');
                            // expander 안에 있는 h2만 밝은 파랑 적용
                            if (isInExpander) {
                            el.style.color = '#3498DB';
                            el.style.setProperty('color', '#3498DB', 'important');
                                // "전날 만족도" 헤더의 폰트 크기 강제 설정
                                if (el.id && (el.id.startsWith('satisfaction-') || el.id.startsWith('satisfaction-empty-'))) {
                                    el.style.fontSize = '1.3em';
                                    el.style.setProperty('font-size', '1.3em', 'important');
                                }
                            // 내부 요소도 색상 적용
                            const children = el.querySelectorAll('*');
                            children.forEach(child => {
                                child.style.color = '#3498DB';
                                child.style.setProperty('color', '#3498DB', 'important');
                            });
                            }
                        });
                        
                        // 이제 expander 밖의 요소 처리
                        
                        // 최상단 헤더 (페이지 제목) - 검정색
                        // expander 밖에 있는 h1만 타겟팅
                        const allH1s = document.querySelectorAll('h1');
                        allH1s.forEach((h1, index) => {
                            const text = (h1.textContent || h1.innerText || '').trim();
                            const isInExpander = h1.closest('[data-testid="stExpander"]');
                            // expander 밖에 있고, 첫 번째 h1이거나 "Snippet 아카이브"를 포함하는 경우
                            if (!isInExpander && (index === 0 || text.includes('Snippet 아카이브') || text.includes('📚'))) {
                                h1.style.color = '#000000';
                                h1.style.setProperty('color', '#000000', 'important');
                                const children = h1.querySelectorAll('*');
                                children.forEach(child => {
                                    child.style.color = '#000000';
                                    child.style.setProperty('color', '#000000', 'important');
                                });
                            }
                        });
                        
                        // 서브 헤더 (사용자 정보) - 회색
                        // expander 밖에 있는 h2만 타겟팅
                        const allH2s = document.querySelectorAll('h2');
                        allH2s.forEach((h2, index) => {
                            const text = (h2.textContent || h2.innerText || '').trim();
                            const isInExpander = h2.closest('[data-testid="stExpander"]');
                            // expander 밖에 있고, 첫 번째 h2이거나 "님의 Snippet 아카이브"를 포함하는 경우
                            if (!isInExpander && (index === 0 || text.includes('님의 Snippet 아카이브'))) {
                                h2.style.color = '#666666';
                                h2.style.setProperty('color', '#666666', 'important');
                                const children = h2.querySelectorAll('*');
                                children.forEach(child => {
                                    child.style.color = '#666666';
                                    child.style.setProperty('color', '#666666', 'important');
                                });
                            }
                        });
                        
                        // data-level 속성 기반으로 찾기 (다른 요소들에만 적용, 몸 상태/마음 상태/전날 만족도는 제외)
                        // 주의: 몸 상태, 마음 상태, 전날 만족도는 이제 h2로 변경되어 Level 2 색상으로 처리됨
                        for (let level = 1; level <= 5; level++) {
                            const color = levelColors[level];
                            
                            // 모든 가능한 선택자로 요소 찾기 (h2는 제외 - Level 2로 별도 처리)
                            const selectors = [
                                `div[data-level="${level}"]:not(h2)`,
                                `.level-color-${level}:not(h2)`,
                                `div.level-color-${level}:not(h2)`
                            ];
                            
                            selectors.forEach(selector => {
                                try {
                                    const elements = document.querySelectorAll(selector);
                                    elements.forEach(el => {
                                        // class나 data-level을 확인하여 올바른 레벨인지 검증
                                        const elLevel = el.getAttribute('data-level') || 
                                                      (el.className && el.className.match(/level-color-(\\d+)/) ? 
                                                       parseInt(el.className.match(/level-color-(\\d+)/)[1]) : null);
                                        if (elLevel == level || selector.includes(`level-${level}`) || selector.includes(`[data-level="${level}"]`)) {
                                            // 인라인 스타일을 직접 수정 (가장 확실한 방법)
                                            el.style.color = color;
                                            el.style.setProperty('color', color, 'important');
                                            // computed style도 강제 적용
                                            try {
                                                const computed = window.getComputedStyle(el);
                                                if (computed.color !== color && computed.color !== color.toLowerCase()) {
                                                    el.style.color = color;
                                                    el.style.setProperty('color', color, 'important');
                                                }
                                            } catch(e) {
                                                // 무시
                                            }
                                            // 속성도 직접 설정
                                            if (!el.hasAttribute('data-level')) {
                                                el.setAttribute('data-level', level.toString());
                                            }
                                        }
                                    });
                                } catch(e) {
                                    // 무시
                                }
                            });
                            
                            // ID 기반 직접 적용
                            const allDivs = document.querySelectorAll('div[id^="physical-state-"], div[id^="mental-state-"], div[id^="satisfaction-"]');
                            allDivs.forEach(el => {
                                const elLevel = el.getAttribute('data-level');
                                const classMatch = el.className && el.className.match(/level-color-(\\d+)/);
                                const elLevelFromClass = classMatch ? parseInt(classMatch[1]) : null;
                                const finalLevel = elLevel || elLevelFromClass;
                                if (finalLevel == level) {
                                    el.style.color = color;
                                    el.style.setProperty('color', color, 'important');
                                }
                            });
                        }
                        
                        // 텍스트 줄간격 강제로 줄이기
                        const textElements = document.querySelectorAll('[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p, [data-testid="stExpander"] [data-testid="stMarkdownContainer"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]), [data-testid="stExpander"] p, [data-testid="stExpander"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]):not(h1):not(h2), [data-testid="stExpander"] span');
                        textElements.forEach(el => {
                            // 헤더가 아닌 텍스트 요소만
                            if (el.tagName !== 'H1' && el.tagName !== 'H2') {
                                el.style.lineHeight = '1.2';
                                el.style.setProperty('line-height', '1.2', 'important');
                                el.style.marginTop = '0';
                                el.style.setProperty('margin-top', '0', 'important');
                                el.style.marginBottom = '0';
                                el.style.setProperty('margin-bottom', '0', 'important');
                                el.style.paddingTop = '0';
                                el.style.setProperty('padding-top', '0', 'important');
                                el.style.paddingBottom = '0';
                                el.style.setProperty('padding-bottom', '0', 'important');
                                
                                // 내부 모든 요소에도 적용
                                el.querySelectorAll('*').forEach(child => {
                                    child.style.lineHeight = '1.2';
                                    child.style.setProperty('line-height', '1.2', 'important');
                                    child.style.marginTop = '0';
                                    child.style.setProperty('margin-top', '0', 'important');
                                    child.style.marginBottom = '0';
                                    child.style.setProperty('margin-bottom', '0', 'important');
                                });
                            }
                        });
                        
                        // 세부 내용 div에 직접 들여쓰기 적용 (ID로 찾기) - 강력한 적용
                        function applyContentIndent() {
                            const contentDivs = document.querySelectorAll('[data-testid="stExpander"] div[id^="state-reason-content-"], [data-testid="stExpander"] div[id^="improvement-content-"], [data-testid="stExpander"] div[id^="yesterday-work-content-"], [data-testid="stExpander"] div[id^="liked-content-"], [data-testid="stExpander"] div[id^="lacked-content-"], [data-testid="stExpander"] div[id^="learned-content-"], [data-testid="stExpander"] div[id^="looked-forward-content-"], [data-testid="stExpander"] div[id^="longed-for-content-"], [data-testid="stExpander"] div[id^="colleague-praise-content-"], [data-testid="stExpander"] div[id^="today-plan-content-"]');
                            contentDivs.forEach(div => {
                                div.style.paddingLeft = '2rem';
                                div.style.setProperty('padding-left', '2rem', 'important');
                                div.style.marginLeft = '0';
                                div.style.setProperty('margin-left', '0', 'important');
                                div.style.whiteSpace = 'pre-line';
                                div.style.setProperty('white-space', 'pre-line', 'important');
                                // 부모 MarkdownContainer에도 적용
                                let parent = div.parentElement;
                                let depth = 0;
                                while (parent && depth < 5) {
                                    if (parent.getAttribute('data-testid') === 'stMarkdownContainer') {
                                        parent.style.paddingLeft = '2rem';
                                        parent.style.setProperty('padding-left', '2rem', 'important');
                                        parent.style.marginLeft = '0';
                                        parent.style.setProperty('margin-left', '0', 'important');
                                        break;
                                    }
                                    parent = parent.parentElement;
                                    depth++;
                                }
                            });
                            
                            // h2 다음에 오는 MarkdownContainer에도 직접 적용
                            const level2Headers = document.querySelectorAll('[data-testid="stExpander"] h2[id^="state-reason-"], [data-testid="stExpander"] h2[id^="improvement-"], [data-testid="stExpander"] h2[id^="yesterday-"], [data-testid="stExpander"] h2[id^="liked-"], [data-testid="stExpander"] h2[id^="lacked-"], [data-testid="stExpander"] h2[id^="learned-"], [data-testid="stExpander"] h2[id^="looked-forward-"], [data-testid="stExpander"] h2[id^="longed-for-"], [data-testid="stExpander"] h2[id^="colleague-praise-"], [data-testid="stExpander"] h2[id^="today-plan-"]');
                            level2Headers.forEach(header => {
                                let next = header.nextElementSibling;
                                let count = 0;
                                while (next && count < 3) {
                                    if (next.getAttribute('data-testid') === 'stMarkdownContainer') {
                                        next.style.paddingLeft = '2rem';
                                        next.style.setProperty('padding-left', '2rem', 'important');
                                        next.style.marginLeft = '0';
                                        next.style.setProperty('margin-left', '0', 'important');
                                        break;
                                    }
                                    next = next.nextElementSibling;
                                    count++;
                                }
                            });
                        }
                        applyContentIndent();
                        
                        // flexbox 컨테이너 스타일 강제 적용 (별점과 헤더를 같은 줄에 배치)
                        const flexContainers = document.querySelectorAll('[data-testid="stExpander"] div[id^="physical-container-"], [data-testid="stExpander"] div[id^="physical-empty-container-"], [data-testid="stExpander"] div[id^="mental-container-"], [data-testid="stExpander"] div[id^="mental-empty-container-"], [data-testid="stExpander"] div[id^="satisfaction-container-"], [data-testid="stExpander"] div[id^="satisfaction-empty-container-"]');
                        flexContainers.forEach(container => {
                            container.style.display = 'flex';
                            container.style.setProperty('display', 'flex', 'important');
                            container.style.alignItems = 'center';
                            container.style.setProperty('align-items', 'center', 'important');
                            // 전날 만족도는 왼쪽 정렬, 나머지는 기존 유지 (space-between)
                            const isSatisfaction = container.id && (container.id.startsWith('satisfaction-container-') || container.id.startsWith('satisfaction-empty-container-'));
                            container.style.justifyContent = isSatisfaction ? 'flex-start' : 'space-between';
                            container.style.setProperty('justify-content', isSatisfaction ? 'flex-start' : 'space-between', 'important');
                            container.style.gap = '0.5rem';
                            container.style.setProperty('gap', '0.5rem', 'important');
                            
                            // 내부 헤더 스타일 (모든 Level 2 헤더 크기 통일)
                            const header = container.querySelector('h2');
                            if (header) {
                                header.style.margin = '0';
                                header.style.setProperty('margin', '0', 'important');
                                header.style.padding = '0';
                                header.style.setProperty('padding', '0', 'important');
                                header.style.flex = '0 0 auto';
                                header.style.setProperty('flex', '0 0 auto', 'important');
                                // 모든 Level 2 헤더 크기 통일 (1.3em)
                                header.style.fontSize = '1.3em';
                                header.style.setProperty('font-size', '1.3em', 'important');
                            }
                            
                            // 내부 별점 컨테이너 스타일 (모든 별점 크기 통일)
                            const starContainer = container.querySelector('div:last-child');
                            if (starContainer && starContainer !== header) {
                                starContainer.style.flex = '0 0 auto';
                                starContainer.style.setProperty('flex', '0 0 auto', 'important');
                                starContainer.style.margin = '0';
                                starContainer.style.setProperty('margin', '0', 'important');
                                starContainer.style.padding = '0';
                                starContainer.style.setProperty('padding', '0', 'important');
                                starContainer.style.lineHeight = '1';
                                starContainer.style.setProperty('line-height', '1', 'important');
                                // 모든 별점 크기 통일 (1.2em)
                                starContainer.style.fontSize = '1.2em';
                                starContainer.style.setProperty('font-size', '1.2em', 'important');
                                // 별점 내부 요소도 크기 설정
                                const starRating = starContainer.querySelector('.star-rating');
                                if (starRating) {
                                    starRating.style.fontSize = '1.2em';
                                    starRating.style.setProperty('font-size', '1.2em', 'important');
                                }
                            }
                        });
                        
                        // 별점과 헤더 사이 간격 완전 제거
                        const headers = document.querySelectorAll('[data-testid="stExpander"] h2[id^="physical-state-"], [data-testid="stExpander"] h2[id^="physical-empty-"], [data-testid="stExpander"] h2[id^="mental-state-"], [data-testid="stExpander"] h2[id^="mental-empty-"], [data-testid="stExpander"] h2[id^="satisfaction-"], [data-testid="stExpander"] h2[id^="satisfaction-empty-"]');
                        headers.forEach(header => {
                            // 헤더 하단 마진 완전 제거
                            header.style.marginBottom = '0';
                            header.style.setProperty('margin-bottom', '0', 'important');
                            header.style.paddingBottom = '0';
                            header.style.setProperty('padding-bottom', '0', 'important');
                            
                            // 헤더 다음 모든 요소 확인
                            let currentEl = header.nextElementSibling;
                            let checkedCount = 0;
                            // 최대 3개까지 확인 (별점을 찾을 때까지)
                            while (currentEl && checkedCount < 3) {
                                // div나 MarkdownContainer인 경우
                                if (currentEl.tagName === 'DIV' || currentEl.getAttribute('data-testid') === 'stMarkdownContainer') {
                                    currentEl.style.marginTop = '0';
                                    currentEl.style.setProperty('margin-top', '0', 'important');
                                    currentEl.style.paddingTop = '0';
                                    currentEl.style.setProperty('padding-top', '0', 'important');
                                    currentEl.style.lineHeight = '1';
                                    currentEl.style.setProperty('line-height', '1', 'important');
                                    
                                    // 내부에 별점이 있는지 확인
                                    const starRating = currentEl.querySelector('.star-rating');
                                    if (starRating) {
                                        starRating.style.marginTop = '0';
                                        starRating.style.setProperty('margin-top', '0', 'important');
                                        starRating.style.paddingTop = '0';
                                        starRating.style.setProperty('padding-top', '0', 'important');
                                        starRating.style.lineHeight = '1';
                                        starRating.style.setProperty('line-height', '1', 'important');
                                        break; // 별점을 찾았으면 중단
                                    }
                                }
                                // 별점이 직접 다음에 오는 경우
                                if (currentEl.classList && currentEl.classList.contains('star-rating')) {
                                    currentEl.style.marginTop = '0';
                                    currentEl.style.setProperty('margin-top', '0', 'important');
                                    currentEl.style.paddingTop = '0';
                                    currentEl.style.setProperty('padding-top', '0', 'important');
                                    break;
                                }
                                
                                currentEl = currentEl.nextElementSibling;
                                checkedCount++;
                            }
                        });
                    }
                    
                    // DOM이 로드된 후 실행
                    function runApplyColors() {
                        applyLevelColors();
                        // Streamlit의 iframe 내에서 실행될 수도 있으므로 window.parent도 확인
                        if (window.parent && window.parent !== window) {
                            try {
                                const parentDoc = window.parent.document;
                                if (parentDoc) {
                                    // parent 문서에서도 실행
                                    const parentScript = parentDoc.createElement('script');
                                    parentScript.textContent = `
                                        (function() {
                                            const levelColors = {
                                                1: '#E74C3C', 2: '#E67E22', 3: '#F39C12', 4: '#58D68D', 5: '#27AE60'
                                            };
                                            for (let level = 1; level <= 5; level++) {
                                                const color = levelColors[level];
                                                document.querySelectorAll(`div[data-level="${level}"], .level-color-${level}`).forEach(el => {
                                                    el.style.setProperty('color', color, 'important');
                                                });
                                            }
                                        })();
                                    `;
                                    parentDoc.head.appendChild(parentScript);
                                    setTimeout(() => parentDoc.head.removeChild(parentScript), 100);
                                }
                            } catch(e) {
                                // cross-origin 등으로 접근 불가시 무시
                            }
                        }
                    }
                    
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', runApplyColors);
                    } else {
                        runApplyColors();
                    }
                    
                    // MutationObserver로 동적 추가되는 요소도 감지
                    const observer = new MutationObserver(function(mutations) {
                        applyLevelColors();
                    });
                    
                    observer.observe(document.body, {
                        childList: true,
                        subtree: true,
                        attributes: true,
                        attributeFilter: ['class', 'data-level', 'style']
                    });
                    
                    // 여러 시점에서 재적용 (Streamlit 렌더링 완료 대기)
                    [50, 100, 200, 300, 500, 1000, 2000, 3000].forEach(delay => {
                        setTimeout(applyLevelColors, delay);
                    });
                    
                    // 주기적으로 체크하여 Streamlit이 스타일을 덮어쓰는 것을 방지
                    setInterval(function() {
                        applyLevelColors();
                        // 들여쓰기도 주기적으로 재적용
                        const contentDivs = document.querySelectorAll('[data-testid="stExpander"] div[id^="state-reason-content-"], [data-testid="stExpander"] div[id^="improvement-content-"], [data-testid="stExpander"] div[id^="yesterday-work-content-"], [data-testid="stExpander"] div[id^="liked-content-"], [data-testid="stExpander"] div[id^="lacked-content-"], [data-testid="stExpander"] div[id^="learned-content-"], [data-testid="stExpander"] div[id^="looked-forward-content-"], [data-testid="stExpander"] div[id^="longed-for-content-"], [data-testid="stExpander"] div[id^="colleague-praise-content-"], [data-testid="stExpander"] div[id^="today-plan-content-"]');
                        contentDivs.forEach(div => {
                            div.style.paddingLeft = '2rem';
                            div.style.setProperty('padding-left', '2rem', 'important');
                            const parent = div.closest('[data-testid="stMarkdownContainer"]');
                            if (parent) {
                                parent.style.paddingLeft = '2rem';
                                parent.style.setProperty('padding-left', '2rem', 'important');
                            }
                        });
                    }, 200);
                    
                    // 추가로 Level 1, Level 2 헤더 색상 강제 적용 함수
                    function forceHeaderColors() {
                        // 먼저 expander 안의 요소 처리
                        
                        // Level 1 섹션 제목 ([Check-in], [Look-back], [Today's Plan]) - 보라색
                        const h1Elements = document.querySelectorAll('h1.section-header-level1, h1[id^="checkin-header-"], h1[id^="lookback-header-"], h1[id^="plan-header-"], [data-testid="stExpander"] h1');
                        h1Elements.forEach(el => {
                            const text = (el.textContent || el.innerText || '').trim();
                            const id = el.id || '';
                            const isInExpander = el.closest('[data-testid="stExpander"]');
                            // expander 안에 있고 Level 1 섹션 헤더인 경우에만 보라색 적용
                            if (isInExpander && (text.includes('[Check-in]') || text.includes('[Look-back]') || text.includes("[Today's Plan]") ||
                                id.includes('checkin-header') || id.includes('lookback-header') || id.includes('plan-header') ||
                                el.classList.contains('section-header-level1'))) {
                                el.style.color = '#9B59B6';
                                el.style.setProperty('color', '#9B59B6', 'important');
                                el.querySelectorAll('*').forEach(child => {
                                    child.style.color = '#9B59B6';
                                    child.style.setProperty('color', '#9B59B6', 'important');
                                });
                            }
                        });
                        
                        // Level 2 섹션 항목 (밝은 파랑) - 몸 상태, 마음 상태, 상태 이유, 개선 방안, 전날 한 일 등
                        const h2Elements = document.querySelectorAll('h2.section-header-level2, h2[id^="state-reason-"], h2[id^="improvement-"], h2[id^="yesterday-"], h2[id^="liked-"], h2[id^="lacked-"], h2[id^="learned-"], h2[id^="looked-forward-"], h2[id^="longed-for-"], h2[id^="colleague-praise-"], h2[id^="today-plan-"], h2[id^="physical-state-"], h2[id^="physical-empty-"], h2[id^="mental-state-"], h2[id^="mental-empty-"], h2[id^="satisfaction-"], h2[id^="satisfaction-empty-"], [data-testid="stExpander"] h2');
                        h2Elements.forEach(el => {
                            const isInExpander = el.closest('[data-testid="stExpander"]');
                            // expander 안에 있는 h2만 밝은 파랑 적용
                            if (isInExpander) {
                                el.style.color = '#3498DB';
                                el.style.setProperty('color', '#3498DB', 'important');
                                // "전날 만족도" 헤더의 폰트 크기 강제 설정
                                if (el.id && (el.id.startsWith('satisfaction-') || el.id.startsWith('satisfaction-empty-'))) {
                                    el.style.fontSize = '1.3em';
                                    el.style.setProperty('font-size', '1.3em', 'important');
                                }
                                el.querySelectorAll('*').forEach(child => {
                                    child.style.color = '#3498DB';
                                    child.style.setProperty('color', '#3498DB', 'important');
                                });
                            }
                        });
                        
                        // 이제 expander 밖의 요소 처리
                        
                        // 최상단 헤더 (페이지 제목: "📚 Snippet 아카이브") - 검정색
                        const allH1s = document.querySelectorAll('h1');
                        allH1s.forEach((h1, index) => {
                            const text = (h1.textContent || h1.innerText || '').trim();
                            const isInExpander = h1.closest('[data-testid="stExpander"]');
                            // expander 밖에 있고, 첫 번째 h1이거나 "Snippet 아카이브"를 포함하는 경우
                            if (!isInExpander && (index === 0 || text.includes('Snippet 아카이브') || text.includes('📚'))) {
                                h1.style.color = '#000000';
                                h1.style.setProperty('color', '#000000', 'important');
                                h1.querySelectorAll('*').forEach(child => {
                                    child.style.color = '#000000';
                                    child.style.setProperty('color', '#000000', 'important');
                                });
                            }
                        });
                        
                        // 서브 헤더 (사용자 정보: "XXX 님의 Snippet 아카이브") - 회색
                        const allH2s = document.querySelectorAll('h2');
                        allH2s.forEach((h2, index) => {
                            const text = (h2.textContent || h2.innerText || '').trim();
                            const isInExpander = h2.closest('[data-testid="stExpander"]');
                            // expander 밖에 있고, 첫 번째 h2이거나 "님의 Snippet 아카이브"를 포함하는 경우
                            if (!isInExpander && (index === 0 || text.includes('님의 Snippet 아카이브'))) {
                                h2.style.color = '#666666';
                                h2.style.setProperty('color', '#666666', 'important');
                                h2.querySelectorAll('*').forEach(child => {
                                    child.style.color = '#666666';
                                    child.style.setProperty('color', '#666666', 'important');
                                });
                            }
                        });
                        
                        // 세부 내용 div에 직접 들여쓰기 적용 (forceHeaderColors - ID로 찾기)
                        const contentDivs2 = document.querySelectorAll('[data-testid="stExpander"] div[id^="state-reason-content-"], [data-testid="stExpander"] div[id^="improvement-content-"], [data-testid="stExpander"] div[id^="yesterday-work-content-"], [data-testid="stExpander"] div[id^="liked-content-"], [data-testid="stExpander"] div[id^="lacked-content-"], [data-testid="stExpander"] div[id^="learned-content-"], [data-testid="stExpander"] div[id^="looked-forward-content-"], [data-testid="stExpander"] div[id^="longed-for-content-"], [data-testid="stExpander"] div[id^="colleague-praise-content-"], [data-testid="stExpander"] div[id^="today-plan-content-"]');
                        contentDivs2.forEach(div => {
                            div.style.paddingLeft = '2rem';
                            div.style.setProperty('padding-left', '2rem', 'important');
                            div.style.marginLeft = '0';
                            div.style.setProperty('margin-left', '0', 'important');
                            // 부모 MarkdownContainer에도 적용
                            const parent = div.closest('[data-testid="stMarkdownContainer"]');
                            if (parent) {
                                parent.style.paddingLeft = '2rem';
                                parent.style.setProperty('padding-left', '2rem', 'important');
                            }
                        });
                        
                        // 텍스트 줄간격 강제로 줄이기
                        const textElements = document.querySelectorAll('[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p, [data-testid="stExpander"] [data-testid="stMarkdownContainer"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]), [data-testid="stExpander"] p, [data-testid="stExpander"] div:not([class*="star"]):not([id^="physical"]):not([id^="mental"]):not([id^="satisfaction"]):not(h1):not(h2), [data-testid="stExpander"] span');
                        textElements.forEach(el => {
                            // 헤더가 아닌 텍스트 요소만
                            if (el.tagName !== 'H1' && el.tagName !== 'H2') {
                                el.style.lineHeight = '1.2';
                                el.style.setProperty('line-height', '1.2', 'important');
                                el.style.marginTop = '0';
                                el.style.setProperty('margin-top', '0', 'important');
                                el.style.marginBottom = '0';
                                el.style.setProperty('margin-bottom', '0', 'important');
                                el.style.paddingTop = '0';
                                el.style.setProperty('padding-top', '0', 'important');
                                el.style.paddingBottom = '0';
                                el.style.setProperty('padding-bottom', '0', 'important');
                                
                                // 내부 모든 요소에도 적용
                                el.querySelectorAll('*').forEach(child => {
                                    child.style.lineHeight = '1.2';
                                    child.style.setProperty('line-height', '1.2', 'important');
                                    child.style.marginTop = '0';
                                    child.style.setProperty('margin-top', '0', 'important');
                                    child.style.marginBottom = '0';
                                    child.style.setProperty('margin-bottom', '0', 'important');
                                });
                            }
                        });
                        
                        // flexbox 컨테이너 스타일 강제 적용 (forceHeaderColors)
                        const flexContainers2 = document.querySelectorAll('[data-testid="stExpander"] div[id^="physical-container-"], [data-testid="stExpander"] div[id^="physical-empty-container-"], [data-testid="stExpander"] div[id^="mental-container-"], [data-testid="stExpander"] div[id^="mental-empty-container-"], [data-testid="stExpander"] div[id^="satisfaction-container-"], [data-testid="stExpander"] div[id^="satisfaction-empty-container-"]');
                        flexContainers2.forEach(container => {
                            container.style.display = 'flex';
                            container.style.setProperty('display', 'flex', 'important');
                            container.style.alignItems = 'center';
                            container.style.setProperty('align-items', 'center', 'important');
                            // 전날 만족도는 왼쪽 정렬, 나머지는 기존 유지 (space-between)
                            const isSatisfaction = container.id && (container.id.startsWith('satisfaction-container-') || container.id.startsWith('satisfaction-empty-container-'));
                            container.style.justifyContent = isSatisfaction ? 'flex-start' : 'space-between';
                            container.style.setProperty('justify-content', isSatisfaction ? 'flex-start' : 'space-between', 'important');
                            container.style.gap = '0.5rem';
                            container.style.setProperty('gap', '0.5rem', 'important');
                            
                            // 내부 헤더 스타일 (모든 Level 2 헤더 크기 통일)
                            const header = container.querySelector('h2');
                            if (header) {
                                header.style.margin = '0';
                                header.style.setProperty('margin', '0', 'important');
                                header.style.padding = '0';
                                header.style.setProperty('padding', '0', 'important');
                                header.style.flex = '0 0 auto';
                                header.style.setProperty('flex', '0 0 auto', 'important');
                                // 모든 Level 2 헤더 크기 통일 (1.3em)
                                header.style.fontSize = '1.3em';
                                header.style.setProperty('font-size', '1.3em', 'important');
                            }
                            
                            // 내부 별점 컨테이너 스타일 (모든 별점 크기 통일)
                            const starContainer = container.querySelector('div:last-child');
                            if (starContainer && starContainer !== header) {
                                starContainer.style.flex = '0 0 auto';
                                starContainer.style.setProperty('flex', '0 0 auto', 'important');
                                starContainer.style.margin = '0';
                                starContainer.style.setProperty('margin', '0', 'important');
                                starContainer.style.padding = '0';
                                starContainer.style.setProperty('padding', '0', 'important');
                                starContainer.style.lineHeight = '1';
                                starContainer.style.setProperty('line-height', '1', 'important');
                                // 모든 별점 크기 통일 (1.2em)
                                starContainer.style.fontSize = '1.2em';
                                starContainer.style.setProperty('font-size', '1.2em', 'important');
                                // 별점 내부 요소도 크기 설정
                                const starRating = starContainer.querySelector('.star-rating');
                                if (starRating) {
                                    starRating.style.fontSize = '1.2em';
                                    starRating.style.setProperty('font-size', '1.2em', 'important');
                                }
                            }
                        });
                        
                        // 별점과 헤더 사이 간격 완전 제거 (forceHeaderColors)
                        const headers2 = document.querySelectorAll('[data-testid="stExpander"] h2[id^="physical-state-"], [data-testid="stExpander"] h2[id^="physical-empty-"], [data-testid="stExpander"] h2[id^="mental-state-"], [data-testid="stExpander"] h2[id^="mental-empty-"], [data-testid="stExpander"] h2[id^="satisfaction-"], [data-testid="stExpander"] h2[id^="satisfaction-empty-"]');
                        headers2.forEach(header => {
                            // 헤더 하단 마진 완전 제거
                            header.style.marginBottom = '0';
                            header.style.setProperty('margin-bottom', '0', 'important');
                            header.style.paddingBottom = '0';
                            header.style.setProperty('padding-bottom', '0', 'important');
                            
                            // 헤더 다음 모든 요소 확인
                            let currentEl = header.nextElementSibling;
                            let checkedCount = 0;
                            // 최대 3개까지 확인 (별점을 찾을 때까지)
                            while (currentEl && checkedCount < 3) {
                                // div나 MarkdownContainer인 경우
                                if (currentEl.tagName === 'DIV' || currentEl.getAttribute('data-testid') === 'stMarkdownContainer') {
                                    currentEl.style.marginTop = '0';
                                    currentEl.style.setProperty('margin-top', '0', 'important');
                                    currentEl.style.paddingTop = '0';
                                    currentEl.style.setProperty('padding-top', '0', 'important');
                                    currentEl.style.lineHeight = '1';
                                    currentEl.style.setProperty('line-height', '1', 'important');
                                    
                                    // 내부에 별점이 있는지 확인
                                    const starRating = currentEl.querySelector('.star-rating');
                                    if (starRating) {
                                        starRating.style.marginTop = '0';
                                        starRating.style.setProperty('margin-top', '0', 'important');
                                        starRating.style.paddingTop = '0';
                                        starRating.style.setProperty('padding-top', '0', 'important');
                                        starRating.style.lineHeight = '1';
                                        starRating.style.setProperty('line-height', '1', 'important');
                                        break; // 별점을 찾았으면 중단
                                    }
                                }
                                // 별점이 직접 다음에 오는 경우
                                if (currentEl.classList && currentEl.classList.contains('star-rating')) {
                                    currentEl.style.marginTop = '0';
                                    currentEl.style.setProperty('margin-top', '0', 'important');
                                    currentEl.style.paddingTop = '0';
                                    currentEl.style.setProperty('padding-top', '0', 'important');
                                    break;
                                }
                                
                                currentEl = currentEl.nextElementSibling;
                                checkedCount++;
                            }
                        });
                    }
                    
                    // forceHeaderColors도 주기적으로 실행
                    setInterval(function() {
                        forceHeaderColors();
                        // 들여쓰기도 재적용
                        const contentDivs = document.querySelectorAll('[data-testid="stExpander"] div[id^="state-reason-content-"], [data-testid="stExpander"] div[id^="improvement-content-"], [data-testid="stExpander"] div[id^="yesterday-work-content-"], [data-testid="stExpander"] div[id^="liked-content-"], [data-testid="stExpander"] div[id^="lacked-content-"], [data-testid="stExpander"] div[id^="learned-content-"], [data-testid="stExpander"] div[id^="looked-forward-content-"], [data-testid="stExpander"] div[id^="longed-for-content-"], [data-testid="stExpander"] div[id^="colleague-praise-content-"], [data-testid="stExpander"] div[id^="today-plan-content-"]');
                        contentDivs.forEach(div => {
                            div.style.paddingLeft = '2rem';
                            div.style.setProperty('padding-left', '2rem', 'important');
                            let parent = div.closest('[data-testid="stMarkdownContainer"]');
                            if (parent) {
                                parent.style.paddingLeft = '2rem';
                                parent.style.setProperty('padding-left', '2rem', 'important');
                            }
                        });
                    }, 200);
                    forceHeaderColors();
                })();
                </script>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("아직 작성한 Snippet이 없습니다. Daily Snippet 기록을 시작해보세요!")
    else:
        st.warning("데이터를 불러올 수 없습니다. Google Sheets 연동을 확인해주세요.")


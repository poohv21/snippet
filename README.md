# Daily Snippet App

매일의 상태와 업무를 기록하고 팀과 공유하는 Streamlit 애플리케이션입니다.

## 기능

### 3단계 입력 프로세스

#### 1단계: Check-in
- 몸상태 평가 (5점 만점, 필수)
- 마음상태 평가 (5점 만점, 필수)
- 상태 이유 (주관식, 필수)
- 개선 방안 (주관식, 선택)

#### 2단계: Look-back
- 전일 완료 업무 (긴 주관식, 필수)
- 전일 만족도 (5점 만점, 필수)
- 이름 (필수)
- Liked - 좋았던 점 (필수)
- Lacked - 아쉬웠던 점 (필수)
- Learned - 배웠던 점 (선택)
- Looked Forward - 향후 시도해보고 싶은 것 (선택)
- Longed For - 팀과 리더에게 바라는 점 (선택)
- 동료 칭찬 (선택)

#### 3단계: Today's Plans
- 오늘 할 일 목록 (긴 주관식, 선택)

## 설치 및 실행

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. Google Sheets 연동 설정

1. Google Cloud Console에서 프로젝트 생성
2. Google Sheets API 활성화
3. 서비스 계정 생성 및 JSON 키 다운로드
4. 환경변수 설정:
   ```bash
   export GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'
   ```

### 3. 앱 실행
```bash
streamlit run daily_snippet.py
```

## Google Sheets 연동

앱은 지정된 Google Sheets에 데이터를 자동으로 저장합니다:
- 스프레드시트 ID: `1THmwStR6p0_SUyLEV6-edT0kigANvTCPOkAzN7NaEQE`
- 데이터는 기존 형식에 맞춰 추가됩니다

## 사용법

1. 웹 브라우저에서 앱에 접속
2. **로그인**: 휴대폰번호와 비밀번호로 로그인
3. **Daily Snippet 작성**: 1단계부터 순서대로 입력
4. 필수 항목을 모두 입력하면 다음 단계로 진행
5. 모든 단계 완료 후 '전송하기' 버튼 클릭
6. 데이터가 Google Sheets에 자동 저장됩니다

### 로그인 계정 정보
- **박성진**: 01064161169 / tjdwls21 (관리자)
- **홍길동**: 01012345678 / tjdwls21
- **권정미**: 01091238611 / 1007
- **배주리**: 01025385744 / scent1223
- **서지원**: 01062861020 / Tjwldnjs1020!
- **황용철**: 01031153665 / 090820

## 특징

- 단계별 진행으로 사용자 부담 최소화
- 실시간 입력 미리보기
- 필수 항목 유효성 검사
- 직관적인 UI/UX
- Google Sheets 자동 연동

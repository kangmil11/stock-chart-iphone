# 한국 종목명 검색 주식 차트

## GitHub / Streamlit 배포

아래 파일을 GitHub 저장소 루트에 함께 업로드합니다.

- `webull_lightweight_chart_iphone_fixed.py` — Streamlit 시작 파일
- `kr_stock_list.csv` — 한국 전체 상장 주식 목록
- `requirements.txt` — 설치 패키지
- `update_kr_stocks.py` — 목록 갱신 도구
- `.github/workflows/update-kr-stocks.yml` — 선택 사항: 목록 자동 갱신

Streamlit Community Cloud에서 저장소와 위 Python 시작 파일을 선택합니다. Python 3.12 이상을 권장합니다. requirements.txt는 이번 검증에 사용한 직접 의존성 버전으로 고정했습니다. API 키는 필요하지 않습니다. 파일명을 기존 시작 파일명으로 바꾸어도 됩니다. CSV는 반드시 앱 파일과 같은 폴더에 둡니다.

로컬 실행:

```sh
pip install -r requirements.txt
streamlit run webull_lightweight_chart_iphone_fixed.py
```

## 검색 방법

- 기본 입력은 `KOSPI200`이며 `^KS200` 지수를 조회합니다. KODEX 200 ETF와는 별개입니다.
- `엘앤에프` → `066970` → 한국 주가 조회. `.KS`나 `.KQ`를 붙이지 않습니다.
- `066970`, `066970.KQ`, `066970.KS` 입력도 모두 `066970`으로 정규화합니다.
- `삼성` 등 일부 이름을 입력하고 Enter/완료를 누르면 검색 결과가 나옵니다. 결과 선택창 안에서도 입력하여 자동완성할 수 있습니다. 여러 결과가 있으면 선택 전까지 주가를 조회하지 않습니다.
- 영문 한국 종목명 부분검색(예: `SK`, `NAV`)은 시장을 `한국`으로 선택합니다. `NAVER`처럼 정확한 종목명은 `자동`에서도 찾습니다.
- `AAPL`, `MSFT`, `BRK-B` 등 미국 티커는 그대로 유지합니다. 한국 이름과 겹치는 미국 티커는 시장 `미국`을 선택합니다.
- `KODEX 200`, `KODEX 레버리지`는 기존 별칭을 유지합니다. CSV 범위는 KOSPI·KOSDAQ·KONEX 상장 **주식**(우선주 포함)이며 전체 ETF·ETN·ELW 목록은 포함하지 않습니다. ETF는 알려진 코드를 직접 입력할 수도 있습니다.

한국 검색에는 인터넷을 사용하지 않습니다. 주가 조회에는 인터넷이 필요합니다. 회사명 변경·신규상장·상장폐지는 CSV 갱신으로 반영합니다.

## 데이터와 기존 코드 보존

원본: 이전 대화에 첨부된 `붙여넣은 텍스트(1)(1).txt`. 별도의 `webull_lightweight_chart_iphone_fixed.py` 첨부본은 제공되지 않았으므로 확보한 원본을 수정했습니다.

월별 Double, 연속 방향 병합 Double 2, Wave, Big 계산부터 차트 HTML/JS/CSS, iPhone 핀치·터치 이동·가격축 조작, MA 범례, 현재 상태 표까지 원본 코드와 동일하게 보존했습니다. 원본의 삼성전자 기본 입력만 요청에 맞춰 KOSPI200으로 변경했습니다.

한국 주가: FinanceDataReader `NAVER:066970`처럼 코드로 조회합니다. 일봉을 주봉/월봉으로 집계하며 시가 첫 값, 고가 최댓값, 저가 최솟값, 종가 마지막 값, 거래량 합계를 사용합니다. 주/월 날짜는 해당 기간 종료일로 표시하며 진행 중 봉도 포함합니다. Yahoo와 NAVER의 수정주가/데이터 제공 정책 차이로 기존 Yahoo 값과 차이가 날 수 있습니다. 미국/지수는 기존 yfinance 경로를 사용합니다.

CSV 기준일은 `AsOf` 열과 앱 상단에 표시합니다. 초기 제공본: **2026-10-22, 2,868종목**(KOSPI 940, KOSDAQ 1,823, KONEX 105). `KOSDAQ GLOBAL`은 KOSDAQ으로 통합했습니다. 최신 소속 시장은 CSV 값을 사용하며 이전 `.KQ` 표기에서 시장을 추측하지 않습니다.

원본 목록은 FinanceDataReader 프로젝트가 공개하는 KRX 전체 주식 스냅샷을 사용합니다. 거래소 직접 실시간 목록은 아닙니다.

- https://github.com/FinanceData/fdr_krx_data_cache/tree/master/data/listing/krx
- https://github.com/FinanceData/FinanceDataReader

## 목록 생성·갱신

```sh
python update_kr_stocks.py
```

위 도구로 최초 CSV도 생성할 수 있습니다. 실행 시 공개 저장소의 한국시간 오늘 이하 최신 날짜를 선택합니다. 10일 초과 오래된 원본, 2,000종목 미만, 시장 누락, 코드 형식 오류, 코드 중복, 빈 이름이면 실패하고 기존 CSV를 유지합니다. 검증된 결과를 임시 파일에 저장한 뒤 교체하여 다운로드 실패가 기존 목록을 지우지 않습니다. 코드 앞자리 0은 문자열로 보존합니다.

자동 갱신은 포함된 `.github/workflows/update-kr-stocks.yml`을 해당 경로로 업로드하면 됩니다. ZIP은 숨김 폴더도 포함합니다. GitHub 웹에서 압축 파일 자체만 올리면 배포되지 않으므로 **압축을 풀어 내부 파일을 업로드**합니다. 자동 갱신 파일은 필요하면 GitHub의 Add file → Create new file에서 전체 경로로 추가할 수 있습니다.

GitHub Actions에서 워크플로를 활성화하고 저장소 Settings → Actions → General → Workflow permissions를 Read and write permissions로 허용합니다. 평일 한국시간 오전 7시에 실행되며 GitHub 사정에 따라 지연될 수 있습니다. Actions의 Run workflow로 수동 실행도 가능합니다. 기본 브랜치 보호 규칙이 봇의 push를 막으면 수동으로 생성한 CSV를 올리거나 저장소 규칙에 맞는 PR 방식으로 조정합니다. 공개 저장소의 장기 비활동으로 스케줄이 중지되면 다시 활성화해야 합니다.

앱은 CSV 변경 시간을 캐시 키로 사용합니다. 배포본의 CSV가 변경되면 새 목록을 읽습니다. 주가는 10분 캐시합니다. 갱신 실패는 GitHub Actions 실패로 확인하고 기존 CSV를 계속 사용합니다.

## 검증

- 두 Python 파일 문법 검사 통과.
- Streamlit AppTest에서 KOSPI200 기본값, 엘앤에프→066970, 접미사 제거, 여러 결과 선택, AAPL 유지, 없는 한국 이름 안내 확인(주가 응답은 고정 데이터로 대체).
- 원본의 지표 계산 이후 전체 차트·조작·상태 표시 코드가 수정본과 동일함을 비교 확인.
- NAVER:066970 및 NAVER:005930 실제 일별 주가 응답 수신, Yahoo ^KS200 실제 응답 수신 확인. 외부 제공자의 지속적인 가용성을 보장하지는 않습니다.
- 실제 iPhone Safari 기기 조작 검증은 수행하지 않았습니다.

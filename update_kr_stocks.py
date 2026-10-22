"""Refresh the complete KRX equity list; failures leave the existing CSV untouched."""
import argparse
from datetime import datetime
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

REPO = 'https://api.github.com/repos/FinanceData/fdr_krx_data_cache/contents/data/listing/krx'
RAW = 'https://raw.githubusercontent.com/FinanceData/fdr_krx_data_cache/master/data/listing/krx/'


def refresh(output):
    session = requests.Session()
    session.headers['User-Agent'] = 'kr-stock-list-updater/1.0'
    today = datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    response = session.get(REPO, timeout=30)
    response.raise_for_status()
    dates = sorted(item['name'][:-4] for item in response.json()
                   if item['name'].endswith('.csv') and item['name'][:-4] <= today)
    if not dates:
        raise ValueError('공개 저장소에 사용 가능한 종목 목록이 없습니다.')
    as_of = dates[-1]
    if (datetime.fromisoformat(today) - datetime.fromisoformat(as_of)).days > 10:
        raise ValueError(f'원본 목록이 10일 넘게 갱신되지 않았습니다: {as_of}')
    response = session.get(RAW + as_of + '.csv', timeout=30)
    response.raise_for_status()
    frame = pd.read_csv(StringIO(response.text), dtype=str, keep_default_na=False)
    frame = frame[['Code', 'Name', 'Market']].copy()
    frame['Market'] = frame['Market'].replace({'KOSDAQ GLOBAL': 'KOSDAQ'})
    if len(frame) < 2000 or not frame['Code'].str.fullmatch(r'[0-9A-Z]{6}').all():
        raise ValueError('종목 수/코드 검증 실패: 기존 CSV를 유지합니다.')
    if not {'KOSPI', 'KOSDAQ', 'KONEX'}.issubset(set(frame['Market'])):
        raise ValueError('일부 시장이 누락되었습니다: 기존 CSV를 유지합니다.')
    if frame['Code'].duplicated().any() or frame['Name'].eq('').any():
        raise ValueError('중복 코드 또는 빈 종목명: 기존 CSV를 유지합니다.')
    frame['AsOf'] = as_of
    frame = frame.sort_values(['Market', 'Name', 'Code'])
    output = Path(output)
    temporary = output.with_suffix('.csv.tmp')
    frame.to_csv(temporary, index=False, encoding='utf-8-sig')
    temporary.replace(output)
    print(f'{output.name}: {len(frame):,}종목, 기준일 {as_of}')
    print(frame.groupby('Market').size().to_string())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('kr_stock_list.csv'))
    refresh(parser.parse_args().output)

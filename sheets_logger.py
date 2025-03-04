import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class SheetsLogger:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = None
        self.service = None
        self.spreadsheet_id = os.environ.get('GOOGLE_SHEETS_ID')

        # 시트 범위 설정
        self.MEXC_SHEET_RANGE = 'MEXC-Bitget!A:G'  # A부터 G열까지
        self.GATE_SHEET_RANGE = 'Gate.io-Bitget!A:G'  # A부터 G열까지

        # 헤더 설정
        self.headers = [
            '갭 (%)',
            '가격차이 (USDT)',
            '거래소1 가격',
            '거래소2 가격',
            '거래소1 호가',
            '거래소2 호가',
            '최소 호가량'
        ]

    def initialize(self) -> bool:
        """Google Sheets API 초기화"""
        try:
            logger.info("Initializing Google Sheets API...")

            # credentials.json 파일 확인
            if not os.path.exists('credentials.json'):
                logger.error("Missing credentials.json file")
                return True  # 실패해도 앱은 계속 실행되도록 수정

            try:
                if os.path.exists('token.json'):
                    self.creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)

                if not self.creds or not self.creds.valid:
                    if self.creds and self.creds.expired and self.creds.refresh_token:
                        self.creds.refresh(Request())
                    else:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', self.SCOPES)
                        self.creds = flow.run_local_server(port=0)

                    with open('token.json', 'w') as token:
                        token.write(self.creds.to_json())

                self.service = build('sheets', 'v4', credentials=self.creds)

                # 스프레드시트 ID 확인
                if not self.spreadsheet_id:
                    logger.error("Missing GOOGLE_SHEETS_ID environment variable")
                    return True  # 실패해도 앱은 계속 실행되도록 수정

                # 헤더 추가
                self._initialize_headers()
                logger.info("Google Sheets API initialized successfully")
                return True

            except Exception as e:
                logger.error(f"Error during Google Sheets authentication: {e}")
                return True  # 실패해도 앱은 계속 실행되도록 수정

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets API: {e}")
            return True  # 실패해도 앱은 계속 실행되도록 수정

    def _initialize_headers(self):
        """시트에 헤더 추가"""
        try:
            # MEXC-Bitget 시트 헤더
            self._update_values(
                self.MEXC_SHEET_RANGE.split('!')[0],
                'A1:G1',
                [self.headers]
            )
            
            # Gate.io-Bitget 시트 헤더
            self._update_values(
                self.GATE_SHEET_RANGE.split('!')[0],
                'A1:G1',
                [self.headers]
            )
        except Exception as e:
            logger.error(f"Failed to initialize headers: {e}")

    def _update_values(self, sheet_name: str, range_name: str, values: List[List]):
        """시트 값 업데이트"""
        try:
            body = {
                'values': values
            }
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!{range_name}",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        except Exception as e:
            logger.error(f"Failed to update values: {e}")

    def log_price_gap(self, exchange1_data: dict, exchange2_data: dict, gap: float, is_mexc: bool = True):
        """가격 갭 정보를 구글 시트에 기록"""
        try:
            # 데이터 준비
            price_diff = abs(exchange1_data['last_price'] - exchange2_data['last_price'])
            
            # 호가 계산
            exchange1_volume = float(exchange1_data['asks'][0][1])  # 첫 번째 매도호가의 수량
            exchange2_volume = float(exchange2_data['asks'][0][1])  # 첫 번째 매도호가의 수량
            min_volume = min(exchange1_volume, exchange2_volume)
            
            # 기록할 데이터
            row_data = [
                [
                    f"{gap:.2f}",
                    f"{price_diff:.8f}",
                    f"{exchange1_data['last_price']:.8f}",
                    f"{exchange2_data['last_price']:.8f}",
                    f"{exchange1_volume:.8f}",
                    f"{exchange2_volume:.8f}",
                    f"{min_volume:.8f}"
                ]
            ]
            
            # 시트 선택 및 업데이트
            sheet_range = self.MEXC_SHEET_RANGE if is_mexc else self.GATE_SHEET_RANGE
            sheet_name = sheet_range.split('!')[0]
            
            # 다음 빈 행 찾기
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_range
            ).execute()
            next_row = len(result.get('values', [])) + 1
            
            # 데이터 추가
            self._update_values(
                sheet_name,
                f'A{next_row}:G{next_row}',
                row_data
            )
            
            logger.info(f"Successfully logged price gap data to {sheet_name}")
            
        except Exception as e:
            logger.error(f"Failed to log price gap: {e}")
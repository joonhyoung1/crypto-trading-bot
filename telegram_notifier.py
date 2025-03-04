import os
import logging
import pytz
from telegram import Bot
from telegram.error import TelegramError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        self.USDT_TO_KRW = 1300  # USDT to KRW exchange rate
        self.is_enabled = True
        self.KST = pytz.timezone('Asia/Seoul')

        logger.info("Initializing TelegramNotifier")

        if not self.bot_token or not self.chat_id:
            logger.warning("Missing Telegram credentials, notifications will be disabled")
            self.is_enabled = False
            return

        try:
            self.bot = Bot(token=self.bot_token)
            bot_info = self.bot.get_me()
            logger.info(f"Successfully initialized Telegram bot: {bot_info.username}")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.is_enabled = False

        self.last_alerts = {}

    def send_message(self, message: str) -> bool:
        """텔레그램으로 메시지를 전송합니다."""
        if not self.is_enabled:
            logger.warning("Telegram notifications are disabled")
            return False

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info("Message sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    def send_gap_alert(self, exchange1: str, exchange2: str, data1: dict, data2: dict, gap: float) -> bool:
        """가격 갭이 임계값을 초과할 때 알림을 보냅니다."""
        try:
            current_time = datetime.now(self.KST)

            # 거래 가능 금액 계산
            sellAmount1 = float(data1['asks'][0][0]) * float(data1['asks'][0][1])
            buyAmount1 = float(data1['bids'][0][0]) * float(data1['bids'][0][1])
            sellAmount2 = float(data2['asks'][0][0]) * float(data2['asks'][0][1])
            buyAmount2 = float(data2['bids'][0][0]) * float(data2['bids'][0][1])

            trade_amount = min(sellAmount1, buyAmount1, sellAmount2, buyAmount2)
            trade_amount_krw = trade_amount * self.USDT_TO_KRW

            # 코인 아이콘 선택
            coin_icon = "🟣" if "XRP" in data1['symbol'] else "🟡"  # XRP는 보라색, DOGE는 노란색
            gap_icon = "🔵" if gap > 0 else "🔴"  # 플러스는 파란색, 마이너스는 빨간색

            message = (
                f"{gap_icon} MEXC-Bitget 가격차이 발생! {coin_icon} {data1['symbol']}\n"
                f"시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"\n"
                f"MEXC: {data1['last_price']:.4f} USDT\n"
                f"Bitget: {data2['last_price']:.4f} USDT\n"
                f"차이: {gap:+.2f}% ({abs(data1['last_price'] - data2['last_price']):.4f} USDT)\n"
                f"\n"
                f"거래가능금액: {trade_amount:.2f} USDT\n"
                f"원화금액: {trade_amount_krw:,.0f}원"
            )

            return self.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send gap alert: {e}")
            return False
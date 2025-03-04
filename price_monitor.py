import logging
import time
from datetime import datetime
from typing import Optional, Dict, Tuple
from telegram_notifier import TelegramNotifier
from trading import TradingExecutor

logger = logging.getLogger(__name__)

class PriceGapMonitor:
    def __init__(self):
        logger.info("Initializing PriceGapMonitor...")
        try:
            self.telegram = TelegramNotifier()
            self.trading = TradingExecutor()

            # 트레이딩 설정
            self.trading_thresholds = {
                'entry_long': 0.05,   # MEXC에서 숏, Bitget에서 롱 진입 임계값
                'entry_short': -0.06  # MEXC에서 롱, Bitget에서 숏 진입 임계값
            }

            # 감시할 코인 목록
            self.trading_symbols = ['DOGE/USDT', 'XRP/USDT']

            # 기존 알림용 임계값 설정 유지
            self.thresholds = {
                'MEXC': {
                    'entry': 0.05,
                    'exit': -0.06
                }
            }

            self.running = False
            self.last_check: Dict[str, datetime] = {}

            logger.info("PriceGapMonitor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PriceGapMonitor: {e}")
            raise

    def start(self):
        """모니터링을 시작합니다."""
        try:
            logger.info("Starting price gap monitoring...")
            self.running = True

            if self.test_telegram():
                logger.info("Price gap monitoring started successfully")
                self.telegram.send_message(
                    "🔄 자동 트레이딩 시스템이 시작되었습니다.\n"
                    f"- 감시 코인: {', '.join(self.trading_symbols)}\n"
                    f"- 롱 진입: MEXC-Bitget 갭 {self.trading_thresholds['entry_long']}% 이상\n"
                    f"- 숏 진입: MEXC-Bitget 갭 {self.trading_thresholds['entry_short']}% 이하\n"
                    "- 거래 모드: Cross 모드, 1배 레버리지"
                )
            else:
                logger.error("Failed to start price gap monitoring: Telegram test failed")
                self.running = False
        except Exception as e:
            logger.error(f"Failed to start price gap monitoring: {e}")
            self.running = False

    def stop(self):
        """모니터링을 중지합니다."""
        try:
            logger.info("Stopping price gap monitoring...")
            self.running = False
            self.telegram.send_message("🛑 자동 트레이딩 시스템이 중지되었습니다.")
            logger.info("Price gap monitoring stopped")
        except Exception as e:
            logger.error(f"Failed to stop price gap monitoring: {e}")
            raise

    def test_telegram(self) -> bool:
        """텔레그램 봇 연결 테스트"""
        try:
            logger.info("Testing Telegram connection...")
            if self.telegram.send_message("🔄 테스트 메시지: MEXC-Bitget 가격 알림 시스템 작동 중"):
                logger.info("Telegram test message sent successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Telegram test failed: {e}")
            return False

    def execute_arbitrage_trades(self, mexc_data: dict, bitget_data: dict, gap: float):
        """차익거래 주문을 실행합니다."""
        try:
            # 거래 가능 금액 계산
            tradable_amount = self.trading.calculate_tradable_amount(mexc_data, bitget_data)
            if tradable_amount <= 0:
                logger.error("Invalid tradable amount calculated")
                return

            # 실제 거래에 사용할 금액 (USDT)
            trade_amount = tradable_amount * 0.95  # 95%만 사용하여 안전마진 확보

            success = False
            message = ""

            if gap >= self.trading_thresholds['entry_long']:
                # MEXC에서 숏, Bitget에서 롱
                logger.info(f"Executing long arbitrage trades for gap {gap:.2f}%")
                success, message = self.trading.execute_simultaneous_orders(
                    mexc_data['symbol'],
                    bitget_data['symbol'],
                    'sell',  # MEXC 숏
                    'buy',   # Bitget 롱
                    trade_amount
                )

            elif gap <= self.trading_thresholds['entry_short']:
                # MEXC에서 롱, Bitget에서 숏
                logger.info(f"Executing short arbitrage trades for gap {gap:.2f}%")
                success, message = self.trading.execute_simultaneous_orders(
                    mexc_data['symbol'],
                    bitget_data['symbol'],
                    'buy',   # MEXC 롱
                    'sell',  # Bitget 숏
                    trade_amount
                )

            # 거래 결과 텔레그램 알림 전송
            if success:
                direction = "롱" if gap >= self.trading_thresholds['entry_long'] else "숏"
                price_diff = abs(float(mexc_data['last_price']) - float(bitget_data['last_price']))
                message = (
                    f"✅ 차익거래 실행 완료 ({direction})\n"
                    f"코인: {mexc_data['symbol']}\n"
                    f"갭: {gap:+.2f}% ({price_diff:.4f} USDT)\n"
                    f"MEXC 가격: {mexc_data['last_price']:.4f} USDT\n"
                    f"Bitget 가격: {bitget_data['last_price']:.4f} USDT\n"
                    f"거래금액: {trade_amount:.2f} USDT\n"
                    "거래 모드: Cross 모드, 1배 레버리지"
                )
            else:
                message = f"⚠️ 차익거래 실행 실패\n{message}"

            self.telegram.send_message(message)

        except Exception as e:
            logger.error(f"Failed to execute arbitrage trades: {e}")
            self.telegram.send_message(f"⚠️ 차익거래 실행 중 오류 발생: {str(e)}")

    def process_exchange_data(self, data1: dict, data2: dict):
        """거래소 데이터를 처리하고 필요한 경우 알림을 보냅니다."""
        try:
            if not self.running:
                return

            # MEXC-Bitget 또는 Gate.io-Bitget 거래소 쌍에 대해서만 자동 트레이딩 실행
            if data1['exchange'].startswith('MEXC') and data2['exchange'].startswith('Bitget'):
                if data1['symbol'] in self.trading_symbols:  # XRP와 DOGE 코인만 처리
                    price1 = float(data1['last_price'])
                    price2 = float(data2['last_price'])
                    gap = ((price1 - price2) / price2) * 100

                    # 자동 트레이딩 조건 확인 및 실행
                    if gap >= self.trading_thresholds['entry_long'] or gap <= self.trading_thresholds['entry_short']:
                        self.execute_arbitrage_trades(data1, data2, gap)

            elif data1['exchange'].startswith('Gate.io') and data2['exchange'].startswith('Bitget'):
                if data1['symbol'] in self.trading_symbols:  # XRP와 DOGE 코인만 처리
                    price1 = float(data1['last_price'])
                    price2 = float(data2['last_price'])
                    gap = ((price1 - price2) / price2) * 100

                    # 자동 트레이딩 조건 확인 및 실행
                    if gap >= self.trading_thresholds['entry_long'] or gap <= self.trading_thresholds['entry_short']:
                        self.execute_arbitrage_trades(data1, data2, gap)

            # 기존 알림 로직 실행
            gap_info = self.check_price_gap(data1, data2)
            if not gap_info:
                return

            gap, symbol = gap_info
            current_time = datetime.now()
            alert_key = f"{symbol}-{gap:.2f}"

            # 마지막 알림으로부터 최소 5분이 지났는지 확인
            if alert_key in self.last_check:
                time_since_last = current_time - self.last_check[alert_key]
                if time_since_last.total_seconds() < 300:  # 5분 = 300초
                    return

            # 텔레그램 알림 전송
            if self.telegram.send_gap_alert(data1['exchange'], data2['exchange'], data1, data2, gap):
                self.last_check[alert_key] = current_time

        except Exception as e:
            logger.error(f"데이터 처리 중 오류 발생: {e}")

    def check_price_gap(self, data1: dict, data2: dict) -> Optional[Tuple[float, str]]:
        """주어진 거래소 데이터에서 가격 갭을 확인합니다."""
        try:
            if not data1 or not data2:
                return None

            symbol = data1.get('symbol')
            exchange = data1.get('exchange', '').split(' ')[0]  # 'MEXC Futures' -> 'MEXC'
            price1 = float(data1.get('last_price', 0))
            price2 = float(data2.get('last_price', 0))

            if not all([symbol, exchange, price1, price2]):
                return None

            # 가격 갭 계산 (%)
            gap = ((price1 - price2) / price2) * 100

            # 거래소별 임계값 확인
            threshold = self.thresholds.get(exchange, self.thresholds['MEXC'])
            if gap >= threshold['entry'] or gap <= threshold['exit']:
                logger.info(f"Found significant price gap for {exchange}: {gap:.2f}% for {symbol}")
                return gap, symbol

            return None

        except Exception as e:
            logger.error(f"가격 갭 확인 중 오류 발생: {e}")
            return None
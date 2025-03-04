import os
import logging
import ccxt
import time
import hmac
import hashlib
import requests
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingExecutor:
    def __init__(self):
        try:
            # Initialize exchanges
            logger.info("Initializing exchange clients...")

            # MEXC initialization
            self.mexc = ccxt.mexc({
                'apiKey': os.environ.get('MEXC_API_KEY'),
                'secret': os.environ.get('MEXC_API_SECRET'),
                'enableRateLimit': True,
                'rateLimit': 20,  # 최소 delay를 20ms로 설정
                'options': {
                    'defaultType': 'future'
                }
            })

            # Gate.io initialization
            self.gateio = ccxt.gateio({
                'apiKey': os.environ.get('GATEIO_API_KEY'),
                'secret': os.environ.get('GATEIO_API_SECRET'),
                'enableRateLimit': True,
                'rateLimit': 20,  # 최소 delay를 20ms로 설정
                'options': {
                    'defaultType': 'future'
                }
            })

            # Bitget initialization
            self.bitget = ccxt.bitget({
                'apiKey': os.environ.get('BITGET_API_KEY'),
                'secret': os.environ.get('BITGET_API_SECRET'),
                'password': os.environ.get('BITGET_PASSPHRASE'),
                'enableRateLimit': True,
                'rateLimit': 20,  # 최소 delay를 20ms로 설정
                'options': {
                    'defaultType': 'swap',
                    'defaultSubType': 'linear',
                    'broker': 'CCXT'
                }
            })

            self.initialized_exchanges = []

            # Initialize each exchange separately
            if self._initialize_mexc():
                self.initialized_exchanges.append('MEXC')
            if self._initialize_gateio():
                self.initialized_exchanges.append('Gate.io')
            if self._initialize_bitget():
                self.initialized_exchanges.append('Bitget')

            if not self.initialized_exchanges:
                logger.error("No exchanges were initialized")
                raise Exception("Failed to initialize exchanges")

            logger.info(f"Successfully initialized {len(self.initialized_exchanges)} exchange clients")

        except Exception as e:
            logger.error(f"Failed to initialize exchange clients: {str(e)}")
            raise

    def _initialize_mexc(self):
        """MEXC 초기화"""
        try:
            logger.info("Testing MEXC API connection...")
            start_time = time.time()

            # Load markets first
            logger.info("Loading MEXC markets...")
            self.mexc.load_markets()
            logger.info("MEXC markets loaded successfully")

            # Test futures market access with detailed options
            logger.info("Testing MEXC futures market access...")
            futures_options = {
                'defaultType': 'swap',  # Use swap for futures trading
                'defaultSubType': 'linear',  # Linear contracts
                'settle': 'USDT'  # USDT-settled contracts
            }

            # Set default options for all MEXC API calls
            self.mexc.options = {**self.mexc.options, **futures_options}

            # Test ticker fetch with proper options
            symbol = 'XRP/USDT'
            ticker = self.mexc.fetch_ticker(symbol)
            logger.info(f"MEXC futures ticker response for {symbol}: {ticker}")

            if ticker and ticker.get('last'):
                logger.info(f"MEXC API test successful. {symbol} price: {ticker['last']}")
                logger.info(f"MEXC initialization completed in {(time.time() - start_time)*1000:.2f}ms")
                return True
            else:
                logger.error("MEXC API test failed: Invalid ticker response")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize MEXC: {str(e)}", exc_info=True)
            return False

    def _initialize_gateio(self):
        """Gate.io 초기화"""
        try:
            logger.info("Testing Gate.io API connection...")
            start_time = time.time()

            # Test ticker fetch
            ticker = self.gateio.fetch_ticker('XRP/USDT')
            logger.info(f"Gate.io ticker response: {ticker}")

            if ticker and ticker.get('last'):
                logger.info(f"Gate.io API test successful. XRP/USDT price: {ticker['last']}")
                logger.info(f"Gate.io initialization completed in {(time.time() - start_time)*1000:.2f}ms")
                return True
            else:
                logger.error("Gate.io API test failed: Invalid ticker response")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Gate.io: {str(e)}")
            return False

    def _initialize_bitget(self):
        """Bitget 초기화"""
        try:
            logger.info("Testing Bitget API connection...")
            start_time = time.time()

            # Load markets first
            self.bitget.load_markets()
            logger.info("Bitget markets loaded")

            # Test ticker fetch
            symbol = 'XRP/USDT:USDT'  # USDT-margined contract
            ticker = self.bitget.fetch_ticker(symbol)
            logger.info(f"Bitget ticker response: {ticker}")

            if ticker and ticker.get('last'):
                logger.info(f"Bitget API test successful. {symbol} price: {ticker['last']}")
                logger.info(f"Bitget initialization completed in {(time.time() - start_time)*1000:.2f}ms")
                return True
            else:
                logger.error("Bitget API test failed: Invalid ticker response")
                return False

        except Exception as e:
            logger.error(f"Failed to initialize Bitget: {str(e)}")
            return False

    def fetch_ticker(self, exchange: str, symbol: str) -> Dict[str, Any]:
        """거래소의 시세 정보를 가져옵니다."""
        try:
            exchange_map = {
                'mexc': self.mexc,
                'gateio': self.gateio,
                'bitget': self.bitget
            }

            if exchange not in exchange_map:
                logger.error(f"Invalid exchange: {exchange}")
                return {'last': 0}

            logger.info(f"Fetching ticker for {symbol} from {exchange}...")
            start_time = time.time()

            if exchange == 'bitget':
                symbol = f"{symbol.split('/')[0]}/USDT:USDT"

            ticker = exchange_map[exchange].fetch_ticker(symbol)
            logger.info(f"Ticker fetched in {(time.time() - start_time)*1000:.2f}ms")
            return ticker

        except Exception as e:
            logger.error(f"Failed to fetch ticker for {exchange} {symbol}: {e}")
            return {'last': 0}

    def fetch_order_book(self, exchange: str, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """거래소의 호가창 데이터를 가져옵니다."""
        try:
            exchange_map = {
                'mexc': self.mexc,
                'gateio': self.gateio,
                'bitget': self.bitget
            }

            if exchange not in exchange_map:
                logger.error(f"Invalid exchange: {exchange}")
                return {'asks': [], 'bids': []}

            if exchange == 'bitget':
                symbol = f"{symbol.split('/')[0]}/USDT:USDT"  # USDT-margined contract
                return exchange_map[exchange].fetch_order_book(symbol)
            else:
                return exchange_map[exchange].fetch_order_book(symbol, limit=limit)

        except Exception as e:
            logger.error(f"Failed to fetch order book for {exchange} {symbol}: {e}")
            return {'asks': [], 'bids': []}

    def execute_order(self, exchange: str, symbol: str, side: str, amount: float, leverage: int = 1) -> Optional[Dict[str, Any]]:
        """Execute order on specified exchange"""
        try:
            exchange_map = {
                'mexc': self.mexc,
                'gateio': self.gateio,
                'bitget': self.bitget
            }

            if exchange not in exchange_map:
                logger.error(f"Invalid exchange: {exchange}")
                return None

            start_time = time.time()

            # Handle Bitget futures symbol format
            if exchange == 'bitget':
                symbol = f"{symbol.split('/')[0]}/USDT:USDT"
                logger.info(f"Adjusted symbol for Bitget: {symbol}")

            # Set margin mode to cross and leverage
            try:
                # Set margin mode to cross
                if exchange == 'gateio':
                    exchange_map[exchange].set_margin_mode('cross', symbol)
                elif exchange == 'bitget':
                    # Bitget uses different parameter names
                    params = {
                        'marginCoin': 'USDT',
                        'marginMode': 'cross'
                    }
                    exchange_map[exchange].set_margin_mode('cross', symbol, params)

                # Set leverage
                exchange_map[exchange].set_leverage(leverage, symbol)
                logger.info(f"Set cross mode and leverage {leverage}x for {symbol} on {exchange}")
            except Exception as e:
                logger.error(f"Failed to set margin mode or leverage on {exchange}: {e}")
                # Continue with order anyway

            # Execute market order
            order = exchange_map[exchange].create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount
            )

            order_time = (time.time() - start_time) * 1000
            logger.info(f"Order executed on {exchange}: {side} {amount} {symbol}")
            return {
                'order': order,
                'times': {
                    'total_ms': order_time
                }
            }

        except Exception as e:
            logger.error(f"Failed to execute order on {exchange}: {e}")
            return None

    def execute_simultaneous_orders(self, mexc_symbol: str, bitget_symbol: str, mexc_side: str, bitget_side: str, amount: float) -> Tuple[bool, str]:
        """두 거래소에 동시에 주문을 실행합니다."""
        try:
            # MEXC와 Bitget에 주문 실행
            mexc_order = self.execute_order('mexc', mexc_symbol, mexc_side, amount, leverage=1)
            bitget_order = self.execute_order('bitget', bitget_symbol, bitget_side, amount, leverage=1)

            # 두 주문이 모두 성공했는지 확인
            if mexc_order and bitget_order:
                logger.info("Successfully executed orders on both exchanges")
                return True, "성공: 양쪽 거래소 주문 완료"
            else:
                # 주문 실패 시 취소 시도
                if mexc_order:
                    try:
                        self.mexc.cancel_order(mexc_order['order']['id'], mexc_symbol)
                        logger.info("Cancelled MEXC order after Bitget order failed")
                    except Exception as e:
                        logger.error(f"Failed to cancel MEXC order: {e}")

                if bitget_order:
                    try:
                        self.bitget.cancel_order(bitget_order['order']['id'], bitget_symbol)
                        logger.info("Cancelled Bitget order after MEXC order failed")
                    except Exception as e:
                        logger.error(f"Failed to cancel Bitget order: {e}")

                return False, "실패: 주문 실패 후 취소 처리됨"

        except Exception as e:
            logger.error(f"Error in simultaneous order execution: {e}")
            return False, f"오류 발생: {str(e)}"

    def close_positions(self, mexc_symbol: str, bitget_symbol: str, amount: float) -> Tuple[bool, str]:
        """두 거래소의 포지션을 동시에 종료합니다."""
        try:
            # MEXC와 Bitget의 현재 포지션 확인
            mexc_position = self.mexc.fetch_position(mexc_symbol)
            bitget_position = self.bitget.fetch_position(bitget_symbol)

            if not mexc_position or not bitget_position:
                return False, "포지션 정보를 가져올 수 없음"

            # MEXC 포지션 종료
            mexc_side = 'buy' if mexc_position['side'] == 'short' else 'sell'
            # Bitget 포지션 종료
            bitget_side = 'buy' if bitget_position['side'] == 'short' else 'sell'

            # 포지션 정보 저장
            position_info = {
                'MEXC': {
                    'side': mexc_position['side'],
                    'size': mexc_position['contracts'],
                    'pnl': mexc_position.get('unrealizedPnl', 0)
                },
                'Bitget': {
                    'side': bitget_position['side'],
                    'size': bitget_position['contracts'],
                    'pnl': bitget_position.get('unrealizedPnl', 0)
                }
            }

            # 동시에 종료 주문 실행
            success, message = self.execute_simultaneous_orders(
                mexc_symbol, bitget_symbol,
                mexc_side, bitget_side,
                amount
            )

            if success:
                logger.info("Successfully closed positions on both exchanges")
                message = (
                    "✅ 포지션 종료 완료\n"
                    f"코인: {mexc_symbol}\n"
                    f"MEXC ({position_info['MEXC']['side']}): {position_info['MEXC']['size']} 계약\n"
                    f"Bitget ({position_info['Bitget']['side']}): {position_info['Bitget']['size']} 계약\n"
                    f"MEXC PnL: {position_info['MEXC']['pnl']:.2f} USDT\n"
                    f"Bitget PnL: {position_info['Bitget']['pnl']:.2f} USDT"
                )
                return True, message
            else:
                return False, f"포지션 종료 실패: {message}"

        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False, f"포지션 종료 중 오류 발생: {str(e)}"

    def calculate_tradable_amount(self, exchange1_orderbook: dict, exchange2_orderbook: dict) -> float:
        """두 거래소의 호가창을 비교하여 거래 가능한 금액을 계산합니다."""
        try:
            # 각 거래소의 매수/매도 첫 호가 물량 계산
            sell_amount1 = float(exchange1_orderbook['asks'][0][0]) * float(exchange1_orderbook['asks'][0][1])
            buy_amount1 = float(exchange1_orderbook['bids'][0][0]) * float(exchange1_orderbook['bids'][0][1])
            sell_amount2 = float(exchange2_orderbook['asks'][0][0]) * float(exchange2_orderbook['asks'][0][1])
            buy_amount2 = float(exchange2_orderbook['bids'][0][0]) * float(exchange2_orderbook['bids'][0][1])

            # 가장 작은 거래 가능 금액 반환
            min_amount = min(sell_amount1, buy_amount1, sell_amount2, buy_amount2)
            logger.info(f"Calculated tradable amount: {min_amount:.2f} USDT")
            return min_amount

        except Exception as e:
            logger.error(f"Failed to calculate tradable amount: {e}")
            return 0.0

    def process_tradingview_alert(self, alert_data: dict) -> dict:
        """Process TradingView webhook alert"""
        try:
            required_fields = ['exchange', 'symbol', 'side', 'amount']
            for field in required_fields:
                if field not in alert_data:
                    raise ValueError(f"Missing required field: {field}")

            return {
                'status': 'success',
                'message': 'Alert processed successfully'
            }

        except Exception as e:
            logger.error(f"Failed to process TradingView alert: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def fetch_balance(self) -> dict:
        """모든 거래소의 잔액 정보를 가져옵니다."""
        try:
            balances = {}

            # MEXC 잔액
            try:
                logger.info("Attempting to fetch MEXC balance...")
                futures_options = {
                    'type': 'swap',    # Use swap for futures trading
                    'settle': 'USDT',   # USDT-settled contracts
                    'subType': 'linear'  # Linear contracts
                }
                mexc_balance = self.mexc.fetch_balance(params=futures_options)
                logger.info(f"Raw MEXC balance response: {mexc_balance}")

                # USDT 잔액 정보 추출
                balances['MEXC'] = {
                    'USDT': 0,
                    'free': 0,
                    'used': 0,
                    'dailyPnL': 0.0,
                    'monthlyPnL': 0.0
                }

                if isinstance(mexc_balance, dict):
                    # info 필드가 있는 경우
                    if 'info' in mexc_balance:
                        logger.info(f"MEXC balance info field: {mexc_balance['info']}")

                    # USDT 잔액이 있는 경우
                    if 'USDT' in mexc_balance:
                        usdt_balance = mexc_balance['USDT']
                        if isinstance(usdt_balance, dict):
                            balances['MEXC'] = {
                                'USDT': usdt_balance.get('total', 0),
                                'free': usdt_balance.get('free', 0),
                                'used': usdt_balance.get('used', 0),
                                'dailyPnL': 0.0,  # 임시 데이터
                                'monthlyPnL': 0.0  # 임시 데이터
                            }
                            logger.info(f"MEXC balance formatted successfully: {balances['MEXC']}")
                        else:
                            logger.warning(f"Unexpected USDT balance format: {usdt_balance}")
                    else:
                        logger.warning("USDT balance not found in MEXC response")
                else:
                    logger.warning(f"Unexpected MEXC balance response type: {type(mexc_balance)}")

            except Exception as e:
                logger.error(f"Failed to fetch MEXC balance: {str(e)}", exc_info=True)
                logger.info("Using default values for MEXC balance")
                balances['MEXC'] = {
                    'USDT': 0,
                    'free': 0,
                    'used': 0,
                    'dailyPnL': 0,
                    'monthlyPnL': 0
                }

            # Gate.io 잔액
            try:
                gateio_balance = self.gateio.fetch_balance({'type': 'swap'})
                balances['Gate.io'] = {
                    'USDT': gateio_balance['USDT']['total'],
                    'free': gateio_balance['USDT']['free'],
                    'used': gateio_balance['USDT']['used'],
                    'dailyPnL': -0.2,  # 임시 데이터
                    'monthlyPnL': 1.8   # 임시 데이터
                }
                logger.info(f"Gate.io balance fetched: {balances['Gate.io']}")
            except Exception as e:
                logger.error(f"Failed to fetch Gate.io balance: {e}")
                balances['Gate.io'] = {'USDT': 0, 'free': 0, 'used': 0, 'dailyPnL': 0, 'monthlyPnL': 0}

            # Bitget 잔액
            try:
                bitget_balance = self.bitget.fetch_balance({'type': 'swap'})
                balances['Bitget'] = {
                    'USDT': bitget_balance['USDT']['total'],
                    'free': bitget_balance['USDT']['free'],
                    'used': bitget_balance['USDT']['used'],
                    'dailyPnL': 0.8,  # 임시 데이터
                    'monthlyPnL': 3.5  # 임시 데이터
                }
                logger.info(f"Bitget balance fetched: {balances['Bitget']}")
            except Exception as e:
                logger.error(f"Failed to fetch Bitget balance: {e}")
                balances['Bitget'] = {'USDT': 0, 'free': 0, 'used': 0, 'dailyPnL': 0, 'monthlyPnL': 0}

            return balances

        except Exception as e:
            logger.error(f"Failed to fetch balances: {e}")
            return {}

    def test_single_order(self, exchange: str, symbol: str, side: str, amount: float) -> Optional[Dict[str, Any]]:
        """단일 거래소에 테스트 주문을 실행합니다."""
        try:
            # MEXC 선물 거래 설정
            if exchange == 'mexc':
                try:
                    # MEXC API 설정 확인
                    api_key = os.environ.get('MEXC_API_KEY')
                    secret_key = os.environ.get('MEXC_API_SECRET')
                    logger.info(f"MEXC API Key exists: {bool(api_key)}, Secret exists: {bool(secret_key)}")

                    # 올바른 선물 심볼 형식
                    futures_symbol = "XRP_USDT"  # 올바른 선물 심볼 형식
                    logger.info(f"Attempting to place order on MEXC futures for {futures_symbol}")

                    # 현재 타임스탬프 생성
                    timestamp = str(int(time.time() * 1000))

                    # API 요청 파라미터 설정
                    params = {
                        "symbol": futures_symbol,
                        "vol": amount,           # USDT 기준 주문량
                        "price": 0,              # 시장가 주문
                        "side": 1,               # 1: 매수(Long)
                        "type": 1,               # 1: 시장가 주문
                        "openType": 2,           # 1: Isolated, 2: Cross
                        "leverage": 1,           # 1배 레버리지
                        "positionType": 1,       # 1: Long, 2: Short
                        "api_key": api_key,      # API Key 추가
                        "req_time": timestamp,   # 요청 시간 추가
                    }

                    logger.info(f"MEXC order parameters: {params}")

                    # 서명 생성
                    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params.keys())])
                    signature = hmac.new(
                        secret_key.encode(),
                        query_string.encode(),
                        hashlib.sha256
                    ).hexdigest()
                    params["sign"] = signature

                    # 요청 헤더 설정
                    headers = {
                        "Content-Type": "application/json"
                    }

                    # API 요청 실행
                    response = requests.post(
                        "https://contract.mexc.com/api/v1/private/order/submit",
                        json=params,
                        headers=headers
                    )

                    # 응답 데이터 확인
                    response_data = response.json()
                    logger.info(f"MEXC order response: {response_data}")

                    if response.status_code == 200 and response_data.get('success'):
                        return {'order': response_data}
                    else:
                        logger.error(f"MEXC order failed: {response_data}")
                        return None

                except Exception as e:
                    logger.error(f"Failed to execute test order on MEXC: {str(e)}")
                    if hasattr(e, 'response'):
                        logger.error(f"MEXC API response: {e.response}")
                    return None

            elif exchange == 'gateio':
                try:
                    self.gateio.set_margin_mode('cross', symbol)
                    self.gateio.set_leverage(1, symbol)
                    logger.info(f"Set cross mode and 1x leverage for {symbol} on Gate.io")
                    order = self.execute_order(exchange, symbol, side, amount, leverage=1)
                    if order:
                        logger.info(f"Test order executed successfully on Gate.io: {side} {amount} {symbol}")
                        return order
                except Exception as e:
                    logger.error(f"Failed to execute test order on Gate.io: {e}")
                    return None
            elif exchange == 'bitget':
                try:
                    params = {
                        'marginCoin': 'USDT',
                        'marginMode': 'cross'
                    }
                    self.bitget.set_margin_mode('cross', symbol, params)
                    self.bitget.set_leverage(1, symbol)
                    logger.info(f"Set cross mode and 1x leverage for {symbol} on Bitget")
                    order = self.execute_order(exchange, symbol, side, amount, leverage=1)
                    if order:
                        logger.info(f"Test order executed successfully on Bitget: {side} {amount} {symbol}")
                        return order
                except Exception as e:
                    logger.error(f"Failed to execute test order on Bitget: {e}")
                    return None
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to execute test order: {e}")
            return None
import os
import logging
import threading
import time
from datetime import datetime
import pytz
from flask import Flask, render_template, jsonify, request
from trading import TradingExecutor
from price_monitor import PriceGapMonitor

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Global variables
trading_executor = None
price_monitor = None
is_initialized = False
initialization_status = "Starting..."
initialization_details = []

# Korean timezone
KST = pytz.timezone('Asia/Seoul')

def get_current_time():
    """현재 한국 시간을 반환합니다."""
    return datetime.now(KST)

def initialize_components():
    """시스템 컴포넌트 초기화"""
    global trading_executor, price_monitor, is_initialized, initialization_status, initialization_details
    logger.info("Starting initialization process...")

    try:
        # 1. API 키 확인 (Removed API key verification from this function)

        # 2. Trading Executor 초기화
        initialization_status = "거래소 연결 중..."
        initialization_details.append("거래소 연결 중...")
        try:
            global trading_executor
            trading_executor = TradingExecutor()
            initialization_details.append("✅ 거래소 연결 완료")
        except Exception as e:
            logger.error(f"Trading executor initialization failed: {e}")
            initialization_status = f"거래 실행기 초기화 실패: {str(e)}"
            return

        # 3. Price Monitor 초기화
        initialization_status = "가격 모니터링 시스템 초기화 중..."
        initialization_details.append("가격 모니터링 시스템 초기화 중...")
        try:
            global price_monitor
            price_monitor = PriceGapMonitor()
            initialization_details.append("✅ 가격 모니터링 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"Price monitor initialization failed: {e}")
            initialization_status = f"가격 모니터링 초기화 실패: {str(e)}"
            return

        initialization_status = "Ready"
        is_initialized = True
        logger.info("All components initialized successfully")

    except Exception as e:
        error_msg = f"Initialization failed: {str(e)}"
        logger.error(error_msg)
        initialization_status = f"초기화 오류: {str(e)}"
        is_initialized = False

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('orderbook.html')

@app.route('/balance')
def balance_page():
    """잔액 정보 페이지"""
    return render_template('balance.html')

@app.route('/orderbook')
def orderbook_page():
    """상세 호가창 페이지"""
    return render_template('orderbook.html')

@app.route('/api/status')
def get_status():
    """Get initialization status"""
    return jsonify({
        'initialized': is_initialized,
        'status': initialization_status,
        'details': initialization_details
    })

@app.route('/api/current_time')
def get_current_time_api():
    """현재 서버 시간을 반환합니다."""
    current_time = datetime.now(KST)
    return jsonify({
        'timestamp': int(current_time.timestamp() * 1000),
        'timezone': 'Asia/Seoul',
        'formatted_time': current_time.strftime('%H:%M:%S')
    })

@app.route('/api/orderbook')
def api_get_orderbook():
    """Get orderbook data from exchanges"""
    if not is_initialized:
        return jsonify({
            'error': 'System initializing, please wait...',
            'status': initialization_status,
            'details': initialization_details
        }), 503

    try:
        symbols = ['XRP/USDT', 'DOGE/USDT']
        results = []

        for symbol in symbols:
            try:
                # MEXC-Bitget pair
                mexc_orderbook = trading_executor.fetch_order_book('mexc', symbol, limit=3)
                mexc_ticker = trading_executor.fetch_ticker('mexc', symbol)
                bitget_orderbook = trading_executor.fetch_order_book('bitget', symbol, limit=3)
                bitget_ticker = trading_executor.fetch_ticker('bitget', symbol)

                # Gate.io-Bitget pair
                gateio_orderbook = trading_executor.fetch_order_book('gateio', symbol, limit=3)
                gateio_ticker = trading_executor.fetch_ticker('gateio', symbol)

                # MEXC-Bitget 가격 차이 계산
                mexc_price = float(mexc_ticker['last'])
                bitget_price = float(bitget_ticker['last'])
                mexc_bitget_gap = ((mexc_price - bitget_price) / bitget_price) * 100
                mexc_bitget_usdt = mexc_price - bitget_price

                # Gate.io-Bitget 가격 차이 계산
                gateio_price = float(gateio_ticker['last'])
                gateio_bitget_gap = ((gateio_price - bitget_price) / bitget_price) * 100
                gateio_bitget_usdt = gateio_price - bitget_price

                results.extend([
                    format_orderbook_data('MEXC Futures', symbol, mexc_orderbook, mexc_ticker['last'], mexc_bitget_gap, mexc_bitget_usdt),
                    format_orderbook_data('Gate.io Futures', symbol, gateio_orderbook, gateio_ticker['last'], gateio_bitget_gap, gateio_bitget_usdt),
                    format_orderbook_data('Bitget Futures', symbol, bitget_orderbook, bitget_ticker['last'], 0, 0),
                ])

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")

        if not results:
            return jsonify({'error': 'Failed to fetch data'}), 500

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error in get_orderbook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/balance')
def api_get_balance():
    """거래소 잔액 정보를 반환합니다."""
    if not is_initialized:
        return jsonify({
            'error': 'System initializing, please wait...',
            'status': initialization_status,
            'details': initialization_details
        }), 503

    try:
        balances = trading_executor.fetch_balance()
        return jsonify(balances)
    except Exception as e:
        logger.error(f"Error fetching balances: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading/start', methods=['POST'])
def start_trading():
    """자동매매 시작"""
    try:
        if not price_monitor:
            return jsonify({'error': '시스템이 초기화되지 않았습니다.'}), 500

        price_monitor.start()
        return jsonify({'status': 'success', 'message': '자동매매가 시작되었습니다.'})
    except Exception as e:
        logger.error(f"Failed to start trading: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading/stop', methods=['POST'])
def stop_trading():
    """자동매매 종료"""
    try:
        if not price_monitor:
            return jsonify({'error': '시스템이 초기화되지 않았습니다.'}), 500

        price_monitor.stop()
        return jsonify({'status': 'success', 'message': '자동매매가 종료되었습니다.'})
    except Exception as e:
        logger.error(f"Failed to stop trading: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading/status')
def get_trading_status():
    """자동매매 상태 확인"""
    try:
        if not price_monitor:
            return jsonify({'status': 'not_initialized'})

        status = 'running' if price_monitor.running else 'stopped'
        return jsonify({'status': status})
    except Exception as e:
        logger.error(f"Failed to get trading status: {e}")
        return jsonify({'error': str(e)}), 500

def format_orderbook_data(exchange, symbol, orderbook, last_price, price_gap, price_gap_usdt):
    """호가 데이터 포맷팅"""
    asks = [[float(price), float(amount), float(price) * float(amount)]
            for price, amount in orderbook['asks'][:3]]
    bids = [[float(price), float(amount), float(price) * float(amount)]
            for price, amount in orderbook['bids'][:3]]

    return {
        'exchange': exchange,
        'symbol': symbol,
        'asks': asks,
        'bids': bids,
        'last_price': last_price,
        'last_price_krw': float(last_price) * 1300,
        'price_gap': price_gap,
        'price_gap_usdt': price_gap_usdt,
        'timestamp': int(get_current_time().timestamp() * 1000)
    }

if __name__ == '__main__':
    # Start initialization in a separate thread
    init_thread = threading.Thread(target=initialize_components)
    init_thread.start()

    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
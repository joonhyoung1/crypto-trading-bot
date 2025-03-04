import os
import logging
import requests
import hmac
import hashlib
import time
import json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def mask_api_key(key: str) -> str:
    """API 키를 마스킹 처리"""
    if not key:
        return "None"
    return f"{key[:4]}...{key[-4:]}"

def test_mexc_order(symbol: str, volume: float, side: int = 1, leverage: int = 1):
    """MEXC 선물 거래 주문 실행
    side: 1 = Long(매수), 2 = Short(매도)
    """
    try:
        # API 키 설정
        api_key = os.environ.get('MEXC_API_KEY')
        secret_key = os.environ.get('MEXC_API_SECRET')
        logger.info(f"Using MEXC API Key: {mask_api_key(api_key)}")

        # API 요청 파라미터 설정
        params = {
            "symbol": symbol,          # "XRP_USDT"
            "volume": str(volume),     # 주문 수량 (USDT 기준)
            "leverage": str(leverage), # 레버리지 설정
            "side": side,              # 1: 매수(Long), 2: 매도(Short)
            "type": 1,                 # 1: 시장가 주문
            "openType": 2,             # 1: Isolated, 2: Cross
            "positionType": side       # 1: Long, 2: Short
        }

        # 정렬된 파라미터로 쿼리 스트링 생성
        sorted_params = sorted(params.items())
        query_string = '&'.join([f"{key}={value}" for key, value in sorted_params])
        logger.debug(f"MEXC raw params: {params}")
        logger.debug(f"MEXC sorted query string: {query_string}")

        # 현재 타임스탬프 생성
        timestamp = str(int(time.time() * 1000))
        logger.debug(f"MEXC timestamp: {timestamp}")

        # 서명 생성
        sign_data = timestamp + query_string
        logger.debug(f"MEXC sign data (hex): {sign_data.encode().hex()}")
        signature = hmac.new(secret_key.encode(), sign_data.encode(), hashlib.sha256).hexdigest()
        logger.debug(f"MEXC signature: {signature[:4]}...{signature[-4:]}")

        # 요청 헤더 설정
        headers = {
            "Content-Type": "application/json",
            "X-MEXC-APIKEY": api_key,
            "X-MEXC-SIGNATURE": signature,
            "X-MEXC-TIMESTAMP": timestamp
        }

        # 로깅을 위한 안전한 헤더
        safe_headers = headers.copy()
        safe_headers["X-MEXC-APIKEY"] = mask_api_key(safe_headers["X-MEXC-APIKEY"])
        safe_headers["X-MEXC-SIGNATURE"] = f"{safe_headers['X-MEXC-SIGNATURE'][:4]}...{safe_headers['X-MEXC-SIGNATURE'][-4:]}"
        logger.info(f"MEXC request headers: {safe_headers}")
        logger.info(f"MEXC request params: {params}")

        # API 요청 실행
        base_url = "https://contract.mexc.com"
        url = f"{base_url}/api/v1/private/order/submit"
        logger.debug(f"MEXC request URL: {url}")

        try:
            response = requests.post(
                url,
                json=params,
                headers=headers,
                timeout=60  # 타임아웃 증가
            )
            logger.debug(f"MEXC response status: {response.status_code}")
            logger.debug(f"MEXC response headers: {dict(response.headers)}")

            result = response.json()
            logger.info(f"MEXC order response: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to parse MEXC response: {e}")
            if response is not None:
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response text: {response.text}")
            return None

    except requests.Timeout:
        logger.error("MEXC API request timed out")
        return None
    except Exception as e:
        logger.error(f"Error executing MEXC test order: {e}")
        return None

def test_bitget_order(symbol: str, volume: float, side: str = "buy", leverage: int = 1):
    """Bitget 선물 거래 주문 실행"""
    try:
        # API 키 설정
        api_key = os.environ.get('BITGET_API_KEY')
        secret_key = os.environ.get('BITGET_API_SECRET')
        passphrase = os.environ.get('BITGET_PASSPHRASE')
        logger.info(f"Using Bitget API Key: {api_key[:4]}...{api_key[-4:]}")

        # API 요청 파라미터 설정
        symbol = f"{symbol}_UMCBL"  # Convert XRPUSDT to XRPUSDT_UMCBL
        params = {
            "symbol": symbol,        # "XRPUSDT_UMCBL"
            "marginCoin": "USDT",
            "size": str(volume),     # 주문 수량
            "side": side,            # "buy" or "sell"
            "orderType": "market",   # 시장가 주문
            "leverage": str(leverage),    # 레버리지 설정 (문자열로 변환)
            "clientOid": str(int(time.time() * 1000))  # 고유 주문 ID
        }

        # 요청 바디 생성 (공백 없이)
        body = json.dumps(params, separators=(',', ':'))
        path = "/api/mix/v1/order/placeOrder"
        timestamp = str(int(time.time() * 1000))

        # 서명 생성 (timestamp + "POST" + requestPath + body)
        message = timestamp + "POST" + path + body
        logger.debug(f"Bitget request params: {params}")
        logger.debug(f"Bitget timestamp: {timestamp}")
        logger.debug(f"Bitget sign message: {message}")
        logger.debug(f"Bitget sign message (hex): {message.encode().hex()}")
        signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
        logger.debug(f"Bitget signature: {signature}")

        # 요청 헤더 설정
        headers = {
            "ACCESS-KEY": api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json"
        }

        # 로깅을 위한 안전한 헤더
        safe_headers = headers.copy()
        safe_headers["ACCESS-KEY"] = f"{safe_headers['ACCESS-KEY'][:4]}...{safe_headers['ACCESS-KEY'][-4:]}"
        safe_headers["ACCESS-SIGN"] = f"{safe_headers['ACCESS-SIGN'][:4]}...{safe_headers['ACCESS-SIGN'][-4:]}"
        safe_headers["ACCESS-PASSPHRASE"] = "********"
        logger.info(f"Bitget request headers: {safe_headers}")
        logger.info(f"Bitget request body: {body}")

        # API 요청 실행
        base_url = "https://api.bitget.com"
        url = f"{base_url}{path}"
        logger.debug(f"Bitget request URL: {url}")

        response = requests.post(url, json=params, headers=headers, timeout=30)
        logger.debug(f"Bitget response status: {response.status_code}")
        logger.debug(f"Bitget response headers: {dict(response.headers)}")

        try:
            result = response.json()
            logger.info(f"Bitget order response: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to parse Bitget response: {e}")
            if response is not None:
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response text: {response.text}")
            return None

    except requests.Timeout:
        logger.error("Bitget API request timed out")
        return None
    except Exception as e:
        logger.error(f"Error executing Bitget test order: {e}")
        return None

def test_gateio_order(symbol: str, volume: float, side: str = "buy", leverage: int = 1):
    """Gate.io 선물 거래 주문 실행"""
    try:
        # API 키 설정
        api_key = os.environ.get('GATEIO_API_KEY')
        secret_key = os.environ.get('GATEIO_API_SECRET')
        logger.info(f"Using Gate.io API Key: {mask_api_key(api_key)}")

        # API 요청 파라미터 설정
        params = {
            "contract": symbol,        # "XRP_USDT"
            "size": str(volume),       # 주문 수량
            "price": "0",              # 시장가 주문
            "tif": "ioc",             # Time in Force ("ioc": 즉시 실행)
            "text": f"t-{int(time.time())}",  # 고유 주문 ID
            "side": side,             # "buy" or "sell"
            "reduce_only": False,     # 포지션 감소 여부
            "is_close": False         # 포지션 종료 여부
        }

        # 요청 바디 생성
        body = json.dumps(params, separators=(',', ':'))
        path = "/api/v4/futures/usdt/orders"
        query_string = "settle=usdt"
        timestamp = str(int(time.time()))

        # 서명 생성 (HTTP_METHOD\nPATH\nQUERY_STRING\nBODY\nTIMESTAMP)
        pre_hash_string = f"POST\n{path}\n{query_string}\n{body}\n{timestamp}"
        logger.debug(f"Gate.io raw params: {params}")
        logger.debug(f"Gate.io request body: {body}")
        logger.debug(f"Gate.io sign message: {pre_hash_string}")
        logger.debug(f"Gate.io sign message (hex): {pre_hash_string.encode().hex()}")
        signature = hmac.new(secret_key.encode(), pre_hash_string.encode(), hashlib.sha512).hexdigest()
        logger.debug(f"Gate.io signature: {signature}")

        # 요청 헤더 설정
        headers = {
            "KEY": api_key,
            "SIGN": signature,
            "Timestamp": timestamp,
            "Content-Type": "application/json"
        }

        # API 요청 실행
        base_url = "https://api.gateio.ws"
        url = f"{base_url}{path}?{query_string}"
        logger.debug(f"Gate.io request URL: {url}")

        response = requests.post(
            url,
            json=params,
            headers=headers,
            timeout=30
        )
        logger.debug(f"Gate.io response status: {response.status_code}")
        logger.debug(f"Gate.io response headers: {dict(response.headers)}")

        try:
            result = response.json()
            logger.info(f"Gate.io order response: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to parse Gate.io response: {e}")
            if response is not None:
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response text: {response.text}")
            return None

    except requests.Timeout:
        logger.error("Gate.io API request timed out")
        return None
    except Exception as e:
        logger.error(f"Error executing Gate.io test order: {e}")
        return None

if __name__ == "__main__":
    # MEXC 매도 주문 테스트 (side=2는 매도)
    print("\n=== Testing MEXC Sell Order ===")
    mexc_result = test_mexc_order("XRP_USDT", 30, side=2, leverage=1)
    print(f"MEXC 매도 주문 결과: {mexc_result}")

    time.sleep(1)  # API 호출 간 간격 추가

    # Bitget 매도 주문 테스트 
    print("\n=== Testing Bitget Sell Order ===")
    result = test_bitget_order("XRPUSDT", 30, side="sell", leverage=1)
    print(f"Bitget 매도 주문 결과: {result}")

    time.sleep(1)  # API 호출 간 간격 추가

    # Gate.io 매도 주문 테스트
    print("\n=== Testing Gate.io Sell Order ===")
    gateio_result = test_gateio_order("XRP_USDT", 30, side="sell", leverage=1)
    print(f"Gate.io 매도 주문 결과: {gateio_result}")
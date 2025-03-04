const previousPrices = {};

function formatNumber(number, decimals = 2) {
    return number.toLocaleString('ko-KR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatPercentage(number) {
    return number != null ? (number >= 0 ? '+' : '') + number.toFixed(2) + '%' : '0.00%';
}

function updateCurrentTime() {
    fetch('/api/current_time')
        .then(response => response.json())
        .then(data => {
            document.querySelectorAll('.current-time').forEach(el => {
                el.textContent = `현재 시간: ${data.formatted_time}`;
            });
        })
        .catch(error => {
            console.error('Error fetching server time:', error);
            const now = new Date();
            const timeStr = now.toLocaleTimeString('ko-KR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false,
                timeZone: 'Asia/Seoul'
            });
            document.querySelectorAll('.current-time').forEach(el => {
                el.textContent = `현재 시간: ${timeStr}`;
            });
        });
}

let isUpdating = false;
let retryCount = 0;
const MAX_RETRIES = 3;
const RETRY_DELAY = 2000;
const REFRESH_INTERVAL = 500; // 0.5초로 변경
const USDT_TO_KRW = 1300;

function getExchangeLogo(exchange) {
    switch (exchange) {
        case 'MEXC Futures':
            return '<i class="fas fa-chart-line text-primary"></i>';
        case 'Bitget Futures':
            return '<i class="fas fa-chart-bar text-success"></i>';
        case 'Gate.io Futures':
            return '<i class="fas fa-chart-pie text-warning"></i>';
        default:
            return '<i class="fas fa-exchange-alt"></i>';
    }
}

function createExchangeCard(data) {
    if (!data || !data.symbol) {
        console.error('Invalid data in createExchangeCard:', data);
        return '';
    }

    const priceGapClass = !data.price_gap ? '' :
                           data.price_gap >= 0 ? 'text-success' : 'text-danger';

    // 가격 차이 표시 (퍼센트와 USDT 차이)
    let priceGapValue;
    if (data.price_gap === 0) {
        priceGapValue = '기준';
    } else {
        const percentageGap = formatPercentage(data.price_gap);
        const usdtGapValue = formatNumber(Math.abs(data.price_gap_usdt), 6);
        const usdtGapSign = data.price_gap_usdt >= 0 ? '+' : '-';
        priceGapValue = `${percentageGap} (${usdtGapSign}${usdtGapValue})`;
    }

    const baseCurrency = data.symbol.split('/')[0];
    const decimals = baseCurrency === 'XRP' ? 4 : 5;

    return `
        <div class="col-md-6">
            <div class="card h-100">
                <div class="card-header py-2">
                    <h6 class="mb-0">
                        ${getExchangeLogo(data.exchange)}
                        ${data.exchange} ${data.symbol}
                    </h6>
                    <div class="d-flex align-items-center">
                        <span class="current-time small text-muted">--:--:--</span>
                    </div>
                </div>
                <div class="card-body p-0">
                    <table class="table table-sm mb-0">
                        <thead>
                            <tr>
                                <th>${baseCurrency}</th>
                                <th>KRW</th>
                                <th>합계(KRW)</th>
                            </tr>
                        </thead>
                        <tbody class="text-danger sell-orders">
                            <!-- Sell orders -->
                        </tbody>
                        <tbody class="text-center bg-dark current-price">
                            <!-- Current price -->
                        </tbody>
                        <tbody class="text-success buy-orders">
                            <!-- Buy orders -->
                        </tbody>
                    </table>
                    <div class="card-footer py-2 text-center">
                        <span class="${priceGapClass}">
                            ${priceGapValue}
                        </span>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function updateOrderBook(data, cardElement) {
    if (!data || !data.asks || !data.bids) {
        console.error('Invalid data in updateOrderBook:', data);
        return;
    }

    // DOM elements cache
    const sellOrders = cardElement.querySelector('.sell-orders');
    const currentPrice = cardElement.querySelector('.current-price');
    const buyOrders = cardElement.querySelector('.buy-orders');

    const baseCurrency = data.symbol.split('/')[0];
    const decimals = baseCurrency === 'XRP' ? 4 : 5;

    // 가격 변화 감지를 위한 키 생성
    const priceKey = `${data.exchange}-${data.symbol}`;
    const previousPrice = previousPrices[priceKey];
    const currentPriceValue = data.last_price;

    // 가격 변화에 따른 클래스 설정
    let priceChangeClass = '';
    if (previousPrice) {
        priceChangeClass = currentPriceValue > previousPrice ? 'price-up' :
                          currentPriceValue < previousPrice ? 'price-down' : '';
    }
    previousPrices[priceKey] = currentPriceValue;

    // Create document fragment for better performance
    const sellFragment = document.createDocumentFragment();
    const buyFragment = document.createDocumentFragment();

    // Update using requestAnimationFrame for better performance
    requestAnimationFrame(() => {
        // Update sell orders
        data.asks.slice().reverse().forEach(order => {
            const [price, amount, total, krwPrice] = order;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${formatNumber(amount, decimals)}</td>
                <td>${formatNumber(krwPrice, 0)}원</td>
                <td>${formatNumber(krwPrice * amount, 0)}원</td>
            `;
            sellFragment.appendChild(row);
        });

        // Update current price with animation class
        if (data.last_price) {
            const row = document.createElement('tr');
            row.className = priceChangeClass;
            row.innerHTML = `
                <td colspan="3" class="fw-bold py-2">
                    현재가: ${formatNumber(data.last_price_krw, 0)}원
                </td>
            `;
            currentPrice.innerHTML = '';
            currentPrice.appendChild(row);
        }

        // Update buy orders
        data.bids.forEach(order => {
            const [price, amount, total, krwPrice] = order;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${formatNumber(amount, decimals)}</td>
                <td>${formatNumber(krwPrice, 0)}원</td>
                <td>${formatNumber(krwPrice * amount, 0)}원</td>
            `;
            buyFragment.appendChild(row);
        });

        // Batch DOM updates
        sellOrders.innerHTML = '';
        buyOrders.innerHTML = '';
        sellOrders.appendChild(sellFragment);
        buyOrders.appendChild(buyFragment);
    });
}

async function checkInitialization() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        return {
            initialized: data.initialized,
            status: data.status,
            details: data.details || []
        };
    } catch (error) {
        console.error('Error checking initialization status:', error);
        return {
            initialized: false,
            status: 'Error checking status',
            details: []
        };
    }
}

function showInitializing(status, details) {
    const row1 = document.getElementById('exchangeCardsRow1');
    const row2 = document.getElementById('exchangeCardsRow2');
    if (row1) {
        const detailsHtml = details.map(detail =>
            `<li class="small ${detail.includes('✅') ? 'text-success' : 'text-muted'}">${detail}</li>`
        ).join('');

        row1.innerHTML = `
            <div class="col-12">
                <div class="alert alert-info">
                    <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-spinner fa-spin me-2"></i>
                        <span>시스템 초기화 중입니다...</span>
                    </div>
                    <small class="text-muted d-block mb-2">${status}</small>
                    <ul class="mb-0 ps-3">
                        ${detailsHtml}
                    </ul>
                </div>
            </div>
        `;
        if (row2) row2.innerHTML = '';
    }
}

function updatePriceGapSummary(data) {
    const summaryDiv = document.getElementById('priceGapSummary');
    summaryDiv.innerHTML = '';

    // Group data by symbol
    const groupedData = data.reduce((acc, exchange) => {
        if (!exchange || !exchange.symbol) return acc;

        if (!acc[exchange.symbol]) {
            acc[exchange.symbol] = {};
        }
        acc[exchange.symbol][exchange.exchange] = exchange;
        return acc;
    }, {});

    // Create summary for each symbol
    Object.entries(groupedData).forEach(([symbol, exchanges]) => {
        if (exchanges['MEXC Futures'] && exchanges['Bitget Futures']) {
            const mexcData = exchanges['MEXC Futures'];
            const bitgetData = exchanges['Bitget Futures'];

            // Create MEXC vs Bitget comparison
            const col = document.createElement('div');
            col.className = 'col-md-6 mb-3';

            const percentageClass = mexcData.price_gap >= 0 ? 'text-success' : 'text-danger';
            const percentageText = formatPercentage(mexcData.price_gap);
            const usdtText = formatNumber(Math.abs(mexcData.price_gap_usdt), 6);
            const usdtSign = mexcData.price_gap_usdt >= 0 ? '+' : '-';

            // 갭 방향에 따른 거래 가능 금액 계산
            let mexcAmount, bitgetAmount;
            if (mexcData.price_gap >= 0) {
                // MEXC에서 매수, Bitget에서 매도
                mexcAmount = mexcData.asks[0][2] * 1300;  // 시장가 매수 가능 금액 (원화)
                bitgetAmount = bitgetData.bids[0][2] * 1300;  // 시장가 매도 가능 금액 (원화)
            } else {
                // MEXC에서 매도, Bitget에서 매수
                mexcAmount = mexcData.bids[0][2] * 1300;  // 시장가 매도 가능 금액 (원화)
                bitgetAmount = bitgetData.asks[0][2] * 1300;  // 시장가 매수 가능 금액 (원화)
            }

            col.innerHTML = `
                <div class="d-flex align-items-center">
                    <span class="badge bg-primary me-2">${symbol}</span>
                    <span class="me-2">MEXC-Bitget:</span>
                    <span class="${percentageClass}">
                        ${percentageText} (${usdtSign}${usdtText})
                        <small class="ms-2 text-muted">
                            [${formatNumber(mexcAmount, 0)}원 ↔ ${formatNumber(bitgetAmount, 0)}원]
                        </small>
                    </span>
                </div>
            `;
            summaryDiv.appendChild(col);
        }

        if (exchanges['Gate.io Futures'] && exchanges['Bitget Futures']) {
            const gateData = exchanges['Gate.io Futures'];
            const bitgetData = exchanges['Bitget Futures'];

            // Create Gate.io vs Bitget comparison
            const col = document.createElement('div');
            col.className = 'col-md-6 mb-3';

            const percentageClass = gateData.price_gap >= 0 ? 'text-success' : 'text-danger';
            const percentageText = formatPercentage(gateData.price_gap);
            const usdtText = formatNumber(Math.abs(gateData.price_gap_usdt), 6);
            const usdtSign = gateData.price_gap_usdt >= 0 ? '+' : '-';

            // 갭 방향에 따른 거래 가능 금액 계산
            let gateAmount, bitgetAmount;
            if (gateData.price_gap >= 0) {
                // Gate.io에서 매수, Bitget에서 매도
                gateAmount = gateData.asks[0][2] * 1300;  // 시장가 매수 가능 금액 (원화)
                bitgetAmount = bitgetData.bids[0][2] * 1300;  // 시장가 매도 가능 금액 (원화)
            } else {
                // Gate.io에서 매도, Bitget에서 매수
                gateAmount = gateData.bids[0][2] * 1300;  // 시장가 매도 가능 금액 (원화)
                bitgetAmount = bitgetData.asks[0][2] * 1300;  // 시장가 매수 가능 금액 (원화)
            }

            col.innerHTML = `
                <div class="d-flex align-items-center">
                    <span class="badge bg-primary me-2">${symbol}</span>
                    <span class="me-2">Gate-Bitget:</span>
                    <span class="${percentageClass}">
                        ${percentageText} (${usdtSign}${usdtText})
                        <small class="ms-2 text-muted">
                            [${formatNumber(gateAmount, 0)}원 ↔ ${formatNumber(bitgetAmount, 0)}원]
                        </small>
                    </span>
                </div>
            `;
            summaryDiv.appendChild(col);
        }
    });
}

async function fetchOrderBook() {
    if (isUpdating) return;
    isUpdating = true;

    try {
        const initStatus = await checkInitialization();

        if (!initStatus.initialized) {
            showInitializing(initStatus.status, initStatus.details);
            setTimeout(fetchOrderBook, 2000);
            isUpdating = false;
            return;
        }

        const response = await fetch('/api/orderbook');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (!Array.isArray(data)) {
            console.error('Invalid data format:', data);
            throw new Error('Invalid data format received from server');
        }

        // Update price gap summary
        updatePriceGapSummary(data);

        const row1 = document.getElementById('exchangeCardsRow1');
        const row2 = document.getElementById('exchangeCardsRow2');

        if (!row1 || !row2) {
            throw new Error('Required DOM elements not found');
        }

        row1.innerHTML = '';
        row2.innerHTML = '';

        const groupedData = data.reduce((acc, exchange) => {
            if (!exchange || !exchange.symbol) {
                console.error('Invalid exchange data:', exchange);
                return acc;
            }

            const symbol = exchange.symbol;
            if (!acc[symbol]) {
                acc[symbol] = {};
            }
            acc[symbol][exchange.exchange] = exchange;
            return acc;
        }, {});

        Object.entries(groupedData).forEach(([symbol, exchanges]) => {
            if (exchanges['MEXC Futures'] && exchanges['Bitget Futures']) {
                const mexcCard = createExchangeCard(exchanges['MEXC Futures']);
                const bitgetCard = createExchangeCard(exchanges['Bitget Futures']);

                if (mexcCard && bitgetCard) {
                    row1.insertAdjacentHTML('beforeend', mexcCard);
                    row1.insertAdjacentHTML('beforeend', bitgetCard);
                    updateOrderBook(exchanges['MEXC Futures'], row1.children[row1.children.length - 2]);
                    updateOrderBook(exchanges['Bitget Futures'], row1.children[row1.children.length - 1]);
                }
            }

            if (exchanges['Gate.io Futures'] && exchanges['Bitget Futures']) {
                const gateCard = createExchangeCard(exchanges['Gate.io Futures']);
                const bitgetCard = createExchangeCard(exchanges['Bitget Futures']);

                if (gateCard && bitgetCard) {
                    row2.insertAdjacentHTML('beforeend', gateCard);
                    row2.insertAdjacentHTML('beforeend', bitgetCard);
                    updateOrderBook(exchanges['Gate.io Futures'], row2.children[row2.children.length - 2]);
                    updateOrderBook(exchanges['Bitget Futures'], row2.children[row2.children.length - 1]);
                }
            }
        });

        retryCount = 0;
    } catch (error) {
        console.error('Error:', error);
        await handleError(error.message);
    } finally {
        isUpdating = false;
    }
}

async function handleError(errorMsg) {
    if (retryCount < MAX_RETRIES) {
        retryCount++;
        console.log(`Retry attempt ${retryCount}`);
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * retryCount));
        await fetchOrderBook();
    } else {
        showError(errorMsg || '호가 정보를 가져오는데 실패했습니다.');
        retryCount = 0;
    }
}

function showError(message) {
    const row1 = document.getElementById('exchangeCardsRow1');
    const row2 = document.getElementById('exchangeCardsRow2');
    if (row1) {
        row1.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i> ${message}
                </div>
            </div>
        `;
        if (row2) row2.innerHTML = '';
    }
}

const style = document.createElement('style');
style.textContent = `
    .price-up {
        animation: flashGreen 0.5s ease-out;
    }
    .price-down {
        animation: flashRed 0.5s ease-out;
    }
    @keyframes flashGreen {
        0% { background-color: rgba(40, 167, 69, 0.3); }
        100% { background-color: transparent; }
    }
    @keyframes flashRed {
        0% { background-color: rgba(220, 53, 69, 0.3); }
        100% { background-color: transparent; }
    }
`;
document.head.appendChild(style);

fetchOrderBook();
updateCurrentTime();

setInterval(updateCurrentTime, 1000);
setInterval(fetchOrderBook, REFRESH_INTERVAL);
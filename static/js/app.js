const USDT_PRICE_KRW = 1450;

// 이전 데이터 저장용 객체
let previousPrices = {};

function updateCurrentTime() {
    fetch('/api/current_time')
        .then(response => response.json())
        .then(data => {
            document.getElementById('currentTime').textContent = `현재 시간: ${data.formatted_time}`;
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
            document.getElementById('currentTime').textContent = `현재 시간: ${timeStr}`;
        });
}

async function fetchPrices() {
    try {
        const response = await fetch('/api/orderbook');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        if (!Array.isArray(data)) {
            console.error('Invalid data format:', data);
            return;
        }

        // Group data by symbol
        const groupedData = data.reduce((acc, exchange) => {
            const symbol = exchange.symbol;
            if (!acc[symbol]) {
                acc[symbol] = {};
            }
            acc[symbol][exchange.exchange] = {
                price: exchange.last_price,
                status: 'success',
                asks: exchange.asks,
                bids: exchange.bids,
                last_price_krw: exchange.last_price_krw,
                price_gap: exchange.price_gap
            };
            return acc;
        }, {});

        // 새로운 데이터와 이전 데이터를 병합
        Object.entries(groupedData).forEach(([symbol, exchanges]) => {
            if (!previousPrices[symbol]) {
                previousPrices[symbol] = {};
            }
            Object.entries(exchanges).forEach(([exchange, info]) => {
                if (info && info.price !== null) {
                    previousPrices[symbol][exchange] = info;
                }
            });
        });

        // 병합된 데이터로 화면 업데이트
        updatePriceTable(previousPrices);
    } catch (error) {
        console.error('Error fetching prices:', error);
        // 오류 발생 시 이전 데이터로 테이블 유지
        if (Object.keys(previousPrices).length > 0) {
            updatePriceTable(previousPrices);
        } else {
            showError();
        }
    }
}

function formatNumber(number, decimals = 2) {
    return number.toLocaleString('ko-KR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatVolume(volume) {
    if (volume >= 1000000) {
        return `${formatNumber(volume / 1000000)}M`;
    } else if (volume >= 1000) {
        return `${formatNumber(volume / 1000)}K`;
    }
    return formatNumber(volume);
}

function updatePriceTable(data) {
    const tbody = document.querySelector('#priceTablesContainer table tbody');
    if (!tbody) {
        console.error('Price table tbody not found');
        return;
    }

    tbody.innerHTML = '';

    // 각 코인에 대한 데이터 표시
    Object.entries(data).forEach(([symbol, exchanges]) => {
        // Update comparison to use Bitget as the base exchange
        if (exchanges['MEXC Futures'] && exchanges['Bitget Futures']) {
            const row = document.createElement('tr');
            const mexcPrice = exchanges['MEXC Futures'].price;
            const bitgetPrice = exchanges['Bitget Futures'].price;
            const gap = ((mexcPrice - bitgetPrice) / bitgetPrice) * 100;

            row.innerHTML = `
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge ${Math.abs(gap) >= 0.5 ? 'bg-info' : 'bg-success'} me-2">
                            ${Math.abs(gap).toFixed(3)}%
                        </span>
                        <span>${symbol.replace('/USDT', '')}</span>
                    </div>
                </td>
                <td>${formatNumber(bitgetPrice, 4)} USDT</td>
                <td class="${gap >= 0 ? 'text-success' : 'text-danger'}">
                    ${gap >= 0 ? '+' : ''}${gap.toFixed(2)}%
                </td>
                <td>${formatNumber(bitgetPrice * USDT_PRICE_KRW, 0)} KRW</td>
                <td>
                    <span class="badge bg-success">활성</span>
                </td>
            `;

            tbody.appendChild(row);
        }

        // Also add Gate.io vs Bitget comparison if available
        if (exchanges['Gate.io Futures'] && exchanges['Bitget Futures']) {
            const row = document.createElement('tr');
            const gatePrice = exchanges['Gate.io Futures'].price;
            const bitgetPrice = exchanges['Bitget Futures'].price;
            const gap = ((gatePrice - bitgetPrice) / bitgetPrice) * 100;

            row.innerHTML = `
                <td>
                    <div class="d-flex align-items-center">
                        <span class="badge ${Math.abs(gap) >= 0.5 ? 'bg-info' : 'bg-success'} me-2">
                            ${Math.abs(gap).toFixed(3)}%
                        </span>
                        <span>${symbol.replace('/USDT', '')} (Gate)</span>
                    </div>
                </td>
                <td>${formatNumber(bitgetPrice, 4)} USDT</td>
                <td class="${gap >= 0 ? 'text-success' : 'text-danger'}">
                    ${gap >= 0 ? '+' : ''}${gap.toFixed(2)}%
                </td>
                <td>${formatNumber(bitgetPrice * USDT_PRICE_KRW, 0)} KRW</td>
                <td>
                    <span class="badge bg-success">활성</span>
                </td>
            `;

            tbody.appendChild(row);
        }
    });
}

function showError() {
    const container = document.getElementById('priceTablesContainer');
    container.innerHTML = `
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle"></i>
            가격 정보를 가져오는데 실패했습니다. 나중에 다시 시도해주세요.
        </div>
    `;
}

// 탭 전환 이벤트 처리
document.addEventListener('DOMContentLoaded', function() {
    const tabLinks = document.querySelectorAll('.nav-link');
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            tabLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Manual refresh button
    document.getElementById('refreshBtn').addEventListener('click', function() {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> 갱신 중...';
        fetchPrices().finally(() => {
            this.disabled = false;
            this.innerHTML = '<i class="fas fa-sync-alt"></i> 새로고침';
        });
    });
});

// Initial load
fetchPrices();

// Update time every second
setInterval(updateCurrentTime, 1000);

// Auto-refresh every 3 seconds
setInterval(fetchPrices, 3000);
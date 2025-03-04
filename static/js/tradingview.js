const chartConfig = {
    width: document.querySelector('.col-6').offsetWidth - 32,
    height: 400,
    layout: {
        background: { color: '#171B26' },
        textColor: '#d1d4dc',
    },
    grid: {
        vertLines: { color: '#1F2937' },
        horzLines: { color: '#1F2937' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    rightPriceScale: {
        borderColor: '#1F2937',
    },
    timeScale: {
        borderColor: '#1F2937',
    },
};

// OKX 차트 초기화
const chartOKX = LightweightCharts.createChart(document.getElementById('chartOKX'), chartConfig);
const candlestickSeriesOKX = chartOKX.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
});

// MEXC 차트 초기화
const chartMEXC = LightweightCharts.createChart(document.getElementById('chartMEXC'), chartConfig);
const candlestickSeriesMEXC = chartMEXC.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
});

async function fetchPrices() {
    try {
        const response = await fetch('/api/prices');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        updateCoinList(data);
    } catch (error) {
        console.error('Error fetching prices:', error);
    }
}

function updateCoinList(data) {
    const coinList = document.getElementById('coinList');
    coinList.innerHTML = '';

    // BTC, ETH, XRP만 필터링
    const targetCoins = ['BTC/USDT', 'ETH/USDT', 'XRP/USDT'];
    const pairs = [];

    targetCoins.forEach(symbol => {
        if (data[symbol]) {
            const exchanges = data[symbol];
            if (exchanges['OKX'] && exchanges['MEXC']) {
                const gap = ((exchanges['MEXC'].price - exchanges['OKX'].price) / exchanges['OKX'].price) * 100;
                pairs.push({
                    symbol,
                    okx: exchanges['OKX'],
                    mexc: exchanges['MEXC'],
                    gap
                });
            }
        }
    });

    // Create list items
    pairs.forEach(pair => {
        const listItem = document.createElement('a');
        listItem.href = '#';
        listItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        listItem.innerHTML = `
            <div>
                <div class="d-flex align-items-center">
                    <span class="badge ${Math.abs(pair.gap) >= 0.5 ? 'bg-info' : 'bg-success'} me-2">
                        ${Math.abs(pair.gap).toFixed(3)}%
                    </span>
                    <span>${pair.symbol}</span>
                </div>
            </div>
        `;

        listItem.addEventListener('click', (e) => {
            e.preventDefault();
            updateCharts(pair);
        });

        coinList.appendChild(listItem);
    });
}

function updateCharts(pair) {
    // 현재 시간 기준으로 샘플 데이터 생성
    const currentTime = new Date().getTime() / 1000;

    // OKX 차트 데이터
    const okxData = generateChartData(currentTime, pair.okx.price);
    candlestickSeriesOKX.setData(okxData);

    // MEXC 차트 데이터
    const mexcData = generateChartData(currentTime, pair.mexc.price);
    candlestickSeriesMEXC.setData(mexcData);

    // 차트 제목 업데이트
    document.querySelector('#chartOKX').previousElementSibling.querySelector('.card-title').textContent = 
        `OKX - ${pair.symbol} (${pair.okx.price.toFixed(2)})`;
    document.querySelector('#chartMEXC').previousElementSibling.querySelector('.card-title').textContent = 
        `MEXC - ${pair.symbol} (${pair.mexc.price.toFixed(2)})`;
}

function generateChartData(currentTime, currentPrice) {
    const data = [];
    for (let i = 0; i < 50; i++) {
        const time = currentTime - (50 - i) * 60; // 1분 간격
        const basePrice = currentPrice * (1 + (Math.random() - 0.5) * 0.001); // 가격 변동 ±0.05%
        data.push({
            time,
            open: basePrice * (1 + (Math.random() - 0.5) * 0.0002),
            high: basePrice * (1 + Math.random() * 0.0002),
            low: basePrice * (1 - Math.random() * 0.0002),
            close: basePrice * (1 + (Math.random() - 0.5) * 0.0002)
        });
    }
    return data;
}

// Initial load
fetchPrices();

// Auto-refresh every 5 seconds
setInterval(fetchPrices, 5000);

// Update current time
function updateCurrentTime() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    document.getElementById('currentTime').textContent = `현재 시간: ${timeStr}`;
}

setInterval(updateCurrentTime, 1000);
updateCurrentTime();

// Handle window resize
window.addEventListener('resize', () => {
    const width = document.querySelector('.col-6').offsetWidth - 32;
    chartOKX.applyOptions({ width });
    chartMEXC.applyOptions({ width });
});
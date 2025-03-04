const USDT_TO_KRW = 1300;
let isUpdating = false;

function formatNumber(number, decimals = 2) {
    return number.toLocaleString('ko-KR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

function formatPercentage(number) {
    return number != null ? (number >= 0 ? '+' : '') + number.toFixed(2) + '%' : '0.00%';
}

function formatPriceGap(gap) {
    if (gap === 0) return '-';
    return formatPercentage(gap);
}

function updateBalanceTable(data) {
    const tbody = document.getElementById('balanceTableBody');
    tbody.innerHTML = '';

    Object.entries(data).forEach(([exchange, balance]) => {
        const row = document.createElement('tr');
        const usdtBalance = parseFloat(balance.USDT || 0);
        const krwBalance = usdtBalance * USDT_TO_KRW;

        row.innerHTML = `
            <td>
                <div class="d-flex align-items-center">
                    <span class="badge bg-primary me-2">
                        ${exchange}
                    </span>
                </div>
            </td>
            <td>${formatNumber(usdtBalance, 2)} USDT</td>
            <td>${formatNumber(krwBalance, 0)}원</td>
            <td>${formatNumber(balance.free, 2)} USDT</td>
            <td>${formatNumber(balance.used, 2)} USDT</td>
            <td class="text-${balance.dailyPnL >= 0 ? 'success' : 'danger'}">
                ${formatPercentage(balance.dailyPnL)}
            </td>
            <td class="text-${balance.monthlyPnL >= 0 ? 'success' : 'danger'}">
                ${formatPercentage(balance.monthlyPnL)}
            </td>
        `;
        tbody.appendChild(row);
    });
}

async function fetchBalances() {
    if (isUpdating) return;
    isUpdating = true;

    try {
        const response = await fetch('/api/balance');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        updateBalanceTable(data);
    } catch (error) {
        console.error('Error fetching balances:', error);
        showError('잔액 정보를 가져오는데 실패했습니다.');
    } finally {
        isUpdating = false;
    }
}

function showError(message) {
    const tbody = document.getElementById('balanceTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-danger">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </td>
        </tr>
    `;
}

// 자동매매 시작
document.getElementById('startAutoTradingBtn').addEventListener('click', async function() {
    try {
        const response = await fetch('/api/trading/start', { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            alert('자동매매가 시작되었습니다.');
            this.disabled = true;
            document.getElementById('stopAutoTradingBtn').disabled = false;
        } else {
            alert('자동매매 시작 실패: ' + data.error);
        }
    } catch (error) {
        console.error('Error starting auto trading:', error);
        alert('자동매매 시작 중 오류가 발생했습니다.');
    }
});

// 자동매매 종료
document.getElementById('stopAutoTradingBtn').addEventListener('click', async function() {
    try {
        const response = await fetch('/api/trading/stop', { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            alert('자동매매가 종료되었습니다.');
            this.disabled = true;
            document.getElementById('startAutoTradingBtn').disabled = false;
        } else {
            alert('자동매매 종료 실패: ' + data.error);
        }
    } catch (error) {
        console.error('Error stopping auto trading:', error);
        alert('자동매매 종료 중 오류가 발생했습니다.');
    }
});

// 초기 자동매매 상태 확인
async function checkTradingStatus() {
    try {
        const response = await fetch('/api/trading/status');
        const data = await response.json();
        const isRunning = data.status === 'running';
        document.getElementById('startAutoTradingBtn').disabled = isRunning;
        document.getElementById('stopAutoTradingBtn').disabled = !isRunning;
    } catch (error) {
        console.error('Error checking trading status:', error);
    }
}

// 초기 로드
fetchBalances();
checkTradingStatus();

// 자동 새로고침 (30초마다)
setInterval(fetchBalances, 30000);

// 수동 새로고침 버튼
document.getElementById('refreshBtn').addEventListener('click', function() {
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> 갱신 중...';
    fetchBalances().finally(() => {
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-sync-alt"></i> 새로고침';
    });
});
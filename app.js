document.addEventListener('DOMContentLoaded', () => {
    fetchData();
});

async function fetchData() {
    try {
        // 브라우저 캐시 방지를 위해 타임스탬프 추가
        const response = await fetch('data.json?t=' + Date.now());
        const data = await response.json();
        renderDashboard(data);
    } catch (error) {
        console.error('Error fetching data:', error);
        document.getElementById('stock-container').innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-triangle"></i> 데이터를 불러오는데 실패했습니다.
            </div>
        `;
    }
}

function renderDashboard(data) {
    // 헤더 정보 업데이트
    document.getElementById('last-updated-text').textContent = `업데이트: ${data.last_updated}`;
    
    const sessionBadge = document.getElementById('session-badge');
    sessionBadge.textContent = data.session_name;
    sessionBadge.className = `badge ${data.session_type}`;
    
    const container = document.getElementById('stock-container');
    container.innerHTML = '';

    data.stocks.forEach(stock => {
        const card = createStockCard(stock);
        container.appendChild(card);
    });
}

function createStockCard(stock) {
    const card = document.createElement('div');
    card.className = 'stock-card';
    
    const changeClass = stock.change_rate >= 0 ? 'plus' : 'minus';
    const changeIcon = stock.change_rate >= 0 ? '▲' : '▼';
    
    // 로컬스토리지에서 체크 상태 가져오기
    const savedStates = JSON.parse(localStorage.getItem(`dip_sniper_${stock.ticker}`)) || [false, false, false, false, false];

    card.innerHTML = `
        <div class="card-header">
            <div class="ticker-info">
                <h2>${stock.ticker}</h2>
                <div class="name">${stock.name}</div>
            </div>
            <div class="price-info">
                <span class="price">$${stock.current_price}</span>
                <span class="change ${changeClass}">${changeIcon} ${Math.abs(stock.change_rate)}%</span>
            </div>
        </div>

        <div class="stage-badge ${stock.badge_color}">
            ${stock.stage_name}
        </div>

        <div class="action-guide">
            ${stock.action_guide}
        </div>

        <table class="indicators-table">
            <thead>
                <tr>
                    <th>지표</th>
                    <th>가격</th>
                    <th>평균 대비</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>20일 평균</td>
                    <td>$${stock.sma20}</td>
                    <td><span class="diff-badge ${stock.sma20_diff >= 0 ? 'plus' : 'minus'}">${stock.sma20_diff}%</span></td>
                </tr>
                <tr>
                    <td>60일 평균</td>
                    <td>$${stock.sma60}</td>
                    <td><span class="diff-badge ${stock.sma60_diff >= 0 ? 'plus' : 'minus'}">${stock.sma60_diff}%</span></td>
                </tr>
                <tr>
                    <td>120일 평균</td>
                    <td>$${stock.sma120}</td>
                    <td><span class="diff-badge ${stock.sma120_diff >= 0 ? 'plus' : 'minus'}">${stock.sma120_diff}%</span></td>
                </tr>
            </tbody>
        </table>

        <div class="rsi-container">
            <div class="rsi-label">
                <span>RSI(14)</span>
                <span style="font-weight: 700; color: ${stock.rsi < 35 ? 'var(--red)' : 'inherit'}">${stock.rsi}</span>
            </div>
            <div class="rsi-bar-bg">
                <div class="rsi-bar-fill ${stock.rsi < 35 ? 'warning' : ''}" style="width: ${stock.rsi}%"></div>
            </div>
        </div>

        <div class="purchase-tracker">
            <div class="tracker-title">
                <i class="fas fa-calendar-check"></i> 분할 매수 진행 상태
            </div>
            <div class="tracker-grid">
                ${[1, 2, 3, 4, 5].map((day, idx) => `
                    <div class="tracker-item">
                        <input type="checkbox" id="${stock.ticker}-day${day}" 
                            ${savedStates[idx] ? 'checked' : ''} 
                            onchange="saveProgress('${stock.ticker}', ${idx}, this.checked)">
                        <label for="${stock.ticker}-day${day}">${day}일차</label>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    return card;
}

function saveProgress(ticker, index, isChecked) {
    const key = `dip_sniper_${ticker}`;
    let states = JSON.parse(localStorage.getItem(key)) || [false, false, false, false, false];
    states[index] = isChecked;
    localStorage.setItem(key, JSON.stringify(states));
}

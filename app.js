document.addEventListener('DOMContentLoaded', () => {
    fetchData();
});

async function fetchData() {
    try {
        // 브라우저 캐시 방지를 위해 타임스탬프 추가
        const response = await fetch('data.json?t=' + Date.now());
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        if (!data || !data.stocks || data.stocks.length === 0) {
            throw new Error('데이터 형식이 올바르지 않거나 종목 데이터가 비어 있습니다.');
        }

        // 성공한 최신 데이터를 로컬스토리지에 안전 백업 캐시
        try {
            localStorage.setItem('dip_sniper_cached_data', JSON.stringify(data));
        } catch (e) {
            console.warn('LocalStorage cache failed:', e);
        }

        renderDashboard(data);
    } catch (error) {
        console.error('Error fetching data:', error);
        handleFetchError(error);
    }
}

function handleFetchError(error) {
    const isFileProtocol = window.location.protocol === 'file:';
    const cachedDataStr = localStorage.getItem('dip_sniper_cached_data');

    // 1. 만약 직전에 성공했던 캐시 데이터가 남아있다면 우선 화면을 띄워줌
    if (cachedDataStr) {
        try {
            const cachedData = JSON.parse(cachedDataStr);
            renderDashboard(cachedData);

            // 상단 배너에 캐시 데이터 안내 표시
            const updateInfo = document.getElementById('update-info');
            const cacheNotice = document.createElement('div');
            cacheNotice.style.cssText = 'color: #f59e0b; font-size: 0.85rem; margin-top: 4px;';
            cacheNotice.innerHTML = `<i class="fas fa-history"></i> 일시적 통신 지연으로 이전 저장된 데이터(${cachedData.last_updated})를 표시 중입니다.`;
            updateInfo.appendChild(cacheNotice);
            return;
        } catch (e) {
            console.warn('Cache parse failed:', e);
        }
    }

    // 2. 캐시도 없고 완전히 실패한 경우 안내 화면
    const guideText = isFileProtocol 
        ? `로컬 파일(file://)로 직접 열 경우 브라우저 보안 정책에 의해 데이터를 읽을 수 없습니다.<br>
           <strong>GitHub Pages 배포 주소</strong>로 접속하시거나 로컬 웹서버(http://)를 실행해 주세요.`
        : `일시적인 서버 지연 또는 장 개장 직후 데이터 갱신 중일 수 있습니다. 잠시 후 다시 시도해 주세요.`;

    document.getElementById('stock-container').innerHTML = `
        <div class="error" style="text-align: center; padding: 30px; background: rgba(239, 68, 68, 0.1); border-radius: 12px; border: 1px solid rgba(239, 68, 68, 0.2);">
            <i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #ef4444; margin-bottom: 12px;"></i>
            <h3 style="margin-bottom: 8px;">데이터를 불러오는데 실패했습니다</h3>
            <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.5; margin-bottom: 16px;">
                ${guideText}
            </p>
            <button onclick="location.reload()" style="background: #3b82f6; color: white; border: none; padding: 8px 18px; border-radius: 6px; cursor: pointer; font-weight: 600;">
                <i class="fas fa-redo"></i> 다시 시도
            </button>
        </div>
    `;
}

function renderDashboard(data) {
    // 헤더 정보 업데이트
    document.getElementById('last-updated-text').textContent = `업데이트: ${data.last_updated}`;
    
    const sessionBadge = document.getElementById('session-badge');
    sessionBadge.textContent = data.session_name || '데이터 갱신 완료';
    sessionBadge.className = `badge ${data.session_type || 'morning'}`;
    
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

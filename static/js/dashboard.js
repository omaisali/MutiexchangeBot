// Dashboard JavaScript

let config = {};

// Initialize dashboard
// Check and display demo mode
async function checkDemoMode() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const status = await response.json();
            const demoBadge = document.getElementById('demoModeBadge');
            const tradingSection = document.getElementById('tradingActivitySection');
            
            if (status.demo_mode) {
                if (demoBadge) demoBadge.style.display = 'block';
                if (tradingSection) tradingSection.style.display = 'block';
                await loadDemoData();
                // Refresh demo data every 10 seconds
                setInterval(loadDemoData, 10000);
            } else {
                if (demoBadge) demoBadge.style.display = 'none';
                if (tradingSection) tradingSection.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error checking demo mode:', error);
    }
}

// Load demo trading data
async function loadDemoData() {
    try {
        // Load demo stats
        const statsResponse = await fetch('/api/demo/stats');
        if (statsResponse.ok) {
            const statsData = await statsResponse.json();
            const stats = statsData.stats || {};
            
            const statsContainer = document.getElementById('tradingStats');
            if (statsContainer) {
                statsContainer.innerHTML = `
                    <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Total Trades</div>
                        <div style="font-size: 18px; font-weight: 600; color: var(--text-primary);">${stats.total_trades || 0}</div>
                    </div>
                    <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Total Volume</div>
                        <div style="font-size: 18px; font-weight: 600; color: var(--text-primary);">$${stats.total_volume || 0}</div>
                    </div>
                    <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Open Positions</div>
                        <div style="font-size: 18px; font-weight: 600; color: var(--text-primary);">${stats.open_positions || 0}</div>
                    </div>
                    <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; border: 1px solid var(--border);">
                        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Uptime</div>
                        <div style="font-size: 18px; font-weight: 600; color: var(--text-primary);">${Math.floor((stats.uptime_seconds || 0) / 60)}m</div>
                    </div>
                `;
            }
        }
        
        // Load demo trades
        const tradesResponse = await fetch('/api/demo/trades?limit=10');
        if (tradesResponse.ok) {
            const tradesData = await tradesResponse.json();
            const trades = tradesData.trades || [];
            
            const tradesBody = document.getElementById('demoTradesTableBody');
            if (tradesBody) {
                if (trades.length === 0) {
                    tradesBody.innerHTML = '<tr><td colspan="7" class="no-signals">No trades yet</td></tr>';
                } else {
                    tradesBody.innerHTML = trades.reverse().map(trade => {
                        const date = new Date(trade.timestamp);
                        const timeStr = date.toLocaleTimeString();
                        return `
                            <tr>
                                <td>${timeStr}</td>
                                <td>${trade.symbol}</td>
                                <td><span class="signal-badge ${trade.side.toLowerCase()}">${trade.side}</span></td>
                                <td>$${trade.price.toFixed(2)}</td>
                                <td>${trade.quantity.toFixed(6)}</td>
                                <td>$${trade.amount.toFixed(2)}</td>
                                <td><span class="status-badge executed">${trade.status}</span></td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        }
        
        // Load demo positions
        const positionsResponse = await fetch('/api/demo/positions');
        if (positionsResponse.ok) {
            const positionsData = await positionsResponse.json();
            const positions = positionsData.positions || [];
            
            const positionsBody = document.getElementById('demoPositionsTableBody');
            if (positionsBody) {
                if (positions.length === 0) {
                    positionsBody.innerHTML = '<tr><td colspan="6" class="no-signals">No open positions</td></tr>';
                } else {
                    positionsBody.innerHTML = positions.map(pos => {
                        const pnlColor = pos.unrealized_pnl >= 0 ? 'var(--success)' : 'var(--error)';
                        return `
                            <tr>
                                <td>${pos.symbol}</td>
                                <td><span class="signal-badge ${pos.side.toLowerCase()}">${pos.side}</span></td>
                                <td>$${pos.entry_price.toFixed(2)}</td>
                                <td>$${pos.current_price.toFixed(2)}</td>
                                <td>${pos.quantity.toFixed(6)}</td>
                                <td style="color: ${pnlColor}; font-weight: 600;">$${pos.unrealized_pnl.toFixed(2)}</td>
                            </tr>
                        `;
                    }).join('');
                }
            }
        }
    } catch (error) {
        console.error('Error loading demo data:', error);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    setInterval(updateStatus, 30000); // Update status every 30 seconds (includes exchange balances)
    setInterval(updateSignalStatus, 5000); // Update signal status every 5 seconds
    setInterval(updateRecentSignals, 10000); // Update recent signals every 10 seconds
    setInterval(async () => { await renderExchanges(); }, 30000); // Refresh exchange balances every 30 seconds
});

// Load dashboard data
async function loadDashboard() {
    try {
        // Load exchanges
        const exchangesResponse = await fetch('/api/exchanges');
        const exchanges = await exchangesResponse.json();
        
        // Load trading settings
        const tradingSettingsResponse = await fetch('/api/trading-settings');
        const tradingSettings = await tradingSettingsResponse.json();
        
        // Load risk management
        const riskManagementResponse = await fetch('/api/risk-management');
        const riskManagement = await riskManagementResponse.json();
        
        // Load status
        const statusResponse = await fetch('/api/status');
        const status = await statusResponse.json();
        
        config = { exchanges, tradingSettings, riskManagement, status };
        
        renderExchanges();
        renderTradingSettings();
        renderRiskManagement();
        updateStatusIndicator();
        
        // Check for demo mode
        checkDemoMode();
        
        // Load initial signal status
        updateSignalStatus();
        updateRecentSignals();
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error loading dashboard data', 'error');
    }
}

// Render exchanges
async function renderExchanges() {
    const list = document.getElementById('exchangesList');
    list.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">Loading exchanges...</div>';
    
    // Fetch exchange status (connection + balances)
    let exchangeStatus = {};
    try {
        const response = await fetch('/api/exchanges/status');
        if (response.ok) {
            exchangeStatus = await response.json();
        }
    } catch (error) {
        console.error('Error fetching exchange status:', error);
    }
    
    list.innerHTML = '';
    
    // Show all configured exchanges
    Object.entries(config.exchanges)
        .forEach(([key, exchange]) => {
        const item = document.createElement('div');
        item.className = `exchange-item ${exchange.enabled ? 'enabled' : ''}`;
        
        const status = exchangeStatus[key] || {};
        const modeText = exchange.paper_trading !== undefined 
            ? (exchange.paper_trading ? 'Paper' : 'Live') 
            : (exchange.name === 'MEXC' ? 'Live' : '');
        
        // Connection status indicator (only show if connected, hide errors)
        let connectionStatus = '';
        if (status.connected) {
            connectionStatus = '<span style="color: var(--success); font-size: 10px;">● Connected</span>';
        } else {
            // Don't show error messages, just show "Not connected" if not connected
            connectionStatus = '<span style="color: var(--text-muted); font-size: 10px;">● Not connected</span>';
        }
        
        // Format balances - show all balances, not just > 0.01
        let balanceText = '';
        if (status.connected) {
            // Exchange is connected, check if balances were fetched
            if (status.balances !== undefined && status.balances !== null) {
                // Balances were fetched (even if empty)
                if (Object.keys(status.balances).length > 0) {
                    const balanceParts = [];
                    for (const [asset, bal] of Object.entries(status.balances)) {
                        // Show balance if total > 0
                        const total = parseFloat(bal.total || 0);
                        if (total > 0) {
                            // Format with appropriate decimal places
                            let formatted;
                            if (total >= 1) {
                                formatted = total.toFixed(2);
                            } else if (total >= 0.01) {
                                formatted = total.toFixed(4);
                            } else {
                                formatted = total.toFixed(8);
                            }
                            balanceParts.push(`${asset}: ${formatted}`);
                        }
                    }
                    if (balanceParts.length > 0) {
                        balanceText = `<div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px; font-weight: 500;">💰 ${balanceParts.join(' • ')}</div>`;
                    } else {
                        // Connected but all balances are zero
                        balanceText = `<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">💰 All balances: 0.00</div>`;
                    }
                } else {
                    // Connected but balances object is empty (no assets with balance)
                    balanceText = `<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">💰 All balances: 0.00</div>`;
                }
            } else {
                // Connected but balances not fetched yet
                balanceText = `<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Loading balances...</div>`;
            }
        }
        // If not connected, don't show balance text
        
        item.innerHTML = `
            <div class="exchange-item-left">
                <div>
                    <div class="exchange-name">${exchange.name}</div>
                    <div class="exchange-status">
                        ${exchange.enabled ? 'Enabled' : 'Disabled'} ${modeText ? '• ' + modeText : ''}
                        ${connectionStatus ? ' • ' + connectionStatus : ''}
                    </div>
                    ${balanceText}
                </div>
            </div>
            <div class="exchange-item-right">
                <label class="exchange-toggle">
                    <input type="checkbox" ${exchange.enabled ? 'checked' : ''} 
                           onchange="toggleExchange('${key}', this.checked)">
                    <span class="exchange-toggle-slider"></span>
                </label>
                <button class="btn btn-sm" onclick="openExchangeModal('${key}')" title="Configure">
                    <i class="fas fa-cog"></i>
                </button>
            </div>
        `;
        list.appendChild(item);
    });
}

// Render trading settings
function renderTradingSettings() {
    const settings = config.tradingSettings;
    const positionSize = settings.position_size_percent || 20;
    document.getElementById('positionSizePercent').value = positionSize;
    document.getElementById('positionSizeValue').textContent = positionSize;
    document.getElementById('positionSizeFixed').value = settings.position_size_fixed || '';
    document.getElementById('usePercentage').checked = settings.use_percentage !== false;
    document.getElementById('warnExistingPositions').checked = settings.warn_existing_positions !== false;
}

// Render risk management
function renderRiskManagement() {
    const risk = config.riskManagement;
    document.getElementById('stopLossPercent').value = risk.stop_loss_percent || 5.0;
    // TP levels are fixed according to requirements - shown as readonly
    document.getElementById('takeProfit1').value = 1.0;
    document.getElementById('takeProfit2').value = 2.0;
    document.getElementById('takeProfit3').value = 5.0;
    document.getElementById('takeProfit4').value = 6.5;
    document.getElementById('takeProfit5').value = 8.0;
}

// Update status indicator
function updateStatusIndicator() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    
    const enabledExchanges = Object.values(config.exchanges).filter(e => e.enabled).length;
    
    if (enabledExchanges > 0) {
        statusDot.className = 'status-dot active';
        statusText.textContent = `${enabledExchanges} Exchange(s) Active`;
    } else {
        statusDot.className = 'status-dot inactive';
        statusText.textContent = 'No Exchanges Active';
    }
}

// Toggle exchange
async function toggleExchange(exchangeName, enabled) {
    try {
        const response = await fetch(`/api/exchanges/${exchangeName}/toggle`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            config.exchanges[exchangeName].enabled = enabled;
            renderExchanges();
            updateStatusIndicator();
            showToast(result.message, 'success');
        } else {
            showToast(result.error || 'Failed to toggle exchange', 'error');
        }
    } catch (error) {
        console.error('Error toggling exchange:', error);
        showToast('Error toggling exchange', 'error');
    }
}

// Open exchange modal
async function openExchangeModal(exchangeName) {
    const exchange = config.exchanges[exchangeName];
    const modal = document.getElementById('exchangeModal');
    
    document.getElementById('exchangeName').value = exchangeName;
    document.getElementById('modalTitle').textContent = `Configure ${exchange.name}`;
    document.getElementById('exchangeEnabled').checked = exchange.enabled || false;
    // Set API key (show actual value if saved)
    const apiKeyField = document.getElementById('exchangeApiKey');
    apiKeyField.value = exchange.api_key || '';
    console.log(`Loading exchange ${exchangeName}: API Key length = ${(exchange.api_key || '').length}`);
    
    // Set API secret (show '***' if secret exists, empty if not)
    const apiSecretField = document.getElementById('exchangeApiSecret');
    apiSecretField.value = (exchange.api_secret && exchange.api_secret !== '') ? '***' : '';
    // Store original secret status for later comparison
    apiSecretField.dataset.hasSecret = (exchange.api_secret && exchange.api_secret !== '') ? 'true' : 'false';
    console.log(`Loading exchange ${exchangeName}: API Secret present = ${apiSecretField.dataset.hasSecret}`);
    document.getElementById('exchangeBaseUrl').value = exchange.base_url || '';
    
    // Show paper trading option for Alpaca
    const paperTradingGroup = document.getElementById('paperTradingGroup');
    if (exchange.paper_trading !== undefined) {
        paperTradingGroup.style.display = 'block';
        document.getElementById('exchangePaperTrading').checked = exchange.paper_trading || false;
    } else {
        paperTradingGroup.style.display = 'none';
    }
    
    // Show sub-account option for MEXC
    const subAccountGroup = document.getElementById('subAccountGroup');
    const subAccountIdInput = document.getElementById('exchangeSubAccountId');
    const mexcWarning = document.getElementById('mexcWarning');
    
    if (exchangeName === 'mexc') {
        subAccountGroup.style.display = 'block';
        const useSubAccountCheckbox = document.getElementById('exchangeUseSubAccount');
        useSubAccountCheckbox.checked = exchange.use_sub_account || false;
        subAccountIdInput.value = exchange.sub_account_id || '';
        
        // Show sub-account ID input when checkbox is checked
        const toggleSubAccountInput = function() {
            subAccountIdInput.style.display = useSubAccountCheckbox.checked ? 'block' : 'none';
        };
        useSubAccountCheckbox.addEventListener('change', toggleSubAccountInput);
        toggleSubAccountInput(); // Set initial state
        
        // Show MEXC real trading warning
        mexcWarning.style.display = 'block';
    } else {
        subAccountGroup.style.display = 'none';
        mexcWarning.style.display = 'none';
    }
    
    modal.classList.add('show');
}

// Close modal
function closeModal() {
    document.getElementById('exchangeModal').classList.remove('show');
}

// Save exchange
async function saveExchange() {
    const exchangeName = document.getElementById('exchangeName').value;
    const exchange = config.exchanges[exchangeName];
    
    const data = {
        enabled: document.getElementById('exchangeEnabled').checked,
        api_key: document.getElementById('exchangeApiKey').value.trim(),
        api_secret: document.getElementById('exchangeApiSecret').value.trim(),
        base_url: document.getElementById('exchangeBaseUrl').value
    };
    
    // Only include paper_trading if it exists for this exchange
    if (exchange.paper_trading !== undefined) {
        data.paper_trading = document.getElementById('exchangePaperTrading').checked;
    }
    
    // Include sub-account settings for MEXC
    if (exchangeName === 'mexc') {
        data.use_sub_account = document.getElementById('exchangeUseSubAccount').checked;
        data.sub_account_id = document.getElementById('exchangeSubAccountId').value;
    }
    
    // Don't send masked secret
    // Don't send '***' as the secret - it means "keep existing secret"
    const secretField = document.getElementById('exchangeApiSecret');
    if (data.api_secret === '***' || (data.api_secret === '' && secretField.dataset.hasSecret === 'true')) {
        // If field shows '***' or is empty but we had a secret, don't update it
        delete data.api_secret;
        console.log('Keeping existing API secret (not updating)');
    } else if (data.api_secret === '') {
        // If field is empty and we didn't have a secret, send empty to clear it
        console.log('Clearing API secret');
    } else {
        // New secret provided
        console.log('Updating API secret (new value provided)');
    }
    
    try {
        const response = await fetch(`/api/exchanges/${exchangeName}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('Exchange configuration saved successfully', 'success');
            closeModal();
            loadDashboard();
        } else {
            showToast(result.error || 'Failed to save exchange', 'error');
        }
    } catch (error) {
        console.error('Error saving exchange:', error);
        showToast('Error saving exchange', 'error');
    }
}

// Test connection
async function testConnection() {
    const exchangeName = document.getElementById('exchangeName').value;
    
    showToast('Testing connection...', 'success');
    
    try {
        const response = await fetch(`/api/test-connection/${exchangeName}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('Connection successful!', 'success');
        } else {
            showToast(result.error || result.message || 'Connection failed', 'error');
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        showToast('Error testing connection', 'error');
    }
}

// Save trading settings
async function saveTradingSettings() {
    const data = {
        position_size_percent: document.getElementById('positionSizePercent').value,
        position_size_fixed: document.getElementById('positionSizeFixed').value,
        use_percentage: document.getElementById('usePercentage').checked,
        warn_existing_positions: document.getElementById('warnExistingPositions').checked
    };
    
    try {
        const response = await fetch('/api/trading-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('Trading settings saved successfully', 'success');
            loadDashboard();
        } else {
            showToast(result.error || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving trading settings:', error);
        showToast('Error saving trading settings', 'error');
    }
}

// Save risk management
async function saveRiskManagement() {
    const data = {
        stop_loss_percent: document.getElementById('stopLossPercent').value
        // TP levels are fixed - not configurable
    };
    
    try {
        const response = await fetch('/api/risk-management', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('Risk management settings saved successfully', 'success');
            loadDashboard();
        } else {
            showToast(result.error || 'Failed to save settings', 'error');
        }
    } catch (error) {
        console.error('Error saving risk management:', error);
        showToast('Error saving risk management', 'error');
    }
}

// Update status
async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        config.status = status;
        updateStatusIndicator();
    } catch (error) {
        console.error('Error updating status:', error);
    }
}

// Update signal status
async function updateSignalStatus() {
    try {
        // Ping health endpoint to mark webhook as active (this helps show connection status)
        try {
            await fetch('/health');
        } catch (e) {
            // Ignore health check errors, webhook might still be working
        }
        
        const response = await fetch('/api/signals/status');
        const status = await response.json();
        
        // Update webhook connection status
        const connectionDot = document.querySelector('#webhookConnectionIndicator .connection-dot');
        const statusText = document.getElementById('webhookStatusText');
        const webhookStatus = document.getElementById('webhookStatus');
        const lastSignalTime = document.getElementById('lastSignalTime');
        const timeSinceLast = document.getElementById('timeSinceLast');
        const totalSignals = document.getElementById('totalSignals');
        const successfulTrades = document.getElementById('successfulTrades');
        const failedTrades = document.getElementById('failedTrades');
        
        if (status.webhook_status === 'connected') {
            connectionDot.className = 'connection-dot connected';
            statusText.textContent = 'Connected';
            webhookStatus.textContent = 'Connected';
            webhookStatus.className = 'status-value success';
        } else {
            // Show "Waiting for signals" if no signals received yet (webhook is ready, just waiting)
            connectionDot.className = 'connection-dot disconnected';
            if (status.total_signals === 0) {
                statusText.textContent = 'Waiting for signals';
                webhookStatus.textContent = 'Waiting for signals';
                webhookStatus.className = 'status-value';
            } else {
                statusText.textContent = 'Disconnected';
                webhookStatus.textContent = 'Disconnected';
                webhookStatus.className = 'status-value error';
            }
        }
        
        // Update last signal time
        if (status.last_signal_datetime) {
            const date = new Date(status.last_signal_datetime);
            lastSignalTime.textContent = date.toLocaleString();
            
            if (status.time_since_last_signal) {
                const seconds = Math.floor(status.time_since_last_signal);
                const minutes = Math.floor(seconds / 60);
                const hours = Math.floor(minutes / 60);
                
                if (hours > 0) {
                    timeSinceLast.textContent = `${hours}h ${minutes % 60}m ago`;
                } else if (minutes > 0) {
                    timeSinceLast.textContent = `${minutes}m ${seconds % 60}s ago`;
                } else {
                    timeSinceLast.textContent = `${seconds}s ago`;
                }
            }
        } else {
            lastSignalTime.textContent = 'Never';
            timeSinceLast.textContent = '-';
        }
        
        // Update statistics
        totalSignals.textContent = status.total_signals || 0;
        successfulTrades.textContent = status.successful_trades || 0;
        failedTrades.textContent = status.failed_trades || 0;
        
    } catch (error) {
        console.error('Error updating signal status:', error);
        // Mark as disconnected on error
        const connectionDot = document.querySelector('#webhookConnectionIndicator .connection-dot');
        const statusText = document.getElementById('webhookStatusText');
        if (connectionDot) {
            connectionDot.className = 'connection-dot disconnected';
            statusText.textContent = 'Disconnected';
        }
    }
}

// Update recent signals (from last 24 hours)
async function updateRecentSignals() {
    try {
        // Get signals from last 24 hours, limit to 100 for display
        const response = await fetch('/api/signals/recent?limit=100&hours=24');
        const data = await response.json();
        const signals = data.signals || [];
        
        const tbody = document.getElementById('signalsTableBody');
        
        if (signals.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-signals">No signals received yet</td></tr>';
            return;
        }
        
        tbody.innerHTML = signals.reverse().map(signal => {
            const date = new Date(signal.datetime);
            const signalType = signal.signal.toLowerCase();
            const statusClass = signal.executed ? 'executed' : (signal.error ? 'failed' : 'pending');
            const statusText = signal.executed ? 'Executed' : (signal.error ? 'Failed' : 'Pending');
            
            return `
                <tr>
                    <td>${date.toLocaleString()}</td>
                    <td>${signal.symbol || '-'}</td>
                    <td><span class="signal-badge ${signalType}">${signal.signal}</span></td>
                    <td>${signal.price ? signal.price.toFixed(2) : '-'}</td>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                </tr>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error updating recent signals:', error);
    }
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Close modal on outside click
window.onclick = function(event) {
    const modal = document.getElementById('exchangeModal');
    if (event.target === modal) {
        closeModal();
    }
}


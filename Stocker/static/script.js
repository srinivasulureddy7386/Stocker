// Global variables
let stockPrices = {};
let previousPrices = {};

// Password visibility toggle
function togglePassword(inputId) {
    const passwordInput = document.getElementById(inputId);
    const toggleButton = passwordInput.nextElementSibling;
    
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleButton.textContent = '🙈';
    } else {
        passwordInput.type = 'password';
        toggleButton.textContent = '👁️';
    }
}

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatPercentage(value) {
    return (value >= 0 ? '+' : '') + value.toFixed(2) + '%';
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    
    const container = document.querySelector('.dashboard-main') || document.querySelector('.main-content');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
    }
}

// Home page content switching
function showContent(contentId) {
    // Hide all content sections
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => section.classList.remove('active'));
    
    // Show selected content
    const targetSection = document.getElementById(contentId);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // Update nav menu active states
    const navItems = document.querySelectorAll('.nav-menu button');
    navItems.forEach(item => item.classList.remove('active'));
    
    const activeNavItem = document.querySelector(`button[onclick="showContent('${contentId}')"]`);
    if (activeNavItem) {
        activeNavItem.classList.add('active');
    }
}

// Username availability check
function checkUsernameAvailability() {
    const usernameInput = document.getElementById('username');
    const statusDiv = document.getElementById('username-status');
    
    if (!usernameInput || !statusDiv) return;
    
    const username = usernameInput.value.trim();
    
    if (username.length < 3) {
        statusDiv.textContent = '';
        return;
    }
    
    fetch(`/check_username?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            if (data.exists) {
                statusDiv.textContent = '❌ Username already taken';
                statusDiv.className = 'username-status username-taken';
            } else {
                statusDiv.textContent = '✅ Username available';
                statusDiv.className = 'username-status username-available';
            }
        })
        .catch(error => {
            console.error('Error checking username:', error);
            statusDiv.textContent = '';
        });
}

// Stock price updates
async function updateStockPrices() {
    try {
        const response = await fetch('/api/stock_prices');
        const newPrices = await response.json();
        
        // Store previous prices for change calculation
        previousPrices = { ...stockPrices };
        stockPrices = newPrices;
        
        console.log('Stock prices updated:', stockPrices);
        
        // Update stock cards
        Object.entries(newPrices).forEach(([symbol, price]) => {
            const priceElement = document.getElementById(`price-${symbol}`);
            const changeElement = document.getElementById(`change-${symbol}`);
            
            if (priceElement) {
                priceElement.textContent = formatCurrency(price);
                
                // Add price change animation
                priceElement.classList.add('price-updated');
                setTimeout(() => priceElement.classList.remove('price-updated'), 500);
            }
            
            if (changeElement && previousPrices[symbol]) {
                const change = ((price - previousPrices[symbol]) / previousPrices[symbol]) * 100;
                changeElement.textContent = formatPercentage(change);
                changeElement.className = `stock-change ${change >= 0 ? 'profit' : 'loss'}`;
            }
        });
        
        // Update portfolio values
        updatePortfolioValues();
        
        return stockPrices;
        
    } catch (error) {
        console.error('Error updating stock prices:', error);
        return {};
    }
}

// Portfolio value updates
function updatePortfolioValues() {
    // Update portfolio table
    const portfolioRows = document.querySelectorAll('tbody tr');
    portfolioRows.forEach(row => {
        const symbolElement = row.querySelector('.stock-symbol');
        if (!symbolElement) return;
        
        const symbol = symbolElement.textContent.trim();
        if (stockPrices[symbol]) {
            const currentPrice = stockPrices[symbol];
            
            // Update current price displays
            const currentPriceElement = row.querySelector('.current-price');
            if (currentPriceElement) {
                currentPriceElement.textContent = formatCurrency(currentPrice);
            }
            
            // Update all current price elements with this symbol
            const allCurrentPriceElements = document.querySelectorAll(`[id*="current-${symbol}"]`);
            allCurrentPriceElements.forEach(el => {
                el.textContent = formatCurrency(currentPrice);
            });
            
            // Update total value
            const quantityElement = row.querySelector('.quantity');
            if (quantityElement) {
                const quantity = parseInt(quantityElement.textContent);
                const totalValue = quantity * currentPrice;
                
                const totalValueElement = row.querySelector('.total-value');
                if (totalValueElement) {
                    totalValueElement.textContent = formatCurrency(Math.abs(totalValue));
                }
                
                // Update all total value elements with this symbol
                const allTotalValueElements = document.querySelectorAll(`[id*="total-${symbol}"]`);
                allTotalValueElements.forEach(el => {
                    el.textContent = formatCurrency(totalValue);
                });
            }
            
            // Update P&L
            const avgPriceElement = row.querySelector('.avg-price');
            if (avgPriceElement && quantityElement) {
                const avgPrice = parseFloat(avgPriceElement.textContent.replace('$', ''));
                const quantity = parseInt(quantityElement.textContent);
                const pnlAmount = (currentPrice - avgPrice) * quantity;
                const pnlPercent = ((currentPrice - avgPrice) / avgPrice) * 100;
                
                const pnlAmountElement = row.querySelector('.pnl-amount');
                if (pnlAmountElement) {
                    pnlAmountElement.textContent = (pnlAmount >= 0 ? '+' : '') + formatCurrency(Math.abs(pnlAmount));
                    pnlAmountElement.className = pnlAmountElement.className.replace(/profit|loss/g, '') + (pnlAmount >= 0 ? ' profit' : ' loss');
                }
                
                // Update all P&L elements with this symbol
                const allPnlAmountElements = document.querySelectorAll(`[id*="pnl-${symbol}"]`);
                allPnlAmountElements.forEach(el => {
                    el.textContent = (pnlAmount >= 0 ? '+' : '') + formatCurrency(Math.abs(pnlAmount));
                    el.className = el.className.replace(/profit|loss/g, '') + (pnlAmount >= 0 ? ' profit' : ' loss');
                });
                
                const pnlPercentElement = row.querySelector('.pnl-percent');
                if (pnlPercentElement) {
                    pnlPercentElement.textContent = formatPercentage(pnlPercent);
                    pnlPercentElement.className = pnlPercentElement.className.replace(/profit|loss/g, '') + (pnlPercent >= 0 ? ' profit' : ' loss');
                }
                
                const pnlPercentElements = document.querySelectorAll(`.pnl-percent`);
                pnlPercentElements.forEach(el => {
                    if (el.closest('tr') === row) {
                        el.textContent = formatPercentage(pnlPercent);
                        el.className = el.className.replace(/profit|loss/g, '') + (pnlPercent >= 0 ? ' profit' : ' loss');
                    }
                });
            }
        }
    });
    
    // Update total portfolio stats
    updateTotalPortfolioStats();
}

// Update total portfolio statistics
function updateTotalPortfolioStats() {
    const totalValueElement = document.getElementById('totalValue');
    const totalPnLElement = document.getElementById('totalPnL');
    
    if (!totalValueElement || !totalPnLElement) return;
    
    let totalValue = 0;
    let totalPnL = 0;
    
    const portfolioRows = document.querySelectorAll('tbody tr');
    portfolioRows.forEach(row => {
        const totalValueCell = row.querySelector('.total-value');
        const pnlAmountCell = row.querySelector('.pnl-amount');
        
        if (totalValueCell) {
            const value = parseFloat(totalValueCell.textContent.replace(/[$,]/g, ''));
            if (!isNaN(value)) totalValue += value;
        }
        
        if (pnlAmountCell) {
            const pnl = parseFloat(pnlAmountCell.textContent.replace(/[$,+]/g, ''));
            if (!isNaN(pnl)) totalPnL += pnl;
        }
    });
    
    totalValueElement.textContent = formatCurrency(totalValue);
    totalPnLElement.textContent = (totalPnL >= 0 ? '+' : '') + formatCurrency(Math.abs(totalPnL));
    totalPnLElement.className = 'stat-value ' + (totalPnL >= 0 ? 'profit' : 'loss');
}

// Market data updates for trade page
function updateMarketData() {
    Object.entries(stockPrices).forEach(([symbol, price]) => {
        const marketPriceElement = document.getElementById(`market-${symbol}`);
        const marketChangeElement = document.getElementById(`market-change-${symbol}`);
        
        if (marketPriceElement) {
            marketPriceElement.textContent = formatCurrency(price);
        }
        
        if (marketChangeElement && previousPrices[symbol]) {
            const change = ((price - previousPrices[symbol]) / previousPrices[symbol]) * 100;
            marketChangeElement.textContent = formatPercentage(change);
            marketChangeElement.className = `market-change ${change >= 0 ? 'profit' : 'loss'}`;
        }
    });
}

// Trade form initialization
function initializeTradeForm() {
    const stockSelect = document.getElementById('stock_symbol');
    const quantityInput = document.getElementById('quantity');
    const currentPriceElement = document.getElementById('currentPrice');
    const totalCostElement = document.getElementById('totalCost');
    const tradeTypeInputs = document.querySelectorAll('input[name="trade_type"]');
    const tradeForm = document.getElementById('tradeForm');
    
    if (!stockSelect || !quantityInput || !tradeForm) return;
    
    // Initialize stock prices if not already loaded
    if (Object.keys(stockPrices).length === 0) {
        updateStockPrices().then(() => {
            updateTradePreview();
        });
    }
    
    function updateTradePreview() {
        const selectedStock = stockSelect.value;
        const quantity = parseInt(quantityInput.value) || 0;
        const selectedTradeType = document.querySelector('input[name="trade_type"]:checked');
        
        console.log('Updating trade preview:', { selectedStock, quantity, selectedTradeType: selectedTradeType?.value, stockPrices });
        
        if (selectedStock && stockPrices[selectedStock] && quantity > 0 && selectedTradeType) {
            const price = stockPrices[selectedStock];
            const total = price * quantity;
            
            console.log('Price calculation:', { price, total });
            
            if (currentPriceElement) {
                currentPriceElement.textContent = formatCurrency(price);
            }
            
            if (totalCostElement) {
                const tradeType = selectedTradeType.value;
                totalCostElement.textContent = formatCurrency(total);
                
                // Update label based on trade type
                const totalLabel = document.getElementById('totalLabel');
                if (totalLabel) {
                    totalLabel.textContent = tradeType === 'BUY' ? 'Total Cost:' : 'Total Revenue:';
                }
            }
        } else if (selectedStock && stockPrices[selectedStock] && quantity > 0) {
            // Show price even without trade type selected
            const price = stockPrices[selectedStock];
            const total = price * quantity;
            
            if (currentPriceElement) {
                currentPriceElement.textContent = formatCurrency(price);
            }
            
            if (totalCostElement) {
                totalCostElement.textContent = formatCurrency(total);
            }
        } else {
            if (currentPriceElement) {
                currentPriceElement.textContent = '--';
            }
            
            if (totalCostElement) {
                totalCostElement.textContent = '--';
            }
        }
    }
    
    stockSelect.addEventListener('change', updateTradePreview);
    quantityInput.addEventListener('input', updateTradePreview);
    
    tradeTypeInputs.forEach(input => {
        input.addEventListener('change', updateTradePreview);
    });
    
    // Initial update
    setTimeout(updateTradePreview, 500);
    
    // Handle form submission
    tradeForm.addEventListener('submit', function(e) {
        const selectedStock = stockSelect.value;
        const quantity = parseInt(quantityInput.value) || 0;
        const selectedTradeType = document.querySelector('input[name="trade_type"]:checked');
        
        if (!selectedStock || quantity <= 0 || !selectedTradeType) {
            e.preventDefault();
            showAlert('Please fill in all required fields', 'error');
            return false;
        }
        
        // Show loading state
        const submitButton = e.target.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.textContent = 'Processing...';
            submitButton.disabled = true;
        }
    });
}

// Quick trade form on dashboard
function initializeQuickTrade() {
    const stockSelect = document.getElementById('stock_symbol');
    const quantityInput = document.getElementById('quantity');
    const pricePreview = document.getElementById('pricePreview');
    
    if (!stockSelect || !quantityInput || !pricePreview) return;
    
    function updateQuickTradePreview() {
        const selectedStock = stockSelect.value;
        const quantity = parseInt(quantityInput.value) || 0;
        
        if (selectedStock && stockPrices[selectedStock] && quantity > 0) {
            const price = stockPrices[selectedStock];
            const total = price * quantity;
            
            pricePreview.innerHTML = `
                <div>Current Price: ${formatCurrency(price)}</div>
                <div>Total Cost: ${formatCurrency(total)}</div>
            `;
        } else {
            pricePreview.innerHTML = '';
        }
    }
    
    stockSelect.addEventListener('change', updateQuickTradePreview);
    quantityInput.addEventListener('input', updateQuickTradePreview);
}

// Stock selection from market grid
function selectStock(symbol) {
    const stockSelect = document.getElementById('stock_symbol');
    if (stockSelect) {
        stockSelect.value = symbol;
        
        // Trigger change event to update preview
        const event = new Event('change', { bubbles: true });
        stockSelect.dispatchEvent(event);
        
        // Scroll to form
        const tradeForm = document.querySelector('.trade-form');
        if (tradeForm) {
            tradeForm.scrollIntoView({ behavior: 'smooth' });
        }
    }
}

// History filters
function initializeHistoryFilters() {
    const typeFilter = document.getElementById('typeFilter');
    const stockFilter = document.getElementById('stockFilter');
    const historyTable = document.getElementById('historyTable');
    
    if (!typeFilter || !stockFilter || !historyTable) return;
    
    function filterHistory() {
        const selectedType = typeFilter.value;
        const selectedStock = stockFilter.value;
        const rows = historyTable.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const rowType = row.dataset.type;
            const rowStock = row.dataset.stock;
            
            const typeMatch = !selectedType || rowType === selectedType;
            const stockMatch = !selectedStock || rowStock === selectedStock;
            
            row.style.display = (typeMatch && stockMatch) ? '' : 'none';
        });
    }
    
    typeFilter.addEventListener('change', filterHistory);
    stockFilter.addEventListener('change', filterHistory);
}

// FAQ toggle functionality
function toggleFaq(questionElement) {
    const answer = questionElement.nextElementSibling;
    const icon = questionElement.querySelector('.faq-icon');
    
    if (answer.classList.contains('show')) {
        answer.classList.remove('show');
        questionElement.classList.remove('active');
    } else {
        // Close all other FAQ items
        document.querySelectorAll('.faq-answer.show').forEach(openAnswer => {
            openAnswer.classList.remove('show');
            openAnswer.previousElementSibling.classList.remove('active');
        });
        
        // Open clicked FAQ item
        answer.classList.add('show');
        questionElement.classList.add('active');
    }
}

// Admin portfolio page
function initializeAdminPortfolio() {
    const searchInput = document.getElementById('searchPortfolio');
    const stockFilter = document.getElementById('stockFilter');
    const portfolioTable = document.getElementById('portfolioTable');
    
    if (!searchInput || !portfolioTable) return;
    
    function filterPortfolios() {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedStock = stockFilter ? stockFilter.value : '';
        const rows = portfolioTable.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const username = row.querySelector('.username')?.textContent.toLowerCase() || '';
            const stockSymbol = row.querySelector('.stock-symbol')?.textContent || '';
            
            const searchMatch = username.includes(searchTerm) || stockSymbol.toLowerCase().includes(searchTerm);
            const stockMatch = !selectedStock || stockSymbol === selectedStock;
            
            row.style.display = (searchMatch && stockMatch) ? '' : 'none';
        });
    }
    
    searchInput.addEventListener('input', filterPortfolios);
    if (stockFilter) {
        stockFilter.addEventListener('change', filterPortfolios);
    }
}

// Admin history page
function initializeAdminHistory() {
    const searchInput = document.getElementById('searchTrades');
    const typeFilter = document.getElementById('tradeTypeFilter');
    const stockFilter = document.getElementById('stockFilter');
    const tradesTable = document.getElementById('tradesTable');
    
    if (!searchInput || !tradesTable) return;
    
    function filterTrades() {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedType = typeFilter ? typeFilter.value : '';
        const selectedStock = stockFilter ? stockFilter.value : '';
        const rows = tradesTable.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const username = row.dataset.user?.toLowerCase() || '';
            const stockSymbol = row.dataset.stock || '';
            const tradeType = row.dataset.type || '';
            
            const searchMatch = username.includes(searchTerm) || stockSymbol.toLowerCase().includes(searchTerm);
            const typeMatch = !selectedType || tradeType === selectedType;
            const stockMatch = !selectedStock || stockSymbol === selectedStock;
            
            row.style.display = (searchMatch && typeMatch && stockMatch) ? '' : 'none';
        });
    }
    
    searchInput.addEventListener('input', filterTrades);
    if (typeFilter) {
        typeFilter.addEventListener('change', filterTrades);
    }
    if (stockFilter) {
        stockFilter.addEventListener('change', filterTrades);
    }
}

// Admin manage page
function initializeAdminManage() {
    const searchInput = document.getElementById('searchTraders');
    const tradersTable = document.getElementById('tradersTable');
    
    if (!searchInput || !tradersTable) return;
    
    function filterTraders() {
        const searchTerm = searchInput.value.toLowerCase();
        const rows = tradersTable.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const username = row.dataset.username?.toLowerCase() || '';
            const email = row.dataset.email?.toLowerCase() || '';
            
            const searchMatch = username.includes(searchTerm) || email.includes(searchTerm);
            
            row.style.display = searchMatch ? '' : 'none';
        });
    }
    
    searchInput.addEventListener('input', filterTraders);
}

// Trader details modal
function viewTraderDetails(username) {
    const modal = document.getElementById('traderModal');
    const modalBody = document.getElementById('traderDetails');
    
    if (!modal || !modalBody) return;
    
    // Mock trader details - in real app, fetch from server
    modalBody.innerHTML = `
        <div class="trader-details">
            <h4>Trader: ${username}</h4>
            <div class="detail-grid">
                <div class="detail-item">
                    <strong>Status:</strong> Active
                </div>
                <div class="detail-item">
                    <strong>Last Login:</strong> 2 hours ago
                </div>
                <div class="detail-item">
                    <strong>Total Trades:</strong> 45
                </div>
                <div class="detail-item">
                    <strong>Success Rate:</strong> 78%
                </div>
            </div>
        </div>
    `;
    
    modal.style.display = 'block';
}

function closeTraderModal() {
    const modal = document.getElementById('traderModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function contactTrader(email) {
    // Mock contact functionality
    showAlert(`Contact request sent to ${email}`, 'success');
}

// Admin trade functionality
function adminTrade(userId, stockSymbol, tradeType) {
    const quantity = prompt(`Enter quantity to ${tradeType.toLowerCase()} for ${stockSymbol}:`);
    
    if (quantity && !isNaN(quantity) && parseInt(quantity) > 0) {
        // In a real application, this would make an API call to execute the trade
        showAlert(`${tradeType} order for ${quantity} shares of ${stockSymbol} has been queued for ${userId}`, 'success');
        
        // Simulate trade execution
        setTimeout(() => {
            showAlert(`${tradeType} order executed successfully`, 'success');
            // Refresh the page to show updated data
            location.reload();
        }, 2000);
    } else if (quantity !== null) {
        showAlert('Please enter a valid quantity', 'error');
    }
}

// Form validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('error');
            isValid = false;
        } else {
            field.classList.remove('error');
        }
    });
    
    return isValid;
}

// Initialize page-specific functionality
document.addEventListener('DOMContentLoaded', function() {
    // Prevent multiple page loads
    if (window.stockerInitialized) {
        return;
    }
    window.stockerInitialized = true;
    
    // Load initial stock prices
    updateStockPrices();
    
    // Username availability check
    const usernameInput = document.getElementById('username');
    if (usernameInput) {
        usernameInput.addEventListener('input', checkUsernameAvailability);
    }
    
    // Initialize trade form
    if (document.getElementById('tradeForm')) {
        // Wait for stock prices to load before initializing trade form
        setTimeout(() => {
            initializeTradeForm();
        }, 1000);
    }
    
    // Initialize quick trade
    if (document.getElementById('stock_symbol') && document.getElementById('pricePreview')) {
        initializeQuickTrade();
    }
    
    // Initialize history filters
    if (document.getElementById('typeFilter')) {
        initializeHistoryFilters();
    }
    
    // Modal close functionality
    window.addEventListener('click', function(event) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // Form validation on submit
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(form)) {
                event.preventDefault();
                showAlert('Please fill in all required fields', 'error');
            }
        });
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Auto-hide alerts
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }, 5000);
});

// Export functions for global use
window.showContent = showContent;
window.updateStockPrices = updateStockPrices;
window.updatePortfolioValues = updatePortfolioValues;
window.updateMarketData = updateMarketData;
window.selectStock = selectStock;
window.toggleFaq = toggleFaq;
window.viewTraderDetails = viewTraderDetails;
window.closeTraderModal = closeTraderModal;
window.contactTrader = contactTrader;
window.initializeTradeForm = initializeTradeForm;
window.initializeAdminPortfolio = initializeAdminPortfolio;
window.initializeAdminHistory = initializeAdminHistory;
window.initializeAdminManage = initializeAdminManage;
window.initializeHistoryFilters = initializeHistoryFilters;
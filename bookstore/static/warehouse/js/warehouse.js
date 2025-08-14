// warehouse/static/warehouse/js/warehouse.js
// JavaScript functionality for warehouse system

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh dashboard every 30 seconds
    if (window.location.pathname.includes('/warehouse/')) {
        setInterval(function() {
            // Only refresh if user is still active
            if (document.visibilityState === 'visible') {
                // You can implement AJAX refresh here
                console.log('Auto-refresh triggered');
            }
        }, 30000);
    }
    
    // Stock level indicators
    updateStockLevelBars();
    
    // Form validation
    setupFormValidation();
    
    // Quick actions
    setupQuickActions();
});

function updateStockLevelBars() {
    const indicators = document.querySelectorAll('.stock-level-indicator');
    
    indicators.forEach(indicator => {
        const current = parseInt(indicator.dataset.current);
        const max = parseInt(indicator.dataset.max);
        const reorder = parseInt(indicator.dataset.reorder);
        
        const percentage = Math.min((current / max) * 100, 100);
        const bar = indicator.querySelector('.stock-level-bar');
        
        if (bar) {
            bar.style.width = percentage + '%';
            
            // Set color based on stock level
            if (current <= 0) {
                bar.className = 'stock-level-bar stock-level-critical';
            } else if (current <= reorder) {
                bar.className = 'stock-level-bar stock-level-low';
            } else {
                bar.className = 'stock-level-bar stock-level-good';
            }
        }
    });
}

function setupFormValidation() {
    // Add stock form validation
    const addStockForms = document.querySelectorAll('form[action*="add_stock"]');
    addStockForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const quantity = form.querySelector('input[name="quantity"]');
            if (quantity && parseInt(quantity.value) <= 0) {
                e.preventDefault();
                alert('Quantity must be greater than 0');
                quantity.focus();
            }
        });
    });
    
    // Remove stock form validation
    const removeStockForms = document.querySelectorAll('form[action*="remove_stock"]');
    removeStockForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const quantity = form.querySelector('input[name="quantity"]');
            const max = parseInt(quantity.getAttribute('max'));
            
            if (quantity && parseInt(quantity.value) > max) {
                e.preventDefault();
                alert(`Cannot remove more than ${max} units (available stock)`);
                quantity.focus();
            }
        });
    });
}

function setupQuickActions() {
    // Quick add stock buttons
    const quickAddButtons = document.querySelectorAll('.quick-add-stock');
    quickAddButtons.forEach(button => {
        button.addEventListener('click', function() {
            const stockId = this.dataset.stockId;
            const bookTitle = this.dataset.bookTitle;
            const suggestedQuantity = this.dataset.suggested || 10;
            
            if (confirm(`Add ${suggestedQuantity} units to "${bookTitle}"?`)) {
                // Create and submit a quick form
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = `/warehouse/stock/${stockId}/add/`;
                
                // Add CSRF token
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrfmiddlewaretoken';
                csrfInput.value = csrfToken;
                
                // Add quantity
                const quantityInput = document.createElement('input');
                quantityInput.type = 'hidden';
                quantityInput.name = 'quantity';
                quantityInput.value = suggestedQuantity;
                
                // Add reference
                const refInput = document.createElement('input');
                refInput.type = 'hidden';
                refInput.name = 'reference';
                refInput.value = 'Quick-Add-' + Date.now();
                
                // Add reason
                const reasonInput = document.createElement('input');
                reasonInput.type = 'hidden';
                reasonInput.name = 'reason';
                reasonInput.value = 'Quick stock addition';
                
                form.appendChild(csrfInput);
                form.appendChild(quantityInput);
                form.appendChild(refInput);
                form.appendChild(reasonInput);
                
                document.body.appendChild(form);
                form.submit();
            }
        });
    });
}

// Utility functions
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

function updateDashboardMetrics() {
    // This could be used to update metrics via AJAX
    fetch('/warehouse/api/metrics/')
        .then(response => response.json())
        .then(data => {
            document.getElementById('total-books').textContent = formatNumber(data.total_books);
            document.getElementById('total-quantity').textContent = formatNumber(data.total_quantity);
            document.getElementById('low-stock').textContent = formatNumber(data.low_stock);
            document.getElementById('out-of-stock').textContent = formatNumber(data.out_of_stock);
        })
        .catch(error => console.error('Error updating metrics:', error));
}

// Export functions for global use
window.warehouseUtils = {
    updateStockLevelBars,
    updateDashboardMetrics,
    formatNumber
};
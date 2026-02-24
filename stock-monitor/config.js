// Configuration for Stock Monitor

module.exports = {
    // Stock symbols to monitor
    stocks: ['AAPL', 'GOOGL', 'MSFT', 'AMZN'],
    
    // Check interval in milliseconds (default: 1 minute)
    checkInterval: 60000,
    
    // API configuration
    api: {
        baseUrl: 'https://api.example.com',
        key: process.env.API_KEY || ''
    },
    
    // Price alert thresholds
    alerts: {
        enabled: true,
        threshold: 5 // percentage change
    }
};

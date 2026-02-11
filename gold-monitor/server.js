const express = require('express');
const axios = require('axios');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// API endpoint for precious metals prices
app.get('/api/prices', async (req, res) => {
    try {
        // Try multiple free APIs or use fallback data
        
        // Option 1: Try GoldAPI.io (requires API key)
        const goldAPIKey = process.env.GOLDAPI_API_KEY;
        
        if (goldAPIKey) {
            try {
                const metals = ['XAU', 'XAG', 'XPT', 'XPD'];
                const prices = {};
                
                for (const symbol of metals) {
                    const response = await axios.get(`https://www.goldapi.io/api/${symbol}/USD`, {
                        headers: { 'x-access-token': goldAPIKey }
                    });
                    prices[symbol.toLowerCase()] = {
                        price: response.data.price,
                        change: response.data.ch || 0,
                        changePercent: response.data.chp || 0,
                        high: response.data.high || response.data.price,
                        low: response.data.low || response.data.price,
                        open: response.data.open || response.data.price
                    };
                }
                
                res.json(prices);
                return;
            } catch (apiError) {
                console.log('GoldAPI.io error:', apiError.message);
            }
        }
        
        // Option 2: Fallback to demo data with realistic prices
        const baseTime = Date.now();
        const demoData = {
            gold: {
                price: 2034.50 + (Math.sin(baseTime / 1000000) * 50),
                change: 12.35,
                changePercent: 0.61,
                high: 2045.20,
                low: 2020.10,
                open: 2022.15
            },
            silver: {
                price: 22.85 + (Math.sin(baseTime / 1000000) * 2),
                change: 0.45,
                changePercent: 2.01,
                high: 23.20,
                low: 22.40,
                open: 22.40
            },
            platinum: {
                price: 985.30 + (Math.sin(baseTime / 1000000) * 30),
                change: -8.70,
                changePercent: -0.87,
                high: 998.50,
                low: 980.00,
                open: 994.00
            },
            palladium: {
                price: 1050.80 + (Math.sin(baseTime / 1000000) * 40),
                change: 15.20,
                changePercent: 1.47,
                high: 1068.40,
                low: 1035.60,
                open: 1035.60
            }
        };
        
        res.json(demoData);
        
    } catch (error) {
        console.error('Error fetching prices:', error);
        res.status(500).json({ error: 'Failed to fetch prices' });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Precious Metals Monitor running on http://0.0.0.0:${PORT}`);
    console.log(`API endpoint: http://0.0.0.0:${PORT}/api/prices`);
});

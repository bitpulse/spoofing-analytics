# Spoofing Analytics API Documentation

## Overview

The Spoofing Analytics API provides real-time and historical access to cryptocurrency market manipulation (spoofing) data stored in Redis. It offers RESTful endpoints for querying, filtering, and analyzing spoofing events, plus WebSocket support for live updates.

## Features

- **Real-time Access**: Query spoofing data with <1ms response times
- **Multiple Query Patterns**: Recent, by pattern, top spoofs, statistics
- **Advanced Search**: Multi-criteria filtering
- **Live Updates**: WebSocket subscriptions for real-time notifications
- **Data Export**: CSV export functionality for analysis
- **CORS Enabled**: Ready for web frontend integration

## Quick Start

### 1. Start Redis
```bash
redis-server
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the API Server
```bash
python run_api.py
```

The API will be available at `http://localhost:8000`

### 4. View Interactive Documentation
Open `http://localhost:8000/docs` in your browser for Swagger UI

## API Endpoints

### Core Endpoints

#### Get Recent Spoofs
```http
GET /api/spoofs/recent?symbol=BTCUSDT&minutes=5&limit=100
```
Returns spoofing events from the last N minutes.

**Parameters:**
- `symbol` (required): Trading pair (e.g., BTCUSDT)
- `minutes`: Time window (1-1440, default: 5)
- `limit`: Max results (1-1000, default: 100)

**Example Response:**
```json
{
  "symbol": "BTCUSDT",
  "minutes": 5,
  "count": 23,
  "spoofs": [
    {
      "timestamp": "2025-08-18T10:30:45",
      "whale_id": "BTCUSDT_ask_65000_123456",
      "side": "ask",
      "price": 65000.0,
      "initial_value_usd": 6500000.0,
      "time_active_seconds": 45.2,
      "spoof_pattern": "flickering",
      "severity_score": 85
    }
  ]
}
```

#### Get Spoofs by Pattern
```http
GET /api/spoofs/patterns?symbol=BTCUSDT&pattern=flickering&limit=50
```
Filter spoofs by manipulation pattern type.

**Pattern Types:**
- `single`: One-time fake orders
- `flickering`: Rapidly appearing/disappearing orders
- `size_manipulation`: Orders with dramatic size changes

#### Get Top Spoofs
```http
GET /api/spoofs/top?symbol=BTCUSDT&limit=10&by=severity
```
Returns the most significant spoofing events.

**Ranking Options:**
- `severity`: Composite score based on impact
- `size`: By USD value

#### Get Statistics
```http
GET /api/spoofs/stats?symbol=BTCUSDT&hours=24
```
Aggregated statistics for analysis.

**Response Includes:**
- Total spoofs count
- Total/average USD values
- Pattern distribution
- Hourly breakdown
- Top 5 spoofs

#### Advanced Search
```http
POST /api/spoofs/search?symbol=BTCUSDT&limit=100
Content-Type: application/json

{
  "min_value": 100000,
  "max_value": 10000000,
  "min_duration": 5,
  "max_duration": 60,
  "pattern": "flickering",
  "side": "bid"
}
```
Multi-criteria search for specific spoof characteristics.

### Utility Endpoints

#### Export to CSV
```http
GET /api/spoofs/export?symbol=BTCUSDT&hours=24
```
Downloads spoofing data as CSV file.

#### Get Available Symbols
```http
GET /api/symbols
```
Lists all symbols with available spoofing data.

**Example Response:**
```json
{
  "total_symbols": 10,
  "symbols": [
    {
      "symbol": "BTCUSDT",
      "spoof_count": 1523
    },
    {
      "symbol": "ETHUSDT",
      "spoof_count": 892
    }
  ]
}
```

#### Get Monitored Trading Pairs
```http
GET /api/pairs
```
Returns comprehensive list of all monitored trading pairs with configuration details and data availability.

**Example Response:**
```json
{
  "total_pairs": 50,
  "actively_monitored": 45,
  "data_only": 5,
  "monitoring_groups": {
    "1": "Ultra High Risk - Meme Coins & New Listings",
    "2": "AI & Gaming Narrative - Heavy Speculation",
    "3": "Low Cap DeFi & L2s - Liquidity Games",
    "4": "Volatile Alts - Manipulation Favorites",
    "5": "Mid-Cap Majors & Established Alts"
  },
  "pairs": [
    {
      "symbol": "WIFUSDT",
      "monitoring_group": 1,
      "group_name": "Ultra High Risk - Meme Coins",
      "thresholds": {
        "whale": 30000,
        "mega_whale": 100000
      },
      "has_data": true,
      "data_stats": {
        "total_spoofs": 523,
        "first_seen": "2025-08-18T10:00:00",
        "last_seen": "2025-08-19T02:15:00",
        "patterns": {
          "single": 234,
          "flickering": 189,
          "size_manipulation": 100
        }
      }
    },
    {
      "symbol": "BTCUSDT",
      "monitoring_group": 5,
      "group_name": "Mid-Cap Majors",
      "thresholds": {
        "whale": 1000000,
        "mega_whale": 5000000
      },
      "has_data": false,
      "data_stats": {}
    }
  ],
  "summary": {
    "with_data": 25,
    "without_data": 25,
    "by_group": {
      "0": 5,
      "1": 10,
      "2": 10,
      "3": 10,
      "4": 10,
      "5": 10
    }
  }
}
```

**Response Fields:**
- `monitoring_group`: 0 = historical data only, 1-5 = active monitoring groups
- `thresholds`: USD values for whale detection
- `has_data`: Whether spoofing data exists for this pair
- `data_stats`: Statistics if data exists (total spoofs, time range, pattern distribution)

#### Redis Info
```http
GET /api/redis/info
```
Redis connection status and statistics.

#### Health Check
```http
GET /health
```
Service health status for monitoring.

## WebSocket Support

### Live Spoof Notifications
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/spoofs/BTCUSDT');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'spoof') {
    console.log('New spoof detected:', data.data);
    // Update UI with new spoof
  }
};
```

## Frontend Integration Guide

### Using the Pairs Endpoint for Dynamic Symbol Selection

```javascript
// SymbolSelector.js
async function loadAvailablePairs() {
  try {
    const response = await fetch('http://localhost:8000/api/pairs');
    const data = await response.json();
    
    // Filter pairs with data
    const pairsWithData = data.pairs.filter(p => p.has_data);
    
    // Group by monitoring group
    const groupedPairs = {};
    pairsWithData.forEach(pair => {
      const groupName = pair.group_name;
      if (!groupedPairs[groupName]) {
        groupedPairs[groupName] = [];
      }
      groupedPairs[groupName].push(pair);
    });
    
    // Create dropdown options
    const selectElement = document.getElementById('symbolSelect');
    
    Object.entries(groupedPairs).forEach(([group, pairs]) => {
      const optgroup = document.createElement('optgroup');
      optgroup.label = group;
      
      pairs.forEach(pair => {
        const option = document.createElement('option');
        option.value = pair.symbol;
        option.textContent = `${pair.symbol} (${pair.data_stats.total_spoofs} spoofs)`;
        option.dataset.thresholds = JSON.stringify(pair.thresholds);
        optgroup.appendChild(option);
      });
      
      selectElement.appendChild(optgroup);
    });
    
    return data;
  } catch (error) {
    console.error('Failed to load pairs:', error);
  }
}

// React component example
function PairSelector({ onPairSelect }) {
  const [pairs, setPairs] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(1);
  
  useEffect(() => {
    fetch('http://localhost:8000/api/pairs')
      .then(res => res.json())
      .then(data => {
        setPairs(data.pairs);
      });
  }, []);
  
  const filteredPairs = pairs.filter(p => 
    p.monitoring_group === selectedGroup && p.has_data
  );
  
  return (
    <div className="pair-selector">
      <div className="group-tabs">
        {[1, 2, 3, 4, 5].map(group => (
          <button 
            key={group}
            className={selectedGroup === group ? 'active' : ''}
            onClick={() => setSelectedGroup(group)}
          >
            Group {group}
          </button>
        ))}
      </div>
      
      <div className="pairs-grid">
        {filteredPairs.map(pair => (
          <div 
            key={pair.symbol}
            className="pair-card"
            onClick={() => onPairSelect(pair)}
          >
            <h4>{pair.symbol}</h4>
            <div className="stats">
              <span>Spoofs: {pair.data_stats.total_spoofs}</span>
              <span>Threshold: ${pair.thresholds.whale.toLocaleString()}</span>
            </div>
            <div className="patterns">
              {Object.entries(pair.data_stats.patterns || {}).map(([pattern, count]) => (
                <span key={pattern} className={`pattern ${pattern}`}>
                  {pattern}: {count}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Complete React Trading Dashboard Example

```jsx
// SpoofingDashboard.jsx
import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

function SpoofingDashboard() {
  const [availablePairs, setAvailablePairs] = useState([]);
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [recentSpoofs, setRecentSpoofs] = useState([]);
  const [stats, setStats] = useState({});
  const [liveData, setLiveData] = useState([]);
  const ws = useRef(null);
  
  // Load available pairs on mount
  useEffect(() => {
    axios.get(`${API_BASE}/api/pairs`)
      .then(response => {
        const pairsWithData = response.data.pairs.filter(p => p.has_data);
        setAvailablePairs(pairsWithData);
        
        // Set first pair with data as default
        if (pairsWithData.length > 0 && !symbol) {
          setSymbol(pairsWithData[0].symbol);
        }
      })
      .catch(error => console.error('Error loading pairs:', error));
  }, []);

  // Fetch recent spoofs
  const fetchRecentSpoofs = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/spoofs/recent`, {
        params: { symbol, minutes: 5, limit: 20 }
      });
      setRecentSpoofs(response.data.spoofs);
    } catch (error) {
      console.error('Error fetching spoofs:', error);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/spoofs/stats`, {
        params: { symbol, hours: 24 }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Setup WebSocket for live updates
  useEffect(() => {
    // Connect to WebSocket
    ws.current = new WebSocket(`ws://localhost:8000/ws/spoofs/${symbol}`);
    
    ws.current.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'spoof') {
        // Add new spoof to live feed
        setLiveData(prev => [data.data, ...prev.slice(0, 9)]);
        
        // Show notification
        showNotification(data.data);
      }
    };
    
    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    // Cleanup on unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [symbol]);

  // Initial data fetch
  useEffect(() => {
    fetchRecentSpoofs();
    fetchStats();
    const interval = setInterval(() => {
      fetchRecentSpoofs();
      fetchStats();
    }, 30000); // Refresh every 30 seconds
    
    return () => clearInterval(interval);
  }, [symbol]);

  const showNotification = (spoof) => {
    if (Notification.permission === 'granted') {
      new Notification('🚨 Spoofing Alert', {
        body: `${spoof.spoof_pattern} on ${spoof.side} side: $${spoof.value_usd.toLocaleString()}`,
        icon: '/alert-icon.png'
      });
    }
  };

  const getSeverityColor = (score) => {
    if (score >= 80) return '#ff4444';
    if (score >= 60) return '#ff8800';
    if (score >= 40) return '#ffbb33';
    return '#00C851';
  };

  return (
    <div className="dashboard">
      <h1>Spoofing Analytics Dashboard</h1>
      
      {/* Symbol Selector */}
      <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
        <option value="BTCUSDT">BTC/USDT</option>
        <option value="ETHUSDT">ETH/USDT</option>
        <option value="SOLUSDT">SOL/USDT</option>
      </select>

      {/* Statistics Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <h3>24h Spoofs</h3>
          <div className="stat-value">{stats.total_spoofs || 0}</div>
        </div>
        <div className="stat-card">
          <h3>Total Value</h3>
          <div className="stat-value">
            ${(stats.total_value_usd || 0).toLocaleString()}
          </div>
        </div>
        <div className="stat-card">
          <h3>Avg Spoof Size</h3>
          <div className="stat-value">
            ${(stats.avg_value_usd || 0).toLocaleString()}
          </div>
        </div>
        <div className="stat-card">
          <h3>Spoofs/Hour</h3>
          <div className="stat-value">
            {(stats.spoofs_per_hour || 0).toFixed(1)}
          </div>
        </div>
      </div>

      {/* Live Feed */}
      <div className="live-feed">
        <h2>🔴 Live Spoofing Activity</h2>
        <div className="feed-items">
          {liveData.map((spoof, idx) => (
            <div key={idx} className="feed-item animate-in">
              <span className={`side ${spoof.side}`}>{spoof.side.toUpperCase()}</span>
              <span className="value">${spoof.value_usd.toLocaleString()}</span>
              <span className="pattern">{spoof.pattern}</span>
              <span 
                className="severity" 
                style={{color: getSeverityColor(spoof.severity)}}
              >
                {spoof.severity}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Spoofs Table */}
      <div className="spoofs-table">
        <h2>Recent Spoofing Events</h2>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Side</th>
              <th>Price</th>
              <th>Value (USD)</th>
              <th>Duration</th>
              <th>Pattern</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {recentSpoofs.map((spoof) => (
              <tr key={spoof.whale_id}>
                <td>{new Date(spoof.timestamp).toLocaleTimeString()}</td>
                <td className={spoof.side}>{spoof.side}</td>
                <td>${spoof.price.toLocaleString()}</td>
                <td>${spoof.initial_value_usd.toLocaleString()}</td>
                <td>{spoof.time_active_seconds.toFixed(1)}s</td>
                <td>{spoof.spoof_pattern}</td>
                <td>
                  <div 
                    className="severity-bar"
                    style={{
                      width: `${spoof.severity_score}%`,
                      backgroundColor: getSeverityColor(spoof.severity_score)
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### Vue.js Integration

```vue
<!-- SpoofingMonitor.vue -->
<template>
  <div class="spoofing-monitor">
    <h2>Market Manipulation Monitor</h2>
    
    <!-- Real-time Alerts -->
    <div class="alerts-panel">
      <transition-group name="alert" tag="div">
        <div 
          v-for="alert in alerts" 
          :key="alert.id"
          :class="['alert', alert.severity]"
        >
          <span class="time">{{ formatTime(alert.timestamp) }}</span>
          <span class="message">{{ alert.message }}</span>
          <span class="value">${{ alert.value.toLocaleString() }}</span>
        </div>
      </transition-group>
    </div>

    <!-- Pattern Distribution Chart -->
    <div class="chart-container">
      <canvas ref="patternChart"></canvas>
    </div>

    <!-- Filters -->
    <div class="filters">
      <input 
        v-model="filters.minValue" 
        type="number" 
        placeholder="Min Value USD"
      />
      <select v-model="filters.pattern">
        <option value="">All Patterns</option>
        <option value="single">Single</option>
        <option value="flickering">Flickering</option>
        <option value="size_manipulation">Size Manipulation</option>
      </select>
      <button @click="searchSpoofs">Search</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';
import Chart from 'chart.js/auto';

export default {
  setup() {
    const alerts = ref([]);
    const filters = ref({
      minValue: 100000,
      pattern: ''
    });
    let ws = null;
    let chart = null;

    const connectWebSocket = (symbol) => {
      ws = new WebSocket(`ws://localhost:8000/ws/spoofs/${symbol}`);
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'spoof') {
          addAlert(data.data);
          updateChart(data.data);
        }
      };
    };

    const addAlert = (spoof) => {
      const alert = {
        id: Date.now(),
        timestamp: new Date(),
        severity: spoof.severity_score >= 80 ? 'critical' : 'warning',
        message: `${spoof.spoof_pattern} detected on ${spoof.side}`,
        value: spoof.initial_value_usd
      };
      
      alerts.value.unshift(alert);
      if (alerts.value.length > 10) {
        alerts.value.pop();
      }
    };

    const searchSpoofs = async () => {
      try {
        const response = await axios.post(
          'http://localhost:8000/api/spoofs/search?symbol=BTCUSDT',
          filters.value
        );
        console.log('Search results:', response.data);
      } catch (error) {
        console.error('Search error:', error);
      }
    };

    onMounted(() => {
      connectWebSocket('BTCUSDT');
      initChart();
    });

    onUnmounted(() => {
      if (ws) ws.close();
      if (chart) chart.destroy();
    });

    return { alerts, filters, searchSpoofs };
  }
};
</script>
```

### Angular Service Implementation

```typescript
// spoofing.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { webSocket } from 'rxjs/webSocket';

interface Spoof {
  timestamp: string;
  whale_id: string;
  side: 'bid' | 'ask';
  price: number;
  initial_value_usd: number;
  time_active_seconds: number;
  spoof_pattern: string;
  severity_score: number;
}

interface SpoofStats {
  total_spoofs: number;
  total_value_usd: number;
  avg_value_usd: number;
  patterns: Record<string, number>;
}

@Injectable({
  providedIn: 'root'
})
export class SpoofingService {
  private apiUrl = 'http://localhost:8000';
  private spoofSubject = new Subject<Spoof>();
  public spoofs$ = this.spoofSubject.asObservable();

  constructor(private http: HttpClient) {}

  // Get recent spoofs
  getRecentSpoofs(symbol: string, minutes = 5): Observable<any> {
    return this.http.get(`${this.apiUrl}/api/spoofs/recent`, {
      params: { symbol, minutes: minutes.toString() }
    });
  }

  // Get statistics
  getStats(symbol: string, hours = 24): Observable<SpoofStats> {
    return this.http.get<SpoofStats>(`${this.apiUrl}/api/spoofs/stats`, {
      params: { symbol, hours: hours.toString() }
    });
  }

  // Connect to WebSocket
  connectToLiveFeed(symbol: string): void {
    const ws$ = webSocket(`ws://localhost:8000/ws/spoofs/${symbol}`);
    
    ws$.subscribe({
      next: (msg: any) => {
        if (msg.type === 'spoof') {
          this.spoofSubject.next(msg.data);
        }
      },
      error: err => console.error('WebSocket error:', err),
      complete: () => console.log('WebSocket connection closed')
    });
  }

  // Advanced search
  searchSpoofs(symbol: string, filters: any): Observable<any> {
    return this.http.post(
      `${this.apiUrl}/api/spoofs/search?symbol=${symbol}`,
      filters
    );
  }

  // Export data
  exportToCSV(symbol: string, hours = 24): Observable<Blob> {
    return this.http.get(
      `${this.apiUrl}/api/spoofs/export`,
      {
        params: { symbol, hours: hours.toString() },
        responseType: 'blob'
      }
    );
  }
}
```

### Trading Alert System (JavaScript)

```javascript
// TradingAlertSystem.js
class TradingAlertSystem {
  constructor(apiUrl = 'http://localhost:8000') {
    this.apiUrl = apiUrl;
    this.ws = null;
    this.alerts = [];
    this.thresholds = {
      minValue: 100000,
      criticalSeverity: 80,
      warningDuration: 30
    };
  }

  // Initialize monitoring for multiple symbols
  async initializeMonitoring(symbols) {
    for (const symbol of symbols) {
      this.connectWebSocket(symbol);
      await this.loadHistoricalData(symbol);
    }
    
    // Start periodic stats update
    setInterval(() => this.updateDashboard(), 30000);
  }

  connectWebSocket(symbol) {
    const ws = new WebSocket(`ws://localhost:8000/ws/spoofs/${symbol}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'spoof') {
        this.processSpoofAlert(symbol, data.data);
      }
    };
    
    ws.onerror = (error) => {
      console.error(`WebSocket error for ${symbol}:`, error);
      // Implement reconnection logic
      setTimeout(() => this.connectWebSocket(symbol), 5000);
    };
  }

  processSpoofAlert(symbol, spoof) {
    // Check if alert meets thresholds
    if (spoof.initial_value_usd < this.thresholds.minValue) {
      return;
    }

    const alert = {
      id: `${symbol}_${Date.now()}`,
      symbol,
      timestamp: new Date(),
      spoof,
      severity: this.calculateAlertSeverity(spoof),
      actionRequired: this.determineAction(spoof)
    };

    this.alerts.push(alert);
    this.notifyTraders(alert);
    this.logAlert(alert);
  }

  calculateAlertSeverity(spoof) {
    if (spoof.severity_score >= 80) return 'CRITICAL';
    if (spoof.severity_score >= 60) return 'HIGH';
    if (spoof.severity_score >= 40) return 'MEDIUM';
    return 'LOW';
  }

  determineAction(spoof) {
    // Trading logic based on spoof patterns
    const actions = {
      'flickering': {
        'bid': 'Consider SHORT - Fake buy support detected',
        'ask': 'Consider LONG - Fake sell pressure detected'
      },
      'size_manipulation': {
        'bid': 'CAUTION - Large bid being manipulated',
        'ask': 'CAUTION - Large ask being manipulated'
      },
      'single': {
        'bid': 'Monitor - Single large bid appeared',
        'ask': 'Monitor - Single large ask appeared'
      }
    };

    return actions[spoof.spoof_pattern]?.[spoof.side] || 'Monitor';
  }

  notifyTraders(alert) {
    // Browser notification
    if (Notification.permission === 'granted') {
      new Notification(`🚨 ${alert.severity} Spoof Alert - ${alert.symbol}`, {
        body: alert.actionRequired,
        icon: '/alert-icon.png',
        requireInteraction: alert.severity === 'CRITICAL'
      });
    }

    // Sound alert for critical
    if (alert.severity === 'CRITICAL') {
      this.playAlertSound();
    }

    // Update UI
    this.updateAlertPanel(alert);
  }

  playAlertSound() {
    const audio = new Audio('/alert-sound.mp3');
    audio.play();
  }

  async loadHistoricalData(symbol) {
    try {
      const response = await fetch(
        `${this.apiUrl}/api/spoofs/recent?symbol=${symbol}&minutes=60`
      );
      const data = await response.json();
      
      // Analyze patterns
      this.analyzePatterns(symbol, data.spoofs);
    } catch (error) {
      console.error(`Failed to load historical data for ${symbol}:`, error);
    }
  }

  analyzePatterns(symbol, spoofs) {
    // Pattern analysis for predictive alerts
    const patterns = {
      timeDistribution: this.analyzeTimeDistribution(spoofs),
      commonPrices: this.findCommonPriceLevels(spoofs),
      manipulatorProfiles: this.identifyRepeatManipulators(spoofs)
    };

    console.log(`Pattern analysis for ${symbol}:`, patterns);
    return patterns;
  }

  // Export functionality
  async exportData(symbol, format = 'csv') {
    const url = `${this.apiUrl}/api/spoofs/export?symbol=${symbol}&hours=24`;
    
    try {
      const response = await fetch(url);
      const blob = await response.blob();
      
      // Create download link
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `spoofs_${symbol}_${Date.now()}.${format}`;
      a.click();
    } catch (error) {
      console.error('Export failed:', error);
    }
  }
}

// Initialize the system
const alertSystem = new TradingAlertSystem();
alertSystem.initializeMonitoring(['BTCUSDT', 'ETHUSDT', 'SOLUSDT']);
```

### Mobile App Integration (React Native)

```jsx
// SpoofingMobileApp.js
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  RefreshControl,
  Alert
} from 'react-native';
import PushNotification from 'react-native-push-notification';

const SpoofingMobileApp = () => {
  const [spoofs, setSpoofs] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [ws, setWs] = useState(null);

  useEffect(() => {
    // Configure push notifications
    PushNotification.configure({
      onNotification: function(notification) {
        console.log('Notification:', notification);
      },
      permissions: {
        alert: true,
        badge: true,
        sound: true
      }
    });

    // Connect to WebSocket
    connectWebSocket();
    
    return () => {
      if (ws) ws.close();
    };
  }, []);

  const connectWebSocket = () => {
    const websocket = new WebSocket('ws://your-server:8000/ws/spoofs/BTCUSDT');
    
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'spoof') {
        handleNewSpoof(data.data);
      }
    };
    
    setWs(websocket);
  };

  const handleNewSpoof = (spoof) => {
    // Add to list
    setSpoofs(prev => [spoof, ...prev.slice(0, 49)]);
    
    // Send push notification for high severity
    if (spoof.severity_score >= 80) {
      PushNotification.localNotification({
        title: '🚨 Critical Spoof Alert',
        message: `${spoof.spoof_pattern} - $${spoof.initial_value_usd.toLocaleString()}`,
        playSound: true,
        soundName: 'default',
        importance: 'high',
        vibrate: true
      });
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchRecentSpoofs();
    setRefreshing(false);
  };

  const renderSpoof = ({ item }) => (
    <View style={[styles.spoofCard, { borderLeftColor: getSeverityColor(item.severity_score) }]}>
      <View style={styles.spoofHeader}>
        <Text style={styles.pattern}>{item.spoof_pattern}</Text>
        <Text style={[styles.side, item.side === 'bid' ? styles.bid : styles.ask]}>
          {item.side.toUpperCase()}
        </Text>
      </View>
      <Text style={styles.value}>${item.initial_value_usd.toLocaleString()}</Text>
      <Text style={styles.duration}>Active for {item.time_active_seconds.toFixed(1)}s</Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={spoofs}
        renderItem={renderSpoof}
        keyExtractor={(item) => item.whale_id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      />
    </View>
  );
};
```

## Integration Examples

### Python Client
```python
import requests

# Get recent spoofs
response = requests.get(
    'http://localhost:8000/api/spoofs/recent',
    params={'symbol': 'BTCUSDT', 'minutes': 5}
)
spoofs = response.json()['spoofs']

for spoof in spoofs:
    print(f"Spoof: ${spoof['initial_value_usd']:,.0f} "
          f"lasted {spoof['time_active_seconds']:.1f}s")
```

### cURL Examples
```bash
# Get recent spoofs
curl "http://localhost:8000/api/spoofs/recent?symbol=BTCUSDT&minutes=10"

# Get statistics
curl "http://localhost:8000/api/spoofs/stats?symbol=BTCUSDT&hours=24"

# Search with filters
curl -X POST "http://localhost:8000/api/spoofs/search?symbol=BTCUSDT" \
  -H "Content-Type: application/json" \
  -d '{"min_value": 500000, "pattern": "flickering"}'
```

## Performance Considerations

### Response Times
- Recent spoofs: <5ms
- Pattern queries: <10ms
- Statistics: <20ms
- Search: <50ms (depends on criteria)

### Rate Limits
- Default: No rate limiting
- Production: Configure nginx/cloudflare rate limiting

### Caching
- Redis provides inherent caching
- Statistics cached for 1 minute
- Consider CDN for static exports

## Data Retention

- **Default TTL**: 30 days
- **Hourly Stats**: Aggregated and retained longer
- **CSV Exports**: Generated on-demand
- **Cleanup**: Automatic via Redis expiration

## Error Handling

All endpoints return standard HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found
- `500`: Server error

Error response format:
```json
{
  "detail": "Error description"
}
```

## Security Considerations

### CORS Configuration
Currently allows all origins (`*`). For production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Authentication
Not implemented. For production, consider:
- API keys
- JWT tokens
- OAuth2
- Rate limiting by API key

### Data Sanitization
All inputs are validated using Pydantic models.

## Monitoring

### Metrics to Track
- Request rate per endpoint
- Response times (p50, p95, p99)
- Redis memory usage
- WebSocket connections
- Error rates

### Health Checks
```bash
# Simple health check
curl http://localhost:8000/health

# Detailed Redis info
curl http://localhost:8000/api/redis/info
```

## Deployment

### Production Setup
```bash
# Use gunicorn with uvicorn workers
gunicorn src.api.spoofing_api:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.spoofing_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API server
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false  # Set to true for development
```

## Troubleshooting

### Redis Connection Issues
```python
# Test Redis connection
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()  # Should return True
```

### No Data Returned
1. Check if whale monitor is running and detecting spoofs
2. Verify Redis has data: `redis-cli keys "spoof:*"`
3. Check symbol spelling (case-sensitive)

### WebSocket Disconnections
- Implement reconnection logic in client
- Check nginx/proxy WebSocket settings
- Monitor for memory leaks in long connections

## Data Visualization and Charts

### Chart.js Integration for Real-time Charts

```javascript
// SpoofingCharts.js
import Chart from 'chart.js/auto';

class SpoofingCharts {
  constructor() {
    this.charts = {};
  }

  // Create severity distribution chart
  createSeverityChart(canvasId, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    this.charts.severity = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Critical (80-100)', 'High (60-79)', 'Medium (40-59)', 'Low (0-39)'],
        datasets: [{
          data: this.categorizeBySeverity(data),
          backgroundColor: ['#ff4444', '#ff8800', '#ffbb33', '#00C851'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
          tooltip: {
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                const percentage = ((value / total) * 100).toFixed(1);
                return `${label}: ${value} (${percentage}%)`;
              }
            }
          }
        }
      }
    });
  }

  // Create time-series chart for spoof frequency
  createTimeSeriesChart(canvasId, spoofs) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Group spoofs by hour
    const hourlyData = this.groupByHour(spoofs);
    
    this.charts.timeSeries = new Chart(ctx, {
      type: 'line',
      data: {
        labels: Object.keys(hourlyData),
        datasets: [{
          label: 'Spoofs per Hour',
          data: Object.values(hourlyData),
          borderColor: 'rgb(75, 192, 192)',
          backgroundColor: 'rgba(75, 192, 192, 0.2)',
          tension: 0.1
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: 'Number of Spoofs'
            }
          },
          x: {
            title: {
              display: true,
              text: 'Hour'
            }
          }
        }
      }
    });
  }

  // Real-time update for live chart
  updateLiveChart(chartId, newData) {
    const chart = this.charts[chartId];
    if (!chart) return;
    
    // Add new data point
    chart.data.labels.push(new Date().toLocaleTimeString());
    chart.data.datasets[0].data.push(newData);
    
    // Keep only last 20 points
    if (chart.data.labels.length > 20) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    
    chart.update('none'); // Update without animation for performance
  }
}
```

### D3.js Heatmap for Pattern Analysis

```javascript
// PatternHeatmap.js
import * as d3 from 'd3';

function createSpoofingHeatmap(containerId, data) {
  const margin = { top: 50, right: 50, bottom: 100, left: 100 };
  const width = 800 - margin.left - margin.right;
  const height = 400 - margin.top - margin.bottom;

  // Process data into hour x pattern matrix
  const hours = [...new Array(24)].map((_, i) => i);
  const patterns = ['single', 'flickering', 'size_manipulation'];
  
  const matrixData = [];
  hours.forEach(hour => {
    patterns.forEach(pattern => {
      const count = data.filter(d => 
        new Date(d.timestamp).getHours() === hour && 
        d.spoof_pattern === pattern
      ).length;
      
      matrixData.push({
        hour,
        pattern,
        count
      });
    });
  });

  // Create scales
  const xScale = d3.scaleBand()
    .domain(hours)
    .range([0, width])
    .padding(0.05);

  const yScale = d3.scaleBand()
    .domain(patterns)
    .range([height, 0])
    .padding(0.05);

  const colorScale = d3.scaleSequential()
    .interpolator(d3.interpolateReds)
    .domain([0, d3.max(matrixData, d => d.count)]);

  // Create SVG
  const svg = d3.select(containerId)
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  // Create heatmap cells
  svg.selectAll()
    .data(matrixData)
    .enter()
    .append('rect')
    .attr('x', d => xScale(d.hour))
    .attr('y', d => yScale(d.pattern))
    .attr('width', xScale.bandwidth())
    .attr('height', yScale.bandwidth())
    .style('fill', d => colorScale(d.count))
    .on('mouseover', function(event, d) {
      // Show tooltip
      const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0);
      
      tooltip.transition()
        .duration(200)
        .style('opacity', .9);
      
      tooltip.html(`Hour: ${d.hour}:00<br/>
                   Pattern: ${d.pattern}<br/>
                   Count: ${d.count}`)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 28) + 'px');
    });

  // Add axes
  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(d3.axisBottom(xScale));

  svg.append('g')
    .call(d3.axisLeft(yScale));
}
```

## Trading Strategy Implementation

### Using Spoofing Data for Trading Decisions

```javascript
// TradingStrategy.js
class SpoofingTradingStrategy {
  constructor(apiUrl) {
    this.apiUrl = apiUrl;
    this.positions = [];
    this.signals = [];
  }

  async analyzeMarket(symbol) {
    // Get recent spoofing data
    const spoofs = await this.getRecentSpoofs(symbol, 30);
    const stats = await this.getStats(symbol, 1);
    
    // Calculate manipulation intensity
    const manipulationScore = this.calculateManipulationScore(spoofs, stats);
    
    // Generate trading signals
    const signal = this.generateSignal(spoofs, manipulationScore);
    
    return {
      symbol,
      manipulationScore,
      signal,
      confidence: signal.confidence,
      recommendation: this.getRecommendation(signal)
    };
  }

  calculateManipulationScore(spoofs, stats) {
    // Weighted scoring based on:
    // - Frequency of spoofs
    // - Average severity
    // - Pattern distribution
    
    const frequencyScore = Math.min(stats.spoofs_per_hour / 10, 1) * 30;
    const severityScore = (spoofs.reduce((sum, s) => sum + s.severity_score, 0) / spoofs.length) * 0.7;
    const patternScore = this.analyzePatterns(spoofs) * 20;
    
    return frequencyScore + severityScore + patternScore;
  }

  generateSignal(spoofs, manipulationScore) {
    const recentSpoofs = spoofs.slice(0, 10);
    const bidSpoofs = recentSpoofs.filter(s => s.side === 'bid');
    const askSpoofs = recentSpoofs.filter(s => s.side === 'ask');
    
    // Analyze spoof imbalance
    const spoofImbalance = (bidSpoofs.length - askSpoofs.length) / recentSpoofs.length;
    
    // Flickering pattern indicates immediate manipulation
    const flickeringCount = recentSpoofs.filter(s => s.spoof_pattern === 'flickering').length;
    
    let signal = { action: 'HOLD', confidence: 0 };
    
    if (manipulationScore > 70) {
      // High manipulation environment
      if (spoofImbalance > 0.3 && flickeringCount > 3) {
        // Fake buy walls - consider SHORT
        signal = {
          action: 'SHORT',
          confidence: Math.min(spoofImbalance * 100, 85),
          reason: 'Multiple fake buy walls detected',
          stopLoss: 1.02, // 2% stop loss
          target: 0.97    // 3% profit target
        };
      } else if (spoofImbalance < -0.3 && flickeringCount > 3) {
        // Fake sell walls - consider LONG
        signal = {
          action: 'LONG',
          confidence: Math.min(Math.abs(spoofImbalance) * 100, 85),
          reason: 'Multiple fake sell walls detected',
          stopLoss: 0.98,
          target: 1.03
        };
      }
    }
    
    return signal;
  }

  getRecommendation(signal) {
    const recommendations = {
      'SHORT': {
        high: 'Open short position with 2% of portfolio',
        medium: 'Consider small short position or wait',
        low: 'Monitor only - insufficient confidence'
      },
      'LONG': {
        high: 'Open long position with 2% of portfolio',
        medium: 'Consider small long position or wait',
        low: 'Monitor only - insufficient confidence'
      },
      'HOLD': {
        high: 'Stay out of market - high manipulation',
        medium: 'Wait for clearer signals',
        low: 'Normal market conditions'
      }
    };
    
    const confidenceLevel = signal.confidence > 70 ? 'high' : 
                           signal.confidence > 40 ? 'medium' : 'low';
    
    return recommendations[signal.action][confidenceLevel];
  }

  // Risk management based on spoofing activity
  calculatePositionSize(accountBalance, manipulationScore) {
    // Reduce position size in highly manipulated markets
    const baseRisk = 0.02; // 2% base risk
    const adjustmentFactor = Math.max(0.3, 1 - (manipulationScore / 200));
    
    return accountBalance * baseRisk * adjustmentFactor;
  }
}
```

## Data Export and Analysis

### Automated Report Generation

```python
# generate_report.py
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import requests

class SpoofingReportGenerator:
    def __init__(self, api_url='http://localhost:8000'):
        self.api_url = api_url
    
    def generate_daily_report(self, symbol):
        """Generate comprehensive daily spoofing report"""
        
        # Fetch data
        stats = self.get_stats(symbol, 24)
        recent_spoofs = self.get_recent_spoofs(symbol, 1440)  # 24 hours
        
        # Create DataFrame
        df = pd.DataFrame(recent_spoofs)
        
        # Analysis
        report = {
            'summary': self.generate_summary(stats, df),
            'pattern_analysis': self.analyze_patterns(df),
            'time_distribution': self.analyze_time_distribution(df),
            'severity_analysis': self.analyze_severity(df),
            'recommendations': self.generate_recommendations(df)
        }
        
        # Generate visualizations
        self.create_visualizations(df, symbol)
        
        # Save report
        self.save_report(report, symbol)
        
        return report
    
    def analyze_patterns(self, df):
        """Analyze spoofing patterns"""
        pattern_counts = df['spoof_pattern'].value_counts()
        pattern_values = df.groupby('spoof_pattern')['initial_value_usd'].sum()
        
        return {
            'most_common': pattern_counts.index[0],
            'distribution': pattern_counts.to_dict(),
            'total_values': pattern_values.to_dict(),
            'flickering_rate': (pattern_counts.get('flickering', 0) / len(df)) * 100
        }
    
    def analyze_time_distribution(self, df):
        """Analyze when spoofing occurs most"""
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly_counts = df.groupby('hour').size()
        
        peak_hours = hourly_counts.nlargest(3).index.tolist()
        quiet_hours = hourly_counts.nsmallest(3).index.tolist()
        
        return {
            'peak_hours': peak_hours,
            'quiet_hours': quiet_hours,
            'hourly_distribution': hourly_counts.to_dict()
        }
    
    def generate_recommendations(self, df):
        """Generate trading recommendations based on analysis"""
        recommendations = []
        
        # Check manipulation intensity
        spoofs_per_hour = len(df) / 24
        if spoofs_per_hour > 10:
            recommendations.append("HIGH MANIPULATION: Reduce position sizes or avoid trading")
        
        # Check pattern distribution
        flickering_rate = (df['spoof_pattern'] == 'flickering').mean()
        if flickering_rate > 0.5:
            recommendations.append("FLICKERING DOMINANT: Expect high volatility, use tight stops")
        
        # Check time patterns
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        peak_hour = df.groupby('hour').size().idxmax()
        recommendations.append(f"PEAK MANIPULATION: Highest activity at {peak_hour}:00 UTC")
        
        return recommendations
    
    def create_visualizations(self, df, symbol):
        """Create charts for the report"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Pattern distribution
        df['spoof_pattern'].value_counts().plot(kind='bar', ax=axes[0, 0])
        axes[0, 0].set_title('Spoofing Pattern Distribution')
        
        # Severity distribution
        axes[0, 1].hist(df['severity_score'], bins=20, edgecolor='black')
        axes[0, 1].set_title('Severity Score Distribution')
        
        # Time distribution
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        df.groupby('hour').size().plot(ax=axes[1, 0])
        axes[1, 0].set_title('Hourly Spoofing Activity')
        
        # Value distribution
        axes[1, 1].scatter(df['time_active_seconds'], df['initial_value_usd'], alpha=0.5)
        axes[1, 1].set_xlabel('Duration (seconds)')
        axes[1, 1].set_ylabel('Value (USD)')
        axes[1, 1].set_title('Duration vs Value')
        
        plt.suptitle(f'Spoofing Analysis for {symbol}')
        plt.tight_layout()
        plt.savefig(f'report_{symbol}_{datetime.now().strftime("%Y%m%d")}.png')
```

## Support

For issues or questions:
1. Check API docs at `/docs`
2. Review Redis data structure in `src/storage/redis_storage.py`
3. Check logs for errors
4. Monitor Redis memory usage
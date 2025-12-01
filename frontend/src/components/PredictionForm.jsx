import React, { useState, useEffect, useRef } from 'react'
import Chart from 'chart.js/auto'

const PredictionForm = () => {
  const [ticker, setTicker] = useState('RELIANCE')
  const [days, setDays] = useState(5)
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [mode, setMode] = useState('auto') // 'auto' | 'manual'
  const [frequency, setFrequency] = useState('monthly') // daily | weekly | monthly (default monthly for reliability)
  const [avFunction, setAvFunction] = useState('TIME_SERIES_DAILY') // explicit AV function selector
  const [modelType, setModelType] = useState('ridge') // 'ridge' | 'rf'
  const [modelWindow, setModelWindow] = useState('60') // training window length
  const [ridgeAlpha, setRidgeAlpha] = useState('1.0')
  const [basePrice, setBasePrice] = useState('')
  const [driftPct, setDriftPct] = useState('0.1')
  const [volPct, setVolPct] = useState('1.0')
  const [slope, setSlope] = useState('')
  const chartRef = useRef(null)
  const chartInstanceRef = useRef(null)
  const [history, setHistory] = useState({ rows: [], request: {}, url: '', provider: '' })
  const [quote, setQuote] = useState(null)
  const [indicators, setIndicators] = useState({ rows: [], request: {}, url: '', provider: '' })
  const [indLatest, setIndLatest] = useState(null)
  const [activeTab, setActiveTab] = useState('history') // 'history' | 'quote' | 'indicators' | 'predict'
  const indChartRef = useRef(null)
  const indChartInstanceRef = useRef(null)
  const [featureCols, setFeatureCols] = useState([])
  const [featureColsLoading, setFeatureColsLoading] = useState(false)
  const [marketTicker, setMarketTicker] = useState('')

  useEffect(() => {
    if (!predictions || predictions.length === 0) {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy()
        chartInstanceRef.current = null
      }
      return
    }

    const labels = predictions.map((p) => p.date)
    const data = predictions.map((p) => p.price)

    const ctx = chartRef.current.getContext('2d')

    if (chartInstanceRef.current) {
      chartInstanceRef.current.data.labels = labels
      chartInstanceRef.current.data.datasets[0].data = data
      chartInstanceRef.current.update()
      return
    }

    chartInstanceRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Predicted Price (INR)',
            data,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
          },
        },
        scales: {
          y: {
            beginAtZero: false,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
            },
          },
          x: {
            grid: {
              color: 'rgba(0, 0, 0, 0.1)',
            },
          },
        },
      },
    })

    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy()
        chartInstanceRef.current = null
      }
    }
  }, [predictions])

  // Build/destroy indicators chart when indicator rows change
  useEffect(() => {
    const rows = indicators?.rows || []
    if (!rows.length) {
      if (indChartInstanceRef.current) {
        indChartInstanceRef.current.destroy()
        indChartInstanceRef.current = null
      }
      return
    }

    const ordered = rows.slice().reverse()
    const labels = ordered.map((r) => r.date)
    const close = ordered.map((r) => (r.close ?? null))
    const sma20 = ordered.map((r) => (r.sma_20 ?? null))
    const sma50 = ordered.map((r) => (r.sma_50 ?? null))
    const ema20 = ordered.map((r) => (r.ema_20 ?? null))
    const bbUpper = ordered.map((r) => (r.bb_upper ?? null))
    const bbLower = ordered.map((r) => (r.bb_lower ?? null))

    const ictx = indChartRef.current?.getContext('2d')
    if (!ictx) return

    if (indChartInstanceRef.current) {
      indChartInstanceRef.current.data.labels = labels
      indChartInstanceRef.current.data.datasets[0].data = close
      indChartInstanceRef.current.data.datasets[1].data = sma20
      indChartInstanceRef.current.data.datasets[2].data = sma50
      indChartInstanceRef.current.data.datasets[3].data = ema20
      indChartInstanceRef.current.data.datasets[4].data = bbUpper
      indChartInstanceRef.current.data.datasets[5].data = bbLower
      indChartInstanceRef.current.update()
      return
    }

    indChartInstanceRef.current = new Chart(ictx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Close',
            data: close,
            borderColor: '#111827',
            backgroundColor: 'rgba(17,24,39,0.05)',
            borderWidth: 2,
            tension: 0.2,
          },
          {
            label: 'SMA 20',
            data: sma20,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37,99,235,0.05)',
            borderWidth: 2,
            tension: 0.2,
          },
          {
            label: 'SMA 50',
            data: sma50,
            borderColor: '#7c3aed',
            backgroundColor: 'rgba(124,58,237,0.05)',
            borderWidth: 1.5,
            tension: 0.2,
          },
          {
            label: 'EMA 20',
            data: ema20,
            borderColor: '#dc2626',
            backgroundColor: 'rgba(220,38,38,0.05)',
            borderWidth: 1.5,
            borderDash: [2, 2],
            tension: 0.2,
          },
          {
            label: 'BB Upper',
            data: bbUpper,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16,185,129,0.05)',
            borderWidth: 1.5,
            borderDash: [4, 3],
            tension: 0.2,
          },
          {
            label: 'BB Lower',
            data: bbLower,
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245,158,11,0.05)',
            borderWidth: 1.5,
            borderDash: [4, 3],
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: {
          y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.1)' } },
          x: { grid: { color: 'rgba(0,0,0,0.1)' } },
        },
      },
    })

    return () => {
      if (indChartInstanceRef.current) {
        indChartInstanceRef.current.destroy()
        indChartInstanceRef.current = null
      }
    }
  }, [indicators])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    // don't clear other sections; allow switching via tabs
    setPredictions([])
    setIndLatest(null)

    try {
  const body = { ticker, days, frequency }
      // add model params for ML mode (API key is only from backend .env)
      body.model = {
        type: modelType,
        window: modelWindow !== '' ? Number(modelWindow) : undefined,
        alpha: modelType === 'ridge' && ridgeAlpha !== '' ? Number(ridgeAlpha) : undefined,
      }
      if (marketTicker.trim()) {
        body.market_ticker = marketTicker.trim()
      }
      if (mode === 'manual') {
        body.mode = 'manual'
        body.base_price = basePrice !== '' ? Number(basePrice) : undefined
        body.drift_pct = driftPct !== '' ? Number(driftPct) : undefined
        body.vol_pct = volPct !== '' ? Number(volPct) : undefined
        body.slope = slope !== '' ? Number(slope) : undefined
      }

      const response = await fetch('http://localhost:5000/api/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error || `HTTP ${response.status}`)
      }

      const data = await response.json()
      if (data.error) {
        throw new Error(data.error)
      }

  setPredictions(data.predictions || [])
  setIndLatest(data.indicators_latest || null)
    } catch (err) {
      setError(err.message || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const handleFetchFeatureColumns = async () => {
    setError(null)
    setFeatureColsLoading(true)
    setFeatureCols([])
    try {
      const body = { ticker, frequency, window: modelWindow !== '' ? Number(modelWindow) : undefined }
      if (marketTicker.trim()) {
        body.market_ticker = marketTicker.trim()
      }
      const res = await fetch('http://localhost:5000/api/features-columns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setFeatureCols(data.columns || [])
    } catch (err) {
      setError(err.message || 'Failed to fetch feature columns')
    } finally {
      setFeatureColsLoading(false)
    }
  }

  const handleFetchHistory = async () => {
    setError(null)
    setLoading(true)
    // don't clear other sections; allow switching via tabs
    setHistory({ rows: [], request: {}, url: '', provider: '' })
    try {
      const body = { ticker, function: avFunction, limit: 120 }
      const res = await fetch('http://localhost:5000/api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setHistory({ rows: data.rows || [], request: data.request || {}, url: data.url || '', provider: data.provider || '' })
    } catch (err) {
      setError(err.message || 'Failed to fetch history')
    } finally {
      setLoading(false)
    }
  }

  const handleFetchQuote = async () => {
    setError(null)
    setLoading(true)
    // don't clear other sections; allow switching via tabs
    setQuote(null)
    try {
      const res = await fetch('http://localhost:5000/api/quote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setQuote(data)
    } catch (err) {
      setError(err.message || 'Failed to fetch quote')
    } finally {
      setLoading(false)
    }
  }

  const handleComputeIndicators = async () => {
    setError(null)
    setLoading(true)
    // don't clear other sections; allow switching via tabs
    setIndicators({ rows: [], request: {}, url: '', provider: '' })
    try {
      const body = { ticker, function: avFunction, limit: 120 }
      const res = await fetch('http://localhost:5000/api/indicators', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.error || `HTTP ${res.status}`)
      }
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setIndicators({ rows: data.rows || [], request: data.request || {}, url: data.url || '', provider: data.provider || '' })
    } catch (err) {
      setError(err.message || 'Failed to compute indicators')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="header-section">
        <h1 className="main-title">📈 Stock Price Prediction</h1>
        <p className="subtitle">Advanced ML-powered predictions with 65+ technical indicators for NSE stocks</p>
      </div>

      <div className="form-container">
        <div className="form-row">
          <div className="form-group">
            <label className="form-label" htmlFor="ticker">
              <span className="label-text">📊 Stock Ticker (NSE)</span>
              <span className="label-required">*</span>
            </label>
            <input
              id="ticker"
              type="text"
              className="form-input primary"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="e.g., RELIANCE, TCS, INFY"
              required
            />
            <small className="text-sm mt-1">Enter ticker without .NS suffix</small>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="frequency">
              <span className="label-text">⏱️ Frequency</span>
            </label>
            <select 
              id="frequency" 
              className="form-select"
              value={frequency} 
              onChange={(e)=>setFrequency(e.target.value)}
            >
              <option value="daily">📅 Daily</option>
              <option value="weekly">📆 Weekly</option>
              <option value="monthly">🗓️ Monthly</option>
            </select>
            <small className="text-sm mt-1">Determines whether the API fetches daily, weekly, or monthly data</small>
          </div>
        </div>

        <div className="form-row">\n          <div className="form-group">

      <div className="form-group">
        <label htmlFor="avFunction">Alpha Vantage Function</label>
        <select id="avFunction" value={avFunction} onChange={(e)=>setAvFunction(e.target.value)}>
          <option value="TIME_SERIES_DAILY">TIME_SERIES_DAILY</option>
          <option value="TIME_SERIES_WEEKLY">TIME_SERIES_WEEKLY</option>
          <option value="TIME_SERIES_MONTHLY">TIME_SERIES_MONTHLY</option>
        </select>
        <small>Exact AV function used for history fetch (uses .env API key by default)</small>
      </div>

      <div className="form-group">
        <label htmlFor="marketTicker">Market Index Ticker (Optional)</label>
        <input
          id="marketTicker"
          type="text"
          value={marketTicker}
          onChange={(e) => setMarketTicker(e.target.value)}
          placeholder="e.g., NIFTY, SENSEX, SPY"
        />
        <small>For correlation analysis. Leave empty to skip market correlation features.</small>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <div className="tabs" role="tablist" aria-label="Data views">
          <button
            role="tab"
            aria-selected={activeTab==='history'}
            className={`tab-button ${activeTab==='history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            <span className="tab-icon">📈</span>
            <span className="tab-label">History</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab==='quote'}
            className={`tab-button ${activeTab==='quote' ? 'active' : ''}`}
            onClick={() => setActiveTab('quote')}
          >
            <span className="tab-icon">💰</span>
            <span className="tab-label">Quote</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab==='indicators'}
            className={`tab-button ${activeTab==='indicators' ? 'active' : ''}`}
            onClick={() => setActiveTab('indicators')}
          >
            <span className="tab-icon">⚡</span>
            <span className="tab-label">Indicators</span>
          </button>
          <button
            role="tab"
            aria-selected={activeTab==='predict'}
            className={`tab-button ${activeTab==='predict' ? 'active' : ''}`}
            onClick={() => setActiveTab('predict')}
          >
            <span className="tab-icon">🔮</span>
            <span className="tab-label">Predict</span>
          </button>
        </div>
      </div>

      {loading && (
        <div className="loading">
          Analyzing market data and generating predictions...
        </div>
      )}

      {error && (
        <>
          {/(alpha\s*vantage|alphavantage)/i.test(String(error)) && /(limit|rate)/i.test(String(error)) ? (
            <div className="notice" role="status" aria-live="polite">
              <strong>Alpha Vantage rate limit reached.</strong>
              <div style={{marginTop:'6px'}}>
                You’ve hit the free-tier quota. Please wait a few minutes and retry, or consider using a premium API key for higher limits.
              </div>
            </div>
          ) : null}
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
        </>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="tab-panel" role="tabpanel" aria-labelledby="history">
          <div className="action-buttons">
            <button type="button" className="btn secondary" onClick={handleFetchHistory} disabled={loading}>
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Fetching History...
                </>
              ) : (
                <>
                  📊 Fetch History
                </>
              )}
            </button>
          </div>
          {history.rows && history.rows.length > 0 && (
        <div className="results">
          <h3>History for {ticker.toUpperCase()} ({history.rows.length} rows)</h3>
          <p className="text-sm mb-3">
            Provider: {history.provider || 'alphavantage'} | Function: {avFunction} | URL: {history.url}
          </p>
          <div className="table-container">
            <table className="results-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Open</th>
                  <th>High</th>
                  <th>Low</th>
                  <th>Close</th>
                  <th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {history.rows.slice().reverse().map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.open ?? '-'}</td>
                    <td>{row.high ?? '-'}</td>
                    <td>{row.low ?? '-'}</td>
                    <td>{row.close ?? '-'}</td>
                    <td>{row.volume ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
          )}
        </div>
      )}

      {/* Quote Tab */}
      {activeTab === 'quote' && (
        <div className="tab-panel" role="tabpanel" aria-labelledby="quote">
          <div className="button-row" style={{marginBottom:'12px'}}>
            <button type="button" className="btn secondary" onClick={handleFetchQuote} disabled={loading}>
              {loading ? 'Fetching...' : 'Fetch Quote'}
            </button>
          </div>
          {quote && (
        <div className="results">
          <h3>Global Quote for {ticker.toUpperCase()}</h3>
          <table className="results-table">
            <tbody>
              <tr><td>Price</td><td>{quote.price ?? '-'}</td></tr>
              <tr><td>Open</td><td>{quote.open ?? '-'}</td></tr>
              <tr><td>High</td><td>{quote.high ?? '-'}</td></tr>
              <tr><td>Low</td><td>{quote.low ?? '-'}</td></tr>
              <tr><td>Previous Close</td><td>{quote.previous_close ?? '-'}</td></tr>
              <tr><td>Change</td><td>{quote.change ?? '-'}</td></tr>
              <tr><td>Change %</td><td>{quote.change_percent ?? '-'}</td></tr>
              <tr><td>Volume</td><td>{quote.volume ?? '-'}</td></tr>
              <tr><td>Latest Trading Day</td><td>{quote.latest_trading_day ?? '-'}</td></tr>
            </tbody>
          </table>
        </div>
          )}
        </div>
      )}

      {/* Indicators Tab */}
      {activeTab === 'indicators' && (
        <div className="tab-panel" role="tabpanel" aria-labelledby="indicators">
          <div className="button-row" style={{marginBottom:'12px'}}>
            <button type="button" className="btn secondary" onClick={handleComputeIndicators} disabled={loading}>
              {loading ? 'Computing...' : 'Compute Indicators'}
            </button>
          </div>
          {/* About indicators */}
          <details style={{marginBottom:'12px'}}>
            <summary><strong>About Technical Indicators (65+ Features Calculated)</strong></summary>
            <div style={{marginTop:'8px', lineHeight:1.5}}>
              <h4>🔄 Trend Indicators (8 features)</h4>
              <p><strong>SMA (5,10,20,50)</strong>: Simple Moving Average - arithmetic mean of last N closes</p>
              <p><strong>EMA (12,20,26,50)</strong>: Exponential Moving Average - weights recent prices more heavily</p>
              
              <h4>⚡ Momentum Indicators (10 features)</h4>
              <p><strong>RSI 14</strong>: Relative Strength Index (0-100) - overbought &gt;70, oversold &lt;30</p>
              <p><strong>MACD Suite</strong>: MACD = EMA(12) - EMA(26), Signal = EMA(9) of MACD, Histogram = MACD - Signal</p>
              <p><strong>Stochastic %K/%D</strong>: Oscillator showing position within recent high-low range</p>
              <p><strong>ADX & DI</strong>: Average Directional Index + Plus/Minus Directional Indicators</p>
              
              <h4>📊 Volatility Indicators (11 features)</h4>
              <p><strong>True Range & ATR 14</strong>: Measures market volatility using EMA of True Range</p>
              <p><strong>Bollinger Bands</strong>: SMA(20) ± 2×StdDev bands, width shows volatility expansion</p>
              <p><strong>Rolling Stats</strong>: Standard deviation, skewness, kurtosis, z-scores of price</p>
              
              <h4>📈 Volume Indicators (6 features)</h4>
              <p><strong>OBV</strong>: On-Balance Volume - cumulative volume flow based on price direction</p>
              <p><strong>MFI 14</strong>: Money Flow Index - volume-weighted RSI</p>
              <p><strong>Volume Spike</strong>: Current volume vs 20-period average</p>
              
              <h4>💹 Price Action & Patterns (21+ features)</h4>
              <p><strong>Price Percentages</strong>: (High-Low)/Open%, (Close-Open)/Open%, daily returns</p>
              <p><strong>Lag Features</strong>: Previous close values (1,3,5,10 periods back)</p>
              <p><strong>Candle Patterns</strong>: Doji, bullish/bearish engulfing patterns</p>
              <p><strong>Support/Resistance</strong>: Rolling min/max levels, breakout/breakdown signals</p>
              
              <h4>🔗 Advanced Features</h4>
              <p><strong>Market Correlation</strong>: 20-period rolling correlation with market index (if provided)</p>
              <p><strong>Regime Detection</strong>: Trend vs range-bound market classification</p>
            </div>
          </details>
          {indicators.rows && indicators.rows.length > 0 && (
        <div className="results">
          <h3>Indicators for {ticker.toUpperCase()} ({indicators.rows.length} rows)</h3>
          <div className="chart-container" style={{height:'320px'}}>
            <canvas ref={indChartRef}></canvas>
          </div>
          <div style={{overflowX:'auto'}}>
            <table className="results-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Close</th>
                  <th>SMA 5</th>
                  <th>SMA 20</th>
                  <th>SMA 50</th>
                  <th>EMA 12</th>
                  <th>EMA 20</th>
                  <th>EMA 50</th>
                  <th>RSI 14</th>
                  <th>MACD</th>
                  <th>Signal</th>
                  <th>Hist</th>
                  <th>Stoch %K</th>
                  <th>Stoch %D</th>
                  <th>BB Upper</th>
                  <th>BB Lower</th>
                  <th>BB Width</th>
                  <th>ATR 14</th>
                  <th>True Range</th>
                  <th>ADX 14</th>
                  <th>+DI 14</th>
                  <th>-DI 14</th>
                  <th>Volume Spike</th>
                  <th>OBV</th>
                  <th>MFI 14</th>
                  <th>Corr Index</th>
                </tr>
              </thead>
              <tbody>
                {indicators.rows.slice().reverse().map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.close ? parseFloat(row.close).toFixed(2) : '-'}</td>
                    <td>{row.sma_5 ? parseFloat(row.sma_5).toFixed(2) : '-'}</td>
                    <td>{row.sma_20 ? parseFloat(row.sma_20).toFixed(2) : '-'}</td>
                    <td>{row.sma_50 ? parseFloat(row.sma_50).toFixed(2) : '-'}</td>
                    <td>{row.ema_12 ? parseFloat(row.ema_12).toFixed(2) : '-'}</td>
                    <td>{row.ema_20 ? parseFloat(row.ema_20).toFixed(2) : '-'}</td>
                    <td>{row.ema_50 ? parseFloat(row.ema_50).toFixed(2) : '-'}</td>
                    <td>{row.rsi_14 ? parseFloat(row.rsi_14).toFixed(2) : '-'}</td>
                    <td>{row.macd ? parseFloat(row.macd).toFixed(3) : '-'}</td>
                    <td>{row.macd_signal ? parseFloat(row.macd_signal).toFixed(3) : '-'}</td>
                    <td>{row.macd_hist ? parseFloat(row.macd_hist).toFixed(3) : '-'}</td>
                    <td>{row.stoch_k_14 ?? row.stoch_k ? parseFloat(row.stoch_k_14 ?? row.stoch_k).toFixed(2) : '-'}</td>
                    <td>{row.stoch_d_3 ?? row.stoch_d ? parseFloat(row.stoch_d_3 ?? row.stoch_d).toFixed(2) : '-'}</td>
                    <td>{row.bb_upper ? parseFloat(row.bb_upper).toFixed(2) : '-'}</td>
                    <td>{row.bb_lower ? parseFloat(row.bb_lower).toFixed(2) : '-'}</td>
                    <td>{row.bb_width ? parseFloat(row.bb_width).toFixed(4) : '-'}</td>
                    <td>{row.atr_14 ? parseFloat(row.atr_14).toFixed(2) : '-'}</td>
                    <td>{row.tr ? parseFloat(row.tr).toFixed(2) : '-'}</td>
                    <td>{row.adx_14 ? parseFloat(row.adx_14).toFixed(2) : '-'}</td>
                    <td>{row.plus_di_14 ?? row.di_pos_14 ? parseFloat(row.plus_di_14 ?? row.di_pos_14).toFixed(2) : '-'}</td>
                    <td>{row.minus_di_14 ?? row.di_neg_14 ? parseFloat(row.minus_di_14 ?? row.di_neg_14).toFixed(2) : '-'}</td>
                    <td>{row.volume_spike ?? row.vol_spike ? parseFloat(row.volume_spike ?? row.vol_spike).toFixed(2) : '-'}</td>
                    <td>{row.obv ? parseFloat(row.obv).toFixed(0) : '-'}</td>
                    <td>{row.mfi_14 ? parseFloat(row.mfi_14).toFixed(2) : '-'}</td>
                    <td>{row.corr_with_index_20 ? parseFloat(row.corr_with_index_20).toFixed(3) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
          )}
        </div>
      )}

      {/* Predictions Tab */}
      {activeTab === 'predict' && (
        <div className="tab-panel" role="tabpanel" aria-labelledby="predict">
          {/* Prediction controls */}
          <div className="form-row">
            <label>Mode</label>
            <div className="mode-toggle">
              <label><input type="radio" name="mode" value="auto" checked={mode==='auto'} onChange={()=>setMode('auto')} /> Auto (fetch history)</label>
              <label><input type="radio" name="mode" value="manual" checked={mode==='manual'} onChange={()=>setMode('manual')} /> Manual (enter parameters)</label>
            </div>
          </div>

          {mode === 'manual' && (
            <div className="manual-grid">
              <div className="form-group">
                <label htmlFor="basePrice">Base Price (₹)</label>
                <input id="basePrice" type="number" min="0" step="0.01" value={basePrice} onChange={(e)=>setBasePrice(e.target.value)} placeholder="e.g., 1000" />
                <small>Starting price. Leave empty to use latest fetched close.</small>
              </div>
              <div className="form-group">
                <label htmlFor="driftPct">Drift per step (%)</label>
                <input id="driftPct" type="number" step="0.01" value={driftPct} onChange={(e)=>setDriftPct(e.target.value)} />
                <small>Default 0.1% (upward drift)</small>
              </div>
              <div className="form-group">
                <label htmlFor="volPct">Volatility (std-dev, %)</label>
                <input id="volPct" type="number" step="0.01" value={volPct} onChange={(e)=>setVolPct(e.target.value)} />
                <small>Default 1.0% noise</small>
              </div>
              <div className="form-group">
                <label htmlFor="slope">Additive Slope (₹/step)</label>
                <input id="slope" type="number" step="0.01" value={slope} onChange={(e)=>setSlope(e.target.value)} placeholder="e.g., 2.0" />
                <small>Optional linear change added each day</small>
              </div>
            </div>
          )}

          {mode !== 'manual' && (
            <div className="manual-grid">
              <div className="form-group">
                <label htmlFor="modelType">Model</label>
                <select id="modelType" value={modelType} onChange={(e)=>setModelType(e.target.value)}>
                  <option value="ridge">Ridge Regression</option>
                  <option value="rf">Random Forest</option>
                </select>
                <small>Choose the ML model used for forecasting</small>
              </div>
              <div className="form-group">
                <label htmlFor="modelWindow">Training Window (bars)</label>
                <input id="modelWindow" type="number" min="10" step="1" value={modelWindow} onChange={(e)=>setModelWindow(e.target.value)} />
                <small>Number of most recent bars used for training (e.g., 60)</small>
              </div>
              <div className="form-group">
                <label htmlFor="ridgeAlpha">Ridge Alpha</label>
                <input id="ridgeAlpha" type="number" min="0" step="0.1" value={ridgeAlpha} onChange={(e)=>setRidgeAlpha(e.target.value)} disabled={modelType !== 'ridge'} />
                <small>Regularization strength for Ridge (ignored for Random Forest)</small>
              </div>
            </div>
          )}

          <div className="manual-grid">
            <div className="form-group">
              <label htmlFor="days">Prediction Days</label>
              <input
                id="days"
                type="number"
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                min="1"
                max="5"
                required
              />
              <small>Number of days to predict (1-5)</small>
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="button-row" style={{marginBottom:'12px'}}>
              <button type="submit" className="btn" disabled={loading}>
                {loading ? 'Predicting...' : 'Get Predictions'}
              </button>
              <button type="button" className="btn secondary" onClick={handleFetchFeatureColumns} disabled={featureColsLoading}>
                {featureColsLoading ? 'Loading...' : 'Show Feature Columns'}
              </button>
            </div>
          </form>

          {featureCols && featureCols.length > 0 && (
            <div className="results">
              <h3>Model Feature Columns ({featureCols.length})</h3>
              <details style={{marginBottom:'12px'}}>
                <summary><strong>All Feature Categories (65+ Features)</strong></summary>
                <div style={{marginTop:'8px', lineHeight:1.5}}>
                  <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(250px, 1fr))',gap:'12px'}}>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>🔄 Trend (8 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>sma_5, sma_10, sma_20, sma_50<br/>ema_12, ema_20, ema_26, ema_50</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>⚡ Momentum (10 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>rsi_14, macd, macd_signal, macd_hist<br/>stoch_k_14, stoch_d_3, stoch_k, stoch_d<br/>adx_14, regime_trend</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>📊 Volatility (11 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>tr, atr_14, bb_mid, bb_upper, bb_lower, bb_width<br/>rolling_std_10, rolling_std_20, rolling_skew_10<br/>rolling_kurt_10, rolling_zscore_10</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>📈 Volume (6 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>obv, mfi_14, vol_sma_20<br/>volume_spike, vol_spike, volume</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>💹 Price Action (6 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>hl_pct, co_pct, cp_pct<br/>ret_1, ret_5, close</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>⏰ Lags & History (8 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>close_lag_1, close_lag_3, close_lag_5, close_lag_10<br/>lag_1, lag_3, lag_5, lag_10</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>🎯 Directional (4 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>plus_di_14, minus_di_14<br/>di_pos_14, di_neg_14</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>🕯️ Patterns (7 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>doji, bull_engulf, bear_engulf<br/>support_20, resistance_20, breakout, breakdown</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>🔗 Correlation (2 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>corr_with_index_20, market_index</p>
                    </div>
                    <div>
                      <h4 style={{margin:'0 0 4px 0',color:'#1f2937'}}>📋 Base Data (3 features)</h4>
                      <p style={{fontSize:'0.85rem',margin:'0'}}>open, high, low</p>
                    </div>
                  </div>
                  <p style={{marginTop:'12px',fontSize:'0.9rem',fontStyle:'italic'}}>Total: 65+ features calculated for comprehensive market analysis</p>
                </div>
              </details>
              <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(200px, 1fr))', gap:'6px'}}>
                {featureCols.map((c) => {
                  let category = 'Other'
                  let color = '#f3f4f6'
                  let icon = '📊'
                  if (c.includes('sma_') || c.includes('ema_')) { category = 'Trend'; color = '#dbeafe'; icon = '🔄' }
                  else if (c.includes('rsi_') || c.includes('macd') || c.includes('stoch_') || c.includes('adx_') || c.includes('regime_')) { category = 'Momentum'; color = '#fef3c7'; icon = '⚡' }
                  else if (c.includes('atr_') || c.includes('tr') || c.includes('bb_') || c.includes('rolling_')) { category = 'Volatility'; color = '#fecaca'; icon = '📊' }
                  else if (c.includes('obv') || c.includes('mfi_') || c.includes('vol_') || c.includes('volume_')) { category = 'Volume'; color = '#d1fae5'; icon = '📈' }
                  else if (c.includes('_pct') || c.includes('ret_') || c === 'close') { category = 'Price Action'; color = '#e0e7ff'; icon = '💹' }
                  else if (c.includes('lag_') || c.includes('close_lag_')) { category = 'Lags'; color = '#f3e8ff'; icon = '⏰' }
                  else if (c.includes('di_') || c.includes('plus_') || c.includes('minus_')) { category = 'Directional'; color = '#fde68a'; icon = '🎯' }
                  else if (c.includes('doji') || c.includes('engulf') || c.includes('support') || c.includes('resistance') || c.includes('breakout') || c.includes('breakdown')) { category = 'Patterns'; color = '#e5e7eb'; icon = '🕯️' }
                  else if (c.includes('corr_') || c === 'market_index') { category = 'Correlation'; color = '#fed7d7'; icon = '🔗' }
                  else if (c.includes('f_')) { category = 'Fundamentals'; color = '#fdf2f8'; icon = '💰' }
                  else if (c === 'open' || c === 'high' || c === 'low') { category = 'Base Data'; color = '#f9fafb'; icon = '📋' }
                  return (
                    <div key={c} style={{border:'1px solid #d1d5db', borderRadius:6, padding:'8px', backgroundColor:color, fontSize:'0.8rem', transition:'all 0.2s'}}>
                      <div style={{fontWeight:600, fontSize:'0.7rem', color:'#4b5563', marginBottom:'3px', display:'flex', alignItems:'center', gap:'4px'}}>
                        <span>{icon}</span>
                        {category}
                      </div>
                      <div style={{fontFamily:'monospace', fontSize:'0.8rem', color:'#1f2937'}}>{c}</div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {predictions && predictions.length > 0 && (
        <div className="results">
          <h3>
            Predictions for {ticker.toUpperCase()} ({predictions.length} days)
          </h3>

          {indLatest && (
            <div style={{marginBottom:'12px'}}>
              <h4 style={{margin:'6px 0'}}>Latest indicators (from fetched history)</h4>
              <table className="results-table">
                <tbody>
                  <tr><td>Date</td><td>{indLatest.date ?? '-'}</td></tr>
                  <tr><td>Close</td><td>{indLatest.close ?? '-'}</td></tr>
                  <tr><td>SMA 20</td><td>{indLatest.sma_20 ?? '-'}</td></tr>
                  <tr><td>EMA 20</td><td>{indLatest.ema_20 ?? '-'}</td></tr>
                  <tr><td>RSI 14</td><td>{indLatest.rsi_14 ?? '-'}</td></tr>
                  <tr><td>MACD</td><td>{indLatest.macd ?? '-'}</td></tr>
                  <tr><td>Signal</td><td>{indLatest.macd_signal ?? '-'}</td></tr>
                  <tr><td>Hist</td><td>{indLatest.macd_hist ?? '-'}</td></tr>
                  <tr><td>BB Mid</td><td>{indLatest.bb_mid ?? '-'}</td></tr>
                  <tr><td>BB Upper</td><td>{indLatest.bb_upper ?? '-'}</td></tr>
                  <tr><td>BB Lower</td><td>{indLatest.bb_lower ?? '-'}</td></tr>
                  <tr><td>ATR 14</td><td>{indLatest.atr_14 ?? '-'}</td></tr>
                  <tr><td>OBV</td><td>{indLatest.obv ?? '-'}</td></tr>
                </tbody>
              </table>
            </div>
          )}

          <table className="results-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Predicted Price (INR)</th>
                <th>Change</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((prediction, index) => {
                const prevPrice = index > 0 ? predictions[index - 1].price : null
                const change = prevPrice ? prediction.price - prevPrice : null
                const changePercent = prevPrice ? ((change / prevPrice) * 100).toFixed(2) : null

                return (
                  <tr key={prediction.date}>
                    <td>{prediction.date}</td>
                    <td>₹{prediction.price}</td>
                    <td>
                      {change !== null && (
                        <span style={{ color: change >= 0 ? '#059669' : '#dc2626' }}>
                          {change >= 0 ? '+' : ''}₹{change.toFixed(2)} ({changePercent}%)
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>

          <div className="chart-container">
            <canvas ref={chartRef}></canvas>
          </div>

          <div className="qr-placeholder">
            <strong>QR Code</strong>
            <p>Share predictions via QR code (feature coming soon)</p>
          </div>
        </div>
          )}
        </div>
      )}
    </div>
    </div>
    </div>
    </div>
  )
}

export default PredictionForm
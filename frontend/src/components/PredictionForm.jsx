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
    const bbUpper = ordered.map((r) => (r.bb_upper ?? null))
    const bbLower = ordered.map((r) => (r.bb_lower ?? null))

    const ictx = indChartRef.current?.getContext('2d')
    if (!ictx) return

    if (indChartInstanceRef.current) {
      indChartInstanceRef.current.data.labels = labels
      indChartInstanceRef.current.data.datasets[0].data = close
      indChartInstanceRef.current.data.datasets[1].data = sma20
      indChartInstanceRef.current.data.datasets[2].data = bbUpper
      indChartInstanceRef.current.data.datasets[3].data = bbLower
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
      <h1>Stock Price Prediction</h1>
      <p>Get AI-powered predictions for NSE stocks</p>

      {/* Shared inputs */}
      <div className="form-group">
        <label htmlFor="ticker">Stock Ticker (NSE)</label>
        <input
          id="ticker"
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          placeholder="e.g., RELIANCE, TCS, INFY"
          required
        />
        <small>Enter ticker without .NS suffix</small>
      </div>

      <div className="form-group">
        <label htmlFor="frequency">Frequency</label>
        <select id="frequency" value={frequency} onChange={(e)=>setFrequency(e.target.value)}>
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
        <small>Determines whether the API fetches daily, weekly, or monthly data</small>
      </div>

      <div className="form-group">
        <label htmlFor="avFunction">Alpha Vantage Function</label>
        <select id="avFunction" value={avFunction} onChange={(e)=>setAvFunction(e.target.value)}>
          <option value="TIME_SERIES_DAILY">TIME_SERIES_DAILY</option>
          <option value="TIME_SERIES_WEEKLY">TIME_SERIES_WEEKLY</option>
          <option value="TIME_SERIES_MONTHLY">TIME_SERIES_MONTHLY</option>
        </select>
        <small>Exact AV function used for history fetch (uses .env API key by default)</small>
      </div>

      {/* Tabs */}
      <div className="tabs" role="tablist" aria-label="Data views">
        <button
          role="tab"
          aria-selected={activeTab==='history'}
          className={`tab ${activeTab==='history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          History
        </button>
        <button
          role="tab"
          aria-selected={activeTab==='quote'}
          className={`tab ${activeTab==='quote' ? 'active' : ''}`}
          onClick={() => setActiveTab('quote')}
        >
          Quote
        </button>
        <button
          role="tab"
          aria-selected={activeTab==='indicators'}
          className={`tab ${activeTab==='indicators' ? 'active' : ''}`}
          onClick={() => setActiveTab('indicators')}
        >
          Indicators
        </button>
        <button
          role="tab"
          aria-selected={activeTab==='predict'}
          className={`tab ${activeTab==='predict' ? 'active' : ''}`}
          onClick={() => setActiveTab('predict')}
        >
          Predictions
        </button>
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
          <div className="button-row" style={{marginBottom:'12px'}}>
            <button type="button" className="btn secondary" onClick={handleFetchHistory} disabled={loading}>
              {loading ? 'Fetching...' : 'Fetch History'}
            </button>
          </div>
          {history.rows && history.rows.length > 0 && (
        <div className="results">
          <h3>History for {ticker.toUpperCase()} ({history.rows.length} rows)</h3>
          <p style={{fontSize:'0.9rem'}}>
            Provider: {history.provider || 'alphavantage'} | Function: {avFunction} | URL: {history.url}
          </p>
          <div style={{overflowX:'auto'}}>
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
            <summary><strong>About these indicators</strong></summary>
            <div style={{marginTop:'8px', lineHeight:1.5}}>
              <p><strong>SMA (Simple Moving Average)</strong>: The arithmetic mean of the last N closes. Example: SMA(20) is the average of the last 20 closing prices.</p>
              <p><strong>EMA (Exponential Moving Average)</strong>: A moving average that weights recent prices more, using multiplier k = 2/(N+1). EMA reacts faster than SMA.</p>
              <p><strong>RSI (Relative Strength Index)</strong>: Momentum oscillator from 0–100. RSI = 100 - 100/(1 + RS), where RS is the ratio of average gains to average losses over 14 periods (Wilder's smoothing). Overbought &gt; 70, oversold &lt; 30 (common heuristics).</p>
              <p><strong>MACD</strong>: MACD = EMA(12) - EMA(26). Signal = EMA(9) of MACD. Histogram = MACD - Signal. Shows momentum shifts via line crossovers and histogram expansions.</p>
              <p><strong>Bollinger Bands</strong>: Mid = SMA(20); Upper = Mid + 2×StdDev(20); Lower = Mid - 2×StdDev(20). Width = (Upper - Lower) / Mid. Bands expand with volatility and contract when quiet.</p>
              <p><strong>ATR (Average True Range)</strong>: Measures volatility. True Range = max(high-low, |high-prevClose|, |low-prevClose|). ATR is the average of TR over 14 periods.</p>
              <p><strong>OBV (On-Balance Volume)</strong>: Cumulative volume adding when price closes up and subtracting when price closes down. Attempts to capture volume flow direction.</p>
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
                  <th>SMA 10</th>
                  <th>SMA 20</th>
                  <th>EMA 12</th>
                  <th>EMA 20</th>
                  <th>EMA 26</th>
                  <th>RSI 14</th>
                  <th>MACD</th>
                  <th>Signal</th>
                  <th>Hist</th>
                  <th>BB Mid</th>
                  <th>BB Upper</th>
                  <th>BB Lower</th>
                  <th>BB Width</th>
                  <th>ATR 14</th>
                  <th>OBV</th>
                </tr>
              </thead>
              <tbody>
                {indicators.rows.slice().reverse().map((row) => (
                  <tr key={row.date}>
                    <td>{row.date}</td>
                    <td>{row.close ?? '-'}</td>
                    <td>{row.sma_5 ?? '-'}</td>
                    <td>{row.sma_10 ?? '-'}</td>
                    <td>{row.sma_20 ?? '-'}</td>
                    <td>{row.ema_12 ?? '-'}</td>
                    <td>{row.ema_20 ?? '-'}</td>
                    <td>{row.ema_26 ?? '-'}</td>
                    <td>{row.rsi_14 ?? '-'}</td>
                    <td>{row.macd ?? '-'}</td>
                    <td>{row.macd_signal ?? '-'}</td>
                    <td>{row.macd_hist ?? '-'}</td>
                    <td>{row.bb_mid ?? '-'}</td>
                    <td>{row.bb_upper ?? '-'}</td>
                    <td>{row.bb_lower ?? '-'}</td>
                    <td>{row.bb_width ?? '-'}</td>
                    <td>{row.atr_14 ?? '-'}</td>
                    <td>{row.obv ?? '-'}</td>
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
            </div>
          </form>

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
  )
}

export default PredictionForm
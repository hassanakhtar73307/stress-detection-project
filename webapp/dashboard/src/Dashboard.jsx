import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import samples from './sample_windows.json';
import { useAuth } from './AuthContext';

const API_URL = 'http://127.0.0.1:5000/predict';

const LEVEL_COLORS = {
  Baseline: '#4ec9a8',
  Amusement: '#4ec9a8',
  Stress: '#e0574e',
};

const LEVEL_LABELS = {
  Baseline: 'LOW',
  Amusement: 'LOW',
  Stress: 'ELEVATED',
};

export default function Dashboard({ onOpenProfile }) {
  const { user, authHeader, logout } = useAuth();
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const tickRef = useRef(0);
  const hasInitialised = useRef(false);

  const runPrediction = async (idx, recordHistory = true) => {
    setSelectedIdx(idx);
    setLoading(true);
    setError(null);
    const sample = samples[idx];
    try {
      const res = await axios.post(API_URL, { features: sample.features }, { headers: authHeader });
      setResult({ ...res.data, true_label: sample.true_label, subject: sample.subject });
      if (recordHistory) {
        tickRef.current += 1;
        setHistory((h) => [
          ...h.slice(-19),
          {
            t: tickRef.current,
            time: new Date().toLocaleTimeString([], { hour12: false }),
            confidence: res.data.confidence,
            label: res.data.predicted_label,
            stress_prob: res.data.probabilities.Stress,
          },
        ]);
      }
    } catch (e) {
      if (e.response?.status === 401) {
        setError('Your session has expired — please log in again.');
      } else {
        setError(e.response?.data?.error || e.message || 'Request failed');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hasInitialised.current) return;
    hasInitialised.current = true;
    runPrediction(0, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const levelColor = result ? LEVEL_COLORS[result.predicted_label] : '#4ec9a8';
  const levelLabel = result ? LEVEL_LABELS[result.predicted_label] : '—';

  return (
    <div className="dashboard">
      <div className="header">
        <h1>Stress Monitor // Live Dashboard</h1>
        <div className="header-right">
          <div className="status">
            <span className="status-dot" style={{ background: levelColor, boxShadow: `0 0 6px ${levelColor}` }} />
            {loading ? 'READING...' : 'CONNECTED'}
          </div>
          <button type="button" className="link-btn" onClick={onOpenProfile}>{user?.name || 'Profile'}</button>
          <button type="button" className="link-btn danger" onClick={logout}>Log out</button>
        </div>
      </div>

      <div className="reading-panel" style={{ '--level-color': levelColor }}>
        <p className="reading-label">Current stress level</p>
        {error ? (
          <>
            <p className="reading-value" style={{ color: '#e0574e', fontSize: 20 }}>API unreachable</p>
            <p className="reading-sub">{error} — is webapp\api\app.py running on port 5000?</p>
          </>
        ) : result ? (
          <>
            <p className="reading-value">{levelLabel}</p>
            <p className="reading-sub">
              Predicted: {result.predicted_label} · True label: {result.true_label} · Subject {result.subject} · Confidence {(result.confidence * 100).toFixed(1)}%
            </p>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{ width: `${result.confidence * 100}%` }} />
            </div>
            <div className="probabilities">
              {['Baseline', 'Stress', 'Amusement'].map((cls) => (
                <div className="prob-cell" key={cls}>
                  <div className="label">{cls}</div>
                  <div className="value" style={{ color: LEVEL_COLORS[cls] }}>
                    {(result.probabilities[cls] * 100).toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p className="reading-value">Loading…</p>
        )}
      </div>

      <div className="samples-panel">
        <h2>Simulated sensor windows (real WESAD data)</h2>
        <div className="sample-grid">
          {samples.map((s, idx) => (
            <button
              key={idx}
              className={`sample-btn ${selectedIdx === idx ? 'active' : ''}`}
              style={selectedIdx === idx ? { '--level-color': LEVEL_COLORS[s.true_label] } : {}}
              onClick={() => runPrediction(idx)}
            >
              {s.true_label}
              <span className="subj">Subject {s.subject}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="chart-panel">
        <h2>Prediction history (this session)</h2>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={history}>
            <CartesianGrid stroke="#1f2b28" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="#7a938c" fontSize={11} tickLine={false} />
            <YAxis domain={[0, 1]} stroke="#7a938c" fontSize={11} tickLine={false} />
            <ReferenceLine y={0.5} stroke="#2a3a36" strokeDasharray="4 4" />
            <Tooltip
              contentStyle={{ background: '#0e1513', border: '1px solid #1f2b28', borderRadius: 4, fontFamily: 'JetBrains Mono', fontSize: 12 }}
              labelStyle={{ color: '#7a938c' }}
            />
            <Line type="monotone" dataKey="stress_prob" stroke="#e0574e" strokeWidth={2} dot={{ r: 3 }} name="Stress probability" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="footer-note">
        Research prototype — not a diagnostic tool. Model: XGBoost, 0.785 LOSO accuracy.<br />
        Mean inference latency: 0.67ms.
      </p>
    </div>
  );
}
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  LineChart, Line, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import samples from './sample_windows.json';
import { useAuth } from './AuthContext';

const API_URL = 'http://127.0.0.1:5000/predict';
const INSIGHTS_URL = 'http://127.0.0.1:5000/model-insights';

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
      const fullResult = { ...res.data, true_label: sample.true_label, subject: sample.subject };
      setResult(fullResult);
      if (recordHistory) {
        tickRef.current += 1;
        setHistory((h) => [
          ...h.slice(-19),
          {
            t: tickRef.current,
            time: new Date().toLocaleTimeString([], { hour12: false }),
            confidence: res.data.confidence,
            label: res.data.predicted_label,
            baseline_prob: res.data.probabilities.Baseline,
            stress_prob: res.data.probabilities.Stress,
            amusement_prob: res.data.probabilities.Amusement,
            idx,
            fullResult,
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

  const resetHistory = () => {
    setHistory([]);
    tickRef.current = 0;
    setResult(null);
    setSelectedIdx(null);
  };

  const undoLast = () => {
    setHistory((h) => {
      const next = h.slice(0, -1);
      if (next.length > 0) {
        const last = next[next.length - 1];
        setResult(last.fullResult);
        setSelectedIdx(last.idx);
      } else {
        setResult(null);
        setSelectedIdx(null);
      }
      return next;
    });
  };

  useEffect(() => {
    if (hasInitialised.current) return;
    hasInitialised.current = true;
    runPrediction(0, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [showInfo, setShowInfo] = useState(false);
  const [insights, setInsights] = useState(null);

  useEffect(() => {
    axios.get(INSIGHTS_URL).then((res) => {
      if (res.data.available) setInsights(res.data);
    }).catch(() => {
      // Model insights are optional -- silently skip if not yet generated
    });
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
          <button type="button" className="link-btn" onClick={() => setShowInfo((v) => !v)}>
            {showInfo ? 'Hide info' : 'How this works'}
          </button>
          <button type="button" className="link-btn" onClick={onOpenProfile}>{user?.name || 'Profile'}</button>
          <button type="button" className="link-btn danger" onClick={logout}>Log out</button>
        </div>
      </div>

      {showInfo && (
        <div className="info-panel">
          <h2>How this works</h2>
          <ol>
            <li>
              <strong>Real sensor recordings, not live sensors.</strong> Each button below is one
              real, pre-recorded window of chest-worn sensor data (ECG, EDA, EMG, respiration,
              temperature) from the WESAD dataset — not a live device on you right now.
            </li>
            <li>
              <strong>45 numeric features per window.</strong> Each window is summarised into
              45 statistics (mean, variability, frequency content, etc.) across the five sensors.
            </li>
            <li>
              <strong>A trained XGBoost model classifies it.</strong> Clicking a button sends
              those 45 numbers to this project's Flask API, which loads the trained model
              (0.785 mean accuracy under subject-independent LOSO cross-validation) and returns
              a prediction with a confidence score.
            </li>
            <li>
              <strong>"True label" is the real answer.</strong> Shown alongside the prediction so
              you can verify whether the model got it right for that specific window.
            </li>
            <li>
              <strong>Scope.</strong> This demonstrates a complete, working pipeline from
              physiological signal to a served prediction — it is a research prototype, not a
              clinical or diagnostic tool, and is not currently connected to a live wearable device.
            </li>
          </ol>
        </div>
      )}


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
              Predicted: {result.predicted_label} · True label: {result.true_label} · Participant {result.subject} · Confidence {(result.confidence * 100).toFixed(1)}%
            </p>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{ width: `${result.confidence * 100}%` }} />
            </div>
            <div className="prob-chart">
              <ResponsiveContainer width="100%" height={110}>
                <BarChart data={['Baseline', 'Stress', 'Amusement'].map((cls) => ({
                  name: cls, value: result.probabilities[cls] * 100,
                }))} layout="vertical" margin={{ left: 10, right: 20 }}>
                  <XAxis type="number" domain={[0, 100]} hide />
                  <YAxis type="category" dataKey="name" stroke="#7a938c" fontSize={12} tickLine={false} width={80} />
                  <Tooltip
                    formatter={(v) => `${v.toFixed(1)}%`}
                    contentStyle={{ background: '#0e1513', border: '1px solid #1f2b28', borderRadius: 4, fontFamily: 'JetBrains Mono', fontSize: 12 }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {['Baseline', 'Stress', 'Amusement'].map((cls) => (
                      <Cell key={cls} fill={LEVEL_COLORS[cls]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <>
            <p className="reading-value">{loading ? 'Loading…' : '—'}</p>
            {!loading && <p className="reading-sub">No reading yet — click a sample window below.</p>}
          </>
        )}
      </div>

      <div className="samples-panel">
        <h2>Simulated sensor windows (real WESAD data)</h2>
        <p className="panel-subtitle">
          Each button is one real recording from a different anonymised study participant.
          "S16", "S9" etc. are the participant ID codes used in the original WESAD dataset —
          not real names, just how the dataset labels its 15 volunteers.
        </p>
        <div className="sample-grid">
          {samples.map((s, idx) => (
            <button
              key={idx}
              className={`sample-btn ${selectedIdx === idx ? 'active' : ''}`}
              style={selectedIdx === idx ? { '--level-color': LEVEL_COLORS[s.true_label] } : {}}
              onClick={() => runPrediction(idx)}
            >
              {s.true_label}
              <span className="subj">Participant {s.subject}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="chart-panel">
        <div className="chart-header">
          <h2>Prediction history (this session)</h2>
          <div className="chart-header-buttons">
            <button type="button" className="reset-btn" onClick={undoLast} disabled={history.length === 0}>
              Undo last
            </button>
            <button type="button" className="reset-btn" onClick={resetHistory} disabled={history.length === 0}>
              Reset
            </button>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={history}>
            <CartesianGrid stroke="#1f2b28" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="#7a938c" fontSize={11} tickLine={false} />
            <YAxis domain={[0, 1]} stroke="#7a938c" fontSize={11} tickLine={false} />
            <ReferenceLine y={0.5} stroke="#2a3a36" strokeDasharray="4 4" />
            <Tooltip
              contentStyle={{ background: '#0e1513', border: '1px solid #1f2b28', borderRadius: 4, fontFamily: 'JetBrains Mono', fontSize: 12 }}
              labelStyle={{ color: '#7a938c' }}
            />
            <Legend wrapperStyle={{ fontSize: 12, fontFamily: 'JetBrains Mono' }} />
            <Line type="monotone" dataKey="baseline_prob" stroke="#4ec9a8" strokeWidth={2} dot={{ r: 3 }} name="Baseline" />
            <Line type="monotone" dataKey="stress_prob" stroke="#e0574e" strokeWidth={2} dot={{ r: 3 }} name="Stress" />
            <Line type="monotone" dataKey="amusement_prob" stroke="#8ab4f8" strokeWidth={2} dot={{ r: 3 }} name="Amusement" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {insights && (
        <div className="chart-panel">
          <h2>Model insights — which sensors drive predictions</h2>
          <p className="insight-note">
            Computed from the deployed XGBoost model's actual feature importance
            (src/feature_importance.py), not a general assumption about wearable sensors.
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={insights.by_sensor} margin={{ left: 10, right: 20 }}>
              <CartesianGrid stroke="#1f2b28" strokeDasharray="3 3" />
              <XAxis dataKey="sensor" stroke="#7a938c" fontSize={12} tickLine={false} />
              <YAxis stroke="#7a938c" fontSize={11} tickLine={false} unit="%" />
              <Tooltip
                formatter={(v) => `${v.toFixed(1)}%`}
                contentStyle={{ background: '#0e1513', border: '1px solid #1f2b28', borderRadius: 4, fontFamily: 'JetBrains Mono', fontSize: 12 }}
              />
              <Bar dataKey="importance_pct" fill="#4ec9a8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <p className="footer-note">
        Research prototype — not a diagnostic tool. Model: XGBoost, 0.785 LOSO accuracy.<br />
        Mean inference latency: 0.67ms.
      </p>
    </div>
  );
}
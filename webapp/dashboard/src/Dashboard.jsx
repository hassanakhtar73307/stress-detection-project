import { useEffect, useRef, useState } from 'react';
import './Dashboard.css';
import axios from 'axios';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import samples from './sample_windows.json';
import { useAuth } from './AuthContext';
import { API_BASE } from './api';

const API_URL = `${API_BASE}/predict`;
const HEALTH_URL = `${API_BASE}/health`;
const INSIGHTS_URL = `${API_BASE}/model-insights`;
const MODEL_META = {
  xgboost: {
    displayName: 'XGBoost',
    status: 'Recommended',
    accuracy: 79.9,
    precision: 68.2,
    recall: 71.3,
    f1: 67.7,
  },
  random_forest: {
    displayName: 'Random Forest',
    status: 'Alternative',
    accuracy: 76.8,
    precision: 64.5,
    recall: 66.2,
    f1: 63.1,
  },
  boost_forest: {
    displayName: 'Boost Forest',
    status: 'Ensemble',
    accuracy: 80.1,
    precision: 70.5,
    recall: 71.1,
    f1: 67.9,
  },
};

const STATE_META = {
  Baseline: {
    label: 'Calm State',
    shortLabel: 'Calm',
    level: 'LOW STRESS',
    color: '#2dd4bf',
    className: 'calm',
  },
  Stress: {
    label: 'Stress Response',
    shortLabel: 'Stress',
    level: 'ELEVATED STRESS',
    color: '#f59e0b',
    className: 'stress',
  },
  Amusement: {
    label: 'Positive Emotion',
    shortLabel: 'Positive emotion',
    level: 'POSITIVE STATE',
    color: '#8b5cf6',
    className: 'positive',
  },
};

const SCENARIO_COPY = [
  {
    title: 'Calm State',
    description: 'Typical resting physiological pattern',
    icon: 'calm',
  },
  {
    title: 'Resting State',
    description: 'Relaxed and stable body response',
    icon: 'rest',
  },
  {
    title: 'Calm State',
    description: 'Low arousal and a balanced body state',
    icon: 'leaf',
  },
  {
    title: 'Stress Response',
    description: 'Mild stress indicators in the sensor pattern',
    icon: 'bolt',
  },
  {
    title: 'Elevated Stress',
    description: 'Higher stress indicators observed',
    icon: 'alert',
  },
  {
    title: 'Stress Response',
    description: 'Stress pattern with increased arousal',
    icon: 'heart',
  },
  {
    title: 'Positive Emotion',
    description: 'Signs of a positive emotional state',
    icon: 'smile',
  },
  {
    title: 'Amusement Response',
    description: 'Pattern associated with amusement',
    icon: 'laugh',
  },
  {
    title: 'Positive Emotion',
    description: 'A second positive emotional example',
    icon: 'star',
  },
];

function Icon({ name, size = 24, className = '' }) {
  const common = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    className,
    'aria-hidden': true,
  };

  switch (name) {
    case 'brain':
      return (
        <svg {...common}>
          <path d="M9.5 4.5a3 3 0 0 0-5.2 2A3.4 3.4 0 0 0 3 12.9a3.4 3.4 0 0 0 2.2 5.8A3 3 0 0 0 9.5 20V4.5Z" />
          <path d="M14.5 4.5a3 3 0 0 1 5.2 2 3.4 3.4 0 0 1 1.3 6.4 3.4 3.4 0 0 1-2.2 5.8A3 3 0 0 1 14.5 20V4.5Z" />
          <path d="M9.5 8H7.7a2 2 0 0 0-2 2" />
          <path d="M14.5 8h1.8a2 2 0 0 1 2 2" />
          <path d="M9.5 15H7.8a2.2 2.2 0 0 0-2.1 1.4" />
          <path d="M14.5 15h1.7a2.2 2.2 0 0 1 2.1 1.4" />
        </svg>
      );
    case 'pulse':
      return (
        <svg {...common}>
          <path d="M3 12h4l2-5 4 10 2-5h6" />
          <path d="M20.8 7.2A5.2 5.2 0 0 0 12 4.3 5.2 5.2 0 0 0 3.2 7.2" />
        </svg>
      );
    case 'analysis':
      return (
        <svg {...common}>
          <path d="M4 19V9" />
          <path d="M10 19V5" />
          <path d="M16 19v-7" />
          <path d="m4 7 5-3 5 4 6-5" />
          <path d="M17 3h3v3" />
        </svg>
      );
    case 'chip':
      return (
        <svg {...common}>
          <rect x="6" y="6" width="12" height="12" rx="2" />
          <path d="M9 9h6v6H9z" />
          <path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4" />
        </svg>
      );
    case 'target':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="8" />
          <circle cx="12" cy="12" r="3" />
          <path d="m15 9 5-5M17 4h3v3" />
        </svg>
      );
    case 'calm':
      return (
        <svg {...common}>
          <circle cx="12" cy="7" r="3" />
          <path d="M5 20c1-4 3.3-6 7-6s6 2 7 6" />
          <path d="M8 17c1.2 1 2.5 1.5 4 1.5S14.8 18 16 17" />
        </svg>
      );
    case 'rest':
      return (
        <svg {...common}>
          <path d="M3 18V7M21 18v-6a2 2 0 0 0-2-2H8v8" />
          <path d="M3 15h18M6 10h2" />
          <circle cx="6" cy="8" r="2" />
        </svg>
      );
    case 'leaf':
      return (
        <svg {...common}>
          <path d="M20 4C11 4 5 8 5 14a5 5 0 0 0 5 5c6 0 10-6 10-15Z" />
          <path d="M4 21c3-5 7-8 12-11" />
        </svg>
      );
    case 'bolt':
      return (
        <svg {...common}>
          <path d="m13 2-8 12h7l-1 8 8-12h-7l1-8Z" />
        </svg>
      );
    case 'alert':
      return (
        <svg {...common}>
          <path d="M10.3 3.6 2.6 18a2 2 0 0 0 1.8 3h15.2a2 2 0 0 0 1.8-3L13.7 3.6a2 2 0 0 0-3.4 0Z" />
          <path d="M12 9v4M12 17h.01" />
        </svg>
      );
    case 'heart':
      return (
        <svg {...common}>
          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />
          <path d="M4.5 12h4l1.5-3 3 6 1.5-3h5" />
        </svg>
      );
    case 'smile':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 14s1.5 2 4 2 4-2 4-2" />
          <path d="M9 9h.01M15 9h.01" />
        </svg>
      );
    case 'laugh':
      return (
        <svg {...common}>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 14h8c-.6 2-2 3-4 3s-3.4-1-4-3Z" />
          <path d="m8 9 2-1M16 9l-2-1" />
        </svg>
      );
    case 'star':
      return (
        <svg {...common}>
          <path d="m12 2.5 3 6.1 6.7 1-4.8 4.7 1.1 6.7-6-3.2-6 3.2 1.1-6.7-4.8-4.7 6.7-1 3-6.1Z" />
        </svg>
      );
    case 'history':
      return (
        <svg {...common}>
          <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
          <path d="M3 3v5h5M12 7v5l3 2" />
        </svg>
      );
    case 'undo':
      return (
        <svg {...common}>
          <path d="M9 7 4 12l5 5" />
          <path d="M20 17a7 7 0 0 0-7-7H4" />
        </svg>
      );
    case 'trash':
      return (
        <svg {...common}>
          <path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 11v6M14 11v6" />
        </svg>
      );
    default:
      return null;
  }
}

function ProcessStep({ icon, title, subtitle, isLast }) {
  return (
    <>
      <div className="process-step">
        <div className="process-icon"><Icon name={icon} size={26} /></div>
        <div>
          <span>{title}</span>
          <small>{subtitle}</small>
        </div>
      </div>
      {!isLast && <span className="process-arrow" aria-hidden="true">→</span>}
    </>
  );
}

export default function Dashboard({
  onOpenProfile,
  onOpenAdmin,
  onOpenComparison,
}) {
  const { user, authHeader, logout } = useAuth();
  const [selectedIdx, setSelectedIdx] = useState(null);
  const [selectedModel, setSelectedModel] = useState('xgboost');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [showInfo, setShowInfo] = useState(false);
  const [insights, setInsights] = useState(null);
  const [apiStatus, setApiStatus] = useState('checking');
const tickRef = useRef(0);

useEffect(() => {
  let active = true;

  axios.get(HEALTH_URL, { timeout: 45000 })
    .then(() => {
      if (active) {
        setApiStatus('online');
      }
    })
    .catch(() => {
      if (active) {
        setApiStatus('offline');
      }
    });

  return () => {
    active = false;
  };
}, []);

useEffect(() => {
  let active = true;

  setInsights(null);

  axios.get(INSIGHTS_URL, {
    params: {
      model_name: selectedModel,
    },
    timeout: 45000,
  })
    .then((res) => {
      if (active && res.data.available) {
        setInsights(res.data);
      }
    })
    .catch(() => {
      if (active) {
        setInsights(null);
      }
    });

  return () => {
    active = false;
  };
}, [selectedModel]);


  const runPrediction = async (idx, recordHistory = true) => {
    setSelectedIdx(idx);
    setLoading(true);
    setError(null);

    const sample = samples[idx];

    try {
      const res = await axios.post(
        API_URL,
        {
          features: sample.features,
          model_name: selectedModel,
          sample_id: `scenario_${String(idx + 1).padStart(2, '0')}`,
          participant_id: sample.subject,
          expected_label: sample.true_label,
        },
        { headers: authHeader, timeout: 60000 },
      );

      const fullResult = {
        ...res.data,
        true_label: sample.true_label,
        subject: sample.subject,
        scenario: SCENARIO_COPY[idx],
      };

      setResult(fullResult);
      setApiStatus('online');

      if (recordHistory) {
        tickRef.current += 1;
        setHistory((current) => [
          ...current.slice(-19),
          {
            t: tickRef.current,
            time: new Date().toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
            }),
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
    } catch (requestError) {
      if (requestError.response?.status === 401) {
        // The saved token belongs to another backend, has expired, or the local
        // SQLite user no longer exists. Clear it and return to the login page.
        logout();
        return;
      }

      setApiStatus('offline');

      if (requestError.code === 'ECONNABORTED') {
        setError('The prediction service is taking longer than expected. It may be waking up—please try again in a moment.');
      } else {
        setError(
          requestError.response?.data?.error
          || 'The prediction service could not be reached. Please wait a moment and try again.',
        );
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
    setError(null);
  };

  const undoLast = () => {
    setHistory((current) => {
      const next = current.slice(0, -1);

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

  const predictedMeta = result
    ? STATE_META[result.predicted_label]
    : STATE_META.Baseline;

  const levelColor = predictedMeta.color;
  const activeModelMeta = MODEL_META[selectedModel];

  const statusCopy = loading
    ? 'ANALYZING...'
    : apiStatus === 'online'
      ? 'SYSTEM ONLINE'
      : apiStatus === 'offline'
        ? 'API OFFLINE'
        : 'CHECKING API...';

  return (
    <div className="dashboard-shell">
      <header className="dashboard-header">
        <div className="brand-lockup">
          <span className="brand-primary">Stress Monitor</span>
          <span className="brand-divider">//</span>
          <span>Live Dashboard</span>
        </div>

        <nav className="header-actions" aria-label="Dashboard navigation">
          <span className={`system-status ${apiStatus}`}>
            <span className="status-dot" />
            {statusCopy}
          </span>
          <button type="button" className="header-link" onClick={() => setShowInfo((value) => !value)}>
            {showInfo ? 'Hide explanation' : 'About the analysis'}
          </button>
          {user?.is_admin && (
            <button type="button" className="header-link admin-link" onClick={onOpenAdmin}>
              User analytics
            </button>
          )}
          <button type="button" className="header-link" onClick={onOpenComparison}>
            Model comparison
          </button>
          <button type="button" className="header-link" onClick={onOpenProfile}>
            {user?.name || 'Profile'}
          </button>
          <button type="button" className="header-link logout-link" onClick={logout}>
            Log out
          </button>
        </nav>
      </header>

      {showInfo && (
        <section className="explanation-panel" aria-label="How the stress analysis works">
          <div>
            <span className="eyebrow">About the analysis</span>
            <h2>Research data is analysed by a trained machine-learning model</h2>
          </div>
          <div className="explanation-grid">
            <p>
              Each scenario is a pre-recorded WESAD sensor window, not a live reading from the current user.
            </p>
            <p>
              The window is represented by 45 physiological features from ECG, EDA, EMG, respiration and temperature.
            </p>
            <p>
              The selected {activeModelMeta.displayName} model classifies the
              pattern as calm, stress or positive emotion.
            </p>
            <p>
              This is an academic research prototype and is not a medical or diagnostic system.
            </p>
          </div>
        </section>
      )}
      <section
  className="model-selector-panel"
  aria-label="Prediction model selection"
>
  <div className="model-selector-copy">
    <span className="eyebrow">Prediction model</span>
    <h2>Choose a trained model</h2>
    <p>
      {activeModelMeta.displayName} is currently selected. XGBoost and
      Random Forest are the tuned base models, while Boost Forest combines
      both using class-specific probability weights.
    </p>
  </div>

  <div className="model-selector-actions">
    <button
      type="button"
      className={`model-option ${
        selectedModel === 'xgboost' ? 'active' : ''
      }`}
      onClick={() => {
      setSelectedModel('xgboost');
      resetHistory();
  }}
    >
      <strong>XGBoost</strong>
      <span>Recommended · Accuracy 79.9%</span>
    </button>

    <button
      type="button"
      className={`model-option ${
        selectedModel === 'random_forest' ? 'active' : ''
      }`}
      onClick={() => {
      setSelectedModel('random_forest');
      resetHistory();
  }}
    >
      <strong>Random Forest</strong>
      <span>Alternative · Accuracy 76.8%</span>
    </button>

    <button
      type="button"
      className={`model-option ${
        selectedModel === 'boost_forest' ? 'active' : ''
      }`}
      onClick={() => {
      setSelectedModel('boost_forest');
      resetHistory();
  }}
    >
      <strong>Boost Forest</strong>
      <span>Ensemble · Accuracy 80.1%</span>
    </button>
  </div>
</section>

      <section className="classification-panel" style={{ '--active-color': levelColor }}>
        <div className="classification-summary">
          <span className="eyebrow">Current classification</span>

          <div className="classification-main">
            <div className={`classification-icon ${loading ? 'is-loading' : ''}`}>
              <Icon name={error ? 'alert' : 'brain'} size={54} />
            </div>

            <div className="classification-copy" aria-live="polite">
              {error ? (
                <>
                  <h2 className="error-title">Prediction unavailable</h2>
                  <p>{error}</p>
                  <button
                    type="button"
                    className="primary-action"
                    onClick={() => selectedIdx !== null && runPrediction(selectedIdx)}
                    disabled={selectedIdx === null || loading}
                  >
                    Try selected sample again
                  </button>
                </>
              ) : loading ? (
                <>
                  <h2>Analysing physiological data…</h2>
                  <p>The model is processing the selected 45-feature sensor window.</p>
                </>
              ) : result ? (
                <>
                  <div className="result-heading-row">
                    <h2>{predictedMeta.label}</h2>
                    <span className={`state-badge ${predictedMeta.className}`}>{predictedMeta.level}</span>
                  </div>
                  <p>
                    Scenario {String(selectedIdx + 1).padStart(2, '0')} · Dataset ID {result.subject} ·
                    {' '}model confidence {(result.confidence * 100).toFixed(1)}%
                  </p>
                  <div className="confidence-meter" aria-label={`Confidence ${(result.confidence * 100).toFixed(1)} percent`}>
                    <div className="confidence-fill" style={{ width: `${result.confidence * 100}%` }} />
                  </div>
                </>
              ) : (
                <>
                  <h2>Select a sample to begin</h2>
                  <p>Choose a scenario below to see how the system analyses physiological patterns.</p>
                </>
              )}
            </div>
          </div>

          {result && !loading && !error && (
            <div className="result-details">
              <div>
                <span>Model prediction</span>
                <strong>{predictedMeta.label}</strong>
              </div>
              <div>
                <span>Research reference</span>
                <strong>{STATE_META[result.true_label].label}</strong>
              </div>
              <div>
                <span>Dataset participant</span>
                <strong>{result.subject}</strong>
              </div>
            </div>
          )}
        </div>

        <div className="process-overview">
          <span className="eyebrow">How it works</span>
          <div className="process-steps">
            <ProcessStep icon="pulse" title="Physiological" subtitle="data" />
            <ProcessStep icon="analysis" title="Feature" subtitle="analysis" />
            <ProcessStep icon="chip" title="AI model" subtitle={activeModelMeta.displayName}/>
            <ProcessStep icon="target" title="State" subtitle="prediction" isLast />
          </div>

          {result && !loading && !error && (
            <div className="probability-summary">
              {['Baseline', 'Stress', 'Amusement'].map((label) => {
                const meta = STATE_META[label];
                const value = result.probabilities[label] * 100;
                return (
                  <div className="probability-row" key={label}>
                    <div>
                      <span>{meta.shortLabel}</span>
                      <strong>{value.toFixed(1)}%</strong>
                    </div>
                    <div className="probability-track">
                      <div style={{ width: `${value}%`, background: meta.color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section className="scenario-panel">
        <div className="section-heading-row">
          <div>
            <span className="eyebrow">Research-based sample scenarios</span>
            <p>
              Select a scenario to see how the model classifies a real anonymised WESAD sensor recording.
              The original participant code is shown on every card for research traceability.
            </p>
          </div>
          <div className="scenario-legend" aria-label="Scenario categories">
            <span><i className="legend-dot calm" /> Calm / resting</span>
            <span><i className="legend-dot stress" /> Stress</span>
            <span><i className="legend-dot positive" /> Positive emotion</span>
          </div>
        </div>

        <div className="scenario-grid">
          {samples.map((sample, idx) => {
            const scenario = SCENARIO_COPY[idx];
            const state = STATE_META[sample.true_label];
            const isActive = selectedIdx === idx;

            return (
              <button
                type="button"
                key={`${sample.subject}-${idx}`}
                className={`scenario-card ${state.className} ${isActive ? 'active' : ''}`}
                style={{ '--scenario-color': state.color }}
                onClick={() => runPrediction(idx)}
                disabled={loading}
                aria-pressed={isActive}
              >
                <span className="scenario-accent" />
                <div className="scenario-card-top">
                  <span className="scenario-icon"><Icon name={scenario.icon} size={30} /></span>
                  <div>
                    <strong>{scenario.title}</strong>
                    <small>Sample scenario {String(idx + 1).padStart(2, '0')}</small>
                  </div>
                </div>
                <p>{scenario.description}</p>
                <span className="participant-code">
                  <span>WESAD dataset ID</span>
                  <strong>{sample.subject}</strong>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      <section className="history-panel">
        <div className="history-header">
          <div>
            <span className="eyebrow">Prediction history</span>
            <p>This session only</p>
          </div>
          <div className="history-actions">
            <button type="button" className="secondary-action" onClick={undoLast} disabled={history.length === 0}>
              <Icon name="undo" size={17} />
              Undo last
            </button>
            <button type="button" className="secondary-action danger" onClick={resetHistory} disabled={history.length === 0}>
              <Icon name="trash" size={17} />
              Clear history
            </button>
          </div>
        </div>

        {history.length === 0 ? (
          <div className="history-empty">
            <Icon name="history" size={28} />
            <span>Your recent predictions will appear here after you select a scenario.</span>
          </div>
        ) : (
          <div className="history-chart" aria-label="Prediction probability history chart">
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={history} margin={{ top: 10, right: 10, left: -12, bottom: 0 }}>
                <CartesianGrid stroke="#24302e" strokeDasharray="3 4" />
                <XAxis dataKey="time" stroke="#76918a" fontSize={11} tickLine={false} />
                <YAxis domain={[0, 1]} stroke="#76918a" fontSize={11} tickLine={false} />
                <ReferenceLine y={0.5} stroke="#32413d" strokeDasharray="4 4" />
                <Tooltip
                  formatter={(value) => `${(value * 100).toFixed(1)}%`}
                  contentStyle={{
                    background: '#0d1518',
                    border: '1px solid #26343a',
                    borderRadius: 10,
                    fontFamily: 'JetBrains Mono',
                    fontSize: 12,
                  }}
                  labelStyle={{ color: '#9fb1ad' }}
                />
                <Legend wrapperStyle={{ fontSize: 12, fontFamily: 'JetBrains Mono' }} />
                <Line type="monotone" dataKey="baseline_prob" stroke={STATE_META.Baseline.color} strokeWidth={2} dot={{ r: 3 }} name="Calm" />
                <Line type="monotone" dataKey="stress_prob" stroke={STATE_META.Stress.color} strokeWidth={2} dot={{ r: 3 }} name="Stress" />
                <Line type="monotone" dataKey="amusement_prob" stroke={STATE_META.Amusement.color} strokeWidth={2} dot={{ r: 3 }} name="Positive emotion" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {insights && (
        <section className="insights-panel">
          <div className="section-heading-row compact">
            <div>
              <span className="eyebrow">Model insight</span>
              <p>
                Global contribution of each sensor group across the trained{' '}
                {activeModelMeta.displayName} model. This does not explain an
                individual prediction.
              </p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={insights.by_sensor} margin={{ left: 0, right: 12, top: 6 }}>
              <CartesianGrid stroke="#24302e" strokeDasharray="3 4" />
              <XAxis dataKey="sensor" stroke="#76918a" fontSize={12} tickLine={false} />
              <YAxis stroke="#76918a" fontSize={11} tickLine={false} unit="%" />
              <Tooltip
                formatter={(value) => `${value.toFixed(1)}%`}
                contentStyle={{
                  background: '#0d1518',
                  border: '1px solid #26343a',
                  borderRadius: 10,
                  fontFamily: 'JetBrains Mono',
                  fontSize: 12,
                }}
              />
              <Bar dataKey="importance_pct" radius={[5, 5, 0, 0]}>
                {insights.by_sensor.map((entry, index) => (
                  <Cell key={`${entry.sensor}-${index}`} fill={index % 2 === 0 ? '#2dd4bf' : '#39a99e'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      )}

      <footer className="dashboard-footer">
  Research prototype—not a diagnostic tool.{' '}
  {activeModelMeta.displayName} model · accuracy{' '}
  {activeModelMeta.accuracy.toFixed(1)}% · macro F1{' '}
  {activeModelMeta.f1.toFixed(1)}%.
</footer>
    </div>
  );
}

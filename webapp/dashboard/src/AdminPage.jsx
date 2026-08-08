import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import './Admin.css';
import { useAuth } from './AuthContext';
import { API_BASE } from './api';

const LABELS = {
  student: 'Student',
  employed: 'Employed',
  self_employed: 'Self-employed',
  researcher: 'Researcher / academic',
  not_working: 'Not currently working',
  other: 'Other',
  study_stress: 'Study stress',
  work_stress: 'Work stress',
  general_wellbeing: 'General wellbeing',
  research_demo: 'Research / demonstration',
  none: 'No wearable',
  smartwatch: 'Smartwatch / fitness tracker',
  chest_sensor: 'Chest-worn sensor',
};

function formatDate(value) {
  if (!value) return 'Never';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString([], {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function escapeCsvValue(value) {
  let text = String(value ?? '');

  // Prevent spreadsheet programs from interpreting user data as a formula.
  if (/^[=+\-@\t\r]/.test(text)) {
    text = `'${text}`;
  }

  return `"${text.replace(/"/g, '""')}"`;
}

function predictionResult(record) {
  const expected = String(record.expected_label || '')
    .trim()
    .toLowerCase();

  const predicted = String(record.predicted_label || '')
    .trim()
    .toLowerCase();

  if (!expected) {
    return 'Not available';
  }

  return expected === predicted ? 'Correct' : 'Incorrect';
}

function formatModelName(modelName) {
  if (modelName === 'random_forest') return 'Random Forest';
  if (modelName === 'boost_forest') return 'Boost Forest';
  return 'XGBoost';
}

function SummaryList({ title, rows }) {
  const maximum = Math.max(
    ...(rows || []).map((row) => row.count),
    1,
  );

  return (
    <section className="admin-breakdown-card">
      <h3>{title}</h3>

      <div className="admin-breakdown-list">
        {(rows || []).map((row) => (
          <div className="admin-breakdown-row" key={row.name}>
            <div className="admin-breakdown-label">
              <span>{LABELS[row.name] || row.name}</span>
              <strong>{row.count}</strong>
            </div>

            <div className="admin-breakdown-track" aria-hidden="true">
              <span
                style={{
                  width: `${Math.max(
                    (row.count / maximum) * 100,
                    4,
                  )}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function AdminPage({ onBack }) {
  const { user, authHeader, logout } = useAuth();

  const [overview, setOverview] = useState(null);
  const [users, setUsers] = useState([]);
  const [predictions, setPredictions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  const [predictionSearch, setPredictionSearch] = useState('');
  const [modelFilter, setModelFilter] = useState('all');
  const [resultFilter, setResultFilter] = useState('all');
  const [classFilter, setClassFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  useEffect(() => {
    let active = true;

    setLoading(true);
    setError('');

    Promise.all([
      axios.get(`${API_BASE}/admin/overview`, {
        headers: authHeader,
        timeout: 30000,
      }),
      axios.get(`${API_BASE}/admin/users?limit=500`, {
        headers: authHeader,
        timeout: 30000,
      }),
      axios.get(`${API_BASE}/admin/predictions?limit=500`, {
        headers: authHeader,
        timeout: 30000,
      }),
    ])
      .then(
        ([overviewResponse, usersResponse, predictionsResponse]) => {
          if (!active) return;

          setOverview(overviewResponse.data);
          setUsers(usersResponse.data.users || []);
          setPredictions(predictionsResponse.data.predictions || []);
        },
      )
      .catch((requestError) => {
        if (!active) return;

        if (requestError.response?.status === 401) {
          logout();
          return;
        }

        setError(
          requestError.response?.data?.error ||
            'User analytics could not be loaded.',
        );
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [authHeader, logout]);

  const filteredUsers = useMemo(() => {
    const term = search.trim().toLowerCase();

    if (!term) {
      return users;
    }

    return users.filter((record) =>
      [
        record.name,
        record.email,
        record.occupation,
        LABELS[record.user_type] || record.user_type,
        LABELS[record.primary_goal] || record.primary_goal,
      ].some((value) =>
        String(value || '').toLowerCase().includes(term),
      ),
    );
  }, [search, users]);

  const filteredPredictions = useMemo(() => {
    const searchTerm = predictionSearch.trim().toLowerCase();

    return predictions.filter((record) => {
      const modelMatches =
        modelFilter === 'all' || record.model_name === modelFilter;

      const predictedClass = String(record.predicted_label || '')
        .trim()
        .toLowerCase();

      const classMatches =
        classFilter === 'all' || predictedClass === classFilter;

      const result = predictionResult(record).toLowerCase();
      const resultMatches =
        resultFilter === 'all' || result === resultFilter;

      const searchableValues = [
        record.user_name,
        record.user_email,
        record.sample_id,
        record.source_participant_id,
        record.model_name,
        formatModelName(record.model_name),
        record.expected_label,
        record.predicted_label,
        record.comparison_id,
      ];

      const searchMatches =
        !searchTerm ||
        searchableValues.some((value) =>
          String(value || '').toLowerCase().includes(searchTerm),
        );

      const createdAt = record.created_at
        ? new Date(record.created_at)
        : null;

      const validCreatedAt =
        createdAt && !Number.isNaN(createdAt.getTime());

      const fromDate = dateFrom
        ? new Date(`${dateFrom}T00:00:00`)
        : null;

      const toDate = dateTo
        ? new Date(`${dateTo}T23:59:59.999`)
        : null;

      const dateMatches =
        (!fromDate || (validCreatedAt && createdAt >= fromDate)) &&
        (!toDate || (validCreatedAt && createdAt <= toDate));

      return (
        modelMatches &&
        classMatches &&
        resultMatches &&
        searchMatches &&
        dateMatches
      );
    });
  }, [
    predictions,
    predictionSearch,
    modelFilter,
    resultFilter,
    classFilter,
    dateFrom,
    dateTo,
  ]);

  const exportPredictionsCsv = () => {
    if (!filteredPredictions.length) {
      return;
    }

    const headers = [
      'User',
      'Email',
      'Scenario',
      'WESAD participant',
      'Model',
      'Expected class',
      'Predicted class',
      'Result',
      'Confidence (%)',
      'Processing time (ms)',
      'Comparison ID',
      'Created time',
    ];

    const rows = filteredPredictions.map((record) => [
      record.user_name || '',
      record.user_email || '',
      record.sample_id || '',
      record.source_participant_id || '',
      formatModelName(record.model_name),
      record.expected_label || '',
      record.predicted_label || '',
      predictionResult(record),
      ((Number(record.confidence) || 0) * 100).toFixed(1),
      record.processing_time_ms === null ||
      record.processing_time_ms === undefined
        ? ''
        : Number(record.processing_time_ms).toFixed(3),
      record.comparison_id || '',
      record.created_at ? new Date(record.created_at).toISOString() : '',
    ]);

    const csvContent = [headers, ...rows]
      .map((row) =>
        row.map((value) => escapeCsvValue(value)).join(','),
      )
      .join('\n');

    const csvBlob = new Blob([`\uFEFF${csvContent}`], {
      type: 'text/csv;charset=utf-8;',
    });

    const downloadUrl = URL.createObjectURL(csvBlob);
    const downloadLink = document.createElement('a');

    downloadLink.href = downloadUrl;
    downloadLink.download = `prediction-history-${
      new Date().toISOString().split('T')[0]
    }.csv`;

    document.body.appendChild(downloadLink);
    downloadLink.click();
    downloadLink.remove();
    URL.revokeObjectURL(downloadUrl);
  };

  if (!user?.is_admin) {
    return (
      <main className="admin-page">
        <section className="admin-empty-card">
          <h1>Administrator access required</h1>

          <button
            type="button"
            className="admin-primary-button"
            onClick={onBack}
          >
            Back to dashboard
          </button>
        </section>
      </main>
    );
  }

  const totals = overview?.totals || {};

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div>
          <span className="admin-eyebrow">
            Private administrator area
          </span>

          <h1>User and usage analytics</h1>

          <p>
            Account information is loaded from the server database.
            Password hashes are never displayed.
          </p>
        </div>

        <div className="admin-header-actions">
          <span
            className={`admin-database-badge ${
              overview?.database?.location || ''
            }`}
          >
            {overview?.database?.location === 'hosted'
              ? 'Hosted PostgreSQL'
              : 'Local SQLite'}
          </span>

          <button
            type="button"
            className="admin-secondary-button"
            onClick={onBack}
          >
            Back to dashboard
          </button>
        </div>
      </header>

      {loading && (
        <section className="admin-status-card">
          Loading user analytics…
        </section>
      )}

      {error && (
        <section className="admin-status-card error" role="alert">
          {error}
        </section>
      )}

      {!loading && !error && overview && (
        <>
          <section
            className="admin-metrics-grid"
            aria-label="Account summary"
          >
            <article>
              <span>Total users</span>
              <strong>{totals.users || 0}</strong>
              <small>{totals.active_users || 0} active accounts</small>
            </article>

            <article>
              <span>New users</span>
              <strong>{totals.registrations_7d || 0}</strong>
              <small>
                {totals.registrations_30d || 0} in the last 30 days
              </small>
            </article>

            <article>
              <span>Complete profiles</span>
              <strong>{totals.complete_profiles || 0}</strong>
              <small>Routine, goal and device provided</small>
            </article>

            <article>
              <span>Predictions made</span>
              <strong>{totals.predictions || 0}</strong>
              <small>Saved to prediction history</small>
            </article>
          </section>

          <section className="admin-breakdown-grid">
            <SummaryList
              title="Users by current routine"
              rows={overview.by_user_type}
            />
            <SummaryList
              title="Users by main goal"
              rows={overview.by_primary_goal}
            />
            <SummaryList
              title="Users by wearable access"
              rows={overview.by_wearable_device}
            />
          </section>

          <section className="admin-table-panel">
            <div className="admin-table-heading">
              <div>
                <span className="admin-eyebrow">Registered accounts</span>
                <h2>
                  {filteredUsers.length} user
                  {filteredUsers.length === 1 ? '' : 's'} shown
                </h2>
              </div>

              <label>
                <span>Search users</span>
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Name, email, occupation…"
                />
              </label>
            </div>

            <div className="admin-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Age</th>
                    <th>Context</th>
                    <th>Goal</th>
                    <th>Wearable</th>
                    <th>Logins</th>
                    <th>Joined</th>
                    <th>Last login</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredUsers.map((record) => (
                    <tr key={record.id}>
                      <td>
                        <strong>{record.name}</strong>
                        <span>{record.email}</span>
                      </td>
                      <td>{record.age || '—'}</td>
                      <td>
                        <strong>
                          {LABELS[record.user_type] ||
                            record.user_type ||
                            '—'}
                        </strong>
                        <span>
                          {record.occupation || 'No occupation provided'}
                        </span>
                      </td>
                      <td>
                        {LABELS[record.primary_goal] ||
                          record.primary_goal ||
                          '—'}
                      </td>
                      <td>
                        {LABELS[record.wearable_device] ||
                          record.wearable_device ||
                          '—'}
                      </td>
                      <td>{record.login_count || 0}</td>
                      <td>{formatDate(record.created_at)}</td>
                      <td>{formatDate(record.last_login_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="admin-table-panel compact">
            <div className="admin-table-heading">
              <div>
                <span className="admin-eyebrow">Prediction history</span>
                <h2>
                  {filteredPredictions.length} prediction
                  {filteredPredictions.length === 1 ? '' : 's'} shown
                </h2>
              </div>

              <button
                type="button"
                className="admin-primary-button"
                onClick={exportPredictionsCsv}
                disabled={!filteredPredictions.length}
              >
                Export CSV
              </button>
            </div>

            <div className="admin-prediction-filters">
              <label>
                <span>Search predictions</span>
                <input
                  type="search"
                  value={predictionSearch}
                  onChange={(event) =>
                    setPredictionSearch(event.target.value)
                  }
                  placeholder="User, scenario, participant…"
                />
              </label>

              <label>
                <span>Model</span>
                <select
                  value={modelFilter}
                  onChange={(event) => setModelFilter(event.target.value)}
                >
                  <option value="all">All models</option>
                  <option value="xgboost">XGBoost</option>
                  <option value="random_forest">Random Forest</option>
                  <option value="boost_forest">Boost Forest</option>
                </select>
              </label>

              <label>
                <span>Result</span>
                <select
                  value={resultFilter}
                  onChange={(event) => setResultFilter(event.target.value)}
                >
                  <option value="all">All results</option>
                  <option value="correct">Correct</option>
                  <option value="incorrect">Incorrect</option>
                </select>
              </label>

              <label>
                <span>Predicted class</span>
                <select
                  value={classFilter}
                  onChange={(event) => setClassFilter(event.target.value)}
                >
                  <option value="all">All classes</option>
                  <option value="baseline">Baseline</option>
                  <option value="stress">Stress</option>
                  <option value="amusement">Amusement</option>
                </select>
              </label>

              <label>
                <span>From date</span>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(event) => setDateFrom(event.target.value)}
                />
              </label>

              <label>
                <span>To date</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(event) => setDateTo(event.target.value)}
                />
              </label>

              <button
                type="button"
                className="admin-secondary-button"
                onClick={() => {
                  setPredictionSearch('');
                  setModelFilter('all');
                  setResultFilter('all');
                  setClassFilter('all');
                  setDateFrom('');
                  setDateTo('');
                }}
              >
                Clear filters
              </button>
            </div>

            <div className="admin-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Scenario</th>
                    <th>WESAD ID</th>
                    <th>Model</th>
                    <th>Expected</th>
                    <th>Predicted</th>
                    <th>Result</th>
                    <th>Confidence</th>
                    <th>Processing time</th>
                    <th>Time</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredPredictions.map((record) => (
                    <tr key={record.id}>
                      <td>
                        <strong>{record.user_name}</strong>
                        <span>{record.user_email}</span>
                      </td>
                      <td>{record.sample_id || '—'}</td>
                      <td>{record.source_participant_id || '—'}</td>
                      <td>{formatModelName(record.model_name)}</td>
                      <td>{record.expected_label || '—'}</td>
                      <td>{record.predicted_label || '—'}</td>
                      <td>{predictionResult(record)}</td>
                      <td>
                        {Math.round(
                          (Number(record.confidence) || 0) * 100,
                        )}
                        %
                      </td>
                      <td>
                        {record.processing_time_ms !== null &&
                        record.processing_time_ms !== undefined &&
                        Number.isFinite(
                          Number(record.processing_time_ms),
                        )
                          ? `${Number(
                              record.processing_time_ms,
                            ).toFixed(3)} ms`
                          : 'Not available'}
                      </td>
                      <td>{formatDate(record.created_at)}</td>
                    </tr>
                  ))}

                  {!filteredPredictions.length && (
                    <tr>
                      <td colSpan={10}>
                        No predictions match the selected filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}

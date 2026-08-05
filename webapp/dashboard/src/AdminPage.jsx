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
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString([], {
    year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

function SummaryList({ title, rows }) {
  const maximum = Math.max(...(rows || []).map((row) => row.count), 1);
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
              <span style={{ width: `${Math.max((row.count / maximum) * 100, 4)}%` }} />
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');

    Promise.all([
      axios.get(`${API_BASE}/admin/overview`, { headers: authHeader, timeout: 30000 }),
      axios.get(`${API_BASE}/admin/users?limit=500`, { headers: authHeader, timeout: 30000 }),
    ])
      .then(([overviewResponse, usersResponse]) => {
        if (!active) return;
        setOverview(overviewResponse.data);
        setUsers(usersResponse.data.users || []);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError.response?.status === 401) logout();
        setError(requestError.response?.data?.error || 'User analytics could not be loaded.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [authHeader, logout]);

  const filteredUsers = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return users;
    return users.filter((record) => [
      record.name,
      record.email,
      record.occupation,
      LABELS[record.user_type] || record.user_type,
      LABELS[record.primary_goal] || record.primary_goal,
    ].some((value) => String(value || '').toLowerCase().includes(term)));
  }, [search, users]);

  if (!user?.is_admin) {
    return (
      <main className="admin-page">
        <section className="admin-empty-card">
          <h1>Administrator access required</h1>
          <button type="button" className="admin-primary-button" onClick={onBack}>Back to dashboard</button>
        </section>
      </main>
    );
  }

  const totals = overview?.totals || {};

  return (
    <main className="admin-page">
      <header className="admin-header">
        <div>
          <span className="admin-eyebrow">Private administrator area</span>
          <h1>User and usage analytics</h1>
          <p>Account information is loaded from the server database. Password hashes are never displayed.</p>
        </div>
        <div className="admin-header-actions">
          <span className={`admin-database-badge ${overview?.database?.location || ''}`}>
            {overview?.database?.location === 'hosted' ? 'Hosted PostgreSQL' : 'Local SQLite'}
          </span>
          <button type="button" className="admin-secondary-button" onClick={onBack}>Back to dashboard</button>
        </div>
      </header>

      {loading && <section className="admin-status-card">Loading user analytics…</section>}
      {error && <section className="admin-status-card error" role="alert">{error}</section>}

      {!loading && !error && overview && (
        <>
          <section className="admin-metrics-grid" aria-label="Account summary">
            <article><span>Total users</span><strong>{totals.users || 0}</strong><small>{totals.active_users || 0} active accounts</small></article>
            <article><span>New users</span><strong>{totals.registrations_7d || 0}</strong><small>{totals.registrations_30d || 0} in the last 30 days</small></article>
            <article><span>Complete profiles</span><strong>{totals.complete_profiles || 0}</strong><small>Routine, goal and device provided</small></article>
            <article><span>Predictions made</span><strong>{totals.predictions || 0}</strong><small>Saved to prediction history</small></article>
          </section>

          <section className="admin-breakdown-grid">
            <SummaryList title="Users by current routine" rows={overview.by_user_type} />
            <SummaryList title="Users by main goal" rows={overview.by_primary_goal} />
            <SummaryList title="Users by wearable access" rows={overview.by_wearable_device} />
          </section>

          <section className="admin-table-panel">
            <div className="admin-table-heading">
              <div>
                <span className="admin-eyebrow">Registered accounts</span>
                <h2>{filteredUsers.length} user{filteredUsers.length === 1 ? '' : 's'} shown</h2>
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
                      <td><strong>{record.name}</strong><span>{record.email}</span></td>
                      <td>{record.age || '—'}</td>
                      <td><strong>{LABELS[record.user_type] || record.user_type || '—'}</strong><span>{record.occupation || 'No occupation provided'}</span></td>
                      <td>{LABELS[record.primary_goal] || record.primary_goal || '—'}</td>
                      <td>{LABELS[record.wearable_device] || record.wearable_device || '—'}</td>
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
                <span className="admin-eyebrow">Recent model use</span>
                <h2>Latest saved predictions</h2>
              </div>
            </div>
            <div className="admin-table-scroll">
              <table>
                <thead><tr><th>User</th><th>Scenario</th><th>WESAD ID</th><th>Expected</th><th>Predicted</th><th>Confidence</th><th>Time</th></tr></thead>
                <tbody>
                  {(overview.recent_predictions || []).map((record) => (
                    <tr key={record.id}>
                      <td><strong>{record.user_name}</strong><span>{record.user_email}</span></td>
                      <td>{record.sample_id || '—'}</td>
                      <td>{record.source_participant_id || '—'}</td>
                      <td>{record.expected_label || '—'}</td>
                      <td>{record.predicted_label}</td>
                      <td>{Math.round((record.confidence || 0) * 100)}%</td>
                      <td>{formatDate(record.created_at)}</td>
                    </tr>
                  ))}
                  {!(overview.recent_predictions || []).length && (
                    <tr><td colSpan="7">No predictions have been recorded yet.</td></tr>
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

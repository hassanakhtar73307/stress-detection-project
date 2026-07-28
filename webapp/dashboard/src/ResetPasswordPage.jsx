import { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:5000';

export default function ResetPasswordPage({ onSwitchToLogin }) {
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/reset-password`, { token, new_password: newPassword });
      setMessage(res.data.message);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not reset password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-panel">
      <h1 className="auth-title">Enter reset code</h1>
      <p className="auth-hint">
        Check the Flask server console window (this project has no live email server configured) --
        the reset code was printed there.
      </p>
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Reset code
          <input type="text" value={token} onChange={(e) => setToken(e.target.value)} required />
        </label>
        <label>
          New password
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={6} />
        </label>
        {error && <p className="auth-error">{error}</p>}
        {message && <p className="auth-success">{message}</p>}
        <button type="submit" disabled={loading}>{loading ? 'Resetting...' : 'Reset password'}</button>
      </form>
      <p className="auth-switch">
        <button type="button" className="link-btn" onClick={onSwitchToLogin}>← Back to sign in</button>
      </p>
    </div>
  );
}

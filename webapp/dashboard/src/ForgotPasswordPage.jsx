import { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:5000';

export default function ForgotPasswordPage({ onSwitchToLogin, onGotCode }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/forgot-password`, { email });
      setMessage(res.data.message);
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-panel">
      <h1 className="auth-title">Reset your password</h1>
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        {error && <p className="auth-error">{error}</p>}
        {message && <p className="auth-success">{message}</p>}
        <button type="submit" disabled={loading}>{loading ? 'Sending...' : 'Send reset code'}</button>
      </form>
      <p className="auth-switch">
        Already have a code?{' '}
        <button type="button" className="link-btn" onClick={onGotCode}>Enter it here</button>
      </p>
      <p className="auth-switch">
        <button type="button" className="link-btn" onClick={onSwitchToLogin}>← Back to sign in</button>
      </p>
    </div>
  );
}

import { useState } from 'react';
import axios from 'axios';
import AuthLayout from './AuthLayout';
import { API_BASE } from './api';

export default function ForgotPasswordPage({ onSwitchToLogin, onGotCode }) {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/forgot-password`, { email });
      setMessage(response.data.message);
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'We could not start the reset process.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Account recovery"
      title="Reset your password"
      description="Enter your account email to generate a secure reset code."
      footer={<button type="button" className="text-action" onClick={onSwitchToLogin}>← Return to sign in</button>}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="field-group" htmlFor="forgot-email">
          <span className="field-label">Email address</span>
          <input id="forgot-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" autoComplete="email" required />
        </label>
        {error && <p className="form-message error" role="alert">{error}</p>}
        {message && <p className="form-message success" role="status">{message}</p>}
        <button type="submit" className="primary-button" disabled={loading}>{loading ? 'Generating code…' : 'Generate reset code'}</button>
      </form>
      <p className="secondary-copy">Already have a reset code? <button type="button" className="text-action" onClick={onGotCode}>Enter it here</button></p>
    </AuthLayout>
  );
}

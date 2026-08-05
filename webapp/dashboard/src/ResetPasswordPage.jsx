import { useState } from 'react';
import axios from 'axios';
import AuthLayout from './AuthLayout';
import PasswordField from './PasswordField';
import { API_BASE } from './api';

export default function ResetPasswordPage({ onSwitchToLogin }) {
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setMessage(null);

    if (newPassword !== confirmPassword) {
      setError('The passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/reset-password`, { token, new_password: newPassword });
      setMessage(response.data.message);
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'We could not reset your password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Secure password reset"
      title="Create a new password"
      description="Enter the reset code and choose a new password for your account."
      footer={<button type="button" className="text-action" onClick={onSwitchToLogin}>← Return to sign in</button>}
    >
      <div className="prototype-notice">
        During local testing, the reset code appears in the Flask terminal because no email service is configured.
      </div>
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="field-group" htmlFor="reset-code">
          <span className="field-label">Reset code</span>
          <input id="reset-code" value={token} onChange={(event) => setToken(event.target.value)} placeholder="Paste the code from the Flask terminal" required />
        </label>
        <PasswordField id="reset-password" label="New password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="At least 8 characters" autoComplete="new-password" minLength={8} />
        <PasswordField id="reset-confirm-password" label="Confirm new password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Re-enter your password" autoComplete="new-password" minLength={8} />
        {error && <p className="form-message error" role="alert">{error}</p>}
        {message && <p className="form-message success" role="status">{message}</p>}
        <button type="submit" className="primary-button" disabled={loading}>{loading ? 'Updating password…' : 'Update password'}</button>
      </form>
    </AuthLayout>
  );
}

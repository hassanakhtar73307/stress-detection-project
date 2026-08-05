import { useState } from 'react';
import { useAuth } from './AuthContext';
import AuthLayout from './AuthLayout';
import PasswordField from './PasswordField';

export default function LoginPage({ onSwitchToRegister, onForgotPassword }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email, password });
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'We could not sign you in. Check your details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Secure account access"
      title="Welcome back"
      description="Sign in to continue to your stress classification dashboard."
      footer={(
        <p>
          New to Stress Monitor?{' '}
          <button type="button" className="text-action" onClick={onSwitchToRegister}>Create an account</button>
        </p>
      )}
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <label className="field-group" htmlFor="login-email">
          <span className="field-label">Email address</span>
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </label>

        <PasswordField
          id="login-password"
          label="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter your password"
          autoComplete="current-password"
        />

        <div className="form-inline-actions">
          <span className="secure-copy">Encrypted sign-in</span>
          <button type="button" className="text-action" onClick={onForgotPassword}>Forgot password?</button>
        </div>

        {error && <p className="form-message error" role="alert">{error}</p>}

        <button type="submit" className="primary-button" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in to dashboard'}
        </button>
      </form>
    </AuthLayout>
  );
}

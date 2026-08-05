import { useMemo, useState } from 'react';
import { useAuth } from './AuthContext';
import AuthLayout from './AuthLayout';
import PasswordField from './PasswordField';

const INITIAL_FORM = {
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
  age: '',
  occupation: '',
  userType: '',
  primaryGoal: '',
  wearableDevice: '',
  researchNoticeAcknowledged: false,
};

export default function RegisterPage({ onSwitchToLogin }) {
  const { register } = useAuth();
  const [form, setForm] = useState(INITIAL_FORM);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const passwordChecks = useMemo(() => ({
    length: form.password.length >= 8,
    letter: /[A-Za-z]/.test(form.password),
    number: /\d/.test(form.password),
    match: form.password.length > 0 && form.password === form.confirmPassword,
  }), [form.confirmPassword, form.password]);

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (!passwordChecks.length || !passwordChecks.letter || !passwordChecks.number) {
      setError('Use at least 8 characters with one letter and one number.');
      return;
    }
    if (!passwordChecks.match) {
      setError('The passwords do not match.');
      return;
    }
    if (!form.researchNoticeAcknowledged) {
      setError('Please confirm that you understand the research-prototype notice.');
      return;
    }

    setLoading(true);
    try {
      await register({
        name: form.name,
        email: form.email,
        password: form.password,
        age: form.age || null,
        occupation: form.occupation,
        user_type: form.userType,
        primary_goal: form.primaryGoal,
        wearable_device: form.wearableDevice,
        research_notice_acknowledged: form.researchNoticeAcknowledged,
      });
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'We could not create your account. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Personalised account setup"
      title="Create your profile"
      description="Tell us only the practical context needed to make the dashboard easier to understand."
      footer={(
        <p>
          Already registered?{' '}
          <button type="button" className="text-action" onClick={onSwitchToLogin}>Sign in</button>
        </p>
      )}
    >
      <form onSubmit={handleSubmit} className="auth-form registration-form">
        <div className="form-section-heading">
          <span>01</span>
          <div><h3>Account details</h3><p>Used for secure access and account recovery.</p></div>
        </div>

        <div className="field-grid two-columns">
          <label className="field-group" htmlFor="register-name">
            <span className="field-label">Full name</span>
            <input id="register-name" value={form.name} onChange={(event) => update('name', event.target.value)} autoComplete="name" placeholder="Your full name" required />
          </label>
          <label className="field-group" htmlFor="register-email">
            <span className="field-label">Email address</span>
            <input id="register-email" type="email" value={form.email} onChange={(event) => update('email', event.target.value)} autoComplete="email" placeholder="you@example.com" required />
          </label>
        </div>

        <div className="field-grid two-columns">
          <PasswordField
            id="register-password"
            label="Create password"
            value={form.password}
            onChange={(event) => update('password', event.target.value)}
            placeholder="At least 8 characters"
            autoComplete="new-password"
            minLength={8}
          />
          <PasswordField
            id="register-confirm-password"
            label="Confirm password"
            value={form.confirmPassword}
            onChange={(event) => update('confirmPassword', event.target.value)}
            placeholder="Re-enter your password"
            autoComplete="new-password"
            minLength={8}
          />
        </div>

        <div className="password-requirements" aria-label="Password requirements">
          <span className={passwordChecks.length ? 'met' : ''}>8+ characters</span>
          <span className={passwordChecks.letter ? 'met' : ''}>One letter</span>
          <span className={passwordChecks.number ? 'met' : ''}>One number</span>
          <span className={passwordChecks.match ? 'met' : ''}>Passwords match</span>
        </div>

        <div className="form-section-heading">
          <span>02</span>
          <div><h3>Your context</h3><p>This personalises explanations; it does not change the model prediction.</p></div>
        </div>

        <div className="field-grid two-columns">
          <label className="field-group" htmlFor="register-age">
            <span className="field-label">Age <em>Optional</em></span>
            <input id="register-age" type="number" value={form.age} onChange={(event) => update('age', event.target.value)} min="16" max="120" placeholder="e.g. 24" />
          </label>
          <label className="field-group" htmlFor="register-occupation">
            <span className="field-label">Occupation <em>Optional</em></span>
            <input id="register-occupation" value={form.occupation} onChange={(event) => update('occupation', event.target.value)} placeholder="e.g. Student, Designer" autoComplete="organization-title" />
          </label>
        </div>

        <div className="field-grid two-columns">
          <label className="field-group" htmlFor="register-user-type">
            <span className="field-label">Current routine</span>
            <select id="register-user-type" value={form.userType} onChange={(event) => update('userType', event.target.value)} required>
              <option value="">Select one</option>
              <option value="student">Student</option>
              <option value="employed">Employed</option>
              <option value="self_employed">Self-employed</option>
              <option value="researcher">Researcher / academic</option>
              <option value="not_working">Not currently working</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label className="field-group" htmlFor="register-primary-goal">
            <span className="field-label">Main reason for using the app</span>
            <select id="register-primary-goal" value={form.primaryGoal} onChange={(event) => update('primaryGoal', event.target.value)} required>
              <option value="">Select one</option>
              <option value="study_stress">Understand study stress</option>
              <option value="work_stress">Understand work stress</option>
              <option value="general_wellbeing">Explore general wellbeing</option>
              <option value="research_demo">Research or demonstration</option>
              <option value="other">Other</option>
            </select>
          </label>
        </div>

        <label className="field-group" htmlFor="register-device">
          <span className="field-label">Sensor or wearable access</span>
          <select id="register-device" value={form.wearableDevice} onChange={(event) => update('wearableDevice', event.target.value)} required>
            <option value="">Select one</option>
            <option value="none">No wearable — use sample data</option>
            <option value="smartwatch">Smartwatch / fitness tracker</option>
            <option value="chest_sensor">Chest-worn physiological sensor</option>
            <option value="other">Other sensor</option>
          </select>
        </label>

        <label className="consent-row" htmlFor="research-notice">
          <input
            id="research-notice"
            type="checkbox"
            checked={form.researchNoticeAcknowledged}
            onChange={(event) => update('researchNoticeAcknowledged', event.target.checked)}
          />
          <span>
            I understand that Stress Monitor is a research prototype and its classifications are not medical advice or a diagnosis.
          </span>
        </label>

        <div className="privacy-callout">
          <strong>Privacy-conscious setup</strong>
          <p>We do not ask for diagnoses, medication, exact location, or other unnecessary health information.</p>
        </div>

        {error && <p className="form-message error" role="alert">{error}</p>}

        <button type="submit" className="primary-button" disabled={loading}>
          {loading ? 'Creating your account…' : 'Create account and continue'}
        </button>
      </form>
    </AuthLayout>
  );
}

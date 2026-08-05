import { useMemo, useState } from 'react';
import { useAuth } from './AuthContext';

const USER_TYPE_LABELS = {
  student: 'Student',
  employed: 'Employed',
  self_employed: 'Self-employed',
  researcher: 'Researcher / academic',
  not_working: 'Not currently working',
  other: 'Other',
};

const GOAL_LABELS = {
  study_stress: 'Understand study stress',
  work_stress: 'Understand work stress',
  general_wellbeing: 'Explore general wellbeing',
  research_demo: 'Research or demonstration',
  other: 'Other',
};

const DEVICE_LABELS = {
  none: 'Sample data only',
  smartwatch: 'Smartwatch / fitness tracker',
  chest_sensor: 'Chest-worn physiological sensor',
  other: 'Other sensor',
};

export default function ProfilePage({ onBack }) {
  const { user, updateProfile, logout } = useAuth();
  const [form, setForm] = useState({
    name: user?.name || '',
    age: user?.age ?? '',
    occupation: user?.occupation || '',
    userType: user?.user_type || '',
    primaryGoal: user?.primary_goal || '',
    wearableDevice: user?.wearable_device || '',
  });
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const initials = useMemo(() => {
    const parts = (form.name || user?.email || 'User').trim().split(/\s+/).filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]?.toUpperCase()).join('') || 'U';
  }, [form.name, user?.email]);

  const completion = useMemo(() => {
    const values = [form.name, form.age, form.occupation, form.userType, form.primaryGoal, form.wearableDevice];
    return Math.round((values.filter((value) => value !== '' && value !== null && value !== undefined).length / values.length) * 100);
  }, [form]);

  const update = (key, value) => {
    setSaved(false);
    setForm((current) => ({ ...current, [key]: value }));
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setError(null);
    setSaved(false);
    setLoading(true);
    try {
      await updateProfile({
        name: form.name,
        age: form.age || null,
        occupation: form.occupation,
        user_type: form.userType,
        primary_goal: form.primaryGoal,
        wearable_device: form.wearableDevice,
      });
      setSaved(true);
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'We could not save your profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="profile-page">
      <header className="profile-topbar">
        <button type="button" className="back-button" onClick={onBack}>← Back to dashboard</button>
        <div className="profile-topbar-brand">
          <span>Stress Monitor</span>
          <small>Account settings</small>
        </div>
        <button type="button" className="secondary-button compact danger-text" onClick={logout}>Log out</button>
      </header>

      <main className="profile-container">
        <section className="profile-hero">
          <div className="profile-avatar" aria-hidden="true">{initials}</div>
          <div className="profile-identity">
            <span className="auth-eyebrow">Your account</span>
            <h1>{form.name || 'Complete your profile'}</h1>
            <p>{user?.email}</p>
            <div className="profile-tags">
              {form.userType && <span>{USER_TYPE_LABELS[form.userType] || form.userType}</span>}
              {form.primaryGoal && <span>{GOAL_LABELS[form.primaryGoal] || form.primaryGoal}</span>}
              {form.wearableDevice && <span>{DEVICE_LABELS[form.wearableDevice] || form.wearableDevice}</span>}
            </div>
          </div>
          <div className="profile-completion">
            <div className="completion-value">{completion}%</div>
            <p>Profile complete</p>
            <div className="completion-track" aria-label={`${completion}% profile complete`}>
              <span style={{ width: `${completion}%` }} />
            </div>
          </div>
        </section>

        <div className="profile-content-grid">
          <form onSubmit={handleSave} className="profile-form-card">
            <div className="profile-section-header">
              <div><span className="auth-eyebrow">Personal details</span><h2>About you</h2></div>
              <p>Keep your account details accurate and your explanations relevant.</p>
            </div>

            <div className="field-grid two-columns">
              <label className="field-group" htmlFor="profile-name">
                <span className="field-label">Full name</span>
                <input id="profile-name" value={form.name} onChange={(event) => update('name', event.target.value)} autoComplete="name" required />
              </label>
              <label className="field-group" htmlFor="profile-email">
                <span className="field-label">Email address</span>
                <input id="profile-email" value={user?.email || ''} readOnly aria-readonly="true" />
                <small className="field-helper">Email changes are not enabled in this prototype.</small>
              </label>
            </div>

            <div className="field-grid two-columns">
              <label className="field-group" htmlFor="profile-age">
                <span className="field-label">Age <em>Optional</em></span>
                <input id="profile-age" type="number" value={form.age} onChange={(event) => update('age', event.target.value)} min="16" max="120" placeholder="e.g. 24" />
              </label>
              <label className="field-group" htmlFor="profile-occupation">
                <span className="field-label">Occupation <em>Optional</em></span>
                <input id="profile-occupation" value={form.occupation} onChange={(event) => update('occupation', event.target.value)} placeholder="e.g. Student, Designer" />
              </label>
            </div>

            <div className="profile-section-divider" />

            <div className="profile-section-header compact-header">
              <div><span className="auth-eyebrow">Usage preferences</span><h2>How you use Stress Monitor</h2></div>
              <p>These choices personalise wording only. They are not fed into the trained model.</p>
            </div>

            <div className="field-grid two-columns">
              <label className="field-group" htmlFor="profile-user-type">
                <span className="field-label">Current routine</span>
                <select id="profile-user-type" value={form.userType} onChange={(event) => update('userType', event.target.value)}>
                  <option value="">Select one</option>
                  <option value="student">Student</option>
                  <option value="employed">Employed</option>
                  <option value="self_employed">Self-employed</option>
                  <option value="researcher">Researcher / academic</option>
                  <option value="not_working">Not currently working</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label className="field-group" htmlFor="profile-primary-goal">
                <span className="field-label">Main reason for using the app</span>
                <select id="profile-primary-goal" value={form.primaryGoal} onChange={(event) => update('primaryGoal', event.target.value)}>
                  <option value="">Select one</option>
                  <option value="study_stress">Understand study stress</option>
                  <option value="work_stress">Understand work stress</option>
                  <option value="general_wellbeing">Explore general wellbeing</option>
                  <option value="research_demo">Research or demonstration</option>
                  <option value="other">Other</option>
                </select>
              </label>
            </div>

            <label className="field-group" htmlFor="profile-device">
              <span className="field-label">Sensor or wearable access</span>
              <select id="profile-device" value={form.wearableDevice} onChange={(event) => update('wearableDevice', event.target.value)}>
                <option value="">Select one</option>
                <option value="none">No wearable — use sample data</option>
                <option value="smartwatch">Smartwatch / fitness tracker</option>
                <option value="chest_sensor">Chest-worn physiological sensor</option>
                <option value="other">Other sensor</option>
              </select>
            </label>

            {error && <p className="form-message error" role="alert">{error}</p>}
            {saved && <p className="form-message success" role="status">Profile updated successfully.</p>}

            <div className="profile-form-actions">
              <button type="button" className="secondary-button" onClick={onBack}>Cancel</button>
              <button type="submit" className="primary-button fit-content" disabled={loading}>
                {loading ? 'Saving changes…' : 'Save profile changes'}
              </button>
            </div>
          </form>

          <aside className="profile-sidebar">
            <section className="profile-info-card">
              <span className="auth-eyebrow">Profile use</span>
              <h2>What this information does</h2>
              <ul>
                <li>Personalises labels and future onboarding guidance.</li>
                <li>Helps distinguish student, work, and research use cases.</li>
                <li>Records whether you plan to use sample data or a wearable.</li>
              </ul>
            </section>

            <section className="profile-info-card privacy-card">
              <span className="auth-eyebrow">Privacy boundary</span>
              <h2>What we do not request</h2>
              <ul>
                <li>Medical diagnoses or medication details.</li>
                <li>Exact home or workplace location.</li>
                <li>Unnecessary demographic or identity information.</li>
              </ul>
            </section>

            <section className="profile-info-card prototype-card">
              <strong>Research prototype</strong>
              <p>Profile context does not alter the XGBoost prediction. Predictions use the selected 45 physiological features only.</p>
            </section>
          </aside>
        </div>
      </main>
    </div>
  );
}

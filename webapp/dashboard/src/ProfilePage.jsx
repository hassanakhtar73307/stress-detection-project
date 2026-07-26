import { useState } from 'react';
import { useAuth } from './AuthContext';

export default function ProfilePage({ onBack }) {
  const { user, updateProfile, logout } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [age, setAge] = useState(user?.age ?? '');
  const [occupation, setOccupation] = useState(user?.occupation || '');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setLoading(true);
    try {
      await updateProfile({ name, age: age || null, occupation });
      setSaved(true);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not save profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-panel">
      <h1 className="auth-title">My profile</h1>
      <div className="profile-readonly">
        <p><span className="label">Email</span> {user?.email}</p>
      </div>
      <form onSubmit={handleSave} className="auth-form">
        <label>
          Full name
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Age
          <input type="number" value={age} onChange={(e) => setAge(e.target.value)} min="1" max="120" />
        </label>
        <label>
          Occupation
          <input type="text" value={occupation} onChange={(e) => setOccupation(e.target.value)} />
        </label>
        {error && <p className="auth-error">{error}</p>}
        {saved && <p className="auth-success">Profile updated.</p>}
        <button type="submit" disabled={loading}>{loading ? 'Saving...' : 'Save changes'}</button>
      </form>
      <div className="profile-actions">
        <button type="button" className="link-btn" onClick={onBack}>← Back to dashboard</button>
        <button type="button" className="link-btn danger" onClick={logout}>Log out</button>
      </div>
    </div>
  );
}

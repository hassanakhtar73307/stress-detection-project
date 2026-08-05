import { useState } from 'react';

function EyeIcon({ hidden }) {
  return hidden ? (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m3 3 18 18" />
      <path d="M10.6 10.7a2 2 0 0 0 2.7 2.7" />
      <path d="M9.9 4.2A10.6 10.6 0 0 1 12 4c5.5 0 9 5 9 5a15.5 15.5 0 0 1-2.1 2.6" />
      <path d="M6.6 6.7C4.3 8.2 3 10 3 10s3.5 5 9 5c1 0 1.9-.2 2.8-.4" />
    </svg>
  ) : (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

export default function PasswordField({
  id,
  label,
  value,
  onChange,
  placeholder,
  autoComplete,
  required = true,
  minLength,
  helper,
}) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="field-group">
      <label className="field-label" htmlFor={id}>{label}</label>
      <span className="password-control">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((current) => !current)}
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
        >
          <EyeIcon hidden={visible} />
          <span>{visible ? 'Hide' : 'Show'}</span>
        </button>
      </span>
      {helper && <small className="field-helper">{helper}</small>}
    </div>
  );
}

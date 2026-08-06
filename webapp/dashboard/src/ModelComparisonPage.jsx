import { useState } from 'react';
import './ModelComparisonPage.css';
import axios from 'axios';
import samples from './sample_windows.json';
import { useAuth } from './AuthContext';
import { API_BASE } from './api';

const PREDICT_URL = `${API_BASE}/predict`;

const MODEL_META = {
  xgboost: {
    displayName: 'XGBoost',
    status: 'Recommended',
    accuracy: 79.9,
    precision: 68.2,
    recall: 71.3,
    f1: 67.7,
  },
  random_forest: {
    displayName: 'Random Forest',
    status: 'Alternative',
    accuracy: 76.8,
    precision: 64.5,
    recall: 66.2,
    f1: 63.1,
  },
};

export default function ModelComparisonPage({ onBack }) {
  const { authHeader, logout } = useAuth();

  const [selectedIdx, setSelectedIdx] = useState(0);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const compareModels = async () => {
    const sample = samples[selectedIdx];

    setLoading(true);
    setError('');
    setComparison(null);

    try {
      const createPayload = (modelName) => ({
        features: sample.features,
        model_name: modelName,
        sample_id: `comparison_scenario_${String(
          selectedIdx + 1,
        ).padStart(2, '0')}`,
        participant_id: sample.subject,
        expected_label: sample.true_label,
      });

      const [xgboostResponse, randomForestResponse] =
        await Promise.all([
          axios.post(
            PREDICT_URL,
            createPayload('xgboost'),
            {
              headers: authHeader,
              timeout: 60000,
            },
          ),
          axios.post(
            PREDICT_URL,
            createPayload('random_forest'),
            {
              headers: authHeader,
              timeout: 60000,
            },
          ),
        ]);

      setComparison({
        sample,
        xgboost: xgboostResponse.data,
        random_forest: randomForestResponse.data,
      });
    } catch (requestError) {
      if (requestError.response?.status === 401) {
        logout();
        return;
      }

      setError(
        requestError.response?.data?.error ||
          'The model comparison could not be completed.',
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="comparison-page">
      <header className="comparison-header">
        <div>
          <span className="eyebrow">
            Machine-learning evaluation
          </span>
          <h1>Model Comparison</h1>
          <p>
            Run the same 45-feature WESAD sample through
            XGBoost and Random Forest.
          </p>
        </div>

        <button
          type="button"
          className="secondary-action"
          onClick={onBack}
        >
          Back to dashboard
        </button>
      </header>

      <section className="comparison-controls">
        <label htmlFor="comparison-sample">
          Select sample scenario
        </label>

        <select
          id="comparison-sample"
          value={selectedIdx}
          onChange={(event) => {
            setSelectedIdx(Number(event.target.value));
            setComparison(null);
            setError('');
          }}
        >
          {samples.map((sample, index) => (
            <option
              value={index}
              key={`${sample.subject}-${index}`}
            >
              Scenario {String(index + 1).padStart(2, '0')}
              {' — '}
              WESAD {sample.subject}
              {' — '}
              Expected {sample.true_label}
            </option>
          ))}
        </select>

        <button
          type="button"
          className="primary-action"
          onClick={compareModels}
          disabled={loading}
        >
          {loading
            ? 'Comparing models...'
            : 'Compare both models'}
        </button>
      </section>

      {error && (
        <div className="comparison-error">
          {error}
        </div>
      )}

      <section className="comparison-results">
        {Object.entries(MODEL_META).map(
          ([modelName, modelMeta]) => {
            const result = comparison?.[modelName];

            return (
              <article
                className="comparison-model-card"
                key={modelName}
              >
                <div className="comparison-model-heading">
                  <div>
                    <span>{modelMeta.status}</span>
                    <h2>{modelMeta.displayName}</h2>
                  </div>

                  <strong>
                    {modelMeta.accuracy.toFixed(1)}% accuracy
                  </strong>
                </div>

                <div className="comparison-metrics">
                  <div>
                    <span>Precision</span>
                    <strong>
                      {modelMeta.precision.toFixed(1)}%
                    </strong>
                  </div>

                  <div>
                    <span>Recall</span>
                    <strong>
                      {modelMeta.recall.toFixed(1)}%
                    </strong>
                  </div>

                  <div>
                    <span>Macro F1</span>
                    <strong>
                      {modelMeta.f1.toFixed(1)}%
                    </strong>
                  </div>
                </div>

                {result ? (
                  <div className="comparison-prediction">
                    <span>Prediction</span>
                    <h3>{result.predicted_label}</h3>
                    <p>
                      Confidence:{' '}
                      {(result.confidence * 100).toFixed(1)}%
                    </p>

                    <div className="comparison-probabilities">
                      {Object.entries(
                        result.probabilities,
                      ).map(([label, probability]) => (
                        <div key={label}>
                          <span>{label}</span>
                          <strong>
                            {(probability * 100).toFixed(1)}%
                          </strong>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="comparison-placeholder">
                    Run the comparison to view this model’s
                    prediction.
                  </p>
                )}
              </article>
            );
          },
        )}
      </section>
    </div>
  );
}
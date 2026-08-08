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
  boost_forest: {
    displayName: 'Boost Forest',
    status: 'Ensemble',
    accuracy: 80.1,
    precision: 70.5,
    recall: 71.1,
    f1: 67.9,
  },
};

const normaliseLabel = (value) =>
  String(value || '').trim().toLowerCase();

const createComparisonSummary = (comparison) => {
  if (!comparison) {
    return null;
  }

  const {
    sample,
    xgboost,
    random_forest: randomForest,
    boost_forest: boostForest,
    comparisonId,
  } = comparison;

  const expectedLabel = sample.true_label;

  const modelResults = [
    { key: 'xgboost', name: 'XGBoost', result: xgboost },
    {
      key: 'random_forest',
      name: 'Random Forest',
      result: randomForest,
    },
    {
      key: 'boost_forest',
      name: 'Boost Forest',
      result: boostForest,
    },
  ];

  const predictions = modelResults.map((item) => ({
    ...item,
    prediction: item.result.predicted_label,
    confidence: Number(item.result.confidence) || 0,
    processingTime: Number(
      item.result.processing_time_ms,
    ),
    correct:
      normaliseLabel(item.result.predicted_label) ===
      normaliseLabel(expectedLabel),
  }));

  const modelsAgree = predictions.every(
    (item) =>
      normaliseLabel(item.prediction) ===
      normaliseLabel(predictions[0].prediction),
  );

  const finiteTimes = predictions.filter((item) =>
    Number.isFinite(item.processingTime),
  );

  let fastestModel = 'Not available';
  let processingTimeRange = null;

  if (finiteTimes.length === predictions.length) {
    const ordered = [...finiteTimes].sort(
      (a, b) => a.processingTime - b.processingTime,
    );

    fastestModel =
      ordered[0].processingTime ===
      ordered[ordered.length - 1].processingTime
        ? 'Tie'
        : ordered[0].name;

    processingTimeRange =
      ordered[ordered.length - 1].processingTime -
      ordered[0].processingTime;
  }

  const confidenceValues = predictions.map(
    (item) => item.confidence,
  );

  const confidenceRange =
    (Math.max(...confidenceValues) -
      Math.min(...confidenceValues)) *
    100;

  const correctModels = predictions.filter(
    (item) => item.correct,
  );

  let bestModel = 'None';
  let bestReason =
    'None of the three models matched the expected class for this sample.';

  if (correctModels.length > 0) {
    const orderedCorrect = [...correctModels].sort(
      (a, b) => b.confidence - a.confidence,
    );

    bestModel = orderedCorrect[0].name;

    if (correctModels.length === 1) {
      bestReason =
        `${bestModel} was the only model that matched the expected class.`;
    } else {
      bestReason =
        `${bestModel} had the highest confidence among the models that matched the expected class.`;
    }
  }

  const classLabels = [
    'Amusement',
    'Baseline',
    'Stress',
  ];

  const classProbabilityComparisons =
    classLabels.map((label) => {
      const values = modelResults.map((item) => ({
        key: item.key,
        name: item.name,
        percentage: Number(
          (
            (Number(
              item.result.probabilities?.[label],
            ) || 0) * 100
          ).toFixed(1),
        ),
      }));

      const sorted = [...values].sort(
        (a, b) => b.percentage - a.percentage,
      );

      return {
        label,
        values,
        range:
          sorted[0].percentage -
          sorted[sorted.length - 1].percentage,
        highestModel:
          sorted[0].percentage ===
          sorted[sorted.length - 1].percentage
            ? 'Equal'
            : `${sorted[0].name} higher`,
      };
    });

  return {
    comparisonId,
    expectedLabel,
    predictions,
    modelsAgree,
    fastestModel,
    processingTimeRange,
    confidenceRange,
    bestModel,
    bestReason,
    classProbabilityComparisons,
  };
};

export default function ModelComparisonPage({
  onBack,
}) {
  const { authHeader, logout } = useAuth();

  const [selectedIdx, setSelectedIdx] =
    useState(0);

  const [comparison, setComparison] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState('');

  const comparisonSummary =
    createComparisonSummary(comparison);

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

      const comparisonId =
        typeof crypto !== 'undefined' &&
        crypto.randomUUID
          ? crypto.randomUUID()
          : `comparison-${Date.now()}`;

      const [
        xgboostResponse,
        randomForestResponse,
        boostForestResponse,
      ] = await Promise.all([
        axios.post(
          PREDICT_URL,
          {
            ...createPayload('xgboost'),
            comparison_id: comparisonId,
          },
          {
            headers: authHeader,
            timeout: 60000,
          },
        ),

        axios.post(
          PREDICT_URL,
          {
            ...createPayload(
              'random_forest',
            ),
            comparison_id: comparisonId,
          },
          {
            headers: authHeader,
            timeout: 60000,
          },
        ),

        axios.post(
          PREDICT_URL,
          {
            ...createPayload(
              'boost_forest',
            ),
            comparison_id: comparisonId,
          },
          {
            headers: authHeader,
            timeout: 60000,
          },
        ),
      ]);

      setComparison({
        sample,
        comparisonId,
        xgboost: xgboostResponse.data,
        random_forest:
          randomForestResponse.data,
        boost_forest:
          boostForestResponse.data,
      });
    } catch (requestError) {
      if (
        requestError.response?.status === 401
      ) {
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
            XGBoost, Random Forest and Boost Forest.
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
            setSelectedIdx(
              Number(event.target.value),
            );
            setComparison(null);
            setError('');
          }}
        >
          {samples.map((sample, index) => (
            <option
              value={index}
              key={`${sample.subject}-${index}`}
            >
              Scenario{' '}
{String(index + 1).padStart(
  2,
  '0',
)}
{' — '}
WESAD {sample.subject}
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
            : 'Compare all three models'}
        </button>
      </section>

      {error && (
        <div className="comparison-error">
          {error}
        </div>
      )}

      {comparisonSummary && (
        <section className="comparison-summary">
          <div className="comparison-summary-heading">
            <div>
              <span className="eyebrow">
                Comparison result
              </span>

              <h2>Result overview</h2>
            </div>

            <div className="comparison-tracking-id">
              <span>Comparison ID</span>
              <code>
                {
                  comparisonSummary.comparisonId
                }
              </code>
            </div>
          </div>
<div className="comparison-summary-grid">
  <div className="comparison-summary-item">
    <span>Processing speed</span>
    <strong>
      {comparisonSummary.fastestModel === 'Not available'
        ? 'Not available'
        : comparisonSummary.fastestModel === 'Tie'
          ? 'Tie'
          : `${comparisonSummary.fastestModel} faster`}
    </strong>
    <p>
      {comparisonSummary.predictions.map(
        (item, index) => (
          <span key={item.key}>
            {index > 0 && ' · '}
            {item.name}:{' '}
            {Number.isFinite(item.processingTime)
              ? `${item.processingTime.toFixed(3)} ms`
              : 'N/A'}
          </span>
        ),
      )}
      {comparisonSummary.processingTimeRange !== null &&
        ` · Range: ${comparisonSummary.processingTimeRange.toFixed(3)} ms`}
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>Ground truth</span>
    <strong>{comparisonSummary.expectedLabel}</strong>
    <p>
      Known WESAD research label used to evaluate
      the three predictions for this sample.
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>Three-model agreement</span>
    <strong>
      {comparisonSummary.modelsAgree ? 'Yes' : 'No'}
    </strong>
    <p>
      {comparisonSummary.predictions.map(
        (item, index) => (
          <span key={item.key}>
            {index > 0 && ' · '}
            {item.name}: {item.prediction}
          </span>
        ),
      )}
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>Confidence range</span>
    <strong>
      {comparisonSummary.confidenceRange.toFixed(1)}
      {' percentage points'}
    </strong>
    <p>
      Difference between the highest and lowest
      top-class confidence across all three models.
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>Best matching result for this sample</span>
    <strong>{comparisonSummary.bestModel}</strong>
    <p>{comparisonSummary.bestReason}</p>
  </div>
</div>

<div className="class-probability-comparison">
  <div className="class-probability-heading">
    <span className="eyebrow">
      All class probabilities
    </span>
    <h3>
      Amusement, Baseline and Stress comparison
    </h3>
    <p>
      Compare the probability assigned to every
      class by XGBoost, Random Forest and Boost Forest.
    </p>
  </div>

  <div className="class-probability-grid">
    {comparisonSummary.classProbabilityComparisons.map(
      (classResult) => (
        <article
          className="class-probability-card"
          key={classResult.label}
        >
          <h4>{classResult.label}</h4>

          {classResult.values.map((item) => (
            <div key={item.key}>
              <span>{item.name}</span>
              <strong>
                {item.percentage.toFixed(1)}%
              </strong>
            </div>
          ))}

          <div className="class-difference">
            <span>Range</span>
            <strong>
              {classResult.range.toFixed(1)}
              {' percentage points'}
            </strong>
          </div>

          <p>{classResult.highestModel}</p>
        </article>
      ),
    )}
  </div>
</div>
</section>
)}
      <section className="comparison-results">
        {Object.entries(MODEL_META).map(
          ([modelName, modelMeta]) => {
            const result =
              comparison?.[modelName];

            return (
              <article
                className="comparison-model-card"
                key={modelName}
              >
                <div className="comparison-model-heading">
                  <div>
                    <span>
                      {modelMeta.status}
                    </span>

                    <h2>
                      {modelMeta.displayName}
                    </h2>
                  </div>

                  <strong>
                    {modelMeta.accuracy.toFixed(
                      1,
                    )}
                    % accuracy
                  </strong>
                </div>

                <div className="comparison-metrics">
                  <div>
                    <span>Precision</span>

                    <strong>
                      {modelMeta.precision.toFixed(
                        1,
                      )}
                      %
                    </strong>
                  </div>

                  <div>
                    <span>Recall</span>

                    <strong>
                      {modelMeta.recall.toFixed(
                        1,
                      )}
                      %
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

    <h3>
      {result.predicted_label}
    </h3>

    <p>
      Confidence:{' '}
      {(result.confidence * 100).toFixed(1)}
      %
    </p>

    <p>
      Processing time:{' '}
      {Number.isFinite(
        Number(result.processing_time_ms),
      )
        ? `${Number(
            result.processing_time_ms,
          ).toFixed(3)} ms`
        : 'Not available'}
    </p>

    <div className="comparison-probabilities">
      {Object.entries(
        result.probabilities,
      ).map(
        ([label, probability]) => (
          <div key={label}>
            <span>
              {label}
            </span>

            <strong>
              {(probability * 100).toFixed(1)}
              %
            </strong>
          </div>
        ),
      )}
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

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
    comparisonId,
  } = comparison;

  const expectedLabel = sample.true_label;

  const xgboostCorrect =
    normaliseLabel(xgboost.predicted_label) ===
    normaliseLabel(expectedLabel);

  const randomForestCorrect =
    normaliseLabel(randomForest.predicted_label) ===
    normaliseLabel(expectedLabel);

  const modelsAgree =
    normaliseLabel(xgboost.predicted_label) ===
    normaliseLabel(randomForest.predicted_label);

  const xgboostConfidence =
    Number(xgboost.confidence) || 0;

  const randomForestConfidence =
    Number(randomForest.confidence) || 0;

  const confidenceDifference =
    Math.abs(
      xgboostConfidence - randomForestConfidence,
    ) * 100;
    const classLabels = [
  'Amusement',
  'Baseline',
  'Stress',
];

const classProbabilityDifferences =
  classLabels.map((label) => {
    const xgboostProbability =
      Number(
        xgboost.probabilities?.[label],
      ) || 0;

    const randomForestProbability =
      Number(
        randomForest.probabilities?.[label],
      ) || 0;

    const xgboostPercentage =
  Number((xgboostProbability * 100).toFixed(1));

const randomForestPercentage =
  Number((randomForestProbability * 100).toFixed(1));

const difference =
  Math.abs(
    xgboostPercentage -
      randomForestPercentage,
  );

let higherModel = 'Equal';

if (
  xgboostPercentage >
  randomForestPercentage
) {
  higherModel = 'XGBoost higher';
} else if (
  randomForestPercentage >
  xgboostPercentage
) {
  higherModel = 'Random Forest higher';
}

    return {
      label,
      xgboostProbability: xgboostPercentage,
randomForestProbability: randomForestPercentage,
      difference,
      higherModel,
    };
  });

  let betterModel = 'Tie';
  let betterReason =
    'Both models produced equally suitable results.';

  if (xgboostCorrect && !randomForestCorrect) {
    betterModel = 'XGBoost';
    betterReason =
      'XGBoost matched the expected class while Random Forest did not.';
  } else if (
    randomForestCorrect &&
    !xgboostCorrect
  ) {
    betterModel = 'Random Forest';
    betterReason =
      'Random Forest matched the expected class while XGBoost did not.';
  } else if (
    xgboostCorrect &&
    randomForestCorrect
  ) {
    if (
      xgboostConfidence >
      randomForestConfidence
    ) {
      betterModel = 'XGBoost';
      betterReason =
        'Both models were correct, but XGBoost had higher confidence.';
    } else if (
      randomForestConfidence >
      xgboostConfidence
    ) {
      betterModel = 'Random Forest';
      betterReason =
        'Both models were correct, but Random Forest had higher confidence.';
    } else {
      betterModel = 'Tie';
      betterReason =
        'Both models were correct with equal confidence.';
    }
  } else {
    betterModel = 'Neither';
    betterReason =
      'Neither model matched the expected class for this sample.';
  }

  return {
    comparisonId,
    expectedLabel,
    modelsAgree,
    confidenceDifference,
    betterModel,
    betterReason,
    classProbabilityDifferences,
    xgboostPrediction: xgboost.predicted_label,
    randomForestPrediction:
      randomForest.predicted_label,
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
      ]);

      setComparison({
        sample,
        comparisonId,
        xgboost: xgboostResponse.data,
        random_forest:
          randomForestResponse.data,
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
            Run the same 45-feature WESAD
            sample through XGBoost and Random
            Forest.
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
            : 'Compare both models'}
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
    <span>Ground truth</span>

    <strong>
      {comparisonSummary.expectedLabel}
    </strong>

    <p>
      Known research label revealed after both models
      complete their predictions.
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>Model agreement</span>

    <strong>
      {comparisonSummary.modelsAgree ? 'Yes' : 'No'}
    </strong>

    <p>
      XGBoost:{' '}
      {comparisonSummary.xgboostPrediction}
      {' · '}
      Random Forest:{' '}
      {comparisonSummary.randomForestPrediction}
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>
      Top-confidence difference
    </span>

    <strong>
      {comparisonSummary.confidenceDifference.toFixed(1)}
      {' percentage points'}
    </strong>

    <p>
      Difference between each model’s highest prediction
      confidence for this sample.
    </p>
  </div>

  <div className="comparison-summary-item">
    <span>
      Best result for this sample
    </span>

    <strong>
      {comparisonSummary.betterModel}
    </strong>

    <p>
      {comparisonSummary.betterReason}
    </p>
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
      This compares the probability assigned to every
      class by both models, not only the final predicted
      class.
    </p>
  </div>

  <div className="class-probability-grid">
    {comparisonSummary.classProbabilityDifferences.map(
      (classResult) => (
        <article
          className="class-probability-card"
          key={classResult.label}
        >
          <h4>{classResult.label}</h4>

          <div>
            <span>XGBoost</span>

            <strong>
              {classResult.xgboostProbability.toFixed(1)}%
            </strong>
          </div>

          <div>
            <span>Random Forest</span>

            <strong>
              {classResult.randomForestProbability.toFixed(1)}
              %
            </strong>
          </div>

          <div className="class-difference">
            <span>Difference</span>

            <strong>
              {classResult.difference.toFixed(1)}
              {' percentage points'}
            </strong>
          </div>

          <p>{classResult.higherModel}</p>
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
                      {(
                        result.confidence * 100
                      ).toFixed(1)}
                      %
                    </p>

                    <div className="comparison-probabilities">
                      {Object.entries(
                        result.probabilities,
                      ).map(
                        ([
                          label,
                          probability,
                        ]) => (
                          <div key={label}>
                            <span>
                              {label}
                            </span>

                            <strong>
                              {(
                                probability *
                                100
                              ).toFixed(1)}
                              %
                            </strong>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                ) : (
                  <p className="comparison-placeholder">
                    Run the comparison to view
                    this model’s prediction.
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
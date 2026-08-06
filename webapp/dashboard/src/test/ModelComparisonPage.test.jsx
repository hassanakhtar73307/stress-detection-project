import {
  beforeEach,
  describe,
  expect,
  test,
  vi,
} from 'vitest';

import {
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';

import userEvent from '@testing-library/user-event';
import axios from 'axios';

import ModelComparisonPage from '../ModelComparisonPage';


const {
  logoutMock,
  stableAuthHeader,
} = vi.hoisted(() => ({
  logoutMock: vi.fn(),

  stableAuthHeader: {
    Authorization: 'Bearer test-token',
  },
}));


vi.mock('axios', () => ({
  default: {
    post: vi.fn(),
  },
}));


vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    authHeader: stableAuthHeader,
    logout: logoutMock,
  }),
}));


const xgboostResult = {
  prediction_id: 101,
  model_name: 'xgboost',
  model_display_name: 'XGBoost',
  predicted_class: 1,
  predicted_label: 'Baseline',
  confidence: 0.91,
  processing_time_ms: 2.1,
  probabilities: {
    Amusement: 0.03,
    Baseline: 0.91,
    Stress: 0.06,
  },
};


const randomForestResult = {
  prediction_id: 102,
  model_name: 'random_forest',
  model_display_name: 'Random Forest',
  predicted_class: 2,
  predicted_label: 'Stress',
  confidence: 0.76,
  processing_time_ms: 4.6,
  probabilities: {
    Amusement: 0.08,
    Baseline: 0.16,
    Stress: 0.76,
  },
};


describe('ModelComparisonPage', () => {
  beforeEach(() => {
    axios.post.mockReset();
    logoutMock.mockReset();

    vi.stubGlobal('crypto', {
      randomUUID: vi.fn(
        () => 'comparison-test-id',
      ),
    });

    axios.post
      .mockResolvedValueOnce({
        data: xgboostResult,
      })
      .mockResolvedValueOnce({
        data: randomForestResult,
      });
  });


  test(
    'compares both models using one comparison ID',
    async () => {
      const user = userEvent.setup();

      render(
        <ModelComparisonPage
          onBack={vi.fn()}
        />,
      );

      expect(
        screen.getByLabelText(
          'Select sample scenario',
        ),
      ).toHaveValue('0');

      await user.click(
        screen.getByRole('button', {
          name: 'Compare both models',
        }),
      );

      await waitFor(() => {
        expect(
          axios.post,
        ).toHaveBeenCalledTimes(2);
      });

      const firstCall = axios.post.mock.calls[0];
      const secondCall = axios.post.mock.calls[1];

      const firstPayload = firstCall[1];
      const secondPayload = secondCall[1];

      expect(firstPayload.model_name).toBe(
        'xgboost',
      );

      expect(secondPayload.model_name).toBe(
        'random_forest',
      );

      expect(firstPayload.comparison_id).toBe(
        'comparison-test-id',
      );

      expect(secondPayload.comparison_id).toBe(
        'comparison-test-id',
      );

      expect(firstPayload.sample_id).toBe(
        'comparison_scenario_01',
      );

      expect(secondPayload.sample_id).toBe(
        'comparison_scenario_01',
      );

      expect(firstPayload.participant_id).toBe(
        'S16',
      );

      expect(secondPayload.participant_id).toBe(
        'S16',
      );

      expect(firstPayload.expected_label).toBe(
        'Baseline',
      );

      expect(secondPayload.expected_label).toBe(
        'Baseline',
      );

      expect(firstPayload.features).toEqual(
        secondPayload.features,
      );

      expect(firstCall[2]).toEqual({
        headers: stableAuthHeader,
        timeout: 60000,
      });

      expect(secondCall[2]).toEqual({
        headers: stableAuthHeader,
        timeout: 60000,
      });
    },
  );


  test(
    'displays predictions and processing comparison',
    async () => {
      const user = userEvent.setup();

      render(
        <ModelComparisonPage
          onBack={vi.fn()}
        />,
      );

      await user.click(
        screen.getByRole('button', {
          name: 'Compare both models',
        }),
      );

      const overviewHeading =
        await screen.findByRole('heading', {
          name: 'Result overview',
        });

      const summarySection =
        overviewHeading.closest('section');

      expect(summarySection).not.toBeNull();

      const summary = within(summarySection);

      expect(
        summary.getByText(
          'comparison-test-id',
        ),
      ).toBeInTheDocument();

      expect(
        summary.getByText(
          'XGBoost faster',
        ),
      ).toBeInTheDocument();

      expect(
        summary.getByText('No'),
      ).toBeInTheDocument();

      expect(
        summary.getByText('XGBoost', {
          selector: 'strong',
        }),
      ).toBeInTheDocument();

      const xgboostCard = screen
  .getByRole('heading', {
    name: 'XGBoost',
    level: 2,
  })
  .closest('article');

const randomForestCard = screen
  .getByRole('heading', {
    name: 'Random Forest',
    level: 2,
  })
  .closest('article');

expect(xgboostCard).not.toBeNull();
expect(randomForestCard).not.toBeNull();

const xgboostView = within(xgboostCard);
const randomForestView = within(
  randomForestCard,
);

expect(
  xgboostView.getByRole('heading', {
    name: 'Baseline',
    level: 3,
  }),
).toBeInTheDocument();

expect(
  xgboostView.getByText(/Confidence:/),
).toHaveTextContent(
  'Confidence: 91.0%',
);

expect(
  xgboostView.getByText(/Processing time:/),
).toHaveTextContent(
  'Processing time: 2.100 ms',
);

expect(
  randomForestView.getByRole('heading', {
    name: 'Stress',
    level: 3,
  }),
).toBeInTheDocument();

expect(
  randomForestView.getByText(/Confidence:/),
).toHaveTextContent(
  'Confidence: 76.0%',
);

expect(
  randomForestView.getByText(
    /Processing time:/,
  ),
).toHaveTextContent(
  'Processing time: 4.600 ms',
);
    },
  );
});
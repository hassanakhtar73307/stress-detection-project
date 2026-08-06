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
} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';

import AdminPage from '../AdminPage';


const {
  logoutMock,
  adminUser,
  stableAuthHeader,
} = vi.hoisted(() => ({
  logoutMock: vi.fn(),

  adminUser: {
    id: 1,
    email: 'admin@example.com',
    is_admin: true,
  },

  stableAuthHeader: {
    Authorization: 'Bearer test-token',
  },
}));


vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
  },
}));


vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: adminUser,
    authHeader: stableAuthHeader,
    logout: logoutMock,
  }),
}));


const overviewResponse = {
  database: {
    location: 'hosted',
  },
  totals: {
    users: 2,
    active_users: 2,
    registrations_7d: 1,
    registrations_30d: 2,
    complete_profiles: 2,
    predictions: 2,
  },
  by_user_type: [],
  by_primary_goal: [],
  by_wearable_device: [],
};


const usersResponse = {
  users: [
    {
      id: 1,
      name: 'Admin User',
      email: 'admin@example.com',
      age: 30,
      occupation: 'Researcher',
      user_type: 'researcher',
      primary_goal: 'research_demo',
      wearable_device: 'smartwatch',
      login_count: 2,
      created_at: '2026-08-01T10:00:00Z',
      last_login_at: '2026-08-06T10:00:00Z',
    },
  ],
};


const predictionsResponse = {
  predictions: [
    {
      id: 1,
      user_name: 'XGBoost User',
      user_email: 'xgboost@example.com',
      sample_id: 'sample-xgb',
      source_participant_id: 'S2',
      model_name: 'xgboost',
      expected_label: 'Baseline',
      predicted_label: 'Baseline',
      confidence: 0.92,
      processing_time_ms: 2.4,
      comparison_id: 'comparison-1',
      created_at: '2026-08-05T10:00:00Z',
    },
    {
      id: 2,
      user_name: 'Random Forest User',
      user_email: 'forest@example.com',
      sample_id: 'sample-rf',
      source_participant_id: 'S3',
      model_name: 'random_forest',
      expected_label: 'Baseline',
      predicted_label: 'Stress',
      confidence: 0.81,
      processing_time_ms: 3.1,
      comparison_id: 'comparison-2',
      created_at: '2026-08-06T10:00:00Z',
    },
  ],
};


function configureApiResponses() {
  axios.get.mockImplementation((url) => {
    if (url.includes('/admin/overview')) {
      return Promise.resolve({
        data: overviewResponse,
      });
    }

    if (url.includes('/admin/users')) {
      return Promise.resolve({
        data: usersResponse,
      });
    }

    if (url.includes('/admin/predictions')) {
      return Promise.resolve({
        data: predictionsResponse,
      });
    }

    return Promise.reject(
      new Error(`Unexpected URL: ${url}`),
    );
  });
}


describe('AdminPage prediction filters', () => {
  beforeEach(() => {
    axios.get.mockReset();
    logoutMock.mockReset();
    configureApiResponses();
  });


  test('filters prediction history by model', async () => {
    const user = userEvent.setup();

    render(
      <AdminPage onBack={vi.fn()} />,
    );

    expect(
      await screen.findByText(
        /2 predictions shown/i,
      ),
    ).toBeInTheDocument();

    expect(
      screen.getByText('XGBoost User'),
    ).toBeInTheDocument();

    expect(
      screen.getByText('Random Forest User'),
    ).toBeInTheDocument();

    await user.selectOptions(
      screen.getByLabelText('Model'),
      'random_forest',
    );

    expect(
      screen.getByText(/1 prediction shown/i),
    ).toBeInTheDocument();

    expect(
      screen.getByText('Random Forest User'),
    ).toBeInTheDocument();

    expect(
      screen.queryByText('XGBoost User'),
    ).not.toBeInTheDocument();
  });


  test('clear filters restores all predictions', async () => {
    const user = userEvent.setup();

    render(
      <AdminPage onBack={vi.fn()} />,
    );

    await screen.findByText(
      /2 predictions shown/i,
    );

    await user.selectOptions(
      screen.getByLabelText('Result'),
      'correct',
    );

    expect(
      screen.getByText(/1 prediction shown/i),
    ).toBeInTheDocument();

    expect(
      screen.queryByText('Random Forest User'),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole('button', {
        name: 'Clear filters',
      }),
    );

    expect(
      screen.getByText(/2 predictions shown/i),
    ).toBeInTheDocument();

    expect(
      screen.getByText('XGBoost User'),
    ).toBeInTheDocument();

    expect(
      screen.getByText('Random Forest User'),
    ).toBeInTheDocument();
  });
});
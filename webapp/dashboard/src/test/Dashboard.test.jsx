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
} from '@testing-library/react';

import userEvent from '@testing-library/user-event';
import axios from 'axios';

import Dashboard from '../Dashboard';


vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));


vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => (
    <div>{children}</div>
  ),

  LineChart: ({ children }) => (
    <div>{children}</div>
  ),

  BarChart: ({ children }) => (
    <div>{children}</div>
  ),

  Bar: ({ children }) => (
    <div>{children}</div>
  ),

  CartesianGrid: () => null,
  Cell: () => null,
  Legend: () => null,
  Line: () => null,
  ReferenceLine: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}));


const {
  authHeader,
  dashboardUser,
  logoutMock,
} = vi.hoisted(() => ({
  authHeader: {
    Authorization: 'Bearer dashboard-test-token',
  },

  dashboardUser: {
    id: 1,
    name: 'Dashboard Test User',
    email: 'dashboard@example.com',
    is_admin: true,
  },

  logoutMock: vi.fn(),
}));


vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: dashboardUser,
    authHeader,
    logout: logoutMock,
  }),
}));


function configureGetRequests() {
  axios.get.mockImplementation((url) => {
    if (url.includes('/health')) {
      return Promise.resolve({
        data: {
          status: 'ok',
        },
      });
    }

    if (url.includes('/model-insights')) {
      return Promise.resolve({
        data: {
          available: false,
        },
      });
    }

    return Promise.reject(
      new Error(`Unexpected GET request: ${url}`),
    );
  });
}


function renderDashboard() {
  const props = {
    onOpenProfile: vi.fn(),
    onOpenAdmin: vi.fn(),
    onOpenComparison: vi.fn(),
  };

  render(<Dashboard {...props} />);

  return props;
}


describe('Dashboard', () => {
  beforeEach(() => {
    axios.get.mockReset();
    axios.post.mockReset();
    logoutMock.mockReset();

    configureGetRequests();
  });


  test(
    'opens the dashboard navigation pages',
    async () => {
      const user = userEvent.setup();
      const props = renderDashboard();

      expect(
        await screen.findByText('SYSTEM ONLINE'),
      ).toBeInTheDocument();

      await user.click(
        screen.getByRole('button', {
          name: 'User analytics',
        }),
      );

      expect(
        props.onOpenAdmin,
      ).toHaveBeenCalledTimes(1);

      await user.click(
        screen.getByRole('button', {
          name: 'Model comparison',
        }),
      );

      expect(
        props.onOpenComparison,
      ).toHaveBeenCalledTimes(1);

      await user.click(
        screen.getByRole('button', {
          name: 'Dashboard Test User',
        }),
      );

      expect(
        props.onOpenProfile,
      ).toHaveBeenCalledTimes(1);

      await user.click(
        screen.getByRole('button', {
          name: 'Log out',
        }),
      );

      expect(logoutMock).toHaveBeenCalledTimes(1);
    },
  );


  test(
    'submits a sample using XGBoost by default',
    async () => {
      const user = userEvent.setup();

      axios.post.mockResolvedValueOnce({
        data: {
          predicted_label: 'Baseline',
          confidence: 0.91,
          probabilities: {
            Baseline: 0.91,
            Stress: 0.06,
            Amusement: 0.03,
          },
        },
      });

      renderDashboard();

      await screen.findByText('SYSTEM ONLINE');

      await user.click(
        screen.getByRole('button', {
          name: /Sample scenario 01/i,
        }),
      );

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledTimes(1);
      });

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/predict'),
        expect.objectContaining({
          features: expect.any(Object),
          model_name: 'xgboost',
          sample_id: 'scenario_01',
          participant_id: 'S16',
          expected_label: 'Baseline',
        }),
        {
          headers: authHeader,
          timeout: 60000,
        },
      );

      expect(
        await screen.findByLabelText(
          'Confidence 91.0 percent',
        ),
      ).toBeInTheDocument();

      expect(
        screen.getByText(
          /model confidence 91\.0%/i,
        ),
      ).toBeInTheDocument();
    },
  );


  test(
    'submits a sample using Random Forest',
    async () => {
      const user = userEvent.setup();

      axios.post.mockResolvedValueOnce({
        data: {
          predicted_label: 'Stress',
          confidence: 0.76,
          probabilities: {
            Baseline: 0.16,
            Stress: 0.76,
            Amusement: 0.08,
          },
        },
      });

      renderDashboard();

      await screen.findByText('SYSTEM ONLINE');

      await user.click(
        screen.getByRole('button', {
          name: /Random Forest/i,
        }),
      );

      await user.click(
        screen.getByRole('button', {
          name: /Sample scenario 01/i,
        }),
      );

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledTimes(1);
      });

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining('/predict'),
        expect.objectContaining({
          model_name: 'random_forest',
          sample_id: 'scenario_01',
          participant_id: 'S16',
          expected_label: 'Baseline',
        }),
        {
          headers: authHeader,
          timeout: 60000,
        },
      );

      expect(
        await screen.findByLabelText(
          'Confidence 76.0 percent',
        ),
      ).toBeInTheDocument();
    },
  );


  test(
    'logs out when the prediction API returns 401',
    async () => {
      const user = userEvent.setup();

      axios.post.mockRejectedValueOnce({
        response: {
          status: 401,
        },
      });

      renderDashboard();

      await screen.findByText('SYSTEM ONLINE');

      await user.click(
        screen.getByRole('button', {
          name: /Sample scenario 01/i,
        }),
      );

      await waitFor(() => {
        expect(logoutMock).toHaveBeenCalledTimes(1);
      });
    },
  );
});
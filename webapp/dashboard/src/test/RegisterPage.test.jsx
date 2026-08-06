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

import RegisterPage from '../RegisterPage';


const { registerMock } = vi.hoisted(() => ({
  registerMock: vi.fn(),
}));


vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    register: registerMock,
  }),
}));


async function completeRegistrationForm(
  user,
  {
    acknowledgeNotice = true,
    password = 'Testing123!',
    confirmPassword = 'Testing123!',
  } = {},
) {
  await user.type(
    screen.getByLabelText('Full name'),
    'Registration Test User',
  );

  await user.type(
    screen.getByLabelText('Email address'),
    'registration@example.com',
  );

  await user.type(
    screen.getByLabelText('Create password'),
    password,
  );

  await user.type(
    screen.getByLabelText('Confirm password'),
    confirmPassword,
  );

  await user.type(
    screen.getByLabelText(/Age/i),
    '29',
  );

  await user.type(
    screen.getByLabelText(/Occupation/i),
    'Software tester',
  );

  await user.selectOptions(
    screen.getByLabelText('Current routine'),
    'employed',
  );

  await user.selectOptions(
    screen.getByLabelText(
      'Main reason for using the app',
    ),
    'work_stress',
  );

  await user.selectOptions(
    screen.getByLabelText(
      'Sensor or wearable access',
    ),
    'smartwatch',
  );

  if (acknowledgeNotice) {
    await user.click(
      screen.getByRole('checkbox', {
        name: /research prototype/i,
      }),
    );
  }
}


describe('RegisterPage', () => {
  beforeEach(() => {
    registerMock.mockReset();
  });


  test(
    'shows and hides the create-password field',
    async () => {
      const user = userEvent.setup();

      render(
        <RegisterPage
          onSwitchToLogin={vi.fn()}
        />,
      );

      const passwordInput =
        screen.getByLabelText(
          'Create password',
        );

      expect(passwordInput).toHaveAttribute(
        'type',
        'password',
      );

      await user.click(
        screen.getByRole('button', {
          name: 'Show create password',
        }),
      );

      expect(passwordInput).toHaveAttribute(
        'type',
        'text',
      );

      await user.click(
        screen.getByRole('button', {
          name: 'Hide create password',
        }),
      );

      expect(passwordInput).toHaveAttribute(
        'type',
        'password',
      );
    },
  );


  test(
    'requires the research-prototype acknowledgement',
    async () => {
      const user = userEvent.setup();

      render(
        <RegisterPage
          onSwitchToLogin={vi.fn()}
        />,
      );

      await completeRegistrationForm(user, {
        acknowledgeNotice: false,
      });

      await user.click(
        screen.getByRole('button', {
          name: 'Create account and continue',
        }),
      );

      expect(
        await screen.findByRole('alert'),
      ).toHaveTextContent(
        'Please confirm that you understand the research-prototype notice.',
      );

      expect(
        registerMock,
      ).not.toHaveBeenCalled();
    },
  );


  test(
    'submits the complete registration payload',
    async () => {
      const user = userEvent.setup();

      registerMock.mockResolvedValueOnce({
        id: 1,
      });

      render(
        <RegisterPage
          onSwitchToLogin={vi.fn()}
        />,
      );

      await completeRegistrationForm(user);

      await user.click(
        screen.getByRole('button', {
          name: 'Create account and continue',
        }),
      );

      expect(
        registerMock,
      ).toHaveBeenCalledTimes(1);

      expect(
        registerMock,
      ).toHaveBeenCalledWith({
        name: 'Registration Test User',
        email: 'registration@example.com',
        password: 'Testing123!',
        age: '29',
        occupation: 'Software tester',
        user_type: 'employed',
        primary_goal: 'work_stress',
        wearable_device: 'smartwatch',
        research_notice_acknowledged: true,
      });
    },
  );


  test(
    'displays an API registration error',
    async () => {
      const user = userEvent.setup();

      registerMock.mockRejectedValueOnce({
        response: {
          data: {
            error:
              'An account with this email already exists',
          },
        },
      });

      render(
        <RegisterPage
          onSwitchToLogin={vi.fn()}
        />,
      );

      await completeRegistrationForm(user);

      await user.click(
        screen.getByRole('button', {
          name: 'Create account and continue',
        }),
      );

      expect(
        await screen.findByRole('alert'),
      ).toHaveTextContent(
        'An account with this email already exists',
      );
    },
  );
});
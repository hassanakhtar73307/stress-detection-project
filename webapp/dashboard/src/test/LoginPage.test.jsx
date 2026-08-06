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

import LoginPage from '../LoginPage';

const { loginMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
}));

vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  test('shows and hides the password', async () => {
    const user = userEvent.setup();

    render(
      <LoginPage
        onSwitchToRegister={vi.fn()}
        onForgotPassword={vi.fn()}
      />,
    );

    const passwordInput =
      screen.getByLabelText('Password');

    expect(passwordInput).toHaveAttribute(
      'type',
      'password',
    );

    await user.click(
      screen.getByRole('button', {
        name: 'Show password',
      }),
    );

    expect(passwordInput).toHaveAttribute(
      'type',
      'text',
    );

    await user.click(
      screen.getByRole('button', {
        name: 'Hide password',
      }),
    );

    expect(passwordInput).toHaveAttribute(
      'type',
      'password',
    );
  });

  test('submits the entered email and password', async () => {
    const user = userEvent.setup();

    loginMock.mockResolvedValueOnce({
      token: 'test-token',
    });

    render(
      <LoginPage
        onSwitchToRegister={vi.fn()}
        onForgotPassword={vi.fn()}
      />,
    );

    await user.type(
      screen.getByLabelText('Email address'),
      'tester@example.com',
    );

    await user.type(
      screen.getByLabelText('Password'),
      'Testing123!',
    );

    await user.click(
      screen.getByRole('button', {
        name: 'Sign in to dashboard',
      }),
    );

    expect(loginMock).toHaveBeenCalledTimes(1);

    expect(loginMock).toHaveBeenCalledWith({
      email: 'tester@example.com',
      password: 'Testing123!',
    });
  });

  test('displays the API login error', async () => {
    const user = userEvent.setup();

    loginMock.mockRejectedValueOnce({
      response: {
        data: {
          error: 'Invalid email or password',
        },
      },
    });

    render(
      <LoginPage
        onSwitchToRegister={vi.fn()}
        onForgotPassword={vi.fn()}
      />,
    );

    await user.type(
      screen.getByLabelText('Email address'),
      'tester@example.com',
    );

    await user.type(
      screen.getByLabelText('Password'),
      'WrongPassword123!',
    );

    await user.click(
      screen.getByRole('button', {
        name: 'Sign in to dashboard',
      }),
    );

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent(
      'Invalid email or password',
    );
  });
});
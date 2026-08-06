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

import ProfilePage from '../ProfilePage';


const {
  profileUser,
  updateProfileMock,
  logoutMock,
} = vi.hoisted(() => ({
  profileUser: {
    id: 1,
    name: 'Profile Test User',
    email: 'profile@example.com',
    age: 30,
    occupation: 'Software developer',
    user_type: 'employed',
    primary_goal: 'work_stress',
    wearable_device: 'smartwatch',
  },

  updateProfileMock: vi.fn(),
  logoutMock: vi.fn(),
}));


vi.mock('../AuthContext', () => ({
  useAuth: () => ({
    user: profileUser,
    updateProfile: updateProfileMock,
    logout: logoutMock,
  }),
}));


function renderProfilePage() {
  return render(
    <ProfilePage onBack={vi.fn()} />,
  );
}


describe('ProfilePage', () => {
  beforeEach(() => {
    updateProfileMock.mockReset();
    logoutMock.mockReset();
  });


  test(
    'loads the current profile details',
    () => {
      renderProfilePage();

      expect(
        screen.getByLabelText('Full name'),
      ).toHaveValue('Profile Test User');

      expect(
        screen.getByLabelText(/Email address/i)
      ).toHaveValue('profile@example.com');

      expect(
        screen.getByLabelText(/Email address/i)
      ).toHaveAttribute('readonly');

      expect(
        screen.getByLabelText(/Age/i),
      ).toHaveValue(30);

      expect(
        screen.getByLabelText(/Occupation/i),
      ).toHaveValue('Software developer');

      expect(
        screen.getByLabelText(
          'Current routine',
        ),
      ).toHaveValue('employed');

      expect(
        screen.getByLabelText(
          'Main reason for using the app',
        ),
      ).toHaveValue('work_stress');

      expect(
        screen.getByLabelText(
          'Sensor or wearable access',
        ),
      ).toHaveValue('smartwatch');

      expect(
        screen.getByLabelText(
          '100% profile complete',
        ),
      ).toBeInTheDocument();
    },
  );


  test(
    'submits the updated profile payload',
    async () => {
      const user = userEvent.setup();

      updateProfileMock.mockResolvedValueOnce({
        ...profileUser,
        name: 'Updated Profile User',
      });

      renderProfilePage();

      const nameInput =
        screen.getByLabelText('Full name');

      const ageInput =
        screen.getByLabelText(/Age/i);

      const occupationInput =
        screen.getByLabelText(/Occupation/i);

      await user.clear(nameInput);
      await user.type(
        nameInput,
        'Updated Profile User',
      );

      await user.clear(ageInput);
      await user.type(ageInput, '31');

      await user.clear(occupationInput);
      await user.type(
        occupationInput,
        'Research assistant',
      );

      await user.selectOptions(
        screen.getByLabelText(
          'Current routine',
        ),
        'researcher',
      );

      await user.selectOptions(
        screen.getByLabelText(
          'Main reason for using the app',
        ),
        'research_demo',
      );

      await user.selectOptions(
        screen.getByLabelText(
          'Sensor or wearable access',
        ),
        'chest_sensor',
      );

      await user.click(
        screen.getByRole('button', {
          name: 'Save profile changes',
        }),
      );

      expect(
        updateProfileMock,
      ).toHaveBeenCalledTimes(1);

      expect(
        updateProfileMock,
      ).toHaveBeenCalledWith({
        name: 'Updated Profile User',
        age: '31',
        occupation: 'Research assistant',
        user_type: 'researcher',
        primary_goal: 'research_demo',
        wearable_device: 'chest_sensor',
      });

      expect(
        await screen.findByRole('status'),
      ).toHaveTextContent(
        'Profile updated successfully.',
      );
    },
  );


  test(
    'displays an API profile update error',
    async () => {
      const user = userEvent.setup();

      updateProfileMock.mockRejectedValueOnce({
        response: {
          data: {
            error:
              'Profile information could not be saved',
          },
        },
      });

      renderProfilePage();

      await user.click(
        screen.getByRole('button', {
          name: 'Save profile changes',
        }),
      );

      expect(
        await screen.findByRole('alert'),
      ).toHaveTextContent(
        'Profile information could not be saved',
      );
    },
  );


  test(
    'logs the user out from the profile page',
    async () => {
      const user = userEvent.setup();

      renderProfilePage();

      await user.click(
        screen.getByRole('button', {
          name: 'Log out',
        }),
      );

      expect(logoutMock).toHaveBeenCalledTimes(1);
    },
  );
});
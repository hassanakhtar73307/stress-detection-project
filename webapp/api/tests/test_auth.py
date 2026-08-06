def registration_payload(email):
    return {
        "name": "Pytest User",
        "email": email,
        "password": "Testing123!",
        "age": 28,
        "occupation": "Software tester",
        "user_type": "employed",
        "primary_goal": "work_stress",
        "wearable_device": "smartwatch",
        "research_notice_acknowledged": True,
    }


def register_user(client, email):
    response = client.post(
        "/register",
        json=registration_payload(email),
    )

    assert response.status_code == 201

    data = response.get_json()

    assert data is not None
    assert data["token"]
    assert data["user"]["email"] == email
    assert "password_hash" not in data["user"]

    return data


def test_register_creates_account(client):
    data = register_user(
        client,
        "register-test@example.com",
    )

    assert data["user"]["name"] == "Pytest User"
    assert data["user"]["age"] == 28
    assert data["user"]["occupation"] == "Software tester"
    assert data["user"]["user_type"] == "employed"
    assert data["user"]["primary_goal"] == "work_stress"
    assert data["user"]["wearable_device"] == "smartwatch"


def test_register_rejects_duplicate_email(client):
    email = "duplicate-test@example.com"

    first_response = client.post(
        "/register",
        json=registration_payload(email),
    )

    second_response = client.post(
        "/register",
        json=registration_payload(email),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

    data = second_response.get_json()

    assert data["error"] == (
        "An account with this email already exists"
    )


def test_login_returns_token(client):
    email = "login-test@example.com"
    password = "Testing123!"

    register_user(client, email)

    response = client.post(
        "/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data["token"]
    assert data["user"]["email"] == email
    assert data["user"]["login_count"] >= 1
    assert "password_hash" not in data["user"]


def test_login_rejects_invalid_password(client):
    email = "wrong-password-test@example.com"

    register_user(client, email)

    response = client.post(
        "/login",
        json={
            "email": email,
            "password": "Incorrect123!",
        },
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data["error"] == "Invalid email or password"


def test_authenticated_user_can_view_profile(client):
    email = "profile-test@example.com"

    registration = register_user(client, email)
    token = registration["token"]

    response = client.get(
        "/profile",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data["email"] == email
    assert "password_hash" not in data
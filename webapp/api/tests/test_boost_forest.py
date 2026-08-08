def registration_payload(email):
    return {
        "name": "Boost Forest Test User",
        "email": email,
        "password": "Testing123!",
        "age": 28,
        "occupation": "Software tester",
        "user_type": "employed",
        "primary_goal": "work_stress",
        "wearable_device": "smartwatch",
        "research_notice_acknowledged": True,
    }


def register_and_get_token(client, email):
    response = client.post(
        "/register",
        json=registration_payload(email),
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data is not None
    assert data["token"]
    return data["token"]


def authorization_header(token):
    return {
        "Authorization": f"Bearer {token}",
    }


def test_boost_forest_prediction_returns_complete_response(client):
    token = register_and_get_token(
        client,
        "boost-forest-prediction@example.com",
    )

    response = client.post(
        "/predict",
        headers=authorization_header(token),
        json={
            "model_name": "boost_forest",
            "features": [0.0] * 45,
            "sample_id": "pytest-boost-forest-sample",
            "participant_id": "S2",
            "expected_label": "Baseline",
            "comparison_id": "pytest-boost-forest-comparison",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data["prediction_id"] is not None
    assert data["model_name"] == "boost_forest"
    assert data["model_display_name"] == "Boost Forest"
    assert data["predicted_label"] in {
        "Baseline",
        "Stress",
        "Amusement",
    }
    assert isinstance(data["predicted_class"], int)
    assert 0 <= data["predicted_class"] <= 2
    assert 0 <= data["confidence"] <= 1
    assert isinstance(data["probabilities"], dict)
    assert set(data["probabilities"]) == {
        "Baseline",
        "Stress",
        "Amusement",
    }
    assert abs(sum(data["probabilities"].values()) - 1.0) <= 0.001
    assert data["processing_time_ms"] >= 0


def test_available_models_include_boost_forest(client):
    token = register_and_get_token(
        client,
        "boost-forest-model-list@example.com",
    )

    response = client.post(
        "/predict",
        headers=authorization_header(token),
        json={
            "model_name": "not_a_model",
            "features": [0.0] * 45,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "Unsupported model"
    assert set(data["available_models"]) == {
        "xgboost",
        "random_forest",
        "boost_forest",
    }

def registration_payload(email):
    return {
        "name": "Prediction Test User",
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


def test_predict_rejects_wrong_feature_count(client):
    token = register_and_get_token(
        client,
        "wrong-features@example.com",
    )

    response = client.post(
        "/predict",
        headers=authorization_header(token),
        json={
            "model_name": "xgboost",
            "features": [0.0] * 44,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == (
        "Expected 45 features, got 44"
    )


def test_predict_rejects_unsupported_model(client):
    token = register_and_get_token(
        client,
        "unsupported-model@example.com",
    )

    response = client.post(
        "/predict",
        headers=authorization_header(token),
        json={
            "model_name": "invalid_model",
            "features": [0.0] * 45,
        },
    )

    assert response.status_code == 400

    data = response.get_json()

    assert data["error"] == "Unsupported model"
    assert set(data["available_models"]) == {
        "xgboost",
        "random_forest",
    }


def test_xgboost_prediction_returns_complete_response(client):
    token = register_and_get_token(
        client,
        "xgboost-prediction@example.com",
    )

    response = client.post(
        "/predict",
        headers=authorization_header(token),
        json={
            "model_name": "xgboost",
            "features": [0.0] * 45,
            "sample_id": "pytest-xgb-sample",
            "participant_id": "S2",
            "expected_label": "Baseline",
            "comparison_id": "pytest-xgb-comparison",
        },
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data is not None
    assert data["prediction_id"] is not None
    assert data["model_name"] == "xgboost"
    assert data["model_display_name"]
    assert data["predicted_label"]
    assert isinstance(
        data["predicted_class"],
        int,
    )
    assert 0 <= data["confidence"] <= 1
    assert isinstance(data["probabilities"], dict)
    assert len(data["probabilities"]) == 3
    assert data["processing_time_ms"] >= 0


def test_model_comparison_is_saved_in_prediction_history(
    client,
):
    admin_token = register_and_get_token(
        client,
        "admin@example.com",
    )

    comparison_id = "pytest-model-comparison"
    features = [0.0] * 45

    for model_name in (
        "xgboost",
        "random_forest",
    ):
        response = client.post(
            "/predict",
            headers=authorization_header(
                admin_token,
            ),
            json={
                "model_name": model_name,
                "features": features,
                "sample_id": "pytest-comparison-sample",
                "participant_id": "S3",
                "expected_label": "Stress",
                "comparison_id": comparison_id,
            },
        )

        assert response.status_code == 200

        data = response.get_json()

        assert data["model_name"] == model_name
        assert data["processing_time_ms"] >= 0

    history_response = client.get(
        "/admin/predictions?limit=500",
        headers=authorization_header(
            admin_token,
        ),
    )

    assert history_response.status_code == 200

    history_data = history_response.get_json()

    matching_records = [
        record
        for record in history_data["predictions"]
        if record.get("comparison_id")
        == comparison_id
    ]

    assert len(matching_records) == 2

    assert {
        record["model_name"]
        for record in matching_records
    } == {
        "xgboost",
        "random_forest",
    }

    for record in matching_records:
        assert (
            record["comparison_id"]
            == comparison_id
        )
        assert record["processing_time_ms"] is not None
        assert (
            record["sample_id"]
            == "pytest-comparison-sample"
        )
        assert (
            record["source_participant_id"]
            == "S3"
        )
        assert record["expected_label"] == "Stress"
        assert record["predicted_label"]
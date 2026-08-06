def test_health_endpoint_returns_api_status(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "ok"
    assert data["n_features_expected"] == 45
    assert data["default_model"] == "xgboost"

    assert set(data["available_models"]) == {
        "xgboost",
        "random_forest",
    }

    assert data["database"]["backend"] == "sqlite"
    assert data["database"]["location"] == "local"


def test_predict_requires_authentication(client):
    response = client.post(
        "/predict",
        json={
            "model_name": "xgboost",
            "features": [0.0] * 45,
        },
    )

    assert response.status_code == 401

    data = response.get_json()

    assert data is not None
    assert "error" in data
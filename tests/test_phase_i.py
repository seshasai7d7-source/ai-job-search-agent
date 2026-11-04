import logging


def test_request_logs_exclude_query_parameters_and_bodies(client, caplog):
    secret = "do-not-log-this-value"
    with caplog.at_level(logging.INFO, logger="app.requests"):
        response = client.get("/health", params={"private": secret})
        body_response = client.post(
            "/health",
            params={"private": secret},
            content=secret,
        )

    assert response.status_code == 200
    assert body_response.status_code == 405
    request_logs = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.requests"
    ]
    assert any(
        "http_request method=GET path=/health status_code=200" in message
        for message in request_logs
    )
    assert all(secret not in message for message in request_logs)

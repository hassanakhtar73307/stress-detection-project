import json
import math
import os
import statistics
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = os.getenv(
    "BENCHMARK_API_URL",
    "https://stress-detection-project-imdt.onrender.com",
).rstrip("/")

EMAIL = os.getenv("BENCHMARK_EMAIL", "").strip()
PASSWORD = os.getenv("BENCHMARK_PASSWORD", "")
MODEL_NAME = os.getenv("BENCHMARK_MODEL", "xgboost").strip()

REQUEST_COUNT = 100
WARMUP_COUNT = 3
TIMEOUT_SECONDS = 90


def post_json(url, payload, token=None):
    body = json.dumps(payload).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    started = time.perf_counter()

    with urlopen(
        request,
        timeout=TIMEOUT_SECONDS,
    ) as response:
        response_body = response.read().decode("utf-8")

    elapsed_ms = (
        time.perf_counter() - started
    ) * 1000

    return json.loads(response_body), elapsed_ms


def percentile(values, percentile_value):
    ordered = sorted(values)

    index = max(
        0,
        math.ceil(
            percentile_value / 100 * len(ordered)
        ) - 1,
    )

    return ordered[index]


def load_sample():
    script_directory = Path(__file__).resolve().parent

    sample_file = (
        script_directory.parent
        / "dashboard"
        / "src"
        / "sample_windows.json"
    )

    with sample_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        samples = json.load(file)

    if not samples:
        raise RuntimeError(
            "No sample records were found."
        )

    return samples[0]


def main():
    if not EMAIL or not PASSWORD:
        raise RuntimeError(
            "Set BENCHMARK_EMAIL and "
            "BENCHMARK_PASSWORD before running."
        )

    if MODEL_NAME not in {
        "xgboost",
        "random_forest",
        "boost_forest",
    }:
        raise RuntimeError(
            "BENCHMARK_MODEL must be "
            "xgboost, random_forest, or boost_forest."
        )

    print(f"API: {API_BASE}")
    print(f"Model: {MODEL_NAME}")
    print(f"Measured requests: {REQUEST_COUNT}")
    print(f"Warm-up requests: {WARMUP_COUNT}")
    print()

    login_response, login_latency = post_json(
        f"{API_BASE}/login",
        {
            "email": EMAIL,
            "password": PASSWORD,
        },
    )

    token = login_response.get("token")

    if not token:
        raise RuntimeError(
            "Login succeeded but no token was returned."
        )

    print(
        f"Login successful "
        f"({login_latency:.2f} ms)"
    )

    sample = load_sample()

    base_payload = {
        "features": sample["features"],
        "model_name": MODEL_NAME,
        "participant_id": sample.get(
            "subject",
            "benchmark",
        ),
        "expected_label": sample.get(
            "true_label",
        ),
	"benchmark_mode": True,
    }

    print("Running warm-up requests...")

    for warmup_index in range(WARMUP_COUNT):
        payload = {
            **base_payload,
            "sample_id":
                f"warmup_{warmup_index + 1:03d}",
        }

        post_json(
            f"{API_BASE}/predict",
            payload,
            token,
        )

    print("Running measured requests...")

    round_trip_times = []
    processing_times = []
    failures = []

    for request_index in range(REQUEST_COUNT):
        payload = {
            **base_payload,
            "sample_id":
                f"latency_{request_index + 1:03d}",
        }

        try:
            response, elapsed_ms = post_json(
                f"{API_BASE}/predict",
                payload,
                token,
            )

            round_trip_times.append(elapsed_ms)

            internal_time = response.get(
                "processing_time_ms"
            )

            if internal_time is not None:
                processing_times.append(
                    float(internal_time)
                )

            print(
                f"{request_index + 1:03d}/"
                f"{REQUEST_COUNT}: "
                f"{elapsed_ms:.2f} ms"
            )

        except (
            HTTPError,
            URLError,
            TimeoutError,
            ValueError,
        ) as error:
            failures.append(
                {
                    "request":
                        request_index + 1,
                    "error": str(error),
                }
            )

            print(
                f"{request_index + 1:03d}/"
                f"{REQUEST_COUNT}: FAILED"
            )

    successful = len(round_trip_times)

    print()
    print("=" * 48)
    print("100-REQUEST LATENCY BENCHMARK")
    print("=" * 48)
    print(f"Model: {MODEL_NAME}")
    print(f"Successful requests: {successful}")
    print(f"Failed requests: {len(failures)}")

    if round_trip_times:
        print()
        print("End-to-end API response time:")
        print(
            f"Mean: "
            f"{statistics.mean(round_trip_times):.2f} ms"
        )
        print(
            f"Median: "
            f"{statistics.median(round_trip_times):.2f} ms"
        )
        print(
            f"Minimum: "
            f"{min(round_trip_times):.2f} ms"
        )
        print(
            f"Maximum: "
            f"{max(round_trip_times):.2f} ms"
        )
        print(
            f"95th percentile: "
            f"{percentile(round_trip_times, 95):.2f} ms"
        )

        target_met = (
            statistics.mean(round_trip_times) < 200
        )

        print(
            "Mean below 200 ms target: "
            f"{'YES' if target_met else 'NO'}"
        )

    if processing_times:
        print()
        print("Backend model-processing time:")
        print(
            f"Mean: "
            f"{statistics.mean(processing_times):.3f} ms"
        )
        print(
            f"Median: "
            f"{statistics.median(processing_times):.3f} ms"
        )
        print(
            f"Minimum: "
            f"{min(processing_times):.3f} ms"
        )
        print(
            f"Maximum: "
            f"{max(processing_times):.3f} ms"
        )
        print(
            f"95th percentile: "
            f"{percentile(processing_times, 95):.3f} ms"
        )

    if failures:
        print()
        print("Failure details:")

        for failure in failures:
            print(
                f"Request {failure['request']}: "
                f"{failure['error']}"
            )


if __name__ == "__main__":
    main()

import json
from urllib import error, request

from django.conf import settings


class OpenAIServiceError(Exception):
    """Raised when an OpenAI API request fails in a user-facing workflow."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def call_openai_responses_api(payload: dict) -> dict:
    api_request = request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(api_request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise OpenAIServiceError(
            _build_openai_error_message(exc),
            status_code=exc.code,
        ) from exc
    except error.URLError as exc:
        raise OpenAIServiceError(
            "Could not reach OpenAI. Check the backend container network connection and try again.",
        ) from exc
    except TimeoutError as exc:
        raise OpenAIServiceError("OpenAI took too long to respond. Please try again.") from exc


def extract_output_text(api_response: dict) -> str:
    if api_response.get("output_text"):
        return api_response["output_text"]

    for output_item in api_response.get("output", []):
        for content_item in output_item.get("content", []):
            if content_item.get("type") == "output_text":
                return content_item.get("text", "")

    raise OpenAIServiceError("OpenAI response did not include usable output text.")


def _build_openai_error_message(exc: error.HTTPError) -> str:
    if exc.code == 401:
        return "OpenAI rejected the configured API key. Update OPENAI_API_KEY and restart the backend container."

    openai_message = _read_openai_error_message(exc)
    if openai_message:
        return f"OpenAI request failed: {openai_message}"

    return f"OpenAI request failed with status {exc.code}."


def _read_openai_error_message(exc: error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
        data = json.loads(body)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""

    error_data = data.get("error", {})
    if isinstance(error_data, dict):
        message = error_data.get("message", "")
        return message if isinstance(message, str) else ""

    return ""

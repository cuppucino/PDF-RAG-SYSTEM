# API Rate Limits & Insufficient Quotas: Interview Guide

This guide explains what an API **Rate Limit (HTTP 429)** is, how it differs from an **Insufficient Quota** error, and how to handle it in production applications.

---

## 1. What is an HTTP 429 Error?

The **HTTP 429 Too Many Requests** status code indicates that the client has sent too many requests in a given amount of time (rate limiting).

However, in the case of OpenAI:
*   **Rate Limits (RPM/TPM)**: Requests per Minute or Tokens per Minute limits. If you hit this, waiting a few seconds and retrying using **Exponential Backoff** resolves it.
*   **Insufficient Quota (Billing Limit)**: You have run out of money/credits in your OpenAI platform account, or you have hit your monthly spending limit.
    *   *Note*: This is also returned under HTTP 429, but with the sub-code `'insufficient_quota'`. Waiting will **not** fix this error. You must add funds to your account dashboard.

---

## 2. Resolving the Quota Error

1.  **Fund Account**: Go to the OpenAI API Billing settings and add a credit card or prepay credit funds.
2.  **Use Free Local Alternatives**: If you want to develop without paying, you can switch from OpenAI to local embeddings using python libraries like **Hugging Face (`sentence-transformers`)** which run completely on your machine for free!

---

## 3. Handling API Failures in Code

In production, you must build robust retry mechanism for API failures (like temporary rate limits).

### Implementation (Exponential Backoff Retry)

```python
import time
import logging
from typing import List
from openai import OpenAI, RateLimitError

app_logger = logging.getLogger("uvicorn.error")

def embed_with_retry(client: OpenAI, texts: List[str], max_retries: int = 3) -> List[List[float]]:
    """Generates embeddings, retrying with exponential backoff if rate-limited."""
    delay = 1.0  # Initial sleep time in seconds
    
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model="text-embedding-3-large",
                input=texts
            )
            return [item.embedding for item in response.data]
            
        except RateLimitError as error:
            # Check if this is an insufficient quota issue (cannot be resolved by retrying)
            error_msg = str(error)
            if "insufficient_quota" in error_msg or "quota" in error_msg.lower():
                app_logger.critical("Billing quota exceeded. Refusing to retry.")
                raise RuntimeError("API Billing Quota Exceeded. Please fund your account.") from error
                
            if attempt == max_retries - 1:
                app_logger.error("Max retries reached. Failing request.")
                raise error
                
            # If it's a standard temporary rate limit, back off and retry
            app_logger.warning(f"Rate limited. Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Double the wait time for the next try
            
        except Exception as general_error:
            app_logger.error(f"Unexpected API error: {str(general_error)}")
            raise general_error
            
    raise RuntimeError("Failed to complete embedding request.")
```

### Unit Tests

```python
import pytest
from unittest.mock import MagicMock
from openai import RateLimitError

def test_embed_with_quota_error() -> None:
    """Verifies that an insufficient quota error raises a RuntimeError immediately without retrying."""
    mock_client = MagicMock()
    # Mocking standard OpenAI RateLimitError for insufficient quota
    mock_response = MagicMock()
    mock_response.status_code = 429
    # Simulate the insufficient_quota message
    mock_client.embeddings.create.side_effect = RateLimitError(
        message="You exceeded your current quota, please check your plan...",
        response=mock_response,
        body={"error": {"type": "insufficient_quota"}}
    )
    
    with pytest.raises(RuntimeError) as error_info:
        embed_with_retry(mock_client, ["test text"])
        
    assert "Billing Quota Exceeded" in str(error_info.value)
    # Assert it gave up immediately after the first check
    assert mock_client.embeddings.create.call_count == 1
```

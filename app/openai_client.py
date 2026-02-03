"""OpenAI API client wrapper with streaming support."""

import queue
import threading
from collections.abc import Callable, Iterable
from typing import Any, cast

from loguru import logger
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


class StreamingClient:
    """OpenAI client with streaming support."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """Initialize OpenAI client."""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self._stop_event = threading.Event()

    def stream_chat_completion(
        self,
        messages: list[dict[str, str]] | list[ChatCompletionMessageParam],
        on_token: Callable[[str], None],
        on_complete: Callable[[str], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """
        Stream chat completion in a background thread.

        Args:
            messages: List of messages for the chat completion
            on_token: Callback for each token received
            on_complete: Callback when streaming completes with full response
            on_error: Callback if an error occurs
        """
        self._stop_event.clear()

        def _stream() -> None:
            try:
                full_response = ""
                # Ensure messages are the expected iterable type for the SDK
                messages_param = cast(Iterable[ChatCompletionMessageParam], messages)
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages_param,
                    stream=True,
                )

                # Cast stream elements to Any for safe attribute access
                stream_any = cast(Iterable[Any], stream)
                for chunk in stream_any:
                    if self._stop_event.is_set():
                        logger.info("Streaming stopped by user")
                        break

                    chunk_any = cast(Any, chunk)
                    if getattr(chunk_any.choices[0].delta, "content", None):
                        token = chunk_any.choices[0].delta.content
                        full_response += token
                        on_token(token)

                if not self._stop_event.is_set():
                    on_complete(full_response)
                    logger.info("Streaming completed successfully")

            except Exception as e:
                logger.error(f"Error during streaming: {e}")
                on_error(e)

        thread = threading.Thread(target=_stream, daemon=True)
        thread.start()

    def stop_streaming(self) -> None:
        """Signal to stop the current streaming operation."""
        self._stop_event.set()
        logger.info("Stop signal sent")


class StreamQueue:
    """Thread-safe queue for streaming tokens to GUI."""

    def __init__(self) -> None:
        """Initialize the queue."""
        self.queue: queue.Queue[str | None] = queue.Queue()
        self._complete = False
        self._error: Exception | None = None

    def add_token(self, token: str) -> None:
        """Add a token to the queue."""
        self.queue.put(token)

    def mark_complete(self) -> None:
        """Mark streaming as complete."""
        self._complete = True
        self.queue.put(None)  # Sentinel value

    def mark_error(self, error: Exception) -> None:
        """Mark streaming as errored."""
        self._error = error
        self.queue.put(None)  # Sentinel value

    def get_token(self, timeout: float = 0.01) -> str | None:
        """
        Get next token from queue.

        Returns:
            Token string, or None if queue is empty or streaming complete
        """
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_complete(self) -> bool:
        """Check if streaming is complete."""
        return self._complete

    def has_error(self) -> bool:
        """Check if streaming encountered an error."""
        return self._error is not None

    def get_error(self) -> Exception | None:
        """Get the error if one occurred."""
        return self._error

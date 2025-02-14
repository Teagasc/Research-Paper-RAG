import reflex as rx


config = rx.Config(
    app_name="chat",
    api_url="http://localhost:8001",  # This is the URL the frontend will use for WebSocket connections.
)

# Security

Recommendations for running `rosbridge` and this project securely:

- Do not expose `rosbridge_server` to untrusted networks. If exposure is required, place a reverse proxy (nginx) with TLS and token-based authentication in front.
- Use firewall rules to restrict access to WebSocket port (default 9090).
- Enable per-client rate limiting via the `client_id` field in `/chat_input` messages (JSON format). The node enforces a basic per-client limit; for stricter controls use an API gateway.
- Monitor `vision/health` topic for unusual activity and set up alerting.

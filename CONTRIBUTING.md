# Contributing

Thank you for contributing to ROS-Chat. Please follow these guidelines:

- Fork the repository and create feature branches named `feat/xxx` or `fix/xxx`.
- Follow commit message style: short summary, blank line, optional body.
- Run linters and tests before opening a PR:

```bash
# Python
pip install -r src/llm_chat_node/requirements-dev.txt
pytest -q src/llm_chat_node/tests

# Frontend
cd frontend
npm ci
npm run test
```

- Add tests for new behavior and update documentation under `docs/`.

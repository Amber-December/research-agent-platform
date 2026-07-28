# OpenAI Compatible Deployment

## Public protocol

- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/responses`

## Launch

1. Deploy the FastAPI app behind HTTPS.
2. Put it behind a reverse proxy such as Nginx or a cloud load balancer.
3. Set `OPENAI_BASE_URL` to `https://YOUR_DOMAIN/v1`.
4. Set `PUBLIC_API_KEY` on this service and use the same value as a normal OpenAI API key with a `Bearer` header.
5. Set `UPSTREAM_MODEL` explicitly when your upstream relay exposes multiple models. Recommended default: `gpt-5.4-mini`.
6. Set upstream runtime variables in `.env`:
   - `UPSTREAM_BASE_URL=https://token4research.cn/v1`
   - `UPSTREAM_API_KEY=...`
   - `UPSTREAM_MODEL=gpt-5.4-mini`
   - `PUBLIC_API_KEY=...`
   - `IMAGE_MODEL=gpt-image-2`

## Client test

```python
from openai import OpenAI

client = OpenAI(api_key="sk-test", base_url="https://YOUR_DOMAIN/v1")
print(client.models.list())
```

## Qingxiaoda plaza integration

- If the plaza supports a custom OpenAI-compatible model endpoint, register `base_url=https://YOUR_DOMAIN/v1`.
- If it requires its own gateway, expose the same `/v1/*` surface on that gateway.
- If it only accepts a fixed internal adapter, add a thin translator service that maps their schema to `/v1/chat/completions` and `/v1/responses`.
- If the platform wants a service registration form, use the public `https://YOUR_DOMAIN/v1` base URL and a bearer token style API key.
- Test against the exact fields the platform expects before going live, especially `stream`, `usage`, and `stop` handling.

## Notes

- OpenAI recommends Responses for new integrations, while Chat Completions remains supported.
- I could not find a public developer document for the plaza's exact registration form, so the final wiring may need the platform admin console or an internal API.
- For presentation-heavy milestones, build the talk deck from experiment artifacts first, then generate page images after outline approval, then review the deck visually before release.

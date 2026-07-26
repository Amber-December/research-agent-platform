# Literature Providers
## Web of Science

- Set `WOS_API_KEY` and optionally `WOS_API_BASE_URL`.
- Default base URL: `https://api.clarivate.com/apis/wos-starter/v1`
- Default database: `WOS`

## CNKI

- Set `CNKI_SEARCH_ENDPOINT` to an institutional relay or licensed API you control.
- Optional auth controls:
  - `CNKI_SEARCH_METHOD` (`GET` or `POST`)
  - `CNKI_API_KEY`
  - `CNKI_AUTH_HEADER`
  - `CNKI_AUTH_SCHEME`

## CNKI payload expectation

The adapter accepts a JSON response containing one of:

- `items`
- `papers`
- `records`
- `data`
- `hits`
- `results`

Each item should include some mix of:

- `title`
- `authors`
- `year`
- `abstract`
- `url`
- `venue`
- `citationCount`

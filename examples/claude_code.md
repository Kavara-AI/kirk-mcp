# Claude Code

Verified against the installed CLI. Personal key as a header:

```sh
claude mcp add --transport http kirk https://kirk-mcp.kavara.ai/mcp \
  -H "Authorization: Bearer k_YOUR_PERSONAL_KEY"
```

Service-token pair instead:

```sh
claude mcp add --transport http kirk https://kirk-mcp.kavara.ai/mcp \
  -H "CF-Access-Client-Id: YOUR_SERVICE_TOKEN_ID" \
  -H "CF-Access-Client-Secret: YOUR_SERVICE_TOKEN_SECRET"
```

Confirm with `claude mcp list`, then ask Claude to call `kirk_verify_engine` —
it is free and returns the engine sha.

Prefer the header forms above to putting the key in the URL: a URL reaches shell
history, process listings and request logs, and a header does not.

# Per-client configuration

Every template points at the same endpoint and the same authentication. Only the
surrounding config shape differs between clients.

| File | Client | Status |
| --- | --- | --- |
| [`claude_code.md`](./claude_code.md) | Claude Code | verified against the CLI |
| [`claude_desktop_config.json`](./claude_desktop_config.json) | Claude Desktop | config shape per Claude Desktop docs |
| [`cursor_mcp_config.json`](./cursor_mcp_config.json) | Cursor | config shape per Cursor docs |
| [`generic_mcp_config.json`](./generic_mcp_config.json) | Grok, VS Code, other MCP clients | **generic** — see note below |
| [`service_token_config.json`](./service_token_config.json) | any, service-token holders | — |
| [`python_client_example.py`](./python_client_example.py) | your own code | — |

## About the generic template

Remote-MCP client configuration has not fully converged. The common shape is
`mcpServers` → `{url, headers}`, and that is what the generic template uses. Two
variations are worth trying if a client does not pick it up:

- the top-level key may be `servers` rather than `mcpServers`;
- `url` and `headers` may need to sit inside a nested `transport` object.

The endpoint, the header and the auth semantics are the same in all of them.

We have deliberately **not** shipped a template claiming to be verified for a
client we have not tested against. If you get Kirk working in Grok, VS Code or
anything else, a PR with the exact config that worked is welcome — that is more
useful than a guess from us.

## If your client accepts only a URL

Some connector dialogs take a URL and no headers. Use the key in the path:

```
https://kirk-mcp.kavara.ai/mcp/k_YOUR_PERSONAL_KEY
```

Same key, same account. Prefer a header wherever headers are supported.

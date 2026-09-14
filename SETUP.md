# Set up Kirk in your AI assistant or IDE

**Copy everything in the box below and paste it into Grok, Claude, Cursor, Copilot
Chat, or whatever assistant you use.** It will work out which client you are on and
configure it. You do not need to read the rest of this repository first.

You will need a credential from Kavara — `sales@kavara.ai`. First 100 inference
units are free per new account.

---

```text
Set up an MCP server for me. Work out the details yourself and ask me only what
you genuinely cannot determine.

SERVER
  name       kirk
  transport  remote MCP over streamable HTTP
  url        https://kirk-mcp.kavara.ai/mcp

AUTHENTICATION
  I hold ONE of these two. Ask me which, and do NOT ask me to paste the secret
  into this chat - write the config with a placeholder and tell me exactly where
  to put the secret myself.

  (a) Personal key: looks like  k_  followed by 32 hex characters.
      As a header (preferred):  Authorization: Bearer k_...
      As a URL, for clients whose "add connector" dialog accepts only a URL:
        https://kirk-mcp.kavara.ai/mcp/k_...
      Same key and same account either way. Prefer the header: a key in a URL
      ends up in shell history, process listings and request logs.

  (b) Cloudflare Access service token: a client id and a client secret.
      Headers: CF-Access-Client-Id and CF-Access-Client-Secret. No URL form.

  Exactly one method is required. Do not send both.

WHAT TO DO
  1. Identify which client I am using and where its MCP configuration lives.
  2. Write the configuration. The shape most clients accept is:

     {"mcpServers":{"kirk":{"url":"https://kirk-mcp.kavara.ai/mcp",
       "headers":{"Authorization":"Bearer PUT_MY_KEY_HERE"}}}}

     If the client does not pick it up, two variations are worth trying: the
     top-level key may be "servers" rather than "mcpServers", and "url" plus
     "headers" may need to sit inside a nested "transport" object.

     For a command-line client such as Claude Code:
       claude mcp add --transport http kirk https://kirk-mcp.kavara.ai/mcp \
         -H "Authorization: Bearer PUT_MY_KEY_HERE"

  3. Tell me if I need to restart the client.
  4. Verify: call kirk_verify_engine. It is free, and returns status ok plus an
     engine sha. Show me the sha and tell me to keep it with any result I save -
     results from different engine builds are not interchangeable.

IF SOMETHING FAILS
  403 that looks like an auth failure - usually the User-Agent, not the
    credential. The CDN rejects some default client agents with a 1010
    "browser signature banned" error that arrives as a 403. Set an explicit
    User-Agent before touching the credential.
  "URL key ... is unknown" - mistyped or revoked. Keys are per person and are
    not shared. Ask Kavara for a new one.
  402 - the account balance is exhausted. Call kirk_billing_show.
  A model that kirk_list_models advertises but which errors when called - the
    catalogue is a list of registered models, not a liveness check. Report it.

COST, SO YOU DO NOT SPEND MY BALANCE BY ACCIDENT
  Free: kirk_verify_engine, kirk_list_models, kirk_render_book,
        kirk_bulk_howto, kirk_billing_show, kirk_billing_usage.
  Metered: kirk_score_book 1 IU per call; kirk_score_book_batch 1 IU per 50
        books; kirk_score_l2_book 1 IU per call.
  Every response carries a _cost block. Do not loop the metered tools from a
  chat: above roughly 200 books call kirk_bulk_howto, which returns a
  self-contained Python client that scores at zero model tokens per book.

Start by asking me which credential I have.
```

---

## If you would rather do it by hand

Per-client configuration files are in [`examples/`](./examples), and the
[README quick start](./README.md#quick-start) has the same settings as plain JSON.

## A note on pasting secrets

The block above tells the assistant to use a placeholder and let you insert the
key yourself. That is deliberate. A key is a bearer credential that spends real
balance, and a chat transcript is not a good place for one. If an assistant asks
you to paste your key into the conversation, put it in the config file instead.

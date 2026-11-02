# Project memory

Read [CURRENT.md](CURRENT.md) first when resuming an interrupted session.
[graph.json](graph.json) records the application, service, feature, and release
relationships without credentials. It is versioned with the source so recovery
does not depend on a particular MCP server or local chat history.

The same application and feature relationships are mirrored in the MCP memory
graph under `Fabrything`. The optional code-review-graph server is a separate code
index; it was unavailable during this release. Its absence does not replace code
review or test verification.

Production evidence lives in the linked release/check documents. Keep credentials,
private environment values, customer information, and live access tokens out of
both this directory and the MCP graph.

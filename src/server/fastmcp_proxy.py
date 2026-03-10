# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
MCP proxy that forwards requests to the Relevance Studio MCP server.

When the upstream MCP server has AUTH_ENABLED=true, configure the proxy to
forward credentials so tool calls succeed. The proxy forwards the Authorization
header from incoming requests to the upstream server. MCP clients should send
either:
  - Basic: Authorization: Basic <base64(username:password)>
  - ApiKey: Authorization: ApiKey <base64(id:api_key)>
  - Bearer: Authorization: Bearer <base64(id:api_key)>

See docs for MCP client credential configuration.
"""

from fastmcp import FastMCP

mcp = FastMCP.as_proxy(
    "http://127.0.0.1:4200/mcp/",
    name="Relevance Studio"
)

if __name__ == "__main__":
    mcp.run()
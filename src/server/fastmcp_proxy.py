# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

from fastmcp import FastMCP

mcp = FastMCP.as_proxy(
    "http://127.0.0.1:4200/mcp/", 
    name="Relevance Studio"
)

if __name__ == "__main__":
    mcp.run()
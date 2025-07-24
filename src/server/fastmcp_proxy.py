from fastmcp import FastMCP

mcp = FastMCP.as_proxy(
    "http://127.0.0.1:4200/mcp/", 
    name="Relevance Studio"
)

if __name__ == "__main__":
    mcp.run()
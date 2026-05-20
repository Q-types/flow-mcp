# Mind MCP v2

Long-term memory MCP server for Claude with semantic search.

## Features

- **Semantic search** using nomic-embed-text-v1.5 embeddings
- **Hybrid retrieval** combining embeddings + BM25 keyword search
- **Decision tracking** with salience-based learning
- **Temporal memory levels** (hours to years)
- **SQLite storage** - zero external dependencies

## Installation

```bash
pip install -e .
```

## Configuration

Add to your Claude Code MCP config (`~/.claude.json`):

```json
{
  "mcpServers": {
    "mind": {
      "command": "python",
      "args": ["-m", "mind_mcp"]
    }
  }
}
```

## Tools

- `mind_health` - Health check and model info
- `mind_remember` - Store a memory with embedding
- `mind_retrieve` - Semantic + keyword search
- `mind_decide` - Track decisions and adjust salience

## Environment Variables

- `MIND_DB_PATH` - Database path (default: `~/.mind/v2/memories.db`)
- `MIND_MODEL` - Embedding model (default: `nomic-ai/nomic-embed-text-v1.5`)

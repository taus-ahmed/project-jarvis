# Groq API Integration Guide

## Why Groq?

The local Ollama models have limitations:
- **Small models (1B-3B)**: Generate malformed JSON and make mistakes
- **Large models (7B+)**: Require more VRAM than available (4GB GPU)

Groq solves both issues:
- ✅ **Large 70B models** for high-quality structured JSON output
- ✅ **Cloud-hosted** - no VRAM requirements
- ✅ **Fast inference** - 500+ tokens/second
- ✅ **Free tier** - generous quota for development

## Setup

### 1. Get Groq API Key

Visit https://console.groq.com/keys and create a free account to get your API key.

### 2. Set Environment Variable

**PowerShell (Windows):**
```powershell
$env:GROQ_API_KEY="gsk_your_api_key_here"
```

**For persistent setup (Windows):**
```powershell
[System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', 'gsk_your_api_key_here', 'User')
```

**Bash/Linux:**
```bash
export GROQ_API_KEY="gsk_your_api_key_here"
```

### 3. Run with Groq

**Interactive mode:**
```bash
node llm-client.js --groq --interactive
```

**Task mode:**
```bash
node llm-client.js --groq --task "Navigate to github.com and take a screenshot"
```

## Available Models

Groq models (recommended):
- `llama-3.3-70b-versatile` (default) - Best quality, structured output
- `llama-3.1-8b-instant` - Faster, still good quality
- `mixtral-8x7b-32768` - Alternative with 32K context

Ollama models (local):
- `llama3.2:1b` - Very fast but lower quality
- `llama3.2:3b` - Good for simple tasks
- `llama3:latest` - Requires 8GB+ VRAM

## Usage Examples

```bash
# Use Groq with llama3-70b (default)
node llm-client.js --groq --interactive

# Use Groq with different model
node llm-client.js --groq --interactive mixtral-8x7b-32768

# Use local Ollama
node llm-client.js --ollama --interactive llama3.2:1b

# Task with Groq
node llm-client.js --groq --task "Search for 'MCP protocol' on Google"

# Task with Ollama
node llm-client.js --ollama --task "Navigate to example.com"
```

## Comparison

| Feature | Local (Ollama) | Cloud (Groq) |
|---------|----------------|--------------|
| Cost | Free | Free tier |
| Speed | Fast | Very fast (500+ tok/s) |
| Quality (1B-3B) | ⚠️ Poor JSON | N/A |
| Quality (70B) | ❌ VRAM needed | ✅ Excellent |
| Privacy | ✅ Local | ⚠️ Cloud API |
| Setup | Requires Ollama | Needs API key |

## Troubleshooting

**"GROQ_API_KEY environment variable not set"**
- Set the environment variable as shown above
- Restart your terminal after setting it

**"HTTP 401 Unauthorized"**
- Check your API key is correct
- Verify it's properly set in the environment

**"Rate limit exceeded"**
- Free tier has limits - wait a moment
- Consider upgrading to paid tier for higher limits

## Architecture

The integration uses:
- OpenAI-compatible chat completions API (`/v1/chat/completions`)
- System prompt with tool descriptions and JSON schema
- Temperature 0.1 for consistent structured output
- Streaming disabled for reliable JSON parsing

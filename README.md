# Project Jarvis - MCP Browser Automation

An intelligent browser automation system powered by **Model Context Protocol (MCP)** and **Large Language Models (LLMs)**. Control your browser using natural language commands with AI-powered decision making.

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/taus-ahmed/project-jarvis.git
cd project-jarvis

# 2. Install dependencies
npm install

# 3. Build the project
npm run build

# 4. Set your Groq API key
$env:GROQ_API_KEY="your_api_key_here"  # Windows PowerShell
# export GROQ_API_KEY="your_api_key_here"  # Linux/Mac

# 5. Run in interactive mode
node llm-client.js --groq --interactive
```

Get your free Groq API key at [console.groq.com/keys](https://console.groq.com/keys)

## 🛠️ Features

- **10 Browser Automation Tools** via MCP protocol
- **Chrome Profile Management** - Use your real Chrome profile with logged-in sessions
- **Natural Language Control** - Describe actions in plain English
- **Dual LLM Support** - Groq Cloud API (70B models) or Local Ollama
- **Persistent Authentication** - Saves browser cookies/storage (`auth_state.json`)
- **Intelligent Element Selection** - Smart CSS, text, aria-label, role selector resolution
- **Page Snapshots** - Get simplified DOM structure for LLM reasoning
- **Screenshots** - Full-page or viewport captures for vision models
- **JavaScript Execution** - Run custom scripts in browser context
- **State Management** - Wait for elements (visible, hidden, attached, detached)

## 📋 Prerequisites

- **Node.js** v18+ - [Download](https://nodejs.org/)
- **Git** - [Download](https://git-scm.com/)
- **Groq API Key** (free) - [Get one](https://console.groq.com/keys)
- **Ollama** (optional) - [Download](https://ollama.com/)

## 🚦 Usage

### Interactive Mode with Groq (Recommended)

```bash
node llm-client.js --groq --interactive
```

**Example commands:**
- "Navigate to github.com"
- "Click on the Sign up button"
- "Fill email with test@example.com"
- "Take a screenshot"
- "Get a snapshot of the page"

### Task Mode (Single Command)

```bash
node llm-client.js --groq --task "Navigate to linkedin.com and click sign up"
```

### Test the MCP Server

```bash
node test-client.js
```

## 🤖 Available Models

**Groq (Cloud):**
- `llama-3.3-70b-versatile` (default) - Best quality
- `llama-3.1-8b-instant` - Faster
- `mixtral-8x7b-32768` - 32K context

**Ollama (Local):**
```bash
node llm-client.js --ollama --interactive llama3.2:3b
```

## 🛠️ Available MCP Tools

1. **browser_navigate** - Navigate to URLs
2. **browser_click** - Click elements
3. **browser_fill_form** - Fill input fields
4. **browser_get_snapshot** - Get interactive DOM elements
5. **browser_screenshot** - Capture screenshots
6. **browser_wait_for** - Wait for elements/timeouts
7. **browser_evaluate** - Execute JavaScript
8. **browser_save_auth** - Save authentication state
9. **browser_list_profiles** - List available Chrome profiles
10. **browser_select_profile** - Switch to a specific Chrome profile

## 📖 Command Examples

```bash
# Navigate and interact
"Navigate to linkedin.com"
"Click on the sign up button"
"Fill Email with myemail@example.com"

# Search
"Navigate to google.com"
"Search for 'artificial intelligence'"
"Click on the first result"

# Screenshots & inspection
"Take a screenshot"
"Get a snapshot of the page"
"Get the page title using JavaScript"
```

## 👤 Chrome Profile Management

**NEW!** Use your real Chrome profile with all your logged-in sessions (Gmail, Amazon, etc.)

When you start the interactive client, it will:
1. Detect all your Chrome profiles automatically
2. Show you a list with names and email addresses
3. Let you select which profile to use
4. Launch Chrome with your selected profile

**Example:**
```bash
node llm-client.js --groq --interactive

# Output:
# 🔍 Checking for Chrome profiles...
# 
# 📂 Found 5 Chrome profile(s):
# 
#   1. Tauseef (taus08ahmed@gmail.com)
#   2. Person 1 (taususethis@gmail.com)
#   3. Your Chrome
#   4. Person 1 (tauseef28ahmed@gmail.com)
#   5. asu.edu (mnola354@asu.edu)
# 
# 👤 Select profile (1-5, or press Enter to skip): 1
# 
# ✅ Browser initialized with profile: Tauseef (taus08ahmed@gmail.com)
# 🌐 Chrome is now open with your profile!
```

**Benefits:**
- Access Gmail, Google Sheets, Amazon with existing logins
- No need to manually log in each time
- Test real-world workflows with your actual accounts
- Skip profile selection to use default test browser

**Manual Profile Commands:**
```bash
# List profiles
{"tool":"browser_list_profiles","arguments":{}}

# Select specific profile
{"tool":"browser_select_profile","arguments":{"directory":"Default"}}
```

## 🏗️ Project Structure

```
project-jarvis/
├── src/
│   └── index.ts          # MCP server (10 browser tools + profile management)
├── llm-client.js         # Interactive LLM client with profile selection
├── test-client.js        # Tool validation
├── test-profiles.js      # Profile management testing
├── GROQ_SETUP.md         # Groq integration guide
└── README.md             # This file
```

## 🐛 Troubleshooting

**"GROQ_API_KEY not set"**
```powershell
$env:GROQ_API_KEY="your_key_here"
```

**"Could not resolve selector"**
- Be more specific: "Sign in button" vs "button"
- Use exact text: "Click on 'Get Started'"
- Take a screenshot first

**Browser doesn't launch**
```bash
npx playwright install chromium
```

## 📚 Documentation

- [MCP Protocol](https://modelcontextprotocol.io/docs)
- [Playwright Docs](https://playwright.dev/)
- [Groq API](https://console.groq.com/docs)
- [GROQ_SETUP.md](./GROQ_SETUP.md)

## 🔐 Security

- Never commit `auth_state.json`
- Keep API keys private
- Use test accounts for automation

## MCP Integration

### Option 1: Direct Execution
```bash
npm run dev
```

### Option 2: MCP Configuration

Add to your MCP client configuration (e.g., Claude Desktop, Cline):

```json
{
  "mcpServers": {
    "browser-automation": {
      "command": "node",
      "args": ["f:\\Browser\\dist\\index.js"],
      "env": {}
    }
  }
}
```

### Option 3: stdio Integration

```javascript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "node",
  args: ["f:\\Browser\\dist\\index.js"]
});

const client = new Client({
  name: "browser-client",
  version: "1.0.0"
}, {
  capabilities: {}
});

await client.connect(transport);
```

## Tool Examples

### Navigate to a Website
```json
{
  "name": "browser_navigate",
  "arguments": {
    "url": "https://github.com/login",
    "waitUntil": "networkidle"
  }
}
```

### Get Page Structure (for LLM)
```json
{
  "name": "browser_get_snapshot",
  "arguments": {
    "simplified": true
  }
}
```

Response includes interactive elements with selectors and positions:
```json
{
  "url": "https://github.com/login",
  "title": "Sign in to GitHub",
  "elements": [
    {
      "index": 0,
      "tag": "input",
      "type": "text",
      "text": "",
      "placeholder": "Username or email address",
      "selector": "input#login_field",
      "position": { "x": 100, "y": 150, "width": 300, "height": 40 }
    }
  ]
}
```

### Fill Form and Submit
```json
// Fill username
{
  "name": "browser_fill_form",
  "arguments": {
    "selector": "Username or email address",
    "value": "myusername"
  }
}

// Fill password
{
  "name": "browser_fill_form",
  "arguments": {
    "selector": "Password",
    "value": "mypassword"
  }
}

// Click submit
{
  "name": "browser_click",
  "arguments": {
    "selector": "Sign in"
  }
}
```

### Save Authentication
```json
{
  "name": "browser_save_auth",
  "arguments": {}
}
```

### Capture Screenshot (Vision Model Fallback)
```json
{
  "name": "browser_screenshot",
  "arguments": {
    "filename": "login-page.png",
    "fullPage": false
  }
}
```

## Workflow: LLM-Driven Automation

1. **LLM asks**: "Navigate to GitHub and login"
2. **Tool**: `browser_navigate` → GitHub login page
3. **Tool**: `browser_get_snapshot` → LLM sees form structure
4. **LLM identifies**: Username field, password field, submit button
5. **Tool**: `browser_fill_form` × 2 → Fill credentials
6. **Tool**: `browser_click` → Submit form
7. **Tool**: `browser_save_auth` → Persist session

On subsequent runs, the saved auth state is automatically loaded.

## Hybrid Approach: Code + Vision

When code-based selectors fail:
1. Tool returns error with suggestion
2. LLM calls `browser_screenshot`
3. Screenshot sent to vision model (Qwen-VL, GPT-4V)
4. Vision model returns coordinates $(x, y)$
5. LLM uses `browser_evaluate` with coordinate-based click

Example coordinate-based click:
```json
{
  "name": "browser_evaluate",
  "arguments": {
    "script": "document.elementFromPoint(450, 320).click()"
  }
}
```

## Architecture

```
┌─────────────────┐
│   LLM Client    │
│ (Llama/Mistral) │
└────────┬────────┘
         │ MCP Protocol (stdio/SSE)
         │
┌────────▼────────┐
│   MCP Server    │
│  (This Project) │
├─────────────────┤
│ • Tool Router   │
│ • Auth Manager  │
│ • Selector AI   │
└────────┬────────┘
         │
┌────────▼────────┐
│   Playwright    │
│   (Chromium)    │
└─────────────────┘
```

## Files and Directories

```
f:\Browser/
├── src/
│   └── index.ts           # Main MCP server implementation
├── dist/                  # Compiled JavaScript (generated)
├── downloads/             # Browser downloads (auto-created)
├── screenshots/           # Captured screenshots (auto-created)
├── auth_state.json        # Persistent authentication (generated)
├── package.json
├── tsconfig.json
└── README.md
```

## Configuration

Edit these constants in [src/index.ts](src/index.ts) to customize:

```typescript
const AUTH_STATE_FILE = path.join(process.cwd(), "auth_state.json");
const DOWNLOADS_DIR = path.join(process.cwd(), "downloads");
const SCREENSHOTS_DIR = path.join(process.cwd(), "screenshots");
```

Browser launch options:
```typescript
browser = await chromium.launch({
  headless: false,  // Set to true for background operation
  args: ['--disable-blink-features=AutomationControlled']
});
```

## Advanced Usage

### Custom JavaScript Execution
```json
{
  "name": "browser_evaluate",
  "arguments": {
    "script": "return document.querySelectorAll('a').length"
  }
}
```

### Wait for Dynamic Content
```json
{
  "name": "browser_wait_for",
  "arguments": {
    "selector": ".loading-spinner",
    "state": "hidden",
    "timeout": 10000
  }
}
```

### Full Accessibility Tree (Raw)
```json
{
  "name": "browser_get_snapshot",
  "arguments": {
    "simplified": false
  }
}
```

## Integration with Filesystem MCP

Downloaded files and screenshots are stored in accessible directories:
- `./downloads/` - Files downloaded via browser
- `./screenshots/` - Captured screenshots

Your Filesystem MCP can read these directories to provide files to the LLM.

## Troubleshooting

**Browser doesn't start:**
```bash
npx playwright install chromium
```

**Auth state not loading:**
- Check `auth_state.json` exists and is valid JSON
- Manually trigger `browser_save_auth` after logging in
- Check file permissions

**Selector not found:**
- Use `browser_get_snapshot` to see available elements
- Try text-based selectors instead of CSS
- Fall back to `browser_screenshot` + vision model

## Security Considerations

⚠️ **Important:**
- `auth_state.json` contains sensitive session data
- Do not commit this file to version control
- Use appropriate file permissions
- Consider encrypting the auth state for production

## Development

```bash
# Watch mode for development
npm run watch

# In another terminal
npm start

# Clean build artifacts
npm run clean
```

## License

MIT

## Credits

Built with:
- [@modelcontextprotocol/sdk](https://github.com/modelcontextprotocol/sdk)
- [Playwright](https://playwright.dev/)
- [Zod](https://zod.dev/)

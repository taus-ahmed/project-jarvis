#!/usr/bin/env node

/**
 * Ollama/Groq MCP Browser Client
 * Connects LLM (Ollama or Groq) to MCP Browser Automation Server
 * Allows natural language browser automation
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import readline from "readline";
import fetch from "node-fetch";
import { promises as fs } from "fs";
import path from "path";
import {
  findSimilarSequences,
  storeInteraction,
  formatSequenceForLLM
} from "./interaction-memory.js";

let mcpClient = null;
let availableTools = [];
let transport = null;

// Browser context tracking
let lastUrl = "";
let lastTitle = "";

// LLM configuration
const OLLAMA_API = "http://localhost:11434/api/generate";
const GROQ_API = "https://api.groq.com/openai/v1/chat/completions";
let selectedModel = "llama3-70b-8192"; // Default Groq model
let useGroq = false;
let groqApiKey = "";

async function loadGroqApiKey() {
  if (process.env.GROQ_API_KEY) return process.env.GROQ_API_KEY;

  const candidates = ["groq.config.json", "config.json"];
  for (const file of candidates) {
    try {
      const data = await fs.readFile(path.join(process.cwd(), file), "utf-8");
      const json = JSON.parse(data);
      const key = json.GROQ_API_KEY || json.groqApiKey;
      if (key) return key;
    } catch (error) {
      // ignore missing or invalid files
    }
  }

  return "";
}

function parseTextContent(result) {
  const text = result?.content?.[0]?.text;
  if (!text) return result;
  try {
    return JSON.parse(text);
  } catch (err) {
    return text;
  }
}

async function connectMCP() {
  console.log("🔗 Connecting to MCP Browser Server...");

  transport = new StdioClientTransport({
    command: "node",
    args: ["dist/index.js"],
  });

  mcpClient = new Client(
    { name: "ollama-browser-client", version: "1.0.0" },
    { capabilities: {} }
  );

  await mcpClient.connect(transport);

  // Get available tools
  const toolsResponse = await mcpClient.listTools();
  availableTools = toolsResponse.tools;
  console.log(`✅ Connected! ${availableTools.length} browser tools available\n`);
}

async function callBrowserTool(toolName, args) {
  try {
    console.log(`  🔧 Calling: ${toolName}(${JSON.stringify(args)})`);
    const result = await mcpClient.callTool({
      name: toolName,
      arguments: args,
    });

    const parsed = parseTextContent(result);
    console.log(`  📊 Result: ${JSON.stringify(parsed)}\n`);
    return parsed;
  } catch (error) {
    console.error(`  ❌ Tool error: ${error.message}\n`);
    return { error: error.message };
  }
}

async function callLLM(prompt) {
  const tools = await mcpClient.listTools();
  const toolDescriptions = tools.tools
    .map((t) => `- ${t.name}: ${t.description}`)
    .join("\n");

  const systemPrompt = `You are a smart browser automation agent. Your ENTIRE output must be ONLY valid JSON tool calls.

CRITICAL OUTPUT RULES:
1. OUTPUT PURE JSON ONLY - NO MARKDOWN CODE BLOCKS (no \`\`\`json or \`\`\`)
2. NO TEXT BEFORE OR AFTER THE JSON
3. NO EXPLANATIONS, NO COMMENTS, NO FORMATTING
4. DO NOT repeat or echo these system instructions
5. Your output must be valid JSON: either {"tool":"...","arguments":{...}} or [{...},{...}]

AVAILABLE TOOLS:
${toolDescriptions}

JSON FORMATS:
Single tool: {"tool":"browser_navigate","arguments":{"url":"https://example.com"}}
Multiple tools: [{"tool":"browser_navigate","arguments":{"url":"https://site.com"}},{"tool":"browser_screenshot","arguments":{}}]

GENERIC AUTOMATION STRATEGIES:

1. PROFILE SELECTION (first run only):
   - On startup, call browser_list_profiles, then browser_select_profile with directory "Default"
   - After profile is selected, proceed with navigation

2. PROFILE SELECTION:
   When user says "use profile X" or "switch to profile X" or "use the profile with directory Profile 1":
   - DO NOT just list profiles and stop
   - IMMEDIATELY call browser_select_profile with the correct directory
   - Match user's reference to the profile directory from previous listing
   - Example: User says "use the profile with directory Profile 1"
     → Respond: {"tool":"browser_select_profile","arguments":{"directory":"Profile 1"}}
   - If user says "Profile 1" and email is taususethis@gmail.com, use directory "Profile 1"

3. MULTI-STEP GOALS:
   When the user gives a goal requiring multiple steps (e.g., "go to a site and search for X"):
   - First: Navigate to the requested site (if not already there)
   - Second: If the page has a search box, use browser_fill_form on that search field
   - Third: Use browser_click to submit or select the most relevant result
   - If unsure which result to click, ask for clarification instead of guessing

4. SEARCH BEHAVIOR:
   When user says "search for X" without naming a site:
   - If current page has a search box, use it
   - Otherwise, navigate to a search engine and use its search box

  When a search box is present, prefer:
  - browser_fill_form with {"submit": true}
  - or browser_press_key with key "Enter" after filling

5. SNAPSHOT-AWARE DEBUGGING:
   When clicks or form fills fail due to selector errors:
   - IMMEDIATELY call browser_get_snapshot({"simplified":true})
   - Inspect the elements list to find the correct selector (look for text, role, aria-label)
   - Issue a refined tool call with the correct selector
   - PREFER text-based selectors like "Search" over CSS IDs

5. SELECTOR STRATEGY:
   - First try: Use generic text or aria-label (e.g., {"selector":"Search"})
   - If that fails: System auto-fetches snapshot - use selectors from elements list
   - For attribute selectors with quotes, escape properly: {"selector":"a[href*=\\\"text\\\"]"}
   - NEVER use unescaped quotes: {"selector":"a[href*="bad"]"} ← WRONG, breaks JSON

6. URL CONSTRUCTION:
   - Always use full HTTPS URLs like "https://example.com"
   - Never use relative paths or placeholders

7. EMAIL COMPOSITION (Gmail or webmail):
  When the user asks to write/compose/email someone or provides a context to send:
  - You MUST draft a concise subject and body based on the user's context.
  - Then call tools to open compose UI and fill:
    • To: recipient address
    • Subject: generated subject
    • Body: generated body
  - Prefer selectors by visible labels: "To", "Subject", "Message Body".
  - If selectors fail, call browser_get_snapshot and retry with correct selectors.
  - NEVER click Send unless the user explicitly asks to send.

TOOL EXAMPLES (use as patterns, not literal copies):
- List profiles: {"tool":"browser_list_profiles","arguments":{}}
- Select profile: {"tool":"browser_select_profile","arguments":{"directory":"Default"}}
- Navigate: {"tool":"browser_navigate","arguments":{"url":"https://..."}}
- Click: {"tool":"browser_click","arguments":{"selector":"Button Text or CSS"}}
- Fill: {"tool":"browser_fill_form","arguments":{"selector":"input name or label","value":"text"}}
- Fill+Submit: {"tool":"browser_fill_form","arguments":{"selector":"Search","value":"query","submit":true}}
- Press key: {"tool":"browser_press_key","arguments":{"key":"Enter"}}
- Snapshot: {"tool":"browser_get_snapshot","arguments":{"simplified":true}}
- Screenshot: {"tool":"browser_screenshot","arguments":{}}
- Scroll: {"tool":"browser_scroll","arguments":{"to":"bottom"}}

REMEMBER: Output ONLY valid JSON. No explanations, no echoing instructions.`;

  if (useGroq) {
    return await callGroq(systemPrompt, prompt);
  } else {
    return await callOllama(systemPrompt, prompt);
  }
}

async function callGroq(systemPrompt, userPrompt) {
  try {
    const response = await fetch(GROQ_API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${groqApiKey}`
      },
      body: JSON.stringify({
        model: selectedModel,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.1,
        max_tokens: 1000
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    
    if (!data || !data.choices || !data.choices[0] || !data.choices[0].message) {
      console.error(`Groq API response:`, data);
      throw new Error('Invalid response from Groq');
    }
    
    return data.choices[0].message.content.trim();
  } catch (error) {
    console.error(`Groq error: ${error.message}`);
    return null;
  }
}

async function callOllama(systemPrompt, userPrompt) {
  try {
    const response = await fetch(OLLAMA_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: selectedModel,
        prompt: `${systemPrompt}\n\n${userPrompt}\n\nRespond with ONLY JSON:`,
        stream: false,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    
    if (!data || !data.response) {
      console.error(`Ollama API response:`, data);
      throw new Error('Invalid response from Ollama - response field missing');
    }
    
    return data.response.trim();
  } catch (error) {
    console.error(`Ollama error: ${error.message}`);
    return null;
  }
}

async function executeBrowserAction(userInput, conversationHistory) {
  console.log("\n🤖 LLM thinking...");

  // Build context-aware user prompt
  const contextLine = lastUrl
    ? `Current URL: ${lastUrl}. Current page title: ${lastTitle || "unknown"}.`
    : `Current URL: unknown (no navigation yet).`;
  
  let userPromptWithContext = `${contextLine}\nUser request: ${userInput}`;

  // Email compose hint
  const emailIntent = /(gmail|email|mail|compose|write.*mail|send.*mail)/i.test(userInput) && /@/.test(userInput);
  if (emailIntent) {
    userPromptWithContext += `\n\nEmail drafting requirement: generate a concise subject and body from the user's context, then fill To/Subject/Message Body using tool calls. Do NOT send unless explicitly asked.`;
  }

  // Try interaction memory for similar sequences
  if (lastUrl) {
    try {
      const matches = await findSimilarSequences(lastUrl, userInput, 0.6);
      if (matches.length > 0) {
        const topMatches = matches.slice(0, 2).map(formatSequenceForLLM).join("\n");
        userPromptWithContext += `\n\nRelevant cached interactions:\n${topMatches}`;
      }
    } catch (error) {
      console.error(`⚠️  Memory lookup failed: ${error.message}`);
    }
  }

  const llmResponse = await callLLM(userPromptWithContext);
  
  // Strong validation: reject null/empty responses
  if (!llmResponse || llmResponse.trim() === "") {
    console.log("⚠️  LLM returned empty response.\n");
    return conversationHistory;
  }

  console.log(`💬 LLM Response:\n${llmResponse}\n`);

  // Strip markdown code blocks if present (fallback for misbehaving LLM)
  let cleanedResponse = llmResponse.trim();
  if (cleanedResponse.startsWith('```')) {
    // Remove ```json or ``` from start and ``` from end
    cleanedResponse = cleanedResponse.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '').trim();
    console.log(`⚠️  Stripped markdown code blocks from response\n`);
  }

  // Handle multi-line JSON (separate objects on different lines)
  if (!cleanedResponse.startsWith('[')) {
    const multilineMatch = cleanedResponse.match(/(}\s*\n\s*{)/g);
    if (multilineMatch && multilineMatch.length > 0) {
      // Convert multiple JSON objects to array: {}{} -> [{},{}]
      const lines = cleanedResponse.split('\n').filter(l => l.trim());
      cleanedResponse = '[' + lines.join(',') + ']';
      console.log(`⚠️  Converted multi-line JSON (${lines.length} objects) to array\n`);
    }
  }

  // Strong JSON validation
  let toolCalls = [];
  try {
    const parsed = JSON.parse(cleanedResponse);
    
    if (Array.isArray(parsed)) {
      // Multiple tool calls - validate each has tool and arguments
      toolCalls = parsed.filter(call => call && typeof call === 'object' && call.tool && call.arguments);
      if (toolCalls.length === 0) {
        console.log("⚠️  Array contains no valid tool calls.\n");
        conversationHistory.push({ role: "user", content: userInput });
        conversationHistory.push({ 
          role: "assistant", 
          content: "I couldn't extract any tool calls. I must respond with JSON objects like {\"tool\":\"browser_navigate\",\"arguments\":{...}}."
        });
        return conversationHistory;
      }
    } else if (parsed && typeof parsed === 'object' && parsed.tool && parsed.arguments) {
      // Single tool call
      toolCalls = [parsed];
    } else {
      console.log("⚠️  Response is JSON but not in expected tool format.\n");
      conversationHistory.push({ role: "user", content: userInput });
      conversationHistory.push({ 
        role: "assistant", 
        content: "I must respond with JSON tool calls only. The format should be {\"tool\":\"tool_name\",\"arguments\":{...}} or an array of such objects."
      });
      return conversationHistory;
    }

    console.log("🔄 Executing tool calls...\n");
    let results = [];
    const steps = [];
    let allSuccess = true;

    for (const call of toolCalls) {
      const result = await callBrowserTool(call.tool, call.arguments);
      results.push(result);
      const stepSuccess = !!(result && result.success);
      allSuccess = allSuccess && stepSuccess;
      steps.push({
        action: call.tool,
        arguments: call.arguments || {},
        timestamp: Date.now(),
        success: stepSuccess
      });
      
      // Store profile list in context for future decisions
      if (call.tool === "browser_list_profiles" && result && result.success && result.profiles) {
        conversationHistory.push({
          role: "system",
          content: `Available profiles: ${JSON.stringify(result.profiles.map(p => ({name: p.name, email: p.email, directory: p.directory})))}`
        });
      }
      
      // Update context if navigation succeeded
      if (call.tool === "browser_navigate" && result && result.success) {
        lastUrl = result.url || lastUrl;
        lastTitle = result.title || lastTitle;
        console.log(`📍 Context updated: ${lastUrl}\n`);
      }
      
      // Auto-fetch snapshot on selector failures
      if (!result.success && result.error && (
        result.error.includes("Could not resolve selector") ||
        result.error.includes("Timeout") ||
        result.error.includes("element is not visible")
      )) {
        console.log(`🔍 Selector failed, auto-fetching page snapshot...\n`);
        const snapshotResult = await callBrowserTool("browser_get_snapshot", {"simplified": true});
        if (snapshotResult && snapshotResult.elements) {
          console.log(`📸 Found ${snapshotResult.elements.length} elements on page\n`);
          // Add snapshot to conversation so LLM can see correct selectors
          conversationHistory.push({
            role: "system",
            content: `Previous selector failed. Here are the actual elements on the page:\n${JSON.stringify(snapshotResult.elements.slice(0, 30), null, 2)}\n\nUse the correct selector from this list and retry your operation.`
          });
        }
      }
      
      await new Promise((r) => setTimeout(r, 500));
    }

    conversationHistory.push({ role: "user", content: userInput });
    conversationHistory.push({
      role: "assistant",
      content: `Executed: ${toolCalls.map((c) => c.tool).join(", ")}`,
    });

    if (lastUrl && steps.length > 0) {
      try {
        await storeInteraction(lastUrl, userInput, steps, allSuccess);
      } catch (error) {
        console.error(`⚠️  Memory store failed: ${error.message}`);
      }
    }
  } catch (e) {
    console.log(`⚠️  Failed to parse JSON: ${e.message}`);
    console.log(`📝 Response preview: ${cleanedResponse.substring(0, 100)}...\n`);
    conversationHistory.push({ role: "user", content: userInput });
    conversationHistory.push({
      role: "assistant",
      content: `Error: Invalid JSON in response. ${e.message}. I must respond with ONLY valid JSON like {"tool":"...","arguments":{...}} or [{...},{...}].`,
    });
  }

  return conversationHistory;
}

async function interactiveMode() {
  await connectMCP();

  const providerName = useGroq ? "Groq" : "Ollama";
  console.log(`🤖 Provider: ${providerName}`);
  console.log(`🤖 Model: ${selectedModel}`);
  console.log("💡 Examples:");
  console.log("  - Navigate to github.com");
  console.log("  - Search for 'javascript tutorials'");
  console.log("  - Take a screenshot\n");
  console.log("Type 'exit' to quit\n");

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  let conversationHistory = [];

  // Initial startup: let LLM select a profile
  console.log("🔧 Initializing browser profiles...\n");
  try {
    conversationHistory = await executeBrowserAction(
      "List profiles with browser_list_profiles, then select Default profile with browser_select_profile using directory \"Default\"",
      conversationHistory
    );
  } catch (error) {
    console.error(`⚠️  Profile initialization error: ${error.message}`);
  }

  console.log("\n✅ Ready for commands!\n");

  const askQuestion = () => {
    rl.question("You: ", async (input) => {
      if (input.toLowerCase() === "exit") {
        console.log("\n👋 Goodbye!");
        await mcpClient.close();
        await transport.close();
        process.exit(0);
      }

      if (input.trim()) {
        try {
          conversationHistory = await executeBrowserAction(
            input,
            conversationHistory
          );
        } catch (error) {
          console.error(`❌ Error: ${error.message}`);
        }
      }

      askQuestion();
    });
  };

  askQuestion();
}

async function runTask(taskDescription) {
  await connectMCP();

  console.log(`\n📋 Task: ${taskDescription}\n`);

  let history = [];
  const result = await executeBrowserAction(taskDescription, history);

  await mcpClient.close();
  await transport.close();
  process.exit(0);
}

// Main
groqApiKey = await loadGroqApiKey();

const args = process.argv.slice(2);

// DEFAULT: Use Groq 70B if API key is available
if (groqApiKey) {
  useGroq = true;
  selectedModel = "llama-3.3-70b-versatile";
  console.log("🎯 Auto-detected Groq API key, using llama-3.3-70b-versatile by default\n");
}

if (args.length === 0) {
  console.log("❌ Usage:");
  console.log("  Interactive (default Groq 70B): node llm-client.js --interactive");
  console.log("  Interactive (Ollama):           node llm-client.js --ollama --interactive [model]");
  console.log("  Task (default Groq 70B):        node llm-client.js --task 'task description'");
  console.log("\nGroq Models: llama-3.3-70b-versatile (default), llama-3.1-8b-instant, mixtral-8x7b-32768");
  console.log("Ollama Models: llama3.2:3b, llama3.1:8b, llama3:latest");
  console.log("\nExamples:");
  console.log("  node llm-client.js --interactive                  # Uses Groq 70B (recommended)");
  console.log("  node llm-client.js --ollama --interactive llama3.2:3b");
  console.log("  node llm-client.js --task 'Navigate to github.com and take a screenshot'");
  console.log("\nGroq API key sources (checked in order):");
  console.log("  1) GROQ_API_KEY env var");
  console.log("  2) groq.config.json (GROQ_API_KEY or groqApiKey)");
  console.log("  3) config.json (GROQ_API_KEY or groqApiKey)");
  process.exit(1);
}

// Parse provider and model (can override defaults)
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--groq') {
    useGroq = true;
    if (!selectedModel || selectedModel.includes("llama3.2")) {
      selectedModel = "llama-3.3-70b-versatile"; // Groq default
    }
  } else if (args[i] === '--ollama') {
    useGroq = false;
    selectedModel = "llama3.2:3b"; // Better Ollama default (not 1B)
  } else if (args[i] === '--interactive' && args[i + 1] && !args[i + 1].startsWith('--')) {
    selectedModel = args[i + 1];
    i++; // skip next arg
  }
}

// Validate Groq API key if using Groq
if (useGroq && !groqApiKey) {
  console.error("❌ GROQ_API_KEY not set.");
  console.error("   Provide it via environment or groq.config.json/config.json (field GROQ_API_KEY or groqApiKey)");
  console.error("   Get one at: https://console.groq.com/keys");
  process.exit(1);
}

const mode = args.find(arg => arg === '--interactive' || arg === '--task');

// If no mode specified but has interactive flag, default to interactive
if (!mode && args.length > 0) {
  const nonFlagArgs = args.filter(arg => !arg.startsWith('--'));
  if (nonFlagArgs.length === 0) {
    console.log("🎯 No mode specified, defaulting to --interactive");
    args.push('--interactive');
  }
}

if (mode === "--interactive" || args.includes('--interactive')) {
  interactiveMode().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
} else if (mode === "--task") {
  // Extract task from args after --task
  const taskIndex = args.indexOf('--task');
  const taskArgs = args.slice(taskIndex + 1).filter(arg => !arg.startsWith('--'));
  const task = taskArgs.join(" ");
  
  if (!task) {
    console.error("❌ Task description required after --task");
    process.exit(1);
  }
  
  runTask(task).catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });
} else {
  console.log("❌ Invalid arguments");
  process.exit(1);
}


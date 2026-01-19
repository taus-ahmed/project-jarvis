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

let mcpClient = null;
let availableTools = [];
let transport = null;

// LLM configuration
const OLLAMA_API = "http://localhost:11434/api/generate";
const GROQ_API = "https://api.groq.com/openai/v1/chat/completions";
let selectedModel = "llama3-70b-8192"; // Default Groq model
let useGroq = false;
let groqApiKey = process.env.GROQ_API_KEY || "";

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

  const systemPrompt = `You are a browser automation agent. RESPOND WITH ONLY VALID JSON.

AVAILABLE TOOLS:
${toolDescriptions}

RESPOND WITH EXACTLY ONE of these formats:

FORMAT 1 - Single tool:
{"tool":"browser_navigate","arguments":{"url":"https://example.com"}}

FORMAT 2 - Multiple tools (ARRAY):
[{"tool":"browser_navigate","arguments":{"url":"https://github.com"}},{"tool":"browser_screenshot","arguments":{}}]

IMPORTANT RULES:
1. ONLY respond with JSON - NO OTHER TEXT
2. For navigate: use full HTTPS URL like "https://github.com"
3. Never use placeholder URLs like "/path/to/page"
4. Use exact tool names: browser_navigate, browser_click, browser_fill_form, browser_get_snapshot, browser_screenshot, browser_save_auth, browser_evaluate, browser_wait_for
5. Arguments must match the tool (check examples below)

TOOL ARGUMENT EXAMPLES:
- navigate: {"tool":"browser_navigate","arguments":{"url":"https://..."}}
- click: {"tool":"browser_click","arguments":{"selector":"Button Text"}}
- fill: {"tool":"browser_fill_form","arguments":{"selector":"Email","value":"test@example.com"}}
- snapshot: {"tool":"browser_get_snapshot","arguments":{"simplified":true}}
- screenshot: {"tool":"browser_screenshot","arguments":{}}
- save: {"tool":"browser_save_auth","arguments":{}}
- evaluate: {"tool":"browser_evaluate","arguments":{"script":"document.title"}}
- wait: {"tool":"browser_wait_for","arguments":{"selector":"button","state":"visible"}}

NEVER output anything except valid JSON.`;

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
        prompt: `${systemPrompt}\n\nUser request: ${userPrompt}\n\nRespond with ONLY JSON:`,
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

  const llmResponse = await callLLM(userInput);
  if (!llmResponse) return conversationHistory;

  console.log(`💬 Ollama:\n${llmResponse}\n`);

  // Try to parse as tool calls with validation
  let toolCalls = [];
  try {
    const parsed = JSON.parse(llmResponse);
    
    if (Array.isArray(parsed)) {
      // Multiple tool calls
      toolCalls = parsed.filter(call => call.tool && call.arguments);
    } else if (parsed.tool && parsed.arguments) {
      // Single tool call
      toolCalls = [parsed];
    } else {
      console.log("⚠️  Response is JSON but not in tool format. Please rephrase.\n");
      conversationHistory.push({ role: "user", content: userInput });
      conversationHistory.push({ role: "assistant", content: "I couldn't understand that request. Please be more specific (e.g., 'Navigate to github.com' or 'Take a screenshot')." });
      return conversationHistory;
    }
    
    if (toolCalls.length === 0) {
      console.log("⚠️  No valid tool calls found.\n");
      return conversationHistory;
    }

    console.log("🔄 Executing tool calls...\n");
    let results = [];

    for (const call of toolCalls) {
      const result = await callBrowserTool(call.tool, call.arguments);
      results.push(result);
      await new Promise((r) => setTimeout(r, 500));
    }

    conversationHistory.push({ role: "user", content: userInput });
    conversationHistory.push({
      role: "assistant",
      content: `Executed: ${toolCalls.map((c) => c.tool).join(", ")}`,
    });
  } catch (e) {
    console.log(`⚠️  Invalid JSON response. Please try again.\n`);
    conversationHistory.push({ role: "user", content: userInput });
    conversationHistory.push({
      role: "assistant",
      content: "I need to respond with JSON tool calls. Please rephrase your request.",
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
const args = process.argv.slice(2);

if (args.length === 0) {
  console.log("❌ Usage:");
  console.log("  Interactive (Groq):   node llm-client.js --groq --interactive [model]");
  console.log("  Interactive (Ollama): node llm-client.js --ollama --interactive [model]");
  console.log("  Task (Groq):          node llm-client.js --groq --task 'task description'");
  console.log("  Task (Ollama):        node llm-client.js --ollama --task 'task description'");
  console.log("\nGroq Models: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768");
  console.log("Ollama Models: llama3.2:1b, llama3.2:3b, llama3:latest");
  console.log("\nExamples:");
  console.log("  node llm-client.js --groq --interactive");
  console.log("  node llm-client.js --ollama --interactive llama3.2:1b");
  console.log("  node llm-client.js --groq --task 'Navigate to github.com and take a screenshot'");
  console.log("\nNote: Set GROQ_API_KEY environment variable for Groq");
  process.exit(1);
}

// Parse provider and model
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--groq') {
    useGroq = true;
    selectedModel = "llama-3.3-70b-versatile"; // default Groq model
  } else if (args[i] === '--ollama') {
    useGroq = false;
    selectedModel = "llama3.2:1b"; // default Ollama model
  } else if (args[i] === '--interactive' && args[i + 1] && !args[i + 1].startsWith('--')) {
    selectedModel = args[i + 1];
  }
}

// Validate Groq API key
if (useGroq && !groqApiKey) {
  console.error("❌ GROQ_API_KEY environment variable not set!");
  console.error("   Set it with: $env:GROQ_API_KEY=\"your_api_key_here\"");
  console.error("   Get one at: https://console.groq.com/keys");
  process.exit(1);
}

const mode = args.find(arg => arg === '--interactive' || arg === '--task');

if (mode === "--interactive") {
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


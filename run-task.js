#!/usr/bin/env node

/**
 * Pre-built Browser Automation Tasks
 * Run these with: node run-task.js <task-name> [model]
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import fetch from "node-fetch";

let mcpClient = null;
let transport = null;
let selectedModel = "llama2";

const OLLAMA_API = "http://localhost:11434/api/generate";

// Pre-built automation tasks
const TASKS = {
  github: "Navigate to github.com, take a screenshot, get the page snapshot to see the layout",
  
  search: "Navigate to google.com, fill the search box with 'web automation', click the search button, wait 3 seconds, then take a screenshot",
  
  weather: "Navigate to weather.com, take a screenshot and describe what you see",
  
  screenshot_example: "Navigate to example.com and capture a screenshot of the page",
  
  form_demo: "Navigate to http://localhost:3000/demo (if available), fill a form if present, and take a screenshot",
};

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
    { name: "task-runner", version: "1.0.0" },
    { capabilities: {} }
  );

  await mcpClient.connect(transport);
  console.log("✅ Connected to browser server\n");
}

async function callBrowserTool(toolName, args) {
  try {
    console.log(`  🔧 ${toolName}`);
    const result = await mcpClient.callTool({
      name: toolName,
      arguments: args,
    });

    return parseTextContent(result);
  } catch (error) {
    return { error: error.message };
  }
}

async function callOllama(prompt) {
  const tools = await mcpClient.listTools();
  const toolDescriptions = tools.tools
    .map((t) => `- ${t.name}: ${t.description}`)
    .join("\n");

  const systemPrompt = `You are a browser automation agent. You MUST respond with ONLY valid JSON tool calls, nothing else.

Available tools:
${toolDescriptions}

When responding, output ONLY a JSON array of tool calls like this:
[{"tool": "browser_navigate", "arguments": {"url": "..."}}, {"tool": "browser_screenshot", "arguments": {}}]

Or a single tool call:
{"tool": "browser_navigate", "arguments": {"url": "..."}}

IMPORTANT: Respond with ONLY valid JSON, no other text.`;

  try {
    const response = await fetch(OLLAMA_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: selectedModel,
        prompt: `${systemPrompt}\n\nTask: ${prompt}\n\nRespond with only JSON:`,
        stream: false,
      }),
    });

    const data = await response.json();
    return data.response.trim();
  } catch (error) {
    console.error(`Ollama error: ${error.message}`);
    return null;
  }
}

async function executeToolCalls(toolCalls) {
  const results = [];

  for (const call of toolCalls) {
    const result = await callBrowserTool(call.tool, call.arguments);
    results.push(result);

    // Small delay between calls
    await new Promise((r) => setTimeout(r, 500));
  }

  return results;
}

async function runTask(taskName) {
  const taskDescription = TASKS[taskName];

  if (!taskDescription) {
    console.log("❌ Unknown task. Available tasks:");
    Object.keys(TASKS).forEach((name) => {
      console.log(`  - ${name}`);
    });
    process.exit(1);
  }

  console.log(`\n📋 Task: ${taskName}`);
  console.log(`📝 Description: ${taskDescription}\n`);
  console.log("🤖 Generating automation plan...\n");

  const planJson = await callOllama(taskDescription);

  if (!planJson) {
    console.error("Failed to get automation plan from Ollama");
    process.exit(1);
  }

  console.log("📜 Plan (JSON):");
  console.log(planJson);
  console.log();

  // Parse tool calls
  let toolCalls = [];
  try {
    const parsed = JSON.parse(planJson);
    if (Array.isArray(parsed)) {
      toolCalls = parsed;
    } else if (parsed.tool) {
      toolCalls = [parsed];
    }
  } catch (e) {
    console.error(`Failed to parse tool calls: ${e.message}`);
    process.exit(1);
  }

  if (toolCalls.length === 0) {
    console.log("No tool calls found in plan");
    process.exit(1);
  }

  console.log(`🔄 Executing ${toolCalls.length} tool calls...\n`);

  const results = await executeToolCalls(toolCalls);

  console.log("\n✅ Task Complete!\n");
  console.log("📊 Results:");
  results.forEach((result, i) => {
    console.log(`  [${i + 1}] ${JSON.stringify(result).substring(0, 100)}...`);
  });

  await mcpClient.close();
  await transport.close();
}

// Main
const args = process.argv.slice(2);

if (args.length === 0) {
  console.log("📋 Available automation tasks:\n");
  Object.entries(TASKS).forEach(([name, description]) => {
    console.log(`  ${name}:`);
    console.log(`    ${description}\n`);
  });
  console.log("Usage: node run-task.js <task-name> [model]");
  console.log("Example: node run-task.js github llama2");
  process.exit(0);
}

const taskName = args[0];
selectedModel = args[1] || "llama2";

console.log(`🤖 Using model: ${selectedModel}\n`);

connectMCP()
  .then(() => runTask(taskName))
  .catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
  });

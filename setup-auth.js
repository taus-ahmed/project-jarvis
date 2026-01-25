#!/usr/bin/env node

/**
 * One-time auth setup - manually login, then save auth state
 * After this, all automation sessions will be logged in
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import readline from "readline";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

async function prompt(question) {
  return new Promise((resolve) => {
    rl.question(question, resolve);
  });
}

async function main() {
  console.log("🔐 One-Time Auth Setup\n");
  console.log("This will open a browser for you to manually login to Gmail.");
  console.log("After you login, we'll save the session so automation works!\n");

  const transport = new StdioClientTransport({
    command: "node",
    args: ["dist/index.js"],
  });

  const client = new Client(
    { name: "auth-setup", version: "1.0.0" },
    { capabilities: {} }
  );

  await client.connect(transport);

  try {
    // Navigate to Gmail
    console.log("📧 Opening Gmail...\n");
    await client.callTool({
      name: "browser_navigate",
      arguments: { url: "https://mail.google.com" },
    });

    console.log("✋ PLEASE MANUALLY LOGIN TO GMAIL IN THE BROWSER WINDOW\n");
    console.log("After you've logged in and see your inbox:");
    await prompt("Press Enter to save the session...");

    // Save auth state
    console.log("\n💾 Saving your login session...");
    const saveResult = await client.callTool({
      name: "browser_save_auth",
      arguments: {},
    });

    console.log("✅ Authentication saved!");
    console.log("\n🎉 Setup complete! From now on, automation will work with your Gmail logged in.");

    await client.callTool({
      name: "browser_close",
      arguments: {},
    });
  } finally {
    await client.close();
    await transport.close();
    rl.close();
  }
}

main().catch(console.error);

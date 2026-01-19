#!/usr/bin/env node

/**
 * Simple MCP test client that performs the required initialize handshake
 * before listing tools and calling sample actions.
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

function parseTextContent(result) {
  const text = result?.content?.[0]?.text;
  if (!text) return result;
  try {
    return JSON.parse(text);
  } catch (err) {
    return text;
  }
}

async function main() {
  console.log("Connecting to MCP browser automation server...\n");

  const transport = new StdioClientTransport({
    command: "node",
    args: ["dist/index.js"],
  });

  const client = new Client(
    {
      name: "test-client",
      version: "1.0.0",
    },
    {
      capabilities: {},
    }
  );

  await client.connect(transport);
  console.log("Connected.\n");

  console.log("Available tools:");
  const tools = await client.listTools();
  tools.tools.forEach((tool, index) => {
    console.log(`${index + 1}. ${tool.name} - ${tool.description}`);
  });

  console.log("\nRunning smoke test: navigate -> snapshot\n");

  const navigateResult = await client.callTool({
    name: "browser_navigate",
    arguments: {
      url: "https://example.com",
      waitUntil: "load",
    },
  });

  const navData = parseTextContent(navigateResult);
  console.log("Navigation result:", navData);

  const snapshotResult = await client.callTool({
    name: "browser_get_snapshot",
    arguments: { simplified: true },
  });

  const snapshotData = parseTextContent(snapshotResult);
  if (snapshotData && snapshotData.elements) {
    console.log(
      `Snapshot: ${snapshotData.elementCount} interactive elements on ${snapshotData.title} (${snapshotData.url})`
    );
    const preview = snapshotData.elements.slice(0, 3);
    if (preview.length > 0) {
      console.log("First elements:");
      preview.forEach((el, idx) => {
        console.log(`  ${idx + 1}. ${el.tag} - ${el.text?.slice(0, 60) || ""}`);
      });
    }
  } else {
    console.log("Snapshot response:", snapshotData);
  }

  await client.close();
  await transport.close();
  console.log("\nTest complete.\n");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

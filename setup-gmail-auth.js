/**
 * One-time setup: Login to Gmail and save authentication
 * This will properly save your Gmail login session for automation
 */

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import readline from "readline";

async function setupGmailAuth() {
  console.log("🔐 Gmail Authentication Setup\n");
  console.log("This will open a browser for you to login to Gmail.");
  console.log("After logging in and seeing your inbox, press Enter to save the session.\n");

  const transport = new StdioClientTransport({
    command: "node",
    args: ["dist/index.js"]
  });

  const client = new Client({
    name: "gmail-auth-setup",
    version: "1.0.0"
  }, {
    capabilities: {}
  });

  try {
    await client.connect(transport);
    console.log("✓ Connected to MCP server\n");

    // List and select a profile
    const listResult = await client.callTool({
      name: "browser_list_profiles",
      arguments: {}
    });
    
    const profiles = JSON.parse(listResult.content[0].text);
    const profile = profiles.profiles[0];
    
    console.log(`🎯 Using profile: ${profile.name} (${profile.directory})\n`);
    
    await client.callTool({
      name: "browser_select_profile",
      arguments: { directory: profile.directory }
    });

    // Navigate directly to Gmail sign-in page
    console.log("📧 Opening Gmail sign-in page...");
    await client.callTool({
      name: "browser_navigate",
      arguments: { url: "https://accounts.google.com/ServiceLogin?service=mail&continue=https://mail.google.com/mail/" }
    });

    console.log("\n" + "=".repeat(60));
    console.log("👉 PLEASE COMPLETE THESE STEPS IN THE BROWSER:");
    console.log("=".repeat(60));
    console.log("1. Enter your Gmail address");
    console.log("2. Enter your password");
    console.log("3. Complete any 2FA if prompted");
    console.log("4. Wait until you see your Gmail inbox");
    console.log("5. Press Enter here in the terminal");
    console.log("=".repeat(60) + "\n");

    // Wait for user to press Enter
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    await new Promise(resolve => {
      rl.question("Press Enter after you've logged in and see your inbox... ", () => {
        rl.close();
        resolve();
      });
    });

    console.log("\n💾 Saving your authentication state...");
    
    const saveResult = await client.callTool({
      name: "browser_save_auth",
      arguments: {}
    });

    const saveData = JSON.parse(saveResult.content[0].text);
    
    if (saveData.success) {
      console.log("✅ Authentication saved successfully!");
      console.log(`   File: ${saveData.path}`);
      console.log("\n🎉 Setup complete! Your Gmail login is now saved.");
      console.log("   From now on, browser automation will start with Gmail already logged in.");
      
      // Verify by checking cookie count
      const fs = await import("fs/promises");
      const authData = JSON.parse(await fs.readFile(saveData.path, "utf-8"));
      console.log(`   Saved ${authData.cookies?.length || 0} cookies`);
      
      if (authData.cookies?.length > 10) {
        console.log("   ✓ Good cookie count - Gmail login should work!");
      } else {
        console.log("   ⚠️  Low cookie count - you may need to login again");
      }
    } else {
      console.log("❌ Failed to save authentication");
    }

    process.exit(0);

  } catch (error) {
    console.error("\n❌ Setup failed:", error.message);
    console.error(error);
    process.exit(1);
  }
}

setupGmailAuth();

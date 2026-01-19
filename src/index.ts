#!/usr/bin/env node

/**
 * MCP Browser Automation Server
 * Provides browser control via Playwright to external LLMs
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { chromium, Browser, BrowserContext, Page } from "playwright";
import { promises as fs } from "fs";
import path from "path";

// Configuration
const AUTH_STATE_FILE = path.join(process.cwd(), "auth_state.json");
const DOWNLOADS_DIR = path.join(process.cwd(), "downloads");
const SCREENSHOTS_DIR = path.join(process.cwd(), "screenshots");

// Global browser state
let browser: Browser | null = null;
let context: BrowserContext | null = null;
let page: Page | null = null;

// Ensure required directories exist
async function ensureDirectories() {
  await fs.mkdir(DOWNLOADS_DIR, { recursive: true });
  await fs.mkdir(SCREENSHOTS_DIR, { recursive: true });
}

/**
 * Initialize browser with persistent authentication
 */
async function initializeBrowser(): Promise<void> {
  if (browser) {
    return; // Already initialized
  }

  browser = await chromium.launch({
    headless: false, // Set to false to see browser UI; true for headless
    args: ['--disable-blink-features=AutomationControlled']
  });

  // Check if we have saved authentication state
  let storageState = undefined;
  try {
    const authData = await fs.readFile(AUTH_STATE_FILE, "utf-8");
    storageState = JSON.parse(authData);
    // console.error("Loaded authentication state from auth_state.json");
  } catch (error) {
    // console.error("No existing auth state found, starting fresh session");
  }

  context = await browser.newContext({
    storageState,
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    acceptDownloads: true,
  });

  page = await context.newPage();
}

/**
 * Save current authentication state
 */
async function saveAuthState(): Promise<void> {
  if (!context) {
    throw new Error("Browser context not initialized");
  }

  const state = await context.storageState();
  await fs.writeFile(AUTH_STATE_FILE, JSON.stringify(state, null, 2));
  // console.error("Authentication state saved to auth_state.json");
}

/**
 * Get accessibility tree snapshot for LLM reasoning
 */
async function getAccessibilitySnapshot(): Promise<string> {
  if (!page) {
    throw new Error("Browser page not initialized");
  }

  // Get accessible name and role for all elements
  // Using string form since evaluate() will execute this in browser context
  const snapshot = await page.evaluate(`
    (() => {
      const walker = document.createTreeWalker(
        document.body,
        1
      );
      const nodes = [];
      let node;
      while (node = walker.nextNode()) {
        const element = node;
        const role = element.getAttribute('role') || element.tagName.toLowerCase();
        const name = element.getAttribute('aria-label') || element.textContent?.trim().substring(0, 50) || '';
        if (name) {
          nodes.push({ role, name });
        }
      }
      return nodes;
    })()
  ` as any);
  return JSON.stringify(snapshot, null, 2);
}

/**
 * Extract simplified accessibility tree for better LLM parsing
 */
async function getSimplifiedSnapshot(): Promise<any> {
  if (!page) {
    throw new Error("Browser page not initialized");
  }

  // Get page title and URL
  const url = page.url();
  const title = await page.title();

  // Extract interactive elements with semantic information
  // Using string form since evaluate() will execute this in browser context
  const elements = await page.evaluate(`
    (() => {
      const results = [];
      
      const getPath = (element) => {
        const parts = [];
        let current = element;
        
        while (current && current !== document.body) {
          let selector = current.tagName.toLowerCase();
          if (current.id) {
            selector += '#' + current.id;
          } else if (current.className) {
            const classes = Array.from(current.classList).slice(0, 2).join('.');
            if (classes) selector += '.' + classes;
          }
          parts.unshift(selector);
          current = current.parentElement;
        }
        
        return parts.join(' > ');
      };

      const selectors = [
        'a[href]',
        'button',
        'input',
        'textarea',
        'select',
        '[role="button"]',
        '[role="link"]',
        '[role="textbox"]',
        '[onclick]',
        '[tabindex]'
      ];

      const elements = document.querySelectorAll(selectors.join(','));
      
      elements.forEach((el, index) => {
        const rect = el.getBoundingClientRect();
        
        if (rect.width === 0 || rect.height === 0) return;
        if (rect.top > window.innerHeight || rect.bottom < 0) return;
        
        const item = {
          index: index,
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute('type') || undefined,
          role: el.getAttribute('role') || undefined,
          text: (el.textContent || '').trim().substring(0, 100),
          ariaLabel: el.getAttribute('aria-label') || undefined,
          placeholder: el.getAttribute('placeholder') || undefined,
          value: el.value || undefined,
          href: el.getAttribute('href') || undefined,
          selector: getPath(el),
          position: {
            x: Math.round(rect.left),
            y: Math.round(rect.top),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          }
        };
        
        Object.keys(item).forEach(key => {
          if (item[key] === undefined || item[key] === '') {
            delete item[key];
          }
        });
        
        results.push(item);
      });
      
      return results;
    })()
  ` as any);

  return {
    url,
    title,
    timestamp: new Date().toISOString(),
    elementCount: (elements as any[]).length,
    elements
  };
}

/**
 * Smart selector resolution with fallback logic
 */
async function resolveSelector(selector: string): Promise<string> {
  if (!page) {
    throw new Error("Browser page not initialized");
  }

  // Try the selector as-is first
  try {
    const element = await page.locator(selector).first();
    if (await element.count() > 0) {
      return selector;
    }
  } catch (error) {
    // Continue to fallback strategies
  }

  // Try as text content
  try {
    const byText = page.getByText(selector, { exact: false });
    if (await byText.count() > 0) {
      return `text=${selector}`;
    }
  } catch (error) {
    // Continue
  }

  // Try as aria-label
  try {
    const byLabel = page.getByLabel(selector);
    if (await byLabel.count() > 0) {
      return `aria-label=${selector}`;
    }
  } catch (error) {
    // Continue
  }

  // Try as role
  try {
    const byRole = page.getByRole(selector as any);
    if (await byRole.count() > 0) {
      return `role=${selector}`;
    }
  } catch (error) {
    // Selector not found with any strategy
  }

  throw new Error(`Could not resolve selector: ${selector}`);
}

// Simple argument helper
function getArg<T>(args: any, key: string, defaultValue?: T): T {
  return args?.[key] ?? defaultValue;
}

// Define MCP tools
const tools: Tool[] = [
  {
    name: "browser_navigate",
    description: "Navigate to a URL in the browser. Automatically loads or creates browser context with persistent auth.",
    inputSchema: {
      type: "object",
      properties: {
        url: { type: "string", description: "The URL to navigate to" },
        waitUntil: {
          type: "string",
          enum: ["load", "domcontentloaded", "networkidle"],
          description: "When to consider navigation succeeded",
          default: "load"
        }
      },
      required: ["url"]
    }
  },
  {
    name: "browser_click",
    description: "Click an element using CSS selector, text, aria-label, or role. Uses smart resolution with fallback strategies.",
    inputSchema: {
      type: "object",
      properties: {
        selector: { type: "string", description: "CSS selector, text, aria-label, or role" },
        timeout: { type: "number", description: "Timeout ms", default: 30000 }
      },
      required: ["selector"]
    }
  },
  {
    name: "browser_fill_form",
    description: "Fill a form field with text. Works with input, textarea, and contenteditable elements.",
    inputSchema: {
      type: "object",
      properties: {
        selector: { type: "string", description: "CSS selector, label text, or placeholder" },
        value: { type: "string", description: "Value to fill" },
        timeout: { type: "number", description: "Timeout ms", default: 30000 }
      },
      required: ["selector", "value"]
    }
  },
  {
    name: "browser_get_snapshot",
    description: "Get the current page's accessibility tree or simplified element snapshot. This allows the LLM to 'see' page structure without vision.",
    inputSchema: {
      type: "object",
      properties: {
        simplified: { type: "boolean", description: "Use simplified snapshot", default: true }
      }
    }
  },
  {
    name: "browser_screenshot",
    description: "Capture a screenshot of the current page. Use as fallback when selectors fail or for vision model analysis.",
    inputSchema: {
      type: "object",
      properties: {
        filename: { type: "string", description: "Optional filename" },
        fullPage: { type: "boolean", description: "Capture full page", default: false }
      }
    }
  },
  {
    name: "browser_save_auth",
    description: "Manually save current authentication state (cookies, localStorage) to auth_state.json for future sessions.",
    inputSchema: {
      type: "object",
      properties: {}
    }
  },
  {
    name: "browser_evaluate",
    description: "Execute custom JavaScript in the page context. Use for advanced automation or data extraction.",
    inputSchema: {
      type: "object",
      properties: {
        script: { type: "string", description: "JavaScript code to execute" }
      },
      required: ["script"]
    }
  },
  {
    name: "browser_wait_for",
    description: "Wait for an element to reach a specific state (visible, hidden, attached, detached).",
    inputSchema: {
      type: "object",
      properties: {
        selector: { type: "string", description: "CSS selector" },
        timeout: { type: "number", description: "Timeout ms", default: 30000 },
        state: { type: "string", enum: ["attached", "detached", "visible", "hidden"], default: "visible" }
      },
      required: ["selector"]
    }
  }
];

// Create MCP server instance
const server = new Server(
  {
    name: "mcp-browser-automation",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

// Handle tool execution
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    // Initialize browser if not already done
    await initializeBrowser();

    switch (name) {
      case "browser_navigate": {
        const url = getArg<string>(args, "url", "");
        const waitUntil = getArg<string>(args, "waitUntil", "load");
        await page!.goto(url, { waitUntil: waitUntil as any });
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                url: page!.url(),
                title: await page!.title()
              })
            }
          ]
        };
      }

      case "browser_click": {
        const selector = getArg<string>(args, "selector", "");
        const timeout = getArg<number>(args, "timeout", 30000);
        const resolvedSelector = await resolveSelector(selector);
        await page!.locator(resolvedSelector).first().click({ timeout });
        
        // Wait a bit for any navigation or dynamic content
        await page!.waitForTimeout(1000);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                clicked: selector,
                resolvedSelector,
                currentUrl: page!.url()
              })
            }
          ]
        };
      }

      case "browser_fill_form": {
        const selector = getArg<string>(args, "selector", "");
        const value = getArg<string>(args, "value", "");
        const timeout = getArg<number>(args, "timeout", 30000);
        const resolvedSelector = await resolveSelector(selector);
        await page!.locator(resolvedSelector).first().fill(value, { timeout });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                filled: selector,
                resolvedSelector,
                value: value.substring(0, 50) + (value.length > 50 ? "..." : "")
              })
            }
          ]
        };
      }

      case "browser_get_snapshot": {
        const simplified = getArg<boolean>(args, "simplified", true);
        
        const snapshot = simplified 
          ? await getSimplifiedSnapshot()
          : await getAccessibilitySnapshot();
        
        return {
          content: [
            {
              type: "text",
              text: typeof snapshot === "string" 
                ? snapshot 
                : JSON.stringify(snapshot, null, 2)
            }
          ]
        };
      }

      case "browser_screenshot": {
        const filename = getArg<string>(args, "filename");
        const fullPage = getArg<boolean>(args, "fullPage", false);
        
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        const screenshotName = filename || `screenshot-${timestamp}.png`;
        const screenshotPath = path.join(SCREENSHOTS_DIR, screenshotName);

        await page!.screenshot({
          path: screenshotPath,
          fullPage: fullPage || false
        });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                path: screenshotPath,
                filename: screenshotName
              })
            }
          ]
        };
      }

      case "browser_save_auth": {
        await saveAuthState();
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                message: "Authentication state saved to auth_state.json",
                path: AUTH_STATE_FILE
              })
            }
          ]
        };
      }

      case "browser_evaluate": {
        const script = getArg<string>(args, "script", "");
        const result = await page!.evaluate(script as any);
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                result
              })
            }
          ]
        };
      }

      case "browser_wait_for": {
        const selector = getArg<string>(args, "selector", "");
        const timeout = getArg<number>(args, "timeout", 30000);
        const state = getArg<string>(args, "state", "visible");
        await page!.locator(selector).first().waitFor({ 
          timeout, 
          state: state as any 
        });
        
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                success: true,
                selector,
                state,
                message: `Element reached ${state} state`
              })
            }
          ]
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    
    // On selector failures, suggest using screenshot tool
    const suggestionHint = errorMessage.includes("selector") 
      ? "\n\nSuggestion: Use browser_screenshot tool to capture visual context for vision model analysis."
      : "";
    
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            success: false,
            error: errorMessage + suggestionHint
          })
        }
      ],
      isError: true
    };
  }
});

// Cleanup on shutdown
async function cleanup() {
  // console.error("Shutting down browser automation server...");
  
  if (context) {
    try {
      // Auto-save auth state on shutdown
      await saveAuthState();
    } catch (error) {
      // Silent failure
    }
  }
  
  if (browser) {
    await browser.close();
  }
  
  process.exit(0);
}

process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);

// Start the server
async function main() {
  try {
    await ensureDirectories();
    
    const transport = new StdioServerTransport();
    await server.connect(transport);
    
    // Don't log to stderr during normal operation - it interferes with MCP protocol
    // console.error("MCP Browser Automation Server running on stdio");
    // console.error(`Auth state: ${AUTH_STATE_FILE}`);
    // console.error(`Screenshots: ${SCREENSHOTS_DIR}`);
    // console.error(`Downloads: ${DOWNLOADS_DIR}`);
  } catch (error) {
    console.error("Server initialization error:", error);
    throw error;
  }
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});

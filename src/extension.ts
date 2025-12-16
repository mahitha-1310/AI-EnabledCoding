import * as vscode from "vscode";

const PYTHON_BACKEND_URL = "http://localhost:8000";

export function activate(context: vscode.ExtensionContext) {
  console.log("HASAIM Agent extension activated!");

  const disposable = vscode.commands.registerCommand(
    "aidocagent.openPanel",
    () => {
      console.log("Opening HASAIM Agent panel...");
      
      const panel = vscode.window.createWebviewPanel(
        "aiChat",
        "🤖 HASAIM",
        vscode.ViewColumn.One,
        { enableScripts: true, retainContextWhenHidden: true }
      );

      panel.webview.html = getWebviewHTML();

      // Keep conversation history for context
      const conversation: { role: "user" | "assistant"; content: string }[] = [];

      panel.webview.onDidReceiveMessage(async (message) => {
        console.log("Received message from webview:", message);
        
        if (message.command === "sendMessage") {
          const userMessage = message.text;
          console.log("User message:", userMessage);
          
          conversation.push({ role: "user", content: userMessage });

          // Show typing indicator
          panel.webview.postMessage({
            command: "botReply",
            text: "⏳ Typing..."
          });

          try {
            console.log("Calling Python backend at:", `${PYTHON_BACKEND_URL}/chat`);
            console.log("Conversation history length:", conversation.length);
            
            // Call Python backend
            const response = await fetch(`${PYTHON_BACKEND_URL}/chat`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                messages: conversation
              }),
            });

            console.log("Response status:", response.status);

            if (!response.ok) {
              const errorText = await response.text();
              console.error("Backend error response:", errorText);
              throw new Error(`Backend returned ${response.status}: ${errorText}`);
            }

            const data = await response.json() as {
              success: boolean;
              reply?: string;
              error?: string;
            };

            console.log("Backend response:", data);

            if (!data.success) {
              throw new Error(data.error || "Unknown error from backend");
            }

            const botReply = data.reply || "⚠ No response";
            conversation.push({ role: "assistant", content: botReply });

            console.log("Sending bot reply to webview");
            panel.webview.postMessage({ command: "botReply", text: botReply });
            
          } catch (err) {
            console.error("Error calling Python backend:", err);
            const errorMessage = err instanceof Error ? err.message : "Unknown error";
            panel.webview.postMessage({
              command: "botReply",
              text: `❌ Error: ${errorMessage}\n\nMake sure Python backend is running on port 8000.`
            });
          }
        }
      });
    }
  );

  context.subscriptions.push(disposable);
}

export function deactivate() {
  console.log("HASAIM Agent extension deactivated");
}

function getWebviewHTML(): string {
  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: sans-serif;
      margin: 0;
      padding: 0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      background: #1e1e1e;
      color: white;
    }
    #chatWindow {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }
    .message {
      margin-bottom: 12px;
      line-height: 1.5;
    }
    .input-container {
      display: flex;
      padding: 8px;
      background: #252526;
      border-top: 1px solid #333;
    }
    #inputBox {
      flex: 1;
      padding: 8px;
      border-radius: 4px;
      border: none;
      background: #3c3c3c;
      color: white;
      font-size: 14px;
    }
    #inputBox:focus {
      outline: 1px solid #0078d4;
    }
    #sendBtn {
      margin-left: 8px;
      padding: 8px 16px;
      background: #0078d4;
      border: none;
      color: white;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    }
    #sendBtn:hover {
      background: #006cc1;
    }
    #sendBtn:active {
      background: #005a9e;
    }
  </style>
</head>
<body>
  <div id="chatWindow"></div>
  <div class="input-container">
    <input id="inputBox" type="text" placeholder="Type a message..." />
    <button id="sendBtn">Send</button>
  </div>

  <script>
    (function() {
      console.log("Webview script loaded");
      
      const vscode = acquireVsCodeApi();
      const chatWindow = document.getElementById("chatWindow");
      const inputBox = document.getElementById("inputBox");
      const sendBtn = document.getElementById("sendBtn");

      function addMessage(sender, text) {
        console.log("Adding message:", sender, text);
        const div = document.createElement("div");
        div.className = "message";
        div.innerHTML = "<b>" + sender + ":</b> " + text.replace(/\\n/g, "<br>");
        chatWindow.appendChild(div);
        chatWindow.scrollTop = chatWindow.scrollHeight;
      }

      function sendMessage() {
        const msg = inputBox.value.trim();
        console.log("Send button clicked, message:", msg);
        
        if (!msg) {
          console.log("Empty message, not sending");
          return;
        }
        
        addMessage("You", msg);
        inputBox.value = "";
        
        console.log("Posting message to extension");
        vscode.postMessage({ command: "sendMessage", text: msg });
      }

      sendBtn.addEventListener("click", () => {
        console.log("Send button click event");
        sendMessage();
      });

      inputBox.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          console.log("Enter key pressed");
          sendMessage();
        }
      });

      window.addEventListener("message", (event) => {
        console.log("Received message from extension:", event.data);
        const msg = event.data;
        if (msg.command === "botReply") {
          addMessage("Hasaim", msg.text);
        }
      });

      console.log("Event listeners attached");
      addMessage("Hasaim", "Ready! Type a message and click Send.");
    })();
  </script>
</body>
</html>
`;
}
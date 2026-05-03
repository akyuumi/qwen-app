const statusEl = document.querySelector("#status");
const messagesEl = document.querySelector("#messages");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const codeInput = document.querySelector("#code-input");
const runCodeButton = document.querySelector("#run-code");
const runOutput = document.querySelector("#run-output");
const historyEl = document.querySelector("#history");
const refreshHistoryButton = document.querySelector("#refresh-history");
const profileForm = document.querySelector("#profile-form");
const profileModel = document.querySelector("#profile-model");
const profileUrl = document.querySelector("#profile-url");
const profilePrompt = document.querySelector("#profile-prompt");

function appendMessage(kind, text) {
  const node = document.createElement("div");
  node.className = `message ${kind}`;
  node.textContent = text;
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return node;
}

function appendLoadingMessage(text) {
  const node = document.createElement("div");
  node.className = "message assistant loading-message";
  node.setAttribute("aria-label", text);
  node.innerHTML = `
    <span>${text}</span>
    <span class="typing-dots" aria-hidden="true">
      <span></span><span></span><span></span>
    </span>
  `;
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return node;
}

function setButtonLoading(button, isLoading, loadingText) {
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.classList.add("is-loading");
    button.disabled = true;
    return;
  }
  button.textContent = button.dataset.originalText || button.textContent;
  button.classList.remove("is-loading");
  button.disabled = false;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

async function loadHealth() {
  try {
    await requestJson("/api/health");
    statusEl.textContent = "API接続済み";
  } catch (error) {
    statusEl.textContent = `APIエラー: ${error.message}`;
    statusEl.classList.add("error");
  }
}

async function loadProfile() {
  const profile = await requestJson("/api/profile");
  profileModel.value = profile.model || "";
  profileUrl.value = profile.ollama_base_url || "";
  profilePrompt.value = profile.system_prompt || "";
}

async function loadHistory() {
  const rows = await requestJson("/api/executions?limit=10");
  historyEl.replaceChildren();
  if (rows.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "履歴なし";
    historyEl.appendChild(empty);
    return;
  }
  for (const row of rows) {
    const item = document.createElement("article");
    item.className = "history-item";
    const title = document.createElement("strong");
    title.textContent = `#${row.id} exit ${row.exit_code}`;
    const body = document.createElement("pre");
    body.textContent = [row.code, row.stdout, row.stderr].filter(Boolean).join("\n---\n");
    item.append(title, body);
    historyEl.appendChild(item);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  appendMessage("user", text);
  chatInput.value = "";
  const button = chatForm.querySelector("button");
  const loadingMessage = appendLoadingMessage("応答中");
  setButtonLoading(button, true, "応答中");
  chatInput.disabled = true;
  chatPaneBusy(true);
  try {
    const data = await requestJson("/api/chat", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    loadingMessage.className = "message assistant";
    loadingMessage.removeAttribute("aria-label");
    loadingMessage.textContent = data.response;
    if (data.tool_result) {
      appendMessage("tool", JSON.stringify(data.tool_result, null, 2));
      await loadHistory();
    }
  } catch (error) {
    loadingMessage.className = "message assistant error";
    loadingMessage.removeAttribute("aria-label");
    loadingMessage.textContent = error.message;
  } finally {
    setButtonLoading(button, false);
    chatInput.disabled = false;
    chatInput.focus();
    chatPaneBusy(false);
  }
});

runCodeButton.addEventListener("click", async () => {
  setButtonLoading(runCodeButton, true, "実行中");
  runOutput.innerHTML = `
    <span>Dockerで実行中</span>
    <span class="typing-dots" aria-hidden="true">
      <span></span><span></span><span></span>
    </span>
  `;
  try {
    const data = await requestJson("/api/run-python", {
      method: "POST",
      body: JSON.stringify({ code: codeInput.value }),
    });
    runOutput.textContent = JSON.stringify(data, null, 2);
    await loadHistory();
  } catch (error) {
    runOutput.textContent = error.message;
  } finally {
    setButtonLoading(runCodeButton, false);
  }
});

refreshHistoryButton.addEventListener("click", loadHistory);

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = await requestJson("/api/profile", {
    method: "PUT",
    body: JSON.stringify({
      model: profileModel.value,
      ollama_base_url: profileUrl.value,
      system_prompt: profilePrompt.value,
    }),
  });
  profileModel.value = data.model;
  profileUrl.value = data.ollama_base_url;
  profilePrompt.value = data.system_prompt;
  statusEl.textContent = "プロファイル保存済み";
});

loadHealth();
loadProfile().catch((error) => {
  statusEl.textContent = `プロファイル読み込みエラー: ${error.message}`;
});
loadHistory().catch(() => {});

function chatPaneBusy(isBusy) {
  const pane = document.querySelector(".chat-pane");
  pane.setAttribute("aria-busy", String(isBusy));
}

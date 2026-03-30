let isProcessing = false;
let keyListenerAttached = false;
let clickListenerAttached = false;
let bypassNextClick = false;

function sendToBackground(payload, callback) {
  try {
    const runtime =
      typeof chrome !== "undefined" && chrome.runtime ? chrome.runtime : null;

    if (!runtime || typeof runtime.sendMessage !== "function") {
      console.warn("Extension runtime unavailable");
      updateResultBox("Extension not connected. Reload extension and refresh tab.", "warn");
      return;
    }

    runtime.sendMessage(payload, (response) => {
      const lastError = runtime.lastError;

      if (lastError) {
        const msg = lastError.message || "";

        if (msg.includes("Extension context invalidated")) {
          console.warn("Extension context invalidated. Refresh the tab.");
          updateResultBox("Extension context invalidated. Refresh the tab.", "warn");
          return;
        }

        if (msg.includes("Receiving end does not exist")) {
          console.warn("Background script not available. Reload extension.");
          updateResultBox("Background not available. Reload extension.", "warn");
          return;
        }

        console.warn("Extension messaging warning:", msg);
        updateResultBox("Extension connection issue. Reload extension and refresh tab.", "warn");
        return;
      }

      if (callback) callback(response);
    });
  } catch (err) {
    const msg = String(err || "");

    if (msg.includes("Extension context invalidated")) {
      console.warn("Extension context invalidated. Refresh the tab.");
      updateResultBox("Extension context invalidated. Refresh the tab.", "warn");
      return;
    }

    console.error("sendToBackground error:", err);
    updateResultBox("Extension messaging failed. Reload extension and refresh tab.", "warn");
  }
}

function isVisible(el) {
  if (!el) return false;

  const style = window.getComputedStyle(el);
  const rect = el.getBoundingClientRect();

  return (
    style.display !== "none" &&
    style.visibility !== "hidden" &&
    rect.width > 0 &&
    rect.height > 0
  );
}

function getCandidateInputs() {
  const selectors = [
    "textarea",
    'div[contenteditable="true"]',
    '[role="textbox"]'
  ];

  const candidates = [];

  for (const selector of selectors) {
    const nodes = document.querySelectorAll(selector);
    nodes.forEach((el) => {
      if (isVisible(el)) {
        candidates.push(el);
      }
    });
  }

  return candidates;
}

function findPromptBox() {
  const active = document.activeElement;

  if (
    active &&
    isVisible(active) &&
    typeof active.matches === "function" &&
    (
      active.matches("textarea") ||
      active.matches('div[contenteditable="true"]') ||
      active.matches('[role="textbox"]')
    )
  ) {
    return active;
  }

  const candidates = getCandidateInputs();

  if (candidates.length > 0) {
    candidates.sort((a, b) => {
      const aRect = a.getBoundingClientRect();
      const bRect = b.getBoundingClientRect();
      return bRect.bottom - aRect.bottom;
    });
    return candidates[0];
  }

  return null;
}

function getPromptText(el) {
  if (!el) return "";

  const tag = (el.tagName || "").toLowerCase();

  if (tag === "textarea" || tag === "input") {
    return (el.value || "").trim();
  }

  return (el.innerText || el.textContent || "").trim();
}

function createResultBox() {
  let box = document.getElementById("dlp-result-box");
  if (box) return box;

  box = document.createElement("div");
  box.id = "dlp-result-box";
  box.classList.add("info");
  box.innerHTML = `
    <div id="dlp-result-title">DLP Check</div>
    <div id="dlp-result-body">Ready</div>
  `;
  document.body.appendChild(box);
  return box;
}

function updateResultBox(text, level = "info") {
  const box = createResultBox();
  const body = document.getElementById("dlp-result-body");

  box.className = "";
  box.id = "dlp-result-box";
  box.classList.add(level);
  body.textContent = text;
}

function createModal() {
  let modal = document.getElementById("dlp-modal");
  if (modal) return modal;

  modal = document.createElement("div");
  modal.id = "dlp-modal";
  modal.innerHTML = `
    <div id="dlp-modal-overlay"></div>
    <div id="dlp-modal-box">
      <div id="dlp-modal-badge">Policy Check</div>
      <h3 id="dlp-modal-heading">Warning</h3>
      <div id="dlp-modal-rule"></div>
      <p id="dlp-modal-text"></p>
      <div id="dlp-modal-actions">
        <button id="dlp-modal-cancel">Cancel</button>
        <button id="dlp-modal-proceed">Proceed</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  return modal;
}

function hideModal() {
  const modal = document.getElementById("dlp-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

function showModal({
  mode = "warn",
  rule = "No matched rule",
  severity = "unknown",
  similarity = "N/A",
  message = "No message",
  onProceed = null,
  onCancel = null
}) {
  const modal = createModal();
  const box = document.getElementById("dlp-modal-box");
  const heading = document.getElementById("dlp-modal-heading");
  const ruleEl = document.getElementById("dlp-modal-rule");
  const textEl = document.getElementById("dlp-modal-text");
  const proceedBtn = document.getElementById("dlp-modal-proceed");
  const cancelBtn = document.getElementById("dlp-modal-cancel");

  modal.style.display = "block";

  box.className = "";
  box.id = "dlp-modal-box";
  box.classList.add(mode);

  heading.textContent = mode === "block" ? "Blocked by Policy" : "Policy Warning";
  ruleEl.textContent = `${rule} | severity: ${severity} | sim: ${similarity}`;
  textEl.textContent = message;

  if (mode === "block") {
    proceedBtn.style.display = "none";
    cancelBtn.textContent = "Close";
  } else {
    proceedBtn.style.display = "inline-block";
    cancelBtn.textContent = "Cancel";
  }

  proceedBtn.onclick = () => {
    hideModal();
    if (onProceed) onProceed();
  };

  cancelBtn.onclick = () => {
    hideModal();
    if (onCancel) onCancel();
  };
}

function findSendButtons() {
  const selectors = [
    'button[data-testid*="send"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="send"]'
  ];

  const buttons = [];

  for (const selector of selectors) {
    document.querySelectorAll(selector).forEach((btn) => {
      if (btn && !btn.disabled && isVisible(btn)) {
        buttons.push(btn);
      }
    });
  }

  return buttons;
}

function clickSendButton() {
  const buttons = findSendButtons();

  if (buttons.length > 0) {
    buttons[0].click();
    return true;
  }

  return false;
}

function findSendButtonFromTarget(target) {
  if (!target || typeof target.closest !== "function") return null;

  return target.closest(
    'button[data-testid*="send"], button[aria-label*="Send"], button[aria-label*="send"]'
  );
}

function processPromptSubmission(promptText, sendAction) {
  if (!promptText) {
    updateResultBox("No prompt text found.", "warn");
    isProcessing = false;
    return;
  }

  updateResultBox("Checking before send...", "info");

  sendToBackground(
    {
      type: "CHECK_PROMPT",
      text: promptText
    },
    (response) => {
      if (!response || !response.ok) {
        updateResultBox(
          "API error: " + (response?.error || "Unknown error"),
          "block"
        );
        isProcessing = false;
        return;
      }

      const result = response.data?.decision;
      if (!result) {
        updateResultBox("No decision returned.", "warn");
        isProcessing = false;
        return;
      }

      const action = result.action || "allow";
      const msg = result.message || "No message";
      const matchedRule = result.matched_rule || {};
      const rule = matchedRule.title || "No matched rule";
      const severity = matchedRule.severity || "unknown";
      const similarity =
        typeof matchedRule.similarity === "number"
          ? matchedRule.similarity.toFixed(3)
          : "N/A";

      if (action === "block") {
        updateResultBox(`BLOCK | ${rule} | severity: ${severity} | sim: ${similarity}`, "block");
        showModal({
          mode: "block",
          rule,
          severity,
          similarity,
          message: msg,
          onCancel: () => {
            isProcessing = false;
          }
        });
        return;
      }

      if (action === "warn") {
        updateResultBox(`WARN | ${rule} | severity: ${severity} | sim: ${similarity}`, "warn");
        showModal({
          mode: "warn",
          rule,
          severity,
          similarity,
          message: msg,
          onProceed: () => {
            updateResultBox(`ALLOW | ${rule} | severity: ${severity} | sim: ${similarity}`, "allow");
            setTimeout(() => {
              sendAction();
              isProcessing = false;
            }, 150);
          },
          onCancel: () => {
            updateResultBox("Submission cancelled.", "warn");
            isProcessing = false;
          }
        });
        return;
      }

      updateResultBox(`ALLOW | ${rule} | severity: ${severity} | sim: ${similarity}`, "allow");

      setTimeout(() => {
        sendAction();
        isProcessing = false;
      }, 150);
    }
  );
}

function runManualCheck() {
  const promptBox = findPromptBox();
  const promptText = getPromptText(promptBox);

  if (!promptText) {
    updateResultBox("No prompt text found.", "warn");
    return;
  }

  updateResultBox("Checking prompt...", "info");

  sendToBackground(
    {
      type: "CHECK_PROMPT",
      text: promptText
    },
    (response) => {
      if (!response || !response.ok) {
        updateResultBox(
          "API error: " + (response?.error || "Unknown error"),
          "block"
        );
        return;
      }

      const result = response.data?.decision;
      if (!result) {
        updateResultBox("No decision returned.", "warn");
        return;
      }

      const action = result.action || "allow";
      const msg = result.message || "No message";
      const matchedRule = result.matched_rule || {};
      const rule = matchedRule.title || "No matched rule";
      const severity = matchedRule.severity || "unknown";
      const similarity =
        typeof matchedRule.similarity === "number"
          ? matchedRule.similarity.toFixed(3)
          : "N/A";

      if (action === "block") {
        updateResultBox(`BLOCK | ${rule} | severity: ${severity} | sim: ${similarity}`, "block");
        showModal({
          mode: "block",
          rule,
          severity,
          similarity,
          message: msg
        });
      } else if (action === "warn") {
        updateResultBox(`WARN | ${rule} | severity: ${severity} | sim: ${similarity}`, "warn");
        showModal({
          mode: "warn",
          rule,
          severity,
          similarity,
          message: msg,
          onProceed: () => {},
          onCancel: () => {}
        });
      } else {
        updateResultBox(`ALLOW | ${rule} | severity: ${severity} | sim: ${similarity}`, "allow");
      }
    }
  );
}

function createCheckButton() {
  if (document.getElementById("dlp-check-btn")) return;

  const btn = document.createElement("button");
  btn.id = "dlp-check-btn";
  btn.textContent = "Check Prompt";
  btn.addEventListener("click", runManualCheck);

  document.body.appendChild(btn);
}

function handleSubmitIntercept(e) {
  if (isProcessing) return;
  if (e.defaultPrevented) return;
  if (e.key !== "Enter") return;
  if (e.shiftKey) return;

  const promptBox = findPromptBox();
  if (!promptBox) return;

  const active = document.activeElement;
  if (active !== promptBox) return;

  const promptText = getPromptText(promptBox);
  if (!promptText) return;

  e.preventDefault();
  e.stopPropagation();

  isProcessing = true;

  processPromptSubmission(promptText, () => {
    clickSendButton();
  });
}

function handleClickIntercept(e) {
  if (isProcessing) return;

  const sendBtn = findSendButtonFromTarget(e.target);
  if (!sendBtn) return;

  if (bypassNextClick) {
    bypassNextClick = false;
    return;
  }

  const promptBox = findPromptBox();
  const promptText = getPromptText(promptBox);
  if (!promptText) return;

  e.preventDefault();
  e.stopPropagation();

  if (typeof e.stopImmediatePropagation === "function") {
    e.stopImmediatePropagation();
  }

  isProcessing = true;

  processPromptSubmission(promptText, () => {
    bypassNextClick = true;
    sendBtn.click();
  });
}

function init() {
  createCheckButton();
  createResultBox();
  createModal();

  if (!keyListenerAttached) {
    document.addEventListener("keydown", handleSubmitIntercept, true);
    keyListenerAttached = true;
  }

  if (!clickListenerAttached) {
    document.addEventListener("click", handleClickIntercept, true);
    clickListenerAttached = true;
  }
}

setInterval(() => {
  createCheckButton();
  createResultBox();
}, 2000);

init();
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "CHECK_PROMPT") return;

  fetch("http://127.0.0.1:8000/check", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: message.text,
      user: "local-user",
      source: sender?.url || "browser-extension",
      channel: "chatgpt-extension"
    })
  })
    .then(async (res) => {
      const data = await res.json();
      sendResponse({ ok: true, data });
    })
    .catch((err) => {
      console.error("Background fetch error:", err);
      sendResponse({ ok: false, error: err.message });
    });

  return true;
});
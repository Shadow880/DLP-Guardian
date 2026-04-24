async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    method: options.method || "GET",
    headers: options.headers || {},
    body: options.body,
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

async function fetchActiveUser() {
  const data = await fetchJson("http://127.0.0.1:8000/active-user");
  return data?.active_user || "boss";
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_SITE_POLICIES") {
    fetchJson("http://127.0.0.1:8000/site-policies")
      .then((data) => {
        sendResponse({ ok: true, data });
      })
      .catch((err) => {
        console.error("Site policy fetch error:", err);
        sendResponse({
          ok: false,
          error: err?.message || String(err)
        });
      });

    return true;
  }

  if (message.type === "CHECK_PROMPT") {
    fetchActiveUser()
      .then((activeUser) => {
        return fetchJson("http://127.0.0.1:8000/check", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            text: message.text,
            user: activeUser,
            source: sender?.url || "browser-extension",
            channel: "chatgpt-extension"
          })
        });
      })
      .then((data) => {
        sendResponse({ ok: true, data });
      })
      .catch((err) => {
        console.error("Background fetch error:", err);
        sendResponse({
          ok: false,
          error: err?.message || String(err)
        });
      });

    return true;
  }
});
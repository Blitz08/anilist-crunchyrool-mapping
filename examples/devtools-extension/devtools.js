chrome.devtools.panels.create("Crunchyroll CMS", "", "panel.html", (panel) => {
  let listening = false;
  let panelDocument;

  function show(message, content) {
    const entry = panelDocument.createElement("details");
    const summary = panelDocument.createElement("summary");
    summary.textContent = message;
    entry.append(summary);

    if (content !== undefined) {
      const link = panelDocument.createElement("a");
      link.textContent = "JSON speichern";
      link.download = `cms-${crypto.randomUUID()}.json`;
      link.href = `data:application/json;charset=utf-8,${encodeURIComponent(content)}`;
      const preview = panelDocument.createElement("pre");
      preview.textContent = content;
      entry.append(link, preview);
    }

    panelDocument.getElementById("responses").append(entry);
  }

  panel.onShown.addListener((window) => {
    panelDocument = window.document;
    if (listening) return;
    listening = true;

    chrome.devtools.network.onRequestFinished.addListener((request) => {
      const url = new URL(request.request.url);
      if (
        !(url.hostname === "crunchyroll.com" || url.hostname.endsWith(".crunchyroll.com")) ||
        !url.pathname.startsWith("/content/v2/cms/") ||
        url.pathname.startsWith("/content/v2/cms/videos/")
      ) return;

      if (request.response.status < 200 || request.response.status >= 300) {
        show(`HTTP ${request.response.status}: ${url.pathname}`);
        return;
      }

      request.getContent((body, encoding) => {
        const error = chrome.runtime.lastError;
        if (error) {
          show(`Antwort nicht lesbar: ${error.message}`);
          return;
        }
        if (!body) {
          show(`Kein Antwortinhalt verfügbar: ${url.pathname}`);
          return;
        }

        let content;
        try {
          const text = encoding === "base64"
            ? new TextDecoder("utf-8", { fatal: true }).decode(
              Uint8Array.from(atob(body), (character) => character.charCodeAt(0)),
            )
            : body;
          content = JSON.stringify(JSON.parse(text), null, 2);
        } catch (error) {
          show(`Keine lesbare JSON-Antwort (${url.pathname}): ${error.message}`);
          return;
        }
        show(url.pathname, content);
      });
    });
  });
});

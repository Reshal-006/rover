chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
  const tab = tabs[0];
  if (!tab || !tab.url) {
    document.getElementById("status-text").textContent = "Could not read tab URL.";
    return;
  }

  const url = tab.url;
  const statusText = document.getElementById("status-text");
  const repoInfo = document.getElementById("repo-info");
  const scanBtn = document.getElementById("scan-btn");

  if (url.startsWith("https://github.com/")) {
    const pathParts = new URL(url).pathname.split("/").filter(Boolean);
    if (pathParts.length >= 2) {
      const owner = pathParts[0];
      const repo = pathParts[1];
      
      // Ignore special GitHub pages (e.g. settings, notifications, marketplace)
      const ignoredTerms = ["settings", "notifications", "marketplace", "explore", "trending", "issues", "pulls"];
      if (!ignoredTerms.includes(owner)) {
        const repoUrl = `https://github.com/${owner}/${repo}`;
        statusText.innerHTML = `Active Repository Detected:`;
        repoInfo.textContent = `${owner}/${repo}`;
        repoInfo.style.display = "block";
        
        scanBtn.classList.remove("disabled");
        scanBtn.removeAttribute("disabled");
        scanBtn.addEventListener("click", function () {
          const dashboardUrl = `http://localhost:8501/?repo_url=${encodeURIComponent(repoUrl)}&auto_scan=true`;
          chrome.tabs.create({ url: dashboardUrl });
        });
        return;
      }
    }
  }
  
  statusText.textContent = "Please navigate to a GitHub repository page to use Rover.";
});

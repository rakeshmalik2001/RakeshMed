(function () {
  const doc = document;
  const body = doc.body;
  if (!body) {
    return;
  }

  const storage = window.localStorage;
  const dashboardRoot = doc.querySelector("[data-dashboard-root]");
  const toastStack = doc.querySelector("[data-toast-stack]");
  const sessionWarning = doc.querySelector("[data-session-warning]");
  const sessionContinue = doc.querySelector("[data-session-continue]");
  const topbarSearch = doc.querySelector(".admin-topbar-search input");
  const navFilter = doc.getElementById("nav-filter");
  const commandPalette = doc.querySelector("[data-command-palette]");
  const commandInput = doc.querySelector("[data-command-input]");
  const commandList = doc.querySelector("[data-command-list]");
  const themeButtons = Array.from(doc.querySelectorAll("[data-theme-style]"));
  const contrastToggle = doc.querySelector("[data-contrast-toggle]");
  const glowControl = doc.querySelector("[data-glow-intensity]");
  const liveTimestamp = doc.querySelector("[data-live-timestamp]");
  const dashboardLiveUrl = dashboardRoot ? dashboardRoot.getAttribute("data-live-url") : "";
  const commandItemsNode = doc.getElementById("admin-command-items");
  const commandItems = commandItemsNode ? JSON.parse(commandItemsNode.textContent || "[]") : [];
  let activeCommandIndex = 0;
  let liveFeedSignatures = new Set();
  let lastActivityAt = Date.now();
  let liveRefreshTimer = null;
  let sessionTimer = null;
  let sessionWarningVisible = false;

  function savePreference(key, value) {
    try {
      storage.setItem(key, value);
    } catch (_error) {
      // Ignore private mode or blocked storage.
    }
  }

  function loadPreference(key) {
    try {
      return storage.getItem(key);
    } catch (_error) {
      return null;
    }
  }

  function showToast(title, bodyText) {
    if (!toastStack) {
      return;
    }
    const toast = doc.createElement("article");
    toast.className = "admin-toast";
    toast.innerHTML = "<strong></strong><p></p>";
    toast.querySelector("strong").textContent = title;
    toast.querySelector("p").textContent = bodyText;
    toastStack.prepend(toast);
    window.setTimeout(() => toast.remove(), 4200);
  }

  function applyTheme(theme) {
    body.dataset.themeStyle = theme;
    savePreference("tc-theme-style", theme);
    themeButtons.forEach((button) => {
      button.classList.toggle("is-active", button.getAttribute("data-theme-style") === theme);
    });
  }

  function applyContrast(enabled) {
    body.dataset.contrastMode = enabled ? "high" : "standard";
    savePreference("tc-contrast-mode", enabled ? "high" : "standard");
  }

  function applyGlow(value) {
    const glowScale = Math.max(0.8, Math.min(1.8, Number(value) / 100));
    body.style.setProperty("--tc-glow-scale", String(glowScale));
    savePreference("tc-glow-intensity", String(value));
  }

  function focusSearch() {
    if (topbarSearch) {
      topbarSearch.focus();
      topbarSearch.select();
    }
  }

  function filterLinks(query) {
    const normalized = query.trim().toLowerCase();
    const containers = Array.from(doc.querySelectorAll("#nav-sidebar tbody tr, .dashboard-app-card li, .dashboard-role-card, .dashboard-metric-item"));
    containers.forEach((item) => {
      const match = !normalized || item.textContent.toLowerCase().includes(normalized);
      item.style.display = match ? "" : "none";
    });
  }

  function renderCommandList(query) {
    if (!commandList) {
      return;
    }
    const normalized = (query || "").trim().toLowerCase();
    const items = commandItems.filter((item) => {
      return !normalized || `${item.label} ${item.group}`.toLowerCase().includes(normalized);
    });
    activeCommandIndex = Math.min(activeCommandIndex, Math.max(items.length - 1, 0));
    commandList.innerHTML = "";

    if (!items.length) {
      commandList.innerHTML = '<div class="admin-command-item"><strong>No matches</strong><small>Try another keyword</small></div>';
      return;
    }

    items.forEach((item, index) => {
      const link = doc.createElement("a");
      link.className = `admin-command-item${index === activeCommandIndex ? " is-active" : ""}`;
      link.href = item.href;
      link.innerHTML = `<strong>${item.label}</strong><small>${item.group}</small>`;
      commandList.appendChild(link);
    });
  }

  function openCommandPalette() {
    if (!commandPalette) {
      return;
    }
    commandPalette.hidden = false;
    activeCommandIndex = 0;
    renderCommandList(commandInput ? commandInput.value : "");
    if (commandInput) {
      commandInput.focus();
      commandInput.select();
    }
  }

  function closeCommandPalette() {
    if (commandPalette) {
      commandPalette.hidden = true;
    }
  }

  function updateScope(scope, values) {
    Object.entries(values || {}).forEach(([key, value]) => {
      const node = doc.querySelector(`[data-live-scope="${scope}"][data-live-key="${key}"] h2`);
      if (node) {
        node.textContent = value;
      }
    });
  }

  function renderFeed(selector, items, kind) {
    const container = doc.querySelector(selector);
    if (!container || !Array.isArray(items)) {
      return;
    }
    container.innerHTML = "";
    items.forEach((item) => {
      const article = doc.createElement(kind === "feed" ? "a" : "article");
      if (kind === "feed") {
        article.href = item.href || "#";
        article.className = `dashboard-feed-item dashboard-feed-item--${item.tone || "cyan"}`;
        article.innerHTML = `
          <span class="dashboard-feed-dot"></span>
          <div class="dashboard-feed-copy">
            <strong>${item.title}</strong>
            <p>${item.meta}</p>
          </div>
          <time>${item.timestamp}</time>
        `;
      } else if (kind === "notifications") {
        article.className = `dashboard-notification-item${item.is_read ? "" : " is-unread"}`;
        article.innerHTML = `
          <div class="dashboard-notification-head">
            <strong>${item.title}</strong>
            <span>${item.kind}</span>
          </div>
          <p>${item.body}</p>
          <time>${item.timestamp}</time>
        `;
      } else {
        article.className = `dashboard-audit-item dashboard-audit-item--${item.severity || "info"}`;
        article.innerHTML = `
          <span class="dashboard-audit-line"></span>
          <div>
            <strong>${item.title}</strong>
            <p>${item.meta}</p>
          </div>
          <time>${item.timestamp}</time>
        `;
      }
      container.appendChild(article);
    });
  }

  function hideSessionWarning() {
    if (!sessionWarning) {
      return;
    }
    sessionWarning.hidden = true;
    sessionWarning.classList.add("is-hidden");
    sessionWarningVisible = false;
  }

  function showSessionWarning() {
    if (!sessionWarning) {
      return;
    }
    sessionWarning.hidden = false;
    sessionWarning.classList.remove("is-hidden");
    sessionWarningVisible = true;
  }

  async function refreshDashboard() {
    if (!dashboardLiveUrl) {
      return;
    }
    try {
      const response = await window.fetch(dashboardLiveUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error(`Live refresh failed with ${response.status}`);
      }
      const payload = await response.json();
      updateScope("kpis", payload.kpis);
      updateScope("business", payload.business);
      updateScope("today", payload.today);
      updateScope("alerts", payload.alerts);
      if (liveTimestamp) {
        liveTimestamp.textContent = `Last sync ${payload.timestamp}`;
      }
      renderFeed("[data-live-feed]", payload.feed, "feed");
      renderFeed("[data-live-notifications]", payload.notifications, "notifications");
      renderFeed("[data-live-audit]", payload.audit, "audit");

      (payload.feed || []).forEach((item) => {
        const signature = `${item.title}|${item.timestamp}`;
        if (!liveFeedSignatures.has(signature)) {
          liveFeedSignatures.add(signature);
        }
      });

      const unreadAlerts = payload.alerts ? Number(payload.alerts["Unread Alerts"] || 0) : 0;
      if (unreadAlerts > 0) {
        body.dataset.dashboardReady = "true";
      }
    } catch (error) {
      showToast("Live dashboard", error instanceof Error ? error.message : "Refresh failed");
    }
  }

  function setupTilt() {
    const targets = doc.querySelectorAll(".dashboard-panel, .dashboard-kpi, .dashboard-action, .dashboard-file-card");
    targets.forEach((target) => {
      target.addEventListener("pointermove", (event) => {
        const rect = target.getBoundingClientRect();
        const offsetX = (event.clientX - rect.left) / rect.width - 0.5;
        const offsetY = (event.clientY - rect.top) / rect.height - 0.5;
        target.style.transform = `perspective(1000px) rotateX(${offsetY * -6}deg) rotateY(${offsetX * 8}deg) translateY(-2px)`;
      });
      target.addEventListener("pointerleave", () => {
        target.style.transform = "";
      });
    });
  }

  function setupDragAndResize() {
    const columns = Array.from(doc.querySelectorAll(".dashboard-column"));
    const panels = Array.from(doc.querySelectorAll(".dashboard-panel"));
    let dragged = null;

    panels.forEach((panel) => {
      panel.classList.add("is-draggable", "is-resizable");
      panel.draggable = true;
      panel.addEventListener("dragstart", () => {
        dragged = panel;
        panel.classList.add("is-dragging");
      });
      panel.addEventListener("dragend", () => {
        panel.classList.remove("is-dragging");
        dragged = null;
      });
    });

    columns.forEach((column) => {
      column.addEventListener("dragover", (event) => {
        event.preventDefault();
      });
      column.addEventListener("drop", (event) => {
        event.preventDefault();
        if (!dragged) {
          return;
        }
        const dropTarget = event.target.closest(".dashboard-panel");
        if (dropTarget && dropTarget !== dragged) {
          dropTarget.parentNode.insertBefore(dragged, dropTarget);
        } else {
          column.appendChild(dragged);
        }
      });
    });
  }

  function setupRipples() {
    doc.addEventListener("pointerdown", (event) => {
      const target = event.target.closest(".button, input[type='submit'], .admin-control-chip, .admin-command-trigger");
      if (!target) {
        return;
      }
      const ripple = doc.createElement("span");
      ripple.className = "admin-ripple";
      ripple.style.left = `${event.clientX}px`;
      ripple.style.top = `${event.clientY}px`;
      body.appendChild(ripple);
      window.setTimeout(() => ripple.remove(), 750);
    });
  }

  function markActivity() {
    lastActivityAt = Date.now();
    hideSessionWarning();
    savePreference("tc-last-activity", String(lastActivityAt));
  }

  function startSessionMonitor() {
    sessionTimer = window.setInterval(() => {
      if (Date.now() - lastActivityAt > 4 * 60 * 1000 && sessionWarning && !sessionWarningVisible) {
        showSessionWarning();
      }
    }, 15000);
  }

  function init() {
    applyTheme(loadPreference("tc-theme-style") || "cyan");
    applyContrast(loadPreference("tc-contrast-mode") === "high");
    applyGlow(loadPreference("tc-glow-intensity") || glowControl?.value || "100");

    themeButtons.forEach((button) => {
      button.addEventListener("click", () => applyTheme(button.getAttribute("data-theme-style")));
    });

    if (contrastToggle) {
      contrastToggle.addEventListener("click", () => applyContrast(body.dataset.contrastMode !== "high"));
    }

    if (glowControl) {
      glowControl.addEventListener("input", () => applyGlow(glowControl.value));
    }

    if (topbarSearch) {
      topbarSearch.addEventListener("input", (event) => filterLinks(event.target.value));
    }

    if (navFilter) {
      navFilter.addEventListener("input", (event) => filterLinks(event.target.value));
    }

    doc.querySelectorAll("[data-command-open]").forEach((button) => {
      button.addEventListener("click", openCommandPalette);
    });
    doc.querySelectorAll("[data-command-close]").forEach((button) => {
      button.addEventListener("click", closeCommandPalette);
    });

    if (commandInput) {
      commandInput.addEventListener("input", () => {
        activeCommandIndex = 0;
        renderCommandList(commandInput.value);
      });
      commandInput.addEventListener("keydown", (event) => {
        const links = Array.from(commandList?.querySelectorAll(".admin-command-item") || []);
        if (event.key === "ArrowDown") {
          event.preventDefault();
          activeCommandIndex = Math.min(activeCommandIndex + 1, Math.max(links.length - 1, 0));
          renderCommandList(commandInput.value);
        }
        if (event.key === "ArrowUp") {
          event.preventDefault();
          activeCommandIndex = Math.max(activeCommandIndex - 1, 0);
          renderCommandList(commandInput.value);
        }
        if (event.key === "Enter" && links[activeCommandIndex]) {
          links[activeCommandIndex].click();
        }
      });
    }

    doc.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        openCommandPalette();
      }
      if (event.key === "Escape") {
        closeCommandPalette();
      }
      if (event.key === "/" && doc.activeElement !== topbarSearch && doc.activeElement !== commandInput) {
        event.preventDefault();
        focusSearch();
      }
      if (event.altKey && event.key.toLowerCase() === "d") {
        event.preventDefault();
        window.location.href = "/admin/";
      }
      markActivity();
    });

    doc.addEventListener("pointermove", (event) => {
      body.style.setProperty("--cursor-x", `${event.clientX}px`);
      body.style.setProperty("--cursor-y", `${event.clientY}px`);
      markActivity();
    });
    doc.addEventListener("click", markActivity);

    if (sessionContinue) {
      sessionContinue.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        markActivity();
      });
    }

    setupTilt();
    setupDragAndResize();
    setupRipples();
    hideSessionWarning();
    startSessionMonitor();
    renderCommandList("");
    refreshDashboard();
    liveRefreshTimer = window.setInterval(refreshDashboard, 20000);
    body.dataset.dashboardReady = "true";
  }

  init();
})();

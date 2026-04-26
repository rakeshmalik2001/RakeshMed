document.addEventListener("DOMContentLoaded", () => {
  const select = document.querySelector("[data-auto-refresh-select]");
  const status = document.querySelector("[data-auto-refresh-status]");

  if (!(select instanceof HTMLSelectElement)) {
    return;
  }

  const storageKey = "rakeshmed-super-admin-auto-refresh-ms";
  const currentPath = window.location.pathname + window.location.search;
  let timerId = null;
  let countdownId = null;
  let remainingMs = 0;
  let isPausedForInput = false;

  const clearTimer = () => {
    if (timerId !== null) {
      window.clearInterval(timerId);
      timerId = null;
    }
    if (countdownId !== null) {
      window.clearInterval(countdownId);
      countdownId = null;
    }
  };

  const renderStatus = (text) => {
    if (status instanceof HTMLElement) {
      status.textContent = text;
    }
  };

  const shouldPauseForActiveElement = () => {
    const activeElement = document.activeElement;

    if (!(activeElement instanceof HTMLElement)) {
      return false;
    }

    if (activeElement.isContentEditable) {
      return true;
    }

    return activeElement.matches("input, textarea, select");
  };

  const formatRemaining = (ms) => {
    const seconds = Math.max(0, Math.ceil(ms / 1000));
    return `${seconds}s`;
  };

  const applyValue = (rawValue) => {
    clearTimer();
    const intervalMs = Number(rawValue);

    if (!Number.isFinite(intervalMs) || intervalMs <= 0) {
      window.localStorage.setItem(storageKey, "0");
      renderStatus("Auto-refresh off");
      return;
    }

    window.localStorage.setItem(storageKey, String(intervalMs));
    remainingMs = intervalMs;
    renderStatus(`Auto-refresh on · next refresh in ${formatRemaining(remainingMs)}`);
    countdownId = window.setInterval(() => {
      isPausedForInput = shouldPauseForActiveElement();
      if (isPausedForInput) {
        renderStatus(`Auto-refresh paused while editing · ${formatRemaining(remainingMs)} remaining`);
        return;
      }
      remainingMs -= 1000;
      if (remainingMs <= 0) {
        remainingMs = intervalMs;
      }
      renderStatus(`Auto-refresh on · next refresh in ${formatRemaining(remainingMs)}`);
    }, 1000);
    timerId = window.setInterval(() => {
      if (shouldPauseForActiveElement()) {
        return;
      }
      if (document.visibilityState !== "visible") {
        return;
      }
      if (window.location.pathname + window.location.search !== currentPath) {
        clearTimer();
        return;
      }
      window.location.reload();
    }, intervalMs);
  };

  const storedValue = window.localStorage.getItem(storageKey) || select.value || "0";
  select.value = storedValue;
  applyValue(storedValue);

  select.addEventListener("change", () => {
    applyValue(select.value);
  });

  window.addEventListener("beforeunload", clearTimer);
});

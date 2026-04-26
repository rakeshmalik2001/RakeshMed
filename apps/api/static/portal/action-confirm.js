document.addEventListener("submit", (event) => {
  const form = event.target;

  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  const submitter = event.submitter instanceof HTMLElement ? event.submitter : null;
  const message =
    submitter?.getAttribute("data-confirm-message") ||
    form.getAttribute("data-confirm-message");

  if (!message) {
    return;
  }

  if (!window.confirm(message)) {
    event.preventDefault();
  }
});

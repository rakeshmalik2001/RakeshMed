(() => {
    document.querySelectorAll("[data-auto-dismiss]").forEach((node) => {
        const timeout = Number(node.getAttribute("data-auto-dismiss") || "3000");
        window.setTimeout(() => {
            if (!node.isConnected) {
                return;
            }
            if (typeof bootstrap !== "undefined" && bootstrap.Alert) {
                bootstrap.Alert.getOrCreateInstance(node).close();
                return;
            }
            node.remove();
        }, timeout);
    });
})();

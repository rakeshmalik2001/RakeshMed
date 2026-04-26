(() => {
    const EXTRA_WIDTH = 48;
    const MIN_WIDTH = 92;

    const measureNode = document.createElement("span");
    measureNode.style.position = "absolute";
    measureNode.style.visibility = "hidden";
    measureNode.style.whiteSpace = "pre";
    measureNode.style.pointerEvents = "none";
    measureNode.style.left = "-9999px";
    measureNode.style.top = "-9999px";
    document.body.appendChild(measureNode);

    const getLongestOptionLabel = (select) => {
        const labels = Array.from(select.options || [])
            .map((option) => (option.textContent || "").trim())
            .filter(Boolean);
        if (!labels.length) {
            return "";
        }
        return labels.reduce((longest, current) => (current.length > longest.length ? current : longest), labels[0]);
    };

    const autosizeSelect = (select) => {
        if (!(select instanceof HTMLSelectElement) || select.multiple) {
            return;
        }
        if (select.dataset.autosize !== "true") {
            select.style.removeProperty("width");
            select.style.removeProperty("min-width");
            select.style.setProperty("max-width", "100%", "important");
            return;
        }

        const computed = window.getComputedStyle(select);
        measureNode.style.font = computed.font;
        measureNode.style.fontSize = computed.fontSize;
        measureNode.style.fontWeight = computed.fontWeight;
        measureNode.style.letterSpacing = computed.letterSpacing;
        measureNode.style.textTransform = computed.textTransform;

        const selectedLabel = (select.selectedOptions?.[0]?.textContent || "").trim();
        const longestLabel = getLongestOptionLabel(select);
        measureNode.textContent = selectedLabel.length >= longestLabel.length ? selectedLabel : longestLabel;

        const measuredWidth = Math.ceil(measureNode.getBoundingClientRect().width + EXTRA_WIDTH);
        const parentWidth = select.parentElement ? Math.floor(select.parentElement.getBoundingClientRect().width) : 0;
        const viewportWidth = Math.max(document.documentElement.clientWidth - 48, MIN_WIDTH);
        const cappedWidth = Math.min(
            Math.max(measuredWidth, MIN_WIDTH),
            parentWidth > 0 ? parentWidth : viewportWidth,
            viewportWidth,
        );

        select.style.setProperty("width", `${cappedWidth}px`, "important");
        select.style.setProperty("min-width", `${Math.min(cappedWidth, MIN_WIDTH)}px`, "important");
        select.style.setProperty("max-width", "100%", "important");
    };

    const autosizeAllSelects = (root = document) => {
        root.querySelectorAll("select").forEach((select) => autosizeSelect(select));
    };

    document.addEventListener("change", (event) => {
        if (event.target instanceof HTMLSelectElement) {
            autosizeSelect(event.target);
        }
    });

    window.addEventListener("resize", () => autosizeAllSelects());
    document.addEventListener("DOMContentLoaded", () => autosizeAllSelects());
    window.addEventListener("load", () => autosizeAllSelects());
    document.addEventListener("shown.bs.modal", (event) => autosizeAllSelects(event.target));

    if (typeof MutationObserver !== "undefined") {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                mutation.addedNodes.forEach((node) => {
                    if (!(node instanceof HTMLElement)) {
                        return;
                    }
                    if (node.matches("select")) {
                        autosizeSelect(node);
                        return;
                    }
                    autosizeAllSelects(node);
                });
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
})();

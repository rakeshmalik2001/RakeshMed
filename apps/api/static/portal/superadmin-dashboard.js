(() => {
    const body = document.body;
    const roleCatalogNode = document.getElementById("user-role-catalog-data");
    const roleCatalog = roleCatalogNode ? JSON.parse(roleCatalogNode.textContent || "[]") : [];
    const roleCatalogByRole = new Map(roleCatalog.map((entry) => [entry.role_value, entry]));
    const countryStatesNode = document.getElementById("user-country-states-data");
    const countryStatesMap = countryStatesNode ? JSON.parse(countryStatesNode.textContent || "{}") : {};
    ["createUserModal", "viewUserModal", "editUserModal", "deleteUserModal"].forEach((modalId) => {
        const modalNode = document.getElementById(modalId);
        if (modalNode && modalNode.parentElement !== body) {
            body.appendChild(modalNode);
        }
    });

    const themeToggle = document.querySelector("[data-theme-toggle]");
    const themeStorageKey = "rakeshmed-superadmin-theme";
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    const applyTheme = (theme) => {
        body.dataset.theme = theme;
        if (themeToggle) {
            themeToggle.innerHTML = theme === "dark"
                ? '<i class="bi bi-sun"></i>'
                : '<i class="bi bi-moon-stars"></i>';
        }
    };

    applyTheme(localStorage.getItem(themeStorageKey) || (prefersDark ? "dark" : "light"));

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const nextTheme = body.dataset.theme === "dark" ? "light" : "dark";
            localStorage.setItem(themeStorageKey, nextTheme);
            applyTheme(nextTheme);
            window.dispatchEvent(new Event("rakeshmed-theme-changed"));
        });
    }

    const userTable = document.querySelector("[data-user-table]");
    const userTableWrap = userTable ? userTable.closest(".table-wrap") : null;
    const pageTopbar = document.querySelector(".topbar");
    let floatingUserHeader = null;
    let floatingUserHeaderTable = null;
    let floatingUserHeaderDirty = true;

    const ensureFloatingUserHeader = () => {
        if (!userTable || !userTableWrap || !pageTopbar) {
            return null;
        }
        if (floatingUserHeader && floatingUserHeaderTable) {
            return { host: floatingUserHeader, table: floatingUserHeaderTable };
        }
        floatingUserHeader = document.createElement("div");
        floatingUserHeader.className = "floating-user-header";
        floatingUserHeader.setAttribute("aria-hidden", "true");
        floatingUserHeaderTable = document.createElement("table");
        floatingUserHeaderTable.className = userTable.className;
        floatingUserHeader.appendChild(floatingUserHeaderTable);
        document.body.appendChild(floatingUserHeader);
        return { host: floatingUserHeader, table: floatingUserHeaderTable };
    };

    const syncFloatingUserHeaderStructure = () => {
        const headerParts = ensureFloatingUserHeader();
        if (!headerParts || !userTable.tHead) {
            return;
        }
        headerParts.table.innerHTML = "";
        headerParts.table.appendChild(userTable.tHead.cloneNode(true));

        const sourceCells = Array.from(userTable.tHead.querySelectorAll("th"));
        const cloneCells = Array.from(headerParts.table.querySelectorAll("th"));
        sourceCells.forEach((sourceCell, index) => {
            const cloneCell = cloneCells[index];
            if (!cloneCell) {
                return;
            }
            cloneCell.style.width = `${Math.ceil(sourceCell.getBoundingClientRect().width)}px`;
            cloneCell.style.minWidth = cloneCell.style.width;
            cloneCell.style.maxWidth = cloneCell.style.width;
        });

        headerParts.table.style.width = `${Math.ceil(userTable.getBoundingClientRect().width)}px`;

        const sourceSelectAll = userTable.tHead.querySelector("[data-select-all]");
        const cloneSelectAll = headerParts.table.querySelector("[data-select-all]");
        if (sourceSelectAll && cloneSelectAll) {
            cloneSelectAll.checked = sourceSelectAll.checked;
            cloneSelectAll.addEventListener("change", () => {
                sourceSelectAll.checked = cloneSelectAll.checked;
                sourceSelectAll.dispatchEvent(new Event("change", { bubbles: true }));
            });
        }
        floatingUserHeaderDirty = false;
    };

    const syncFloatingUserHeaderPosition = () => {
        const headerParts = ensureFloatingUserHeader();
        if (!headerParts || !userTable || !userTableWrap || !userTable.tHead) {
            return;
        }

        if (floatingUserHeaderDirty) {
            syncFloatingUserHeaderStructure();
        }

        const topbarRect = pageTopbar.getBoundingClientRect();
        const wrapRect = userTableWrap.getBoundingClientRect();
        const headRect = userTable.tHead.getBoundingClientRect();
        const tableRect = userTable.getBoundingClientRect();
        const stickyTop = Math.ceil(topbarRect.top + topbarRect.height + 14);
        const floatingHeight = Math.ceil(headerParts.table.getBoundingClientRect().height || headRect.height || 0);
        const shouldShow =
            headRect.top <= stickyTop &&
            tableRect.bottom > stickyTop + floatingHeight + 12 &&
            wrapRect.width > 0;

        if (!shouldShow) {
            headerParts.host.classList.remove("is-visible");
            return;
        }

        headerParts.host.style.top = `${stickyTop}px`;
        headerParts.host.style.left = `${Math.ceil(wrapRect.left)}px`;
        headerParts.host.style.width = `${Math.ceil(wrapRect.width)}px`;
        headerParts.table.style.transform = `translateX(${-userTableWrap.scrollLeft}px)`;
        headerParts.host.classList.add("is-visible");
    };

    if (userTable && userTableWrap && pageTopbar) {
        syncFloatingUserHeaderPosition();
        window.addEventListener("scroll", syncFloatingUserHeaderPosition, { passive: true });
        window.addEventListener("resize", () => {
            floatingUserHeaderDirty = true;
            syncFloatingUserHeaderPosition();
        });
        window.addEventListener("load", () => {
            floatingUserHeaderDirty = true;
            syncFloatingUserHeaderPosition();
        });
        window.addEventListener("rakeshmed-theme-changed", () => {
            floatingUserHeaderDirty = true;
            syncFloatingUserHeaderPosition();
        });
        userTableWrap.addEventListener("scroll", syncFloatingUserHeaderPosition, { passive: true });
        if (typeof ResizeObserver !== "undefined") {
            const floatingHeaderResizeObserver = new ResizeObserver(() => {
                floatingUserHeaderDirty = true;
                syncFloatingUserHeaderPosition();
            });
            floatingHeaderResizeObserver.observe(userTableWrap);
            floatingHeaderResizeObserver.observe(userTable);
            floatingHeaderResizeObserver.observe(pageTopbar);
        }
    }

    const permissionMatrixTable = document.querySelector("[data-permission-matrix-table]");
    const permissionMatrixWrap = permissionMatrixTable ? permissionMatrixTable.closest("[data-permission-matrix-wrap]") : null;
    let floatingPermissionHeader = null;
    let floatingPermissionHeaderTable = null;
    let floatingPermissionHeaderDirty = true;

    const ensureFloatingPermissionHeader = () => {
        if (!permissionMatrixTable || !permissionMatrixWrap || !pageTopbar) {
            return null;
        }
        if (floatingPermissionHeader && floatingPermissionHeaderTable) {
            return { host: floatingPermissionHeader, table: floatingPermissionHeaderTable };
        }
        floatingPermissionHeader = document.createElement("div");
        floatingPermissionHeader.className = "floating-permission-header";
        floatingPermissionHeader.setAttribute("aria-hidden", "true");
        floatingPermissionHeaderTable = document.createElement("table");
        floatingPermissionHeaderTable.className = permissionMatrixTable.className;
        floatingPermissionHeader.appendChild(floatingPermissionHeaderTable);
        document.body.appendChild(floatingPermissionHeader);
        return { host: floatingPermissionHeader, table: floatingPermissionHeaderTable };
    };

    const syncFloatingPermissionHeaderStructure = () => {
        const headerParts = ensureFloatingPermissionHeader();
        if (!headerParts || !permissionMatrixTable.tHead) {
            return;
        }
        headerParts.table.innerHTML = "";
        headerParts.table.appendChild(permissionMatrixTable.tHead.cloneNode(true));

        const sourceCells = Array.from(permissionMatrixTable.tHead.querySelectorAll("th"));
        const cloneCells = Array.from(headerParts.table.querySelectorAll("th"));
        sourceCells.forEach((sourceCell, index) => {
            const cloneCell = cloneCells[index];
            if (!cloneCell) {
                return;
            }
            cloneCell.style.width = `${Math.ceil(sourceCell.getBoundingClientRect().width)}px`;
            cloneCell.style.minWidth = cloneCell.style.width;
            cloneCell.style.maxWidth = cloneCell.style.width;
        });

        headerParts.table.style.width = `${Math.ceil(permissionMatrixTable.getBoundingClientRect().width)}px`;
        floatingPermissionHeaderDirty = false;
    };

    const syncFloatingPermissionHeaderPosition = () => {
        const headerParts = ensureFloatingPermissionHeader();
        if (!headerParts || !permissionMatrixTable || !permissionMatrixWrap || !permissionMatrixTable.tHead) {
            return;
        }

        if (floatingPermissionHeaderDirty) {
            syncFloatingPermissionHeaderStructure();
        }

        const topbarRect = pageTopbar.getBoundingClientRect();
        const wrapRect = permissionMatrixWrap.getBoundingClientRect();
        const headRect = permissionMatrixTable.tHead.getBoundingClientRect();
        const stickyTop = Math.ceil(topbarRect.top + topbarRect.height + 14);
        const floatingHeight = Math.ceil(headerParts.table.getBoundingClientRect().height || headRect.height || 0);
        const isInnerScrolled = permissionMatrixWrap.scrollTop > 0;
        const shouldShow =
            (wrapRect.top <= stickyTop || isInnerScrolled) &&
            wrapRect.bottom > stickyTop + floatingHeight + 12 &&
            wrapRect.width > 0;

        if (!shouldShow) {
            headerParts.host.classList.remove("is-visible");
            return;
        }

        const hostTop = isInnerScrolled ? Math.max(Math.ceil(wrapRect.top), stickyTop) : stickyTop;
        headerParts.host.style.top = `${hostTop}px`;
        headerParts.host.style.left = `${Math.ceil(wrapRect.left)}px`;
        headerParts.host.style.width = `${Math.ceil(wrapRect.width)}px`;
        headerParts.table.style.transform = `translateX(${-permissionMatrixWrap.scrollLeft}px)`;
        headerParts.host.classList.add("is-visible");
    };

    if (permissionMatrixTable && permissionMatrixWrap && pageTopbar) {
        syncFloatingPermissionHeaderPosition();
        window.addEventListener("scroll", syncFloatingPermissionHeaderPosition, { passive: true });
        window.addEventListener("resize", () => {
            floatingPermissionHeaderDirty = true;
            syncFloatingPermissionHeaderPosition();
        });
        window.addEventListener("load", () => {
            floatingPermissionHeaderDirty = true;
            syncFloatingPermissionHeaderPosition();
        });
        window.addEventListener("rakeshmed-theme-changed", () => {
            floatingPermissionHeaderDirty = true;
            syncFloatingPermissionHeaderPosition();
        });
        permissionMatrixWrap.addEventListener("scroll", syncFloatingPermissionHeaderPosition, { passive: true });
        if (typeof ResizeObserver !== "undefined") {
            const floatingPermissionResizeObserver = new ResizeObserver(() => {
                floatingPermissionHeaderDirty = true;
                syncFloatingPermissionHeaderPosition();
            });
            floatingPermissionResizeObserver.observe(permissionMatrixWrap);
            floatingPermissionResizeObserver.observe(permissionMatrixTable);
            floatingPermissionResizeObserver.observe(pageTopbar);
        }
    }

    document.querySelectorAll("[data-select-all]").forEach((node) => {
        node.addEventListener("change", () => {
            const table = node.closest("table");
            if (!table) {
                return;
            }
            table.querySelectorAll('tbody input[type="checkbox"][name="selected_user_ids"]').forEach((checkbox) => {
                checkbox.checked = node.checked;
            });
        });
    });

    document.querySelectorAll("[data-column-toggle]").forEach((node) => {
        node.addEventListener("change", () => {
            const form = node.closest("form[data-user-filter-form]");
            if (!form) {
                return;
            }
            const table = document.querySelector("[data-user-table]");
            const syncColumns = () => {
                if (!table) {
                    return;
                }
                const checkedKeys = new Set(
                    Array.from(form.querySelectorAll('[data-column-toggle]:checked')).map((checkbox) => checkbox.value)
                );
                table.querySelectorAll("[data-column-key]").forEach((cell) => {
                    cell.style.display = checkedKeys.has(cell.dataset.columnKey) ? "" : "none";
                });
            };

            syncColumns();
            floatingUserHeaderDirty = true;
            syncFloatingUserHeaderPosition();

            const url = new URL(window.location.href);
            url.searchParams.delete("columns");
            url.searchParams.set("columns_configured", "1");
            url.searchParams.delete("page");
            form.querySelectorAll('[data-column-toggle]:checked').forEach((checkbox) => {
                url.searchParams.append("columns", checkbox.value);
            });
            window.history.replaceState({}, "", url.toString());
        });
    });

    const applyUserFilters = (form) => {
        if (!(form instanceof HTMLFormElement)) {
            return;
        }
        const url = new URL(window.location.href);
        const params = new URLSearchParams();
        const formData = new FormData(form);
        const usersShell = form.closest(".users-page-shell");
        if (usersShell) {
            usersShell.classList.add("is-filter-loading");
            usersShell.setAttribute("aria-busy", "true");
        }
        form.querySelectorAll("[data-auto-filter], .pill-btn, .toolbar-input, .toolbar-select").forEach((field) => {
            if (field instanceof HTMLElement) {
                field.setAttribute("aria-disabled", "true");
            }
            if ("disabled" in field) {
                field.disabled = true;
            }
        });

        formData.forEach((value, key) => {
            if (!value || key === "save_view" || key === "save_view_name") {
                return;
            }
            params.append(key, String(value));
        });

        params.delete("page");
        url.search = params.toString();
        window.location.assign(url.toString());
    };

    const permissionMatrixForm = document.getElementById("permission-matrix-form");
    const matrixSearchInput = document.querySelector("[data-matrix-search]");
    const matrixModuleSelect = document.querySelector("[data-matrix-module-select]");
    const matrixRoleFilter = document.querySelector("[data-matrix-role-filter]");
    const matrixStateFilter = document.querySelector("[data-matrix-state-filter]");
    const matrixModuleTabs = Array.from(document.querySelectorAll("[data-module-tab]"));
    const matrixRows = Array.from(document.querySelectorAll("[data-permission-row]"));
    const matrixSectionBanners = Array.from(document.querySelectorAll("[data-section-banner-row]"));
    const matrixFilterCardMatchingValue = document.querySelector('[data-filter-card-value="matching"]');
    const matrixFilterCardMatchingMeta = document.querySelector('[data-filter-card-meta="matching"]');
    const matrixFilterCardModuleValue = document.querySelector('[data-filter-card-value="module"]');
    const matrixFilterCardModuleMeta = document.querySelector('[data-filter-card-meta="module"]');
    const matrixFilterCardRoleValue = document.querySelector('[data-filter-card-value="role"]');
    const matrixFilterCardRoleMeta = document.querySelector('[data-filter-card-meta="role"]');
    const matrixFilterCardLevelValue = document.querySelector('[data-filter-card-value="level"]');
    const matrixFilterCardLevelMeta = document.querySelector('[data-filter-card-meta="level"]');
    const matrixDirtyCountNode = document.querySelector("[data-matrix-dirty-count]");
    const matrixDirtyTextNode = document.querySelector("[data-matrix-dirty-text]");
    const matrixResultsTextNode = document.querySelector("[data-matrix-results-text]");
    const matrixSaveDock = document.querySelector(".matrix-save-dock");
    const matrixSummaryRolesNode = document.querySelector("[data-matrix-summary-roles]");
    const matrixSummaryAllowedNode = document.querySelector("[data-matrix-summary-allowed]");
    const matrixSummaryLimitedNode = document.querySelector("[data-matrix-summary-limited]");
    const matrixSummaryDeniedNode = document.querySelector("[data-matrix-summary-denied]");
    const matrixSummaryRolesBarNode = document.querySelector("[data-matrix-summary-roles-bar]");
    const matrixSummaryAllowedBarNode = document.querySelector("[data-matrix-summary-allowed-bar]");
    const matrixSummaryLimitedBarNode = document.querySelector("[data-matrix-summary-limited-bar]");
    const matrixSummaryDeniedBarNode = document.querySelector("[data-matrix-summary-denied-bar]");
    let permissionMatrixAutosaveTimeout = null;
    let permissionMatrixAutosaveInFlight = false;
    let permissionMatrixAutosaveQueued = false;

    const formatMatrixStateLabel = (value) => {
        if (value === "allowed") {
            return "Full";
        }
        if (value === "limited") {
            return "Limited";
        }
        return "Denied";
    };

    const updatePermissionMatrixSummary = () => {
        if (!permissionMatrixForm) {
            return;
        }
        const controls = Array.from(permissionMatrixForm.querySelectorAll("[data-permission-control]"));
        const roleCount = document.querySelectorAll("[data-role-column]").length;
        const totalCells = controls.length;
        let allowedCount = 0;
        let limitedCount = 0;
        let deniedCount = 0;

        controls.forEach((control) => {
            const state = control.dataset.currentState || control.dataset.initialState || "denied";
            if (state === "allowed") {
                allowedCount += 1;
            } else if (state === "limited") {
                limitedCount += 1;
            } else {
                deniedCount += 1;
            }
        });

        const toPercent = (value, total) => {
            if (!total) {
                return "0%";
            }
            return `${Math.max(0, Math.min(100, (value / total) * 100))}%`;
        };

        if (matrixSummaryRolesNode) {
            matrixSummaryRolesNode.textContent = String(roleCount);
        }
        if (matrixSummaryAllowedNode) {
            matrixSummaryAllowedNode.textContent = String(allowedCount);
        }
        if (matrixSummaryLimitedNode) {
            matrixSummaryLimitedNode.textContent = String(limitedCount);
        }
        if (matrixSummaryDeniedNode) {
            matrixSummaryDeniedNode.textContent = String(deniedCount);
        }
        if (matrixSummaryRolesBarNode) {
            matrixSummaryRolesBarNode.style.width = roleCount > 0 ? "100%" : "0%";
        }
        if (matrixSummaryAllowedBarNode) {
            matrixSummaryAllowedBarNode.style.width = toPercent(allowedCount, totalCells);
        }
        if (matrixSummaryLimitedBarNode) {
            matrixSummaryLimitedBarNode.style.width = toPercent(limitedCount, totalCells);
        }
        if (matrixSummaryDeniedBarNode) {
            matrixSummaryDeniedBarNode.style.width = toPercent(deniedCount, totalCells);
        }
    };

    const setPermissionControlState = (control, state, markDirty = true) => {
        if (!(control instanceof HTMLElement)) {
            return;
        }
        const input = control.querySelector("[data-matrix-state-input]");
        if (!(input instanceof HTMLInputElement)) {
            return;
        }
        const normalizedState = ["allowed", "limited", "denied"].includes(state) ? state : "denied";
        input.value = normalizedState;
        control.dataset.currentState = normalizedState;
        control.dataset.state = normalizedState;
        control.querySelectorAll("[data-state-choice]").forEach((button) => {
            button.classList.toggle("is-active", button.dataset.stateChoice === normalizedState);
        });
        const initialState = control.dataset.initialState || "denied";
        const isDirty = normalizedState !== initialState;
        control.classList.toggle("is-dirty", markDirty && isDirty);
        const cell = control.closest("[data-cell-state]");
        if (cell) {
            cell.dataset.cellState = normalizedState;
        }
        const label = control.parentElement?.querySelector("[data-matrix-state-label]");
        if (label) {
            label.textContent = formatMatrixStateLabel(normalizedState);
        }
        updatePermissionMatrixSummary();
    };

    const getVisibleMatrixRows = () => matrixRows.filter((row) => row.style.display !== "none");

    const updateMatrixDirtyState = () => {
        if (!permissionMatrixForm) {
            return;
        }
        const dirtyControls = Array.from(permissionMatrixForm.querySelectorAll("[data-permission-control].is-dirty"));
        const dirtyCount = dirtyControls.length;
        permissionMatrixForm.dataset.hasUnsavedChanges = dirtyCount > 0 ? "true" : "false";
        if (matrixDirtyCountNode) {
            matrixDirtyCountNode.textContent = String(dirtyCount);
        }
        if (matrixDirtyTextNode) {
            matrixDirtyTextNode.textContent = dirtyCount
                ? "Saving will apply these permission changes to live backend rules and audit logs."
                : "No unsaved changes. The current matrix matches the last saved state.";
        }
        if (matrixSaveDock) {
            matrixSaveDock.classList.toggle("is-dirty", dirtyCount > 0);
            matrixSaveDock.classList.toggle("is-clean", dirtyCount === 0);
        }
    };

    const markPermissionMatrixControlsSaved = () => {
        if (!permissionMatrixForm) {
            return;
        }
        permissionMatrixForm.querySelectorAll("[data-permission-control]").forEach((control) => {
            const currentState = control.dataset.currentState || control.dataset.initialState || "denied";
            control.dataset.initialState = currentState;
            control.classList.remove("is-dirty");
        });
        updatePermissionMatrixSummary();
        updateMatrixDirtyState();
    };

    const autosavePermissionMatrix = async () => {
        if (!permissionMatrixForm) {
            return;
        }
        if (permissionMatrixAutosaveInFlight) {
            permissionMatrixAutosaveQueued = true;
            return;
        }
        permissionMatrixAutosaveInFlight = true;
        permissionMatrixForm.dataset.autosaving = "true";
        if (matrixDirtyTextNode) {
            matrixDirtyTextNode.textContent = "Saving changes to the database...";
        }

        try {
            const formData = new FormData(permissionMatrixForm);
            const response = await fetch(window.location.href, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json",
                },
                credentials: "same-origin",
            });

            if (!response.ok) {
                throw new Error(`Autosave failed with status ${response.status}`);
            }

            await response.json();
            markPermissionMatrixControlsSaved();
            if (matrixDirtyTextNode) {
                matrixDirtyTextNode.textContent = "All permission changes are saved in real time.";
            }
        } catch (_error) {
            permissionMatrixForm.dataset.hasUnsavedChanges = "true";
            if (matrixDirtyTextNode) {
                matrixDirtyTextNode.textContent = "Autosave failed. Your latest permission changes are not yet saved.";
            }
        } finally {
            permissionMatrixAutosaveInFlight = false;
            permissionMatrixForm.dataset.autosaving = "false";
            if (permissionMatrixAutosaveQueued) {
                permissionMatrixAutosaveQueued = false;
                window.setTimeout(() => {
                    void autosavePermissionMatrix();
                }, 120);
            }
        }
    };

    const schedulePermissionMatrixAutosave = () => {
        if (!permissionMatrixForm) {
            return;
        }
        if (permissionMatrixAutosaveTimeout) {
            window.clearTimeout(permissionMatrixAutosaveTimeout);
        }
        permissionMatrixAutosaveTimeout = window.setTimeout(() => {
            permissionMatrixAutosaveTimeout = null;
            void autosavePermissionMatrix();
        }, 220);
    };

    const updateMatrixSectionVisibility = () => {
        matrixSectionBanners.forEach((bannerRow) => {
            const sectionKey = bannerRow.dataset.sectionBannerRow;
            const hasVisibleRows = matrixRows.some((row) => row.dataset.sectionKey === sectionKey && row.style.display !== "none");
            bannerRow.style.display = hasVisibleRows ? "" : "none";
        });
    };

    const updateMatrixModuleTabsSummary = () => {
        const query = (matrixSearchInput?.value || "").trim().toLowerCase();
        const roleKey = matrixRoleFilter?.value || "all";
        const stateKey = matrixStateFilter?.value || "all";
        const moduleKey = matrixModuleSelect?.value || "all";
        const moduleCounts = new Map();

        matrixRows.forEach((row) => {
            const rowText = (row.dataset.searchIndex || row.textContent || "").toLowerCase();
            const textMatches = !query || rowText.includes(query);
            const cells = Array.from(row.querySelectorAll("[data-role-key]"));
            const selectedRoleCell = roleKey === "all"
                ? null
                : cells.find((cell) => cell.dataset.roleKey === roleKey);

            let rowMatches = textMatches;
            if (rowMatches && roleKey !== "all") {
                rowMatches = Boolean(selectedRoleCell);
            }
            if (rowMatches && stateKey !== "all") {
                if (selectedRoleCell) {
                    rowMatches = selectedRoleCell.dataset.cellState === stateKey;
                } else {
                    rowMatches = cells.some((cell) => cell.dataset.cellState === stateKey);
                }
            }

            if (!rowMatches) {
                return;
            }
            const sectionKey = row.dataset.sectionKey || "";
            moduleCounts.set(sectionKey, (moduleCounts.get(sectionKey) || 0) + 1);
        });

        const totalMatching = Array.from(moduleCounts.values()).reduce((sum, value) => sum + value, 0);
        matrixModuleTabs.forEach((tab) => {
            const tabKey = tab.dataset.moduleTab || "all";
            const labelNode = tab.querySelector("[data-module-tab-label]");
            const countNode = tab.querySelector("[data-module-tab-count]");
            const unitNode = tab.querySelector("[data-module-tab-unit]");
            const baseLabel = tab.dataset.moduleLabel || "Module";
            const count = tabKey === "all" ? totalMatching : (moduleCounts.get(tabKey) || 0);
            const roleLabel = roleKey !== "all"
                ? (matrixRoleFilter?.selectedOptions?.[0]?.textContent?.trim() || "")
                : "";
            const stateLabel = stateKey !== "all"
                ? (matrixStateFilter?.selectedOptions?.[0]?.textContent?.trim() || "")
                : "";
            const labelParts = [baseLabel];
            if (roleLabel) {
                labelParts.push(roleLabel);
            }
            if (stateLabel) {
                labelParts.push(stateLabel);
            }

            if (labelNode) {
                labelNode.textContent = labelParts.join(" · ");
            }
            if (countNode) {
                countNode.textContent = String(count);
            }
            if (unitNode) {
                unitNode.textContent = count === 1 ? "rule" : "rules";
            }
        });
    };

    const applyMatrixFilters = () => {
        const query = (matrixSearchInput?.value || "").trim().toLowerCase();
        const moduleKey = matrixModuleSelect?.value || "all";
        const roleKey = matrixRoleFilter?.value || "all";
        const stateKey = matrixStateFilter?.value || "all";

        matrixRows.forEach((row) => {
            const rowText = (row.dataset.searchIndex || row.textContent || "").toLowerCase();
            const moduleMatches = moduleKey === "all" || row.dataset.sectionKey === moduleKey;
            const textMatches = !query || rowText.includes(query);
            const cells = Array.from(row.querySelectorAll("[data-role-key]"));
            const roleMatches = roleKey === "all" || cells.some((cell) => cell.dataset.roleKey === roleKey);
            const stateMatches = stateKey === "all" || cells.some((cell) => {
                if (roleKey !== "all" && cell.dataset.roleKey !== roleKey) {
                    return false;
                }
                return cell.dataset.cellState === stateKey;
            });
            row.style.display = moduleMatches && textMatches && roleMatches && stateMatches ? "" : "none";
        });

        const visibleRows = getVisibleMatrixRows();
        if (matrixResultsTextNode) {
            matrixResultsTextNode.textContent = visibleRows.length
                ? `Showing ${visibleRows.length} permission rows with live backend sync on save.`
                : "No permission rows match the current search/filter combination.";
        }

        document.querySelectorAll("[data-role-column]").forEach((th) => {
            const shouldHide = roleKey !== "all" && th.dataset.roleColumn !== roleKey;
            th.classList.toggle("is-role-hidden", shouldHide);
        });
        matrixRows.forEach((row) => {
            row.querySelectorAll("[data-role-key]").forEach((cell) => {
                const shouldHide = roleKey !== "all" && cell.dataset.roleKey !== roleKey;
                cell.closest("td")?.classList.toggle("is-role-hidden", shouldHide);
            });
        });

        matrixModuleTabs.forEach((tab) => {
            tab.classList.toggle("active", (tab.dataset.moduleTab || "all") === moduleKey);
        });

        updateMatrixFilterCards();
        updateMatrixSectionVisibility();
        floatingPermissionHeaderDirty = true;
        syncFloatingPermissionHeaderPosition();
    };

    const updateMatrixFilterCards = () => {
        const visibleRows = getVisibleMatrixRows();
        const visibleCount = visibleRows.length;
        const totalRoles = document.querySelectorAll("[data-role-column]").length;
        const moduleLabel = matrixModuleSelect?.selectedOptions?.[0]?.textContent?.trim() || "All modules";
        const roleLabel = matrixRoleFilter?.selectedOptions?.[0]?.textContent?.trim() || "All roles";
        const stateLabel = matrixStateFilter?.selectedOptions?.[0]?.textContent?.trim() || "All levels";
        const searchText = (matrixSearchInput?.value || "").trim();

        if (matrixFilterCardMatchingValue) {
            matrixFilterCardMatchingValue.textContent = String(visibleCount);
        }
        if (matrixFilterCardMatchingMeta) {
            matrixFilterCardMatchingMeta.textContent = visibleCount === 1 ? "rule visible" : "rules visible";
        }
        if (matrixFilterCardModuleValue) {
            matrixFilterCardModuleValue.textContent = moduleLabel;
        }
        if (matrixFilterCardModuleMeta) {
            matrixFilterCardModuleMeta.textContent = `${visibleCount} ${visibleCount === 1 ? "matching rule" : "matching rules"}`;
        }
        if (matrixFilterCardRoleValue) {
            matrixFilterCardRoleValue.textContent = roleLabel;
        }
        if (matrixFilterCardRoleMeta) {
            matrixFilterCardRoleMeta.textContent = roleLabel.toLowerCase() === "all roles"
                ? `${totalRoles} roles available`
                : `${visibleCount} ${visibleCount === 1 ? "matching rule" : "matching rules"}`;
        }
        if (matrixFilterCardLevelValue) {
            matrixFilterCardLevelValue.textContent = stateLabel;
        }
        if (matrixFilterCardLevelMeta) {
            matrixFilterCardLevelMeta.textContent = searchText
                ? `Search: ${searchText}`
                : `${visibleCount} ${visibleCount === 1 ? "matching rule" : "matching rules"}`;
        }
    };

    const resetPermissionMatrixControls = () => {
        if (!permissionMatrixForm) {
            return;
        }
        permissionMatrixForm.querySelectorAll("[data-permission-control]").forEach((control) => {
            setPermissionControlState(control, control.dataset.initialState || "denied", false);
        });
        updatePermissionMatrixSummary();
        updateMatrixDirtyState();
        applyMatrixFilters();
    };

    const getMatrixControlsForVisibleRows = () => {
        const controls = [];
        getVisibleMatrixRows().forEach((row) => {
            row.querySelectorAll("[data-permission-control]").forEach((control) => controls.push(control));
        });
        return controls;
    };

    if (permissionMatrixForm) {
        permissionMatrixForm.querySelectorAll("[data-permission-control]").forEach((control) => {
            setPermissionControlState(control, control.dataset.initialState || "denied", false);
        });
        updatePermissionMatrixSummary();
        updateMatrixDirtyState();
        applyMatrixFilters();
        permissionMatrixForm.addEventListener("submit", () => {
            permissionMatrixForm.dataset.hasUnsavedChanges = "false";
        });
    }

    window.addEventListener("beforeunload", (event) => {
        if (permissionMatrixForm?.dataset.hasUnsavedChanges === "true") {
            event.preventDefault();
            event.returnValue = "";
        }
    });

    document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }

        const moduleTab = target.closest("[data-module-tab]");
        if (moduleTab instanceof HTMLElement) {
            const nextValue = moduleTab.dataset.moduleTab || "all";
            if (matrixModuleSelect) {
                matrixModuleSelect.value = nextValue;
            }
            applyMatrixFilters();
            return;
        }

        const stateButton = target.closest("[data-state-choice]");
        if (stateButton instanceof HTMLElement) {
            const control = stateButton.closest("[data-permission-control]");
            setPermissionControlState(control, stateButton.dataset.stateChoice || "denied");
            updateMatrixDirtyState();
            applyMatrixFilters();
            schedulePermissionMatrixAutosave();
            return;
        }

        const rowStateButton = target.closest("[data-row-state-set]");
        if (rowStateButton instanceof HTMLElement) {
            const row = rowStateButton.closest("[data-permission-row]");
            if (!row) {
                return;
            }
            row.querySelectorAll("[data-permission-control]").forEach((control) => {
                if (roleKeyMatchesCurrentFilter(control.closest("[data-role-key]"))) {
                    setPermissionControlState(control, rowStateButton.dataset.rowStateSet || "denied");
                }
            });
            updateMatrixDirtyState();
            applyMatrixFilters();
            schedulePermissionMatrixAutosave();
            return;
        }

        const clearFiltersButton = target.closest("[data-matrix-clear-filters]");
        if (clearFiltersButton instanceof HTMLElement) {
            if (matrixSearchInput) {
                matrixSearchInput.value = "";
            }
            if (matrixModuleSelect) {
                matrixModuleSelect.value = "all";
            }
            if (matrixRoleFilter) {
                matrixRoleFilter.value = "all";
            }
            if (matrixStateFilter) {
                matrixStateFilter.value = "all";
            }
            applyMatrixFilters();
            return;
        }

        const resetButton = target.closest("[data-matrix-reset]");
        if (resetButton instanceof HTMLElement) {
            resetPermissionMatrixControls();
            return;
        }

        const copyButton = target.closest("[data-matrix-copy-apply]");
        if (copyButton instanceof HTMLElement) {
            const sourceRole = permissionMatrixForm.querySelector("[data-matrix-copy-source]")?.value || "";
            const targetRole = permissionMatrixForm.querySelector("[data-matrix-copy-target]")?.value || "";
            if (!sourceRole || !targetRole || sourceRole === targetRole) {
                return;
            }
            getVisibleMatrixRows().forEach((row) => {
                const sourceControl = row.querySelector(`[data-role-key="${sourceRole}"] [data-permission-control]`);
                const targetControl = row.querySelector(`[data-role-key="${targetRole}"] [data-permission-control]`);
                if (sourceControl && targetControl) {
                    const nextState = sourceControl.dataset.currentState || sourceControl.dataset.initialState || "denied";
                    setPermissionControlState(targetControl, nextState);
                }
            });
            updateMatrixDirtyState();
            applyMatrixFilters();
            schedulePermissionMatrixAutosave();
            return;
        }

        const applyButton = target.closest("[data-matrix-state-apply]");
        if (applyButton instanceof HTMLElement) {
            const bulkState = permissionMatrixForm.querySelector("[data-matrix-bulk-state]")?.value || "denied";
            getMatrixControlsForVisibleRows().forEach((control) => {
                if (roleKeyMatchesCurrentFilter(control.closest("[data-role-key]"))) {
                    setPermissionControlState(control, bulkState);
                }
            });
            updateMatrixDirtyState();
            applyMatrixFilters();
            schedulePermissionMatrixAutosave();
        }
    });

    function roleKeyMatchesCurrentFilter(roleCell) {
        if (!(roleCell instanceof HTMLElement)) {
            return false;
        }
        const activeRoleFilter = matrixRoleFilter?.value || "all";
        return activeRoleFilter === "all" || roleCell.dataset.roleKey === activeRoleFilter;
    }

    document.addEventListener("input", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        if (target === matrixSearchInput) {
            applyMatrixFilters();
        }
    });

    document.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        if (target === matrixModuleSelect || target === matrixRoleFilter || target === matrixStateFilter) {
            applyMatrixFilters();
        }
    });

    document.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        if (!target.matches("[data-auto-filter]")) {
            return;
        }
        const form = target.closest("form[data-user-filter-form]");
        if (!form) {
            return;
        }
        applyUserFilters(form);
    });

    const userSearchInput = document.querySelector("[data-user-search-input]");
    const userTableBody = document.querySelector("[data-user-table-body]");
    const userTableMeta = document.querySelector("[data-user-table-meta]");
    if (userSearchInput && userTableBody) {
        const userRows = Array.from(userTableBody.querySelectorAll("[data-user-row]"));
        const emptyRow = userTableBody.querySelector("[data-user-empty-row]");
        const baseMetaText = userTableMeta ? userTableMeta.textContent : "";

        const filterUserRows = () => {
            const query = userSearchInput.value.trim().toLowerCase();
            let visibleCount = 0;

            userRows.forEach((row) => {
                const haystack = (row.dataset.searchIndex || row.textContent || "").toLowerCase();
                const matches = !query || haystack.includes(query);
                row.style.display = matches ? "" : "none";
                if (matches) {
                    visibleCount += 1;
                }
            });

            if (emptyRow) {
                emptyRow.style.display = visibleCount === 0 ? "" : "none";
            }
            if (userTableMeta) {
                userTableMeta.textContent = query
                    ? `Showing ${visibleCount} matching users on this page`
                    : baseMetaText;
            }
        };

        filterUserRows();
        userSearchInput.addEventListener("input", filterUserRows);
    }

    const readPayload = (userId) => {
        if (!userId) {
            return null;
        }
        const payloadNode = document.getElementById(`user-payload-${userId}`);
        if (!payloadNode) {
            return null;
        }
        const payload = {};
        payloadNode.querySelectorAll("[data-field]").forEach((fieldNode) => {
            payload[fieldNode.dataset.field] = fieldNode.value ?? fieldNode.textContent ?? "";
        });
        return payload;
    };

    const selectedUserActions = document.querySelector("[data-selected-user-actions]");
    if (selectedUserActions && selectedUserActions.parentElement !== document.body) {
        document.body.appendChild(selectedUserActions);
    }

    const isUserRowInteractiveTarget = (target) => {
        return Boolean(target.closest("button, a, input, select, textarea, label, .dropdown-menu"));
    };

    const selectUserRow = (row) => {
        if (!row || !selectedUserActions) {
            return;
        }
        const checkbox = row.querySelector('input[name="selected_user_ids"]');
        const userId = row.dataset.userId || (checkbox ? checkbox.value : "");
        const payload = readPayload(userId);
        if (!payload) {
            return;
        }

        document.querySelectorAll("[data-user-row].is-row-selected").forEach((selectedRow) => {
            selectedRow.classList.remove("is-row-selected");
        });
        row.classList.add("is-row-selected");

        const displayName = payload.full_name || payload.phone_number || `User ${userId}`;
        const initialNode = selectedUserActions.querySelector("[data-selected-user-initial]");
        const nameNode = selectedUserActions.querySelector("[data-selected-user-name]");
        const metaNode = selectedUserActions.querySelector("[data-selected-user-meta]");
        if (initialNode) {
            initialNode.textContent = String(displayName).trim().slice(0, 1).toUpperCase() || "U";
        }
        if (nameNode) {
            nameNode.textContent = displayName;
        }
        if (metaNode) {
            metaNode.textContent = `${payload.employee_code || "-"} | ${payload.role_label || payload.role || "-"} | ${payload.account_status_label || payload.account_status || "-"}`;
        }

        selectedUserActions.querySelectorAll("[data-selected-target-id]").forEach((field) => {
            field.value = userId;
        });
        selectedUserActions.querySelectorAll("[data-selected-view-trigger]").forEach((trigger) => {
            trigger.dataset.userViewTrigger = userId;
        });
        selectedUserActions.querySelectorAll("[data-selected-edit-trigger]").forEach((trigger) => {
            trigger.dataset.userEditTrigger = userId;
        });
        selectedUserActions.querySelectorAll("[data-selected-delete-trigger]").forEach((trigger) => {
            trigger.dataset.userDeleteTrigger = userId;
            trigger.dataset.userDeleteName = displayName;
            trigger.disabled = userId === String(selectedUserActions.dataset.currentUserId || "");
        });

        const auditLink = selectedUserActions.querySelector("[data-selected-audit-link]");
        if (auditLink) {
            auditLink.href = `${window.location.pathname}?audit_user=${encodeURIComponent(userId)}`;
        }
        const statusAction = selectedUserActions.querySelector("[data-selected-status-action]");
        const statusLabel = selectedUserActions.querySelector("[data-selected-status-label]");
        if (statusAction && statusLabel) {
            const shouldDeactivate = payload.account_status === "active";
            statusAction.value = shouldDeactivate ? "deactivate" : "activate";
            statusLabel.innerHTML = shouldDeactivate
                ? '<i class="bi bi-toggle-off"></i>Deactivate'
                : '<i class="bi bi-toggle-on"></i>Activate';
        }
        const lockAction = selectedUserActions.querySelector("[data-selected-lock-action]");
        const lockLabel = selectedUserActions.querySelector("[data-selected-lock-label]");
        if (lockAction && lockLabel) {
            const shouldUnlock = payload.account_locked_bool === "true";
            lockAction.value = shouldUnlock ? "unlock" : "lock";
            lockLabel.innerHTML = shouldUnlock
                ? '<i class="bi bi-unlock"></i>Unlock'
                : '<i class="bi bi-lock"></i>Lock';
        }

        if (window.bootstrap?.Modal) {
            window.bootstrap.Modal.getOrCreateInstance(selectedUserActions).show();
        }
    };

    document.addEventListener("click", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLElement)) {
            return;
        }
        if (isUserRowInteractiveTarget(target)) {
            return;
        }
        const row = target.closest("[data-user-row]");
        if (!row) {
            return;
        }
        selectUserRow(row);
    });

    document.querySelectorAll("[data-user-row]").forEach((row) => {
        row.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLElement) || isUserRowInteractiveTarget(target)) {
                return;
            }
            selectUserRow(row);
        });
    });

    selectedUserActions?.addEventListener("hidden.bs.modal", () => {
        document.querySelectorAll("[data-user-row].is-row-selected").forEach((selectedRow) => {
            selectedRow.classList.remove("is-row-selected");
        });
    });

    const assignFormValue = (form, fieldName, value) => {
        if (!form) {
            return;
        }
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (!field) {
            return;
        }
        if (field.type === "checkbox") {
            field.checked = value === true || value === "true" || value === "True" || value === "1";
            return;
        }
        field.value = value ?? "";
    };

    function rebuildSelectOptions(field, values, selectedValue, placeholderLabel) {
        if (!field) {
            return;
        }
        const uniqueValues = Array.from(new Set((values || []).filter(Boolean)));
        const preferredValue = selectedValue ?? "";
        if (preferredValue && !uniqueValues.includes(preferredValue)) {
            uniqueValues.push(preferredValue);
        }

        field.innerHTML = "";
        const placeholderOption = document.createElement("option");
        placeholderOption.value = "";
        placeholderOption.textContent = placeholderLabel;
        field.appendChild(placeholderOption);

        uniqueValues.forEach((value) => {
            const option = document.createElement("option");
            option.value = value;
            option.textContent = value;
            field.appendChild(option);
        });

        field.value = preferredValue && uniqueValues.includes(preferredValue) ? preferredValue : "";
    }

    function syncRoleCatalogFields(form, overrides = {}) {
        if (!form) {
            return;
        }
        const roleField = form.querySelector('[name="role"]');
        if (!roleField) {
            return;
        }
        const roleEntry = roleCatalogByRole.get(roleField.value);
        const typeOfUserField = form.querySelector('[name="type_of_user"]');
        const departmentField = form.querySelector('[name="department"]');
        const designationField = form.querySelector('[name="designation"]');

        if (typeOfUserField && roleEntry) {
            typeOfUserField.value = overrides.typeOfUserValue || roleEntry.type_of_user_value || "";
        }

        rebuildSelectOptions(
            departmentField,
            roleEntry ? [roleEntry.department] : [],
            overrides.departmentValue || (roleEntry ? roleEntry.department : ""),
            roleEntry ? "Select department" : "Select role first"
        );
        rebuildSelectOptions(
            designationField,
            roleEntry ? [roleEntry.designation] : [],
            overrides.designationValue || (roleEntry ? roleEntry.designation : ""),
            roleEntry ? "Select designation" : "Select role first"
        );
    }

    const assignLookupPayloadToForm = (form, payload) => {
        if (!form || !payload) {
            return;
        }
        const hiddenIdField = form.querySelector("[data-edit-hidden-id]");
        if (hiddenIdField) {
            hiddenIdField.value = payload.id || "";
        }
        const userIdLookupField = form.querySelector("[data-user-id-lookup]");
        if (userIdLookupField) {
            userIdLookupField.value = payload.id || "";
        }
        [
            "employee_code",
            "username",
            "full_name",
            "role",
            "email",
            "phone_number",
            "country",
            "state",
            "district",
            "address",
            "account_status",
            "remarks",
        ].forEach((fieldName) => assignFormValue(form, fieldName, payload[fieldName]));
        syncRoleCatalogFields(form, {
            typeOfUserValue: payload.type_of_user,
            departmentValue: payload.department,
            designationValue: payload.designation,
        });
        void syncLocationFields(form, {
            countryValue: payload.country,
            stateValue: payload.state,
            districtValue: payload.district,
        });
        assignFormValue(form, "email_verified", payload.email_verified);
        assignFormValue(form, "account_locked", payload.account_locked);
        assignFormValue(form, "mfa_enabled", payload.mfa_enabled);
        assignFormValue(form, "invite_user", false);
        assignFormValue(form, "temporary_password", "");
    };

    const setEmployeeCodeFeedback = (field, message) => {
        const feedbackNode = field?.closest("div")?.querySelector("[data-employee-code-feedback]");
        if (feedbackNode) {
            feedbackNode.textContent = message;
        }
    };

    const setUserIdFeedback = (field, message) => {
        const feedbackNode = field?.closest("div")?.querySelector("[data-user-id-feedback]");
        if (feedbackNode) {
            feedbackNode.textContent = message;
        }
    };

    const setUsernameFeedback = (field, message) => {
        const feedbackNode = field?.closest("div")?.querySelector("[data-username-feedback]");
        if (feedbackNode) {
            feedbackNode.textContent = message;
        }
    };

    async function lookupEditUser(form, params, feedbackField, setFeedback) {
        const query = new URLSearchParams(params);
        setFeedback(feedbackField, "Looking up user...");
        try {
            const response = await fetch(`/api/v1/auth/admin/users/employee-code/lookup/?${query.toString()}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.detail || "Employee not found.");
            }
            assignLookupPayloadToForm(form, payload);
            refreshProfileCompletion(form);
            setEmployeeCodeFeedback(form.querySelector('[name="employee_code"]'), "Employee loaded successfully. You can search by full code or numeric code only.");
            setUserIdFeedback(form.querySelector("[data-user-id-lookup]"), "User loaded successfully.");
        } catch (error) {
            const message = error instanceof Error ? error.message : "Employee not found.";
            setFeedback(feedbackField, message);
        }
    }

    async function syncLocationFields(form, overrides = {}) {
        if (!form) {
            return;
        }
        const countryField = form.querySelector('[name="country"]');
        const stateField = form.querySelector('[name="state"]');
        const districtField = form.querySelector('[name="district"]');
        if (!countryField || !stateField || !districtField) {
            return;
        }

        const countryValue = overrides.countryValue ?? countryField.value ?? "";
        const stateValue = overrides.stateValue ?? stateField.value ?? "";
        const districtValue = overrides.districtValue ?? districtField.value ?? "";

        countryField.value = countryValue || "";

        if (!countryValue) {
            rebuildSelectOptions(stateField, [], "", "Select country first");
            rebuildSelectOptions(districtField, [], "", "Select state first");
            return;
        }

        const availableStates = countryStatesMap[countryValue] || [];
        if (!availableStates.length) {
            rebuildSelectOptions(stateField, [], "", "Select state");
            rebuildSelectOptions(districtField, [], "", "Select state first");
            return;
        }
        rebuildSelectOptions(stateField, availableStates, stateValue, "Select state");

        if (!stateValue) {
            rebuildSelectOptions(districtField, [], "", "Select state first");
            return;
        }

        try {
            const districtResponse = await fetch(
                `/api/v1/auth/admin/users/location-options/?country=${encodeURIComponent(countryValue)}&state=${encodeURIComponent(stateValue)}`,
                {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    credentials: "same-origin",
                }
            );
            const districtPayload = await districtResponse.json();
            rebuildSelectOptions(districtField, districtPayload.districts || [], districtValue, "Select district");
        } catch (_error) {
            rebuildSelectOptions(districtField, [], districtValue, "Select district");
        }
    }

    async function generateEmployeeCode(roleValue, employeeCodeField) {
        if (!roleValue || !employeeCodeField) {
            return;
        }
        setEmployeeCodeFeedback(employeeCodeField, "Generating employee code...");
        try {
            const response = await fetch(`/api/v1/auth/admin/users/employee-code/generate/?role=${encodeURIComponent(roleValue)}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                credentials: "same-origin",
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.detail || "Could not generate employee code.");
            }
            employeeCodeField.value = payload.employee_code || "";
            setEmployeeCodeFeedback(employeeCodeField, `Generated automatically for ${payload.role.replace(/_/g, " ")}.`);
            refreshProfileCompletion(employeeCodeField.form);
        } catch (error) {
            setEmployeeCodeFeedback(employeeCodeField, error instanceof Error ? error.message : "Could not generate employee code.");
        }
    }

    function normalizeUsernameCandidate(value) {
        const asciiValue = String(value || "")
            .normalize("NFKD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
        const parts = asciiValue
            .split(/\s+/)
            .map((part) => part.replace(/[^a-z0-9]+/g, ""))
            .filter(Boolean);
        if (parts.length >= 2) {
            return `${parts[0]}.${parts[1]}`.slice(0, 80).replace(/^\.+|\.+$/g, "") || "user";
        }
        if (parts.length === 1) {
            return parts[0].slice(0, 80) || "user";
        }
        const compact = asciiValue.replace(/[^a-z0-9]+/g, "");
        return compact.slice(0, 80) || "user";
    }

    async function generateAvailableUsername(form, options = {}) {
        if (!form || form.id !== "createUserForm") {
            return;
        }
        const fullNameField = form.querySelector('[name="full_name"]');
        const usernameField = form.querySelector('[name="username"]');
        if (!fullNameField || !usernameField) {
            return;
        }
        const isForced = Boolean(options.force);
        const hasUserEdited = usernameField.dataset.userEdited === "true";
        const currentValue = String(usernameField.value || "").trim();
        if (!isForced && hasUserEdited && currentValue) {
            return;
        }
        const fullNameValue = String(fullNameField.value || "").trim();
        if (!fullNameValue) {
            usernameField.value = "";
            usernameField.dataset.autoGenerated = "true";
            setUsernameFeedback(usernameField, "Username will be generated automatically from full name.");
            return;
        }
        const requestId = String(Date.now());
        usernameField.dataset.usernameRequestId = requestId;
        setUsernameFeedback(usernameField, "Checking available username...");
        try {
            const response = await fetch(
                `/api/v1/auth/admin/users/username/generate/?full_name=${encodeURIComponent(fullNameValue)}`,
                {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    credentials: "same-origin",
                }
            );
            const payload = await response.json();
            if (usernameField.dataset.usernameRequestId !== requestId) {
                return;
            }
            if (!response.ok) {
                throw new Error(payload.detail || "Could not generate username.");
            }
            usernameField.value = payload.username || normalizeUsernameCandidate(fullNameValue);
            usernameField.dataset.autoGenerated = "true";
            if (!isForced) {
                usernameField.dataset.userEdited = "false";
            }
            setUsernameFeedback(usernameField, "Available username generated automatically.");
            refreshProfileCompletion(form);
        } catch (error) {
            if (usernameField.dataset.usernameRequestId !== requestId) {
                return;
            }
            usernameField.value = normalizeUsernameCandidate(fullNameValue);
            usernameField.dataset.autoGenerated = "true";
            setUsernameFeedback(usernameField, error instanceof Error ? error.message : "Could not generate username.");
        }
    }

    function refreshProfileCompletion(form) {
        if (!form) {
            return;
        }
        const progressNode = form.querySelector("[data-profile-progress]");
        if (!progressNode) {
            return;
        }
        const trackedFieldNames = [
            "employee_code",
            "username",
            "full_name",
            "type_of_user",
            "role",
            "department",
            "designation",
            "email",
            "phone_number",
            "country",
            "state",
            "district",
            "address",
            "account_status",
        ];
        let completed = 0;
        trackedFieldNames.forEach((fieldName) => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (!field) {
                return;
            }
            const value = "value" in field ? String(field.value || "").trim() : "";
            if (value) {
                completed += 1;
            }
        });
        const total = trackedFieldNames.length;
        const percentage = total ? Math.round((completed / total) * 100) : 0;
        const valueNode = progressNode.querySelector("[data-profile-progress-value]");
        const countNode = progressNode.querySelector("[data-profile-progress-count]");
        const barNode = progressNode.querySelector("[data-profile-progress-bar]");
        if (valueNode) {
            valueNode.textContent = `${percentage}%`;
        }
        if (countNode) {
            countNode.textContent = `${completed} of ${total} fields completed`;
        }
        if (barNode) {
            barNode.style.width = `${percentage}%`;
            barNode.setAttribute("aria-valuenow", String(percentage));
        }
    }

    function initializeCreateUserForm(form) {
        if (!form) {
            return;
        }
        const roleField = form.querySelector('[name="role"]');
        const employeeCodeField = form.querySelector('[name="employee_code"]');
        const usernameField = form.querySelector('[name="username"]');
        if (employeeCodeField) {
            employeeCodeField.readOnly = true;
        }
        if (usernameField) {
            usernameField.dataset.autoGenerated = usernameField.value ? "false" : "true";
            usernameField.dataset.userEdited = "false";
        }
        syncRoleCatalogFields(form);
        void syncLocationFields(form);
        void generateAvailableUsername(form, { force: !usernameField?.value });
        refreshProfileCompletion(form);
        if (roleField && employeeCodeField && roleField.value && !employeeCodeField.value) {
            void generateEmployeeCode(roleField.value, employeeCodeField);
        }
    }

    const CREATE_USER_DRAFT_KEY = "superadmin.createUserFormDraft";

    function getCreateUserDraftStatusNode(form) {
        return form?.querySelector("[data-create-user-draft-status]") || null;
    }

    function setCreateUserDraftStatus(form, message) {
        const statusNode = getCreateUserDraftStatusNode(form);
        if (statusNode) {
            statusNode.textContent = message;
        }
    }

    function updateCreateUserDraftPanel(form) {
        if (!form) {
            return;
        }
        const panel = form.querySelector("[data-create-user-draft-panel]");
        if (!panel) {
            return;
        }
        const hasDraft = Boolean(window.localStorage.getItem(CREATE_USER_DRAFT_KEY));
        panel.hidden = !hasDraft;
        if (hasDraft) {
            setCreateUserDraftStatus(form, "Draft available locally.");
        }
    }

    function clearCreateUserDraft(form) {
        window.localStorage.removeItem(CREATE_USER_DRAFT_KEY);
        updateCreateUserDraftPanel(form);
    }

    function serializeCreateUserDraft(form) {
        const payload = {};
        form.querySelectorAll("input[name], select[name], textarea[name]").forEach((field) => {
            if (!field.name || field.name === "csrfmiddlewaretoken" || field.name === "user_action") {
                return;
            }
            if (field instanceof HTMLInputElement && (field.type === "checkbox" || field.type === "radio")) {
                payload[field.name] = field.checked;
                return;
            }
            payload[field.name] = field.value;
        });
        return payload;
    }

    function saveCreateUserDraft(form) {
        if (!form) {
            return;
        }
        const payload = serializeCreateUserDraft(form);
        window.localStorage.setItem(CREATE_USER_DRAFT_KEY, JSON.stringify(payload));
        updateCreateUserDraftPanel(form);
        setCreateUserDraftStatus(form, "Draft saved locally.");
    }

    async function applyCreateUserDraft(form, payload) {
        if (!form || !payload) {
            return;
        }
        form.querySelectorAll("input[name], select[name], textarea[name]").forEach((field) => {
            if (!field.name || field.name === "csrfmiddlewaretoken" || field.name === "user_action") {
                return;
            }
            const nextValue = payload[field.name];
            if (typeof nextValue === "undefined") {
                return;
            }
            if (field instanceof HTMLInputElement && (field.type === "checkbox" || field.type === "radio")) {
                field.checked = Boolean(nextValue);
                return;
            }
            field.value = nextValue;
        });
        const usernameField = form.querySelector('[name="username"]');
        if (usernameField) {
            usernameField.dataset.userEdited = usernameField.value ? "true" : "false";
            usernameField.dataset.autoGenerated = usernameField.value ? "false" : "true";
        }
        syncRoleCatalogFields(form);
        await syncLocationFields(form, {
            countryValue: payload.country || "",
            stateValue: payload.state || "",
            districtValue: payload.district || "",
        });
        refreshProfileCompletion(form);
    }

    async function loadCreateUserDraft(form) {
        if (!form) {
            return;
        }
        const rawDraft = window.localStorage.getItem(CREATE_USER_DRAFT_KEY);
        if (!rawDraft) {
            updateCreateUserDraftPanel(form);
            return;
        }
        try {
            const payload = JSON.parse(rawDraft);
            await applyCreateUserDraft(form, payload);
            setEmployeeCodeFeedback(form.querySelector('[name="employee_code"]'), "Draft loaded successfully.");
            setCreateUserDraftStatus(form, "Draft loaded locally.");
        } catch (_error) {
            clearCreateUserDraft(form);
            setCreateUserDraftStatus(form, "Draft could not be loaded.");
        }
    }

    async function resetCreateUserForm(form) {
        if (!form) {
            return;
        }
        form.reset();
        const usernameField = form.querySelector('[name="username"]');
        const employeeCodeField = form.querySelector('[name="employee_code"]');
        if (usernameField) {
            usernameField.value = "";
            usernameField.dataset.autoGenerated = "true";
            usernameField.dataset.userEdited = "false";
        }
        if (employeeCodeField) {
            employeeCodeField.value = "";
            employeeCodeField.readOnly = true;
            setEmployeeCodeFeedback(employeeCodeField, "Select a role to generate an employee code.");
        }
        setUsernameFeedback(usernameField, "Username will be generated automatically from full name.");
        syncRoleCatalogFields(form);
        await syncLocationFields(form, {
            countryValue: "",
            stateValue: "",
            districtValue: "",
        });
        setCreateUserDraftStatus(form, "Draft available locally.");
        refreshProfileCompletion(form);
        updateCreateUserDraftPanel(form);
    }

    function initializeEditUserForm(form) {
        if (!form) {
            return;
        }
        syncRoleCatalogFields(form);
        void syncLocationFields(form);
        refreshProfileCompletion(form);
    }

    const createUserModalNode = document.getElementById("createUserModal");
    const createUserForm = document.getElementById("createUserForm");
    if (createUserForm) {
        const createEmployeeCodeField = createUserForm.querySelector('[name="employee_code"]');
        if (createEmployeeCodeField) {
            createEmployeeCodeField.readOnly = true;
        }
        initializeCreateUserForm(createUserForm);
        updateCreateUserDraftPanel(createUserForm);
        const saveDraftButton = createUserForm.querySelector("[data-create-user-draft-save]");
        const loadDraftButton = createUserForm.querySelector("[data-create-user-draft-load]");
        const discardDraftButton = createUserForm.querySelector("[data-create-user-draft-discard]");
        if (saveDraftButton) {
            saveDraftButton.addEventListener("click", () => {
                saveCreateUserDraft(createUserForm);
            });
        }
        if (loadDraftButton) {
            loadDraftButton.addEventListener("click", () => {
                void loadCreateUserDraft(createUserForm);
            });
        }
        if (discardDraftButton) {
            discardDraftButton.addEventListener("click", () => {
                clearCreateUserDraft(createUserForm);
                setCreateUserDraftStatus(createUserForm, "Draft removed.");
            });
        }
        createUserForm.addEventListener("submit", () => {
            clearCreateUserDraft(createUserForm);
        });
    }
    if (createUserModalNode && createUserForm) {
        createUserModalNode.addEventListener("show.bs.modal", (event) => {
            if (createUserModalNode.dataset.openUserCreateModal === "true" && !event.relatedTarget) {
                updateCreateUserDraftPanel(createUserForm);
                refreshProfileCompletion(createUserForm);
                return;
            }
            void resetCreateUserForm(createUserForm);
        });
    }
    if (
        createUserModalNode &&
        createUserModalNode.dataset.openUserCreateModal === "true" &&
        typeof bootstrap !== "undefined" &&
        bootstrap.Modal
    ) {
        const createUserModal = new bootstrap.Modal(createUserModalNode);
        createUserModal.show();
    }

    const viewUserModalNode = document.getElementById("viewUserModal");
    if (viewUserModalNode) {
        viewUserModalNode.addEventListener("show.bs.modal", (event) => {
            const trigger = event.relatedTarget;
            const payload = readPayload(trigger?.dataset.userViewTrigger);
            if (!payload) {
                return;
            }
            viewUserModalNode.querySelectorAll("[data-view-field]").forEach((node) => {
                const value = payload[node.dataset.viewField];
                node.textContent = value && String(value).trim() ? value : "-";
            });
        });
    }

    const editUserModalNode = document.getElementById("editUserModal");
    const editUserForm = document.getElementById("editUserForm");
    if (editUserModalNode && editUserForm) {
        initializeEditUserForm(editUserForm);
        editUserModalNode.addEventListener("show.bs.modal", (event) => {
            const trigger = event.relatedTarget;
            const userId = trigger?.dataset.userEditTrigger;
            const payload = readPayload(userId);
            if (!payload) {
                return;
            }
            assignLookupPayloadToForm(editUserForm, {
                ...payload,
                email_verified: payload.email_verified_bool,
                account_locked: payload.account_locked_bool,
                mfa_enabled: payload.mfa_enabled_bool,
            });
            setUserIdFeedback(editUserForm.querySelector("[data-user-id-lookup]"), "Enter a User ID and press Enter to fetch an existing user.");
            setEmployeeCodeFeedback(editUserForm.querySelector('[name="employee_code"]'), "Enter a full employee code or only the numeric part, then press Enter.");
            refreshProfileCompletion(editUserForm);
        });

        const editUserIdLookupField = editUserForm.querySelector("[data-user-id-lookup]");
        if (editUserIdLookupField) {
            editUserIdLookupField.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") {
                    return;
                }
                event.preventDefault();
                const userId = editUserIdLookupField.value.trim();
                if (!userId) {
                    return;
                }
                void lookupEditUser(editUserForm, { user_id: userId }, editUserIdLookupField, setUserIdFeedback);
            });
        }

        const editEmployeeCodeField = editUserForm.querySelector('[name="employee_code"]');
        if (editEmployeeCodeField) {
            editEmployeeCodeField.readOnly = false;
            editEmployeeCodeField.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") {
                    return;
                }
                event.preventDefault();
                const employeeCode = editEmployeeCodeField.value.trim().toUpperCase();
                if (!employeeCode) {
                    return;
                }
                void lookupEditUser(editUserForm, { employee_code: employeeCode }, editEmployeeCodeField, setEmployeeCodeFeedback);
            });
        }

        if (
            editUserModalNode.dataset.openUserEditModal === "true" &&
            typeof bootstrap !== "undefined" &&
            bootstrap.Modal
        ) {
            const editUserModal = new bootstrap.Modal(editUserModalNode);
            editUserModal.show();
        }
    }

    document.addEventListener("change", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement)) {
            return;
        }
        const form = target.form;
        if (!form || (form.id !== "createUserForm" && form.id !== "editUserForm")) {
            return;
        }
        if (target.name === "role") {
            syncRoleCatalogFields(form);
            if (form.id === "createUserForm") {
                const employeeCodeField = form.querySelector('[name="employee_code"]');
                if (employeeCodeField) {
                    employeeCodeField.value = "";
                    void generateEmployeeCode(target.value, employeeCodeField);
                }
            }
            refreshProfileCompletion(form);
            return;
        }
        if (target.name === "country") {
            void syncLocationFields(form, {
                countryValue: target.value,
                stateValue: "",
                districtValue: "",
            });
            refreshProfileCompletion(form);
            return;
        }
        if (target.name === "state") {
            const countryField = form.querySelector('[name="country"]');
            void syncLocationFields(form, {
                countryValue: countryField ? countryField.value : "",
                stateValue: target.value,
                districtValue: "",
            });
            refreshProfileCompletion(form);
            return;
        }
        refreshProfileCompletion(form);
    });

    document.addEventListener("input", (event) => {
        const target = event.target;
        if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement)) {
            return;
        }
        const form = target.form;
        if (!form || (form.id !== "createUserForm" && form.id !== "editUserForm")) {
            return;
        }
        if (form.id === "createUserForm" && target.name === "full_name") {
            const usernameField = form.querySelector('[name="username"]');
            if (usernameField?.dataset.usernameDebounceId) {
                window.clearTimeout(Number(usernameField.dataset.usernameDebounceId));
            }
            const timeoutId = window.setTimeout(() => {
                void generateAvailableUsername(form);
            }, 250);
            if (usernameField) {
                usernameField.dataset.usernameDebounceId = String(timeoutId);
            }
        }
        if (form.id === "createUserForm" && target.name === "username") {
            target.dataset.userEdited = "true";
            target.dataset.autoGenerated = "false";
            setUsernameFeedback(target, "Manual username entered.");
        }
        refreshProfileCompletion(form);
    });

    const deleteUserModalNode = document.getElementById("deleteUserModal");
    if (deleteUserModalNode) {
        deleteUserModalNode.addEventListener("show.bs.modal", (event) => {
            const trigger = event.relatedTarget;
            const userId = trigger?.dataset.userDeleteTrigger || "";
            const userName = trigger?.dataset.userDeleteName || "-";
            const hiddenIdField = deleteUserModalNode.querySelector("[data-delete-hidden-id]");
            const nameNode = deleteUserModalNode.querySelector("[data-delete-user-name]");
            if (hiddenIdField) {
                hiddenIdField.value = userId;
            }
            if (nameNode) {
                nameNode.textContent = userName;
            }
        });
    }

    const chartNode = document.getElementById("superadmin-chart-data");
    if (!chartNode || typeof Chart === "undefined") {
        return;
    }

    const chartData = JSON.parse(chartNode.textContent);
    const getThemeColors = () => {
        const computed = getComputedStyle(body);
        return {
            text: computed.getPropertyValue("--sa-text").trim() || "#173246",
            softText: computed.getPropertyValue("--sa-text-soft").trim() || "#687b88",
            blue: computed.getPropertyValue("--sa-blue").trim() || "#2f80ed",
            teal: computed.getPropertyValue("--sa-teal").trim() || "#18a0a6",
            green: computed.getPropertyValue("--sa-green").trim() || "#1f9c62",
            orange: computed.getPropertyValue("--sa-orange").trim() || "#f18a4f",
            border: computed.getPropertyValue("--sa-border").trim() || "rgba(20,48,66,0.09)",
        };
    };

    const chartDefaults = (colors) => ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: colors.softText,
                    usePointStyle: true,
                    boxWidth: 10,
                    boxHeight: 10,
                    font: { family: "Inter, Segoe UI, sans-serif", size: 12, weight: "600" },
                    padding: 16,
                },
            },
            tooltip: {
                backgroundColor: body.dataset.theme === "dark" ? "rgba(17, 28, 40, 0.94)" : "rgba(19, 37, 51, 0.92)",
                titleColor: "#fff",
                bodyColor: "rgba(255,255,255,.88)",
                borderWidth: 0,
                padding: 12,
                displayColors: true,
            },
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: {
                    color: colors.softText,
                    font: { family: "Inter, Segoe UI, sans-serif", size: 11, weight: "600" },
                },
                border: { display: false },
            },
            y: {
                beginAtZero: true,
                grid: { color: colors.border },
                ticks: {
                    color: colors.softText,
                    font: { family: "Inter, Segoe UI, sans-serif", size: 11, weight: "600" },
                },
                border: { display: false },
            },
        },
    });

    const chartInstances = [];
    const animateCounters = () => {
        document.querySelectorAll("[data-counter-target]").forEach((node) => {
            const target = Number(node.dataset.counterTarget || "0");
            if (!Number.isFinite(target)) {
                return;
            }
            const prefix = node.textContent.trim().startsWith("₹") ? "₹" : "";
            const duration = 900;
            const start = performance.now();
            const tick = (now) => {
                const progress = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const value = Math.round(target * eased);
                node.textContent = `${prefix}${value}`;
                if (progress < 1) {
                    requestAnimationFrame(tick);
                }
            };
            requestAnimationFrame(tick);
        });
    };

    const destroyCharts = () => {
        while (chartInstances.length) {
            const instance = chartInstances.pop();
            instance.destroy();
        }
    };

    const buildCharts = () => {
        destroyCharts();
        const colors = getThemeColors();

        const revenueCtx = document.getElementById("revenueTrendChart");
        const volumeCtx = document.getElementById("volumeComparisonChart");
        const categoryCtx = document.getElementById("categoryDistributionChart");
        const patientCtx = document.getElementById("patientGrowthChart");
        if (!revenueCtx || !volumeCtx || !categoryCtx || !patientCtx) {
            return;
        }

        const revenueGradient = revenueCtx.getContext("2d").createLinearGradient(0, 0, 0, 320);
        revenueGradient.addColorStop(0, "rgba(47, 128, 237, 0.34)");
        revenueGradient.addColorStop(1, "rgba(47, 128, 237, 0.03)");

        chartInstances.push(new Chart(revenueCtx, {
            type: "line",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Revenue",
                        data: chartData.revenue,
                        borderColor: colors.blue,
                        backgroundColor: revenueGradient,
                        fill: true,
                        tension: 0.38,
                        borderWidth: 2.2,
                        pointRadius: 0,
                        pointHoverRadius: 5,
                    },
                    {
                        label: "Patient growth",
                        data: chartData.patients,
                        borderColor: colors.teal,
                        tension: 0.38,
                        borderWidth: 2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                    },
                ],
            },
            options: chartDefaults(colors),
        }));

        chartInstances.push(new Chart(volumeCtx, {
            type: "bar",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "Orders",
                        data: chartData.orders,
                        backgroundColor: "rgba(47, 128, 237, 0.78)",
                        borderRadius: 10,
                        borderSkipped: false,
                    },
                    {
                        label: "Prescriptions",
                        data: chartData.prescriptions,
                        backgroundColor: "rgba(24, 160, 166, 0.72)",
                        borderRadius: 10,
                        borderSkipped: false,
                    },
                ],
            },
            options: {
                ...chartDefaults(colors),
                scales: {
                    ...chartDefaults(colors).scales,
                    x: { ...chartDefaults(colors).scales.x, stacked: false },
                    y: { ...chartDefaults(colors).scales.y, stacked: false },
                },
            },
        }));

        chartInstances.push(new Chart(categoryCtx, {
            type: "doughnut",
            data: {
                labels: chartData.categories.labels,
                datasets: [
                    {
                        data: chartData.categories.values,
                        borderWidth: 0,
                        hoverOffset: 4,
                        backgroundColor: [
                            "rgba(47, 128, 237, 0.92)",
                            "rgba(24, 160, 166, 0.88)",
                            "rgba(71, 201, 133, 0.84)",
                            "rgba(241, 138, 79, 0.84)",
                            "rgba(126, 145, 255, 0.84)",
                        ],
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                plugins: chartDefaults(colors).plugins,
            },
        }));

        const patientGradient = patientCtx.getContext("2d").createLinearGradient(0, 0, 0, 250);
        patientGradient.addColorStop(0, "rgba(24, 160, 166, 0.34)");
        patientGradient.addColorStop(1, "rgba(24, 160, 166, 0.03)");

        chartInstances.push(new Chart(patientCtx, {
            type: "line",
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: "New patients",
                        data: chartData.patients,
                        borderColor: colors.teal,
                        backgroundColor: patientGradient,
                        fill: true,
                        tension: 0.42,
                        borderWidth: 2.2,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                    },
                ],
            },
            options: chartDefaults(colors),
        }));
    };

    buildCharts();
    animateCounters();
    window.addEventListener("rakeshmed-theme-changed", buildCharts);
})();

(() => {
    const roleField = document.getElementById("id_role");
    if (!roleField) {
        return;
    }

    const groups = document.querySelectorAll("[data-role-group]");

    function syncRoleFields() {
        const selectedRole = roleField.value;

        groups.forEach((group) => {
            const groupRole = group.dataset.roleGroup;
            const shouldShow = selectedRole === groupRole;
            group.classList.toggle("d-none", !shouldShow);

            group.querySelectorAll("input, select, textarea").forEach((input) => {
                if (!shouldShow && input.type !== "hidden") {
                    input.value = "";
                }
            });
        });
    }

    roleField.addEventListener("change", syncRoleFields);
    syncRoleFields();
})();

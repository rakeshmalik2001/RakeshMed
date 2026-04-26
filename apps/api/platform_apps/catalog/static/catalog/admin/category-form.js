(function () {
  function filterCategoryOptions() {
    var navbarSelect = document.getElementById("id_navbar_category");
    var categorySelect = document.getElementById("id_section_category");

    if (!navbarSelect || !categorySelect) {
      return;
    }

    var selectedNavbarId = navbarSelect.value;
    var currentValue = categorySelect.value;
    var hasVisibleCurrentOption = false;

    Array.prototype.forEach.call(categorySelect.options, function (option) {
      if (!option.value) {
        option.hidden = false;
        option.disabled = false;
        return;
      }

      var optionNavbarId = option.getAttribute("data-navbar-id");
      var shouldShow = !selectedNavbarId || optionNavbarId === selectedNavbarId;

      option.hidden = !shouldShow;
      option.disabled = !shouldShow;

      if (shouldShow && option.value === currentValue) {
        hasVisibleCurrentOption = true;
      }
    });

    if (currentValue && !hasVisibleCurrentOption) {
      categorySelect.value = "";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var navbarSelect = document.getElementById("id_navbar_category");
    if (!navbarSelect) {
      return;
    }

    filterCategoryOptions();
    navbarSelect.addEventListener("change", filterCategoryOptions);
  });
})();

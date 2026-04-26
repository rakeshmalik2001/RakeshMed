document.addEventListener("DOMContentLoaded", () => {
  const links = Array.from(document.querySelectorAll("[data-section-nav]"));

  if (!links.length || !("IntersectionObserver" in window)) {
    return;
  }

  const sectionMap = new Map();

  links.forEach((link) => {
    const href = link.getAttribute("href") || "";
    if (!href.startsWith("#")) {
      return;
    }

    const section = document.querySelector(href);
    if (section) {
      sectionMap.set(section, link);
    }
  });

  if (!sectionMap.size) {
    return;
  }

  const setActiveLink = (activeSection) => {
    links.forEach((link) => link.classList.remove("active"));
    const activeLink = sectionMap.get(activeSection);
    if (activeLink) {
      activeLink.classList.add("active");
    }
  };

  const observer = new IntersectionObserver(
    (entries) => {
      const visibleSections = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio);

      if (visibleSections.length) {
        setActiveLink(visibleSections[0].target);
      }
    },
    {
      rootMargin: "-20% 0px -55% 0px",
      threshold: [0.2, 0.4, 0.6],
    }
  );

  sectionMap.forEach((_, section) => observer.observe(section));
});

"use strict";

const applyFilter = (chips, releases, filter) => {
    for (const chip of chips) {
        const active = chip.dataset.filter === filter;
        chip.classList.toggle("kd-chip-active", active);
        chip.setAttribute("aria-pressed", String(active));
    }
    for (const release of releases) {
        const entries = [...release.querySelectorAll("[data-category]")];
        for (const entry of entries) {
            entry.hidden = filter !== "all" && entry.dataset.category !== filter;
        }
        release.hidden = entries.every((entry) => entry.hidden);
    }
};

(() => {
    const chips = [...document.querySelectorAll("[data-filter]")];
    const releases = [...document.querySelectorAll("[data-release]")];
    for (const chip of chips) {
        chip.addEventListener("click", () => applyFilter(chips, releases, chip.dataset.filter));
    }
})();
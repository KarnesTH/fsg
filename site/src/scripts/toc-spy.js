"use strict";

const markActive = (links, id) => {
    for (const link of links) {
        link.classList.toggle("kd-active", link.hash === `#${id}`);
    }
};

(() => {
    const links = [...document.querySelectorAll(".kd-toc a")];
    const headings = links.map((link) => document.getElementById(link.hash.slice(1))).filter(Boolean);
    if (headings.length === 0) return;

    const observer = new IntersectionObserver(
        (entries) => {
            const visible = entries.filter((entry) => entry.isIntersecting);
            if (visible.length > 0) markActive(links, visible[0].target.id);
        },
        { rootMargin: "0px 0px -70% 0px" },
    );
    for (const heading of headings) observer.observe(heading);
    markActive(links, headings[0].id);
})();
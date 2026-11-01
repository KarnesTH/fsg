"use strict";

const markActive = (links, id) => {
    for (const link of links) {
        link.classList.toggle("kd-active", link.hash === `#${id}`);
    }
};

const currentHeading = (headings) => {
    const bottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
    if (bottom) return headings[headings.length - 1];
    const line = window.innerHeight * 0.3;
    return headings.findLast((heading) => heading.getBoundingClientRect().top <= line) ?? headings[0];
};

(() => {
    const links = [...document.querySelectorAll(".kd-toc a")];
    const headings = links.map((link) => document.getElementById(link.hash.slice(1))).filter(Boolean);
    if (headings.length === 0) return;

    let pending = false;
    const update = () => {
        pending = false;
        markActive(links, currentHeading(headings).id);
    };
    const schedule = () => {
        if (pending) return;
        pending = true;
        requestAnimationFrame(update);
    };
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    update();
})();
"use strict";

const codeText = (block) => {
    const source = block.querySelector(".kd-tab:checked + .kd-tab-content pre") ?? block.querySelector("pre, .kd-code-lines");
    const lines = source.innerText.split("\n");
    const commands = lines.filter((line) => line.startsWith("$ "));
    return commands.length > 0 ? commands.map((line) => line.slice(2)).join("\n") : lines.join("\n");
};

const copyCode = (button) => {
    navigator.clipboard.writeText(codeText(button.closest(".kd-code")));
};

(() => {
    document.addEventListener("click", (event) => {
        const button = event.target.closest(".kd-code-copy");
        if (button) copyCode(button);
    });
})();
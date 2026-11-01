import source from "../../../CHANGELOG.md?raw";

export type Category = "Added" | "Changed" | "Fixed" | "Security";

export interface Entry {
    category: Category;
    html: string;
}

export interface Release {
    version: string;
    date: string;
    entries: Entry[];
}

const escape = (text: string) => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const inline = (text: string) => escape(text).replace(/`([^`]+)`/g, "<code>$1</code>");

const parse = (markdown: string): Release[] =>
    markdown
        .split(/^## /m)
        .slice(1)
        .flatMap((block) => {
            const [head, ...lines] = block.trim().split("\n");
            const match = head.match(/^\[(.+?)\] - (\d{4}-\d{2}-\d{2})/);
            if (!match) return [];
            const entries: Entry[] = [];
            let category: Category | null = null;
            for (const line of lines) {
                if (line.startsWith("### ")) category = line.slice(4).trim() as Category;
                else if (line.startsWith("- ") && category) entries.push({ category, html: inline(line.slice(2).trim()) });
            }
            return [{ version: match[1], date: match[2], entries }];
        });

export const releases = parse(source);

export const latest = releases[0];
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

interface Strings {
    placeholder: string;
    pages: string;
    sections: string;
    empty: string;
    select: string;
    open: string;
    close: string;
}

interface Props {
    strings: Strings;
    base: string;
}

interface Hit {
    group: "pages" | "sections";
    url: string;
    title: string;
    detail: string;
}

interface PagefindResult {
    url: string;
    excerpt: string;
    meta: { title?: string };
    sub_results: { title: string; url: string; excerpt: string }[];
}

interface Pagefind {
    options: (options: { baseUrl?: string }) => Promise<void>;
    debouncedSearch: (term: string) => Promise<{ results: { data: () => Promise<PagefindResult> }[] } | null>;
}

const toHits = (results: PagefindResult[]): Hit[] => [
    ...results.map((result): Hit => ({ group: "pages", url: result.url, title: result.meta.title ?? result.url, detail: result.excerpt })),
    ...results.flatMap((result) =>
        result.sub_results
            .filter((section) => section.url !== result.url)
            .map((section): Hit => ({ group: "sections", url: section.url, title: section.title, detail: result.meta.title ?? "" })),
    ),
];

const SearchDialog = ({ strings, base }: Props) => {
    const dialog = useRef<HTMLDialogElement>(null);
    const input = useRef<HTMLInputElement>(null);
    const pagefind = useRef<Pagefind | null>(null);
    const [term, setTerm] = useState("");
    const [hits, setHits] = useState<Hit[]>([]);
    const [active, setActive] = useState(0);

    const open = () => {
        dialog.current?.showModal();
        input.current?.focus();
    };

    useEffect(() => {
        const onClick = (event: MouseEvent) => {
            if ((event.target as HTMLElement).closest("[data-search-open]")) open();
        };
        const onKey = (event: globalThis.KeyboardEvent) => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                if (dialog.current?.open) dialog.current.close();
                else open();
            }
        };
        document.addEventListener("click", onClick);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("click", onClick);
            document.removeEventListener("keydown", onKey);
        };
    }, []);

    useEffect(() => {
        if (term.trim() === "") {
            setHits([]);
            return;
        }
        const run = async () => {
            if (!pagefind.current) {
                const bundle = `${base}/pagefind/pagefind.js`;
                pagefind.current = (await import(/* @vite-ignore */ bundle)) as Pagefind;
                await pagefind.current.options({ baseUrl: `${base}/` });
            }
            const search = await pagefind.current.debouncedSearch(term);
            if (!search) return;
            const results = await Promise.all(search.results.slice(0, 5).map((result) => result.data()));
            setHits(toHits(results));
            setActive(0);
        };
        run();
    }, [term, base]);

    const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            setActive((index) => Math.min(index + 1, hits.length - 1));
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            setActive((index) => Math.max(index - 1, 0));
        } else if (event.key === "Enter" && hits[active]) {
            window.location.href = hits[active].url;
        }
    };

    const groups = (["pages", "sections"] as const).filter((group) => hits.some((hit) => hit.group === group));

    return (
        <dialog ref={dialog} className="kd-modal items-start pt-24" onClick={(event) => event.target === dialog.current && dialog.current.close()}>
            <div className="kd-command" role="search">
                <label className="kd-command-input">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 10a7 7 0 1 0 14 0a7 7 0 1 0 -14 0" /><path d="M21 21l-6 -6" /></svg>
                    <input ref={input} type="search" placeholder={strings.placeholder} aria-label={strings.placeholder} value={term} onChange={(event) => setTerm(event.target.value)} onKeyDown={onKeyDown} />
                    <kbd className="kd-kbd kd-kbd-sm">Esc</kbd>
                </label>
                <ul className="kd-command-list">
                    {term.trim() !== "" && hits.length === 0 && <li className="kd-command-group">{strings.empty}</li>}
                    {groups.map((group) => [
                        <li key={group} className="kd-command-group">{strings[group]}</li>,
                        ...hits.map((hit, index) => hit.group !== group ? null : (
                            <li key={`${group}-${hit.url}`}>
                                <a className={`kd-command-item${index === active ? " kd-active" : ""}`} href={hit.url} onMouseEnter={() => setActive(index)}>
                                    {group === "pages"
                                        ? <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M14 3v4a1 1 0 0 0 1 1h4" /><path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2" /><path d="M9 9l1 0" /><path d="M9 13l6 0" /><path d="M9 17l6 0" /></svg>
                                        : <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 9l14 0" /><path d="M5 15l14 0" /><path d="M11 4l-4 16" /><path d="M17 4l-4 16" /></svg>}
                                    <span>{hit.title}<small className="line-clamp-1 [&_mark]:bg-transparent [&_mark]:text-kd-primary-hover" dangerouslySetInnerHTML={{ __html: hit.detail }} /></span>
                                </a>
                            </li>
                        )),
                    ])}
                </ul>
                <div className="kd-command-footer">
                    <span><kbd className="kd-kbd kd-kbd-sm">↑</kbd><kbd className="kd-kbd kd-kbd-sm">↓</kbd>{strings.select}</span>
                    <span><kbd className="kd-kbd kd-kbd-sm">↵</kbd>{strings.open}</span>
                    <span><kbd className="kd-kbd kd-kbd-sm">Esc</kbd>{strings.close}</span>
                </div>
            </div>
        </dialog>
    );
};

export default SearchDialog;
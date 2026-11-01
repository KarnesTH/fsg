import { getCollection, type CollectionEntry } from "astro:content";
import type { Locale } from "../i18n";

export type Doc = CollectionEntry<"docs">;

export const sections = ["getting-started", "guides"] as const;

export type Section = (typeof sections)[number];

export const slugOf = (doc: Doc) => doc.id.split("/")[1];

export const docsFor = async (locale: Locale): Promise<Doc[]> => {
    const all: Doc[] = await getCollection("docs");
    return all
        .filter((doc: Doc) => doc.id.startsWith("en/"))
        .map((english: Doc) => all.find((doc: Doc) => doc.id === `${locale}/${slugOf(english)}`) ?? english)
        .sort((a: Doc, b: Doc) => sections.indexOf(a.data.section) - sections.indexOf(b.data.section) || a.data.order - b.data.order);
};
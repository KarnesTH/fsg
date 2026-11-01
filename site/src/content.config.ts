import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const docs = defineCollection({
    loader: glob({ pattern: "**/*.mdx", base: "./src/content/docs" }),
    schema: z.object({
        title: z.string(),
        description: z.string(),
        section: z.enum(["getting-started", "guides"]),
        order: z.number(),
        updated: z.coerce.date(),
    }),
});

export const collections = { docs };
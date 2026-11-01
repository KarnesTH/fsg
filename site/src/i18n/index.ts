import de from "./de.json";
import en from "./en.json";

export const strings = { en, de };

export type Locale = keyof typeof strings;
/** Einfacher i18n-Hook – lädt de/en aus locales/*.json */

import de from "../locales/de.json";
import en from "../locales/en.json";

const locales: Record<string, Record<string, unknown>> = {
  de: de as Record<string, unknown>,
  en: en as Record<string, unknown>,
};

function getNested(obj: unknown, path: string): string | undefined {
  const parts = path.split(".");
  let current: unknown = obj;
  for (const p of parts) {
    if (current == null || typeof current !== "object") return undefined;
    current = (current as Record<string, unknown>)[p];
  }
  return typeof current === "string" ? current : undefined;
}

export function useI18n(lang: "de" | "en" = "de") {
  const t = (key: string): string => {
    const val = getNested(locales[lang], key);
    return val ?? key;
  };
  return { t, lang };
}

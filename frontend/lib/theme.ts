import type { ThemeKey } from "@/lib/types";

export const DEFAULT_THEME: ThemeKey = "black_white_gold";

export const themeOptions: Array<{ value: ThemeKey; label: string; description: string; swatches: string[] }> = [
  {
    value: "black_white_gold",
    label: "Black, white and gold",
    description: "Crisp, focused, and classic.",
    swatches: ["#111111", "#ffffff", "#f5c542"]
  },
  {
    value: "royal_blue_white_gold",
    label: "Royal blue, white and gold",
    description: "Confident and academic.",
    swatches: ["#1d4ed8", "#ffffff", "#f5c542"]
  },
  {
    value: "green_white_gold",
    label: "Green, white and gold",
    description: "Calm, fresh, and steady.",
    swatches: ["#15803d", "#ffffff", "#f5c542"]
  },
  {
    value: "red_white_gold",
    label: "Red, white and gold",
    description: "Bold and energetic.",
    swatches: ["#b91c1c", "#ffffff", "#f5c542"]
  },
  {
    value: "purple_white_gold",
    label: "Purple, white and gold",
    description: "Creative and polished.",
    swatches: ["#7e22ce", "#ffffff", "#f5c542"]
  }
];

export function isThemeKey(value: string): value is ThemeKey {
  return themeOptions.some((theme) => theme.value === value);
}

export function applyTheme(theme: ThemeKey): void {
  document.documentElement.dataset.theme = theme;
  window.localStorage.setItem("abbot-study-theme", theme);
  window.localStorage.removeItem("studyflow-theme");
}

export function getStoredTheme(): ThemeKey {
  if (typeof window === "undefined") {
    return DEFAULT_THEME;
  }

  const storedTheme = window.localStorage.getItem("abbot-study-theme") ?? window.localStorage.getItem("studyflow-theme");
  return storedTheme && isThemeKey(storedTheme) ? storedTheme : DEFAULT_THEME;
}

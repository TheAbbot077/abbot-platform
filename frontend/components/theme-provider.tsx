"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";

import { getUserSettings } from "@/lib/api";
import { applyTheme, getStoredTheme } from "@/lib/theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    applyTheme(getStoredTheme());

    async function loadSavedTheme() {
      try {
        const settings = await getUserSettings();
        applyTheme(settings.theme);
      } catch {
        // Logged-out users keep the default or locally cached theme.
      }
    }

    void loadSavedTheme();
  }, []);

  return children;
}

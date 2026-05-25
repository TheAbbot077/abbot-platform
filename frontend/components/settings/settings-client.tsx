"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Loader2 } from "lucide-react";

import { getCurrentUser, getUserSettings, logout, updateUserSettings } from "@/lib/api";
import type { ThemeKey, User } from "@/lib/types";
import { applyTheme, DEFAULT_THEME, themeOptions } from "@/lib/theme";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SettingsClient() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [selectedTheme, setSelectedTheme] = useState<ThemeKey>(DEFAULT_THEME);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSettings() {
      try {
        const [userResponse, settingsResponse] = await Promise.all([
          getCurrentUser(),
          getUserSettings()
        ]);
        if (!isMounted) {
          return;
        }
        setUser(userResponse.user);
        setSelectedTheme(settingsResponse.theme);
        applyTheme(settingsResponse.theme);
      } catch (caught) {
        if (isMounted) {
          setError(caught instanceof Error ? caught.message : "Could not load settings.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadSettings();

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleThemeChange(theme: ThemeKey) {
    setSelectedTheme(theme);
    applyTheme(theme);
    setIsSaving(true);
    setMessage(null);
    setError(null);

    try {
      const settings = await updateUserSettings(theme);
      setSelectedTheme(settings.theme);
      applyTheme(settings.theme);
      setMessage("Theme saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save theme.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <p className="font-medium">{user?.username ?? "Loading account..."}</p>
            <p className="text-muted-foreground">{user?.email || "No email set"}</p>
          </div>
          {isLoading ? (
            <p className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading settings...
            </p>
          ) : null}
          <Button type="button" variant="outline" className="w-full sm:w-auto" onClick={handleLogout}>Logout from this device</Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Theme</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Choose the color palette used across Abbot Study. Your choice is saved to your account.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {themeOptions.map((theme) => {
              const isSelected = selectedTheme === theme.value;
              return (
                <button
                  key={theme.value}
                  type="button"
                  className={cn(
                    "min-h-28 rounded-2xl border bg-card p-4 text-left transition-colors hover:border-primary",
                    isSelected ? "border-primary ring-2 ring-ring" : "border-border"
                  )}
                  onClick={() => handleThemeChange(theme.value)}
                  disabled={isSaving}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{theme.label}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{theme.description}</p>
                    </div>
                    {isSelected ? <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden="true" /> : null}
                  </div>
                  <div className="mt-4 flex gap-2">
                    {theme.swatches.map((swatch) => (
                      <span
                        key={swatch}
                        className="h-6 w-6 rounded-md border"
                        style={{ backgroundColor: swatch }}
                        aria-hidden="true"
                      />
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
          {isSaving ? <p className="text-sm text-muted-foreground">Saving theme...</p> : null}
          {message ? <p className="text-sm font-medium text-primary">{message}</p> : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>
    </div>
  );
}

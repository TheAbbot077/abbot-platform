"use client";

import { useEffect, useState } from "react";

import { clearClientAuthState, getCurrentUser, logout } from "@/lib/api";

export function PublicSessionInvalidator() {
  const [isInvalidating, setIsInvalidating] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function invalidateIfAuthenticated() {
      try {
        const response = await getCurrentUser();
        if (!response.user) {
          clearClientAuthState();
          return;
        }

        if (isMounted) {
          setIsInvalidating(true);
        }
        await logout();
      } catch {
        clearClientAuthState();
      } finally {
        if (isMounted) {
          setIsInvalidating(false);
        }
      }
    }

    void invalidateIfAuthenticated();

    function handlePageShow() {
      void invalidateIfAuthenticated();
    }

    window.addEventListener("pageshow", handlePageShow);

    return () => {
      isMounted = false;
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, []);

  if (!isInvalidating) {
    return null;
  }

  return (
    <div className="fixed inset-x-4 top-4 z-50 rounded-2xl border bg-card p-3 text-sm text-muted-foreground shadow-sm sm:left-1/2 sm:right-auto sm:w-96 sm:-translate-x-1/2">
      Ending the previous study session...
    </div>
  );
}

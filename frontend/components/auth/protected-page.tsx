"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { clearClientAuthState, getCurrentUser } from "@/lib/api";

export function ProtectedPage({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [message, setMessage] = useState("Checking your session...");

  useEffect(() => {
    let isMounted = true;

    async function checkAuth(showCheckingState = false) {
      if (showCheckingState && isMounted) {
        setIsAuthenticated(false);
        setIsChecking(true);
        setMessage("Checking your session...");
      }

      try {
        const response = await getCurrentUser();
        if (isMounted) {
          setIsAuthenticated(Boolean(response.user));
        }
      } catch (caught) {
        if (isMounted) {
          clearClientAuthState();
          setMessage(caught instanceof Error ? caught.message : "Please log in again to continue.");
        }
        router.replace("/login");
      } finally {
        if (isMounted) {
          setIsChecking(false);
        }
      }
    }

    void checkAuth();

    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) {
        void checkAuth(true);
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        void checkAuth(true);
      }
    }

    window.addEventListener("pageshow", handlePageShow);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      isMounted = false;
      window.removeEventListener("pageshow", handlePageShow);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [router]);

  if (isChecking || !isAuthenticated) {
    return <div className="rounded-lg border bg-card p-8 text-sm text-muted-foreground">{message}</div>;
  }

  return children;
}

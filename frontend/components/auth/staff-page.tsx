"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";

import { clearClientAuthState, getCurrentUser } from "@/lib/api";

export function StaffPage({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"checking" | "allowed" | "blocked">("checking");
  const [message, setMessage] = useState("Checking admin access...");

  useEffect(() => {
    let isMounted = true;

    async function checkStaffAccess() {
      try {
        const response = await getCurrentUser();
        if (!isMounted) {
          return;
        }

        if (response.user?.is_staff) {
          setStatus("allowed");
        } else {
          setStatus("blocked");
          setMessage("Abbot Command Center is available only to staff administrators.");
        }
      } catch (caught) {
        if (isMounted) {
          clearClientAuthState();
          setStatus("blocked");
          setMessage(caught instanceof Error ? caught.message : "Please log in again to continue.");
        }
      }
    }

    void checkStaffAccess();

    return () => {
      isMounted = false;
    };
  }, []);

  if (status === "allowed") {
    return children;
  }

  return (
    <div className="rounded-2xl border bg-card p-8 shadow-sm">
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-1 h-5 w-5 text-primary" aria-hidden="true" />
        <div>
          <h2 className="text-lg font-semibold">{status === "checking" ? "Checking access" : "Admin access required"}</h2>
          <p className="mt-2 text-sm text-muted-foreground">{message}</p>
          {status === "blocked" ? (
            <Link className="mt-4 inline-flex text-sm font-medium text-primary hover:underline" href="/dashboard">
              Return to student dashboard
            </Link>
          ) : null}
        </div>
      </div>
    </div>
  );
}

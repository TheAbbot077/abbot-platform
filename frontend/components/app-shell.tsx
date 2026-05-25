"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AppHeader } from "@/components/app-header";
import { StudyToolkit } from "@/components/study-toolkit";

const publicRoutes = new Set(["/", "/login", "/signup"]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isPublicRoute = publicRoutes.has(pathname);

  if (isPublicRoute) {
    return children;
  }

  return (
    <>
      <AppHeader />
      <div className="app-page-shell min-h-screen pb-[calc(8rem+env(safe-area-inset-bottom))] pt-24 lg:pb-0 lg:pl-24 lg:pt-0">{children}</div>
      <StudyToolkit />
    </>
  );
}

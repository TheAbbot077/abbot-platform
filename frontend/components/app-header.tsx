"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BookOpen, BrainCircuit, CheckCircle2, GraduationCap, Home, LogOut, Settings, Shield, Sparkles, UserCircle } from "lucide-react";

import { clearClientAuthState, getCurrentUser, getSubjects } from "@/lib/api";
import { logoutSession } from "@/lib/auth-session";
import type { Subject, User } from "@/lib/types";
import { Button } from "@/components/ui/button";

const publicRoutes = new Set(["/", "/login", "/signup"]);

const navItems = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/subjects", label: "Study", icon: BookOpen },
  { href: "/settings", label: "Style", icon: Settings }
];

const staffNavItem = { href: "/command-center", label: "Command", icon: Shield };

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [activeHash, setActiveHash] = useState("");
  const [querySubjectId, setQuerySubjectId] = useState<number | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const isPublicRoute = publicRoutes.has(pathname);
  const currentSubjectId = getCurrentSubjectId(pathname, querySubjectId);
  const currentSubject = subjects.find((subject) => subject.id === currentSubjectId) ?? null;
  const subjectWorkspaceHref = currentSubjectId ? `/subjects/${currentSubjectId}` : "/subjects";

  useEffect(() => {
    let isMounted = true;

    async function loadUser(redirectOnFailure = false) {
      if (isPublicRoute) {
        setUser(null);
        return;
      }

      try {
        const response = await getCurrentUser();
        if (isMounted) {
          setUser(response.user);
        }
      } catch {
        if (isMounted) {
          clearClientAuthState();
          setUser(null);
        }
        if (redirectOnFailure) {
          router.replace("/login");
        }
      }
    }

    void loadUser();

    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) {
        void loadUser(true);
      }
    }

    window.addEventListener("pageshow", handlePageShow);

    return () => {
      isMounted = false;
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, [isPublicRoute, pathname, router]);

  useEffect(() => {
    let isMounted = true;

    async function loadSubjects() {
      if (isPublicRoute || !user) {
        setSubjects([]);
        return;
      }

      try {
        const response = await getSubjects();
        if (isMounted) {
          setSubjects(response);
        }
      } catch {
        if (isMounted) {
          setSubjects([]);
        }
      }
    }

    void loadSubjects();

    return () => {
      isMounted = false;
    };
  }, [isPublicRoute, user]);

  useEffect(() => {
    function syncHash() {
      setActiveHash(window.location.hash.replace("#", ""));
      const subjectParam = new URLSearchParams(window.location.search).get("subject");
      setQuerySubjectId(subjectParam && Number.isFinite(Number(subjectParam)) ? Number(subjectParam) : null);
    }

    syncHash();
    window.addEventListener("hashchange", syncHash);
    window.addEventListener("popstate", syncHash);
    return () => {
      window.removeEventListener("hashchange", syncHash);
      window.removeEventListener("popstate", syncHash);
    };
  }, [pathname]);

  async function handleLogout() {
    setIsLoggingOut(true);
    try {
      await logoutSession(router);
    } finally {
      setUser(null);
      setIsLoggingOut(false);
    }
  }

  if (isPublicRoute || !user) {
    return null;
  }

  const visibleNavItems = user.is_staff ? [...navItems, staffNavItem] : navItems;
  const mobileNavItems = [
    { href: "/dashboard", label: "Home", icon: Home, isActive: pathname === "/dashboard" },
    { href: "/subjects", label: "Subjects", icon: BookOpen, isActive: pathname === "/subjects" || (pathname.startsWith("/subjects/") && !activeHash) },
    { href: `${subjectWorkspaceHref}#abbot`, label: "Abbot", icon: GraduationCap, isActive: pathname.startsWith("/learn") || activeHash === "abbot" },
    { href: `${subjectWorkspaceHref}#ariel`, label: "Ariel", icon: BrainCircuit, isActive: activeHash === "ariel" },
    { href: `${subjectWorkspaceHref}#progress`, label: "Progress", icon: CheckCircle2, isActive: activeHash === "progress" },
    { href: "/settings", label: "Settings", icon: Settings, isActive: pathname === "/settings" }
  ];

  return (
    <>
      <aside className="fixed inset-y-4 left-4 z-40 hidden w-16 flex-col items-center justify-between rounded-2xl border bg-card/95 px-2 py-3 shadow-lg shadow-primary/10 lg:flex">
        <div className="space-y-5">
          <Link className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary text-primary-foreground" href="/dashboard" aria-label="Abbot Study">
            <Sparkles className="h-5 w-5" aria-hidden="true" />
          </Link>
          <nav className="space-y-2">
            {visibleNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = item.label === "Study" ? pathname.startsWith("/subjects") || pathname.startsWith("/learn") : pathname === item.href;
              return (
                <Link
                  key={item.label}
                  className={`flex h-11 w-11 items-center justify-center rounded-2xl transition-colors ${isActive ? "bg-secondary text-secondary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
                  href={item.href}
                  aria-label={item.label}
                  title={item.label}
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                </Link>
              );
            })}
          </nav>
        </div>
        <Button type="button" variant="outline" size="icon" onClick={handleLogout} disabled={isLoggingOut} aria-label="Logout">
          <LogOut className="h-4 w-4" aria-hidden="true" />
        </Button>
      </aside>

      <header className="fixed inset-x-2 top-2 z-40 rounded-3xl border bg-card/95 px-3 py-2 shadow-lg shadow-primary/10 backdrop-blur lg:hidden">
        <div className="flex min-h-14 items-center justify-between gap-3">
          <Link className="flex min-w-0 items-center gap-2" href="/dashboard" aria-label="Abbot Study home">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-semibold">Abbot Study</span>
              <span className="block max-w-[11rem] truncate text-xs text-muted-foreground">
                {currentSubject?.name ?? (currentSubjectId ? "Subject workspace" : "Choose a subject")}
              </span>
            </span>
          </Link>

          <details className="relative shrink-0">
            <summary className="flex min-h-11 min-w-11 cursor-pointer list-none items-center justify-center rounded-2xl border bg-background text-muted-foreground">
              <UserCircle className="h-5 w-5" aria-hidden="true" />
              <span className="sr-only">Open profile menu</span>
            </summary>
            <div className="absolute right-0 mt-2 w-52 rounded-2xl border bg-card p-2 text-sm shadow-lg">
              <p className="px-3 py-2 text-xs text-muted-foreground">Signed in as</p>
              <p className="truncate px-3 pb-2 font-medium">{user.username}</p>
              <Link className="flex min-h-11 items-center gap-2 rounded-xl px-3 py-2 text-muted-foreground hover:bg-muted" href="/settings">
                <Settings className="h-4 w-4" aria-hidden="true" />
                Settings
              </Link>
              {user.is_staff ? (
                <Link className="flex min-h-11 items-center gap-2 rounded-xl px-3 py-2 text-muted-foreground hover:bg-muted" href="/command-center">
                  <Shield className="h-4 w-4" aria-hidden="true" />
                  Command Center
                </Link>
              ) : null}
              <button
                type="button"
                className="flex min-h-11 w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-muted-foreground hover:bg-muted"
                onClick={handleLogout}
                disabled={isLoggingOut}
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Logout
              </button>
            </div>
          </details>
        </div>
      </header>

      <nav className="fixed inset-x-2 bottom-2 z-40 flex items-center gap-1 overflow-x-auto rounded-3xl border bg-card/95 p-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] shadow-lg shadow-primary/10 backdrop-blur lg:hidden">
        {mobileNavItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              className={`flex min-h-14 min-w-[4.75rem] flex-1 flex-col items-center justify-center gap-1 rounded-2xl px-2 py-2 text-xs font-medium transition-colors ${item.isActive ? "bg-secondary text-secondary-foreground" : "text-muted-foreground"}`}
              href={item.href}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}

function getCurrentSubjectId(pathname: string, querySubjectId: number | null): number | null {
  if (querySubjectId) {
    return querySubjectId;
  }

  const match = pathname.match(/^\/subjects\/(\d+)/);
  if (!match) {
    return null;
  }

  return Number(match[1]);
}

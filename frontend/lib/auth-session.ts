import { clearClientAuthState, logout } from "@/lib/api";

type RouterReplace = {
  replace: (href: string) => void;
};

export async function logoutSession(router: RouterReplace): Promise<void> {
  try {
    await logout();
  } finally {
    clearClientAuthState();
    router.replace("/login");
  }
}

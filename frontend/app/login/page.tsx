import { AuthForm } from "@/components/auth/auth-form";
import { PublicSessionInvalidator } from "@/components/auth/public-session-invalidator";

export default function LoginPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl items-center px-4 py-8 sm:px-6 lg:px-8">
      <PublicSessionInvalidator />
      <AuthForm mode="login" />
    </main>
  );
}

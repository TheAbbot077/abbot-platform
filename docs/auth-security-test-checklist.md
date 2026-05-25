# Auth Security Manual Test Checklist

Use this checklist after auth changes because the MVP does not yet include a browser test runner.

1. Log in with User A and confirm `/dashboard` loads User A data.
2. Click logout and confirm the app redirects to `/login`.
3. Refresh `/login` and confirm User A is not silently restored.
4. Open `/dashboard` directly after logout and confirm it redirects to `/login`.
5. From `/login`, press the browser forward button back to the previously opened dashboard. Confirm the dashboard immediately re-checks auth and redirects back to `/login`.
6. Open `/subjects`, `/settings`, `/learn/<documentId>`, and `/command-center` after logout and confirm each requires login.
7. Close the browser, reopen it, and confirm `/dashboard` requires login unless a future remember-me feature is explicitly enabled.
8. Visit the landing page `/` after logout and click Start studying. Confirm it opens signup and does not redirect to dashboard.
9. Add fake `user`, `auth_user`, `access_token`, and `refresh_token` values to localStorage/sessionStorage, then reload `/dashboard`. Confirm the backend auth check still redirects to login.
10. Log in as User A, logout, then log in as User B in the same browser. Confirm User B sees only User B subjects, textbooks, dashboard, Ariel, and Abbot context.
11. Leave a logged-in tab idle past the configured session age, then refresh. Confirm protected pages redirect to login with a friendly expired-session message.

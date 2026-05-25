# Abbot Study Staging QA Checklist

Use this checklist before promoting a staging build. Test with at least one normal student account and one staff/admin account.

Recommended devices:

- Desktop browser
- Mobile browser width, ideally a real phone
- Private/incognito browser session for auth checks

## 1. Mobile Landing Page

- Open the staging frontend URL on a phone.
- Confirm the landing page loads without horizontal scrolling.
- Confirm the hero image, headline, signup button, and login button are visible.
- Tap signup and confirm it opens the signup page.
- Tap login and confirm it opens the login page.

Expected result: public pages are mobile-friendly and do not auto-login the user.

## 2. Signup

- Create a new student account.
- Fill required fields: first name, last name, email, password, confirm password, country, role.
- Leave optional demographics blank or choose “Prefer not to say.”
- Submit the form.

Expected result: account is created, user lands in the app, and no sensitive data is required unnecessarily.

## 3. Login

- Log out if already signed in.
- Log in with the new student account.
- Refresh the dashboard.

Expected result: login succeeds, the user remains authenticated after refresh during the active session, and dashboard data belongs only to that user.

## 4. Logout

- Click logout from the app shell or profile menu.
- Confirm the app redirects to login or landing page.
- Try opening `/dashboard`, `/subjects`, `/settings`, and a known subject URL.

Expected result: protected pages redirect to login and protected API calls return unauthorized.

## 5. Strict Back/Forward Auth Behavior

- Log in and reach the dashboard.
- Press the browser Back button to return to login or landing page.
- Press browser Forward to attempt to return to dashboard.
- Close and reopen the tab/browser, then try a protected page.

Expected result: protected pages perform a fresh backend auth check. If the session was invalidated by returning to login/logout behavior, the user must sign in again. A cached browser history page must not grant access.

## 6. Create Subject

- Go to Subjects.
- Create a subject, for example “Economics.”
- Open the subject workspace.

Expected result: the subject appears in the subject list and opens a focused workspace scoped to that subject.

## 7. Upload PDF From Phone

- From the subject workspace, open textbook upload.
- Upload a small PDF from the phone file picker.
- Confirm upload progress and status messages are readable on mobile.

Expected result: the PDF uploads successfully and is attached to the selected subject.

## 8. Parser Processing

- Wait for textbook processing.
- Check status messages such as “Preparing your textbook” and “Finding what you need to learn.”
- Open the textbook chapters once processing finishes.

Expected result: chapters appear in the original document order using explicit sequence numbers. The parser should not order chapters by task completion time.

## 9. Subject Workspace

- Open the selected subject workspace.
- Check tabs or sections: Overview, Textbooks, Concepts, The Abbot, Ariel, Progress, Reinforcement.
- Confirm the current subject name remains visible on mobile.

Expected result: concepts and progress are scoped to this subject only. No unrelated subject content appears.

## 10. The Abbot

- Open the current unlocked concept.
- Start the lesson with The Abbot.
- Confirm the explanation is readable on mobile.
- If math appears, confirm equations render nicely and long equations do not break layout.

Expected result: The Abbot teaches only the current unlocked concept using the current chapter context.

## 11. Follow-Up Questions

- Ask The Abbot a question about the current concept.
- Ask a question that may need general clarification.

Expected result: The Abbot answers without unlocking progress, labels general knowledge clarification when used, and stays focused on the current concept.

## 12. MCQs

- Open the concept check.
- Confirm MCQ options are large enough to tap on mobile.
- Submit incorrect answers first if safe for the test account.
- Submit correct answers on a retry.

Expected result: MCQs test only the current concept. Failure shows remediation actions. Passing marks the concept passed and unlocks the next concept only when the threshold is met.

## 13. Progress Update

- Return to the dashboard and subject workspace progress.
- Check document, chapter, and concept status.

Expected result: progress reflects the latest quiz result. Passed concepts show passed, the next concept is available, and future concepts remain locked.

## 14. Themes

- Open Settings.
- Change the theme.
- Refresh the page.
- Log out and log back in.

Expected result: the selected theme applies globally and persists across refresh/login. Background gradients and glossy cards remain readable.

## 15. Delete Textbook

- Upload or choose a disposable textbook.
- Delete it from the UI.
- Confirm the destructive action prompt appears.
- Confirm deletion.

Expected result: only the current user’s textbook is deleted. Related chapters, concepts, attempts, progress, and Ariel records are removed or no longer shown.

## 16. Restart Lesson

- Open a concept with quiz attempts.
- Restart the current concept.
- If available, restart the chapter or textbook on disposable data.

Expected result: confirmation appears before reset. Sequence order is preserved. The reset does not delete the uploaded textbook file unless explicitly requested.

## 17. Admin Access Blocked For Normal Users

- Log in as a normal student.
- Try opening `/command-center` or any admin route.
- Try calling admin APIs through the browser if possible.

Expected result: normal users are blocked from admin pages and admin APIs. No admin data is exposed.

## 18. Admin Smoke Test

- Log in as a staff/admin user.
- Open Abbot Command Center.
- Check dashboard metrics, users, textbooks, parser preview, analytics, and audit logs.

Expected result: admin pages load only for staff/admin users and show aggregated or authorized data.

## 19. Final Staging Notes

Record:

- Staging frontend URL:
- Staging API URL:
- Test student email:
- Test admin email:
- Browser/device tested:
- PDF tested:
- Parser result:
- Failed checks:
- Fix owner:
- Retest date:


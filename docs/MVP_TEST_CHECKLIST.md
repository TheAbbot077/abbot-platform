# MVP Test Checklist

Use this checklist before every MVP demo or release candidate. The automated backend tests cover the most fragile ordering, ownership, and learning rules. The manual checks make sure the full student experience still feels clear and friendly.

## Before Testing

- Start Docker: `docker compose up`
- Apply migrations: `docker exec study_backend python manage.py migrate`
- Run backend tests:
  - `docker exec study_backend python manage.py test accounts documents learning --noinput`
- Run frontend typecheck:
  - From `frontend/`: `node node_modules/typescript/bin/tsc --noEmit --incremental false --pretty false`
- Open the app at `http://localhost:3000`

## Test Accounts

Create two users:

- Student A: owns the main subjects/textbooks.
- Student B: used to verify ownership protection.

## Auth

- Signup:
  - Create a new account from the signup page with first name, last name, email, password confirmation, country, and role.
  - Expected: user lands in the app, session is active, dashboard loads, and optional demographic fields can be skipped or set to prefer not to say.
- Login:
  - Log out, then log in with the same account.
  - Expected: dashboard loads and shows that user’s own study space.
- Logout:
  - Use the logout button in the side nav or bottom nav.
  - Expected: user is redirected to login.
- Protected routes:
  - While logged out, try `/dashboard`, `/settings`, and an existing `/learn/<document_id>` URL.
  - Expected: user is redirected or shown a friendly login-required state.
- Expired session handling:
  - Clear browser cookies or restart the backend session.
  - Refresh `/dashboard`.
  - Expected: friendly session message or login redirect, not a raw technical error.

## Subjects

- Create subject:
  - Add a subject such as “Economics”.
  - Expected: subject appears in “Your subjects”.
- View subjects:
  - Refresh the page.
  - Expected: subject remains visible.
- Delete subject:
  - Delete an empty subject.
  - Expected: subject disappears.
- Delete subject with textbooks:
  - Try deleting a subject that has a textbook.
  - Expected: deletion is blocked with a helpful message.
- Ownership protection:
  - Log in as Student B.
  - Expected: Student A’s subjects are not visible or deletable.

## Textbooks

- Upload PDF:
  - Choose a subject and upload a valid PDF.
  - Expected: textbook appears with friendly status copy.
- Processing status:
  - Watch status while Celery processes.
  - Expected: “Preparing your textbook” / “Finding what you need to learn” style copy, not technical pipeline language.
- Ordered chapters:
  - Open the textbook card after processing.
  - Expected: chapters appear by explicit chapter sequence.
- Delete textbook:
  - Delete a textbook.
  - Expected: textbook, chapters, concepts, attempts, progress, and Ariel memory for that textbook are removed.
- Restart textbook:
  - Restart a textbook.
  - Expected: PDF remains, chapter/concept order remains, learning progress resets.
- Ownership protection:
  - As Student B, attempt Student A’s textbook URL/API ID if known.
  - Expected: access denied or not found.

## Learning

- Chapter order:
  - Confirm chapters remain in textbook order even if processing finished asynchronously.
- Concept order:
  - Confirm concepts appear in sequence order inside each chapter.
- Objectives:
  - Check a chapter with objectives.
  - Expected: objectives are context only; they are not teachable concepts.
- The Abbot teaches current concept only:
  - Start a study round.
  - Expected: The Abbot teaches only the currently available concept.
- Follow-up questions:
  - Ask The Abbot a question about the current concept.
  - Expected: answer appears, no concept is marked passed, no next concept unlocks.
- MCQs:
  - Generate practice questions.
  - Expected: questions test only the current concept and official lesson material.
- Visual tutoring:
  - Ask The Abbot: "Can you graph y = x^2?"
  - Expected: The Abbot returns `visual_content` with `type=graph` and `render_mode=function_plot`; the learning page renders a parabola.
  - Ask The Abbot: "Draw a right triangle."
  - Expected: The Abbot returns `visual_content` with `type=geometry`, `render_mode=geometry_diagram`, and `shape=triangle`; the learning page renders a triangle with labels if provided.
  - Study or ask about a supply-and-demand concept.
  - Expected: The Abbot may return a helpful line graph or chart, but only when it improves the explanation.
  - Study a non-visual definition-only concept.
  - Expected: The Abbot does not force a graph or diagram.
  - Ask for or simulate malicious visual content containing raw HTML, JavaScript, SVG strings, or an external image URL.
  - Expected: backend strips the unsafe visual and returns the explanation without `visual_content`.
  - Ask for an unsupported or invalid graph expression.
  - Expected: frontend shows a friendly visual fallback instead of crashing.
  - Generate MCQs after a visual lesson.
  - Expected: MCQs still use only official concept lesson text/source context; visual data does not unlock concepts or affect grading.
- Passing:
  - Submit correct answers.
  - Expected: concept is passed and next concept unlocks.
- Failing:
  - Submit incorrect answers.
  - Expected: remediation appears, current concept remains the focus, next concept stays locked.
- Restart concept:
  - Restart the current concept.
  - Expected: lesson, attempts, and practice questions clear; ordering remains intact.
- Restart chapter:
  - Restart a chapter.
  - Expected: chapter concepts reset and later chapter content locks again.

## Progress

- Dashboard updates:
  - Pass a concept, return home.
  - Expected: continue learning card updates to the next concept.
- Completed chapter:
  - Pass the final required concept in a chapter.
  - Expected: chapter shows complete and the next chapter unlocks.
- Locked content:
  - Try to query or learn a future concept directly.
  - Expected: locked content remains inaccessible.
- Friendly dashboard:
  - Expected sections are visible: continue learning, subjects, textbooks, current chapter, current concept, Ariel status if available, weak concepts if available.

## Settings

- Theme changes:
  - Pick each theme in Settings.
  - Expected: colors update across dashboard, learning page, buttons, cards, and navigation.
- Persistence:
  - Change theme, refresh, log out, log in.
  - Expected: selected theme remains applied.
- Default:
  - New user starts on Black, white and gold.

## Celebrations

- Concept pass:
  - Pass a concept.
  - Expected: short confetti plays once.
- Chapter completion:
  - Pass the last concept in a chapter.
  - Expected: confetti and balloons play once.
- Ariel examiner pass:
  - Submit Ariel to examiner and get a passing result.
  - Expected: confetti and balloons play once.
- No replay on refresh:
  - Refresh after a celebration.
  - Expected: animation does not replay.
- Reduced motion:
  - Enable OS/browser reduced motion.
  - Expected: animations are suppressed.

## Security

- Abbot Command Center API:
  - Log in as a normal student and request `/api/admin/command-center/`.
  - Expected: request is rejected with 403 and no admin metrics are returned.
- Abbot Command Center page:
  - Log in as a normal student and open `/command-center`.
  - Expected: page shows an admin access required message and does not show metrics, recent textbooks, or failed jobs.
- Staff Command Center:
  - Log in as a staff/admin user and open `/command-center`.
  - Expected: Abbot Command Center loads totals, recent uploaded textbooks, parser confidence, and recent failed jobs.
- Admin user analytics:
  - Open Abbot Command Center as a staff/admin user.
  - Expected: aggregated userbase analytics appear for countries, age ranges, gender, education levels, roles, signups, active users, active subjects, textbooks per user, and completed concepts per user.
  - Expected: analytics are grouped by default and do not expose individual age or gender details.
- Admin user management:
  - Log in as a superuser or staff user with user-change permission.
  - Expected: user list loads; search by username/email works; active/inactive and staff/student filters work.
- Admin user detail:
  - Select a user in Abbot Command Center.
  - Expected: profile summary, subjects, textbooks, and learning progress appear; password/secrets are never shown.
- Admin user activation:
  - Deactivate and reactivate a test user.
  - Expected: user status changes, normal users cannot perform the action, and admins cannot deactivate their own account.
- Admin textbook management:
  - Log in as a superuser or staff user with document-change permission.
  - Expected: all textbooks appear; status and parser-confidence filters work; parser warnings are visible.
- Admin parser preview:
  - Select a textbook and run parser preview.
  - Expected: stored chapters remain unchanged; proposed chapters show in sequence order with warnings and differences.
- Admin textbook reprocess:
  - Try reprocessing a textbook with existing learning progress.
  - Expected: system warns that progress may reset and requires explicit force confirmation.
- Admin textbook delete:
  - Delete a test textbook from Abbot Command Center.
  - Expected: confirmation is required; chapters, concepts, quizzes, progress, Ariel records, and stored file are removed safely.
- Admin quality tools:
  - Log in as a superuser or staff user with learning question or concept-change permission.
  - Expected: concepts can be filtered by textbook/chapter, MCQ pass/fail rates are visible, commonly failed concepts appear, and possible objective-as-concept warnings are shown.
- Admin MCQ refresh:
  - Refresh MCQs for a concept from Abbot Command Center.
  - Expected: confirmation is required; only unanswered generated MCQs are cleared; quiz attempts and progress remain.
- Admin Abbot lesson refresh:
  - Refresh The Abbot lesson for a concept from Abbot Command Center.
  - Expected: confirmation is required; stored lesson rows are cleared; concept progress, quiz attempts, and ordered unlocking remain unchanged.
- Admin audit log:
  - Open `/command-center/audit` as a user with audit-log permission.
  - Expected: sensitive events such as user activation changes, textbook deletes, reprocess requests, restarts, and quality-tool refreshes appear with actor, target, timestamp, and IP when available.
  - Open the same page as a normal student or staff user without audit permission.
  - Expected: audit data is not exposed.
- Cross-user subjects:
  - Student B cannot see, edit, or delete Student A’s subjects.
- Cross-user textbooks:
  - Student B cannot see, delete, restart, or upload into Student A’s textbooks/subjects.
- Cross-user progress:
  - Student B cannot view Student A’s progress, current concept, MCQs, tutor lesson, or dashboard data.
- Delete endpoints:
  - Deleting another user’s subject/textbook returns denied or not found.
- Restart endpoints:
  - Restarting another user’s concept/chapter/textbook returns denied or not found.

## Automated Coverage Map

- Auth/settings: `backend/accounts/tests.py`
- Subjects/textbooks/extraction/delete ownership: `backend/documents/tests.py`
- Ordering/unlocking/tutor/MCQs/grading/restart/dashboard/Ariel/celebrations: `backend/learning/tests.py`

## Release Gate

Do not call the MVP ready unless:

- Backend tests pass.
- Frontend typecheck passes.
- A fresh user can complete signup to first concept pass.
- A second user cannot access the first user’s data.
- The dashboard uses friendly copy and never exposes raw backend wording to the student.

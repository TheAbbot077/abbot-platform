# Study Toolkit QA Checklist

Use this checklist on desktop and mobile widths before release.

## Entry Points

- [ ] Study Tools button appears on the lesson/concept page.
- [ ] Study Tools button appears in the MCQ/quiz panel.
- [ ] Floating Study Tools button appears on protected app pages.
- [ ] Opening the toolkit does not change quiz answers, score, progress, or unlock state.

## Whiteboard

- [ ] Whiteboard opens in the toolkit.
- [ ] Drawing works with desktop mouse.
- [ ] Drawing works with mobile touch/finger.
- [ ] Page does not scroll while drawing on the canvas.
- [ ] Black marker works.
- [ ] Blue marker works.
- [ ] Red marker works.
- [ ] Green marker works.
- [ ] Gold marker works.
- [ ] Small marker size works.
- [ ] Medium marker size works.
- [ ] Large marker size works.
- [ ] Eraser removes strokes.
- [ ] Undo restores the previous board state.
- [ ] Redo restores an undone board state.
- [ ] Clear board asks for confirmation.
- [ ] Confirming clear board clears the canvas.
- [ ] Cancelling clear board leaves the canvas unchanged.

## Calculators

- [ ] Basic calculator evaluates arithmetic.
- [ ] Scientific calculator evaluates `sin`, `cos`, `tan`, `log`, `ln`, square, square root, exponents, and parentheses.
- [ ] Calculator uses safe math parsing, not browser `eval`.
- [ ] Graph tab renders `y = x^2`.
- [ ] Graph tab rejects unsafe or unsupported expressions with a friendly message.
- [ ] Simple interest computes `A = P(1 + rt)`.
- [ ] Compound interest computes `A = P(1 + r/n)^(nt)`.
- [ ] Present value computes `PV = FV / (1 + r)^t`.
- [ ] Future value computes `FV = PV(1 + r)^t`.

## Notes

- [ ] Scratch notes can be typed.
- [ ] Notes remain after closing and reopening the toolkit in the same browser.
- [ ] Notes are scoped to the current concept when opened from a lesson/quiz.

## Mobile UX

- [ ] Toolkit opens full-screen on small screens.
- [ ] Toolbar buttons are large enough to tap.
- [ ] Calculator buttons are large enough to tap.
- [ ] Mobile keyboard does not hide the active input permanently.
- [ ] Drawer content can scroll without scrolling the page behind it.

## Learning Safety

- [ ] Toolkit does not affect quiz grading.
- [ ] Toolkit does not unlock concepts.
- [ ] Toolkit does not submit whiteboard or notes to the backend.

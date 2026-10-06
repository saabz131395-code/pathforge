# Changelog

## 2.2.0

- Added **6 new career paths**: Mobile App Development, AI/Machine Learning, Graphic Design, Content Writing/Copywriting, E-commerce Store Management and Game Development, for **16 paths** in total. Each new path comes with beginner-to-advanced resources, 4 projects and 6 level-check questions.
- Rebalanced the quick-match quiz for 16 paths. Across all 4,032 possible answer combinations, about 85% give one clear match, ties never include more than 3 paths, and every path can win.
- Home page: clicking a path card goes straight to its level check. Removed the duplicate path list. "Not sure?" now links to the quick match.
- New home sections, editable in `catalog/home.yaml`: **learning tips**, **free tools to publish your proof**, and **first freelance steps**.
- The link checker no longer marks a link as failed when the internet itself is unreachable (DNS error or timeout). Those results aren't saved. Added `--retry-failed`.
- Replaced the GCFGlobal graphic-design link (moved, and the new site was under maintenance) with Canva Design School's free Graphic Design Basics course.
- Grew the test suite to 58 tests.

## 2.1.0

### Personalised learning flow
- Clicking a path now opens a **level check**: 6 real knowledge questions (2 basic, 2 intermediate, 2 advanced), shown one at a time with a progress bar. There's an "I don't know yet" option, and the form still works without JavaScript.
- The result places the learner at **Beginner, Intermediate or Advanced**, shows their score, and lists the topics they missed with the correct answer and a short explanation.
- A new **start guide** page shows where to start (the best resource for their level, plus a backup), the first session, how to study at that level, what to build, and how to prove it. Each step has a checkbox saved in the browser.
- Learners can switch level or retake the check at any time. Anyone completely new can skip the check.
- Added a new **Advanced** level, with 12 advanced resources and 10 advanced projects (one per path).
- Added 60 level-check questions in `catalog/assessments.yaml`. Each one is validated, and its options are shuffled the same way every time.
- Removed the "where are you starting?" self-rating from the home page, because the level check replaces it.
- Added a favicon.
- Grew the test suite to 52 tests.

## 2.0.0

### Trust and verification
- A resource is now marked **Verified** only when a curator has confirmed its cost, certificate, level and skill fit **and** a real link check has passed. Previously, seeding the database marked every resource as verified without checking anything.
- Link-check results are kept in their own table and survive re-seeding.
- Resources with a broken link are hidden. Never-checked resources show as "Review pending", with each check visible.
- The link checker retries every failed HEAD request with a normal GET, because some sites (Kaggle, PortSwigger) answer HEAD with a false 404. Sites that block automated requests are marked **BLOCKED**: they stay visible to learners but are not verified until a person confirms the link.
- The link checker adds `--pending-only` and `--db`, waits briefly between requests, and prints a summary.

### Content
- Moved all paths, resources and projects into editable YAML files under `catalog/`, with validation and readable error messages.
- Expanded the resource list from 24 to 42 (at least 3 per path). Removed the Figma homepage, which is a tool rather than a learning resource. The new resources start with curator checks set to `PENDING`.

### Quick-match quiz
- Replaced the two "pick a path" dropdowns, which ended in a tie for almost any pair of different answers, with 4 multiple-choice questions and a tie-breaker. Across all 750 possible answer combinations, about 85% now give one clear match, ties never include more than 3 paths, and every path can win.
- Incomplete answers send the learner back with a message instead of showing all 10 paths as a "tie".

### Reliability
- The app works no matter which folder it is started from, because the database path is now absolute.
- The database is built automatically on the first run.
- Each request uses one database connection, which is always closed, including when an error happens.
- Debug mode is off unless `FLASK_DEBUG=1` is set.
- Added friendly 404 and 400 pages, and unknown filter or level values are ignored safely.
- Progress is saved under permanent path and project keys instead of database ids, so it survives re-seeding. It also warns when the browser blocks storage.
- All SQL now lives in the service layer, and routes contain none.

### Quality
- Grew the test suite from 5 tests to 39: recommendation rules, every page and redirect, validation, verification rules, re-seeding, database upgrades, and the link checker using a fake network.
- Added GitHub Actions CI on Python 3.10 and 3.12.
- Added screenshots, and rewrote the README.

## 1.0.0
- First version: 10 career paths, resources, projects, progress tracking and CV guidance.

# Baldy Route Finder — Sun Valley Bald Mountain

## What This Is
A personalized ski route planner for Bald Mountain (Baldy) at Sun Valley, Idaho — installed as an app on your phone, it generates a step-by-step itinerary of lifts and runs based on your difficulty preference, how long you want to ski, whether you want groomed runs or moguls, and what you've liked or disliked in the past. It only ever routes you through runs that are actually open today.

## Tech Stack
- Single `index.html` file — no build tools, no npm, React 18 + Babel + Tailwind all loaded from CDN
- `trail-map.jpg` — official Bald Mountain trail map image (2600×1467px)
- `manifest.json` + `sw.js` + `icon-*.png` — makes it an installable PWA (add to home screen, works offline)
- `scripts/update_groomed.py` — standard-library-only Python scraper, run daily by a scheduled cloud job
- `groomed-today.json` — the day's grooming/open-run data, read by the app at runtime
- Hosted on Netlify (`graceful-pie-61aeec.netlify.app`), auto-deployed from GitHub (`github.com/baldy-coder/baldy-route-finder`) — just `git push` to ship a change, no manual upload step

## How It Works

### Data Model
All data lives in JS objects at the top of `index.html`:

- **RUNS** (72 runs) — `id`, `name`, `difficulty` (green/blue/black/double-black), `area`, `time` (minutes to ski), `connectsTo` (run IDs or base IDs reachable from the bottom), and optionally `mandatoryLift` (see below)
- **LIFTS** (12 lifts) — `id`, `name`, `time` (ride time in minutes), `base` (which base it departs from), `topRuns` (which runs are accessible from the top)
- **BASES** (6 bases) — `name` and `lifts` (which lifts depart from here)
- **SUMMIT_RUNS** — run IDs accessible from any lift that reaches the true summit
- **FACILITIES** (4 lodges) — Warm Springs, River Run, Seattle Ridge, and Lookout lodges, each flagged for `hasBathroom`/`hasFood`, used for inserting lunch/bathroom breaks
- **PREF_SCORES** / **GROOM_PREF_BONUS** — scoring tables for the difficulty and groomed/moguls preferences

### Virtual Combo Lifts
Some lifts are actually two (or more) stages chained together, modeled as single entries with combined ride times — except where a real fork exists partway through (see Gondola below):
- `rr-lookout` — "River Run Express → Lookout" (14 min) — River Run Base to summit
- `gondola-christmas` — "Gondola → Christmas Lift" (18 min) — River Run Base to summit
- `gondola` — the same physical gondola, but modeled separately (9 min) for getting off *before* Christmas Lift to ski Roundhouse Slope instead of continuing to the summit
- `gondola-seattle` — "Gondola → Gun Tower → Seattle Ridge" (15 min) — River Run Base to Seattle Ridge
- `broadway-christmas` — "Broadway Express → Christmas Lift" (15 min) — Lower Broadway Base to summit

### Route Generation Algorithm (`generateRoute`)
Weighted random walk through the lift/run graph. At each decision point, every candidate lift or run gets a score built from several additive factors:

1. **Pick a lift** from current base — scored by run quality (does it serve runs matching your difficulty preference?), freshness (haven't ridden it in a while? bonus — resets over ~8 steps), exploration bonus (unskied runs up top?), and area novelty.
2. **Ski down** — chain runs until reaching a base. Each run's score combines:
   - Difficulty match (your preference)
   - Freshness (not skied recently this session)
   - Area variety (penalizes repeatedly skiing the same zone)
   - **Stuck-loop escape** — if you've circled one area for several runs in a row, a growing bonus pushes toward leaving it, regardless of difficulty preference (fixes a bug where "just blues" could get trapped looping Frenchman's Base forever)
   - **Groomed/moguls bonus** — boosts or penalizes based on today's real grooming data and your preference
   - **Personal history bonus** — boosts runs you've 👍'd, penalizes ones you've 👎'd, and nudges toward runs you've never skied before
   - **Open-run hard filter** — a run you can't currently ski (closed today) is excluded entirely, not just deprioritized — see Daily Mountain Data below
3. **Mandatory lifts** — a run can carry a `mandatoryLift` field forcing the very next lift choice, bypassing scoring. Currently used for Lower Broadway → Broadway Express (that run only connects to Lower Broadway Base, which could otherwise send you up via the Broadway Express → Christmas Lift combo instead).
4. **Repeat** until time runs out, then `insertBreaks` walks the finished route inserting lunch/bathroom stops at real lodges once enough time has passed.

## Daily Mountain Data
`scripts/update_groomed.py` scrapes `sunvalley.com/the-mountain/mountain-report/` (plain HTML, no JS rendering needed) for every Bald Mountain trail's groomed and open/closed status, maps resort trail names to this app's run IDs (a handful need manual aliases for spelling/punctuation differences — see `NAME_ALIASES`), and writes `groomed-today.json`. A scheduled cloud routine (`claude.ai/code/routines`) runs this every morning at 7am Mountain Time, commits, and pushes — fully hands-off. The app fetches this file at runtime; if it's ever missing or stale, the app just doesn't apply the groomed bonus or open-run filter rather than breaking.

## Personalization
Fully on-device, no server account:
- First visit asks for a name + username, stored in `localStorage` (`baldy_profile`)
- A brief full-screen greeting ("Good morning, Otis!") on open, time-of-day aware, fades after ~1.5s
- 👍/👎 buttons on every run in the itinerary feed into `baldy_run_history` (`localStorage`), which future routes read to favor liked runs, avoid disliked ones, and nudge toward runs never skied before
- "Wipe my data" (in the config panel, not the header — placing it near the top caused mobile scroll-bounce to make it hard to tap) clears everything and returns to the welcome screen

## React Components
- **App** — top-level state: route result, profile, run history, groomed/open data (fetched on mount)
- **Header** — title bar + time-aware greeting
- **GreetingIntro** / **WelcomeModal** — the splash greeting and first-run setup
- **TrailMap** — trail map image with an SVG overlay showing the *current section* of the route in full color (lines matched to hand-placed coordinates), other sections faded; sticky-pinned on mobile once a route exists
- **MapEditor** — hidden dev tool (Shift+E) for clicking to (re)define a run or lift's map coordinates; outputs JSON to paste into `RUN_COORDS`/`LIFT_COORDS`
- **RouteConfig** — difficulty, groomed/moguls, duration, starting base, bathroom/lunch break toggles, generate button, wipe-data link
- **RouteDisplay** — step-by-step itinerary, grouped into sections (one per lift + the runs after it) with Prev/Next navigation and click-to-jump; like/dislike buttons per run
- **RouteStats** — summary cards (runs skied, lifts ridden, total time)
- **RunSearch** — collapsible browse/filter of all runs by name and difficulty

## What We Tried (Map Overlay)
Early attempts at an interactive map — hand-drawn SVG paths, highlighted lines over the photo, text-label highlighting — all got scrapped as too inaccurate or too much manual work. The approach that stuck: the **Map Editor** (Shift+E) lets you click directly on the trail photo to place waypoints per run/lift, copy the resulting JSON, and paste it into `RUN_COORDS`/`LIFT_COORDS` — accurate because a human who knows the mountain placed the points, not guesswork.

## Known Issues / TODO
- **Some run connections may still be wrong** — Otis is the authority on which runs connect to what; we fix these as they're found (e.g. Roundhouse Slope was mis-wired to Broadway Express before being corrected)
- **"Roundhouse Lane"** appears on the resort's official trail list but isn't in our RUNS data — low priority, hasn't blocked anything yet
- **Lift open/closed status isn't tracked yet** — only run status is; a lift could theoretically be closed while its runs show open. Natural next step given how `update_groomed.py` already works.
- **Route can still feel repetitive on very long sessions** — much improved by the stuck-loop fix, but not perfectly tuned
- **Groomed/moguls bonus magnitude (±0.35) is a guess** — directionally verified correct, not yet tuned against real daily data since the mountain only recently opened for the season

## Mountain Geography Quick Reference
- **Warm Springs** (right side of map) — Challenger Express serves this area. Upper/mid/lower variants of Warm Springs, Limelight, Greyhawk, Hemingway, Cozy, Picabo Street
- **Frenchman's** (center-right) — Flying Squirrel Express and Frenchman's lift. College runs, Can-Can, French Dip, Janss Pass, Arnold's Run
- **River Run** (center) — Main base area. River Run Express → Lookout and the Gondola are the main ways up; getting off the Gondola before Christmas Lift reaches Roundhouse Slope, which forks to Olympic Lane or Lower Canyon. Upper/Mid/Lower River Run, Holiday runs
- **Christmas** (center-left) — Christmas Ridge, Christmas Bowl, Easter Bowl, Little Easter Bowl
- **Seattle Ridge** (left) — Seattle Ridge Express. Gretchen's Gold, Muffy's Medals, Christin's Silver, Leigh Lane. All green runs. Lower Broadway only exits via Broadway Express (mandatory, enforced in code).
- **Bowls** (far left) — Mayday Express serves Bowl Lane → various bowls (Mayday, Lefty's, Kaitlyn's, Sigi's). Also Lookout Bowl, Sunrise Bowl, Numbers, Cold Springs Chutes

## Deployment & Automation
- Code lives at `github.com/baldy-coder/baldy-route-finder`, auto-deploys to Netlify on every push to `main`
- The grooming/open-run scraper runs as a scheduled Claude cloud routine (`trig_01EdYSjGFsQ7HXcuqjUE9KUW`), daily 7am Mountain Time — view/manage at `claude.ai/code/routines`
- That routine needs the Claude GitHub App installed on the repo to push (a plain claude.ai GitHub connection isn't enough) — if daily updates silently stop, check this first
- Otis's laptop is school-managed (Jamf) — third-party installers can silently fail there; prefer things that already work (`git`, `curl`, `python3`) over installing new CLI tools when a workaround exists

## User Context
The user is Otis, a Kent Denver School student building this as an independent study project (with a supervising mentor he checks in with). He was a beginner developer when this started — first time with git, GitHub, and command-line tools — and is a skier who knows Bald Mountain well. He's the source of truth for all run difficulties, connections, and lift access. He prefers concise communication, quick iteration, and plain-language explanations of technical steps.

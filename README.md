# Baldy Route Finder — Sun Valley Bald Mountain

## What This Is
A single-file HTML web app that generates personalized ski route itineraries for Bald Mountain (Baldy) at Sun Valley, Idaho. The user picks their difficulty preference, how long they want to ski, and which base to start from — the algorithm generates a step-by-step route with lifts and runs.

## Tech Stack
- Single `index.html` file — no build tools, no npm
- React 18 + Babel (loaded from CDN)
- Tailwind CSS (loaded from CDN)
- `trail-map.jpg` — official Bald Mountain trail map image (2600×1467px)

## How It Works

### Data Model
All data lives in JS objects at the top of `index.html`:

- **RUNS** (~73 runs) — Each has `id`, `name`, `difficulty` (green/blue/black/double-black), `area`, `time` (minutes to ski), and `connectsTo` (array of run IDs or base IDs reachable from the bottom)
- **LIFTS** (~11 lifts) — Each has `id`, `name`, `time` (ride time in minutes), `base` (which base it departs from), and `topRuns` (which runs are accessible from the top)
- **BASES** (6 bases) — Each has `name` and `lifts` (which lifts depart from here)
- **SUMMIT_RUNS** — Array of run IDs accessible from any lift that reaches the summit

### Virtual Combo Lifts
Some lifts are actually two lifts chained together (because you have to ride one to reach the next). These are modeled as single entries with combined ride times:
- `rr-lookout` — "River Run Express → Lookout" (14 min) — River Run Base to summit
- `gondola-christmas` — "Gondola → Christmas Lift" (18 min) — River Run Base to summit
- `gondola-seattle` — "Gondola → Gun Tower → Seattle Ridge" (15 min) — River Run Base to Seattle Ridge
- `broadway-christmas` — "Broadway Express → Christmas Lift" (15 min) — Lower Broadway Base to summit

### Route Generation Algorithm (`generateRoute`)
Weighted random walk through the lift/run graph:

1. **Pick a lift** from current base — scored by:
   - Run quality (do the runs match user's difficulty preference?)
   - Lift freshness (haven't ridden it in a while? bonus — takes 8 steps to fully reset)
   - Exploration bonus (does this lift access runs we haven't skied yet?)
   - Area novelty (does it go to a part of the mountain we haven't visited much?)

2. **Ski down** — chain runs until reaching a base:
   - Each run scored by difficulty match, freshness, area variety, plus randomness
   - When a run connects to multiple bases, picks the one with the freshest lift options

3. **Repeat** until time runs out

### Key Constraint: Lower Broadway → Broadway Express
Lower Broadway *only* connects to `lower-broadway-base`. After skiing Lower Broadway, you MUST take Broadway Express — there's no other way out. This is how the real mountain works. (Note: this mandatory-lift-after-run isn't yet enforced as a hard constraint in the algorithm — it works because lower-broadway-base's only lifts are broadway-express and broadway-christmas. But if you add other runs connecting to lower-broadway-base, be aware of this.)

## React Components
- **App** — Top-level state, holds route result
- **Header** — Title bar
- **TrailMap** — Just renders the trail map image (no overlay — we tried SVG trail tracing and text-label highlighting, both scrapped)
- **RouteConfig** — User inputs: difficulty preference, duration slider, starting base
- **RouteDisplay** — Step-by-step itinerary with hover effects (each step glows in its difficulty color on hover)
- **RouteStats** — Summary cards (runs skied, lifts ridden, total time)
- **RunSearch** — Browse/filter all runs by name and difficulty

## What We Tried and Scrapped
1. **Interactive SVG trail map** — Hand-drawn SVG paths for every run. Too much work, didn't look good.
2. **SVG trail overlay on photo** — Drew highlighted lines over the trail map photo following run paths. Lines didn't match actual trails well. User said "that was kinda ass."
3. **Text label highlighting** — Found pixel coordinates of run name text on the map, drew colored rectangles behind them. Angles and positions were too hard to get right at scale.
4. **Option D chosen** — Map is just a static reference image. Route list has interactive hover highlighting instead.

## Known Issues / TODO
- **Lower Broadway → Broadway Express should be mandatory** — Currently works by coincidence (only lifts at that base). Could be made explicit.
- **Lunch/bathroom breaks** — User discussed adding "after X minutes, stop for lunch" and "after Y minutes, bathroom break" features. Not implemented yet. The idea: ask the user how long before they want a lunch break and a bathroom break, then insert those into the route at the right times.
- **Exhibition run removed** — User said to just get rid of it; it's not accessible from the summit despite being labeled that way on some maps.
- **Route sometimes feels repetitive on long sessions** — Algorithm improvements helped a lot but could still be tuned.
- **Some run connections may be wrong** — User (Otis) is the authority on which runs connect to what. When in doubt, ask him.

## Mountain Geography Quick Reference
- **Warm Springs** (right side of map) — Challenger Express serves this area. Has upper/mid/lower variants of Warm Springs, Limelight, Greyhawk, Hemingway, Cozy, Picabo Street
- **Frenchman's** (center-right) — Flying Squirrel Express and Frenchman's lift. College runs, Can-Can, French Dip, Janss Pass, Arnold's Run
- **River Run** (center) — Main base area. River Run Express → Lookout and Gondola are the main ways up. Upper/Mid/Lower River Run, Canyon, Roundhouse, Holiday runs
- **Christmas** (center-left) — Christmas Ridge, Christmas Bowl, Easter Bowl, Little Easter Bowl
- **Seattle Ridge** (left) — Seattle Ridge Express. Gretchen's Gold, Muffy's Medals, Christin's Silver, Leigh Lane. All green runs.
- **Bowls** (far left) — Mayday Express serves Bowl Lane → various bowls (Mayday, Lefty's, Kaitlyn's, Sigi's). Also Lookout Bowl, Sunrise Bowl, Numbers, Cold Springs Chutes

## User Context
The user is Otis, a beginner developer and a skier who knows Bald Mountain well. He's the source of truth for all run difficulties, connections, and lift access. He prefers concise communication and quick iteration.

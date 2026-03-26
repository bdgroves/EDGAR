# EDGAR
### *Early Data & Game Analytics Report*

---

> *"The first thing I figured out was — we're not trying to win the World Series by buying players. We're trying to win the World Series by buying wins. And to buy wins, we buy runs."*
> — Billy Beane, Oakland Athletics

> **Seattle does it different. Seattle does it with data.**

---

## The Argument

There are 30 teams in Major League Baseball.

Twenty-nine of them watch the same highlights, debate the same batting averages, and trust the same gut feelings their scouts have had since 1962.

**EDGAR is the thirtieth.**

The numbers have always been there. Box scores. Spray charts. The arc of a breaking ball at 3-2 in the seventh inning of a Tuesday game in April. For decades, that data lived in notebooks, then spreadsheets, then databases no one looked at twice.

Billy Beane looked. He saw something no one else was willing to see: that baseball — this slow, beautiful, infuriating game — could be *understood*. Not perfectly. Never perfectly. But better than before.

The Mariners have Ken Griffey Jr.'s swing. They have Edgar Martinez turning a 1-2 changeup into a dynasty moment. They have the long shadow of a franchise that has never won it all — and the hunger that comes with that.

They also have 2,430 regular season games of signal hiding in the noise.

**EDGAR is how we start listening.**

---

## What This Is

A Python-powered analytics dashboard tracking the Seattle Mariners — and their Triple-A affiliate, the Tacoma Rainiers — across the full 2026 season. Built on the same publicly available data that modern front offices use. Automated. Transparent. Open source.

Not a fan blog. Not a takes machine.

**A tool for understanding what's actually happening on the field.**

---

## The Stats That Matter

> *"Your goal shouldn't be to buy players. Your goal should be to buy wins."*

### 🛢️ Barrels
A batted ball hit with the right combination of exit velocity and launch angle. Not a home run — something rarer. The *intention* to hit the ball well, executed. Barrel% tells you who's squaring the ball up consistently. It's one of the strongest predictors of future offensive performance. BA doesn't tell you this. Barrel% does.

### 💥 Exit Velocity
How hard is the ball leaving the bat? 95+ mph is hard contact. 100+ is punishment. Max EV tells you ceiling. Average EV tells you floor. Together they tell you who's locked in at the plate and who's just getting lucky.

### 🎲 xBA vs BA — The Luck Index
Your batting average is a fact. Your *expected* batting average is the truth. xBA is what your BA *should* be based on exit velocity and launch angle alone. The gap between the two is luck — good or bad. A guy hitting .210 with an xBA of .290 isn't slumping. He's *due*. EDGAR tracks that gap every single day.

### 💨 Sprint Speed
Feet per second. Baseball's fastest players create havoc — stretched singles, extra bases, stolen opportunities. Speed doesn't slump. Speed doesn't age gracefully either, which is why tracking it matters.

### 🎯 Sweet Spot %
Launch angles between 8° and 32°. The window where physics is on your side. Barrels live here. Line drives live here. Pop-ups and grounders do not. A hitter with a consistently high sweet spot % isn't lucky — they've built a swing.

### ⚾ FIP
Fielding Independent Pitching. Strip away the defense. Strip away the ball-in-play luck. What does this pitcher actually *control*? Strikeouts. Walks. Home runs. FIP answers the question ERA refuses to. A pitcher with a 4.20 ERA and a 3.10 FIP is being robbed. A pitcher with a 3.10 ERA and a 4.20 FIP is being given something he hasn't earned.

### 🌀 CSW% — Called Strikes + Whiffs
The most underrated pitching stat you're not talking about. Every pitch either beats the hitter or it doesn't. CSW% measures *stuff* — pure, raw stuff — independent of what happens when the ball is put in play. High CSW% pitchers don't wait for luck. They manufacture outcomes.

---

## The Modules

```
EDGAR
├── AL West Standings       ← Where are we? Where are they?
├── Statcast Intelligence   ← Exit velo · barrels · sprint · luck index
├── Pitcher Breakdown       ← FIP · CSW% · pitch arsenal · SwStr%
└── Tacoma Rainiers         ← Who's coming? Who's ready?
```

The Tacoma module isn't an afterthought. The 2026 Mariners will be built, in part, by players who are in Cheney Stadium right now. **EDGAR watches them.**

---

## The Stack

```
pybaseball          ← Statcast · Baseball Reference · FanGraphs
mlb-statsapi        ← Live scores · MiLB · schedules · rosters
pandas              ← Because data doesn't clean itself
matplotlib          ← When numbers need to become pictures
GitHub Actions      ← Runs at 10 PM PT every night. No days off.
GitHub Pages        ← Always on. Always current.
pixi                ← Reproducible environments, no excuses
```

Data updates automatically. No manual refreshes. No stale screenshots.
The pipeline runs. The numbers update. You come back tomorrow and it's different.

---

## Get Started

```bash
git clone https://github.com/bdgroves/edgar
cd edgar
pixi install

# Pull today's data
pixi run fetch

# Build the site
pixi run build

# Push to GitHub → live at bdgroves.github.io/edgar
git push
```

Or run individual modules:
```bash
pixi run standings   # AL West standings
pixi run statcast    # Barrels, EV, sprint speed, xBA
pixi run pitchers    # FIP, CSW%, pitch mix
pixi run rainiers    # Tacoma results + prospect watch
```

---

## The Name

**EDGAR** — Early Data & Game Analytics Report.

But really: Edgar Martinez. Mariners DH. Hall of Famer. The greatest right-handed hitter of his generation, playing half his career in a pitcher's park, putting up numbers that sabermetrics eventually learned to fully appreciate long after the scouts had moved on.

He hit .312 lifetime. His career OPS+ was 147. His xwOBA, if we could reach back and calculate it, would make you understand why a generation of Seattle fans still says his name like a prayer.

The man waited. He studied. He didn't swing at bad pitches.

**Neither should we.**

---

## The Bigger Picture

Baseball has always been a game of information asymmetry. The teams with better data, better models, and better processes win more games than they should — until everyone catches up, and the advantage moves to whoever finds the next edge.

The edge right now is in the *combination*: traditional scouting wisdom informing modern metrics, human judgment layered over probabilistic models. It's not Moneyball vs. old school. That argument is over. It's how you *integrate* them.

EDGAR is one piece of that. Open source, reproducible, and built around a single team in the Pacific Northwest that has been waiting a long time for everything to click.

The math says it can click. The math doesn't know about rain in April or a bullpen that gives up three runs in the eighth.

But the math helps. It always helps.

---

## Contributing

Found a better stat? A cleaner data source? A visualization that would make the dashboard sing?

Open a pull request. EDGAR is a tool, not a monument. It should get better every week.

---

## License

MIT. Use it, fork it, build on it. Just root for the right team.

---

*Built in the Pacific Northwest. For the Pacific Northwest.*
*Let's go, M's. 🧢*

---

<div align="center">

**EDGAR** · bdgroves.github.io/edgar  
*Powered by `pybaseball` · `mlb-statsapi` · GitHub Actions*  
*Data: Baseball Savant · FanGraphs · Baseball Reference · MLB StatsAPI*

</div>

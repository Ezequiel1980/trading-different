# Trading Dashboard — Design Redesign Prompt

**Context:** Professional BTC/crypto trading dashboard. Dark theme. Single-page app (HTML/CSS/JS). Current stack: CSS variables, CSS Grid (2-col: main feed + 340px right panel), bottom slide-up analysis panel with tabs.

**Current palette:** `#0d1117` base · `#161b22` cards · `#30363d` borders · accent: green `#3fb950`, red `#f85149`, purple `#8957e5`, gold `#f0c040`

---

## Redesign Goals

Elevate from "functional dark UI" → **premium trading terminal**. Think Bloomberg Terminal meets Linear.app.

### Visual direction
- **Glassmorphism cards**: `backdrop-filter: blur(12px)` + subtle `rgba` backgrounds + `1px solid rgba(255,255,255,0.08)` borders
- **Accent glow**: key numbers (BTC price, P&L, signals) get a soft `text-shadow` or `box-shadow` in their semantic color
- **Typography hierarchy**: price = 32px 800 weight tabular-nums · section labels = 9px 700 uppercase tracked · data = 13px 500 monospace
- **Micro-animations**: price tick → 150ms color flash · pool map bars → `transition: height 0.4s cubic-bezier` · tab switch → `opacity + translateY` fade-in
- **Grid refinement**: tighten card padding to 14px · use `gap: 1px` with shared background as dividers instead of borders

### Specific components
| Component | Current | Target |
|---|---|---|
| Navbar | flat bar | frosted glass, `position:sticky`, subtle bottom border glow |
| Price header | plain number | large mono font, live tick animation, ▲/▼ colored badge |
| Section cards | flat `#161b22` | glass with inner highlight `inset 0 1px 0 rgba(255,255,255,0.06)` |
| Pool map bars | plain colored divs | gradient fills, rounded caps, hover tooltip with BTC amount |
| Bottom panel tabs | plain buttons | pill-style active tab with accent underline + icon |
| Signals | text labels | colored badge chips with dot indicator |
| Tables | flat rows | zebra with `rgba(255,255,255,0.02)` · hover row highlight |
| Buttons | flat rectangles | rounded `8px`, gradient on primary, ghost on secondary |

### Color system upgrade
```
--surface-0: #080b10
--surface-1: rgba(22,27,34,0.8)   /* glass cards */
--surface-2: rgba(33,38,45,0.6)
--border-subtle: rgba(255,255,255,0.06)
--border-accent: rgba(63,185,80,0.3)  /* green glow borders */
--glow-green: 0 0 20px rgba(63,185,80,0.15)
--glow-red:   0 0 20px rgba(248,81,73,0.15)
--glow-gold:  0 0 16px rgba(240,192,64,0.12)
```

### Do NOT change
- Layout structure (2-col grid + bottom panel)
- All JS logic / data fetching
- Element IDs and class names used by JS
- Mobile responsive breakpoints

**Output:** Full redesigned CSS block (`:root` variables + all component styles). Keep selector names identical. Add new utility classes for glow/glass effects. Optimize for < 800 lines CSS.

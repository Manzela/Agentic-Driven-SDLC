# Competitive Audit: AI Coding Agent Platforms
## Autonomous SDLC Platform Design Research

### OBJECTIVE
Extract reusable UI/UX and brand design principles from 6 closest competitors (AI coding agents + code-quality tools). Focus: how they position autonomy, trust, and verification to enterprise buyers via private-beta motions.

### RESEARCH SCOPE

**Target Competitors:**
1. Cognition / Devin — https://cognition.ai + https://devin.ai
2. Magic.dev — https://magic.dev
3. Augment Code — https://www.augmentcode.com
4. Sourcegraph (Cody/Amp) — https://sourcegraph.com
5. CodeRabbit — https://www.coderabbit.ai
6. Graphite — https://graphite.dev

**Pages to Scrape per Site:**
- Homepage (hero, positioning, value props)
- /pricing or /plans (if available)
- /features or /product (if available)
- Note nav + footer structure

### DELIVERY STRUCTURE

For EACH competitor site, produce a **STRUCTURED PROFILE** with:

1. **POSITIONING**
   - Hero headline (verbatim)
   - Subheading (verbatim)
   - Brand promise / core value
   - How they frame "autonomy" and "trust/verification"

2. **IA / NAVIGATION**
   - Top-level nav menu items (exact labels)
   - Full page set (Product, Features, Solutions, Pricing, Docs, Customers, Blog, Company, etc.)
   - Footer structure (links, company info, legal)

3. **COLOR SYSTEM**
   - Light vs. dark mode presence
   - Primary background color (hex if discoverable)
   - Accent / brand color (hex)
   - Overall palette character (e.g., "cool blues + neon accent", "dark minimal")

4. **TYPOGRAPHY**
   - Heading font (name if discoverable)
   - Body font (name if discoverable)
   - Notable treatment patterns (all-caps, monospace, serif, etc.)
   - Heavy code/terminal aesthetics usage?

5. **LAYOUT & DENSITY**
   - Container width (px if visible)
   - Product screenshots vs. abstract diagrams
   - Section rhythm (tight vs. breathing room)

6. **SIGNATURE MOTIFS** (recurring visual patterns)
   - Terminal / code demos
   - Before/after diffs
   - Agent-trace visualizations
   - Dashboards / performance charts
   - Animated product demos
   - Gradients (linear, radial, colors)
   - Other unique visual language

7. **CREDIBILITY MODULES**
   - Benchmarks cited (e.g., SWE-bench, LeetCode, GitHub stats)
   - Customer logos shown?
   - Security/SOC2 badges?
   - Testimonials or case studies?
   - Funding / backers mentioned?
   - GitHub stars or similar social proof?

8. **CTA STRATEGY**
   - Primary CTA button text (verbatim)
   - Secondary CTA text (if present)
   - CTA placement (hero, below fold, sticky header, etc.)
   - Language: "Get Started Free", "Book Demo", "Join Waitlist", "Talk to Sales"?

9. **STEAL / AVOID** (2-3 bullets for verification-first platform)
   - What design patterns should be adopted
   - What should be avoided
   - Why (specific to private-beta + regulated enterprise positioning)

### SYNTHESIS SECTION (After all 6 profiles)

**CLUSTER SYNTHESIS: How AI Coding Platforms Sell Autonomy + Trust**

Synthesize 5-8 actionable bullets covering:
- Dominant hero/demo patterns across the set
- How they position "verification" vs. "autonomy"
- Benchmark/credibility conventions (which signals work?)
- Color/typography trends
- CTA patterns (demo vs. free vs. waitlist)
- What a **proof/evidence-first platform** should adopt vs. avoid
- Specific hex colors, font families, and exact section patterns observed

### EXECUTION PLAN

**Phase 1: Scraping (firecrawl-scrape)**
- Scrape homepages: cognition.ai, devin.ai, magic.dev, augmentcode.com, sourcegraph.com, coderabbit.ai, graphite.dev
- Attempt /pricing, /features, /product pages where cheap
- Save markdown to .firecrawl/ directory

**Phase 2: Analysis**
- Read each page; extract positioning, nav, colors (via CSS inspection if possible), fonts
- Catalog CTAs, credentials, signature motifs
- Note tone: hype vs. technical vs. enterprise

**Phase 3: Synthesis**
- Cluster findings across all 6
- Identify dominant patterns (color palettes, hero structures, benchmark strategies)
- Draft 5-8 actionable takeaways for a verification-first, enterprise-privacy SDLC platform
- Return findings as final message (no files written)

### SUCCESS CRITERIA
- Each profile filled in completely with specific hex colors, font names, verbatim CTAs
- Synthesis identifies repeatable patterns (e.g., "5/6 show SWE-bench", "4/6 use neon accent on dark bg")
- Actionable recommendations specific to proof-driven, deterministic-verification positioning
- Output is readable and directly usable for design-system / brand-strategy work

---

**Status:** Ready to execute on approval.

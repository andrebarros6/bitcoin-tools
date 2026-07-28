# Design Guidelines — bitcoinpt

## Archetype

**Editorial Minimalism + Bold & Opinionated (hybrid).** Structural restraint from Editorial Minimalism (near-black background, borders-only depth, no decoration) carries one confident, sparingly-used accent color from Bold & Opinionated (Bitcoin orange, `#f7931a`). The user arrives anxious about money and needs the page to read as precise and evidence-led, not hyped — cold structure plus one deliberate color signal does that better than either archetype alone.

## Design Tokens

```css
:root {
  --color-bg: #0a0a0a;
  --color-surface: #111111;
  --color-surface-raised: #1a1a1a;
  --color-border: rgba(255,255,255,0.08);
  --color-border-strong: rgba(255,255,255,0.16);
  --color-text: #ededed;
  --color-text-secondary: #a1a1a1;
  --color-text-tertiary: #6b6b6b;
  --color-accent: #f7931a;        /* real Bitcoin brand orange, not an arbitrary pick */
  --color-accent-hover: #e07f0e;
  --color-accent-muted: rgba(247,147,26,0.1);
  --color-positive: #22c55e;
  --color-negative: #ef4444;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  /* shadows: none — borders only */
}
```

Type scale (4 sizes, 1.25 ratio subset): 14px body/UI, 20px card titles, 32–40px hero headline, weight hierarchy (400/500/600/700) does most of the lifting.

## Design Principles

1. **Orange appears in exactly 3 places**: the hero's key stat, the live tool's primary CTA, the "live" status dot. Nowhere else — it stays a signal, not decoration.
2. **No shadows, ever.** Depth comes from `--color-border` only. Matches the "ledger, not app" feel.
3. **Numbers lead, adjectives don't.** Copy states the percentage/price change; it does not editorialize about how alarming it is.
4. **Card grid uses `auto-fill, minmax(280px, 1fr)`**, never a fixed 3-column — future tools slot in without a layout rewrite.
5. **"Coming soon" states are flat, not apologetic.** "Em breve" / "Dados em preparação" — no "estamos a trabalhar arduamente."
6. **No YC-template sections.** No testimonials (no real users yet — fabricating quotes breaks the no-hype voice), no pricing (free tools), no FAQ (no real repeated questions yet), no logos.
7. **Data-source footer replaces social proof.** Naming CoinGecko/Idealista/DECO PROTESTE is the credibility signal this audience actually wants.
8. **"tu" form throughout, no mixing with "você".**
9. **System-ui font stack** — no licensed display font needed for a 1-page hub; the restraint itself is the personality.

## Copy Voice

**Attributes:**
- States the number, not the feeling about the number.
- Never uses exclamation marks or hype verbs ("descobre," "revoluciona").
- Names the comparison directly, lets the reader draw the conclusion.
- Uses "tu" form consistently — addresses someone checking real numbers, not a customer being sold to.
- Domain terms (PPR, cabaz alimentar) used correctly, without hand-holding footnotes.

**Banned phrases:** Elevate, Streamline, Empower, Unlock, Seamless, Revolutionary, Transform, Supercharge, Leverage, Synergy, Game-changer, "At the end of the day," "In today's fast-paced world," "Delve," "Robust/comprehensive solution," "Simple, powerful, [third thing]" tricolons, "Take your X to the next level," "It's important to note that," "Potencialize," "De forma transparente," "Na vanguarda," "Solução completa," "Descobre" as a CTA verb, "Revolucionário," any exclamation marks.

**Preferred moves:** Short declarative sentences. Lead with the number. Flat, unapologetic "coming soon" states.

## Microcopy

1. Primary CTA (live tool): **"Ver os dados"**
2. Secondary/disabled CTA (coming soon): **"Em breve"**
3. Hero subheadline: **"O euro perde poder de compra todos os anos. Comparamos com Bitcoin — em imóveis, no cabaz alimentar, e nos PPR."**
4. Card description (imob): **"O preço do m² em Portugal, em euros e em Bitcoin, desde 2015."**
5. Card description (cabaz): **"O custo do cabaz alimentar português, em euros e em Bitcoin."**
6. Card description (PPR): **"O PPR existe para proteger a tua reforma da inflação. Compara o retorno com o de Bitcoin."**
7. Coming-soon microcopy under disabled card: **"Dados em preparação."**
8. Footer/data note: **"Dados atualizados diariamente via CoinGecko, Idealista e DECO PROTESTE."**
9. Loading state (if added later): **"A carregar dados."**
10. Section label above the 3 cards: **"As ferramentas"**

## IA / Flow

Single-page hub, no navigation beyond the 3 cards:

1. **Hero** — the problem, stated bluntly with a real claim. Exists because the anxious user needs their pain named accurately before anything else.
2. **3-card tool grid** — name, one-line description, live/coming-soon status, single CTA per card. No intermediate "how it works" section; each tool explains itself once opened.
3. **Data-source footer line** — replaces testimonials/social proof with source credibility.
4. **Link back to barrosbuilds.com** — minimal, since this is one project among several on the parent site.

Rejected: features grid (3 tools already are the "features"), testimonials (no real users yet), pricing (free), FAQ (no real questions yet), "how it works" 3-step explainer (mechanism shown inside each tool's own chart).

## Non-negotiables

- Static HTML/CSS only — no Next.js/shadcn, matches the Streamlit deploy pattern of the sibling apps (imob, cabaz).
- PT-PT copy throughout.
- At launch: 1 tool live (imob), 2 marked "coming soon" (cabaz, PPR).

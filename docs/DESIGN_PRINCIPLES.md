# EuroSetu Design Principles

The public site, the demo and the pilot dashboard all read as **one regulatory system**.
Anything that makes the product look like a growth-stage SaaS landing page is a defect.

Four principles govern every change to `app/static/*`.

## 1. Regulatory

The interface should look like an instrument, not a brochure.

- **One restrained radius scale.** No ad-hoc values. Every corner comes from a token:

  | Token | Value | Applies to |
  |---|---|---|
  | `--radius-chip` | `8px` | tags, proof chips, status pills, banners, notes |
  | `--radius-btn` | `10px` | buttons, inputs, selects |
  | `--radius` | `16px` | cards, panels, terminal, glass surfaces |
  | `--radius-panel` | `18px` | large grouped containers (e.g. pricing table) |

- **No pill shapes.** `border-radius: 999px` is reserved for genuinely circular
  elements (numeric step counters). Status chips are rounded rectangles.
- **No decorative gradients, glows or blurs on content.** Depth is expressed with a
  1px hairline border and, at most, the shared `--shadow`.
- **One accent.** `--green` for emphasis, `--red` for blocked, `--amber` for caution.
  Nothing else competes.

## 2. Trustworthy

The chrome never lies about where you are, and it never hides the disclaimer.

- **Persistent header.** `nav` / `.topnav` is `position: sticky; top: 0` with an opaque
  backdrop. You can always reach Platform, Services, Pricing and the demo CTA.
- **Terminal footer.** `footer` is a normal-flow dark ink assurance bar at the
  document end. It is only seen when scrolled all the way down — it never
  overlays content mid-page.
- **Sticky header, static footer.** Only the header is sticky, so no content is ever
  trapped underneath chrome at the end of a page.
- **Anchor-aware scrolling.** `scroll-padding-top: calc(var(--nav-h) + 20px)` keeps
  in-page anchors clear of the sticky header.

## 3. Professional

Restraint reads as competence.

- Hairline borders (`--line`) instead of heavy dividers.
- Elevation is earned: only `.featured` and primary surfaces carry `--shadow`.
- Type does the hierarchy work — `clamp()` display sizes, tight letter-spacing on
  headings, uppercase micro-labels for eyebrows and tags.
- Tabular figures for money and quantities so columns align.

## 4. Audit-grade

Trust is also an accessibility property.

- Full `:focus-visible` outline (`2px solid var(--green)`, 2px offset) on all
  interactive elements. Never remove focus styling.
- Never rely on colour alone — pair `--red` / `--green` with a glyph or label.
- Disclaimer and methodology copy is always visible, verbatim, and never truncated by
  layout. Shortening it for aesthetics is not an option.
- Copy avoids hype adjectives. State what the system does, what it does not do, and
  what the number means.

## Layout contract

Content is constrained to `1180px` and centred. Sticky chrome aligns to that same grid
using the shared gutter token:

```css
--nav-h: 68px;
--gutter: max(28px, calc(50% - 562px)); /* 1180 / 2 - 28 = 562 */
```

Use `padding: 0 var(--gutter)` on full-bleed bars so their contents line up exactly with
`main`. When changing the content width, update `--gutter` in both `public.css` and
`demo.css`.

## Where this lives

| File | Scope |
|---|---|
| `app/static/public.css` | Public marketing site (`index.html`) |
| `app/static/demo.css` | Demo (`demo.html`) and pilot (`pilot.html`) |
| `app/static/pilot.html` | Inline `<style>` uses the tokens from `demo.css` — no hard-coded radii |

Both stylesheets declare the same token names. If you add a radius, add it to both.

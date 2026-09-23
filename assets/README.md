# Brand assets

| File | Use |
| --- | --- |
| `maestro-mark-flat.svg` | Master mark, one color (`#B7410E`); derive every other version from it |
| `maestro-mark-dark.svg` | The mark on dark with the glowing star; reference image for renders |
| `avatar.jpg` | Organization picture, uploaded in Organization settings, Profile (web UI only) |

The banner and the pillar icons live in [`../profile/`](../profile/), next to the
page that shows them.

## Mark

A monogram M of five forged nodes joined by straight bars, under a four-point
north star glowing between the peaks, inside a ring with four compass ticks. M is
Maestro; the star is the Northstar, never reached; the four points and ticks are
the four pillars; forged copper is Rust.

It reads at 32 px, works in one flat color, and stays clear of the Rust
Foundation logo: no letter R, no gear teeth.

## Palette

| Name | Hex | Use |
| --- | --- | --- |
| Forge Black | `#0E0B09` | Backgrounds |
| Oxide | `#2A1F1A` | Surfaces |
| Rust Copper | `#B7410E` | The mark, strokes |
| Burnished Brass | `#D9A066` | Highlights on copper |
| Molten Ember | `#FF6A1A` | The north star and one highlight per image |
| Vector Steel | `#5E7383` | Data, KPIs, quiet details |
| Bone | `#F2E8DC` | Text on dark |

## Type

- Display: Barlow Condensed, bold capitals.
- Technical: JetBrains Mono.

## Words

- Tagline: **Never reached. Always pursued.**
- Descriptor: **Automate the guardrails: faster, better, more maintainable, more
  secure.**
- Organization description (Organization settings, Profile): "Automated
  guardrails for faster, better, more maintainable and more secure code. Our
  Northstar: never reached, always pursued."
- Every claim is one a KPI in `rust-workflows`'
  [northstar.md](https://github.com/Orchestration-Maestro/rust-workflows/blob/main/docs/standards/northstar.md)
  backs.

## Icons

Drawn in code: a 32 px Forge Black tile (radius 7) holding a 24 px grid, 2 px
`#C8743A` stroke with round caps and joins, and exactly one Molten Ember dot.

## Regenerating artwork

Artwork is generated without text; titles and taglines are set in HTML so the
spelling is exact. FLUX takes no negative prompt, so each prompt describes only
what belongs in the frame.

### Avatar

1024 x 1024, with `maestro-mark-dark.svg` as the reference image so the geometry
stays exact.

```text
Transform the flat emblem in the reference image into a premium 3D forged-metal
app icon, keeping its exact geometry, proportions and position: the slim circular
ring with four short tick marks at north, east, south and west, the five round
nodes joined by straight bars that form the letter M, and the four-pointed north
star floating above the M between its two peaks. The ring, ticks, bars and nodes
are burnished copper shading from rust copper (#B7410E) to warm brass (#D9A066),
with a light rust patina and a hammered forge texture; the north star is glowing
molten metal in molten ember orange (#FF6A1A) with a white-hot centre, its warm
glow contained inside the ring. Deep forge-black (#0E0B09) background with a
faint warm vignette. Centered, bold silhouette, crisp edges, soft rim light from
the upper left, premium 3D product render, studio lighting; the emblem is the
only object in the frame.
```

### Banner

2560 x 1024 artwork for `profile/banner.jpg`; a 1280 x 640 crop serves as a
repository's social preview.

```text
Cinematic ultra-wide key art of a vast, dark, cathedral-scale foundry hall built
from rust-stained iron beams and riveted steel girders. High in the right half of
the frame, through a round opening in the roof, a single brilliant four-pointed
north star shines in a deep night sky: long vertical rays, shorter horizontal
rays, a white-hot centre fading into molten ember orange (#FF6A1A). Below it, two
long forged-iron guardrails run in perspective from the lower right foreground
toward the distant light, lining a narrow walkway of worn steel plates that leads
toward the star; the rails catch warm rim light in burnished rust copper
(#B7410E). Faint points of cool blued-steel light (#5E7383) hang in the air like
distant stars; a few embers rise through volumetric haze. The left 40 percent of
the frame is calm, deep forge-black (#0E0B09) shadow holding only soft haze and
the faint silhouettes of distant beams, a wide empty space for a title. The
palette stays within forge black, oxide brown (#2A1F1A), rust copper, molten
ember and a touch of blued steel. Photographic realism, 35mm lens, shallow depth
of field, AAA game key art, ultra-detailed metal materials, dramatic cinematic
lighting. The scene holds only architecture, metal and light.
```

Overlay on the dark left side: the mark and "AUTOMATED GUARDRAILS · RUST", the
title "ORCHESTRATION / MAESTRO", the tagline with "Always pursued." in Molten
Ember, and the footer "SPEED · QUALITY · MAINTAINABILITY · SECURITY".

# Phase 3 — heritage-register classification

Register: Museovirasto, Kulttuuriympariston paikkatietoaineistot WFS
(`geoserver.museovirasto.fi`). Match distance 50 m.

| window | candidates | known_military | known_other | undocumented |
| --- | ---: | ---: | ---: | ---: |
| miehikkala | 21 | 19 | 0 | 2 |
| salpa-virolahti-c10 | 14 | 13 | 0 | 1 |
| control-forest-keski | 41 | 0 | 0 | 41 |
| control-farmland-pohjanmaa | 32 | 0 | 0 | 32 |
| control-forest-hame | 19 | 0 | 0 | 19 |

## Reading these numbers

The two Salpa Line windows are **fully documented ground**, so a working filter
should suppress nearly everything there — and does (19/21 and 13/14). The three
control windows contain nothing the register knows about, so a working filter
should suppress nothing — and does (0 of 92).

That is the filter behaving correctly in both directions, which is the point of
running both.

## What "known" actually means

**Within 50 m of a registered site's geometry**, and much of that geometry is
broad *area* polygons covering a whole fortification zone rather than individual
structures. At Miehikkälä the "Laajanpohja" and "Salpalinja-museo" polygons
cover the entire site, so even the drainage false positives inside them come
back `known_military`.

This is the right behaviour for the stated goal — skew output toward genuinely
undocumented finds — but it is *not* per-feature identification. A candidate
marked `known_military` means "inside an area somebody has already surveyed",
not "this exact feature is individually recorded".

## The honest limit

The filter only removes noise where things are already recorded. Over
unsurveyed terrain it passes everything through, which is exactly what the three
controls show. Its value is negative evidence: it tells you which candidates are
*not* already accounted for. It does nothing about the forest-ditch false
positives documented in `../phase-2/manual-review.md`, because those are not in
any register either.

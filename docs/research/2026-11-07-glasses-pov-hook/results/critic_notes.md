# Completeness critic, loop 2 (2026-11-07)

Read: final_v2.json, baseline_v2(.json/_notes), judge_*_notes, all 5 experiments/*/NOTES.md, integrate_notes.md,
refute_hook-in-data_notes.md, refute_provenance_notes.md, showcase_notes.md, make_showcase.py, track_v2.py clean_series,
showcase frames throw9_192142_pin, throw9_192142_mid, throw1_185121_pin, throw5_190115_pin (Read), overlays
final__192636, final__191913 (Read). Re-computed: showcase dot selection (make_showcase.trim on the shipped tracks), the
pin-triangle depth in base(), and clean_series extended to the observed contact on 192142/192636. Nothing shipped edited.

## Headline
The tracks are tracker output, and the hook in them comes from the raw boards. But **the video does not show the
fix-pass drawing.** `make_showcase.py` draws per-frame `ft` filtered by per-frame `zone`, and stops at pin_hit+2.
`showcase_notes.md` says "constant-speed depth", which is false. The overlays JPEGs do use ft_cv; the mp4 does not. On
the two throws with the biggest hooks, the video keeps playing to pin_hit+15. The ball visibly carries on to the head
pin, but the panel has already printed "entry board 11.0 / 13.8". The truth at the observed contact is 21.65 / 20.55.

## (a) Is the rendered trace tracker output?  Yes, with declared inputs
- The boards come from track_v2: the audit hook made 155-165 opens per stem and opened 0 truth/label/holdout paths, and
  the canary held (cuts.json and the L1 track appear in every log). A provenance re-run of 192636 was byte-identical.
  lane_top_down.board equals boards{} (the med3 of boards_raw) on 10/10 stems. No path_fit is drawn.
- Inputs that nothing detects: release_frame and pin_hit_frame from cuts.json. Per the loop-1 README they are hand
  labels: "09-19 truth" on 3 dev stems and "visual read" on the other 7. Both depth models anchor 60 ft at the input
  pin_hit: per-frame ft is rescaled so pin_hit = 60, and ft_cv = 60 (f-rel)/(pin-rel). So every feet value is prior,
  including "min board 6.3 at 47 ft" and "pins (60 ft)". The ball stage also stops at pin_hit+4 by construction.
- Loop-2 truth says the input pin_hit is 10 frames early on 192142 (contact f490) and 6 frames early on 192636 (f463).
  On 191913 the truth's own headpin-row frame is 17 frames before the cut pin_hit. No instrument measured where the
  pins are in time on the other 7 throws.

## (b) Hook in the data, per throw (last-15-ft direction; raw = slope x12 of boards_raw over pin-11..pin; fit = path_fit_diag, NOT drawn)
| stem | split | raw | fit (diag) | truth | verdict |
|---|---|---|---|---|---|
| 185121 | dev | flat +0.6 | line | flat +0.2 | agree, no hook |
| 185331 | dev | rises +3.9 | line+hook 3.1 | rises +2.5 | agree |
| 185454 | dev | falls -1.2 | line | falls -0.9 | agree, no hook |
| 185645 | dev | flat -0.4 | line | flat -0.1 | agree |
| 190115 | dev | flat -0.5 | line | flat -0.6 | agree |
| 191253 | HO | rises +3.0 | line+hook 2.7 | rises +3.5 (marginal) | agree, but loop-1 truth called this throw monotonic (entry 6.5 vs 9.47) |
| 191820 | HO | flat -0.15 after the fix (it was +9.7 from the f463 artefact) | line | +2.57 inside the gutter | direction_ok False. A trend in the gutter is meaningless |
| 191913 | HO | rises +3.6 | line+hook 3.5 | rises +2.8 | agree in sign. The track turns at about f496 vs truth f503 and reads 1.3-3 boards high over f501-509 (lane edge, not the ball) |
| 192142 | HO | rises +5.3 | line+hook 4.9 | rises +4.5, then +11 more to contact | sign agrees. The magnitude is truncated by the input pin_hit |
| 192636 | HO | rises +6.0 | line+hook 6.5 | rises +6.1, then +6 more to contact | same |
No drawn hook comes from a fit or a prior. Raw past pin_hit already carries on hooking: 192142 f481-484 reads
13.2-14.9 (truth 13.35/15.14), and 192636 f458-461 reads 14.7-18.2 (truth 15.99/18.33). That is in the JSON but is
trimmed from the video.

## (c) Numbers that could not have come out otherwise
- Dev means (path_far 0.53, entry 0.47, hook 0.54, direction 100 %): the refine thresholds were tuned on the same dev far
  frames the scorer reads. The edge+smooth3 variant and smoothing window were chosen after reading the dev table. Only
  185331 has a dev truth trend of 1 board or more, so the dev direction score is 1 informative stem plus 3 coin flips.
- `dev_reproduced=true` on all 5 judges: one stem (185331) re-run, giving byte-identical output. This is a deterministic
  re-run, not reproduction. The same applies to the provenance re-run of 192636.
- Holdout v2 means: the stages were picked from the judges' holdout rows (the leave-one-out flips show this), and the
  clean_series rule was written after the 191820 holdout row was seen. So 191820 path_err_far 7.98 -> 2.26, and with
  it holdout path_far 2.26 -> 1.11, is post-hoc.
- Holdout far recall 80 -> 100 is one stem (191913). Loop 1 was already 100 on 4/5 at a 16-20 px tolerance.
- "drawing trims nothing on all 10" is by construction: clean_series removed the only frame the trim used to catch.
- px and board agreement is with a shared instrument: the purple HSV ball and wood->gutter edge lines in both truth and
  tracker. v1 (SAM) is scored on the instrument v2 copies.
- Entry vs entry_at_cut_pin_hit (0.17 / 0.21 on 192142/192636): truth and tracker both read the same input frame.
- Feet readouts (60 ft at pin_hit, the breakpoint ft) are fixed by the anchor, not measured.

## (d) Weakest numbers
1. Holdout entry_err 3.98 and hook_err 4.53 mix two truth conventions. 192142/192636 are scored at the observed contact
   (10.65 / 6.75); 191253/191913/191820 at the cut pin_hit. On the cut convention the holdout entry mean is about 0.57;
   on the contact convention, nobody has measured the other three throws.
2. Truth moved between loops. Loop-1 vs loop-2 holdout entries are 6.5/9.47 (191253), 10.0/21.65 (192142),
   12.5/20.55 (192636) and 7.0/10.1 (191913). So v1's "8.04 -> 3.98" entry before/after is partly a change of truth
   convention, not of the tracker.
3. Holdout direction_ok 80 % (n=5): 191820's False is a gutter-ball trend, and flat-truth throws are coin flips.
4. Holdout path_err_far 1.11 and far px 1.9 sit below the truth's own 1-2 board floor (pin ruler vs edge profile). They
   are post-selection, and 1.11 depends on the post-hoc rule.
5. The closing card shows n=9 (v1) against n=10 (v2), and v2 includes 185121 at entry 0.03. Like for like on n=9, v2
   entry is 2.46 (not 2.22) and path_far 0.84. 5 of the 10 throws are in-sample dev.
6. The lane pick flips to the loop-1 engine lane on 3 of 5 holdout leave-outs. The ball+lane pair was never judged
   together before integration, which ran on the already-seen holdout.

## (e) Showcase defects a bowler notices (must fix)
1. 192142 (throw 9) and 192636 (throw 10): the panel stops and reads "entry board 11.0 / 13.8" while the video runs to
   pin_hit+15 and shows the ball carrying across to the head pin (truth contact 21.65 / 20.55). The biggest part of the
   hook is cut off.
2. The depth axis is per-frame ft, not ft_cv (make_showcase.py `dots = (k, bd2[k], td2[k]['ft'])`, plus the zone
   filter). The line doubles back in depth 1-12 times per throw: 191913 12, 185331 9, 192636 8, 191820 7. 4-33 points
   per throw are more than 5 ft off ft_cv. 185331's pin_hit f358 (zone past_pins, 64.3 ft) and 185645's f299 are
   dropped from the line, then f359-360 are drawn. This is the fix the integrator applied to the JPEGs only.
3. A vertical "board ruler" (1 at the pins, 39 at the foul line) sits beside a panel whose vertical axis is feet. The
   magenta current-board arrow and the green entry tick land at a height that reads as a distance (board 11 at about
   44 ft).
4. The pin triangle is drawn 3 ft short: head pin at 57.0 ft, back row at 59.6 ft (real: 60 and 62.6). So the ring "at
   60 ft" sits past the back row, among the 6/10 pins.
5. 191820 (gutter ball) reads "entry board -1.7" and "min board -2.4 at 46 ft". It should say gutter.
6. "min board X at Y ft" uses per-frame ft. It disagrees with the overlay's constant-speed depth by up to 9 ft (191820
   46 vs 55, 192636 51 vs 45, 185331 51 vs 46).
7. Near-foul-line zigzag: 1.5-2 board jumps near the arrows on 190115 and 192142 draw a Z.
8. The first 10 s are all in-sample dev throws (holdout starts at 15 s). The closing card says "10 throws, vs truth"
   with no holdout split, no shared-instrument line and mismatched n.

## (f) Gaps and how to close them
1. Contact frame is a hand input and is wrong by 6-10 frames on 2/5 holdout throws. Close it by detecting contact from
   pin-deck motion (frame differencing in the rack box after camera compensation; first pin lean). Score window_err
   against truth observed_pin_contact_frame (present on 192142/192636; label the other 8). Then re-anchor 60 ft at
   contact.
2. The ball stage stops at pin_hit+4. Extend it to the detected contact+2. **clean_series must change first.**
   Extended to contact, its Theil-Sen reference (192142 slope 0.40/frame) predicts 14.46 at f490 where truth is 22.15
   (deviation 7.69 > 6). On 192636 it predicts 14.67 at f463 vs truth 21.18 (6.51 > 6). So the shipped rule would
   reject the real hook end. Make it reject only on jumps between frames (e.g. a step of more than 6 boards from the
   previous kept frame), and test it on 191820 f463-467 and on a synthetic hook.
3. Truth convention: re-read every throw's entry at the observed contact (pin motion), keep the cut-frame reads beside
   it, and re-score v1 and v2 on one convention.
4. Showcase: rebuild from ft_cv (or contact-anchored depth), select frames by f, draw past the cut pin_hit to contact,
   delete the vertical ruler, move the pins to 60-62.6 ft, label gutter balls, and put the holdout-only numbers and
   caveats on the closing card. Read every saved frame, not 3 of 9.
5. Fresh holdout: all 10 throws have now been seen. Record a new glasses session with at least 3 strong hookers and 2
   straight balls, and freeze truth before running track_v2.
6. Independent truth: a second instrument that does not use HSV purple or wood edges, e.g. a pin-ruler-only read, or a
   fixed second camera on the next session.
7. Path stage (the bowling-sense line): not built. A path fit is only safe after gaps 1-2. Physics-smoother drew a
   7.4-board hook on a gutter ball.
8. Not standalone: v2 reads the loop-1 sam2-video track from disk (wall 108-131 s per throw), and nothing landed in the
   pov-engine branch.
9. 191913's turn is 7 frames early with the far end 1.3-3 boards high (per-frame lane edge at the deck). The near end
   wobbles from per-frame quad jitter, and a lane-relative temporal filter is untried.

## (g) The question Tom asks first
"On throw 9 I can see the ball keep hooking into the head pin. Why does the line stop short of the pins and say entry
board 11?"

# Lane: getting it made (frames, enclosure, circuit boards, assembly)

Written 2026-11-14 by a research agent. Status line at the bottom of the file says whether this write-up is complete.

## 0. Scope, method and how to read the sourcing

**Question.** How does one person in the United States, a software engineer with no circuit-board or
computer-aided design (CAD) experience, get a physical camera-glasses prototype manufactured: frames, enclosure,
printed circuit boards (PCBs) and assembly? What does each route cost in dollars and weeks for 1 to 3 units, and for
scale at 50 to 100 units?

**Not in this lane.** Choosing the image sensor, the processor or the firmware. This file only uses the envelope from
`REQUIREMENTS.md`: at least 2 hours awake on the face, 15 minutes of recording, a lithium cell beside the head, a
visible recording light, a camera that keeps at least the Meta glasses' pixels per degree, and a phone-only setup.

**Sourcing legend.** Every price, minimum order, lead time and software term carries a URL, the access date
(all 2026-11-14) and a short quote. Each is tagged:

- **[page]** the agent opened the page itself (through a fetch tool that summarises the page with a small model; where
  the quote is the tool's paraphrase and not verbatim text, it says "paraphrase").
- **[snippet]** only the search-result snippet was seen; the page was not opened. The quoted words are then the
  search tool's extract or summary of the page, and the agent matched each extract to the URL it appeared to come
  from; treat both the wording and the attribution as approximate until the page is opened.
- **(from memory, unverified)** the agent's training knowledge, which is older than this market. Treat as a lead.

Claims that could not be sourced are collected under "Unsourced" at the end; they are not presented as fact.

**Cost framing.** At 1 to 3 units the one-off design labour (drawing the frame, laying out the board) is far larger
than the fabrication bill. Each route below therefore separates **one-off cost** from **per-unit cost**. The budget in
`REQUIREMENTS.md` section 6 is ambiguous (one unit, or the whole effort), so both are shown.

## 1. Headline for a reader in a hurry

1. **One to three units is a "print it and hand-assemble it" job, not a manufacturing job.** Every route that involves
   a design house, a contract manufacturer or injection-mould tooling starts at five figures (sections 5 and 2.4). The
   routes that fit about $1,000 are: a clip-on module on ordinary frames, then a nylon 3D-printed frame, both carrying
   off-the-shelf boards.
2. **Fabrication is cheap; design labour and import duty are the real costs.** A 5-piece flexible board is about $25
   and a printed nylon frame is tens of dollars, but a hired board designer is $2,000 to $10,000+ and flexible or
   assembled boards from China now carry duty that vendor blogs put at 25 % to 37.5 % (they disagree), with no
   low-value exemption (section 6.2).
3. **The custom circuit board is the stage that breaks the budget and should come last**, only after a clip-on rig has
   proved that the chosen camera beats the Meta glasses on pixels at the far end of the lane.
4. **Do not cross the hinge in a first prototype.** Keep camera, board and cell on one non-folding temple (or in a
   clip-on pod). A cable through a folding hinge is the classic failure point in commercial glasses (section 2.5).

## 2. (a) Frames and enclosure, least custom to most custom

### 2.1 The four mechanical routes

| Route | What it is | One-off cost | Per-unit cost | Lead time | Notes |
|---|---|---|---|---|---|
| A1. Clip-on pod on ordinary frames | A printed pod (camera, board, cell) that clips or straps to the temple of the glasses the wearer already owns | $0 if he draws it himself; see 3.3 if hired | About $3 to $30 per printed pod from a service (derived, see 2.2) | 3 to 5 working days to print, plus shipping | Keeps his existing prescription lenses. Precedent: the open-source omiGlass kit is exactly this kind of printed mount |
| A2. Modified off-the-shelf frames | Buy thick-templed frames and cut or hollow a temple, or replace one temple with a printed one on the original hinge | $0 to a few hundred dollars of spoiled frames | Frame price plus a printed temple | 1 to 2 weeks | Fiddly hand work; hinge screw patterns are not standard across brands (from memory, unverified) |
| A3. Fully 3D-printed frame | Front and two temples printed in nylon, standard metal hinges screwed or heat-set in | $0 self-drawn, or $1,000 to $8,000 hired (3.3) | About $20 to $110 per frame set per iteration (2.2) | 4 to 7 working days per iteration plus shipping | The sensible ceiling for 1 to 100 units |
| A4. Machined or injection-moulded | Computer-controlled machining of acetate, or moulded plastic | Tooling $1,000 to $12,000 **per moulded part**, 3 to 5 parts in a pair of glasses (2.4) | $0.60 to $4 per moulded part | 4 to 10 weeks (from memory, unverified) | Only makes sense at several hundred units and a frozen design |

Sources for the omiGlass precedent: https://docs.omi.me/doc/hardware/omiGlass **[page]**, accessed 2026-11-14:
"Print the glasses mount case using the STL files in the `hardware` folder"; "Mount all components into the 3D
printed case and attach hinges"; hinges are "Standard glasses hinges"; power is "6x 150mAh batteries" plus
"1x 250mAh battery"; the board is a "XIAO ESP32 S3 Sense". The page itself warns to "treat battery life and stability
as unvalidated until you test your own build". (That board's camera is far below the Meta baseline; it is cited here
as a mechanical precedent only.)

### 2.2 3D-printing processes, materials and price examples

**Which process on the face.** Powder-bed nylon, either Multi Jet Fusion (MJF, HP's process) or selective laser
sintering (SLS), in polyamide 12 (PA12), is what commercial 3D-printed eyewear uses: it is tough, slightly flexible,
light, and can be dyed black and smoothed. Standard photopolymer resin (stereolithography, SLA) gives a nicer surface
but is brittle at hinge and temple thickness and uncured resin is a skin irritant, so use it for look-and-feel models
only (process comparison from memory, unverified; the eyewear-in-PA12 claim is supported by the service listings
below). Desktop filament printing (fused deposition, FDM) is fine for the stage-1 clip-on pod.

| Service | Price evidence | Lead time evidence | Source |
|---|---|---|---|
| JLC3DP (China) | MJF PA12 material rate cut "from $0.35/g to $0.275/g, excluding tax" (August 2025 notice); MJF and SLS nylon listed "from $1.00"; site-wide "starting price is from 0.3$/pcs" | "Build time of roughly 72 hours" for MJF PA12; SLS nylon 3-day build | https://jlc3dp.com/news/drastic-material-price-cuts-and-adjusted-post-processing-service-fees , https://jlc3dp.com/help/article/pa12-hp-nylon , https://jlc3dp.com/ **[snippet]** 2026-11-14 |
| FacFox (China) | MJF PA12 glasses frames (thin-framed, bold-framed, full-colour) listed in a "$1-100" price band (a placeholder band, not a quote) | "4 workdays" and "5 workdays" | https://facfox.com/case/consumer-case/mjf-3d-printed-nylon-pa-12-thin-framed-glasses-frame-dyed-black-sand-blasted/ **[snippet]** 2026-11-14 |
| Craftcloud / Materialise / Xometry (marketplaces, US delivery) | An All3DP comparison of one small polished PA12 job: Craftcloud $62.65 (2 to 3 days), Materialise OnSite $83.94 (6 days), Xometry $106.53 (3 days). Date of the quotes unclear | as listed | https://all3dp.com/1/mjf-3d-printing-price-comparison-charts-5-sample-projects/ **[snippet]** 2026-11-14 |
| Xometry (US) | quote only | MJF "lead time: 3 days"; "free shipping on all 3D printing orders originating in the US" | https://www.xometry.com/capabilities/3d-printing-service/hp-multi-jet-fusion/ **[snippet]** 2026-11-14 |
| Shapeways | quote only. Relaunched in 2025 after its 2024 bankruptcy; MJF and SLS pricing restructured and "publicly accessible"; a move to a new Eindhoven building expected "in late 2026" | not found | https://www.fabbaloo.com/news/revived-shapeways-prepares-for-future-growth-with-new-high-capacity-site **[snippet]** 2026-11-14 |
| PCBWay 3D printing | quote only; no public price found in this run | not found | see Unsourced |
| US job shop (SSG MFG) | "$37.50 per part budgetary price for a PA12 housing at 25 pieces" | 3 to 7 days | https://ssgmfg.com/processes/additive-manufacturing/nylon-pa12 **[snippet]** 2026-11-14 |

**Derived price for this job (agent arithmetic, not a quote).** A nylon frame set weighs roughly 15 to 25 g and a
clip-on pod 5 to 10 g. At JLC3DP's published $0.275 per gram that is about $4 to $7 of material rate for a frame and
$1.50 to $3 for a pod, before minimum charges, dyeing, shipping (typically more than the part) and duty. The US
marketplace example ($63 to $107 for one small polished PA12 job) is the realistic upper end. Hence "about $3 to $30"
per pod and "about $20 to $110" per frame set per iteration. Plan on 3 to 5 iterations before one fits.
No instant-quote calculator was used (they need a file upload), so these are not quotes.

### 2.3 Weight and comfort targets

- Ray-Ban Meta weight: Target lists "Weight: 49 Grams" (https://www.target.com/p/-/A-94901811); Currys lists
  "Frame: 53 g, Charging case: 133 g"
  (https://www.currys.co.uk/products/rayban-meta-wayfarer-gen-2-glasses-matte-black-with-gradient-graphite-lenses-10291936.html);
  Android Central says Generation 2 weighs "52g on average" against "around 48g" for Generation 1
  (https://androidcentral.com/wearables/ray-ban-meta-gen-2); EyeBuyDirect lists 41 g for a frame "without the lenses"
  (https://www.eyebuydirect.com/-glasses/frames/ray-ban-meta-wayfarer-gen-2-shiny-transparent-gray-m-31611).
  All **[snippet]**, 2026-11-14. No official Meta specification page was read.
- **Target for the prototype:** total on the face at or under about 55 g, which is what he already wears for a
  65-minute session. Ordinary prescription glasses are roughly 25 to 40 g (from memory, unverified), which leaves
  about 15 to 25 g for a clip-on pod including its cell. Put the cell on the opposite temple or behind the ear if the
  pod alone exceeds about 15 g, because a one-sided load makes the frame slide and twists the camera's horizon
  (comfort thresholds are agent judgement, not sourced).
- Session envelope from `REQUIREMENTS.md` section 4: 2 hours awake, 15 minutes recording. The omiGlass kit carries
  about 1,150 mAh across seven small cells (6 x 150 + 250 mAh, source in 2.1), which shows that a glasses-sized
  enclosure can hold several times a Meta-class cell if weight allows.

### 2.4 Machining and injection moulding: when it starts to make sense

- Tooling: an aluminium low-volume tool is "$3,000 to $12,000 ... plus $0.60 to $4.00 per part for most
  consumer-sized plastic parts" (https://lanpdt.com/low-volume-injection-molding-cost/ , dated August 2026,
  **[snippet]**); a "simple single-cavity prototype mold" is "$1,000–$3,000" (https://zetarmold.com/?p=52613 ,
  **[snippet]**); general range "$1,000–$8,000+ for tooling and $0.50–$5.00+ per part"
  (https://rjcmold.com/guides/low-volume-injection-molding/ , **[snippet]**). All accessed 2026-11-14.
- A pair of camera glasses is at least three moulded parts (front, two temples) and usually five or more with
  electronics covers, so tooling is roughly $9,000 to $40,000+ before the first part (agent arithmetic on the ranges
  above).
- **Break-even (agent arithmetic):** at $20 to $40 per printed nylon frame set, 100 units cost $2,000 to $4,000 to
  print with no tooling. Moulding only wins somewhere between several hundred and a couple of thousand units, and
  only once the design has stopped changing. For 1 to 100 units, print.
- Machined acetate (how conventional frames are made) needs a specialist eyewear workshop; no public price was found
  in this run (see Unsourced).

### 2.5 Hinges, and how a cable or flexible circuit crosses one

- Commercial practice: the parts are "split across both arms and joined by flexible circuits that run through the
  hinges" (https://safeguard.sh/resources/blog/how-smart-glasses-are-made-cameras-microphones-displays-socs-firmware-and-bystander-privacy ,
  **[snippet]**, secondary source). A Hackaday teardown of a pair of smart sunglasses found that "even removing the
  hinges broke the flexible PCBs behind them"
  (https://hackaday.com/2023/05/06/inside-a-pair-of-smart-sunglasses , **[snippet]**). iFixit says of Meta's display
  glasses that Meta "didn't intend for anyone to ever put these back together, let alone swap a battery or fix a
  broken hinge" (https://www.engadget.com/ar-vr/ifixit-calls-metas-ray-ban-display-glasses-unrepairable-but-praises-the-tech-154820301.html ,
  **[snippet]**). All accessed 2026-11-14. No teardown showing the exact cable path in the Ray-Ban Meta hinge was found.
- Options for a prototype, easiest first (engineering judgement, not sourced):
  1. **Do not cross.** Camera, board and cell all sit on one temple, or in a clip-on pod, and that temple does not
     fold (or the whole module unclips). This is the recommendation for stages 1 and 2.
  2. **Cross with fine stranded wire** (power and a low-speed bus only, for example a cell on the opposite side
     feeding the board) through a hollow printed hinge barrel or over the top of a standard hinge with a slack loop.
  3. **Cross with a flexible circuit tail** with a service loop. A camera's high-speed serial link (MIPI CSI-2, the
     standard phone-camera interface) can run on a flexible circuit, but a tail that bends every time the glasses fold
     must be designed as "dynamic flex" (single copper layer in the bend, generous bend radius). This is custom-board
     work and belongs to stage 3.
- Ready-made hinges: standard spring and barrel eyewear hinges are sold by the bag by eyewear-repair suppliers for a
  few dollars each (from memory, unverified); the omiGlass kit uses "Standard glasses hinges" (source in 2.1).

### 2.6 Prescription lenses

- Lens labs will cut lenses for a frame the customer sends in. One lab says a "customer-owned frame lens replacement
  service can usually cut fresh prescription lenses" if the frame is structurally sound, with rimless or very curved
  frames needing a check first
  (https://www.lensdirect.com/blog/glasses/can-you-put-prescription-lenses-in-your-own-frames-what-to-check-before-you-order/ ,
  **[snippet]**). Price evidence: "usually ranges from $75 to $300" (https://howmuchblog.com/?p=6635 , **[snippet]**);
  "Lenses from $29.99 · Ready in 2–7 business days"
  (https://designeroptics.com/en-ca/products/send-your-own-frame-to-add-prescription , **[snippet]**).
  All accessed 2026-11-14.
- **No source confirmed that a lab will accept a home-designed 3D-printed frame.** The lens has to snap into a
  V-shaped groove in the rim, and the lab traces the rim shape; a printed nylon rim that is rough or too flexible may
  be refused (from memory, unverified). Two ways around it: (1) the clip-on route, which keeps his existing glasses
  and needs no lens work at all; (2) copy the rim shape and groove of a frame he already owns and move those lenses
  across.

## 3. (b) Design software, starting models and hired design

### 3.1 CAD for a beginner

| Tool | Free-tier terms (as found) | Fit for this job | Source |
|---|---|---|---|
| Onshape (browser-based) | Free plan is "for non-commercial use only"; free users cannot create private documents, so every design is public and copyable | Best first choice: nothing to install, works on any laptop, good tutorials. The public-documents rule is the cost | https://cad.onshape.com/help/Content/plansfaqs.htm and https://www.onshape.com/en/pricing **[snippet]** 2026-11-14 |
| Autodesk Fusion for Personal Use | "10 editable documents" at once (others become read-only); home, non-commercial use; one 2026 guide says under $1,000 a year of revenue from designs. Sources disagree on whether the licence renews yearly or every three years | Good alternative with private files; the surfacing tools suit curved frames | https://www.autodesk.com/products/fusion-360/blog/the-10-document-limit-for-personal-use-explained-in-7-steps/ , https://www.autodesk.com/products/fusion-360/personal/compare , https://stacksheriff.com/3d-printing/fusion-360-free-personal-license/ **[snippet]** 2026-11-14 |
| Code-driven CAD in Python (CadQuery, build123d), OpenSCAD, FreeCAD | Free and open source (from memory, unverified) | Worth a look for the stage-1 pod specifically: a Python engineer can script a parametric clip (temple width, camera tilt angle) faster than learning sketch-based CAD. Poor for sculpted frames | see Unsourced |

Both free tiers are non-commercial. That is fine for a personal prototype and stops being fine at the 50 to 100 unit
stage if units are sold.

### 3.2 Open-source frame models to start from (each checked today)

| Project | What the page shows | Usable as a starting frame? | Source |
|---|---|---|---|
| Open Source Smart Glasses (Mentra community repository) | "All work contained here is licensed under the MIT License." Has an `electronics_and_firmware` folder and a `mechanical` folder. The folder listing shows printable meshes (for example `FRONT_FRAME_NO_ARMS_0p3.stl`, `ARM_LEFT_3DPRINT_OSSG_0p3.stl`) and editable geometry (`MAIN_FRAME_CAD_0p3.stp`, `MAIN_FRAME_CAD_0p3.CATPart`, `Lens.stp`, `ear_battery_to_scale_OSSG.f3d`). A 2024 note says "we've moved on to build AugmentOS, a unifying OS for smart glasses". 252 commits, last-commit date not shown | Yes, as a geometry donor: STEP (`.stp`) is a neutral exchange format that Onshape and Fusion import without feature history (import capability from memory, unverified). It is a display-and-microphone design with a camera listed only among goals, and it is no longer the team's focus, so expect to redraw the temples | https://github.com/Mentra-Community/OpenSourceSmartGlasses and https://github.com/Mentra-Community/OpenSourceSmartGlasses/tree/main/mechanical **[page]** 2026-11-14 |
| OpenGlass, now omiGlass | MIT licence. A printed clip-on case: STL files (a mesh format, awkward to edit) in a `hardware` folder, standard hinges. The original OpenGlass repository says it has moved to the Omi repository | Yes, as the pattern for the stage-1 pod. The mesh files can be measured and redrawn rather than edited | https://docs.omi.me/doc/hardware/omiGlass **[page]**; https://awesome.ecosyste.ms/projects/github.com%2Fbasedhardware%2Fopenglass **[snippet]** 2026-11-14 |
| OpenAR 2.0 (University of Eastern Finland) | Ships "the original Fusion 360 design files together with STEP files", but it is a headset, not glasses | Reference for mounting details only | https://sites.uef.fi/openar/openar20/ **[snippet]** 2026-11-14 |

Mentra also sells camera glasses with an open software kit (from memory, unverified; not checked today, and whether
its frame CAD is published was not verified).

### 3.3 What a hired mechanical or industrial designer costs

- Hourly evidence, all **[snippet]**, 2026-11-14: CAD drafting "$45–$95/hr across junior to senior levels"
  (https://www.cadcrowd.com/blog/?p=50394); individual freelance mechanical engineers "around $50 USD / hour" and an
  industrial designer at "$45 USD per hour" (https://www.freelancer.com/freelancers/skills/industrial-design);
  industrial design experts "between $60 and $200+ per hour" (https://mentorcruise.com/experts/industrialdesign/ ,
  mentoring rates); US average pay for a freelance SolidWorks design engineer "$47.71" per hour
  (https://www.ziprecruiter.com/Jobs/Freelance-Design-Engineer-Solidworks , employee pay, so a floor).
- Fixed-price evidence **[page]**, 2026-11-14, https://www.cadcrowd.com/blog/cost-to-design-a-new-electronic-product-develop-pcb-hardware-prototype-rates-at-firms/amp
  (last updated 23 March 2026): "Plastic Enclosure Design, estimated cost: $5,000+" and "Plastic Enclosure
  Prototype, estimated cost: $500+ per iteration".
- **Estimate for this job (agent arithmetic):** a clip-on pod is 8 to 20 hours of a competent freelancer, so about
  $400 to $2,000. A full wearable frame with hinge, lens groove and board pockets is 30 to 80 hours across two or
  three fit iterations, so about $1,500 to $8,000, consistent with the "$5,000+" figure. Learning Onshape well
  enough to draw the pod himself is a few weekends (agent judgement).

## 4. (c) Circuit boards

### 4.1 Prototype fabrication and assembly

"Rigid" is an ordinary fibreglass board. "Flex" is a thin bendable polyimide circuit. "Rigid-flex" is both laminated
into one piece, which is what commercial glasses use and the most expensive of the three. SMT is surface-mount
technology (machine placement and soldering of parts). MOQ is minimum order quantity.

| Vendor | Offers | Price evidence | Minimum and lead time | Source |
|---|---|---|---|---|
| JLCPCB (China) | Rigid; flex in 1, 2 and 4 layers; assembly on flex ("SMT assembly is available for flex builds, with components drawn from the JLCPCB parts library"). The article read does **not** say JLCPCB makes rigid-flex | "flexible PCBs start from $25 for 5 pieces with a 4 to 5 day build"; rigid "$2.00 for 5 pieces" with "a 24-hour build" | 5 pieces is the only quantity quoted; build time excludes order review and shipping | https://jlcpcb.com/blog/flex-pcb-cost-pricing-guide (published 1 Sep 2026, updated 12 Nov 2026) **[page]** for the prices and the assembly statement, **[snippet]** for the layer counts and what the build time excludes; 2026-11-14 |
| PCBWay (China) | Flex in 1 to 10 layers, rigid-flex in "2 Layers" to "32 Layers"; assembly as "Turnkey, Kitted or Consigned, and Combo" | Home page: "Flex,Rigid-Flex PCB From $46.74" (quantity not stated) **[snippet]**. The order page showed "Shipping Cost: $125" to the US by DHL before any board price **[page]** | "Build Time:6-7 days" **[snippet]**; exact price is calculator only (not used) | https://www.pcbway.com/ **[snippet]**, https://www.pcbway.com/rigidflex.html **[page]** 2026-11-14 |
| Rigid-flex in general (estimate by AtlasPCB, a competing vendor's blog) | n/a | "5 pcs (prototype)" of a 6-layer rigid-flex at 80x60 mm: "$250-400"; a 4-layer, 10-piece example "$800-1,500"; rigid-flex costs "5-10x standard rigid boards" | "12-18 days" | https://www.atlaspcb.com/blog/rigid-flex-pcb-cost-breakdown-pricing-optimization/ **[snippet]** 2026-11-14 |
| OSH Park (United States) | 2-layer flex only; no assembly (from memory, unverified) | "$10 per square inch, which includes three copies of your design" | Sold in multiples of three; "12-21 calendar days" when available; the service is listed as "temporarily unavailable" and turn times "temporarily suspended" | https://docs.oshpark.com/services/flex/ , https://oshpark.com/ **[snippet]** 2026-11-14 |
| MacroFab (United States) | Fabrication and assembly, US facilities | quote only (instant quote needs a design upload) | "no minimum order quantities"; a "10-day turnaround" option when an order qualifies | https://macrofab.com/prototyping , https://macrofab.com/blog/macrofab-now-offers-10-day-prototyping **[snippet]** 2026-11-14 |
| CircuitHub (United States) | Fabrication, parts purchasing and assembly in Massachusetts | quote only; price "includes bare board fabrication, parts procurement, and PCB Assembly" | "as short as 3 days" for "low to mid complexity 2-4 layer boards"; prototype quantities of 1 to 10 boards (third-party profile) | https://circuithub.com/prototyping-capabilities , https://circuithub.com/expedited-pcb-assembly **[snippet]** 2026-11-14 |

**What this means for the prototype.**

- A true rigid-flex board is not needed and not affordable to iterate at this stage. The cheap equivalent is a small
  4-layer rigid main board plus a separate flex tail (or simply the camera module's own ribbon cable), which keeps
  each spin at tens of dollars of fabrication instead of hundreds.
- Parts sourcing: JLCPCB assembles from its own parts library; PCBWay will buy parts ("Turnkey") or accept parts the
  customer ships ("Kitted or Consigned"). A camera sensor or a processor that is not in the assembler's library must be
  consigned or hand-soldered, which is the usual snag for a camera board (the consignment snag is from memory,
  unverified).
- Budget per board spin, landed in the US (agent arithmetic on the rows above): flex or 4-layer rigid fabrication
  $25 to $60, assembly set-up and parts $50 to $250, express shipping $25 to $125, duty of up to 37.5 % of the declared value
  (section 6.2). Call it **$150 to $500 per spin for 5 boards**, and plan on 2 to 3 spins.

### 4.2 Hiring a board designer against learning KiCad

KiCad is the free, open-source board design program (from memory, unverified).

- Hourly evidence **[snippet]**, 2026-11-14: Fiverr's 2026 guide lists circuit-board work at "Hourly Rate: $45 - $80"
  (https://www.fiverr.com/resources/guides/costs/electronics-design-engineer); a freelancer who designs Raspberry Pi
  Compute Module carrier boards with two camera interfaces lists "$80 / hour" (https://www.fiverr.com/freelancers/tailongk).
- A directly comparable job post **[page]**, 2026-11-14: https://www.cadcrowd.com/job/9896-camera-smart-glasses-pcb-design
  asks for a camera smart-glasses board ("Design a 4-layer or higher multilayer PCB", processor chosen from "Allwinner
  V821", "Rockchip RV1103", "Rockchip RV1106", prototype must "Stream at least 720p30", deliverables "Complete
  KiCad/Altium/EasyEDA source files"). Budget "$750" fixed, duration "1-3 months", "16 Applicants", "0 interviews in
  progress", status "Ended", posted about three months ago. Read this as the **floor of what buyers hope to pay**, not
  as evidence that a working board was delivered for $750.
- Firm-level figure **[page]**, 2026-11-14 (Cad Crowd blog, URL in 3.3): "PCB Design, estimated cost: $10,000+" and
  "Prototyping, estimated cost: $1,000+ per iteration".
- **Estimate for this job (agent arithmetic):** schematic, layout and first power-up support for a small camera board
  with a high-speed camera interface is roughly 40 to 120 hours at $45 to $100 per hour: **$2,000 to $12,000**, plus
  fabrication spins. An offshore fixed-price freelancer may quote $750 to $2,500; the risk is a board that never
  boots and nobody to debug it.
- **Learning KiCad instead.** A first simple 2-layer board (a battery charger, a light-emitting-diode driver, a
  breakout for an inertial sensor) is a realistic 2 to 4 week evening project for a software engineer. A board with a
  phone-class processor, memory and a high-speed camera link is not a sensible first or second board: it needs
  controlled-impedance routing, fine-pitch packages he cannot hand-solder, and bring-up equipment (agent judgement;
  no source). The middle path is a **carrier board**: keep the processor on a bought module and design only the
  simple board that joins module, camera connector, charger, sensor and recording light. That is learnable in one to
  two months and is the stage-3 recommendation.

## 5. (d) Contract design and manufacture

| Option | One-off engineering fee | Minimum order | Timeline | Source |
|---|---|---|---|---|
| US product-development firm (full program to manufacturing-ready files) | "commonly lands between $80,000 and $400,000"; one firm's marketplace profile lists "Min. project size $25,000+" and "$100 - $149 /hr" | none, but they do not usually mass-produce | months | https://lanpdt.com/how-to-choose-a-product-development-company/ , https://clutch.co/profile/milivoja **[snippet]** 2026-11-14 |
| Shenzhen original design manufacturer (ODM, a factory that designs and builds to a brief), fully custom wearable | "$80,000 for a lightly customized ODM platform to $400,000+ for a fully custom device"; a premium custom AI-eyewear program lists "Starting from USD 800,000 NRE" (non-recurring engineering, the one-off fee) | typically hundreds to thousands | 4 to 9 months (from memory, unverified) | https://gmic.ai/custom-ai-wearable-odm-the-b2b-hardware-builders-guide/ , https://www.topaiglasses.com/custom-ai-eyewear-development/ **[snippet]** 2026-11-14 |
| Shenzhen ODM, customise an existing glasses platform (hardware and firmware) | not published | "MOQ is 200 pieces per model"; "functional samples take about seven days"; bulk "15–25 days after approval" (vendor claim in a press release) | 1 to 2 months | https://menafn.com/1111956109/Top-10-Wearable-Odms-Now-Customize-Both-Hardware-And-Firmware-From-200-Pieces-As-Glasses-Shipments-Rise-54 **[snippet]** 2026-11-14 |
| White-label: buy existing camera glasses, add a logo | none or small | listings show minimums from "5 Pieces (MOQ)" and "10-piece MOQ" up to "500 Pieces (MOQ)" and "1,000 Pieces (MOQ)"; unit prices "US$45.00" (10-piece minimum) and "US$40.00-43.00" (500-piece minimum, an "800W", that is 8-megapixel, camera model) | 1 to 4 weeks for samples (from memory, unverified) | https://www.made-in-china.com/products-search/hot-china-products/Camera_Bluetooth_Glasses.html and sibling listing pages **[snippet]** 2026-11-14 |
| Shenzhen build-to-your-files (he supplies the design; a factory builds a first engineering batch) | none | about 10 units | "EVT (about 10 units) ... 3‑4 weeks end‑to‑end ... EVT Cost: $4,000‑$12,000"; a second design-validation batch "6‑10 weeks ... $15,000‑$35,000". Another guide: "Prototype / EVT 10–50 units, $300–$800/unit, 8–14 weeks" | https://chinawithme.com/guides/how-to-prototype-shenzhen , https://huaxingpcba.com/blog/prototype-vs-production **[snippet]** 2026-11-14 |

EVT means engineering validation test, the first small factory build of a new design.

**White-label against ground-up, for this owner.**

- White-label is the only contract route inside $1,000: roughly $45 to $100 per sample pair plus shipping and duty.
  What it buys is a frame, a camera and a cell already integrated and already light. What it does not buy is the
  three things the tracker lane wants: (1) known optics with at least the Meta pixels per degree, (2) a
  time-synchronised motion-sensor log, (3) firmware he controls so clips go straight to the app. No listing found
  today publishes firmware source or a software kit, and whether a factory will change firmware for an order of 5 is
  unknown (see Unsourced). Treat a white-label pair as a **$50 to $150 teardown donor** (frame, hinge, cell and
  cable-routing ideas), not as the prototype.
- Ground-up by a design house is two orders of magnitude over budget and is built for people who will order
  thousands. It is not a route for 1 to 3 units.
- The affordable form of "contract" help is piecework: a freelance board designer (4.2), a freelance mechanical
  designer (3.3), and online fabrication (2.2, 4.1), with the owner acting as his own integrator.

## 6. (e) Rules and logistics for an individual in the United States

### 6.1 Radio rules for a personal prototype

- The home-built exemption, 47 CFR 15.23 (https://www.law.cornell.edu/cfr/text/47/15.23 ; mirror
  https://www.customsmobile.com/regulations/47/15.23 , "last checked for updates: Feb 09, 2026"; **[snippet]**,
  2026-11-14): equipment authorisation is not required for devices that are "not marketed, are not constructed from
  a kit, and are built in quantities of five or less for personal use". The builder "is expected to employ good
  engineering practices to meet the specified technical standards to the greatest extent practicable", and section
  15.5 (no harmful interference) still applies.
- Consequence: 1 to 3 units for his own use need no Federal Communications Commission (FCC) filing. The way to "employ
  good engineering practices" without test equipment is to use a **pre-certified radio module** (a Wi-Fi and
  Bluetooth module that already carries its own FCC identifier, with its approved antenna) rather than laying out a
  radio from chips. The search did not return FCC text on modules specifically; the statement that a module's
  certification covers the radio only when it is used with its approved antenna and that a product **sold** to others
  still needs its own emissions testing and labelling is from memory, unverified.
- At 50 to 100 units handed to other people, the exemption no longer applies (more than five, and arguably
  "marketed"). Budget test-lab time: "the testing chambers' rental fee is around $1,000 per hour" (Cad Crowd blog,
  URL in 3.3, **[page]**). A total certification cost was not sourced (see Unsourced).

### 6.2 Import duty and tariffs on boards and parts from China, as of 2026-11-14

This is the fastest-moving fact in the file. Sources below are trade blogs and a law-firm note, not the tariff
schedule itself; two primary pages could not be opened (see the end of this subsection).

- **No low-value exemption.** The $800 duty-free "de minimis" threshold is suspended for every country and every
  shipping mode. A law-firm trade blog **[page]**, 2026-11-14
  (https://www.thompsonhinesmartrade.com/2026/06/cbp-issues-interim-final-rules-indefinitely-suspending-the-de-minimis-exemption-for-imports/):
  Customs and Border Protection is "indefinitely suspending the $800 de minimis duty exemption for all modes of
  importation", "effective as of June 24, 2026", "with a delayed compliance date for certain specified shipments of
  October 22, 2026". Federal Register documents 2026-12669 and 2026-12670 (24 June 2026) are the primary sources
  (**[snippet]** only).
- **Rate on circuit boards from China.** AtlasPCB, a board vendor, **[page]** (paraphrase: the rates are the
  fetch tool's summary table, not verbatim text), article dated 21 August 2026
  (https://www.atlaspcb.com/news/news-pcb-tariff-section-301-exclusion-expiry-november-2026/): flexible boards,
  rigid-flex boards, boards of six or more layers and assembled boards pay **37.5 %** (a 25 % Section 301 product
  tariff plus a 12.5 % Section 301 layer); 2-layer and 4-layer rigid boards paid 12.5 % under an exclusion
  (code 9903.88.69) that was due to expire on 9 November 2026, after which they also pay 37.5 %. The article says the
  earlier emergency-powers tariffs were struck down in February 2026 and that the temporary Section 122 surcharge
  expired on 24 July 2026 (both paraphrase).
- **Conflict and gap.** A second vendor blog **[page]**, updated 30 June 2026
  (https://www.ourpcb.com/blog/china-us-pcb-tariffs-2026) describes bare boards as base rate "Free" plus Section 301
  "Often 25% unless excluded", confirms the exclusion ran "through 11:59 p.m. Eastern Time on November 9, 2026", and
  says "Duty-free de minimis treatment has been suspended for low-value shipments". The two blogs disagree on the
  total (25 % against 37.5 %), and both were written before the expiry date.
- **Extension reported.** A search run today returned three reports that the US Trade Representative extended all
  178 exclusions, including code 9903.88.69, **through 9 January 2027** (two months, not the year industry asked
  for): https://www.bdo.com/insights/tax/ustr-extends-china-section-301-product-exclusions-and-vietnam-ip-investigation-timeline ,
  https://www.ghy.com/trade-compliance/ustr-extends-section-301-product-exclusions-china and
  https://www.techtimes.com/articles/330285/20261109/ustr-extends-section-301-tariff-exclusions-chinese-goods-entries-after-january-9-pay-full-duty.htm
  (dated 9 November 2026). All **[snippet]**, 2026-11-14; the Federal Register notice was not read. If that holds,
  2-layer and 4-layer rigid boards keep the lower rate until 9 January 2027, and flexible, rigid-flex, six-layer and
  assembled boards are unaffected because the exclusion never covered them. Plan on 37.5 % for everything from
  China and treat anything lower as a bonus.
- **Mechanics.** One blog **[page]**, dated 3 October 2026 with a 23 October note
  (https://landedmath.com/blog/us-de-minimis-postal-route-closes-october-2026/): "duty and fees = value x (Column 1
  rate + Section 301 rate + MPF 0.3464%)" (MPF is the merchandise processing fee); "Since 22 October 2026 Chapter 99
  goods have had no postal informal route", meaning China-origin goods carrying Section 301 codes need a filed entry
  rather than arriving by ordinary post; the blog assumes "$20.00 – $60.00" per shipment for entry preparation and
  bond and says it could not verify enforcement.
- **Practical effect on this project (agent arithmetic).** At 37.5 %, on a $40 board order the duty is about $15; the larger
  costs are express shipping ($25 to $125) and any courier brokerage fee. On a $300 assembled-board order the duty is
  about $113. Over the whole prototype (3 to 6 small orders) expect **$100 to $400 of duty and fees**. Buying
  finished development boards, camera modules and cells from US distributors avoids the paperwork because the
  distributor has already imported them. Duty rates for 3D-printed plastic parts and for finished camera glasses were
  not sourced (see Unsourced).
- Could not open: the Federal Register "Low-Value Shipments" document of 8 October 2026
  (https://www.federalregister.gov/documents/2026/10/08/2026-20650/low-value-shipments) redirected to a bot check,
  and https://octopart.com/pulse/p/tariff-reset-pcb-workarounds returned HTTP 403.

### 6.3 Shipping lithium cells

All **[snippet]**, 2026-11-14.

- Postal limits for lithium-ion and lithium-polymer cells in or with equipment: "Each lithium-ion or lithium polymer
  cell must not exceed more than 20 Wh" and each battery "must not exceed 100 Wh" (USPS Packaging Instruction 9E,
  archived June 2025 edition, https://pe.usps.com/PUB52_Archive/NHTML/PUB52_Archive_20250601/pub52apxc_033.htm). A
  glasses cell of 150 to 250 mAh at 3.7 V is 0.6 to 0.9 watt-hours, far under both limits (agent arithmetic).
- Loose cells are the restricted case: the same archive lists lithium-ion batteries "Without the equipment they
  operate" as "Prohibited" for at least some mail classes, and a carrier guide says the Postal Service "limits
  standalone lithium batteries to ground transportation only" (https://parcelpath.com/shipping-companies/usps/usps-shipping-restrictions/).
  UPS treats lithium polymer as lithium-ion and restricts damaged or defective cells to ground
  (https://www.ups.com/us/en/support/shipping-support/shipping-special-care-regulated-items/hazardous-materials-guide/how-to-ship-batteries).
- 2026 changes reported: new rigid outer-packaging rules for hazardous mail "Effective January 27, 2026" and a "$50
  hazmat noncompliance fee (effective July 12, 2026)" (https://www.stamps.com/article/new-usps-mailing-standards-for-lithium-batteries/
  and related guides). The exact current Publication 52 text was not read.
- **Practical rule:** buy small protected lithium-polymer cells from a US hobby-electronics distributor (they ship
  by ground and the cell arrives with a protection circuit and a connector), never mail a bare or swollen cell, and
  if a finished prototype must be posted, post it with the cell installed. Safety on the face: use a cell with a
  built-in protection circuit, a proper charger chip, a temperature cut-off, and an enclosure wall between cell and
  skin (safety practice from memory, unverified).

### 6.4 Privacy expectations for a wearable camera

All **[snippet]**, 2026-11-14.

- No federal law is specific to smart glasses: "there is no federal law specifically governing the use of smart
  glasses in the United States" (https://www.androidauthority.com/proposed-smart-glasses-recording-law-pennsylvania-3675519/).
- State direction of travel: Pennsylvania House Bill 2603, introduced June 2026, "would require smart glasses sold,
  used, or manufactured in the state to include a visible indicator whenever they are recording" and bans disabling
  it; its penalty section names only retailers and manufacturers
  (https://bgr.com/2191365/smart-glasses-recording-light-bill-pennsylvania/ ,
  https://www.slashgear.com/2192035/smart-glasses-recording-light-proposed-law-pennsylvania/). Whether it has passed
  was not checked.
- Industry norm: the Ray-Ban Meta glasses "use a green LED light on the front of the glasses to signal when photos or
  videos are being captured"; Samsung's glasses "stop recording when the wearer covers the front-facing indicator
  light"; researchers found that "from any real distance the indicator goes undetected"
  (https://www.biometricupdate.com/202609/metas-smart-glasses-privacy-defense-falters-when-ai-can-use-camera-without-recording-light ,
  https://idevice.com/samsung-glasses-already-obey-a-rule-california-has-not-passed.md).
- **Design rule for the prototype:** a forward-facing light wired in hardware to the camera's power or
  recording-active line, so software cannot record with it off. Audio is the stricter legal issue: some states
  require every party's consent to record a conversation (from memory, unverified; no state list was sourced). The
  tracker wants the sound of the pin strike, so record audio only while a clip is active and tell the people on the
  lane. A bowling centre is private property and can simply say no.

## 7. (f) A staged path

Costs below are for the whole stage, not per unit, and exclude his own time. "Electronics" means off-the-shelf
boards, camera module and cell; **which** ones is another lane's question, so this file uses a placeholder of **$60
to $250 per unit (agent estimate, not sourced)** and the reader should substitute that lane's number.

| Stage | What gets made | What it proves | Cost for the stage | Weeks | Skills learned / bought |
|---|---|---|---|---|---|
| 0. Bench | Tools (list below); a $50 to $150 pair of generic camera glasses to take apart (optional) | Nothing yet; it removes the "I cannot solder" blocker | $300 to $800 tools (unsourced estimate) + $0 to $150 donor | 1 | Learned: soldering wires and connectors |
| 1. Clip-on rig | A development board, camera module and small cell in a printed pod clipped to the temple of his own glasses; one unit | That the camera gives at least the Meta pixels per degree at the pins, that a motion-sensor log can be time-synced, and that clips reach the app from the device | $150 to $450: electronics $60 to $250, 2 to 4 pod prints at $3 to $30, shipping and duty $40 to $100 | 2 to 4 | Learned: basic CAD (Onshape, or Python CAD for the pod). Bought: printing |
| 2. Printed frame, off-the-shelf boards | A nylon (MJF PA12) frame, dyed black, with pockets for the same boards; camera-side temple does not fold; recording light on the front; 1 to 3 units | Two-hour comfort, weight at or under about 55 g, heat beside the head, lens fit, that someone else can wear it | $400 to $1,500 self-designed (3 to 5 frame iterations at $20 to $110, electronics for 1 to 3 units, lenses $30 to $300); add $1,500 to $8,000 if the frame is drawn by a freelancer | 4 to 8 | Learned: frame CAD and print tolerances. Optionally bought: mechanical design |
| 3. Custom carrier board | His own small rigid board (plus a flex tail if needed) joining a bought processor module, camera connector, charger, motion sensor and recording light, shrinking the temple | That the electronics fit a normal-looking temple; that a build can be repeated | $500 to $1,500 if he lays it out in KiCad (2 to 3 spins at $150 to $500 landed); $2,500 to $13,000 if a freelancer designs it | 8 to 16 | Learned or bought: board layout. This is the first stage that needs real electronics skill |
| 4. Small batch (only if wanted) | 50 to 100 units: frames printed in one batch, boards assembled by a board house, hand final assembly | That other bowlers can use it | $8,000 to $35,000 total (see table in section 8), plus radio testing because the five-unit exemption no longer applies | 12 to 20 | Bought: assembly, compliance testing |

**Budget reading.** Stages 0 to 2 together are about **$850 to $2,750**, so the frugal end fits the $1,000 figure as
a whole-effort budget and the per-unit cost of each further copy is about $100 to $400. If $1,000 means one unit's
parts, stages 0 to 3 with self-taught layout fit comfortably. Hiring any designer (mechanical or board) breaks the
whole-effort reading of the budget on its own.

**Decision gate after stage 1.** If the stage-1 camera does not match the Meta glasses on ball radius at the pins
(`REQUIREMENTS.md` section 3, item 1), stop and change the camera before spending anything on a frame. The frame is
the cheap part to redo; the sensor choice is not.

**The third-person case.** `REQUIREMENTS.md` section 1 notes that lifting clips are filmed from a stand. The stage-1
pod serves that for free if its clip is drawn to also fit a small tripod thread or a phone clamp; a fully integrated
frame does not.

**Bench tools he must own** (all prices from memory, unverified; see Unsourced): temperature-controlled soldering
iron with a fine tip ($60 to $120); solder, flux, wick, tweezers, flush cutters ($40); multimeter ($30 to $60); USB
power meter ($15 to $25); digital calipers ($25, essential for frame fit); magnifier or USB microscope ($40 to
$100); hot-air rework station, only from stage 3 ($50 to $100); a fire-resistant pouch for lithium cells ($10 to
$15); kitchen scale to 0.1 g ($15); optional desktop filament printer for same-day pod iterations ($200 to $400).

## 8. Summary table: route by cost, time, skills and risk

Costs include fabrication, a reasonable number of iterations, shipping and duty, and exclude the owner's own hours.
The electronics placeholder of $60 to $250 per unit is included where a route needs it. Figures are agent estimates
built from the sourced unit prices in sections 2 to 6; they are ranges, not quotes.

| Route | Cost for 1 to 3 units | Cost at 50 to 100 units | Weeks to first working unit | Skills needed | Biggest risk |
|---|---|---|---|---|---|
| 1. Clip-on pod on his own glasses, off-the-shelf boards | $150 to $450 for one; $350 to $1,000 for three (plus $300 to $800 tools once) | $4,000 to $27,000, almost all of it the off-the-shelf boards; pods are $3 to $15 each in a batch | 2 to 4 | Soldering wires, beginner CAD; all learnable | Bulk and one-sided weight; looks like a gadget; pod shifts and changes the camera angle between sessions |
| 2. Modified off-the-shelf frames | $200 to $600 | Not sensible (hand work per unit) | 2 to 5 | Hand tools, patience | Ruined frames; nothing repeatable; no room for the cell |
| 3. Fully 3D-printed nylon frame, off-the-shelf boards, self-designed | $400 to $1,500 | $5,000 to $30,000 ($20 to $40 frame, electronics, hinges, hand assembly) | 6 to 12 | Intermediate CAD (learned over the project), soldering | Fit and comfort take more iterations than expected; a lens lab may refuse a printed rim; temple is thick because boards are not custom |
| 4. Printed frame drawn by a freelance mechanical designer | $2,000 to $9,500 | $6,500 to $38,000 (design fee is paid once) | 6 to 10 | Writing a clear brief; managing a contractor | Paying for a design that then has to change when the boards change |
| 5. Custom carrier board, self-taught KiCad, in a printed frame | $900 to $3,000 | $6,000 to $25,000 ($60 to $150 per unit built, plus radio testing) | 14 to 28 | Board layout (learned, 1 to 2 months), fine soldering, bring-up | First boards do not work; a camera's high-speed link is unforgiving; duty of up to 37.5 % on every spin |
| 6. Custom board by a freelance board designer, in a printed frame | $3,000 to $15,000 | $8,000 to $35,000 | 12 to 24 | Specification writing, firmware bring-up (his strength) | Cheap fixed-price freelancers deliver files, not a working board; nobody owns debugging |
| 7. White-label camera glasses from a Shenzhen listing | $100 to $500 for 1 to 5 sample pairs | $2,000 to $5,000 at $40 to $45 each, plus duty; logo only | 2 to 5 | Sourcing, negotiation | No firmware control, unknown optics, no motion-sensor log: it may not beat the Meta glasses on any tracker requirement |
| 8. Shenzhen ODM customising an existing platform | Not offered below about 200 units | Fee for customising an existing platform is not published; one guide puts "a lightly customized ODM platform" at $80,000 (section 5); plus at least 200 units | 8 to 16 | Program management, a trip or an agent | Minimum order and fee are both far outside the brief |
| 9. US design house, ground-up | Not offered below about $25,000; typical $80,000 to $400,000 | Same fee plus manufacturing | 26 to 52 | Money | Two orders of magnitude over budget |
| 10. Injection-moulded frame (any electronics route) | Not sensible | $9,000 to $40,000 tooling plus $2 to $20 per frame | 4 to 10 for tooling (from memory, unverified) | A frozen design | Any design change scraps a tool |

**Recommended sequence:** route 1, then route 3, then route 5 (carrier board only), buying help by the hour where he
gets stuck rather than by the project. Routes 7 to 10 are documented so the option is visibly closed, with route 7
kept as a cheap teardown donor.

## 9. Unsourced (not presented as fact)

- **The exact duty rate on circuit boards from China today.** Two vendor blogs disagree (25 % against 37.5 % for
  boards outside the exclusion), and the reported extension of the 2-layer and 4-layer exclusion to 9 January 2027
  was seen only as search snippets. Neither the tariff schedule nor the Federal Register notice was read.
- Express-courier brokerage and disbursement fees on a small China parcel in November 2026 (only one blog's assumed
  $20 to $60 was found).
- US duty rate on 3D-printed nylon parts from China, and on finished camera glasses.
- PCBWay's 3D-printing prices and its rigid-flex price for a stated quantity (calculator only).
- Current JLC3DP per-gram price (the $0.275 per gram figure is from an August 2025 notice, seen as a snippet).
- Whether JLCPCB itself fabricates rigid-flex (one third-party review says yes; JLCPCB's own article does not say so).
- Whether any lens lab accepts a home-designed 3D-printed frame, and at what price.
- Price of machined acetate frames from an eyewear workshop in single quantities.
- Whether a Shenzhen white-label supplier will change firmware, or release a software kit, for an order of 1 to 10.
- Total cost of FCC testing for a product built on a pre-certified module (commonly quoted as a few thousand
  dollars; from memory, unverified), and the exact FCC wording on modules.
- The list of all-party-consent states for audio recording, and the status of Pennsylvania House Bill 2603.
- Every bench-tool price in section 7 and the $60 to $250 electronics placeholder.
- The date of the last commit to the Open Source Smart Glasses repository, and whether its STEP files import
  cleanly into Onshape or Fusion.
- Skin-contact (biocompatibility) certification of dyed MJF PA12 from a given print service. Commercial eyewear is
  printed in it, but no service's certificate was read.
- Comfort thresholds (55 g total, 15 g one-sided) and all hour estimates for design work: agent judgement.
- Statements tagged "(from memory, unverified)" in the body: typical weight of ordinary glasses, hinge parts and
  screw patterns, resin brittleness, consigned-parts snag, OSH Park not offering assembly, KiCad and FreeCAD being
  free, moulding lead times, Mentra selling camera glasses with an open software kit.

## 10. Method log and status

- Web searches run: 24. Pages opened and read: 11 (ourpcb.com tariffs, jlcpcb.com flex cost guide, atlaspcb.com
  tariff notice, cadcrowd.com job 9896, pcbway.com rigid-flex order page, the Open Source Smart Glasses repository and its `mechanical` folder,
  docs.omi.me omiGlass, thompsonhinesmartrade.com de minimis note, landedmath.com postal-route article, cadcrowd.com
  cost blog). Three further fetches failed (octopart.com 403, mddionline.com 403, federalregister.gov bot check).
- Pages are read through a summarising fetch tool; quotes were requested verbatim but short phrases may be the
  tool's paraphrase. Everything tagged **[snippet]** was seen only as a search-result extract.
- No quote form, calculator upload, sign-up or purchase was used. Search terms were generic.
- **Status: DONE**, with the open items listed in section 9. The single most consequential open item is the exact
  duty rate on boards from China, which rests on vendor blogs and search snippets.

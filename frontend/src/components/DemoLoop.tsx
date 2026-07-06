import React from "react";

/**
 * Home-page demo loop: a 12s CSS/SVG animation cycling three scenes of what
 * the app actually does — a plank hold with timer + form check, a bowling
 * ball tracked down the lane, and a scorecard scanned into a handicap.
 * Pure presentation; all timing lives in index.css (demo-* keyframes).
 * Reference: docs/superpowers/specs/assets/2026-07-06-home-redesign-mockup.html
 */
const DemoLoop: React.FC = () => (
  <div>
    <div className="relative glass rounded-2xl overflow-hidden h-[190px]">
      {/* Scene 1: Plank — figure holds, timer counts up, form check pops */}
      <div className="demo-scene demo-scene-plank absolute inset-0">
        <span className="absolute top-3 left-4 text-xs uppercase tracking-wider text-muted-foreground">
          Plank · hold + form
        </span>
        <svg viewBox="0 0 560 190" className="w-full h-full" aria-hidden="true">
          <line x1="80" y1="160" x2="480" y2="160" stroke="hsl(240 4% 22%)" strokeWidth="2" />
          <g className="demo-plank-bob" stroke="hsl(0 0% 80%)" strokeWidth="5" strokeLinecap="round" fill="none">
            <circle cx="176" cy="116" r="11" fill="hsl(0 0% 80%)" stroke="none" />
            <line x1="196" y1="124" x2="352" y2="142" />
            <line x1="200" y1="126" x2="192" y2="156" />
            <line x1="178" y1="157" x2="212" y2="157" />
            <line x1="352" y1="142" x2="362" y2="158" />
          </g>
          <g fontSize="26" fontWeight="700" fill="hsl(0 0% 92%)" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">
            <text className="demo-timer demo-timer-1" x="440" y="90">0:15</text>
            <text className="demo-timer demo-timer-2" x="440" y="90">0:32</text>
            <text className="demo-timer demo-timer-3" x="440" y="90">0:47</text>
          </g>
          <text x="440" y="108" textAnchor="middle" fontSize="11" fill="hsl(240 5% 55%)" letterSpacing="1">HOLD</text>
          <g className="demo-pill-plank">
            <rect x="386" y="122" width="108" height="26" rx="13" fill="hsl(160 70% 45% / 0.15)" />
            <text x="440" y="139" textAnchor="middle" fontSize="13" fontWeight="600" fill="hsl(160 70% 55%)">Hips level ✓</text>
          </g>
        </svg>
      </div>

      {/* Scene 2: Bowl — ball hooks down the lane, trace draws */}
      <div className="demo-scene demo-scene-bowl absolute inset-0">
        <span className="absolute top-3 left-4 text-xs uppercase tracking-wider text-muted-foreground">
          Bowl · ball tracking
        </span>
        <svg viewBox="0 0 560 190" className="w-full h-full" aria-hidden="true">
          <path d="M 240 28 L 320 28 L 400 168 L 160 168 Z" fill="hsl(240 4% 14%)" stroke="hsl(240 4% 22%)" />
          <g fill="hsl(0 0% 85%)">
            <circle cx="262" cy="24" r="5" /><circle cx="280" cy="20" r="5" /><circle cx="298" cy="24" r="5" />
            <circle cx="271" cy="30" r="5" /><circle cx="289" cy="30" r="5" />
          </g>
          <path
            className="demo-trace"
            d="M 285 158 C 320 120 322 70 284 32"
            fill="none"
            stroke="hsl(220 90% 56%)"
            strokeWidth="2.5"
            strokeDasharray="4 5"
            strokeLinecap="round"
          />
          <circle r="9" fill="hsl(220 90% 56%)">
            <animateMotion
              dur="12s"
              repeatCount="indefinite"
              calcMode="linear"
              keyPoints="0;0;1;1"
              keyTimes="0;0.38;0.56;1"
              path="M 285 158 C 320 120 322 70 284 32"
            />
          </circle>
          <g className="demo-pill-bowl">
            <rect x="398" y="70" width="128" height="26" rx="13" fill="hsl(220 90% 56% / 0.15)" />
            <text x="462" y="87" textAnchor="middle" fontSize="13" fontWeight="600" fill="hsl(220 90% 66%)">Board 17 · Pocket ✓</text>
          </g>
        </svg>
      </div>

      {/* Scene 3: Golf — scan line reads the scorecard, handicap pops */}
      <div className="demo-scene demo-scene-golf absolute inset-0">
        <span className="absolute top-3 left-4 text-xs uppercase tracking-wider text-muted-foreground">
          Golf · scorecard → handicap
        </span>
        <svg viewBox="0 0 560 190" className="w-full h-full" aria-hidden="true">
          <g stroke="hsl(240 4% 24%)" fill="none">
            <rect x="90" y="60" width="380" height="70" rx="6" />
            <line x1="90" y1="95" x2="470" y2="95" />
            <line x1="132" y1="60" x2="132" y2="130" /><line x1="174" y1="60" x2="174" y2="130" />
            <line x1="216" y1="60" x2="216" y2="130" /><line x1="258" y1="60" x2="258" y2="130" />
            <line x1="300" y1="60" x2="300" y2="130" /><line x1="342" y1="60" x2="342" y2="130" />
            <line x1="384" y1="60" x2="384" y2="130" /><line x1="426" y1="60" x2="426" y2="130" />
          </g>
          <g fontSize="12" fill="hsl(240 5% 55%)" textAnchor="middle">
            <text x="111" y="82">1</text><text x="153" y="82">2</text><text x="195" y="82">3</text>
            <text x="237" y="82">4</text><text x="279" y="82">5</text><text x="321" y="82">6</text>
            <text x="363" y="82">7</text><text x="405" y="82">8</text><text x="448" y="82">9</text>
          </g>
          <g fontSize="13" fontWeight="600" fill="hsl(0 0% 88%)" textAnchor="middle">
            <text x="111" y="118">5</text><text x="153" y="118">4</text><text x="195" y="118">4</text>
            <text x="237" y="118">6</text><text x="279" y="118">3</text><text x="321" y="118">5</text>
            <text x="363" y="118">4</text><text x="405" y="118">5</text><text x="448" y="118">4</text>
          </g>
          <line className="demo-scanline" x1="90" y1="52" x2="90" y2="138" stroke="hsl(220 90% 56%)" strokeWidth="2" />
          <g className="demo-pill-golf">
            <rect x="238" y="146" width="90" height="28" rx="14" fill="hsl(160 70% 45% / 0.15)" />
            <text x="283" y="165" textAnchor="middle" fontSize="14" fontWeight="700" fill="hsl(160 70% 55%)">HCP 21.0</text>
          </g>
        </svg>
      </div>
    </div>
    <div className="flex gap-1.5 justify-center mt-3" aria-hidden="true">
      <span className="demo-dot w-1.5 h-1.5 rounded-full bg-secondary" />
      <span className="demo-dot w-1.5 h-1.5 rounded-full bg-secondary" />
      <span className="demo-dot w-1.5 h-1.5 rounded-full bg-secondary" />
    </div>
  </div>
);

export default DemoLoop;

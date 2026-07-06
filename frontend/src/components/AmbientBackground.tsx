import React from "react";

// Repeating 320px line-art tile: dumbbell, bowling ball, golf flag + green,
// stopwatch, swoosh — white strokes; the layer's opacity keeps it a whisper.
const DOODLE_TILE = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='320' viewBox='0 0 320 320'%3E%3Cg fill='none' stroke='%23ffffff' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'%3E%3Cg transform='translate(38 44) rotate(-18)'%3E%3Crect x='0' y='6' width='7' height='16' rx='2'/%3E%3Crect x='33' y='6' width='7' height='16' rx='2'/%3E%3Cline x1='7' y1='14' x2='33' y2='14'/%3E%3C/g%3E%3Cg transform='translate(220 60) rotate(12)'%3E%3Ccircle cx='14' cy='14' r='14'/%3E%3Ccircle cx='9' cy='9' r='1.4'/%3E%3Ccircle cx='16' cy='7' r='1.4'/%3E%3Ccircle cx='15' cy='14' r='1.4'/%3E%3C/g%3E%3Cg transform='translate(150 150) rotate(-8)'%3E%3Cline x1='4' y1='34' x2='4' y2='0'/%3E%3Cpath d='M4 2 L26 8 L4 15'/%3E%3Cellipse cx='9' cy='36' rx='9' ry='2.4'/%3E%3C/g%3E%3Cg transform='translate(48 218) rotate(14)'%3E%3Ccircle cx='12' cy='16' r='11'/%3E%3Cline x1='9' y1='2' x2='15' y2='2'/%3E%3Cline x1='12' y1='2' x2='12' y2='5'/%3E%3Cline x1='12' y1='16' x2='17' y2='11'/%3E%3C/g%3E%3Cg transform='translate(238 220) rotate(-10)'%3E%3Cpath d='M8 0 C4 6 12 10 8 16 C4 22 12 26 8 32'/%3E%3Cpath d='M8 0 C12 6 4 10 8 16 C12 22 4 26 8 32' transform='translate(6 0)'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`;

/**
 * App-wide ambient backdrop: faint sports-doodle wallpaper + three slow
 * drifting color glows. Mounted once in Layout; purely decorative.
 */
const AmbientBackground: React.FC = () => (
  <>
    <div
      aria-hidden="true"
      className="fixed inset-0 -z-20 pointer-events-none opacity-[0.05]"
      style={{ backgroundImage: DOODLE_TILE, backgroundSize: "320px 320px" }}
    />
    <div
      aria-hidden="true"
      className="ambient-glow ambient-glow-1 fixed -z-10 pointer-events-none w-[480px] h-[480px] -left-36 top-16"
      style={{ background: "hsl(220 90% 56% / 0.16)" }}
    />
    <div
      aria-hidden="true"
      className="ambient-glow ambient-glow-2 fixed -z-10 pointer-events-none w-[420px] h-[420px] -right-40 top-[340px]"
      style={{ background: "hsl(160 70% 45% / 0.10)" }}
    />
    <div
      aria-hidden="true"
      className="ambient-glow ambient-glow-3 fixed -z-10 pointer-events-none w-[380px] h-[380px] left-[30%] -bottom-44"
      style={{ background: "hsl(30 90% 55% / 0.08)" }}
    />
  </>
);

export default AmbientBackground;

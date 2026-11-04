"use client";

export type AvatarConfig = {
  style: string;
  skin_tone: string;
  hair: string;
  accessory: string;
  background: string;
};

const backgrounds: Record<string, [string, string]> = {
  violet: ["#6d4aff", "#a98cff"],
  ocean: ["#06b6d4", "#2f7cf6"],
  mango: ["#ff8a3d", "#ffcc5c"],
  mint: ["#0fbf9f", "#75e5cb"],
};
const skins: Record<string, string> = {
  sunny: "#f6c59f",
  honey: "#d99a6c",
  cocoa: "#89583e",
  moon: "#f1d9ca",
};

export function Avatar({ config, size = 64, animated = false }: { config: AvatarConfig; size?: number; animated?: boolean }) {
  const [from, to] = backgrounds[config.background] || backgrounds.violet;
  const skin = skins[config.skin_tone] || skins.sunny;
  return (
    <div className={animated ? "avatar-shell avatar-float" : "avatar-shell"} style={{ width: size, height: size }}>
      <svg viewBox="0 0 100 100" role="img" aria-label="Avatar del estudiante">
        <defs>
          <linearGradient id={`bg-${config.background}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor={from} />
            <stop offset="1" stopColor={to} />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="49" fill={`url(#bg-${config.background})`} />
        {config.accessory === "stars" && <><path d="M18 26l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="#fff" opacity=".9"/><circle cx="80" cy="22" r="3" fill="#fff" opacity=".7"/></>}
        {config.accessory === "orbit" && <ellipse cx="50" cy="52" rx="44" ry="19" fill="none" stroke="#fff" strokeWidth="2" opacity=".55" transform="rotate(-18 50 52)"/>}
        <path d="M24 93c3-20 14-28 26-28s23 8 26 28" fill="#ffffff" opacity=".92" />
        <circle cx="50" cy="47" r="23" fill={skin} />
        {config.hair === "waves" && <path d="M28 48c-5-23 12-31 27-27 13 3 20 14 16 30-5-2-8-10-9-16-10 9-24 9-34 13z" fill="#30233e" />}
        {config.hair === "curls" && <path d="M27 49c-5-17 4-30 20-31 19-2 30 13 25 32-4-6-8-10-13-12-6 6-18 9-32 11z" fill="#502d25" stroke="#502d25" strokeWidth="5" strokeLinecap="round" />}
        {config.hair === "short" && <path d="M29 42c1-17 12-24 24-23 13 1 21 10 20 25-7-8-14-11-24-11-8 0-14 3-20 9z" fill="#1f2937" />}
        <ellipse cx="42" cy="49" rx="2.3" ry="3.2" fill="#202539" />
        <ellipse cx="58" cy="49" rx="2.3" ry="3.2" fill="#202539" />
        <path d="M43 58c5 4 10 4 15 0" fill="none" stroke="#9f4e55" strokeWidth="2.2" strokeLinecap="round" />
        {config.accessory === "glasses" && <><rect x="34" y="43" width="13" height="10" rx="4" fill="none" stroke="#31405f" strokeWidth="2"/><rect x="53" y="43" width="13" height="10" rx="4" fill="none" stroke="#31405f" strokeWidth="2"/><path d="M47 47h6" stroke="#31405f" strokeWidth="2"/></>}
      </svg>
    </div>
  );
}

export const defaultAvatar: AvatarConfig = { style: "orbit", skin_tone: "sunny", hair: "waves", accessory: "stars", background: "violet" };

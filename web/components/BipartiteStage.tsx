"use client";

import { useEffect, useState } from "react";

const U = 6;
const V = 6;

const EDGES: ReadonlyArray<readonly [number, number]> = [
  [0, 0], [0, 1], [0, 2],
  [1, 0], [1, 1], [1, 2],
  [2, 0], [2, 1], [2, 2],
  [3, 0], [4, 4], [5, 5], [0, 3],
];

const PEEL: ReadonlyArray<readonly ["U" | "V", number]> = [
  ["U", 5], ["V", 5], ["U", 4], ["V", 4], ["U", 3], ["V", 3],
];

const STEP_MS = 680;
const HOLD_MS = 1600;

function key(side: "U" | "V", index: number) {
  return `${side}${index}`;
}

export function BipartiteStage() {
  const [gone, setGone] = useState<string[]>([]);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    let timer = 0;
    let cancelled = false;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const dropped = PEEL.map(([side, index]) => key(side, index));

    const finish = () => setGone(dropped);

    const start = () => {
      if (cancelled) return;
      if (motion.matches) {
        finish();
        return;
      }
      setGone([]);
      let step = 0;
      const tick = () => {
        if (cancelled) return;
        if (step >= PEEL.length) {
          timer = window.setTimeout(start, HOLD_MS);
          return;
        }
        const [side, index] = PEEL[step];
        step += 1;
        setGone((current) => [...current, key(side, index)]);
        timer = window.setTimeout(tick, STEP_MS);
      };
      timer = window.setTimeout(tick, STEP_MS);
    };

    if (!paused) start();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [paused]);

  const dropped = new Set(gone);
  const kept = U + V - dropped.size;

  const yOf = (index: number) => 36 + index * 58;

  return (
    <div className="peel">
      <div className="peel__bar">
        <span>Peel</span>
        <span>{kept} of 12 vertices kept</span>
      </div>
      <svg viewBox="0 0 520 400" role="img" aria-label={`${kept} of 12 vertices kept on one small bipartite graph.`}>
        <title>{`${kept} of 12 vertices kept`}</title>
        {EDGES.map(([u, v]) => {
          const off = dropped.has(key("U", u)) || dropped.has(key("V", v));
          const on = !off && !dropped.has(key("U", u)) && !dropped.has(key("V", v)) && u < 3 && v < 3;
          return (
            <line
              key={`${u}-${v}`}
              x1={92}
              y1={yOf(u)}
              x2={428}
              y2={yOf(v)}
              className={off ? "peel__edge peel__edge--off" : on ? "peel__edge peel__edge--on" : "peel__edge"}
            />
          );
        })}
        {Array.from({ length: U }, (_, index) => (
          <g key={`U${index}`} className={dropped.has(key("U", index)) ? "is-off" : "is-on"}>
            <circle cx={92} cy={yOf(index)} r={11} />
            <text x={64} y={yOf(index) + 4}>{`U${index}`}</text>
          </g>
        ))}
        {Array.from({ length: V }, (_, index) => (
          <g key={`V${index}`} className={dropped.has(key("V", index)) ? "is-off" : "is-on"}>
            <circle cx={428} cy={yOf(index)} r={11} />
            <text x={448} y={yOf(index) + 4}>{`V${index}`}</text>
          </g>
        ))}
      </svg>
      <ol className="peel__log">
        {PEEL.map(([side, index]) => (
          <li key={key(side, index)} className={dropped.has(key(side, index)) ? "is-on" : undefined}>
            {`peel drops ${side}${index}`}
          </li>
        ))}
        <li className={gone.length === PEEL.length ? "is-on" : undefined}>U0–U2 and V0–V2 remain</li>
      </ol>
      <button
        className={`loop-pause${paused ? " is-paused" : ""}`}
        type="button"
        aria-label={paused ? "Play animation" : "Pause animation"}
        onClick={() => setPaused((value) => !value)}
      >
        {paused ? "Play" : "Pause"}
      </button>
    </div>
  );
}

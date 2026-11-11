"use client";

import { useEffect, useState } from "react";
import {
  EDGES,
  HOLD_MS,
  REST_MS,
  STEP_MS,
  VERTEX_COUNT,
  maxClique,
  position,
  type Frame,
} from "@/lib/search";

const EMPTY: Frame = { best: [], at: -1, improved: false };

function cliqueLabel(count: number): string {
  if (count === 0) return "best clique, none yet";
  if (count === 1) return "best clique of 1 vertex";
  return `best clique of ${count} vertices`;
}

export function GraphFigure() {
  const [frame, setFrame] = useState<Frame>(EMPTY);
  const [phase, setPhase] = useState("searching");

  useEffect(() => {
    let timer = 0;
    let cancelled = false;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const finish = (best: number[]) => {
      setFrame({ best, at: -1, improved: false });
      setPhase("complete");
    };

    const start = () => {
      if (cancelled) return;
      setPhase("searching");
      const gen = maxClique();

      if (motion.matches) {
        let best: number[] = [];
        let step = gen.next();
        while (!step.done) {
          best = step.value.best;
          step = gen.next();
        }
        finish(best);
        timer = window.setTimeout(start, REST_MS);
        return;
      }

      const tick = () => {
        if (cancelled) return;
        const step = gen.next();
        if (step.done) {
          setFrame((current) => ({ ...current, at: -1 }));
          setPhase("complete");
          timer = window.setTimeout(start, REST_MS);
          return;
        }
        setFrame(step.value);
        timer = window.setTimeout(tick, step.value.improved ? HOLD_MS : STEP_MS);
      };
      tick();
    };

    start();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  const chosen = new Set(frame.best);
  const count = frame.best.length;
  const label = cliqueLabel(count);

  return (
    <figure className="figure">
      <div className="figure-bar">
        <span>undirected graph</span>
        <span className={`phase phase-${phase}`}>
          <i aria-hidden="true" />
          {phase}
        </span>
      </div>
      <svg viewBox="0 0 640 560" role="img" aria-label={`${label}. pink marks the best clique found so far.`}>
        <title>{`${label}. pink marks the best clique found so far.`}</title>
        <g>
          {EDGES.map(([a, b]) => {
            const on = chosen.has(a) && chosen.has(b);
            const [x1, y1] = position(a);
            const [x2, y2] = position(b);
            return (
              <line
                key={`${a}-${b}`}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                className={on ? "edge edge-on" : "edge"}
              />
            );
          })}
        </g>
        <g>
          {Array.from({ length: VERTEX_COUNT }, (_, vertex) => {
            const on = chosen.has(vertex);
            const [cx, cy] = position(vertex);
            return (
              <circle
                key={vertex}
                cx={cx}
                cy={cy}
                r={on ? 7.4 : 5.2}
                className={on ? "vertex vertex-on" : "vertex"}
              />
            );
          })}
          {frame.at >= 0 && (
            <circle
              cx={position(frame.at)[0]}
              cy={position(frame.at)[1]}
              r={11}
              className="probe"
            />
          )}
        </g>
      </svg>
      <figcaption>
        <span className="count" aria-hidden="true">
          {count === 0 ? "–" : count}
        </span>
        <span>
          <strong id="best-clique">{label}</strong>
          <em>maximum clique, one graph, yielded a step at a time</em>
        </span>
      </figcaption>
    </figure>
  );
}

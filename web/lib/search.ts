export const VERTEX_COUNT = 18;

export const EDGES: ReadonlyArray<readonly [number, number]> = [
  [0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9],
  [9, 10], [10, 11], [11, 12], [12, 13], [13, 14], [14, 15], [15, 16], [16, 17], [0, 17],
  [0, 3], [1, 4], [3, 6], [4, 7], [0, 5], [1, 6],
  [2, 5], [2, 8], [2, 11], [5, 8], [5, 11], [8, 11],
  [7, 10], [7, 12], [7, 14], [7, 16], [10, 12], [10, 14], [10, 16], [12, 14], [12, 16], [14, 16],
  [9, 11], [9, 13], [9, 14], [9, 16], [9, 17], [11, 13], [11, 14], [11, 16], [11, 17],
  [13, 16], [13, 17], [14, 17],
];

export const STEP_MS = 110;
export const HOLD_MS = 900;
export const REST_MS = 3200;

export type Frame = {
  best: number[];
  at: number;
  improved: boolean;
};

const adjacent: boolean[][] = Array.from({ length: VERTEX_COUNT }, () =>
  Array(VERTEX_COUNT).fill(false),
);

for (const [a, b] of EDGES) {
  adjacent[a][b] = true;
  adjacent[b][a] = true;
}

export function position(vertex: number): [number, number] {
  const angle = -Math.PI / 2 + (vertex / VERTEX_COUNT) * Math.PI * 2;
  return [320 + 214 * Math.cos(angle), 278 + 214 * Math.sin(angle)];
}

function touchesAll(vertex: number, clique: number[]): boolean {
  return clique.every((member) => adjacent[vertex][member]);
}

/** Yields once per call so a timer, not the search, owns the clock. */
export function* maxClique(): Generator<Frame> {
  let best: number[] = [];

  function* walk(i: number, clique: number[]): Generator<Frame> {
    let improved = false;
    if (clique.length > best.length) {
      best = clique.slice();
      improved = true;
    }
    yield {
      best: best.slice(),
      at: i < VERTEX_COUNT ? i : -1,
      improved,
    };
    if (clique.length + (VERTEX_COUNT - i) <= best.length || i === VERTEX_COUNT) return;
    if (touchesAll(i, clique)) {
      clique.push(i);
      yield* walk(i + 1, clique);
      clique.pop();
    }
    yield* walk(i + 1, clique);
  }

  yield* walk(0, []);
}

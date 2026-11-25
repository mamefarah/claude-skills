/**
 * Locks: a flight of five canal locks stepping down, one per stage of a POS
 * sale. The pointer picks a lock; its gate sinks and its water drains to the
 * next, then each lock below it opens and drains in turn, staggered outwards
 * from the pointer on the 700ms lift curve. The locks above it stay full and
 * shut. A lock's dots say which stage it is. The slider is the stagger, in ms.
 *
 * The pattern: one of many, on stepped parts. Tweens, a stagger by distance,
 * and a hit test against each lock's own resting top, which never moves.
 */
const {
  Cam, clamp, facing, fit, hull, open, poly, proj, prism, rings, ringAt, rrect, run, unproj,
  tdone, tset, tval, tween, disposer, flatDot, mk, place, pointer, put, register, solid,
} = HL;

const N = 5, LX = 42, LY = 48, WT = 2.8, WR = 6, GH = 18, GOPEN = 0.6;
const NAMES = ["find", "qty", "check", "pay", "done"];
const topOf = (i) => 22 + (N - 1 - i) * 13;
const DIP_REST = [2, 3, 4, 5, 6], GATE_REST = [GH, GH, GH, 14, 10], DIP_FULL = 2, DIP_DRAIN = 14;

/** A run of points ordered left to right on screen. */
const LR = (pts) => (pts[0][0] <= pts[pts.length - 1][0] ? pts : pts.slice().reverse());

function mount({ stage, svg, read }, value) {
  const bag = disposer();
  let stag = value;

  const C = Cam(45, 0.5, 1.32);
  fit(C, [[0, 0, 0], [N * LX, LY, 0], [N * LX, 0, 0], [0, LY, 0], [0, 0, topOf(0) + GH], [0, LY, topOf(0)]], 200, 166);
  const P = proj(C), front = facing(C);

  const g = mk("g", {}, svg), locks = [];
  for (let i = 0; i < N; i++) {
    const x0 = i * LX, x1 = x0 + LX, wh = topOf(i);
    const outer = rrect(x0, 0, x1, LY, WR, 6), inner = rrect(x0 + WT, WT, x1 - WT, LY - WT, WR - WT, 6);
    const lock = mk("g", {}, g);
    // far half: the body, and the rim's inner edge
    mk("path", { d: poly(hull(ringAt(P, outer, 0).concat(ringAt(P, outer, wh)))), class: "sil" }, lock);
    mk("path", { d: poly(ringAt(P, inner, wh)), class: "nf" }, lock);
    const water = mk("path", { class: "" }, lock);
    // near half: one opaque piece from the rim's inner edge down to the ground, over any water that sank behind it
    const iF = LR(ringAt(P, run(inner, front), wh)), oT = LR(ringAt(P, run(outer, front), wh)), oB = LR(ringAt(P, run(outer, front), 0));
    mk("path", { d: poly([...iF, oT[oT.length - 1], ...oB.slice().reverse(), oT[0]]), class: "fo" }, lock);
    mk("path", { d: open(oT), class: "nf lo" }, lock);
    mk("path", { d: open(iF), class: "nf" }, lock);
    mk("path", { d: open([oT[0], ...oB, oT[oT.length - 1]]), class: "nf sil" }, lock);
    // the stage, as dots on the near wall: one for the first lock, five for the last
    const dots = [];
    for (let k = 0; k <= i; k++) {
      const d = flatDot(lock, C, 0.8, "dot off");
      place(d, P(x0 + 9 + k * 4.6, LY - WT / 2, wh));
      dots.push(d);
    }
    const [gr, gi] = rings(x1 - WT, WT, x1, LY - WT, 1.2, 0.5);
    locks.push({ i, wh, inner, water, dots, gate: solid(lock), gr, gi, lv: tween(DIP_REST[i]), gt: tween(GATE_REST[i]), drawn: [NaN, NaN] });
  }

  function draw(L, now) {
    const dip = tval(L.lv, now), gh = tval(L.gt, now);
    if (dip !== L.drawn[0]) L.water.setAttribute("d", poly(ringAt(P, L.inner, L.wh - dip)));
    if (gh !== L.drawn[1]) put(L.gate, prism(P, front, L.gr, L.gi, L.wh, L.wh + gh));
    L.drawn = [dip, gh];
  }

  let act = -1;
  function light() {
    const lit = act < 0 ? 0 : act;
    for (const L of locks) {
      L.water.classList.toggle("hi", L.i === lit);
      L.dots.forEach((d) => d.setAttribute("class", L.i === lit ? "dot" : "dot off"));
    }
  }
  light();

  const B = register(stage, (_dt, now) => {
    let moving = false;
    for (const L of locks) { draw(L, now); if (!tdone(L.lv, now) || !tdone(L.gt, now)) moving = true; }
    return moving;
  });
  bag.add(B.unregister);

  /** Picks lock a (-1 lets go). The stagger spreads out from the lock picked, or the one let go. */
  function setActive(a) {
    if (a === act) return;
    const now = performance.now(), from = a >= 0 ? a : act;
    act = a;
    for (const L of locks) {
      const delay = Math.abs(L.i - from) * stag, below = a >= 0 && L.i >= a;
      const dip = a < 0 ? DIP_REST[L.i] : below ? DIP_DRAIN : DIP_FULL;
      tset(L.lv, dip, now, delay);
      tset(L.gt, a < 0 ? GATE_REST[L.i] : below ? GOPEN : GH, now, delay);
    }
    light();
    read.textContent = a < 0 ? "rest" : NAMES[a];
    B.wake();
  }

  // hit test: each lock's own resting top is a fixed plane; the pointer is on the lock whose middle it lands nearest
  function hit([sx, sy]) {
    let best = -1, bd = Infinity;
    for (const L of locks) {
      const [x, y] = unproj(C, sx, sy, L.wh), u = (x - (L.i + 0.5) * LX) / (LX / 2 + 2), v = (y - LY / 2) / (LY / 2 + 2);
      const d = Math.max(Math.abs(u), Math.abs(v));
      if (d <= 1 && d < bd) { bd = d; best = L.i; }
    }
    return best;
  }

  bag.add(pointer(stage, { move: (p) => setActive(hit(p)), leave: () => setActive(-1) }));
  bag.add(() => svg.replaceChildren());

  return {
    set: (v) => { stag = v; },
    destroy: bag.dispose,
  };
}

hairline({
  name: "locks",
  means: "Five locks step down a sale: the one picked opens and drains, and each lock below it follows in turn.",
  rules: [1, 2, 5, 8],
  range: [0, 60, 120],
  tour: [[121, 95], [200, 164], [278, 233], null],
  mount,
});

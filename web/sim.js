// Cooking model for the carbonara slice: pan and food temperatures, guanciale
// rendering, and egg-sauce chemistry. Pure logic, no rendering. Times are in
// simulated seconds; temperatures in \u00b0C.

export const HEAT = [
  { name: 'Off', target: 22 },
  { name: 'Low', target: 150 },
  { name: 'Medium', target: 195 },
  { name: 'High', target: 245 },
];

export const TOSS = ['Slow', 'Medium', 'Fast'];

// Egg-yolk proteins start to thicken around 62\u00b0C and set firm above ~70\u00b0C.
export const YOLK_THICKENS = 62;
export const YOLK_SCRAMBLES = 70;

export function newState() {
  return {
    simTime: 0,
    heat: 0,
    panTemp: 22,
    // guanciale
    render: 0,      // fraction of fat melted out
    brown: 0,       // Maillard browning on the meat
    burn: 0,        // char
    guancialeDone: false,
    // pasta and sauce
    pastaIn: false,
    savedWater: false,
    eggsIn: false,
    foodTemp: 22,
    thicken: 0,     // how far the yolk has thickened into a sauce
    curds: 0,       // how much has scrambled into solid lumps
    fluid: 0.3,     // free liquid (pasta water + fat) loosening the sauce
    toss: 1,
    plated: false,
    outcomes: [],
  };
}

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

export function stepModel(s, dt) {
  const target = HEAT[s.heat].target;
  // A loaded pan (pasta in it) heats more slowly; cast iron cools slowly.
  const tau = target > s.panTemp ? (s.pastaIn ? 90 : 45) : (s.pastaIn ? 110 : 150);
  s.panTemp += (target - s.panTemp) * (1 - Math.exp(-dt / tau));

  if (!s.pastaIn && !s.guancialeDone && s.tofuInPan !== false) {
    // Fat melts out above ~100\u00b0C; browning needs ~140\u00b0C+; charring above ~215\u00b0C.
    s.render = clamp(s.render + dt * Math.max(0, s.panTemp - 100) / 100 / 240);
    s.brown = clamp(s.brown + dt * Math.max(0, s.panTemp - 140) / 100 / 200 * (0.3 + s.render), 0, 1.3);
    s.burn = clamp(s.burn + dt * (Math.max(0, s.panTemp - 215) / 100 / 40 + Math.max(0, s.brown - 1) * 0.012));
  } else if (s.pastaIn) {
    // Cold food pulls heat out of the pan, too.
    s.panTemp += (s.foodTemp - s.panTemp) * (1 - Math.exp(-dt / 260));
    const contact = [1.35, 1, 0.6][s.toss];      // slow tossing = more time on the hot metal
    const airTau = [420, 220, 90][s.toss];       // fast tossing = more evaporation and cooling
    s.foodTemp += ((s.panTemp - s.foodTemp) / 140 * contact - (s.foodTemp - 25) / airTau) * dt;
    if (!s.eggsIn) s.foodTemp = Math.min(s.foodTemp, 100);  // water boils off at 100\u00b0C
    if (s.eggsIn) {
      const T = s.foodTemp;
      s.thicken = clamp(s.thicken + dt * clamp((T - 55) / 15, 0, 1.2) / 30);
      s.curds = clamp(s.curds + dt * Math.max(0, T - YOLK_SCRAMBLES) / 10 / 7);
      s.fluid = clamp(s.fluid - dt * Math.max(0, T - 55) / 45 * 0.006);
    }
  }
  s.simTime += dt;
}

export function addPasta(s) {
  s.pastaIn = true;
  s.foodTemp = 88;                 // drained pasta, straight from the pot
}

export function addEggs(s) {
  s.eggsIn = true;
  // Room-temperature egg and cheese (about 45% of the mass) cool the hot pasta.
  s.foodTemp = 0.55 * Math.min(s.foodTemp, 95) + 0.45 * 20;
}

export function splashWater(s) {
  if (!s.savedWater) return false;
  s.foodTemp -= 5;
  s.fluid = clamp(s.fluid + 0.22);
  s.thicken = clamp(s.thicken - 0.04);
  return true;
}

// ---------- outcomes ----------
// grade: 'perfect' | 'ok' (recoverable or degraded, the game continues) | 'fatal' (game over)

export function judgeGuanciale(s) {
  if (s.burn >= 0.5) return { grade: 'fatal', title: 'Burnt guanciale', detail: 'The edges charred black. Burnt fat tastes acrid and would ruin the whole dish.' };
  if (s.burn >= 0.2) return { grade: 'ok', title: 'Slightly scorched', detail: 'Some edges caught. You will taste a bitter note.' };
  if (s.render < 0.55) return { grade: 'ok', title: 'Chewy and fatty', detail: 'The fat never melted out, so the pieces are rubbery and there is little fat to build the sauce.' };
  if (s.brown < 0.3) return { grade: 'ok', title: 'Pale and soft', detail: 'Rendered, but no browning. It needed a little more heat or time for crisp, savoury edges.' };
  return { grade: 'perfect', title: 'Crisp and golden', detail: 'Fat rendered out clear, edges browned. Crisp outside, still tender inside.' };
}

export function judgeWater(s) {
  return s.savedWater
    ? { grade: 'perfect', title: 'Saved the pasta water', detail: 'Starchy water is the glue that binds fat, cheese and yolk into a smooth sauce.' }
    : { grade: 'ok', title: 'Drained it all', detail: 'Without starchy water you lose your best tool for loosening and cooling the sauce.' };
}

export function judgeSauce(s) {
  if (s.curds >= 0.65) return { grade: 'fatal', title: 'Scrambled eggs', detail: 'The sauce went past 70\u00b0C. Yolk proteins bonded into firm curds instead of a sauce.' };
  if (s.curds >= 0.3) return { grade: 'ok', title: 'Grainy sauce', detail: 'Parts of the egg set into small curds. Still tasty, but not silky.' };
  if (s.thicken < 0.45) return { grade: 'ok', title: 'Runny sauce', detail: 'The eggs never spent enough time above ~60\u00b0C to thicken. It pools at the bottom of the pan.' };
  if (s.thicken > 0.85 && s.fluid < 0.12) return { grade: 'ok', title: 'Tight and gloopy', detail: 'Thick and sticky. A splash of pasta water would have loosened it to a glossy coat.' };
  return { grade: 'perfect', title: 'Silky sauce', detail: 'Thickened between 62 and 70\u00b0C and loosened with starch: a glossy coat that clings to every strand.' };
}

export function finalVerdict(outcomes) {
  if (outcomes.some(o => o.grade === 'fatal')) return { title: 'Into the bin', blurb: 'One mistake you can\u2019t undo. Every cook has made it. Try again.' };
  const perfect = outcomes.filter(o => o.grade === 'perfect').length;
  if (perfect === outcomes.length) return { title: 'Nonna-approved', blurb: 'Crisp guanciale, silky sauce, nothing wasted. That\u2019s carbonara.' };
  if (perfect >= outcomes.length - 1) return { title: 'Very good', blurb: 'One thing to tighten up next time, but you\u2019d happily eat this.' };
  return { title: 'Edible', blurb: 'It\u2019s dinner. The notes below show what to change.' };
}

// ---------- live descriptions ----------

export function sauceState(s) {
  if (!s.eggsIn) return '';
  if (s.curds >= 0.3) return 'Scrambling';
  if (s.curds >= 0.08) return 'Getting grainy';
  if (s.thicken >= 0.6) return 'Silky';
  if (s.thicken >= 0.25) return 'Thickening';
  return 'Raw and runny';
}

export function guancialeLook(s) {
  if (s.burn >= 0.2) return 'Smoking, edges blackening';
  if (s.brown >= 0.35 && s.render >= 0.55) return 'Golden, crisp edges';
  if (s.render >= 0.55) return 'Fat turning clear, little colour';
  if (s.render >= 0.2) return 'Starting to sweat fat';
  return 'Raw, waxy and pale';
}

// Runs the simulation script in flow.json (exported from design/carbonara_simulation_flow.xlsx).
// Knows nothing about 3D or the DOM: main.js renders what the engine reports and calls back in.
//
// Substep types
//   MCQ - Single select  choose(optionId)
//   MCQ - Multi select   check(selectedIds)  pass = every Correct picked and no Incorrect
//   Procedure            perform(actionId)    numeric Order = required sequence,
//                                             '-' = wrong action, 'opt' = optional helper
// Branch: NEXT / RETRY / GAME_OVER (ending named in the State effect, e.g. "ending = FATAL-SALT")

export class FlowEngine {
  constructor(data) {
    this.data = data;
    this.byId = Object.fromEntries(data.substeps.map((s) => [s.id, s]));
    this.steps = [...new Set(data.substeps.map((s) => s.step))];
    this.reset();
  }

  reset() {
    this.score = Number(this.data.thresholds['Starting score'] ?? 100);
    this.notes = [];            // degraded / fatal moments for the result screen
    this.mistakes = 0;
    this.sub = null;
    this.ended = null;
  }

  start() { return this.enter(this.data.substeps[0].id); }

  enter(id) {
    const sub = this.byId[id];
    this.sub = sub;
    this.attempts = 0;
    this.misses = 0;
    this.done = new Set();      // performed action IDs (correct steps and one-off wrong ones)
    this.ready = false;         // substep finished; waiting for Continue
    this.revealed = null;
    return sub;
  }

  // ---------- lookups ----------
  options(sub = this.sub) { return this.data.options.filter((o) => o.sub === sub.id); }
  actions(sub = this.sub) { return this.data.actions.filter((a) => a.sub === sub.id); }
  tip(sub = this.sub) { return sub.tip ? this.data.tips[sub.tip] : null; }
  item(id) { return this.data.items[id] || { id, name: id, location: 'Right panel' }; }
  stepIndex(sub = this.sub) { return this.steps.indexOf(sub.step) + 1; }
  required(sub = this.sub) {
    return this.actions(sub).filter((a) => /^\d+$/.test(a.order)).sort((x, y) => +x.order - +y.order);
  }
  nextRequired() { return this.required().find((a) => !this.done.has(a.id)) || null; }
  available() {
    // Actions the learner can still pick: unfinished required steps, unused wrong actions, all optional ones.
    return this.actions().filter((a) => a.order === 'opt' || !this.done.has(a.id));
  }

  // ---------- shared outcome handling ----------
  _apply(row, label, feedback) {
    this.score += row.score || 0;
    if (row.correctness === 'Incorrect' || row.outcome === 'Recoverable') this.mistakes += 1;
    if (row.outcome === 'Degraded' || row.outcome === 'Fatal') {
      this.notes.push({ sub: this.sub.id, title: label, outcome: row.outcome, feedback });
    }
    if (row.branch === 'GAME_OVER') {
      const m = /ending\s*=\s*([A-Z0-9-]+)/.exec(row.effect || '');
      this.ended = m ? m[1] : 'FATAL-SCRAMBLED';
    }
  }

  // ---------- MCQ single ----------
  choose(optionId) {
    const o = this.data.options.find((x) => x.id === optionId);
    this._apply(o, o.label, o.feedback);
    const res = { row: o, feedback: o.feedback, outcome: o.outcome, gameOver: !!this.ended };
    if (this.ended) return res;
    if (o.branch === 'RETRY') {
      this.attempts += 1;
      if (this.attempts >= this.sub.maxAttempts) {
        this.revealed = this.options().filter((x) => x.correctness === 'Correct').map((x) => x.id);
        this.ready = true;
        res.reveal = this.revealed;
      }
      return res;
    }
    this.ready = true;
    return res;
  }

  // ---------- MCQ multi ----------
  check(selected) {
    const opts = this.options();
    const picked = opts.filter((o) => selected.has(o.id));
    const wrong = picked.filter((o) => o.correctness === 'Incorrect');
    const missing = opts.filter((o) => o.correctness === 'Correct' && !selected.has(o.id));
    const res = { wrong, missing, acceptable: picked.filter((o) => o.correctness === 'Acceptable') };
    if (!wrong.length && !missing.length) {
      this.ready = true;
      res.pass = true;
      return res;
    }
    wrong.forEach((o) => this._apply(o, o.label, o.feedback));
    this.attempts += 1;
    if (this.attempts >= this.sub.maxAttempts) {
      this.revealed = opts.filter((o) => o.correctness !== 'Incorrect').map((o) => o.id);
      this.ready = true;
      res.reveal = this.revealed;
    }
    return res;
  }

  // ---------- procedure ----------
  perform(actionId) {
    const a = this.data.actions.find((x) => x.id === actionId);
    const res = { row: a };
    if (/^\d+$/.test(a.order)) {
      const next = this.nextRequired();
      if (next && a.id !== next.id) {
        this.misses += 1;
        res.outOfOrder = true;
        res.feedback = a.badFb || 'Not yet. Something else comes first.';
        if (this.misses >= this.sub.maxAttempts) res.hint = next;
        return res;
      }
      this.done.add(a.id);
      this.misses = 0;
      res.ok = true;
      res.feedback = a.okFb;
      if (!this.nextRequired()) { this.ready = true; res.complete = true; }
      return res;
    }
    // Optional helper: just feedback, never counted as a mistake.
    if (a.order === 'opt') {
      res.feedback = a.badFb || a.okFb;
      res.optional = true;
      return res;
    }
    // Wrong action ('-').
    this.done.add(a.id);
    res.feedback = a.badFb || a.okFb;
    res.outcome = a.outcome;
    this._apply(a, a.param, res.feedback);
    res.gameOver = !!this.ended;
    if (a.branch === 'RETRY') this.done.delete(a.id);
    return res;
  }

  // ---------- ending ----------
  ending() {
    const byId = Object.fromEntries(this.data.outcomes.map((o) => [o.id, o]));
    if (this.ended) return { ...byId[this.ended], fatal: true };
    const t = this.data.thresholds;
    const id = this.score >= t['END-PERFECT minimum'] ? 'END-PERFECT'
      : this.score >= t['END-GOOD minimum'] ? 'END-GOOD'
        : this.score >= t['END-OK minimum'] ? 'END-OK' : 'END-POOR';
    return { ...byId[id], fatal: false };
  }
}

// The only side effect is a reviewer-requested JSON download.
const snapshot = JSON.parse(document.querySelector('#snapshot').textContent);
const video = document.querySelector('video');
const rows = [...document.querySelectorAll('tbody tr')];
const error = document.querySelector('#error');
let stopAt = null;
video.ontimeupdate = () => { if (stopAt !== null && video.currentTime >= stopAt) { video.pause(); stopAt = null; } };
for (const row of rows) {
  const original = snapshot.intervals[Number(row.dataset.index)];
  row.querySelector('.listen').onclick = () => {
    video.currentTime = Math.max(0, original.start / snapshot.sample_rate - .8);
    stopAt = Math.min(snapshot.frames / snapshot.sample_rate, original.end / snapshot.sample_rate + .8);
    video.play().catch(e => { error.textContent = e.message; });
  };
  row.querySelector('.decision').onchange = () => {
    const action = row.querySelector('.decision').value;
    row.querySelector('.start').disabled = !['ADJUST_START', 'ADJUST_BOTH'].includes(action);
    row.querySelector('.end').disabled = !['ADJUST_END', 'ADJUST_BOTH'].includes(action);
  };
}
document.querySelector('#export').onclick = () => {
  error.textContent = '';
  try {
    const reviewer = document.querySelector('#reviewer').value.trim();
    if (!reviewer) throw Error('Reviewer obligatoriu.');
    const decisions = [], intervals = snapshot.intervals.map(v => ({...v}));
    for (const row of rows) {
      const action = row.querySelector('.decision').value;
      if (!action) continue;
      const index = Number(row.dataset.index), decision = {index, action, note: row.querySelector('.note').value};
      for (const field of ['start', 'end']) {
        if (row.querySelector('.' + field).disabled) continue;
        const text = row.querySelector('.' + field).value.trim(), value = Number(text);
        if (!text || !Number.isFinite(value)) throw Error('Valoare de timp invalidă.');
        decision[field] = Math.round(value * snapshot.sample_rate);
        if (!Number.isSafeInteger(decision[field])) throw Error('Timp în afara preciziei întregi.');
        intervals[index][field] = decision[field];
      }
      decisions.push(decision);
    }
    if (!decisions.length) throw Error('Export gol: selectează o decizie explicită.');
    let cursor = 0;
    for (const interval of intervals) {
      if (!(cursor <= interval.start && interval.start < interval.end && interval.end <= snapshot.frames)) throw Error('Interval invalid, negativ, suprapus sau peste audio.');
      cursor = interval.end;
    }
    const {intervals: ignored, ...identity} = snapshot;
    const output = {...identity, reviewer, reviewed_utc: new Date().toISOString(), decisions};
    const blob = new Blob([JSON.stringify(output, null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = 'ctc-decisions.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) { error.textContent = e.message; }
};

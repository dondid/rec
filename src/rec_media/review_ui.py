"""Offline review page; exporting never applies decisions to the material."""
import html
import json
import os
from pathlib import Path
from urllib.parse import quote
from . import core


def generate(document,material,report,output,media=None):
    output=Path(output);source=Path(media).resolve() if media else None
    if source is None and len(material['timeline'])==1 and material['timeline'][0]['start']==0:
        source=core.checked(document,material['timeline'][0]['source'])
    if source is not None and not source.is_file():raise ValueError('Sursa playback lipsește.')
    url=quote(Path(os.path.relpath(source,output.parent)).as_posix()) if source else ''
    rows=[];words=material['alignment']['words']
    for segment,units in report['segments'].items():
        for unit in units:
            i=unit['index'];context=' '.join(w.get('display',w['spoken']) for w in words[max(0,i-4):i+5])
            opts=''.join(f'<option value="{a}">{a}</option>' for a in ['ACCEPT','ADJUST_START','ADJUST_END','ADJUST_BOTH','REJECT','NEEDS_REVIEW'])
            rows.append(f'''<tr data-index="{i}"><td>{segment} / {i}</td><td>{html.escape(unit['word'])}<details><summary>Context</summary>{html.escape(context)}</details></td>
<td>{unit['confidence']}</td><td>{unit['start']}–{unit['end']} samples<br>{unit['start']/report['sample_rate']:.6f}–{unit['end']/report['sample_rate']:.6f} s</td>
<td><button class="listen" {'disabled' if not source else ''}>Redă intervalul</button></td>
<td><select class="decision"><option value="">Fără decizie</option>{opts}</select></td>
<td><label>Start (s)<input class="start" type="number" step="0.000001" value="{unit['start']/report['sample_rate']:.6f}" disabled></label>
<label>End (s)<input class="end" type="number" step="0.000001" value="{unit['end']/report['sample_rate']:.6f}" disabled></label></td><td><input class="note" aria-label="Notă"></td></tr>''')
    data={k:report[k] for k in ['schema_version','material','alignment_key','source_text_sha256','audio_sha256','sample_rate','frames','intervals']}
    payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    normalizations=html.escape(json.dumps(report['normalizations'],ensure_ascii=False,indent=2))
    script=Path(__file__).with_name('ctc_review.js').read_text()
    text='''<!doctype html><html lang="ro"><meta charset="utf-8"><title>REC CTC review</title>
<style>body{font:15px system-ui;background:#13232e;color:#eef4f7;margin:20px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border:1px solid #718998}input,select,button{padding:6px;background:#263e50;color:white;border:1px solid #849aaa}input[type=number]{width:110px}input:disabled{opacity:.55}label{display:block}.player{position:sticky;top:0;background:#13232e;padding:12px}video{max-height:36vh;max-width:100%}#error{color:#ffc27d;white-space:pre-wrap}</style>
<h1>CTC review · explicit decisions</h1><p>Timpi existenți; fără ASR sau aliniere nouă. Sfârșitul CTC nu este automat sfârșitul acustic al cuvântului. Confirmă prin audiție și forma de undă. Exportul JSON nu aplică decizii.</p>
<details><summary>Normalizări păstrate</summary><pre>NORMALIZATIONS</pre></details>
<div class="player"><video controls preload="metadata" src="SOURCE"></video><label>Reviewer <input id="reviewer"></label><button id="export">Exportă decizii</button><p id="error" role="alert"></p></div>
<table><thead><tr><th>Segment/index (zero-based)</th><th>Text</th><th>Confidence</th><th>Timpi originali</th><th>Playback</th><th>Decizie</th><th>Corecții</th><th>Notă</th></tr></thead><tbody>ROWS</tbody></table>
<script id="snapshot" type="application/json">PAYLOAD</script><script>SCRIPT</script></html>'''
    text=text.replace('NORMALIZATIONS',normalizations).replace('SOURCE',html.escape(url)).replace('ROWS',''.join(rows)).replace('PAYLOAD',payload).replace('<script>SCRIPT</script>','<script>'+script+'</script>')
    output.write_text(text,encoding='utf-8')
    return str(output)

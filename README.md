# REC: text românesc → MP3 local

Utilitar CLI pentru conversia integrală a unui fișier `.txt` UTF-8 în MP3, folosind Python, **Piper 1.8.0**, vocea fixă **ro_RO-mihai-medium** și FFmpeg, pe CPU. După instalare și descărcarea explicită a modelului, conversia funcționează offline. Nu există interfață grafică, server, conturi, chei API, abonamente sau clonare de voce.

Extensia media are CLI separat `./media`; starea și cerințele consolidate sunt în [planul media canonic](docs/PLAN_EXTINDERE_MEDIA_REC.md). Funcțiile testate și cele rămase sunt descrise mai jos, fără schimbarea fluxului audio.

## Comanda uzuală în mediul deja funcțional

Salvează textul tău în `input/text.txt`, apoi rulează:

```bash
cd /home/daniel/projects/rec &&
./tts render input/text.txt -o output/text.mp3 --force &&
./tts verify output/text.mp3
```

`--force` permite înlocuirea MP3-ului și a raportului de la aceeași destinație; nu obligă resinteza segmentelor valide din cache. Nu arhivează automat versiunea anterioară. Pentru a o păstra, alege înainte de conversie un nume nou, de exemplu `-o output/text_v2.mp3`, sau salvează separat MP3-ul și raportul anterior.

Rezultatul este în `/home/daniel/projects/rec/output/`. Din Windows:

```text
\\wsl.localhost\Debian\home\daniel\projects\rec\output
```

Mediul local este deja instalat. **Nu este necesară reinstalarea pentru utilizarea curentă.** Istoricul testelor, conversiile reale și experimentele de pronunție sunt documentate separat în [TEST_RESULTS.md](TEST_RESULTS.md). Rularea de referință din 16 octombrie 2026 este `20261016T090507-5f8a96d4`, pe versiunea corectată a textului: 30/30 segmente, export tehnic reușit. Aceasta este o verificare tehnică, fără aprobare auditivă consemnată.

## Textul și comenzile disponibile

Editează sau copiază propriul text în `input/text.txt`, cu salvare UTF-8. BOM, CRLF și numele cu spații/diacritice sunt acceptate. O codare invalidă produce eroare, fără ignorarea octeților. Pregătirea normalizează NFC, newline-urile, spațiile redundante și sedilele românești; păstrează alineatele și punctuația. Fișierul original nu este rescris și nu se inventează diacritice lipsă.

| Comandă | Rol |
|---|---|
| `./tts doctor` | Diagnostic local pentru Python, dependențe, model/checksum, CPU provider, FFmpeg/ffprobe, libmp3lame, loudnorm, permisiuni și spațiu. Nu descarcă nimic. |
| `./tts prepare input/text.txt --output-dir work/review-text-v2` | Scrie `normalized.txt`, `segments.json`, `warnings.json`, fără sinteză. Alege un director nou la schimbarea textului: fișierele review existente nu sunt suprascrise. |
| `./tts preview input/text.txt --words 180 -o output/proba_v2.mp3` | Probă parțială până la un sfârșit sigur de propoziție după aproximativ N cuvinte; dacă textul este mai scurt, îl poate include integral. Raportul rămâne marcat ca preview. |
| `./tts render input/text.txt -o output/text_v2.mp3` | Conversie integrală, cu reutilizarea cache-ului valid. |
| `./tts verify output/text.mp3` | Inspectează MP3-ul, îl decodează complet și măsoară nivelul audio. Nu validează pronunția. |

Viteza acceptată este **0.8–1.2**; o valoare mai mare înseamnă vorbire mai rapidă. Adaptorul mapează `length_scale = model_default_length_scale / speed`.

```bash
./tts render input/text.txt -o output/text_lent_v2.mp3 --speed 0.95
./tts render input/text.txt -o output/text_master_v2.mp3 --keep-wav --verbose
```

`--keep-wav` copiază lângă MP3 masterul float fără pierderi **dinaintea normalizării finale**. Dacă acel WAV există deja, este necesar `--force` sau alt nume. `--verbose` afișează progresul segmentelor. `render` și `preview` acceptă `--speed`, `--pronunciations`, `--keep-wav`, `--force`, `--verbose`; `prepare` acceptă `--pronunciations` și `--verbose`. Configurația explicită este o opțiune globală, înainte de subcomandă:

```bash
./tts --config rec.json render input/text.txt -o output/text_config_v2.mp3
```

Wrapperul `tts` folosește `.venv/bin/python` relativ la proiect, fără activare manuală. Căile input/output și cele date explicit se interpretează din directorul apelantului; modelul, `rec.json` și `pronunciations.json` implicite se caută relativ la proiect. Directorul destinației MP3 trebuie să existe. Pentru nume cu spații sau diacritice, pune calea între ghilimele.

## Mediul real și instalarea la nevoie

Dovezile locale din 16 octombrie 2026 indică Debian 13.4 în WSL, x86_64, Python 3.13.5, Piper 1.8.0, ONNX Runtime 1.31.0 cu `CPUExecutionProvider`, SoundFile 0.14.0 și libsndfile 1.2.2 din wheel. Nu s-a instalat CUDA. Verificarea curentă se poate cere cu `./tts doctor`; raportul istoric este [work/doctor.json](work/doctor.json).

FFmpeg și ffprobe **7.0.2-static** sunt instalate în `.tools/ffmpeg/`, deoarece instalarea prin sudo cerea parolă. CLI-ul și bootstrap-ul adaugă această cale la sfârșitul PATH-ului procesului, astfel încât uneltele din sistem au prioritate. Un `ffmpeg` inexistent în PATH-ul terminalului nu demonstrează că lipsește fallback-ul folosit de `./tts`.

```bash
./tts doctor
.tools/ffmpeg/ffmpeg -version
.tools/ffmpeg/ffprobe -version
```

Pentru **un mediu nou sau dependențe într-adevăr lipsă**, calea Debian este:

```bash
cd /home/daniel/projects/rec
sudo apt-get update
sudo apt-get install -y python3 python3-venv ffmpeg libsndfile1 ca-certificates
bash scripts/bootstrap.sh
./tts fetch-model
./tts doctor
```

Alternativa explicită fără sudo, pentru Linux x86_64 și cu `python3`, venv, `curl`, `tar`, `sha256sum` disponibile:

```bash
bash scripts/install-local-ffmpeg.sh
bash scripts/bootstrap.sh
./tts fetch-model
```

Acestea sunt operații de instalare, nu pași necesari înaintea fiecărei conversii. `install-local-ffmpeg.sh` descarcă build-ul fixat de la John Van Sickle, verifică SHA-256 al arhivei testate și păstrează licența/proveniența în `.tools/`; hash-ul local nu este o semnătură independentă a FFmpeg. Dacă executabilele locale există, scriptul le păstrează și le afișează versiunile; nu oferă actualizare automată sau reparare a unei instalări parțiale.

`bootstrap.sh` verifică uneltele, creează `.venv` numai dacă lipsește și instalează cu `--require-hashes` din `requirements.lock`, fără `sudo pip`, `--break-system-packages` sau actualizare automată la randare. Lockfile-ul a fost instalat și într-un mediu curat; compatibilitatea cu alte versiuni Python/arhitecturi nu a fost testată. Dependențele pytest sunt în `requirements-dev.lock`; comenzile istorice de test sunt în [TEST_RESULTS.md](TEST_RESULTS.md).

`fetch-model` este singura comandă de aplicație care descarcă modelul. La prima descărcare identifică o revizie exactă a depozitului oficial; instalarea păstrată este fixată prin `models/piper/model.lock.json` la `c10ece1aade47bb51c153c893d14e5bf8e5b7117`. Lock-ul include surse, dimensiuni și SHA-256. O instalare validă este păstrată; un model corupt sau fișiere existente diferite necesită inspecție și intervenție explicită, fără ștergere automată. Pe o instalare nouă fără lock, revizia descoperită poate diferi. Nicio comandă de generare nu descarcă pachete sau modele.

## Configurație și fișiere

Valorile curente din [rec.json](rec.json), cu opțiunile CLI având prioritate:

| Parametru | Valoare |
|---|---|
| `engine`, `voice` | `piper`, `ro_RO-mihai-medium` |
| `speed` | `1.0` |
| `segment_target_chars`, `segment_max_chars` | `300`, `500` |
| `sentence_gap_ms`, `paragraph_gap_ms` | `150`, `400` |
| `mp3_bitrate`, `channels` | `128k`, `1` |
| `loudness_lufs`, `true_peak_db`, `loudness_range` | `-19.0`, `-2.0`, `11.0` |

Pentru setări fără opțiune CLI, folosește o copie JSON validă prin `--config`. Nu există opțiune CLI `--bitrate`, selecție de alt motor sau manager de versiuni audio.

| Cale | Conținut și rol |
|---|---|
| `tts`, `src/rec_tts/` | Wrapper și implementarea CLI, pregătire text, adaptor Piper, cache și audio. |
| `scripts/`, `requirements*.lock`, `pyproject.toml` | Instalare explicită, versiuni exacte și metadate ale aplicației 1.0.0. |
| `rec.json`, `pronunciations.json` | Configurația și dicționarul general; dicționarul local este în prezent `[]`. |
| `input/` | Texte proprii. |
| `output/` | MP3-uri, rapoarte `*.report.json`, WAV opțional și artefactele comparative de pronunție. |
| `models/piper/` | ONNX, JSON, lock, MODEL_CARD și metadatele depozitului de voci. |
| `work/review*/` | Copii normalizate, segmente și avertismente ale versiunii pregătite atunci. |
| `work/runs/<run-id>/` | `normalized.txt`, `manifest.json` și master RF64 dacă asamblarea a fost atinsă; pot rămâne artefacte și după eșec. |
| `work/cache/` | WAV float32 fără pauzele aplicației, JSON cu checksum și limite interne Piper. |
| `work/pronuntii-experiment/` | Selecția și dovezile experimentului istoric, inclusiv perechile separate SRI/PSD. |
| `samples/`, `tests/` | Texte sintetice și teste; nu înlocuiesc inputul utilizatorului. |
| `.venv/`, `.venv-clean/`, `.tools/` | Mediu de execuție, mediu curat de validare istorică și unelte locale. |
| `licenses/`, `THIRD_PARTY_NOTICES.md` | Licențe și proveniență. |

Textele private, modelele, audio-ul, cache-ul și mediile virtuale sunt excluse prin regulile locale `.gitignore`. Rapoartele conțin căi și checksum-uri; manifestele/review-urile și comparațiile de pronunție conțin textul, deci trebuie tratate ca date private.

## Cache, reluare și protecția exportului

La Ctrl+C sau eroare, segmentele validate rămân pe disc. Repetă comanda: o nouă încercare creează de regulă **un nou run-id**, apoi refolosește segmentele valide din cache; nu continuă prin rescrierea manifestului întrerupt. Stările manifestului sunt `running`, `complete`, `failed`, `interrupted`. Eroarea indică segmentul și manifestul de diagnostic.

Cheia de sinteză depinde de textul exact trimis motorului, versiunea Piper/adaptorului, hash-urile modelului/configurației sale, voce și viteza de sinteză. Nu depinde de numele inputului sau de poziția segmentului. Cache-ul este verificat prin checksum, format, număr de eșantioane, limite și valori finite; un segment corupt este regenerat. Pentru expansiuni peste 500 de caractere, cheia include versiunea mecanismului de împărțire suplimentară.

Schimbarea unui paragraf regenerează segmentele afectate; limitele externe între paragrafe rămân stabile. Modificări într-un singur paragraf foarte lung pot schimba mai multe segmente din acel paragraf. Repetițiile intenționate pot folosi același WAV, dar sunt asamblate în fiecare poziție. Schimbarea numai a bitrate-ului, pauzelor sau normalizării finale nu invalidează sinteza. Modificarea dicționarului nu invalidează segmentele al căror text rostit rămâne identic.

Fără `--force`, un MP3 existent este refuzat, cu excepția aceleiași cereri confirmate de raport, checksum, manifest complet și verificarea audio; atunci poate reveni `already_complete: true`. Excepția nu ocolește protecția unui WAV deja existent cerut prin `--keep-wav`. `--force` reface exportul din sursa fără pierderi, păstrând cache-ul util.

Un lock local refuză comenzi concurente care scriu proiectul. MP3-ul temporar este creat lângă destinație și publicat prin redenumire atomică după verificare. O eroare de sinteză/export înainte de publicare păstrează MP3-ul anterior; `.part` nu este rezultat final. MP3-ul și raportul JSON sunt publicate separat, deci o eroare de scriere a raportului după publicarea MP3 poate lăsa o pereche incompletă; nu există tranzacție comună pentru ele.

Nu există comandă de curățare sau ștergere automată. Masterele RF64, temporarele și cache-ul pot ocupa mult spațiu. Verificările de spațiu din cod sunt praguri minime de 16 MiB, nu estimări ale necesarului întregului document. Arhivează ce trebuie păstrat și curăță numai explicit, după inspecție; păstrarea cache-ului este necesară pentru reluarea cu reutilizare.

## Dicționar și experimente de pronunție

Schema reală este o listă ordonată de înlocuiri literale:

```json
[
  {"match": "API", "say": "interfața de programare", "whole_word": true},
  {"match": "12,5%", "say": "douăsprezece virgulă cinci la sută", "whole_word": false}
]
```

Expresiile mai lungi au prioritate; la lungimi egale se respectă ordinea listei. Potrivirea este sensibilă la majuscule, `whole_word` este implicit `true` și controlează limite Unicode de cuvânt. Nu există regex sau înlocuiri în cascadă în textul nou generat. Regulile se aplică **după segmentarea sursei, separat în fiecare segment**: o expresie care traversează o limită de segment nu se potrivește. `match` și `say` trebuie să fie șiruri ne-goale, iar `say` să conțină text nealb.

Poți folosi explicit exemplul separat, fără să modifici dicționarul general:

```bash
./tts render input/text.txt -o output/text_dictionar_v2.mp3 --pronunciations samples/pronunciations.example.json
```

[Comparația de pronunție](output/pronuntii_comparatie.md) și [regulile experimentale](output/pronuntii_reguli_experimentale.json) aparțin **versiunii anterioare** a textului: 17 forme în 13 propoziții, cu probe originale/propuse și teste separate SRI/PSD. Ele nu sunt corecții aprobate automat și nu sunt încărcate implicit. Interpretările `500:000 → 500.000`, `350:000 → 350.000` și `‘89 → 1989` rămân propuneri neconfirmate din acel experiment; nu trebuie transferate implicit la alte versiuni sau la dicționarul general.

Textul actual și `output/text.mp3` au alt checksum. Rularea actuală are independent 17 avertismente contextuale în propriul manifest, dar vechiul `work/review-text/` nu reprezintă această versiune. Numărul egal nu înseamnă identitate de conținut. Pentru analiza curentă folosește manifestul aferent raportului sau pregătește un review într-un director nou.

## Rapoarte, audio și limite

Rapoartele `*.report.json` leagă sursa prin `source_sha256`, rezultatul prin `output_sha256`, configurația și versiunea/modelul de un `run_id` și de calea `manifest`. Numele `input/text.txt` poate fi același pentru versiuni diferite: identificarea se face prin hash. Un raport vechi `text_lent.report.json` nu dovedește că acel MP3 corespunde textului actual.

| Câmp | Interpretare |
|---|---|
| `segments_expected`, `segments_completed` | Acoperirea la nivelul pipeline-ului; nu dovedește fiecare cuvânt acustic. |
| `cache_hits` | Număr de segmente refolosite în acea rulare, nu număr de cuvinte. |
| `timings.total_seconds` | Timpul total măsurat pentru rularea din raport, nu pentru o verificare ulterioară. |
| `synthesis_seconds`, `generated_audio_seconds`, `rtf` | Sinteză nouă și RTF = timp sinteză / durată nouă; `rtf: null` dacă nu există sinteză nouă. |
| `planned_duration` | Durată calculată din eșantioane și pauze, fără padding-ul MP3. |
| `audio.verification.format.duration` | Durata MP3 raportată de ffprobe; poate diferi ușor de cea planificată. |
| `audio.verification.full_decode` | FFmpeg a decodat integral fișierul fără erori în acea verificare. |
| `audio.verification.measurements.input_i`, `input_tp` | LUFS și true peak măsurate pe MP3-ul decodat; `output_*` descriu filtrarea de măsurare, nu alte măsurători ale fișierului salvat. |
| `audio.attempts[].normalization_type` | Tipul efectiv al normalizării la export; nu se deduce din câmpul omonim al filtrului de măsurare. |
| `technical_status: passed` | Criterii tehnice acceptate la verificarea consemnată. |
| `listening_status: not_listened` | Nu este consemnată o audiție; **nu înseamnă export eșuat**. |

`verify` independent citește media și configurația dată/implicită, fără a confrunta automat sursa curentă sau raportul alăturat. Compararea duratei cu eșantioanele planificate și verificarea ratei modelului se fac intern în fluxul de export/idempotent, unde sunt transmise valorile așteptate. Un `verify` reușit nu înseamnă că MP3-ul provine din versiunea curentă a inputului. Codurile CLI sunt 0 la succes, 1 la erorile gestionate și 130 la Ctrl+C; argparse returnează 2 pentru sintaxă CLI invalidă.

Piper este încărcat o singură dată dacă există segmente de sintetizat, secvențial, pe CPU; la o rulare integral din cache nu este încărcat. Intermediarii sunt float32, iar asamblarea citește blocuri de pe disc în RF64. API-ul Piper 1.8.0 aplică intern clipping float chiar cu `normalize_audio=False`; adaptorul nu adaugă conversie prematură în int16. Parametrii noise rămân cei ai modelului. Generările noi nu sunt garantat identice; cache-ul păstrează audio-ul efectiv produs.

Pauzele de 150 ms între propoziții și 400 ms între paragrafe sunt adaosuri ale aplicației; paragraful înlocuiește pauza externă de propoziție, iar tăierile tehnice nu primesc pauză completă. Sunt alegeri inițiale, nu garanții subiective. Exportul folosește loudnorm în două treceri, `dual_mono=false`, mono, rata nativă 22050 Hz și libmp3lame 128 kb/s. Țintele curente sunt −19 LUFS, −2 dBTP și LRA 11; pentru material de minimum 3 secunde se acceptă ±1 LU, cu true peak decodat cel mult −1 dBTP. Există maximum trei încercări de export cu ajustare din masterul fără pierderi; măsurători nefinite/audio nemăsurabil produc eroare.

Nu există limită arbitrară de document, însă memoria textului și manifestelor, timpul și spațiul pe disc rămân limite reale. Un token indivizibil peste limita segmentului produce eroare explicită, fără trunchiere. Avertismentele de context detectează forme textuale, nu greșeli auzite; nici absența lor nu garantează o lectură corectă. Testele automate și acoperirea textuală nu confirmă naturalețea, intonația, sensul sau pronunția. Aprobarea auditivă rămâne separată.

## Diagnostic și întreținere

| Situație | Acțiune |
|---|---|
| `Destinație existentă` / WAV existent | Alege un nume nou pentru păstrarea versiunii sau folosește explicit `--force`. |
| `Fișier review existent` | Folosește un alt `--output-dir`; `prepare` nu are opțiune `--force`. |
| Model lipsă/invalid ori checksum diferit | Verifică `doctor` și lock-ul; descarcă explicit numai dacă modelul lipsește. Pentru corupție, inspectează și mută separat fișierele înainte de recuperare. |
| `.venv` sau FFmpeg lipsă | Verifică mai întâi calea proiectului și fallback-ul local; folosește pașii de instalare numai pentru componentele lipsă. |
| Input gol / UTF-8 invalid | Corectează salvarea sursei, păstrând o copie; aplicația nu repară automat codarea. |
| Număr, an, URL, siglă, cuvânt cu majuscule avertizat | Citește contextul și ascultă fragmentul; experimentează separat, fără înlocuiri globale riscante ale cifrelor/caracterelor. |
| FFmpeg eșuat / spațiu insuficient / segment eșuat | Citește eroarea și manifestul indicat, verifică discul și destinația; repetă comanda după rezolvarea cauzei. Segmentele valide rămân în cache. |
| Altă comandă folosește proiectul | Așteaptă terminarea procesului activ. Nu șterge arbitrar lock-ul sau cache-ul. |

Licențele și proveniența sunt în [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [licența Piper](licenses/Piper-GPL-3.0.txt) și documentele modelului/uneltelor locale. Licența datasetului nu trebuie confundată cu toate drepturile modelului.

**Regulă de întreținere:** când se schimbă CLI-ul, configurația sau comportamentul aplicației, se actualizează documentația aferentă. Rezultatele testelor se datează și se leagă de rularea/versiunea verificată, păstrând separat testele implementării, experimentele și conversiile reale. O inspecție de documentare nu trebuie prezentată drept o nouă rulare a testelor sau o nouă audiție.


## Extensia media locală — versiunea 0.1.0

Implementarea CPU folosește un singur manifest `material.json` și același renderer pentru materiale integrale, fragmente și compilații. Nu încarcă Piper și nu resintetizează vocea pentru alte profile. `media.json` este separat de `rec.json`; `media` folosește `/usr/bin/python3` cu Pillow **11.1.0 deja instalat în Debian**, iar audio rămâne în `.venv`. Alinierea automată rulează separat în **`.venv-align`**, instalat explicit; mediul audio nu a fost reinstalat. Pinul `requirements-media.lock` consemnează versiunea observată, fără hash-uri de wheel și fără pretenția unei instalări media curate deja validate.

### Starea funcțiilor

| Funcție | Stare verificată la 16 octombrie 2026 UTC |
|---|---|
| Audit audio și hardware | Istoric: 44 teste în copie izolată. Etapa reală: 38 regresii fără resinteză; 4 CPU, 4010608 KiB RAM; GPU/VRAM neexpuse. |
| Materiale, imagine fixă, profile | Testate: 1920×1080, 1080×1920, custom par; H.264/AAC, 30 fps, fără sinteză nouă. |
| Scene/animații | Imagini și clipuri locale; contain/cover, focală, zoom in/out/pan, cut/crossfade și apariție de titlu. |
| Titluri și thumbnail-uri | Extractiv/manual, selecție blocată; imagine+text, scenă aleasă sau copertă grafică; PNG/JPEG, compoziții panel/top. |
| Aliniere și subtitrări | Aliniere automată CPU `ctc-ro` pe vocea reală: 30 ferestre, 1.824 unități, 170 scoruri reduse; import manual păstrat. SRT/ASS, classic real; highlight/scroll testate anterior pe fixture, fără precizie auditivă confirmată. |
| Split/merge | Partition/extract în eșantioane, limite manuale sau alese din aliniere, N părți/durată țintă; compilații interne cu aceeași rată audio. PCM split→merge identic în test. |
| Loturi/relansare | Render/thumbnail/subtitles/titles; checkpoint cu hash-uri și invalidare la schimbări. Joburile eșuate fac lotul eșuat. |
| Backend-uri opționale | WhisperX complet, LLM și generarea de imagini/clipuri nu sunt instalate. Modelul românesc Wav2Vec2 este instalat pentru adaptorul CTC dedicat, fără CUDA/cloud. |

**F2 are acum aliniere automată verificată tehnic pe voce reală; precizia auditivă rămâne nevalidată.** Fixture-urile vechi cu tonuri nu devin probe de vorbire. Nu există măsurare manuală a pragului ±200 ms. Splitul de text și propunerea lexicală sunt implementate în secțiunile de producție de mai jos. Avatar/logo, semantică prin model, mix extern cu resampling, pauze/normalizare la merge și backend-urile AI opționale rămân în [lista canonică de restanțe](docs/PLAN_EXTINDERE_MEDIA_REC.md). Fără GPU, funcțiile CPU continuă.

### Subtitrări automate pentru textul și MP3-ul existente

Materialul real este separat de demonstrații: `materials/real-ro-20261016/`. Importul a confruntat hash-urile din `output/text.report.json` cu textul și MP3-ul actuale și a decodat exact 15.188.520 de eșantioane, fără sinteză. Comenzi executate:

```bash
cd /home/daniel/projects/rec
./media init --id real-ro-20261016 --audio output/text.mp3 --text input/text.txt --tts-report output/text.report.json
./media --report work/media/real-alignment-audit/short-alignment.json align real-ro-20261016 --backend ctc-ro --max-windows 1
./media --report work/media/real-alignment-audit/full-alignment.json align real-ro-20261016 --backend ctc-ro
./media --report work/media/real-alignment-audit/batch-final-result.json batch work/media/real-alignment-audit/batch-final.json
```

`init` se execută o singură dată pentru acel ID; pentru o altă versiune a sursei folosește un ID nou. `--max-windows 1` analizează numai prima fereastră reală TTS (53 de unități aici), salvează proba parțială și **nu atașează o aliniere incompletă materialului**. Comanda fără această opțiune procesează tot textul. Lotul local conține argumentele exacte pentru SRT/ASS, thumbnail-uri și video cu titlu propriu: integral, două fragmente, compilație și proba primei propoziții. Pentru aceste exporturi s-a ales `composition.title_fade_seconds: 0`: titlul fix este compus o singură dată, cu aceeași poziționare pe profil. Fade-ul configurabil rămâne disponibil. Limita sigură dintre fragmente este 348,392 s, în pauza măsurată; eșantioanele split→merge sunt identice. Fișierul lotului conține text privat și rămâne în `work/`, exclus din Git. După terminare, aceeași comandă permite reluarea pe baza hash-urilor.

Rezultatele integrale sunt în `output/media/real-ro-20261016/{landscape,portrait}/video.mp4`; subtitrările în `subtitles/{landscape,portrait}/subtitles.srt` și `subtitles.ass`, împreună cu `alignment.json`. Fragmentele sunt `real-ro-fragment-001` și `real-ro-fragment-002`; compilația este `real-ro-reuniune-20261016`; proba scurtă este `real-ro-proba-sigura-001`. Fiecare folosește același CLI și aceeași voce existentă. Rapoartele `video.report.json` consemnează verificarea fiecărui export; rezultatele și limitele sunt în [TEST_RESULTS.md](TEST_RESULTS.md).

Reperele pentru control manual sunt în `output/media/real-ro-20261016/review/repere.md`: WAV-uri extrase din audio-ul existent, cadre și `checkpoints.json` pentru început/mijloc/final. Nu sunt ancore auditive aprobate. Coperțile geometrice sunt compuse local, fără model generativ sau pretenție de relevanță vizuală semantică. Titlurile sunt propuneri extractive, nu aprobări editoriale.

### Instalarea explicită a alinierii și utilizarea offline

Mediul curent este deja instalat. Pentru o instalare nouă, separată de Piper:

```bash
bash scripts/bootstrap-align.sh
python3 scripts/fetch-alignment-model.py
./media doctor
```

Bootstrap-ul instalează exclusiv în `.venv-align`, din `requirements-align.lock`: PyTorch **2.8.0+cpu**, Transformers **4.56.2**, SoundFile **0.13.1**, num2words **0.5.14** și tranzitive fixate. Lock-ul are versiuni exacte, fără hash-uri de wheel; instalarea într-un al doilea mediu curat nu a fost verificată. Nu instalează CUDA, ASR complet, diarizare sau modele pentru imagini/video. Descărcarea separată păstrează `gigant/romanian-wav2vec2` la revizia **79cf603aac59501d02bfeb37f615efc3ac4ce1b3**, numai safetensors/configurații/vocabular/fișa modelului; fără modelul lingvistic 5-gram. Proveniența, dimensiunile și SHA-256 locale sunt în `models/alignment/romanian-wav2vec2/model.lock.json`. Un fișier existent nevalidat/corupt este refuzat, nu înlocuit automat. Licențele distincte sunt documentate în [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

`align --backend ctc-ro` folosește numai fișiere locale, `local_files_only=True`, `HF_HUB_OFFLINE=1` și `TRANSFORMERS_OFFLINE=1`. Proba reală cu cache gol și video subtitrat a trecut în `unshare -Urn`, cu tabelul de rute gol; sandbox-ul agentului blochează suplimentar crearea socketurilor. Dovezi: `work/media/real-alignment-audit/offline-real-current-result.json`.

Ferestrele lungi provin din eșantioanele reale ale manifestului TTS și pauzele configurate; nu din numărul de caractere. În interior, Viterbi CTC atribuie caracterele cunoscute cadrelor acustice ale modelului. Nu se înlocuiește sursa cu o transcriere. Fără raport TTS, un material de cel mult 35 s poate fi aliniat într-o fereastră; unul mai lung cere `--windows fisier.json`, cu `{"windows":[{"start":0,"end":123456,"spoken":"textul cunoscut"}]}`. Timpii sunt eșantioane la rata materialului; fiecare fereastră are maximum 40 s. Frontierele furnizate trebuie să fie reale, verificate; nu este implementată segmentare semantică automată a unui audio lung fără ancore.

### Încredere, normalizare și reluarea alinierii

Originalul afișat rămâne separat de ținta acustică: numerele sunt expandate numai pentru model, iar `spoken`, `display`, `alignment_target` și intervalul sunt salvate explicit. `‘89` este normalizat numeric ca 89, **fără presupunerea anului 1989**; aceasta nu aprobă o interpretare contextuală și nu modifică dicționarul. Majusculele/siglele și numerele rămân avertizate. Pentru materialul actual textele afișat/rostit au aceeași secvență de tokenuri; mapările editoriale complexe afișat/rostit trebuie furnizate explicit prin importul `--words` și `display_group`, nu sunt deduse automat din audio.

`alignment.json` păstrează `confidence`, `low_confidence`, `normalization`, `unaligned_words`, modelul/configurația și amprenta cererii. Pragul de avertizare al scorului este 0,35; scorul **nu este probabilitatea calibrată că un cuvânt este corect**. Zero cuvinte fără cale CTC nu demonstrează că fiecare cuvânt este sincronizat corect: algoritmul forțează textul cunoscut, iar numele/siglele/rostirile diferite pot primi intervale slabe. În materialul real sunt 170 de scoruri reduse și 17 normalizări contextuale; `aligned_with_warnings` trebuie revizuit prin ascultare. Highlight/scroll sunt disponibile pe intervalele existente, dar nu sunt validate auditiv pe acest material; exporturile reale folosesc classic.

Cache-ul este în `work/media/alignment/<hash>/`: `analysis.wav` la 16 kHz, master, checkpointuri `window-*.json`, progres și rezultat. Caracterele alfabetice care lipsesc din vocabular produc eroare explicită în CLI. Dacă afișarea diferă lexical de rostire, backend-ul automat cere mapare manuală în loc să o deducă.

Cheia include hash-urile surselor audio, cronologia, textul rostit/afișat, ferestrele, modelul, versiunea și codul adaptorului, normalizarea și versiunile dependențelor. Rezoluția/fontul nu cer aliniere nouă. Sursele și modelul sunt revalidate înainte de reutilizare. La Ctrl+C repetă aceeași comandă; checkpointurile validate sunt păstrate, cele corupte se recalculează. Nu se șterge automat nimic. Rezultatul global valid este verificat prin hash separat. `elapsed_seconds` dintr-un raport cu `cache_hit: true` descrie calculul inițial păstrat, nu latența apelului de reutilizare.

Reluarea este verificată după checkpointuri și după un eșec de atașare finală. Recuperarea pregătirii inițiale WAV și a unei copii de analiză corupte a fost verificată ulterior în `work/media/real-alignment-audit/recovery-real-result.json`: încercări distincte, receipt cu hash și validare înaintea publicării. Intermediarii întrerupți rămân pentru diagnostic, fără ștergerea surselor sau a cache-ului Piper.

Depanare: model lipsă → descărcare explicită; `.venv-align` lipsă → bootstrap explicit; hash de sursă diferit → import într-un ID nou; ferestre invalide/prea lungi → corectează ancorele; cale CTC imposibilă → eroare, fără timpi inventați; scoruri reduse → ascultare și eventual mapare manuală justificată. Un alt proces media activ ține lock-ul proiectului: așteaptă-l, fără ștergerea lock-ului. Un eșec de atașare a alinierii nu anulează checkpointurile deja calculate.

### Import și export video

Comenzi executate pentru proba sintetică Piper existentă (ID-urile demo sunt deja create; `init` nu suprascrie un material):

```bash
./media --report work/media/audit/capabilities.json doctor
./media init --id audio-demo --audio output/proba_1.00.mp3 --text samples/test_ro.txt --image "work/media/demo/Copertă ș apostrof' test.png" --tts-report output/proba_1.00.report.json
./media render audio-demo --profiles landscape,portrait --force
./media verify output/media/audio-demo/landscape/video.mp4
```

Pentru un material propriu folosește un **ID nou** și căile locale ale audio-ului și imaginii tale. `--tts-report` este opțional; când este furnizat, trebuie să corespundă hash-urilor audio/text. Atunci textul efectiv rostit este preluat din manifestul TTS, separat de textul afișat. Fără raport, `--text` este acceptat ca text rostit cunoscut furnizat de utilizator, fără verificarea acustică a concordanței.

Importul decodează o copie PCM mono 32-bit, cu rata sursei, în `materials/<id>/source.wav`; originalul este păstrat. La import video, pista audio și vizualul sursă sunt păstrate în material. `--audio` poate primi WAV/MP3 sau un container video cu un singur stream audio. O intrare fără text permite randare/tăiere temporală, dar nu generează text semantic inventat.

```bash
./media render scene-demo --profiles landscape,portrait,custom --width 640 --height 360 --subtitles highlight --title 'Ștefan citește.' --force
./media render scene-demo --profiles custom --width 640 --height 360 --plan-only
```

Ultima comandă validează planul fără randare. Profilele custom cer dimensiuni pare 64–4096; `square` este suplimentar. FPS 1–60, CRF 0–40, preset, fonturi, margini și încadrare se configurează în `media.json` sau într-o copie prin opțiunea globală `--config`. Prioritate efectivă: proiect → `material.composition` → ajustări ale scenei per profil → opțiunile CLI disponibile. Copiii moștenesc compoziția părintelui; compilația pornește de la compoziția primului material, care trebuie inspectată dacă părțile au stiluri diferite.

`fit` este implicit `contain`, cu margini, fără deformare. `cover` și focala `[x,y]` între 0 și 1 se aleg explicit în scenă/profil. Intensitatea `motion_amount` (implicit 0.04), `transition_seconds` (0.2), `title_fade_seconds` (0.2), fontul, `subtitle_outline` și `subtitle_margin_v` sunt validate. Mișcarea are progres pe durata scenei. Subtitrările se aplică după mișcare și rămân stabile. Crossfade-ul folosește cadre menținute, fără suprapunerea sau scurtarea vocilor.

### Timpi, subtitrări și scene editabile

Comenzile testate pe fixture-ul sintetic, **nu pe o aliniere automată a vocii**:

```bash
./media align scene-demo --words work/media/demo/alignment.json --provenance 'Fixture cu tonuri sintetice; timpi cunoscuți prin construcție, fără validare de aliniere a vorbirii'
./media scenes scene-demo --plan work/media/demo/scenes.json
./media subtitles scene-demo --profiles landscape,portrait --mode classic --output-dir output/media/scene-demo/subtitles-classic
```

Exporturile refuză directoare de subtitrări/thumbnail deja existente; alege alt director pentru o nouă versiune. `align --words` cere JSON cu `sample_rate`, `audio_timeline_hash` (valoarea `timeline_hash` afișată de `init`) și `words`: obiecte cu `spoken`, `start`, `end`, opțional `display`, `display_group`. Timpii sunt **indici întregi de eșantioane** la rata materialului, pozitivi/ordonați/fără suprapunere; lista trebuie să acopere exact toate cuvintele textului rostit. Nu se estimează automat din caractere.

Pentru un număr afișat o dată, dar rostit în mai multe cuvinte, fiecare cuvânt poate avea aceeași etichetă `display` și același `display_group` contiguu; eticheta este afișată o singură dată și evidențiată pe durata cuvintelor grupului. Split refuză o limită în interiorul unui cuvânt sau grup afișat. Importul primește `alignment_status: imported_not_reviewed`, nu o aprobare de precizie. Schimbarea cronologiei invalidează amprenta alinierii. Fără timpi, cererea de subtitrări produce eroare, fără fallback uniform tăcut.

`scenes --plan` citește `{"scenes": [...]}`. Fiecare scenă are `id`, `start`, `end`, `path`, `kind` (`image`/`video`), `anchor`, opțional `focal`, `fit`, `motion` (`none`, `zoom_in`, `zoom_out`, `pan`), `motion_amount`, `transition` (`cut`/`crossfade`), `profiles`, `license` și `provenance`. Intervalele trebuie să acopere întregul material fără gol/suprapunere. Asset-urile sunt verificate prin hash; rezoluția insuficientă se avertizează, clipul prea scurt se refuză. O diferență A/V de maximum 100 ms a clipului poate fi acoperită prin menținerea ultimului cadru, explicit raportată. Nu există asociere vizuală AI declarată.

### Titluri și thumbnail-uri independente

```bash
./media titles audio-demo
./media thumbnail audio-demo --text 'Ștefan și Măriuca la Brașov' --image "work/media/demo/Copertă ș apostrof' test.png" --profiles landscape,portrait --output-dir output/media/audio-demo/thumbnails
./media titles scene-demo --manual 'Ștefan citește. Măriuca ascultă.' --approve
./media thumbnail scene-demo --scene ascultare --variant top --format jpeg --profiles landscape,portrait --output-dir output/media/scene-demo/scene-thumbnails
```

Titlurile extractive clasează propoziții din întregul text, nu doar din început, păstrează pasajele sursă și deduplică. `--candidates` acceptă 1–5. Lipsa propozițiilor potrivite este `needs_edit`, nu un titlu inventat. Selecția se face cu `--select candidate_id`; `--approve` blochează alegerea, iar modificarea cere `--unlock` explicit. Titlurile manuale sunt etichetate ca atare, nu drept rezultate AI.

Thumbnail-ul poate folosi o imagine explicită, o scenă aleasă sau o copertă grafică locală când nu există vizual. La scenă video este extras cadrul median al intervalului ales, fără pretenția unei analize semantice a cadrelor. Textul este măsurat cu fontul real și nu este micșorat sub `font_min`; depășirea casetei cere editare. PNG/JPEG are JSON alăturat cu text, sursă, interval, profil, font/hash și geometrie. Dimensiunile se aleg independent de video prin profile/custom. Thumbnail-ul nu este introdus automat în film.

### Fragmente, compilații și loturi

Comenzi executate pe fixture-ul de 52920 eșantioane la 22050 Hz:

```bash
./media split scene-demo --parts 2 --prefix demo-part --apply
./media merge --id demo-compilation --materials demo-part-001 demo-part-002
./media batch work/media/demo/batch-final.json
```

Aplicarea CLI a fost verificată și pe materialul real, separat de exporturile finale:

```bash
./media split real-ro-20261016 --parts 2 --prefix real-ro-cli-fragment --apply
./media merge --id real-ro-cli-compilatie --materials real-ro-cli-fragment-001 real-ro-cli-fragment-002
```

Aceste ID-uri de verificare sunt deja create și nu au exporturi video suplimentare. Pentru alte împărțiri folosește un prefix/ID nou. Materialele video finale rămân cele enumerate în secțiunea despre vorbirea reală.

Split produce întâi `work/media/plans/<id>/split-plan.json`. Fără `--apply` este numai plan. `--mode partition` păstrează tot în ordine, fără goluri/suprapuneri; `--mode extract` permite selecție/ordine/repetiții explicite, marcate. Pentru intervale exacte, `--intervals` citește o listă JSON de perechi `[start_sample,end_sample]`. `--parts N` sau `--target-seconds X` aleg limite sigure din alinierea existentă; fără aliniere sunt necesare intervale manuale. Ținta nu este un maxim strict și N poate produce mai puține părți dacă nu există destule limite distincte. Textul temporal necunoscut nu este ghicit.

Fragmentele primesc ID-uri `<prefix>-001`, etc., referințe la părinți și surse, scene și timpi rebazați. `render`, `titles`, `thumbnail`, `subtitles` funcționează identic pe ele și pe compilație. Titlurile aprobate ale părintelui nu sunt copiate automat. Mișcarea scenei se reia local la începutul fragmentului; continuitatea fazei animației nu este încă implementată.

Merge păstrează ordinea argumentelor, vocile și eșantioanele surselor interne; nu normalizează și nu suprapune implicit vocea. `--plan-only` salvează un plan fără creare de material. Compilația are propriile titluri/thumbnail-uri. Rate audio diferite sunt refuzate clar; importul/conversia explicită la rată comună și fluxul complet de mix extern rămân de extins. Nu se aplică arbitrar `-c copy` pe liste MP4.

Un lot JSON are `jobs`, fiecare cu `args` ca listă de argumente CLI, fără shell. În prezent acceptă **render, thumbnail, subtitles, titles**; importul și derivarea se fac separat. Nu sunt suportate loturi recursive. Checkpoint-ul `work/media/batches/<hash>.json` este actualizat după fiecare job; o relansare refolosește numai rezultate cu amprente de intrare și hash-uri de fișiere încă valide. Lotul istoric `scene-demo` are 6 joburi trecute și refolosite. Lotul vorbirii reale are 11 joburi trecute și 11 refolosite la relansare; acestea sunt probe distincte. Un job lipsă/invalid produce rezultat nominalizat și cod final 1, fără succes total fals.

### Fișiere, verificări și limite de recuperare

Căile din `material.json`, scene, alinieri și referințe se rezolvă față de document, nu față de shell. Căile CLI și cele din listele de argumente batch păstrează semantica argumentelor CLI (folosește căi absolute dacă lotul va fi lansat din alt director). Sursele au hash-uri; nu muta/edita audio/imagini referite fără actualizare explicită și revalidare. Timeline-ul folosește indici întregi de eșantioane, iar conversia în cadre rotunjește o singură dată, cu acoperire completă.

- `materials/<id>/`: manifest, copie PCM, titluri/scene/aliniere. Conțin text privat și nu intră implicit în Git.
- `output/media/<id>/<profil>/video.mp4` și `video.report.json`: exporturi și verificări; thumbnail/subtitles au directoarele alese explicit.
- `work/media/runs/<id>/`: stare `running/complete/failed/interrupted`, temporare, master și cadre/scene FFV1 fără pierderi. Nu există curățare automată; verifică spațiul disponibil.
- `work/media/audit/`: capabilități, hash-uri protejate și regresia audio izolată; `work/media/media-tests.xml` este suita media.

`render` refuză implicit înlocuirea unui export diferit; `--force` este explicit. Exportul video se publică atomic după verificare; raportul și manifestul sunt scrise separat, fără tranzacție comună. Un export identic poate fi verificat/refolosit după hash. După întrerupere, folosește `--resume-run <run-id>` pentru recuperarea scenelor FFV1 din acel run. Scenele existente cer receipt compatibil, hash, profil/fps și decodare integrală cu numărul exact de cadre; sunt reutilizate fără randare. Fără receipt valid, reluarea se oprește păstrând fișierul pentru audit. Fără `--resume-run`, este creat un run nou. Profilele finale identice continuă să fie verificate și reutilizate. Titlurile/subtitrările/thumbnail-urile pot fi refăcute fără sinteză audio. Importul eșuat poate lăsa un director parțial: inspectează-l și folosește alt ID, fără ștergere automată.

Verificarea media decodează integral video și audio, verifică H.264/AAC/yuv420p și măsoară duratele decodate. Pragul inițial A/V este 100 ms; la export se verifică și acoperirea sursei, rezoluția/fps și toleranța de un cadru. `verify` independent nu cunoaște automat dimensiunile intenționate ale unui profil. Există inspecție a câtorva cadre extrase, nu audiție sau vizionare integrală. Statusurile `technical_status`, `alignment_status`, `visual_review_status`, `listening_status`, `editorial_review_status` rămân separate. Datele și limitele exacte sunt în [TEST_RESULTS.md](TEST_RESULTS.md), iar cerințele viitoare rămân în [planul canonic](docs/PLAN_EXTINDERE_MEDIA_REC.md).

## Split text înainte de TTS (2026-10-16 UTC)

`./media split-text input/text.txt --parts 2 --output-dir work/media/text-parts-v1`
scrie părți UTF-8 și `text-parts.json` cu offseturi Unicode și octeți în original,
hash-uri și durate **estimate** la 150 cuvinte/minut. Nu modifică sursa și nu
sintetizează. Alternative exclusive: `--target-duration 90`, `--chapters`
(titluri Markdown/Capitol), `--delimiter '=== CAPITOL ==='`, `--manual-ranges ranges.json`
(schema `{"ranges":[[0,120],[120,250]]}`, acoperire completă), `--semantic`.
Ultima este o propunere locală de coeziune lexicală între paragrafe, fără model AI.
Propozițiile/paragrafele sunt limite preferate; un număr imposibil de părți este refuzat.
`./media merge-text work/media/text-parts-v1/text-parts.json --output work/media/text-reunit-v1.txt`
reconstruiește exact octeții sursei, inclusiv BOM/CRLF, dacă părțile sunt intacte.
Fiecare parte poate fi dată separat la `./tts render` cu o destinație MP3 nouă,
apoi importată prin `./media init`; primește toate funcțiile media existente.
Comenzile de split/merge text sunt offline și nu cer modele suplimentare.

## Revizuire CTC și recuperare

`./media alignment-review real-ro-20261016 --output work/media/review-v1.json`
scrie JSON și Markdown, grupate pe segmente, cu timestamp, cuvânt, confidence și
starea revizuirii. Copiază `alignment_key` într-un JSON cu `reviewer` și `decisions`:
`{"alignment_key":"...","reviewer":"numele tău","decisions":[{"index":12,"status":"corrected","start":1000,"end":2000,"note":"verificat auditiv"}]}`.
Valorile start/end sunt eșantioane, nu milisecunde. Aplicare:
`./media alignment-review material-id --apply work/media/decizii.json`.
Stările sunt `accepted`, `rejected`, `corrected`; numai ultima schimbă timpii.
Unitățile rejected blochează subtitrarea până la corectare/rerulare.
`./media align material-id --backend ctc-ro --segments 2,7` recalculează numai
ferestrele indicate (indici de la zero), reutilizând restul checkpointurilor valide.
Nu resintetizează; modelul CTC existent este necesar, fără rețea. Scorurile reduse
rămân vizibile după aprobare. Nu aplica exemplul de timpi fără măsurare.
Pregătirea WAV folosește încercări distincte, validare completă și publicare atomică;
WAV-ul se reutilizează numai cu hash/format/durată/cronologie confirmate.

## Planuri de scene și preseturi

`./media scene-plan real-ro-20261016 --images assets/imagini/a.png assets/imagini/b.png assets/imagini/c.png --output work/media/scenes-v1.json`
propune intervale din alinierea existentă, cu mapping text/audio și assets în ordinea
explicită. `--folder assets/imagini` folosește ordinea lexicografică consemnată;
`--intervals work/media/intervale.json` poate fixa limitele în eșantioane.
Editează `description`, `motion` (`none`, `zoom_in`, `zoom_out`, `pan`),
`transition` (`cut`, `crossfade`), `focal` și `approval_status`
(`pending`, `approved`, `rejected`), apoi importă cu
`./media scenes real-ro-20261016 --plan work/media/scenes-v1.json`.
Scenele rejected blochează randarea. Pending permite probe, fără aprobare implicită.
Totul rulează local fără model nou. Imaginile și clipurile existente sunt acceptate.
`youtube-landscape` și `shorts-portrait` sunt aliasuri pentru 1920×1080 și
1080×1920, utilizabile la render/subtitles/thumbnail. `custom --width 1280 --height 720`
rămâne disponibil. Preseturile aleg numai dimensiuni media, fără text/voce nouă.
Titlurile aprobate pot primi propuneri extractive noi; selecția aprobată rămâne
blocată până la `--unlock`. Extrasele din propoziții lungi păstrează pasajul și
intervalul sursă; propunerile nu sunt aprobare editorială.

## Orchestratorul workflow

`./media workflow samples/media/workflow.example.json` execută etapele activate
peste comenzile publice `./tts` și `./media`. Exemplul activează numai propunerile
de titlu; activează și adaptează etapele thumbnail/render pentru proiectul tău.
Planul JSON conține `steps` cu `id`, `tool` (`tts`/`media`), `args`, `enabled`,
`depends_on`, `inputs`, `outputs`. Căile din argumente/inputs/outputs sunt relative
la plan. Folosește ID-uri de materiale și destinații noi pentru un proiect nou.
Declară în `inputs` toate fișierele care trebuie să invalideze etapa (text, audio,
config, planuri, assets); `outputs` sunt artefactele ce trebuie verificate prin hash.
Rapoartele media sunt păstrate automat. Manifestele media pot primi metadate noi
în etape ulterioare; nu le declara drept output imuabil al importului inițial.
Starea și logurile sunt lângă plan, în `<nume-plan>.state/`; aceeași comandă reia
etapele confirmate prin hash. Un output schimbat nu este suprascris implicit.
`--only render`, `--disable titles` și `--rerun titles` permit selectarea independentă.
Rerun înseamnă reapelarea comenzii, cu protecțiile sale existente; nu adaugă `--force`.
Un eșec oprește workflow-ul cu diagnostic, păstrând etapele complete. Fără rețea
sau model nou prin orchestrator; o etapă align cere modelul CTC instalat explicit.

`./media synthesize-parts work/media/text-parts-v1/text-parts.json --output-dir output/parti-v1`
planifică MP3-urile părților. Adaugă `--apply` numai pentru sinteza noilor părți.
Nu folosește `--force`; MP3-urile deja valide sunt tratate de `./tts` idempotent.
Sinteza folosește modelul Piper existent, offline; textul original rămâne intact.

## Backend AI de imagini opțional

Hardware verificat la 2026-10-16 UTC: WSL vede i7-13620H, 4 procesoare logice,
4.106.862.592 octeți RAM (~3,82 GiB), fără `/dev/dxg`, `/dev/dri`, `nvidia-smi`.
Windows, verificat separat prin CIM, vede Intel UHD Graphics și
16.890.322.944 octeți RAM (~15,73 GiB). AdapterRAM=2.147.479.552 este o valoare a
driverului, **nu** o măsurare sigură a VRAM dedicate. GPU-ul există în Windows;
CUDA/DirectML nu sunt confirmate disponibile pentru fluxul WSL.

Alegere opțională: stable-diffusion.cpp (MIT), candidat CPU cu SD 1.5
(CreativeML OpenRAIL-M, licență separată cu restricții). Nu este instalat/testat;
WSL are prea puțină memorie disponibilă pentru o probă prudentă concurentă cu
montajul. AI video rămâne separat și neinstalat. Baza media funcționează fără ele.
Pe un alt mediu: rezervă inițial cel puțin 8 GiB RAM disponibilă pentru evaluarea
CPU 512×512 (buget de test propus, nu minim măsurat), fixează o revizie a sursei
stable-diffusion.cpp, compilează conform README oficial, verifică `sd-cli -h`,
obține explicit greutăți SD 1.5 cu licența/fișa și hash-urile, apoi rulează o probă
cu seed fix înaintea folosirii în producție. Pentru GPU trebuie întâi dovedit
backend-ul disponibil; nu presupune că Intel UHD în Windows expune CUDA în WSL.
Nu sunt necesare servicii sau abonamente.

`./media image-plan samples/media/image-request.example.json --output work/media/image-plan-v1.json`
produce contractul portabil și raportează `blocked` (exit 1) pentru binar/model
absente. Completează `executable` și `model` ca obiecte cu `path`, `sha256`,
`revision`, `license` după instalarea explicită pe hardware adecvat. Comanda
validează identitatea și scrie un plan; **nu generează** imagini și nu descarcă.
Importă imaginea rezultată extern/local prin scene/thumbnail după verificare.
Licențele și sursele sunt în [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Reluarea producției după închiderea sesiunii — 2026-10-16 UTC

Auditul incidentului este în `work/media/production-20261016/incident-recovery.json`.
Verificarea proceselor trebuie făcută și pe gazdă: sandboxul poate vedea numai
propriul namespace PID. La recuperare nu mai exista niciun job media vechi;
WSL pornise din nou la 19:53:30 UTC. Run-ul `e7c89d4f63e7481c89a2d0207c194984`
rămăsese `running`, fără profil publicat; al treilea MKV era trunchiat.
Un fișier state rămas `running` nu demonstrează că procesul încă trăiește.
Cauza exactă a mesajului terminalului `process exited with code 1` nu este
înregistrată în dovezile disponibile și nu este atribuită automat pipeline-ului.

Producția continuă din materialul, cronologia și alinierea existente. Recuperarea
WAV anterioară și cele 71 de teste sunt dovezi istorice păstrate. Proba selectivă
nouă reutilizează receipt-ul WAV de la 19:41 UTC; `--segments 1` păstrează intact
checkpointul ferestrei 0. Nicio resinteză a materialului real nu este necesară.

La schimbarea codului, semnătura workflow-ului poate invalida o etapă chiar dacă
artefactul vechi există. Nu adăuga `--force` pentru a trece peste protecție:
inspectează receipt-urile și selectează explicit etapele rămase prin `--only`.
`technical_status: passed` confirmă selecția executată; noul `workflow_status`
este `partial` dacă există etape activate care nu au fost parcurse în acea
invocare. `incomplete` le enumeră, iar state-ul folosește aceeași fază.
`--disable` exclude intenționat etape din scopul invocării. O reîncercare eșuată
păstrează receipt-ul anterior în `previous_success`, ca dovadă istorică, fără
să îl transforme în succes curent sau să accepte outputuri schimbate.

Matricea curentă DONE/PARTIAL/TODO/BLOCKED și limitele de acceptare sunt în
[planul canonic](docs/PLAN_EXTINDERE_MEDIA_REC.md#recuperarea-producției--2026-10-16-utc),
iar rezultatele efective sunt în [TEST_RESULTS.md](TEST_RESULTS.md).

Plafon strict pentru audio existent: `./media split material-id --max-seconds 180
--prefix parti-maxime` (o singură comandă). Planifică implicit; `--apply` creează
materialele derivate, fără resinteză. Numai cu `--max-seconds` caută limite
aliniate în plafon, preferând pauze între propoziții aproape de limita legală.
Cu `--parts`, `--target-seconds` ori `--intervals`, plafonul validează rezultatul
și raportează conflict dacă vreun interval este prea lung; nu schimbă tacit
numărul/limitele cerute. Plafonul folosește floor(secunde × sample_rate),
revalidat înainte de aplicare. Lipsa unei limite aliniate produce eroare, fără
tăiere inventată în cuvinte/grupuri afișate. Un capăt CTC rămâne o limită tehnică,
nu confirmare auditivă a sfârșitului acustic. Pentru text înainte de TTS, durata
rămâne estimată și această garanție nu se aplică.

Pentru jobul lung recuperat, workerul local `work/media/production-20261016/production-runner.py`
folosește CLI-urile publice și scrie `runner-state.json`, loguri pe faze și
`production-completion.json` numai după acceptanță. A fost detașat explicit
într-o sesiune proprie după SIGTERM-ul procesului temporar; un simplu nohup
nu a confirmat pornirea. Verifică PID/procese/lock-uri înaintea oricărei relansări.
Profilul complet se reutilizează numai dacă request-ul și hash-ul coincid și
se decodează integral; un MP4 temporar fără moov nu este checkpoint valid.

Corecția crossfade a producției fixează FPS înainte de paddingul scenelor cu
mișcare. Proba mică numără acum 96/96 cadre și verifică amestecul gradual al
pixelilor roșu/albastru; vechiul comportament avea 91/96. Varianta corectată
exportă în `output/media/scenes-v2/<material>/<profil>/video.mp4`, păstrând
rezultatele anterioare. `./media render material-id --profiles landscape,portrait
--output-root output/media/varianta-noua` permite o destinație distinctă, fără
`--force`; structura material/profil și protecția outputurilor existente rămân.
O schimbare de destinație nu schimbă audio-ul sau alinierea.


## Recuperare din scene FFV1 complete — 2026-10-16 UTC

`render --resume-run <run-id>` reia asamblarea din scenele validate ale run-ului.
Păstrează aceleași opțiuni de profil, subtitrări și titlu ca în cererea originală:

```bash
./media render material-id --profiles landscape --subtitles classic --resume-run RUN_ID --output-root output/media/varianta-noua
```

Dacă cererea inițială conținea `--title`, repetă exact titlul. Exemplul de mai sus
este pentru o cerere fără titlu. Verifică procesele gazdei și lock-urile înainte.
CLI păstrează lock-ul global media; nu șterge fișierul de lock. Configurația efectivă
include `material.composition` și opțiunile scenei per profil.

Receipt-ul scenei include identitatea pipeline-ului `ffv1-cfr-padding-v2`, scena,
asset-ul/hash-ul, profilul, configurația, fontul/hash-ul, Pillow, FFmpeg/hash-ul și
implementarea compoziției imaginilor. Schimbările incompatibile sunt refuzate.
Intermediarii fără receipts nu se adoptă automat: incidentul real a necesitat
migrare explicită după auditul comenzii, configurației, asset-urilor, cadrelor și
decodării. Masterul PCM are receipt separat și sursele audio sunt revalidate.
Nu este reluare în interiorul unui encoder MP4 deja întrerupt.

Fiecare încercare finală are un nume `.part.mp4` distinct și diagnostic persistent
`final-*.command.json`, `.command.stderr`, `.command.stdout` în directorul profilului.
Se păstrează argumentele exacte, cwd, PID, returncode și maximul RSS observat.
Un receipt rămas running după închiderea gazdei nu dovedește proces activ.
Temporarul este verificat complet înainte de `os.replace` atomic în același director;
fișierele `.part` istorice nu sunt publicate și nu sunt șterse automat.
Decodoarele fiecărui input final au explicit numărul configurat de fire.

Pentru producția deja configurată, continuarea recuperată este:

```bash
python3 work/media/production-20261016/recovery-scenes/continue-production.py
```

Workerul folosește lock-ul producției, reia întâi integrala landscape și verifică
exportul înaintea integralei portrait, fragmentelor și compilației. Nu relansează
derivarea sau selecția titlurilor deja complete. Starea și logurile sunt în
`work/media/production-20261016/recovery-scenes/`.

Auditul `scene-validation.json` confirmă scenele 00000/00001/00002 ale run-ului
`9f8ed5ce64054935b51da76f4d686db7`: 6.950/6.765/6.962 cadre FFV1,
fără trunchiere. MP4-ul vechi de 48 bytes are ftyp/free/mdat gol, fără moov;
este păstrat ca diagnostic. Cauza exactă a exit 1 care a închis sesiunea nu este
înregistrată; repornirea WSL este confirmată, OOM sau un returncode FFmpeg anterior
nu sunt dovedite. Probele cu limită artificială de memorie sunt diagnostice noi,
nu dovada cauzei istorice. Rezultatele finale sunt consemnate separat în TEST_RESULTS.

Regresia `test_resume_complete_scenes_after_interrupted_atomic_publication`
simulează întreruperea finalizării, un `.part.mp4` de 48 bytes și relansarea.
Verifică hash/mtime nemodificate ale scenelor, absența rerandării, păstrarea
part-ului incomplet, publicarea atomică și decodarea completă a rezultatului.


Proba de recovery include și `test_recovery_after_process_exit_with_three_valid_scenes`:
două procese separate, ieșire bruscă `os._exit(1)`, running rămas pe disc,
trei MKV complete și part de 48 bytes, urmate de relansare fără rerandare.
Regresia consolidată: 78 teste trecute, cu probele audio de integrare neselectate.
Adoptările între materialele producției sunt auditate explicit în `seeded-runs.json`;
CLI nu presupune compatibilitate cross-material pe baza numelui sau mtime-ului.


## Producție recuperată și verificată — 2026-10-17 UTC

Cele **8 MP4-uri** sunt complete în
`output/media/scenes-v2/<material>/{landscape,portrait}/video.mp4`:

| Material | Durată video / profil | Audio decodat / profil | Max A/V |
|---|---:|---:|---:|
| `prod-ro-20261016-001` | 688,833333 s | 688,843175 s | 9,841 ms |
| `prod-fragment-20261016-001` | 348,400000 s | 348,392200 s | 7,800 ms |
| `prod-fragment-20261016-002` | 340,433333 s | 340,450975 s | 17,642 ms |
| `prod-compilation-20261016` | 688,833333 s | 688,843175 s | 9,841 ms |

H.264/AAC, 30 fps, dimensiunile exacte ale profilului, decodare A/V completă,
acoperire audio integrală și publicare atomică. SRT/ASS/alinierea sunt în
`output/media/<material>/production-subtitles/<profil>/`, iar cele opt coperți
în `production-thumbnails/`. Raport comun:
`work/media/production-20261016/recovery-scenes/final-acceptance.json`.

Cele trei MKV originale landscape nu au fost rerandate: hash/mtime identice,
decodare completă și receipts compatibile. Part-ul original de 48 bytes și
part-ul ulterior de 1.048.624 bytes sunt păstrate ca diagnostic, fără publicare.
Un exit 1 observat în ultima reluare a fost localizat în citirea unui receipt
JSON gol, pereche cu o copie MKV de 0 bytes; perechea este păstrată separat și
scena a fost recopiată dintr-un intermediar verificat cu contract identic.
Cauza închiderii terminalului precedent nu poate fi stabilită din returncode/
stderr inexistente. Cronologia Windows și diagnosticele sunt în TEST_RESULTS.

Continuarea normală, după verificarea proceselor și lock-urilor:

```bash
python3 work/media/production-20261016/recovery-scenes/continue-production.py
```

Nu folosi scriptul punctual `resume-last-profile-20261017.py` ca relansare
generală: acesta consemnează recuperarea ultimului profil când existau exact
șapte rezultate. Comanda normală păstrează exporturile conforme și verifică
subtitrările existente contra alinierii/stilului/fontului, fără suprascriere.
O diferență reală este raportată, fără force implicit. Regresia întărită folosește
antetul real al part-ului și două procese; trei teste au trecut în copie izolată.

Ancorele text ale scenelor derivate au fost corectate prin migrare cu jurnal,
fără modificarea MP4/MKV, audio-ului sau alinierii. Cele 553 fișiere protejate,
1.824 unități și 170 scoruri reduse sunt păstrate. Inspecția vizuală privește
cadre selectate, inclusiv tranzițiile integralei landscape; ascultarea, ancorele
manuale și aprobarea editorială rămân restanțe separate în planul canonic.

## Asset discovery, bibliotecă și editare scene — 2026-10-17 UTC

Etapa extinde manifestul existent, fără TTS nou. `assets` caută/descarcă explicit;
`scenes` selectează și editează local. ASSISTED este implicit: o căutare nu alege
primul rezultat. AUTO este o euristică text/geometrie/licență, cu motive și
alternative păstrate; nu reprezintă înțelegere semantică perfectă sau aprobare
editorială umană. Query-urile RO/EN sunt propuneri lexicale inspectabile.

Comenzi folosite pe copia de lucru `assets-real-20261017`:

```bash
./media assets queries assets-real-20261017 --scene scene-001
./media assets search assets-real-20261017 --scene scene-001 --provider commons openverse --query 'Iasi Metropolitan Cathedral' --limit 6
./media assets search assets-real-20261017 --scene scene-002 --provider commons --query 'protest Bucharest -Wikipedia' --type video --limit 8
./media assets download assets-real-20261017 --scene scene-001 --candidate 46ea9b461631a96c653e479d
./media assets download assets-real-20261017 --scene scene-001 --candidate 211d35f0fd4711a332ad2e2c --rendition thumbnail
./media assets review assets-real-20261017 --output-dir work/media/asset-discovery-20261017/review
./media scenes assets-real-20261017
./media scenes assets-real-20261017 --scene scene-001 --inspect
./media scenes assets-real-20261017 --scene scene-001 --alternatives
./media scenes assets-real-20261017 --scene scene-001 --select 46ea9b461631a96c653e479d --approve
./media assets list --query Cathedral --type image
./media assets credits assets-real-20261017
```

`assets/library/library.sqlite3` este indexul reutilizabil; obiectele sunt adresate
prin SHA256, în `objects/`, iar încercările incomplete rămân în `attempts/`.
`--library-root` permite o bibliotecă separată (înaintea subcomenzii `assets`).
Filtrele JSON acceptă keywords/persons/places/events/period/tags/type/provider/
license/orientation/width/height/duration/checksum. Metadatele importului se pot
furniza cu `assets import FISIER --metadata METADATE.json`. Lipsa licenței unui
fișier local nu dovedește drept de publicare.

Exemple pentru fișierele proprii, fără internet:

```bash
./media assets import /cale/absoluta/imagine.jpg --metadata metadate.json
./media scenes MATERIAL --scene SCENE_ID --replace /cale/absoluta/imagine.jpg --approve
./media scenes MATERIAL --scene SCENE_ID --replace /cale/absoluta/video.mp4 --approve
./media scenes MATERIAL --scene SCENE_ID --set video-interval.json
./media scenes MATERIAL --scene SCENE_ID --profile portrait --select ASSET_ID --approve
./media scenes MATERIAL --scene SCENE_ID --profile portrait --set portrait.json
./media scenes MATERIAL --scene SCENE_ID --remove --approve
./media scenes MATERIAL --scene SCENE_ID --restore
```

`video-interval.json`: `{"video":{"source_start":43.0,"source_end":51.0,"audio_enabled":false},"visual":{"short_policy":"freeze"}}`.
Intervalul trebuie să existe în sursa verificată. Audio-ul extern este mut
obligatoriu în acest renderer. Politica implicită pentru clip scurt este eroare;
`loop` și `freeze` se aleg explicit. Alternativa este alt asset, fallback grafic
sau `--sequence secventa.json`, o listă de `{asset_id,frames,video?,visual?}`;
`frames` sunt eșantioane audio și suma trebuie să acopere exact scena.

`portrait.json`: `{"visual":{"fit":"cover","focal_point":[0.72,0.4],"motion":"none"}}`.
`--set` editează și crop normalizat `[left,top,right,bottom]`, zoom 1–4,
pan `[x,y]`, motion (`none/zoom_in/zoom_out/pan`), transition (`cut/crossfade`),
overlay/title_overlay text și subtitle_placement (`bottom/top`). `start/end`
mută limita comună cu scena vecină în eșantioane, păstrând durata audio.
Selecția anterioară și istoricul rămân disponibile fără redownload.

Pentru rerandare parțială păstrează run-id-ul din primul render:

```bash
./media render assets-real-20261017 --profiles landscape,portrait --subtitles classic --output-root output/media/assets-v1
./media scenes assets-real-20261017 --scene scene-001 --select 6499800dbdbc7373d1b9db4b --approve
./media render assets-real-20261017 --profiles landscape,portrait --subtitles classic --resume-run RUN_ID --rerender-changed --output-root output/media/assets-v1-replaced
./media verify output/media/assets-v1-replaced/assets-real-20261017/landscape/video.mp4
./media thumbnail assets-real-20261017 --scene scene-001 --profiles landscape,portrait --text 'Exemplu de copertă' --output-dir output/media/assets-thumbnails
```

Render/verify/split/merge/subtitles și reutilizarea alinierii rulează offline după
descărcare. Decoderul video acceptă numai protocoale locale `file,pipe`.
Schimbarea selecției păstrează audio-ul/alinierea; receipts/hash/decodare/cadre
exacte decid ce scenă se reutilizează. Scenele schimbate sunt arhivate înainte de
înlocuire; finalul verificat se publică atomic. O tranziție poate afecta paddingul
scenei precedente. Subtitrările sunt aplicate în asamblarea finală, nu în MKV-ul
vizual, astfel că editarea lor nu cere regenerarea imaginilor scenelor.

Commons și Openverse nu cer cheie în implementarea curentă. Pexels este opțional,
cere `PEXELS_API_KEY` prin mediu; cheia nu intră în manifest sau loguri. Numai
search/download cer internet. Erorile HTTP și Retry-After sunt păstrate; 429
instituie pauză per gazdă, fără schimbarea domeniului pentru ocolirea limitei.
Reluarea downloadului folosește Range numai cu ETag puternic și total verificabil;
altfel pornește o încercare nouă. URL, redirecturi, MIME real, mărime, rezoluție,
durată și decodare sunt verificate înainte de indexare/publicare.

Fiecare export are `credits.json` și `CREDITS.md`, inclusiv overrides; thumbnail-ul
are provenance separat. `LICENSE_UNKNOWN` online cere `--approve` împreună cu
`--allow-unknown-license`; AUTO îl exclude. Metadatele furnizorului nu înlocuiesc
review-ul editorial și verificarea obligațiilor licenței. `scene-review.md` și
contact sheet-urile păstrează ID-urile pentru alegeri precum „scene-001 → ID”.
AI local rămâne opțional, fără backend instalat sau fallback cloud.

### Continuarea verificată a etapei assets — 2026-10-18 UTC

Proba lungă `assets-real-20261017` s-a întrerupt înaintea primului MP4; acel run
și `.part` rămân păstrate. Exemplele de mai sus descriu CLI-ul disponibil,
nu dovada unui export integral assets finalizat. Acceptanța nouă folosește
`assets-accept-20261018`: trei extrase din materialul real, 11,820 s PCM,
cu alinierea existentă rebazată, fără sinteză sau inferență CTC nouă.

Preview-ul video din `assets review` conține trei cadre la 10%, 50%, 90% din
clip, timestampuri, rezoluție/provider/licență și contact sheet cu ID-urile
candidaților. Preview-ul este identificat prin checksum și reutilizat local.
La `assets import --metadata`, un checksum declarat diferit de sursă produce
refuz înainte de publicare; dimensiunile indexate sunt cele măsurate local.

Comenzile pentru proba nouă (destinațiile există după acceptanță; pentru alte
variante alege alte destinații):

```bash
./media scenes assets-accept-20261018 --scene assets-accept-cut-20261018-002-scene-002 --inspect
./media assets review assets-accept-20261018 --output-dir work/media/asset-discovery-20261018/review
./media assets credits assets-accept-20261018
./media render assets-accept-20261018 --profiles landscape,portrait --subtitles classic --resume-run efe6b66a60a44bcfad061f4300e9f32d --output-root output/media/assets-accept-20261018-layout
```

Ultima comandă verifică/reutilizează versiunea curentă de layout, fără `--force`.
Prima randare și replace-ul sunt păstrate separat în `assets-accept-20261018-first`
și `assets-accept-20261018-replaced`. Replace-ul efectiv a selectat asset-ul
`edbec9508a5d072a2d309b72` pe scena a treia, apoi a folosit `--rerender-changed`
cu același run. Probele și limitele editoriale sunt în TEST_RESULTS și în
`work/media/asset-discovery-20261018/`; bibliotecă comună: `assets/library/`.

Versiunea finală a probei este în `output/media/assets-accept-20261018-layout/`.
Ea mută sus subtitrarea scenei video și folosește contain pentru persoană în
landscape; scenele cu setări neschimbate au fost reutilizate. Cele trei variante
(first/replaced/layout), câte două profile, sunt păstrate separat. Contact sheets
numerotate și scene-review actualizat: `work/media/asset-discovery-20261018/review-layout/`;
pentru biblioteca completă de candidați: `review-full/`. Șase MP4-uri PASSED
tehnic; inspecția vizuală rămâne limitată la cadre selectate, fără ascultare sau
aprobare editorială. Exportul integral assets nu a fost reluat din part-ul istoric.

## Workflow integral assets — aplicare pe materialul existent

Materialul de lucru este `assets-integral-20261018`, copia integrală a manifestului
existent, cu aceeași voce, cronologie și aliniere. Cele 19 scene sunt grupate după
schimbări de idee/persoană/loc, la frontiere observate în aliniere (16–51 s).
Planul de lucru și selecțiile sunt în `materials/assets-integral-20261018/`;
probele și workflow-ul JSON sunt în `work/media/assets-integral-20261018/`.
Nu există inferență semantică nouă sau tăiere a audio-ului pentru aceste scene.

Fluxul real: scene/query → bibliotecă → căutare explicită dacă lipsesc candidați →
download limitat → review → selecție propusă/fallback → subtitrări → thumbnail →
credits → render landscape/portrait offline → replace unic și reluare → review final.
`assets search` verifică acum întâi biblioteca: minimum trei candidați locali cu
provenance completă evită HTTP. Apoi verifică providerii în ordinea dată, până la
un shortlist suficient. ASSISTED nu selectează primul rezultat. Query-urile
lexicale și cele RO/EN ajustate explicit rămân vizibile în review.

Comenzi verificate în parserul CLI existent; exemplele care editează materialul
se folosesc deliberat, apoi se alege o destinație nouă pentru render:

```bash
./media scenes assets-integral-20261018
./media scenes assets-integral-20261018 --scene scene-016 --inspect
./media assets queries assets-integral-20261018 --scene scene-002
./media assets list --query Georgescu --type image
./media assets search assets-integral-20261018 --scene scene-019 --provider commons openverse --query 'Bucharest Court of Appeal' --limit 5
./media scenes assets-integral-20261018 --scene scene-016 --alternatives
./media assets download assets-integral-20261018 --scene scene-016 --candidate 83edb41295b87ee3d709e996
./media assets review assets-integral-20261018 --output-dir work/media/assets-integral-20261018/review-full
./media scenes assets-integral-20261018 --scene scene-016 --select 83edb41295b87ee3d709e996 --approve
./media scenes assets-integral-20261018 --scene scene-016 --restore
./media scenes assets-integral-20261018 --scene scene-002 --profile portrait --select 6499800dbdbc7373d1b9db4b --approve
./media scenes assets-integral-20261018 --scene scene-002 --profile portrait --set work/media/assets-integral-20261018/edits/portrait.json
./media scenes assets-integral-20261018 --scene scene-002 --set work/media/assets-integral-20261018/edits/crop.json
./media scenes assets-integral-20261018 --scene scene-002 --set work/media/assets-integral-20261018/edits/focal.json
./media scenes assets-integral-20261018 --scene scene-001 --set work/media/assets-integral-20261018/edits/trim.json
./media scenes assets-integral-20261018 --scene scene-002 --set work/media/assets-integral-20261018/edits/transition.json
./media scenes assets-integral-20261018 --scene scene-002 --set work/media/assets-integral-20261018/edits/motion.json
./media scenes assets-integral-20261018 --scene scene-016 --set work/media/assets-integral-20261018/edits/needs-review.json
./media assets credits assets-integral-20261018 --profiles landscape,portrait --output-dir work/media/assets-integral-20261018/credits-final
```

Înlocuire locală: `./media scenes assets-integral-20261018 --scene scene-016 --replace /cale/absoluta/imagine.jpg --approve`;
video: aceeași comandă cu `/cale/absoluta/clip.mp4`. Eliminare: `--remove --approve`.
`--restore` recuperează selecția/setările anterioare fără redownload.
`--set` citește JSON, nu expresii shell. `trim.json` păstrează intervalul 2–52 s;
clipul extern rămâne mut. Un clip scurt cere explicit freeze/loop sau alt asset;
proba integrală folosește freeze, fără loop vizibil. Schimbarea unei tranziții
poate schimba și paddingul scenei precedente.

`review-full/scene-review.md` și `scene-review.json` includ fiecare scenă,
timestamp/context/query-uri, alternative numerotate, surse/licențe, configurații
și preview-uri separate landscape/portrait. Numărul candidatului este poziția în
review-ul respectiv; CLI-ul folosește ID-ul stabil afișat lângă număr. Preview-ul
încadrării este static, fără a pretinde evaluarea integrală a mișcării.

`review_status` este separat de aprobarea tehnică: APPROVED, PROPOSED,
NEEDS_REVIEW, FALLBACK, LICENSE_UNKNOWN, REJECTED. Selecțiile agentului rămân
NEEDS_REVIEW/FALLBACK; `--approve` nu dovedește un review editorial uman.
O decizie explicită se poate înregistra prin `scenes --set` cu review_status și
review_note. REJECTED blochează render. Etapa integrală exclude LICENSE_UNKNOWN.

`credits --profiles landscape,portrait` enumeră numai selecțiile efective ale
acestor profile. Fiecare director de export conține numai credits-ul profilului
său; candidații nefolosiți rămân în review/bibliotecă. Credits-ul thumbnail-ului
conține numai sursele thumbnail-urilor. Titlul manual selectat a fost păstrat;
propunerile extractive sunt separate și un titlu locked nu este suprascris.

Workflow-ul local se rulează cu:

```bash
unshare -Urn ./media workflow work/media/assets-integral-20261018/workflow-integral.json
```

Planul declară inputs/outputs și folosește fișierele scenes/titles, sursele locale,
configurația și snapshotul de contract; exporturile nu sunt declarate ca intrări
imuabile ale importului. Este planul acestei versiuni, cu destinații concrete,
nu o comandă pentru a reseta selecțiile. La schimbări ulterioare folosește
`render --resume-run` și un output-root nou, conform exemplelor de mai jos.

Pexels rămâne opțional. Configurare locală fără afișarea cheii: `read -rs -p 'Pexels API key: ' PEXELS_API_KEY`, apoi `export PEXELS_API_KEY`.
Fără cheie, statusul live este BLOCKED_OPTIONAL; biblioteca/Commons/Openverse/
montajul local continuă. AI rămâne BLOCKED/OPTIONAL, fără instalări noi.

## Integral assets recuperat — 2026-10-19 UTC

Run `5ba454a524f74ffc8991987e14b12cf1`, media 0.1.0, pipeline `scene-assets-v1`.
Ambele exporturi integrale sunt PASSED tehnic, 688,822 s PCM / 688,833 s video,
1920×1080 și 1080×1920 la 30 fps. Baseline-ul landscape și noul portrait sunt în
`output/media/assets-integral-20261018-first/assets-integral-20261018/`.
Landscape-ul, raportul/credits și cele 19 scene ale sale au hash/mtime păstrate.
Portrait: 11 checkpointuri valide refolosite; scena 12 trunchiată/receipt gol
arhivată înaintea regenerării, apoi celelalte 7 scene lipsă generate. Part-urile
istorice și stările încercărilor întrerupte sunt păstrate.

Etapa AI07 din plan este confirmată integral printr-o singură schimbare portrait:
scene-016 → candidate 3, existent local, Focus Creștin / CC BY 3.0. Rezultatul
este în `output/media/assets-integral-20261019-portrait-edit/assets-integral-20261018/portrait/`.
**18 scene refolosite / 1 recalculată**, baseline-urile și biblioteca de blobs/
încercări neschimbate; audio AAC decodat identic, fără TTS sau inferență CTC.
Este o variantă tehnică NEEDS_REVIEW, nu o alegere editorială aprobată.

Review curent: `work/media/assets-integral-20261018/recovery-20261019/scene-review.md`
și `review.html`, raport HTML local fără rețea, cu profil și alegeri goale implicit.
Butonul exportă decizii JSON cu snapshot/scene ID/candidate ID; nu aplică editări.
`ctc-review.html` și raportul CTC curent leagă cele 170 unități de alignment_key,
cu ascultare din MP4-ul existent și export de decizii numai cu reviewer explicit.
Nicio decizie nu este preselectată și alinierea nu se modifică prin aceste pagini.
Numerele candidaților sunt valabile pentru snapshotul afișat. Candidații
nedescărcați cer download explicit ulterior; nu există trei alternative pentru
toate scenele. Contact sheets detaliate păstrate în `review-first-layout2/`;
cadre din exporturile efective în `recovery-20261019/landscape/` și `portrait/`.

```bash
./media scenes assets-integral-20261018 --scene scene-016 --inspect
./media render assets-integral-20261018 --profiles portrait --subtitles classic --resume-run 5ba454a524f74ffc8991987e14b12cf1 --rerender-changed --output-root output/media/O_DESTINATIE_NOUA
```

Inventar: **19 scene = 9 fotografii + 2 video + 8 fallback**, 11 NEEDS_REVIEW
plus 8 FALLBACK cu review uman necesar; 0 LICENSE_UNKNOWN selectate.
Bibliotecă: 59 înregistrări / 59 checksumuri distincte, 17 Commons, 1 Openverse,
41 grafice locale, 0 Pexels; 46976141 octeți în total la audit.
Două thumbnails HD, titlul existent, SRT/ASS/aliniere și credits JSON/Markdown
sunt păstrate. Integral: tranziții cut; un zoom_in în landscape, portrait static.
Crossfade este verificat separat în istoricul proiectului, nu folosit aici.

Probele curente: `recovery-20261019/final-audit.json`,
`partial-rerender-proof.json`, `final-acceptance.json`. Workflow-ul istoric
rămâne păstrat cu phase=running/render failed; nu dovedește un proces activ și
nu este declarat retroactiv reușit. Recovery-ul are receipts/acceptanță separate.
Status vizual: numai cadre selectate; auditiv not_listened, editorial not_reviewed.
Revizuirea umană a scenelor/fallback-urilor și a celor 170 unități CTC rămâne necesară.

## CTC review și subtitrări — 2026-10-19 UTC

Etapa tehnică este implementată și testată pe sample; integralele validate
rămân baseline nemodificat. Review CTC actual, cu cele 170 unități și redare
din MP4-ul existent: `work/media/subtitles-20261019/ctc-review-v2.html`.
Deschide fișierul HTML local în browser. Pagina și scene review au fost testate
în Chromium 149 existent, inclusiv redare și export; nu s-a făcut review uman.

Comenzile reale pentru un raport nou și deciziile exportate de reviewer:

```bash
./media alignment-review assets-integral-20261018 --output work/media/REVIEW_NOU/ctc-review.json --media output/media/assets-integral-20261018-first/assets-integral-20261018/landscape/video.mp4
./media alignment-review assets-integral-20261018 --validate /cale/ctc-decisions.json
./media alignment-review assets-integral-20261018 --apply /cale/ctc-decisions.json
```

`--output` produce JSON/Markdown/HTML; alege o destinație nouă. În HTML:
redă intervalul, consultă textul/confidence/timpii și alege explicit ACCEPT,
ADJUST_START, ADJUST_END, ADJUST_BOTH, REJECT sau NEEDS_REVIEW. Numai câmpurile
cerute de acțiune sunt editabile. Reviewer este obligatoriu; exportul gol,
valorile negative/invalide și suprapunerile sunt refuzate. Exportul salvează
timestampul UTC, `alignment_key`, `source_text_sha256`, `audio_sha256`.
Unitățile UI sunt secunde; JSON-ul aplicabil folosește eșantioane întregi.

Validarea verifică efectiv hash-urile surselor, identitatea textului și audio-ului,
revizia alinierii, limitele audio și ordinea unităților. `audio_sha256` identifică
cronologia verificată (hash-uri fișiere, intervale, sample rate, durată), nu MP4-ul
de playback; text hash include textele materialului și fișierele originale.
Rapoartele vechi fără aceste identități/timestamp nu sunt aplicabile direct:
generează un raport nou. `--validate` nu scrie în material. `--apply` este numai
pentru deciziile reale ale reviewerului: păstrează copii exacte înainte/după,
fișierul deciziilor, jurnal reluabil și `before-after.json` sub
`materials/MATERIAL/alignment-reviews/`. Aplicarea repetată este idempotentă;
reluarea refuză fișiere schimbate în afara perechii auditate. Numai indicii
expliciți primesc review/corecții; celelalte dicționare de unități și timpii lor
rămân identice. Scorurile mici nu sunt șterse. Nicio decizie a testelor nu a
fost aplicată materialului integral.

Subtitrările au trei moduri distincte: `classic`, `highlight`, `scroll`.
`subtitles` are default classic; `render` păstrează default-ul istoric off,
iar `--subtitles classic` păstrează modul clasic. Exemple:

```bash
./media subtitles MATERIAL --profiles landscape,portrait --mode classic --ass-preset safe --output-dir work/media/SUB_CLASSIC_NOU
./media subtitles MATERIAL --profiles landscape,portrait --mode highlight --ass-preset safe --output-dir work/media/SUB_HIGHLIGHT_NOU
./media subtitles MATERIAL --profiles landscape,portrait --mode scroll --ass-preset safe --output-dir work/media/SUB_SCROLL_NOU
./media --config /cale/media-styled.json render MATERIAL --profiles landscape,portrait --subtitles highlight --ass-preset boxed --resume-run RUN_ID --output-root output/media/EXPORT_NOU
```

Configurația este un fișier media complet, cu această secțiune aditivă:

```json
{
  "subtitle_style": {
    "preset": "safe",
    "font": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "outline": 3, "shadow": 1, "alignment": 2,
    "color": "FFFFFF", "outline_color": "101010",
    "background": "80000000", "highlight_color": "FFFF00",
    "highlight_bold": false, "margin_x": 0.06,
    "safe_area": [0.06, 0.52, 0.06, 0.10],
    "scroll_seconds": 0.18, "scroll_lines": 3,
    "profiles": {
      "landscape": {"font_size": 54, "margin_v": 0.14, "line_spacing": 8},
      "portrait": {"font_size": 58, "margin_v": 0.12, "line_spacing": 12}
    }
  }
}
```

Preseturi: safe, boxed, minimal; `--ass-preset` selectează presetul, iar
câmpurile explicite/profile overrides au precedență asupra valorilor lui.
Culorile sunt RGB, background este ASS AARRGGBB (AA=00 opac, FF transparent).
Marginile/safe_area sunt fracții din cadru, ordinea safe_area este left/top/right/bottom.
Alignment este 1–9, font_size/outline/shadow/line_spacing sunt pixeli ASS.
Line spacing este implementat prin poziții verticale măsurate pentru fiecare
linie; nu este câmpul ASS Spacing, care controlează spațiul dintre caractere.
Fontul trebuie să existe local; configurațiile necunoscute/invalide sunt refuzate.

Highlight folosește numai intervalele existente `[start,end)`: context neutru
în pauze, cuvântul sau display_group curent colorat, textul sursă păstrat.
Scroll înfășoară textul o singură dată per scenă și deplasează liniile continuu,
determinist, la limitele lor; nu schimbă fereastra la fiecare cuvânt.
Măsurarea fontului, clip-ul safe area și rezervarea title/panel overlays
previn overflow; un layout imposibil este refuzat. Pentru fallback graphic,
margin_v are minimum 14% landscape și 10% portrait. Această corecție sistemică
este verificată pe sample; MP4-urile integrale istorice nu au fost rerandate.
ASS are rezoluție temporală de centisecundă, apoi video cuantizează la cadre;
`layout.json` păstrează intervalele sursă și intervalele prea scurte omise.
Diferența A/V nu certifică precizia semantică a alinierii.

`subtitle_style`, modul și presetul invalidează asamblarea finală cu subtitrări;
nu schimbă identitatea scenelor, TTS, master audio, CTC, discovery sau downloads.
Folosește `--resume-run` și un `--output-root` nou pentru a păstra exporturile.
Câmpurile istorice exterioare `font`/`safe_margin` sunt folosite și de scene/titluri;
pentru schimbări exclusiv de subtitrare folosește secțiunea `subtitle_style`.
Render adaugă referința exportului în manifestul materialului; aceasta nu este
o schimbare de audio/aliniere. Nu se introduce acces la rețea în render.

Probe: `work/media/subtitles-20261019/`, indexul `samples.html`, șase MP4-uri HD
de 16,46 s (classic/highlight/scroll × landscape/portrait), 494 cadre fiecare,
cu video/foto/fallback și opt unități low-confidence existente.
`subtitle-acceptance.json` conține full decode și diferențe de pixeli;
`style-invalidation.json` dovedește 3 reuse/0 rerender pentru schimbare de stil,
iar `protection-after.json` confirmă cele 720 fișiere protejate și 38 scene keys.
Statusuri: tehnic passed, browser passed, cadre selectate inspectate de agent;
listening not_listened, editorial not_reviewed, ctc_human_review pending.
Următoarea etapă pregătită în plan: EXTERNAL AUDIO MIX.

## External audio mix — 2026-10-19 UTC

Mixerul opțional produce un WAV derivat separat de masterul narativ existent.
Nu sintetizează, nu realiniază și nu modifică audio-ul sursă. Starea tehnică și
fișierele de probă sunt în `work/media/audio-mix-20261019/`; muzica de producție
rămâne **READY_FOR_USER_AUDIO**. Nu s-a ales sau descărcat muzică pentru publicare.

Configurația se importă aditiv în `material.json.audio_mix`, schema material 1
rămânând compatibilă. Narațiunea este trackul obligatoriu implicit din timeline;
lista `tracks` conține numai music, sfx și ambience. Fișier JSON de configurare:

```json
{
  "enabled": true,
  "tracks": [
    {
      "type": "music", "path": "/cale/muzica-locala.wav",
      "source": "sursa furnizată de utilizator", "creator": "autor",
      "license": "licența verificată de utilizator",
      "start": 2.0, "end": 60.0,
      "source_start": 25.0, "source_end": 90.0,
      "volume_db": -20, "loop": false,
      "fade_in": 1.0, "fade_out": 2.0
    },
    {
      "type": "sfx", "path": "/cale/efect-local.wav",
      "start": "00:10.500", "duration": 0.8,
      "volume_db": -12, "fade_in": 0.01, "fade_out": 0.05
    }
  ],
  "ducking": {
    "enabled": true, "amount_db": 12,
    "attack_ms": 40, "release_ms": 350, "threshold_db": -40
  },
  "normalization": {
    "enabled": true, "loudness_lufs": -19,
    "true_peak_db": -2, "loudness_range": 11
  }
}
```

Înlocuiește căile și intervalele cu valori care încap în material și în surse.
Timpii de configurare sunt secunde sau HH:MM:SS.fff; `end` și `duration` sunt
alternative exclusive. `source_start/source_end` aleg intervalul fișierului
extern. Intern sunt stocate eșantioane întregi, rotunjite half-up la rata
materialului; SFX nu este legat de FPS. Căile relative sunt relative la fișierul
JSON importat. SHA256, codec, rată, canale, durată și număr de eșantioane decodate
sunt păstrate împreună cu provenance; `checksum` opțional declarat este verificat.
Metadatele lipsă rămân necunoscute, fără atribuirea unei licențe presupuse.

Comenzile reale, integrate în `./media`:

```bash
./media audio-mix MATERIAL --inspect
./media audio-mix MATERIAL --validate /cale/mix.json
./media audio-mix MATERIAL --set /cale/mix.json
./media audio-mix MATERIAL --render --output-dir output/media/MIX_AUDIO_NOU
./media audio-mix MATERIAL --verify output/media/MIX_AUDIO_NOU/mix.wav
./media audio-mix MATERIAL --render --mux-video /cale/baseline.mp4 --output output/media/MIX_VIDEO_NOU.mp4
./media audio-mix MATERIAL --disable
./media audio-mix MATERIAL --render --output-dir output/media/NARRATION_ONLY_NOU
```

`--validate` verifică fără schimbarea materialului. `--set` păstrează materialul
anterior și configurația importată în `audio-mix-revisions/`; `--disable` păstrează
rețeta dar o dezactivează. Modul disabled produce PCM narativ identic, fără DSP,
și nu cere fișierele externe. `--verify` verifică WAV-ul mono la rata și numărul
exact de eșantioane ale materialului, full decode, peak și loudness raportate.
Alege directoare/fișiere de ieșire noi; comenzile refuză suprascrierea exporturilor.

Sursele sunt locale, cu exact un stream audio și maximum opt canale. FFprobe,
hash-ul și decodarea completă sunt verificate; protocoalele FFmpeg sunt limitate
la file/pipe. Nu există streaming, cloud sau download în mixer. FFmpeg existent
face resampling SWR determinist, fără dither, la rata materialului; downmix-ul
mono este media aritmetică explicită a canalelor. DSP folosește float, iar WAV-ul
final este PCM s32 mono (22050 Hz pentru narațiunea curentă). Nu normalizăm fiecare
track: gain-ul independent este exprimat în dB și balanța rămâne explicită.

Ducking afectează numai music/ambience. Detectorul de energie RMS al narațiunii
folosește blocuri de 10 ms; nu este ASR și nu folosește/modifică timpii CTC.
Anvelopa continuă este limitată de amount_db; attack/release sunt constantele
de timp pentru aproximativ 63% din schimbare. Detectorul poate anticipa cel mult
un bloc de 10 ms. Pragul și nivelurile sunt alegeri configurabile care cer audiție.
Proba controlată măsoară reducere de **11,989 dB** pentru amount_db=12 și revenire
în pauză; SFX nu este ducked.

Fade-urile sunt nenegative și trebuie să încapă împreună în durata activă.
O sursă scurtă cu loop=false se oprește, apoi contribuie cu tăcere; nu este repetată
implicit. Loop este permis explicit numai pentru music/ambience. `loop_fade_ms`
(implicit 5 ms) aplică rampe la capetele perioadei, fără schimbarea lungimii sau
fazei perioadei; 0 dezactivează această protecție. Nu este crossfade editorial
între melodii și nu constituie verificare auditivă a click/pop-urilor.

Mixul final folosește convenția existentă −19 LUFS / −2 dBTP / LRA 11, în două
treceri, dual_mono=false; modul efectiv linear/dynamic este raportat. Narațiunea
nu este normalizată încă o dată separat. Suma float poate depăși 0 dBFS fără
clipping intermediar; o sumă peste domeniul loudnorm primește atenuare globală
raportată înainte de măsurarea finală. Cu normalization.enabled=false, se aplică
numai atenuarea statică necesară respectării plafonului true peak, dacă este cazul.
Nu există hard limiter ascuns. Tăcerea completă și semnalele prea scurte pentru
LUFS sunt raportate distinct; pentru semnal măsurabil ≥3 s normalizarea activă
cere ±1 LU și true peak cel mult ținta +0,1 dB. AAC-ul final este măsurat separat,
cu pragul existent de cel mult −1 dBTP.

Pauzele existente rămân eșantioane ale narațiunii; music/ambience pot continua
peste ele în intervalele configurate. Mixerul nu adaugă intro-uri sau pauze și nu
întinde vocea. Audio-ul clipurilor video rămâne mut implicit; se poate folosi
numai dacă utilizatorul îl declară separat ca track audio local explicit.

Split/merge existente păstrează acum și mixul:

```bash
./media split MATERIAL --mode extract --intervals /cale/intervale-in-esantioane.json --prefix FRAGMENT_MIX --apply
./media merge --id COMPILATIE_MIX --materials FRAGMENT_MIX-001 ALT_MATERIAL
```

Un fragment decupează mixul calculat în contextul original, inclusiv anvelopa,
trim, faza de loop, fade-uri și gain-ul normalizării. Nu reia normalizarea la
începutul fragmentului. Merge păstrează contexte și offseturi distincte; muzica
din două surse/configurații nu este unită automat. Nu se face normalizare globală
suplimentară a compilației și nu se suprapun vocile. Split→merge PCM este identic
cu mixul părinte. Ratele narative diferite la merge cer încă conversie explicită;
suportul ratelor externe diferite în mixer nu schimbă această regulă.

Cache-ul este separat, `work/media/audio-mix/FINGERPRINT/`, cu rețeta și hash-urile
surselor/codului/FFmpeg. Gain/path/timing/fades/ducking schimbă numai mixul și
asamblarea audio finală. Nu schimbă TTS, CTC, discovery, scene keys sau subtitrările.
`--mux-video` copiază streamul video și verifică hash-ul pachetelor; inclusiv
subtitrările arse rămân identice. `render` folosește automat mixul activ și poate
reutiliza compoziții cu `picture_request` compatibil din exporturi anterioare,
fără apelarea generatorului de subtitrări. Pentru un baseline istoric fără acest
receipt nou, folosește `audio-mix --mux-video` explicit. Loturile nu invalidează
subtitles/thumbnail/titles numai pentru schimbarea rețetei audio; workflow-urile
care declară întregul manifest ca input păstrează invalidarea acelui input declarat.

Fiecare încercare păstrează comenzi/stderr/returncode și state. Fișierele `.part`
nu sunt cache valid; mixul se publică atomic după verificare. Retry folosește
intermediari unici și păstrează încercările întrerupte. Pentru predarea curentă:
`work/media/audio-mix-20261019/samples.html` oferă A/B WAV și un singur MP4 portrait
cu highlight păstrat. Fixture-urile sunt tonuri/noise locale, exclusiv tehnice.
technical_audio_status=passed; listening_review=not_listened. Pentru muzică reală,
furnizează un fișier local ales/aprobat și metadatele sale, apoi validează/importă
configurația; audiția și acceptanța editorială rămân ale utilizatorului.

# Rezultatele verificărilor

Document actualizat la **17 octombrie 2026 UTC**. Secțiunile 1–5 păstrează istoricul audio și auditul anterior al documentației, fără rerulare în acel audit. **Secțiunea 6 consemnează separat testele noi ale extensiei media**, regresia audio izolată și verificările curente doar în citire. Recuperările producției sunt consemnate cronologic la final. Nicio probă nouă nu suprascrie rezultatele istorice.

Ghidul de utilizare este [README.md](README.md). Acest document păstrează separat testele implementării, experimentul de pronunție și conversiile utilizatorului. `technical_status: passed` și `full_decode: true` consemnează verificări tehnice; `listening_status: not_listened` indică lipsa unei audiții înregistrate, fără a semnala eșecul exportului.

## 1. Testele istorice ale implementării — 16 octombrie 2026

Rezultate istorice din Debian 13 / WSL, Python 3.13.5, x86_64, CPU, aplicația 1.0.0. La începutul implementării inputul personal `input/text.txt` nu exista; atunci nu a fost creat sau suprascris cu exemple. Ulterior utilizatorul a adăugat și a corectat textul; conversiile lui sunt separate mai jos. Nu s-a consemnat audiție umană în rapoarte.

| Grup | Trecute | Eșecuri | Omise | Timp teste |
|---|---:|---:|---:|---:|
| unit | 38 | 0 | 0 | 0.10 s |
| integration | 4 | 0 | 0 | 34.01 s |
| long | 1 | 0 | 0 | 193.15 s |
| offline | 1 | 0 | 0 | 4.61 s |

Total istoric: **44 de teste trecute, 0 eșecuri, 0 omise** în cele patru selecții de mai sus, rulate pe 16 octombrie 2026; nu au fost rerulate pentru această actualizare de documentație. XML-urile JUnit și logurile sunt în `work/`; `work/validation-summary.json` centralizează cifrele și hash-urile.

Comenzile executate atunci pentru selecțiile finale (nu reprezintă instrucțiuni de rerulare în timpul documentării):

```bash
.venv/bin/python -m pytest -m 'not integration' -q --junitxml=work/unit-tests.xml
.venv/bin/python -m pytest -m 'integration and not slow and not offline' -q --junitxml=work/integration-tests.xml
.venv/bin/python -m pytest -m 'integration and slow' -q --junitxml=work/long-tests.xml
.venv/bin/python -m pytest -m offline -q --junitxml=work/offline-tests.xml
```

Acoperire: UTF-8/BOM/CRLF, sedile/NFC/spații, prescurtări/zecimale/URL-uri/inițiale, reconstrucție, înlocuiri fără cascadă, expansiuni lungi de pronunție, identitate cache, opțiuni invalide, lipsă spațiu simulată, valori audio nefinite, limite interne și pauze, recuperare simulată și SIGINT real, păstrare hash/timestamp, paragrafe identice, paragraf modificat, bitrate fără resinteză, cache corupt, model lipsă și ONNX invalid la încărcare reală, căi cu spații/diacritice/caractere speciale, input gol/invalid, FFmpeg eșuat, destinație protejată, export și decodare completă.

| MP3 în output/ | Durată | LUFS | dBTP | Segmente | Cache hits |
|---|---:|---:|---:|---:|---:|
| proba_0.95.mp3 | 18.834 s | -19.46 | -2.44 | 2/2 | 0 |
| proba_1.00.mp3 | 18.599 s | -19.49 | -2.43 | 2/2 | 2 |
| proba_1.05.mp3 | 18.129 s | -19.51 | -2.43 | 2/2 | 0 |
| proba_offline.mp3 | 15.360 s | -19.38 | -2.43 | 1/1 | 0 |
| test_lung.mp3 | 3868.839 s | -19.46 | -2.41 | 280/280 | 280 |

Toate ieșirile: MP3 mono 22050 Hz, 128000 bit/s, decodare completă și praguri tehnice acceptate. Tipul efectiv al normalizării și eventualele încercări sunt în `audio.attempts` din rapoarte; măsurătorile finale sunt în `audio.verification.measurements.input_*`.

Textul lung: 51643 caractere în fișier, 51642 după normalizare, 280/280 segmente, reconstrucție textuală exactă. Cei trei marcatori apar textual o singură dată fiecare. Cele 15 chei unice reflectă paragrafele sintetice repetate intenționat; fiecare poziție a fost asamblată. Exportul final a refolosit 280 segmente din cache, de aceea RTF-ul lui este null. Acoperirea textuală nu demonstrează auzirea tuturor cuvintelor.

Offline: testul a creat un namespace de rețea diferit de cel părinte, a confirmat blocarea conexiunii externe și a randat un text sintetic nou, cu zero cache hits. Dovada și raportul sunt în `work/offline-evidence.json`; MP3-ul a fost păstrat ca `output/proba_offline.mp3`. Blocarea efectivă a inclus restricțiile sandbox-ului (EPERM). Nu se pretinde o probă pe rețeaua gazdei modificată.

Instalare: mediul curat `.venv-clean` a instalat `requirements.lock` cu `--require-hashes`; `pip check` a trecut (`work/clean-install.log`). `bootstrap.sh` a trecut de două ori consecutiv, fără ștergeri (`work/bootstrap.log`). `doctor` a trecut: CPUExecutionProvider, model/checksum, FFmpeg, ffprobe, libmp3lame, loudnorm, permisiuni și spațiu (`work/doctor.json`). `ffmpeg -h filter=loudnorm` este salvat în `work/loudnorm-help.txt`.

Ajustări față de calea preferată: sudo a cerut parolă, astfel pachetele apt nu au fost instalate de agent. Build-ul FFmpeg static 7.0.2 este instalat numai în `.tools/`, cu sursă, hash și licență păstrate. SoundFile folosește libsndfile din wheel. API-ul Piper 1.8.0 aplică intern clipping float; proiectul nu adaugă o conversie int16 sau normalizare independentă pe propoziții.

Iterații de test: un test inițial a identificat protejarea prea largă a punctului terminal după URL; segmentarea a fost corectată. Prima probă offline a produs MP3, dar aserțiunea auxiliară asupra antetului de rute a eșuat pe fișierul gol expus de mediu; testul a fost corectat, întărit cu verificarea namespace-ului și a conexiunii blocate, apoi reluat cu succes. Primele randări fără FFmpeg au păstrat cache-ul; nu au fost raportate drept MP3 reușite.

Limite: vocea și marcatorii nu au fost verificați auditiv; nu se certifică pronunția sau fiecare cuvânt acustic. Python 3.11/3.12, alte arhitecturi și situația reală de disc plin nu au fost testate; lipsa spațiului a fost simulată, conform planului. Nu s-a umplut discul, nu s-a instalat CUDA, Docker sau un server.

## 2. Proveniența testelor și a măsurătorilor istorice

Tabelul de timp din secțiunea 1 păstrează sumele timpilor cazurilor de test din documentul inițial. XML-urile existente includ și timpul întregii suite, cu overhead:

| Selecție | XML | Început în Europe/Bucharest | Teste | Timp suită |
|---|---|---|---:|---:|
| Unitare și simulări | [unit-tests.xml](work/unit-tests.xml) | 2026-10-16 10:37:26 +03:00 | 38 | 0,203 s |
| Integrare fără slow/offline | [integration-tests.xml](work/integration-tests.xml) | 2026-10-16 10:33:50 +03:00 | 4 | 34,112 s |
| Text lung | [long-tests.xml](work/long-tests.xml) | 2026-10-16 10:30:14 +03:00 | 1 | 193,231 s |
| Offline | [offline-tests.xml](work/offline-tests.xml) | 2026-10-16 10:34:31 +03:00 | 1 | 4,718 s |

Toate cele patru XML-uri au `failures=0`, `errors=0`, `skipped=0`. [model-tests.xml](work/model-tests.xml), la 10:33:07 +03:00, conține o execuție separată a unui test inclus și în suita de integrare; nu este numărat a doua oară în totalul de 44. [work/validation-summary.json](work/validation-summary.json) este o centralizare istorică, nu un jurnal actualizat automat la fiecare rulare.

Rulările probelor sintetice din secțiunea 1:

| Fișier | Run-id din raport |
|---|---|
| `proba_0.95.mp3` | `20261016T072919-7f36ea7a` |
| `proba_1.00.mp3` | `20261016T072918-35865ba7` |
| `proba_1.05.mp3` | `20261016T072923-dc76d101` |
| `proba_offline.mp3` | `20261016T073431-cbb24489` |
| `test_lung.mp3` | `20261016T073015-f2ca34ec` |

Fiecare are raportul aferent în `output/`. Run-id-urile codifică ora UTC, în timp ce XML-urile de mai sus declară explicit fusul +03:00. Cele 280 cache hits ale exportului lung nu sunt o măsurare a vitezei unei sinteze proaspete. Relatarea istorică a modelului CPU, normalizării și izolării de rețea este susținută de rapoartele păstrate, fără o nouă probă de izolare în această etapă.

## 3. Experimentul de pronunție — versiunea anterioară a textului

Experimentul din 16 octombrie 2026 folosește sursa cu SHA-256:

```text
c57368b6450b3ddc51d0d0465408314630f262369aeeb0efae370ae4bd11be3f
```

Aceasta este versiunea veche, corespunzătoare [work/review-text/segments.json](work/review-text/segments.json) și [manifestului 20261016T075928-59e23b0c](work/runs/20261016T075928-59e23b0c/manifest.json), nu textul corectat actual. Din cele 17 forme semnalate au fost extrase 13 propoziții complete, în ordinea din document; au fost păstrate majusculele de accentuare.

| Probă | Run-id | Segmente | Cache hits inițiale | Durată MP3 | LUFS | dBTP |
|---|---|---:|---:|---:|---:|---:|
| [Original](output/pronuntii_original.mp3) | `20261016T081803-fab6f433` | 13/13 | 0 | 115,905306 s | −19,48 | −2,42 |
| [Propus](output/pronuntii_propuse.mp3) | `20261016T081816-a24b3e25` | 13/13 | 0 | 116,166531 s | −19,49 | −2,42 |

Ambele au aceeași voce/configurație, viteză 1.0, MP3 mono 128000 bit/s la 22050 Hz, decodare completă și `technical_status: passed`. `listening_status` este `not_listened`. Toate cele 13 pasaje propuse au chei cache și hash-uri audio diferite de original și au fost sintetizate din nou. Perechile SRI/PSD separate au refolosit apoi cache-ul aceleiași variante proaspăt generate, fără a confunda audio-ul propus cu cel original.

Dovezi și comparație:

- [Comparația integrală, motivele și reperele pentru ascultare](output/pronuntii_comparatie.md).
- [Verificările, hash-urile înainte/după și comparația cache-ului](output/pronuntii_verificari.json).
- [Regulile experimentale pe propoziții complete](output/pronuntii_reguli_experimentale.json), distincte de `pronunciations.json`.
- [Perechea SRI original](work/pronuntii-experiment/sigle/SRI_original.mp3) / [„se re i”](work/pronuntii-experiment/sigle/SRI_propuse.mp3), rulări `20261016T081844-a4c6ac9f` / `20261016T081846-52b3e2c7`.
- [Perechea PSD original](work/pronuntii-experiment/sigle/PSD_original.mp3) / [„pe se de”](work/pronuntii-experiment/sigle/PSD_propuse.mp3), rulări `20261016T081847-43ee10d0` / `20261016T081849-f31b2c2d`.

Interpretările `500:000 → 500.000`, `350:000 → 350.000` și `‘89 → anul 1989` au fost marcate propuneri neconfirmate. Nu au fost introduse în dicționarul general și experimentul nu a regenerat materialul integral. Diacriticele contextuale și numerele în cuvinte apar în copia de probă; ele nu constituie aprobare auditivă.

Dovada de conservare din acel experiment arată sursa veche și opt MP3-uri existente atunci neschimbate. Acea dovadă este istorică: nu trebuie folosită ca afirmație că `input/text.txt` sau `output/text.mp3` nu s-au schimbat ulterior prin conversiile utilizatorului.

## 4. Conversiile reale ale utilizatorului

### Versiunea inițială, înainte de corectarea textului

| Artefact | Run-id | Segmente | Cache hits | Viteză | Durată MP3 din raport |
|---|---|---:|---:|---:|---:|
| `output/proba.mp3`, preview | `20261016T075915-f95fa2fa` | 4/4 | 0 | 1.0 | 74,396735 s |
| Prima conversie integrală | `20261016T075928-59e23b0c` | 29/29 | 3 | — | Raportul/MP3-ul de la vechea destinație nu mai sunt perechea curentă |
| `output/text_lent.mp3` | `20261016T080108-fcc8e64d` | 29/29 | 0 | 0.95 | 712,594286 s |

Cele 3 cache hits ale primei conversii integrale sunt numărate din manifestul istoric. Manifestul nu conține toate câmpurile raportului final; nu îi atribuim durata sau timpul total din raportul actual, care aparține altei rulări. Preview-ul și MP3-ul lent păstrează rapoarte cu `source_sha256` al versiunii vechi `c573…be3f`. Faptul că rapoartele indică aceeași cale `input/text.txt` nu le face rezultate ale sursei actuale.

### Rularea de referință pe textul corectat

**Run-id:** `20261016T090507-5f8a96d4`, început 16 octombrie 2026, 09:05:07 UTC / 12:05:07 Europe/Bucharest. Este cel mai recent run-id dintre cele 34 de manifeste locale inspectate la actualizarea documentației; nu s-a identificat o rulare mai nouă.

Surse locale confruntate:

- [Manifestul de referință](work/runs/20261016T090507-5f8a96d4/manifest.json).
- [Raportul curent output/text.report.json](output/text.report.json).
- [MP3-ul curent](output/text.mp3), al cărui SHA-256 coincide cu `output_sha256` din raport.
- `input/text.txt`: checksum identic cu `source_sha256`, iar normalizarea sa coincide cu textul manifestului.

SHA-256 al sursei actuale:

```text
466c0f8e31d660f346750ab9b95fecbe45dc29763a479a9e2e7561f8f271aa73
```

| Verificare | Valoare locală și proveniență |
|---|---|
| Stare/acoperire | Manifest `state: complete`, 30/30 segmente; toate segmentele complete. |
| Cache | 0 din 30 segmente cu `cache_hit: true`; raport `cache_hits: 0`. |
| Durată MP3 | `audio.verification.format.duration: 688.875102` s, aproximativ 11 min 29 s. |
| Timp total | Raport `timings.total_seconds: 57.56760829999985` s, aproximativ 57,57 s. |
| Încărcare | 1,415582879 s, în manifest și raport. |
| Sinteză nouă | 30,793829645 s pentru 669,918911565 s de audio generat, înainte de pauzele suplimentare; în manifest și raport. |
| RTF | Raport `timings.rtf: 0.04596650298030682`, separat de export și pauze. |
| Procesare audio finală | Raport `timings.processing_seconds: 25.146861146000447` s; nu este timpul total. |
| Format | MP3, mono, 128000 bit/s, 22050 Hz. |
| Nivel decodat | −19,48 LUFS și −2,30 dBTP. |
| Stare tehnică | Raport `technical_status: passed`; verificare `accepted: true`, `full_decode: true`. |
| Audiție | `listening_status: not_listened`. |
| Dicționar | Manifest `replacements: []`; dicționarul general curent este `[]`. |

Valorile din conversație sunt confirmate, cu rotunjirea declarată pentru timpul total. **Durata, formatul, timpul total și starea verificării audio provin din raport, nu exclusiv din manifest.** Manifestul oferă starea segmentelor, cache hits și timpii de încărcare/sinteză; nu conține `timings.total_seconds`, metadatele MP3 sau `full_decode`. Această distincție evită atribuirea unor câmpuri inexistente manifestului.

Și manifestul de referință are **17 avertismente**, verificate independent pentru această versiune. Lista nu este copiată din experiment: de exemplu, acum apar `500.000`, `350.000`, `1967,`, iar offseturile diferă. `work/review-text/normalized.txt` nu coincide cu normalizarea sursei actuale. Numărul egal de avertismente nu înseamnă aceleași pasaje în aceeași versiune; avertismentele rămân indicii textuale generale, nu erori detectate în audio.

Raportul actual nu demonstrează că interpretările experimentale au fost aprobate și nu este atribuit aplicării lor: sursa a fost corectată separat, iar manifestul nu înregistrează înlocuiri de dicționar. `output/text_lent.mp3`, preview-ul vechi și probele de pronunție nu au fost regenerate pentru sursa nouă.

## 5. Auditul documentației audio anterior extinderii media

Pe 16 octombrie 2026 au fost citite CLI-ul, configurația, wrapperul, scripturile, modulele text/cache/pipeline/audio, documentele de licențiere, rapoartele, manifestele și XML-urile locale. Valorile istorice au fost confruntate, fără generare audio sau instalare. Exemplele CLI sunt verificate prin parserul existent, iar linkurile locale prin existența țintelor. Hash-urile fișierelor protejate sunt comparate înainte/după editarea Markdown, nu prezentate drept o nouă validare auditivă sau rerulare pytest.

Limită Git: `git rev-parse --show-toplevel` indică `/home/daniel/projects`, iar `git check-ignore -v` arată că cele trei documente principale din `rec/` sunt ignorate de regula `/*` a repository-ului părinte. Astfel, `git status`/`git diff` obișnuite nu reflectă editările lor; diferențele sunt verificate și direct față de copiile de dinaintea editării. Nu s-au modificat reguli Git, nu s-a făcut commit sau push.

Rămân neverificate auditiv pronunția, intonația, naturalețea și acoperirea acustică a fiecărui cuvânt. Nu există în rapoarte o certificare subiectivă a vocii. Testele pytest, izolarea efectivă de rețea și benchmark-urile menționate mai sus sunt rezultate istorice; nu sunt declarate ca executate din nou pentru această sarcină.

**Întreținere:** schimbările CLI/configurație/comportament cer actualizarea documentației aferente. Rezultatele se datează, se leagă de versiune/run-id și de hash-ul sursei când este relevant, iar istoricul nu se înlocuiește cu rezultatele altei versiuni a textului.

## 6. Extensia media 0.1.0 — rezultate noi din 16 octombrie 2026

Implementare etapizată din planul consolidat, [exemplarul canonic](docs/PLAN_EXTINDERE_MEDIA_REC.md). Codul audio, `.venv`, rec.json, dicționarul, inputurile, MP3-urile inițiale și cache-ul audio nu au fost modificate. Nu s-au instalat pachete sau modele. Media reutilizează Python Debian/Pillow 11.1.0 și FFmpeg local existent, fără GPU obligatoriu. Schema materialelor este 1, fără migrarea manifestelor audio. Nu există commit Git de asociat; repository-ul părinte ignoră proiectul, iar diffs/hash-uri au fost inspectate direct.

### F0 — audit și regresie izolată

Hardware observat direct: 4 CPU, MemTotal 4010608 KiB (~3,8 GiB), x86_64, Debian 13.4/WSL. `/dev/dxg`, `/dev/dri`, nvidia-smi și executabilul WSL nvidia-smi nu sunt expuse. Aceasta înseamnă GPU/VRAM **neobservabile aici**, nu că gazda Windows nu ar avea GPU. Capabilități CPU în [capabilities.json](work/media/audit/capabilities.json): H.264/AAC, scale/pad/crop/ass/overlay/zoompan/xfade/concat/atrim/tpad și test real de encodare/decodare. Font local DejaVu Sans.

Regresia a copiat codul/testele/exemplele sintetice într-un proiect izolat `work/media/audit/audio-regression/`, cu propriile input/output/cache/runs. Numai modelul, executabilele și mediul Python sunt referite din instalarea existentă. Fișierele utilizatorului nu au fost înlocuite de fixture-uri. Au fost rerulate toate cele 44 teste, inclusiv textul lung și namespace-ul offline. Acest rezultat este nou și separat de vechiul total de 44.

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -c work/media/audit/audio-regression/pyproject.toml work/media/audit/audio-regression/tests -q -p no:cacheprovider --junitxml=work/media/audit/audio-regression.xml
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/media -q -p no:cacheprovider --junitxml=work/media/media-tests.xml
./media --report work/media/audit/capabilities.json doctor
```

| Suită nouă | Început UTC din XML | Trecute | Eșecuri/omise | Timp suită |
|---|---|---:|---:|---:|
| [Audio izolat](work/media/audit/audio-regression.xml) | 2026-10-16T09:47:49.083583+00:00 | 44 | 0 / 0 | 239.500 s |
| [Media](work/media/media-tests.xml) | 2026-10-16T10:15:14.797319+00:00 | 16 | 0 / 0 | 21.488 s |

Total al selecțiilor finale noi: **60 teste trecute, fără eșecuri/omisiuni** (44 regresie audio + 16 media). XML-urile și logurile corespondente sunt dovezile; nu se adaugă testul model duplicat din istoricul anterior.

Suita media acoperă: profile/dimensiuni invalide, import/validare aliniere, text neacoperit și timpi suprapuși, SRT/ASS classic/highlight/scroll, mapări afișat/rostit pe grup, escapare ASS, titluri deterministe/manuale/blocate, thumbnail și depășire font, split→merge PCM identic, același renderer pe integral/copil/compilație, tăiere de cuvânt refuzată, export existent și force, scene/motion/crossfade/titlu, asset corupt, mix imagine/clip, lipsă aliniere fără timpi inventați, căi cu spații/apostrof/diacritice, schimbare CWD, ID/focală invalide, întrerupere/relansare, lot incomplet și invalidare, randare reală CPU în namespace de rețea.

Prima extindere a suitei a produs un eșec: materialul lipsă din lot scăpa din raportarea per-job. A fost corectat, apoi suita a trecut integral. Testele finale nu maschează acel eșec inițial.

### F1 — video cu vocea Piper existentă

Materialul `audio-demo` importă `output/proba_1.00.mp3`, textul sintetic `samples/test_ro.txt` și raportul aferent. Nu este textul privat integral și nu a necesitat sinteză nouă. Imaginea de copertă este compusă local din forme și litere. Profilele sunt randate din aceeași copie PCM și aceeași cronologie; nu s-au folosit clipuri MP4 cu pierderi drept intermediari. Scenele intermediare sunt FFV1.

```bash
./media init --id audio-demo --audio output/proba_1.00.mp3 --text samples/test_ro.txt --image "work/media/demo/Copertă ș apostrof' test.png" --tts-report output/proba_1.00.report.json
./media render audio-demo --profiles landscape,portrait --force
./media verify output/media/audio-demo/landscape/video.mp4
```

Comenzile init sunt istorice ale acestei probe și refuză repetarea cu același ID. `--force` a fost folosit numai pentru noile exporturi media de probă, niciodată pentru a înlocui MP3-urile existente.

### F2/F3 — cronologie importată, scene și compoziție

Materialul `scene-demo` are 52920 eșantioane la 22050 Hz (2,4 s), **tonuri sintetice, nu vorbire**, și patru cuvinte în textul de fixture. Timpii sunt cunoscuți prin construcție/import. SRT/ASS și randarea din acești timpi sunt testate; precizia unui aligner pe vorbire românească nu este. Statutul rămâne `imported_not_reviewed`. WhisperX/Wav2Vec2 nu au fost instalate, iar ținta de ±200 ms față de ancore umane nu a fost verificată.

```bash
./media align scene-demo --words work/media/demo/alignment.json --provenance 'Fixture cu tonuri sintetice; timpi cunoscuți prin construcție, fără validare de aliniere a vorbirii'
./media scenes scene-demo --plan work/media/demo/scenes.json
./media subtitles scene-demo --profiles landscape,portrait --mode classic --output-dir output/media/scene-demo/subtitles-classic
./media titles scene-demo --manual 'Ștefan citește. Măriuca ascultă.' --approve
./media render scene-demo --profiles landscape,portrait,custom --width 640 --height 360 --subtitles highlight --title 'Ștefan citește.' --force
./media render scene-demo --profiles custom --width 640 --height 360 --plan-only
./media titles audio-demo
./media thumbnail audio-demo --text 'Ștefan și Măriuca la Brașov' --image "work/media/demo/Copertă ș apostrof' test.png" --profiles landscape,portrait --output-dir output/media/audio-demo/thumbnails
./media thumbnail scene-demo --profiles landscape,portrait --output-dir output/media/scene-demo/graphic-thumbnails
./media thumbnail scene-demo --scene ascultare --variant top --format jpeg --profiles landscape,portrait --output-dir output/media/scene-demo/scene-thumbnails
```

Rezultate: [subtitrări clasice](output/media/scene-demo/subtitles-classic/landscape/subtitles.srt), ASS și alignment JSON alăturate; [thumbnail imagine+text](output/media/audio-demo/thumbnails/landscape-panel.png), [copertă grafică](output/media/scene-demo/graphic-thumbnails/portrait-panel.png), [thumbnail din scenă JPEG](output/media/scene-demo/scene-thumbnails/landscape-top.jpeg). JSON-urile aferente păstrează sursa și geometria textului. Planul cu două scene testează zoom/pan, crossfade și titlu cu apariție progresivă.

### F4 — fragmente, compilație, lot și reluare

```bash
./media split scene-demo --parts 2 --prefix demo-part --apply
./media titles demo-part-001 --manual 'Ștefan citește.' --approve
./media titles demo-part-002 --manual 'Măriuca ascultă.' --approve
./media merge --id demo-compilation --materials demo-part-001 demo-part-002
./media titles demo-compilation
./media batch work/media/demo/batch-final.json
./media batch work/media/demo/batch-final.json
```

Lotul a executat 6/6 cereri, apoi a refolosit 6/6 rezultate după verificarea amprentelor și hash-urilor. Dovezi: [batch-final-result.json](work/media/demo/batch-final-result.json) și [batch-final-resume.json](work/media/demo/batch-final-resume.json). Același renderer exportă copiii (classic/highlight) și compilația (scroll); thumbnail-uri distincte pentru fiecare. Nu există un renderer special de fragmente.

Reconstrucția PCM fără resampling/efecte a păstrat exact 52920 eșantioane; SHA-256 al fluxurilor s32le înainte/după: `f3116ec3ba31b54c2180ca57e506f6f3b7189702ebf242fa626b472faf0c9ea1`. Dovadă: [pcm-roundtrip.json](work/media/demo/pcm-roundtrip.json). Nu se promite identitate binară pentru MP4/AAC.

### Exporturile principale verificate

| Material/profil | Dimensiuni | Durată video | Audio decodat | Diferență A/V |
|---|---:|---:|---:|---:|
| [audio-demo/landscape](output/media/audio-demo/landscape/video.mp4) | 1920×1080 | 18.533333 s | 18.575964 s | 42.630 ms |
| [audio-demo/portrait](output/media/audio-demo/portrait/video.mp4) | 1080×1920 | 18.533333 s | 18.575964 s | 42.630 ms |
| [demo-compilation/custom](output/media/demo-compilation/custom/video.mp4) | 640×360 | 2.400000 s | 2.414875 s | 14.875 ms |
| [demo-part-001/custom](output/media/demo-part-001/custom/video.mp4) | 640×360 | 1.200000 s | 1.207438 s | 7.438 ms |
| [demo-part-002/custom](output/media/demo-part-002/custom/video.mp4) | 640×360 | 1.200000 s | 1.207438 s | 7.438 ms |
| [scene-demo/custom](output/media/scene-demo/custom/video.mp4) | 640×360 | 2.400000 s | 2.414875 s | 14.875 ms |
| [scene-demo/landscape](output/media/scene-demo/landscape/video.mp4) | 1920×1080 | 2.400000 s | 2.414875 s | 14.875 ms |
| [scene-demo/portrait](output/media/scene-demo/portrait/video.mp4) | 1080×1920 | 2.400000 s | 2.414875 s | 14.875 ms |

Toate aceste exporturi au H.264/AAC/yuv420p, 30 fps, decodare A/V completă și `technical_status: passed`. Diferențele sunt sub pragul de 100 ms; sursa audio este acoperită până la ultimul eșantion conform verificării de export și rotunjirii ascendente la cadru. Acest control tehnic nu demonstrează prin ascultare fiecare cuvânt.

Au fost văzute efectiv doar cadre extrase la început, tranziție, final și în profil portrait: [contact sheet](work/media/demo/frames/contact-sheet.png), [portrait](work/media/demo/frames/portrait.png), [final Piper](work/media/demo/frames/piper-end.png). Diacriticele sunt vizibile, contain păstrează imaginea, subtitrările stau jos, iar cadrele finale inspectate nu sunt negre. Titlul mare este un stil demonstrativ, fără aprobare editorială. [Raport vizual parțial](work/media/demo/visual-review.json). Nu s-a vizionat integral și nu s-a ascultat audio-ul; rapoartele de film păstrează `visual_review_status: not_reviewed`, `listening_status: not_listened`, `editorial_review_status: not_reviewed`.

### Protecție și ce rămâne nefinalizat

Hash-urile, dimensiunile și mtime-urile celor **365 fișiere protejate** au rămas identice: inputuri, MP3-uri/rapoarte vechi, cod audio, configurație, dicționar, modele și cache. Inclusiv mulțimea fișierelor din `work/cache/` este neschimbată. Dovezi: [protected-before.json](work/media/audit/protected-before.json), [protected-after.json](work/media/audit/protected-after.json). Nu s-au modificat executabilele, nu s-a folosit sudo/pip pentru extensie și nu s-a făcut commit/push sau curățare. `.gitignore` a primit numai excluderi pentru noile `materials/` și `assets/` private.

F0 și subseturile CPU F1/F3/F4 au probe reale; întregul plan nu este declarat terminat. Rămân: aliniere automată românească și precizie auditivă, backend-uri LLM/AI neinstalate, split text înainte de TTS/semantică, limite maxime stricte, mix extern cu resampling și politică de normalizare, avatar/logo, stil ASS complet configurabil, continuitate de fază a mișcării după split, batch de import/derivare, reluare import parțial și instalare media curată reproductibilă cu hash-uri. Aceste lipsuri nu sunt o eroare GPU pentru funcțiile CPU.

Cadrele unei scene video pot necesita reencodare finală după modificări; nu există promisiune de cache pe fiecare cadru. Exportul, raportul și manifestul se scriu separat, fără tranzacție atomică comună. Intrările media nu au fost validate împotriva unui disc efectiv plin; nu s-a umplut discul. Nu se afirmă naturalețe a vocii sau relevanță editorială garantată.

Verificări finale suplimentare, numai în citire pe audio-ul utilizatorului:

```bash
PYTHONDONTWRITEBYTECODE=1 ./tts doctor
PYTHONDONTWRITEBYTECODE=1 ./tts verify output/text.mp3
```

Ambele au trecut; rapoartele sunt [doctor-audio-current.json](work/media/audit/doctor-audio-current.json) și [verify-audio-current.json](work/media/audit/verify-audio-current.json). Nu s-a executat `tts render` pe originalele utilizatorului. Centralizarea finală include versiunea, SHA-256 al codului media și run-id-urile exporturilor în [work/media/validation-summary.json](work/media/validation-summary.json). Cheile de export și checkpoint includ și implementarea, versiunea Pillow și hash-ul executabilului FFmpeg; actualizarea lor invalidează reutilizarea. Aceasta poate necesita `--force` pentru un export media existent sau un director nou de thumbnail, fără atingerea vocii.

## 7. Aliniere românească și materiale reale — 16 octombrie 2026 UTC

Această etapă continuă media 0.1.0/schema material 1, cu codul identificat prin SHA-256 în `work/media/real-alignment-audit/`. Nu înlocuiește rezultatele istorice din secțiunile 1–6. Testele noi folosesc audio-ul real existent, fără apel Piper și fără sinteză nouă. Datele sunt UTC, separat de fusul Europe/Bucharest.

### 7.1 Corespondența surselor și protecția originalelor

`./media init --id real-ro-20261016 --audio output/text.mp3 --text input/text.txt --tts-report output/text.report.json` a verificat raportul și manifestul `work/runs/20261016T090507-5f8a96d4/manifest.json`. Textul afișat și cel efectiv trimis motorului au aceeași secvență de tokenuri în această versiune; dicționarul nu are înlocuiri. Decodarea MP3 a produs **15.188.520 eșantioane la 22050 Hz**, exact `planned_frames`, adică **688.821768707483 s PCM**. Durata containerului MP3 rămâne 688.875102 s; nu se confundă cu numărul decodat de eșantioane.

- Text original SHA-256: `466c0f8e31d660f346750ab9b95fecbe45dc29763a479a9e2e7561f8f271aa73`.
- MP3 original SHA-256: `31f911a45a0d70b5d1507b77a0ffe842eb667952c023435dcc00f67342c27c22`.
- Snapshot inițial: `work/media/real-alignment-audit/protected-before.json`, **441 fișiere** deja existente: input, output, modele audio, cache audio, cod audio și configurații relevante. Noile rezultate media au ID-uri separate.

Nu s-au modificat `./tts`, `src/rec_tts/`, `.venv`, `rec.json`, dicționarul, inputul sau MP3-urile existente. Nu s-au instalat dependențe în mediul Piper, CUDA, WhisperX complet, diarizare sau generatoare de imagini/clipuri.

### 7.2 Dependențe și model efectiv instalate

Instalare explicită în `.venv-align`: **torch 2.8.0+cpu**, **transformers 4.56.2**, **soundfile 0.13.1**, **num2words 0.5.14** și tranzitivele din `requirements-align.lock`. S-a verificat compatibilitatea wheel-ului CPython 3.13 CPU; `pip check` a trecut. Metadata licențelor: `dependency-metadata.json`; copiile notificărilor sunt în `licenses/alignment/`. `bash scripts/bootstrap-align.sh` a fost executat ulterior cu toate versiunile deja satisfăcute; nu a reinstalat pachetele. Lock-ul este cu versiuni exacte, fără hash-uri de distribuții; instalarea într-un mediu curat secundar rămâne **neverificată**.

Model: **gigant/romanian-wav2vec2**, revizia **79cf603aac59501d02bfeb37f615efc3ac4ce1b3**, safetensors **1.261.955.032 octeți**, SHA-256 `a42ddf6318dfb62d1375887f03cf8d725d7c91e257f8b86487384d4e8d98a800`. Fișa declară Apache-2.0. Descărcare explicită prin `python3 scripts/fetch-alignment-model.py`; a doua executare a păstrat toate fișierele valide fără rețea. Configurațiile/vocabularul/fișa și proveniența sunt în `models/alignment/romanian-wav2vec2/model.lock.json`. Nu s-a descărcat modelul 5-gram sau copia pickle a greutăților. Hash-urile sunt calculate local, fără pretenția unei semnături independente a furnizorului.

Hardware verificat direct: 4 CPU, aproximativ 3,8 GiB RAM și 8 GiB swap; GPU/VRAM nu sunt expuse. Mediul izolat ocupă aproximativ 1,1 GiB, modelul 1,2 GiB. Lipsa GPU nu a blocat alinierea sau video-ul. Nu s-a măsurat un vârf precis de RAM și nu se extrapolează performanța la alte calculatoare.

### 7.3 Aliniere reală, fără transcriere substituită

Comenzi efectiv executate:

```bash
./media --report work/media/real-alignment-audit/short-alignment.json align real-ro-20261016 --backend ctc-ro --max-windows 1
./media --report work/media/real-alignment-audit/full-alignment.json align real-ro-20261016 --backend ctc-ro
```

Prima probă a procesat prima fereastră reală TTS: **53 unități textuale**, 4 scoruri sub 0,35, zero unități fără cale CTC; **7.209788496 s** măsurate în worker. Raportul este `partial: true`; nu a atașat o aliniere incompletă materialului.

Procesarea integrală: **30/30 ferestre, 1.824 unități textuale, 170 scoruri reduse, 17 normalizări contextuale**, zero unități fără cale CTC. Rezultatul a fost calculat în **220.740695981 s** conform cronometrului workerului (după importuri și validarea modelului), la `2026-10-16T10:47:57.198414+00:00`. `model_load_seconds: 0.067978588` reprezintă încărcarea lazy safetensors raportată de adaptor, nu importurile și nici citirea efectivă a tuturor paginilor în prima inferență. Prima atașare a eșuat din cauza importului inutil Pillow; după separarea importurilor grafice, aceeași comandă a atașat rezultatul valid din cache, fără recalcularea celor 30 ferestre. De aceea raportul CLI păstrat are `cache_hit: true`, iar `elapsed_seconds` rămâne timpul calculului inițial, nu durata relansării.

Cache: `work/media/alignment/6c00af4bc1951e99f21a823d7b5d48cc361c052ccd1deb79a76c2233d46846da/`. Rezultatul și checkpointurile au hash-uri de integritate; modelul și sursele audio se verifică din nou la reutilizare. Cheia include textul rostit și afișat, audio/cronologie, ferestre, model, setări, dependențe și codul adaptorului. Testele verifică invalidarea pentru audio/text/model/configurație, nu o împărțire de durată după caractere.

Timpii provin din emisiile acustice ale modelului și backtracking Viterbi CTC; ferestrele sunt ancorate în numărul real de eșantioane și pauzele manifestului TTS. Numerele sunt expandate doar în `alignment_target`, păstrând tokenul original pentru afișare. O unitate numerică poate reprezenta mai multe cuvinte rostite și are un interval comun; nu se pretind limite exportate pentru fiecare cuvânt din expansiune. Siglele și numerele rămân marcate. `‘89` este normalizat numeric ca 89, fără interpretarea contextuală 1989 și fără reguli permanente noi. Alte mapări editoriale afișat/rostit cer import explicit `--words/display_group`; caracterele alfabetice nesuportate produc eroare în CLI.

**Limita metodei:** o cale CTC completă forțează textul cunoscut și nu dovedește sincronizarea fiecărui cuvânt. Scorul este un indicator necalibrat, nu probabilitate de corectitudine. `alignment_status: aligned_with_warnings`, `manual_anchor_accuracy: not_measured`, `listening_status: not_listened`. Precizia ±200 ms și pronunția/naturalețea nu au fost validate auditiv. Exporturile reale folosesc classic; highlight/scroll au probe tehnice sintetice, fără validare auditivă pe acest material.

### 7.4 Împărțire, compilație și frontiera acustică

Prima limită propusă era sfârșitul tokenului CTC la 348.191927438 s. Analiza PCM a arătat o coadă acustică imediat după acel moment; lotul a fost întrerupt controlat, iar limita a fost mutată **în interiorul pauzei**, la **7.682.042 eșantioane / 348.391927438 s**. Pauza dintre intervalele CTC este 400 ms; RMS pe 40 ms în jurul noii limite este **−76.74672834 dBFS**. Dovadă: `safe-boundary.json`. Această măsurătoare tehnică nu este audiție și nu validează toate limitele CTC.

Materialele finale sunt `real-ro-fragment-001`, `real-ro-fragment-002`, `real-ro-reuniune-20261016` și proba `real-ro-proba-sigura-001`, pe lângă integralul `real-ro-20261016`. Fragmentul 1 are 348.391927438 s PCM, fragmentul 2 restul sursei. Indicii/timpii cuvintelor incerte se recalculează local; scenele și subtitrările sunt rebazate. Titlurile/coperțile provin din textul fiecărui material, fără copiere automată a titlului părintelui și fără aprobare editorială implicită. Compilația folosește explicit ordinea 001, 002.

`pcm-roundtrip-safe.json`: split→merge păstrează exact **15.188.520 eșantioane** și **1.824 unități textuale**; SHA-256 PCM înainte/după **07a0622f9e2d4c3853948b1f0cb32678ab47a717c591a8eb2a8d3e4ec8288645**. Nicio resinteză, normalizare nouă, suprapunere de voci sau resampling. MP4/AAC nu sunt declarate identice binar cu MP3/PCM.

Primele materiale `real-ro-parte-*`, `real-ro-compilatie-20261016`, `real-ro-proba-001` și loturile `batch.json`/`batch-safe.json` sunt încercări intermediare păstrate, nu rezultatele finale. Întreruperea externă prin unealta agentului a returnat 130; poate lăsa manifestul intermediar `running` dacă procesul nu mai poate scrie starea terminală. Acest lucru nu dovedește că procesul mai rulează. Nu s-au șters fișierele `.part` sau exporturile anterioare valide. Primele două exporturi integrale sunt arhivate în `before-static-input-optimization/` înaintea exporturilor finale.

### 7.5 Exporturi, eficiență și verificări de revizuire

Imaginile fixe sunt decodate la 1 fps și cadrele decodate sunt duplicate **înaintea** randării ASS la **30 fps**; timpii subtitrării nu sunt reduși la secunde întregi. Pentru probele reale s-a ales explicit `composition.title_fade_seconds: 0`; titlul fix este compus o singură dată în imagine, evitând o suprapunere HD identică pe fiecare cadru. Animația titlului configurabilă rămâne pe calea normală. Testul de cadre la 0,2/0,8 s verifică schimbarea highlight în aceeași secundă. Nu se încarcă toate cadrele în RAM și nu se scrie un FFV1 integral pentru o singură imagine fixă.

Lotul final este `work/media/real-alignment-audit/batch-final.json` (11 joburi: exporturile deja valide de metadate sunt păstrate). Comanda finală, rapoartele per profil și inventarul măsurat sunt consemnate mai jos după terminarea lotului. Sunt cerute numai landscape/portrait și proba scurtă landscape; nu un produs cartezian de variante necerute.

Reperele locale: `output/media/real-ro-20261016/review/repere.md`, `checkpoints.json`, WAV-uri extrase și cadre început/mijloc/final. Ultima unitate CTC se termină la **688.661360544 s**, iar sursa PCM la **688.821768707 s**; textul ultimului cue este contabilizat. Acoperirea audio/ultimul cue și cadrele fără negru sunt probe tehnice; ultimul cuvânt nu a fost confirmat prin ascultare. Se păstrează separat visual_review_status, listening_status și editorial_review_status.

### 7.6 Teste noi și eșecuri remediate

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_text.py tests/test_pipeline.py -q --junitxml=work/media/real-alignment-audit/audio-unit-regression.xml
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/media -q --junitxml=work/media/real-alignment-audit/media-tests-verified.xml
```

**38/38 regresii audio fără motor real și 27/27 teste media trecute în această etapă**, în 0,39 s și, respectiv, 61,88 s. Totalul acestor suite noi este **65**, separat de cele 44 teste audio istorice și cele 16 media inițiale. Cele șase integrări audio care ar sintetiza din nou nu au fost rerulate în această etapă. Testele noi acoperă CTC/repetiții/cadre neuniforme, normalizare fără reinterpretarea secolului, invalidarea cheii, model corupt, refuzul mapării implicite/alfabetului nesuportat, diagnostice locale, grupuri afișate repetate la merge și preferința pentru interiorul pauzei unei propoziții.

Eșecuri păstrate în audit, urmate de rerulare:

- Prima regresie media: 15 passed / 1 failed, fiindcă testul offline folosea lock-ul global al proiectului ocupat de aliniere. Subprocessul testului este acum izolat în fixture; rerulările au trecut.
- Prima publicare a alinierii: Pillow lipsea din mediul izolat, deși validarea timpilor nu cere randare. Importurile grafice au fost mutate în funcțiile grafice; rezultatul CTC deja complet a fost recuperat din cache.
- Un test nou al validării CLI a folosit implicit o configurație inexistentă în fixture: 26 passed / 1 failed. Testul furnizează acum explicit configurația; suita finală are 27 passed.
- Exit 1 al ultimei predări anterioare: cele trei `git diff --no-index --check` returnau 1 pentru documente diferite, fără stdout/stderr și fără diagnostic de whitespace. Reprodus în `previous-exit-investigation.json`; `git diff --check` și verificarea explicită a diagnosticelor nu au raportat spațiere defectă. Nu era o eroare de export audio.

Probele reale suplimentare nu sunt numărate ca pytest-uri:

- `offline-real-current-result.json`: aliniere CTC reală cu cache gol și render subtitrat 640×360 într-o copie izolată a proiectului, prin `unshare -Urn`. Namespace fără rute; socketurile sunt blocate suplimentar de sandbox (`EPERM`). Nicio descărcare în procesare. Nu se afirmă că limita de rețea provine exclusiv din namespace.
- `recovery-real-result.json`: întrerupere controlată după prima dintre două ferestre reale; reluare cu un cache hit și hash/mtime neschimbate pentru prima fereastră. Coruperea rezultatului și a unui checkpoint în copia de test a dus la recalcularea numai a checkpointului invalid, cu celălalt refolosit. Originalele nu au fost folosite pentru simularea corupției.

### 7.7 Git, documente și limite rămase

Git root este `/home/daniel/projects`. Regula părintelui `/*` ascundea directorul rec, inclusiv README și sursele. Cu permisiune s-a adăugat numai `!/rec/` în `.gitignore` al părintelui. `.gitignore` local păstrează mediile/modelele/cache-ul/datele personale/audio-video generate ignorate; dicționarul personal este ignorat, exemplul sintetic rămâne disponibil. Sursele, testele și documentele apar acum ca ne urmărite; nu s-a făcut git add/commit/push. `git diff` normal nu afișează conținutul fișierelor ne urmărite; verificarea finală include și verificări explicite de conținut/Markdown.

Actualizate README, acest istoric, planul canonic (cerințe A1–A20, decizii și matrice pe funcții), THIRD_PARTY_NOTICES și AGENTS. Un singur exemplar canonic al planului este păstrat. Restanțe: ancore auditive ±200 ms, vizionare integrală/editorial, mapări editoriale automate complexe, aliniere lungă fără ancore furnizate, split de text înainte de TTS/capitole/semantică/maxim strict, mix extern complet, pauze/intro/normalizare la merge, continuitatea animației la split, avatar/logo, stil ASS complet, backend-uri AI opționale și instalare curată secundară. Niciun CLI sau test sintetic nu le transformă în funcții finalizate.

### 7.8 Rezultatul final al lotului și verificarea de predare

`batch-final-result.json`: **11/11 joburi passed**. Rerularea exactă a lotului, în `batch-final-resume.json`, a refolosit **11/11 joburi**, verificând amprentele și hash-urile artefactelor. `align-reuse-proof.json`: încă o aliniere CLI a găsit rezultatul valid în cache, a durat 4,797 s la nivelul procesului apelant și a păstrat **identic manifestul materialului**, inclusiv exporturile.

```bash
./media --report work/media/real-alignment-audit/batch-final-result.json batch work/media/real-alignment-audit/batch-final.json
./media --report work/media/real-alignment-audit/batch-final-resume.json batch work/media/real-alignment-audit/batch-final.json
./media --report work/media/real-alignment-audit/doctor-final.json doctor
./media --report work/media/real-alignment-audit/verify-landscape.json verify output/media/real-ro-20261016/landscape/video.mp4
./media --report work/media/real-alignment-audit/verify-portrait.json verify output/media/real-ro-20261016/portrait/video.mp4
./media split real-ro-20261016 --parts 2 --prefix exemple-relecture
./media merge --id compilatie-plan-verificat --materials real-ro-fragment-001 real-ro-fragment-002 --plan-only
```

Ultimele două comenzi au fost executate numai pentru planificare; nu creează încă alte fragmente/compilații. Aplicarea efectivă a materialelor finale este consemnată în `split-safe-plan.json`, `products-safe.json` și manifestele lor, prin aceleași funcții de derivare folosite de CLI. Nu se pretinde că `split` acceptă un `--plan-only` inexistent: planificarea este implicită fără `--apply`.

| Material în output/media/ | Profile | Durată video (s) | Durată audio decodat (s) | Diferență A/V (ms) |
|---|---|---:|---:|---:|
| real-ro-20261016 | landscape, portrait | 688.833333 | 688.843175 | 9.841 |
| real-ro-fragment-001 | landscape, portrait | 348.400000 | 348.392200 | 7.800 |
| real-ro-fragment-002 | landscape, portrait | 340.433333 | 340.450975 | 17.642 |
| real-ro-reuniune-20261016 | landscape, portrait | 688.833333 | 688.843175 | 9.841 |
| real-ro-proba-sigura-001 | landscape | 5.966667 | 5.990748 | 24.082 |

Toate cele **9 MP4-uri** au H.264/yuv420p, AAC mono/22050 Hz, 30 fps, dimensiunile exacte ale profilului și decodare completă reușită. Diferența maximă A/V este **24,082 ms**, sub pragul tehnic de 100 ms. Acest rezultat nu este precizia sincronizării cuvintelor. Verificarea independentă CLI a ambelor profile integrale a trecut. Timpii cumulativi de randare până la ultimul profil, din rapoarte: integral 229,6 s; fragmentul 1 99,9 s; fragmentul 2 98,8 s; compilație 204,7 s; proba 1,81 s. Sunt măsurători ale acestei execuții, cu unele teste concurente, nu benchmark controlat.

`acceptance.json` verifică **9 SRT-uri cu acoperire textuală exactă**, ASS/alinierea alăturate, **9 thumbnail-uri** cu dimensiuni/casete/font minim valide și titluri selectate din conținutul propriu. Selecțiile independente pot coincide când același pasaj este prezent în mai multe materiale; nu s-a copiat starea titlului părintelui în copii. Relevanța editorială rămâne nerevizuită.

Cadrele reale început/mijloc/final în ambele profile, ultimele cadre și contactul thumbnail-urilor derivate au fost **inspectate vizual punctual**. S-au observat diacriticele, rearanjarea titlului/subtitrării pentru portrait, text în cadru și lipsa unui final negru accidental. Hash-urile cadrelor și videoclipurilor sunt în `review/checkpoints.json` și `last-frame-check.json`. Nu s-a făcut vizionare integrală sau ascultare; nu s-au măsurat ancore auditive de ±200 ms și nu se aprobă pronunția/naturalețea.

`protected-after.json`: **441/441 fișiere originale cu hash identic**, inclusiv textul/MP3-urile/cache-ul audio. Setul fișierelor din `work/cache/` este neschimbat. `./tts doctor` și `./tts verify output/text.mp3` au fost executate doar pentru citire: MP3 original full_decode true, accepted true, −19,48 LUFS, −2,3 dBTP. Nu s-a rerulat conversia audio.

Validarea Markdown a verificat sintaxa a **33 exemple CLI din README** și existența a **69 legături locale**; nu a executat din nou comenzile de instalare/randare din exemple. Opțiunile normative propuse și explicit neimplementate din anexă nu sunt confundate cu interfața reală. Verificarea Git a inclus regula părintelui, sursele ne urmărite și ignorarea datelor private; fără staging/commit/push.

**Limită suplimentară de recuperare:** reluarea a fost verificată după checkpointuri de cuvinte și după eșecul atașării finale, nu în timpul construirii inițiale a WAV-ului de analiză. Temporare existente pot opri relansarea acelei faze; acest caz și corupția copiei intermediare de analiză nu au acceptare automată. Păstrează directorul pentru diagnostic și arhivează-l explicit prin redenumire înainte de o recalculare, fără ștergerea surselor/cache-ului Piper. Această restanță este distinctă de recuperarea checkpointurilor JSON deja testată.

Aplicarea CLI, nu numai planificarea, a fost verificată ulterior prin `./media split real-ro-20261016 --parts 2 --prefix real-ro-cli-fragment --apply` și `./media merge --id real-ro-cli-compilatie --materials real-ro-cli-fragment-001 real-ro-cli-fragment-002`. Ambele au returnat passed; rapoarte `split-cli-applied.json` și `merge-cli-applied.json`. Cele trei materiale de verificare nu au MP4-uri suplimentare; inventarul final rămâne de nouă videoclipuri.

## 8. Etapa workflow de producție — 2026-10-16 UTC

Run-id documentar: `production-20261016`, media 0.1.0 cu extensii aditive.
Snapshot inițial: `work/media/production-20261016/protected-before.json`.
Split text implementat; probele și statusurile finale sunt consemnate mai jos.

## 9. Recuperare sesiune și continuare producție — 2026-10-16 UTC

Versiune media 0.1.0, run documentar `production-20261016-recovery`.
Git la recuperare: ` M ../.gitignore`, `?? ./` (proiect neînregistrat în
repo-ul părinte); nu s-au făcut add/commit/push/reset/clean.

Procesele au fost inspectate și în afara sandboxului PID. Nu mai exista niciun
FFmpeg/Python/media al sesiunii precedente; WSL boot: 19:53:30 UTC. Ultima sesiune
salvată se oprește la 19:41:07 UTC cu progres, nu cu raport final de eroare.
Checkpointul `e7c89d4f63e7481c89a2d0207c194984/run.json` era `running`,
`completed=[]`; al treilea MKV avea 4.134 cadre și `File ended prematurely`.
Intermediarii au fost păstrați. Nu exista MP4 de producție publicat de adoptat.

Cauza exactă a mesajului terminalului `process exited with code 1` rămâne
**nedeterminată**: nu există diagnostic terminal complet în logurile disponibile.
Nu s-au găsit OOM/segfault în jurnalul kernel al bootului precedent. Un exit 1
auxiliar anterior, la 19:32:46 UTC, este FileNotFoundError pentru
`/sys/fs/cgroup/memory.max`; nu este demonstrat drept cauza închiderii.
Bootul nou dovedește că joburile vechi nu au supraviețuit până la recuperare,
nu momentul sau semnalul exact al opririi lor.

Dovezi anterioare confirmate fără rerulare costisitoare:

- `recovery-real-result.json`: passed, întrerupere PCM inițială, resume, reutilizare
  și refacere după corupție, SHA analiză `28244aa15418bbbf3e849c415d0825aed457d36517550a4904808f54282da801`.
- `ctc-review.json`: exact 170 unități cu scor redus, alignment_key
  `3dc56edb6af259158feafc35e952a49005d79340c9c9a8dd4d94c61ea66bbec5`.
- `regression.log` + XML: 71 passed, 64,43 s; `production-tests.xml`: 6 passed.
- Cele 553 fișiere din snapshotul protejat au hash-uri identice la reluare;
  split→merge text păstrează exact octeții `input/text.txt`.

Proba selectivă neterminată a fost continuată în `isolated-align/`, cu codul
izolat existent. Receipt-ul WAV creat la **19:41:16 UTC** a fost reutilizat,
SHA `4143b1f56c993228c1793390f32d5655ccf9f9bc1d7ecb867c3b48570d2d3fe9`.
`selective-alignment-result.json`, 20:11:31 UTC: două ferestre/17 unități,
`--segments 1` recalculează numai fereastra 1, fereastra 0 păstrează hash/mtime,
apoi cache_hit=true. Offline `unshare -Urn`, fără resinteză/model nou.

Prima relansare a workflow-ului a întâlnit semnături schimbate după pornirea
vechii sesiuni: thumbnail-ul existent a fost protejat și comanda a returnat 1.
Dovezi: `workflow-recovered.json`, log nominalizat în state. Scenele/titlul
identice au fost reaplicate, fără schimbarea surselor; thumbnail-ul nu a fost
suprascris. Continuarea `workflow-continued.json` selectează explicit etapele
de la render încolo. Noul run integral: `8c5122b32d634bd5a74f677853b70c24`.

Corecție orchestrator: selecția `--only` incompletă raportează workflow_status/
phase=partial și incomplete, cu technical_status pentru selecție. Retry eșuat
păstrează previous_success fără a-l considera succes curent. Testul nou acoperă
ambele situații. Testul backend-ului opțional verifică blocked fără model/binar,
plan cu identități sintetice și refuz la hash schimbat, fără execuție/descărcare.

Comandă nouă efectiv rulată:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/media tests/test_text.py tests/test_pipeline.py -q -p no:cacheprovider --junitxml=work/media/production-20261016/regression-recovered.xml
```

Rezultat: **73 passed în 58,66 s**, fără failures/errors/skips. Testele scriu
fixture-uri în directoare temporare, nu audio în fluxul protejat. Vechiul
`regression.log`/XML sunt păstrate. Incidentul complet:
`work/media/production-20261016/incident-recovery.json`.

În această sesiune, continuarea inițială a primit separat **143/SIGTERM**, fără
receipt terminal de eroare în pipeline. Landscape-ul publicat rămâne passed;
MP4-ul portrait temporar nu are moov și este păstrat ca intermediar invalid.
Nu este confundat cu exit 1 al terminalului precedent. Expeditorul semnalului
nu este înregistrat. Lansarea simplă nohup nu a produs receipt de pornire;
lansarea detașată `setsid --fork` în afara sandboxului temporar a produs
runner-state cu PID 6058 la 20:41:14 UTC. `production-runner.py` continuă prin
CLI-urile publice și păstrează checkpointul landscape; nu pornește în paralel
un al doilea render. Intermediarii fără receipt nu sunt adoptați drept profil
complet. Etapele de metadate validate sunt păstrate separat de această reluare.

Restanță finalizată: `split --max-seconds`. Plafon floor(secunde × sample_rate),
planificare din limite aliniate, preferință pentru pauze între propoziții și
conflict explicit înaintea aplicării. În combinație cu limite/N/țintă validează
cererea fără a o modifica tacit. Revalidare la apply, inclusiv plan editat.
Testul acoperă acoperirea integrală, durate, text, aplicarea fixture-ului și
conflictele/NaN/inf/valori sub un eșantion. Plan real numai citire:
`strict-max-real-plan.json`, patru intervale de 175,754694 / 178,017143 /
177,513878 / 157,536054 s, plafon 3.969.000 eșantioane. Nu reprezintă verificare
auditivă a limitelor CTC și nu garantează durata textului înainte de TTS.

Regresie după această extensie, aceeași selecție de teste și opțiuni, destinație
`work/media/production-20261016/regression-final.xml`: **74 passed în 44,53 s**.
Rularea de 73 de teste rămâne istoric valid înaintea adăugării plafonului.

### Corecție de tranziții demonstrată și exporturi păstrate

Inspecția paddingului a identificat o eroare reală separată de exiturile
terminalului: după zoompan/trim/setpts, tpad primea metadate FPS insuficiente și
cadrele clonate aveau timestampuri duplicate. Proba de 90 + 6 cadre producea
numai **91**, deși verificarea globală A/V putea trece prin rotunjire/duplicare
finală. Dovezi păstrate: `transition-padding-probe.mkv` și
`transition-padding-corrected-probe.mkv` (**96** cadre după fixarea FPS).
Testul nou verifică și culorile amestecate în trei cadre ale tranziției,
nu doar durata finală. Nu mai deducem o tranziție corectă din decodare A/V.

Workerul propriu PID 6058 a fost oprit explicit înaintea corecției; lockurile
runner/media erau libere înaintea relansării. Exporturile și temporarele vechi
rămân intacte. `render --output-root` permite destinația nouă
`output/media/scenes-v2/`, păstrând materialele și alinierea. Nu s-a folosit force.
Workerul corectat PID 7833 a pornit la **20:46:07 UTC**. Planul nou este
`acceptance-scenes-v2-workflow.json`, cu metadate/derivare înaintea celor patru
renderuri, folosind aceleași funcții publice; scena/titlul/thumbnail-ul integral
confirmate în sesiunea precedentă nu sunt regenerate în acest plan.

Regresia după corecția video și noua destinație de export:
`regression-scenes-v2.xml` / `regression-scenes-v2.log`: **75 passed în 53,51 s**.
Testul verifică și destinația cu spații/apostrof/diacritice. Nu s-a schimbat
niciun modul TTS, model sau input protejat.


## Recovery scene complete și publicare întreruptă — 2026-10-16 UTC

Versiune media 0.1.0, run recuperat `9f8ed5ce64054935b51da76f4d686db7`.
Dovezi private: `work/media/production-20261016/recovery-scenes/`.
Procese gazdă verificate separat de sandbox; niciun job vechi activ.
Boot gazdă: 20:51:56 UTC. Ambele lock-uri s-au putut dobândi nonblocking.
Starea running din sesiunea veche nu era dovadă de proces viu.

- `scene-validation.json`: FFV1/yuv420p 1920×1080, 30 fps; scenele 00000/00001/00002
  au 6.950/6.765/6.962 cadre, cu paddingurile necesare. Probe complete ffprobe și
  decodare FFmpeg exit 0 fără stderr; toate marcate reutilizabile. Scena 00002
  crescuse la ~234 MiB înainte de incident, față de observația intermediară ~55 MiB.
- `incomplete-part.stderr`: ffprobe exit 1, moov atom not found. Fișierul vechi de
  48 bytes conține ftyp/free/mdat fără payload; nu este output valid. Păstrat.
- `previous-session-errors.json` și `previous-kernel.log`: niciun returncode final
  FFmpeg/Python/batch legat demonstrabil de închiderea terminalului. Ultima sesiune
  se oprește la 20:50:49Z cu o comandă auxiliară de inspectare manifeste în așteptare.
  Cauza exactă exit 1 istoric: **nedeterminată**; OOM/timeout/semnal nu sunt dovedite.
- Probele noi limitate artificial la 1.800 MiB adresă virtuală au eșuat cu
  returncode FFmpeg 244 (alocare) și 187 (inițializare encoder); stderr și comenzi
  persistente în run/landscape. Acestea nu demonstrează cauza incidentului istoric.
  Proba reală de 30 cadre cu fire explicite per input, fără această limită,
  `assembly-per-input-smoke-*.command.json`, a trecut cu FFmpeg returncode 0.
- Migrarea explicită a verificat asset-urile, pipeline-ul CFR și masterul PCM
  identic decodat cu sursa. Prima încercare de reluare CLI a returnat 1 cu diagnostic
  `Intermediar fără receipt compatibil`, fiindcă migrarea nu inclusese compoziția
  moștenită (`title_fade_seconds=0`); receipts au fost corectate. Nicio scenă
  rerandată și niciun output valid suprascris.
- Regresie nouă: `test_resume_complete_scenes_after_interrupted_atomic_publication`.
  Întrerupere simulată după scene complete, .part de 48 bytes, relansare explicită;
  scene hash/mtime identice, rerandare interzisă prin instrumentarea testului,
  part incomplet păstrat, publicare atomică verificată și MP4 decodat complet.
  Modificarea configurației incompatibile este refuzată.
- `regression-final.xml`: **38 passed** media. Copie izolată în /tmp pentru
  regresia completă fără integrare: `all-regression.xml`, **75 passed, 1 skipped,
  6 deselected**; skip-ul și probele de integrare neexecutate rămân explicite.

Continuarea efectivă rulează prin `recovery-scenes/continue-production.py`, cu
lock unic, rapoarte/exit receipts/loguri separate și finalizare/verificare landscape
înaintea celorlalte exporturi. Acceptanța reală va fi consemnată după încheiere.
Stări separate: technical în curs, visual not_reviewed, listening not_listened,
editorial not_reviewed; aliniere cu 170 scoruri reduse, fără aprobare automată.


Actualizare regresii recovery, 21:12 UTC: proba cu trei scene și două procese reale,
`test_recovery_after_process_exit_with_three_valid_scenes`, a trecut
(`hard-exit-recovery-passed.xml`). Primul proces execută `os._exit(1)` la
finalizare, ocolind tratarea excepțiilor și lăsând running + part 48 bytes;
al doilea finalizează cu scene hash/mtime identice. Prima încercare a testului
se oprise prematur fiindcă subprocessul de test nu moștenea calea Pillow Debian;
mediul fixture-ului a fost corectat, fără instalare. Eșecul de harness este păstrat
în `hard-exit-recovery.xml`, separat de rezultatul trecut.
`recovery-tests.xml`: două probe trecute, inclusiv diagnostic FFmpeg eșuat cu
stderr/comandă/cwd/returncode persistente. Testul de normalizare omis în prima
copie izolată a fost executat separat cu mediul existent, fără instalare:
`alignment-normalization-regression.xml`, 1 passed.

Landscape recuperat: `output/media/scenes-v2/prod-ro-20261016-001/landscape/video.mp4`,
FFmpeg returncode 0; 688,833333 s video, 688,843175 s audio decodat,
9,841270 ms A/V, decodare completă. Maxim RSS observat al FFmpeg: 2.993.428 KiB;
aceasta este proba curentă, fără a dovedi cauza incidentului istoric.
`landscape-frame-checks.json` și contact sheet inspectat: primul și ultimul cadru
nu sunt negre, cele trei scene/subtitrări vizibile; ambele crossfade-uri au amestec
gradual măsurat (alpha aproximativ 0 / 0,14 / 0,48 / 0,82 / 1 și
0 / 0,17 / 0,51 / 0,86 / 1). Vizual: partial_selected_frames_passed;
listening: not_listened; editorial: not_reviewed.


Regresia consolidată finală, 21:12 UTC: `all-regression-final.xml`, **78 passed,
6 deselected**, fără skip; cele șase probe de integrare audio cu sinteză nu au
fost relansate pe proiect. Copia izolată a folosit numai mediile existente,
fără instalări și fără scriere de audio în proiect.

`audio-preservation.json` compară streaming PCM din MP4 cu masterul verificat:
landscape păstrează toate cele 15.188.520 eșantioane ale sursei; AAC decodat are
15.188.992 eșantioane inclusiv padding. Corelație 0,999968419, SNR ~41,95 dB;
nu este audiție și nu aprobă pronunția/precizia CTC. Prima probă a helperului DSP
a folosit din greșeală `video.report.mp4`, cale inexistentă; eroare de harness
păstrată în `audio-preservation-harness-error.log`, apoi corectată. Nu era audio
trunchiat în exportul valid.

`seeded-runs.json` documentează adoptări explicite de MKV între materiale înainte
de executarea profilului destinație. Contractul compară hash asset, tip, dimensiuni,
configurație efectivă, fit/focală/mișcare/intensitate, număr de cadre, padding și
source_start. Diferențele numai în metadate editoriale nu cer calcul de pixeli.
Se copiază octeții validați, cu hash identic, fără suprascriere; rendererul revalidează
receipt-ul noii scene și o decodează integral. Paddingul diferit nu este acceptat
ca intermediar identic. Aceasta este o migrare explicită a producției, nu cache
cross-material implicit în CLI.


## Reluarea stării existente — 2026-10-17 UTC

Media 0.1.0, schema 1; audit privat în
`work/media/production-20261016/recovery-scenes/`. La 05:29 UTC au fost
verificate separat procesele gazdei și namespace-ul sandboxului: niciun worker
FFmpeg/Python precedent activ. Ambele lock-uri s-au putut dobândi nonblocking;
fișierele de lock au fost păstrate. Cinci MP4-uri erau deja publicate și au fost
reverificate prin renderer, fără force și fără reencodare. Workerul unic a reluat
fragmentul 2 portrait, apoi compilația pe cele două profile.

`scene-validation-20261017.json` revalidează cele trei MKV originale ale run-ului
`9f8ed5ce64054935b51da76f4d686db7`: FFV1/yuv420p, 1920×1080, 30 fps,
231,666 / 225,500 / 232,066 s raportate de container; 6.950 / 6.765 / 6.962
cadre decodate integral, exit 0 și stderr gol. Duratele exacte din cadre sunt
231,666667 / 225,500000 / 232,066667 s. Hash-urile și mtime-urile originale sunt
identice; receipts corespund manifestului, configurației efective și paddingului.
Nicio scenă originală nu a fost regenerată.

Diagnostic separat în `incident-20261017.json`, `session-20261017-diagnostic.json`,
`kernel-20261017-boot*.log` și `windows-20261017-*-events.json`. Ultimul eveniment
complet al sesiunii precedente este la 21:32:28.325 UTC, urmat de un record JSONL
trunchiat. Nu există returncode/stderr terminal pentru FFmpeg, Python sau batch
care să identifice exact comanda responsabilă pentru închiderea terminalului.
Windows User32/1074 consemnează o oprire inițiată prin meniul Start la
21:34:39.282 UTC, iar Kernel-General/13 oprirea sistemului la 21:35:01.139 UTC.
Aceste evenimente sunt ulterioare trunchierii sesiunii; nu dovedesc cauza
mesajului anterior exit 1. Nu este stabilit OOM, timeout sau un semnal anume.
Bootul curent este la 2026-10-17 05:28:25 UTC.

`incomplete-parts-20261017.json` consemnează două temporare istorice invalide:
48 bytes pentru integrala landscape și 1.048.624 bytes pentru fragmentul 2
portrait. Ambele dau ffprobe exit 1, fără moov; stderr-ul este păstrat separat.
Nu sunt rezultate publicate și nu au fost șterse. Fiecare reluare folosește alt
part și publică numai după verificare completă prin redenumire atomică.

Regresia cerută există în `tests/media/test_media.py`:
`test_resume_complete_scenes_after_interrupted_atomic_publication`,
`test_recovery_after_process_exit_with_three_valid_scenes` și
`test_failed_final_command_keeps_exact_stderr_and_returncode`.
Rerulare nouă în copie izolată `/tmp`, fără sinteză privată sau instalări:
**3 passed, 23 deselected în 20,96 s**, `regression-20261017.xml` și log.
Comandă echivalentă pentru aceeași selecție, din rădăcina copiei consemnate în `regression-20261017-root.txt`:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/daniel/projects/rec/.venv/bin/python -m pytest tests/media/test_media.py -q -p no:cacheprovider -k 'resume_complete_scenes_after_interrupted_atomic_publication or recovery_after_process_exit_with_three_valid_scenes or failed_final_command_keeps_exact_stderr_and_returncode' --junitxml=/home/daniel/projects/rec/work/media/production-20261016/recovery-scenes/regression-20261017.xml
```

Cele două teste de reluare interzic rerandarea MKV, compară hash/mtime și păstrează
part-ul incomplet; testul publicării verifică `os.replace` în același director,
cu MP4 deja decodat înaintea publicării. Testul în două procese lasă exact trei
scene complete, running pe disc și `os._exit(1)`, apoi verifică relansarea.
Regresia largă de **79 passed, 6 deselected** din `all-regression-mapping.xml`
este rezultatul păstrat al sesiunii precedente, nu o nouă rerulare în această zi.

Două erori auxiliare noi au cauze distincte și sunt consemnate în incident:
prima citire strictă a JSONL-ului s-a oprit la recordul trunchiat, apoi parserul
tolerant l-a consemnat; PowerShell din sandbox a returnat 1 pentru socket WSL
blocat, apoi citirea evenimentelor pe gazdă a trecut. Nu sunt erori ale exportului.


Întărire nouă a celor două regresii de reluare la 2026-10-17 UTC: fixture-ul
folosește acum antetul real de 48 bytes (`ftyp/free/mdat` gol, fără `moov`),
în locul unui buffer generic cu aceeași lungime. Se verifică explicit refuzul
ffprobe cu `moov atom not found` și SHA-256 neschimbat al part-ului după reluare.
Rerularea selecției de mai sus în altă copie izolată:
`regression-header-20261017.xml` / `.log`, **3 passed, 23 deselected în 18,19 s**;
rădăcina este în `regression-header-20261017-root.txt`. Nu se adună aceste trei
cazuri încă o dată la totalul istoric de 79 și nu se pretinde o rerulare completă.


### Eșec localizat la ultima adoptare, apoi reluare strictă

La **05:42:59 UTC** CLI-ul ultimului profil a returnat **1 înaintea encoderului
final**: `Eroare media: Expecting value: line 1 column 1 (char 0)`.
Cauză verificată: `4976dc738c4145fb985508b41d5e101e/portrait/scene-00002.receipt.json`
era gol, iar copia MKV pereche avea tot **0 bytes**. Celelalte trei scene ale
profilului erau complete. Ultima comandă rămasă fără rezultat în sesiunea veche
lansa `recovery-scenes/seed-compatible-scenes.py`; acest fapt nu oferă un
returncode al închiderii terminalului și nu este echivalat cu eșecul actual.

`prod-compilation-20261016-render-portrait-empty-copy-failure-exit.json` păstrează
argv exact și returncode 1; `empty-copy-failure-20261017.stderr` păstrează eroarea.
`empty-adoption-20261017.json` documentează repararea explicită: perechea goală
este păstrată cu sufix `.incomplete-20261017`; scena 00000 din fragmentul 2
portrait a fost decodată complet (**3.257 cadre**) și comparată prin contract de
pixeli/configurație/padding identic cu scena 00002 a compilației. Copia verificată
a fost sincronizată pe disc și publicată atomic, cu receipt nou compatibil.
**Nicio generare de pixeli și nicio resinteză.**

Helperul privat de adoptare nu mai ignoră orice fișier existent: refuză explicit
perechile goale/incompatibile, păstrându-le pentru audit. Copiile noi se fac în
nume temporare unice, cu fsync, hash verificat și publicare atomică. Nu este
adoptare automată în CLI. O întrerupere între publicarea MKV și receipt rămâne
refuzată conservator și cere audit; nu se pretinde tranzacție comună pe două
fișiere sau test real de întrerupere a alimentării.

Reluarea strictă a ultimului profil este consemnată în
`resume-last-profile-20261017.py` și log. Cele șapte MP4-uri deja verificate au
fost reconfirmate prin hash și păstrate. Auditul final care aștepta workerul s-a
oprit corect la starea failed; relansarea lui pe gazdă este separată. Încercarea
de a-i verifica PID-ul gazdei din sandbox a produs ProcessLookupError, păstrat
în log; nu este dovadă că workerul gazdă era oprit.


### Acceptanța finală a producției — 2026-10-17 UTC, 05:58 UTC

**8/8 MP4 PASSED tehnic**, în `output/media/scenes-v2/`. Fiecare are H.264/
yuv420p, AAC mono 22050 Hz, 30 fps și dimensiunile exacte 1920×1080 sau
1080×1920. Toate au fost decodate integral înainte de publicare atomică.
`final-acceptance.json`, `completion.json` și cele cinci receipts `finish-*`
consemnează succesul. Toate cele opt comenzi finale FFmpeg au returncode 0.
Receipts istorice running fără returncode rămân distincte, fără completare inventată.

| Material (ambele profile) | Video (s) | Audio decodat (s) | A/V (ms) |
|---|---:|---:|---:|
| prod-ro-20261016-001 | 688,833333 | 688,843175 | 9,841 |
| prod-fragment-20261016-001 | 348,400000 | 348,392200 | 7,800 |
| prod-fragment-20261016-002 | 340,433333 | 340,450975 | 17,642 |
| prod-compilation-20261016 | 688,833333 | 688,843175 | 9,841 |

`audio-preservation.json`: toate cele opt exporturi acoperă integral eșantioanele
masterelor verificate; corelația PCM↔AAC decodat este cel puțin 0,99996755.
Paddingul AAC este măsurat separat de sursă. Split→merge păstrează exact
15.188.520 eșantioane, SHA-256
`07a0622f9e2d4c3853948b1f0cb32678ab47a717c591a8eb2a8d3e4ec8288645`.
`units-preservation-20261017.json`: 893 + 931 unități și 79 + 91 scoruri reduse.
Toate cele **553 fișiere protejate** și mulțimea cache-ului audio sunt neschimbate.
Nicio resinteză, reinstalare, ștergere de scene/cache sau operație Git de scriere.

Acceptanța verifică numărul exact de cadre/padding pentru cele 22 scene din cele
opt profile și **8 SRT-uri cu acoperire textuală exactă**, ASS/aliniere/font,
plus **8 thumbnail-uri** și cele patru titluri deja selectate. `subtitles-final`
a executat cele patru etape, iar `subtitles-resume.json` le-a refolosit **4/4**,
workflow_status complete/incomplete gol. Acest rezultat aparține workflow-ului
nou de subtitrări; vechiul workflow de producție nu a fost rescris retroactiv.

Cadrele început/mijloc/final ale tuturor celor opt exporturi și contactul celor
două tranziții originale landscape au fost văzute efectiv în această sesiune:
`selected-frame-review-20261017.json`. Diacritice/text în cadru și scene vizibile
la capete; crossfade-uri graduale confirmate și prin proiecțiile pixelilor din
`landscape-frame-checks.json`. Status vizual: **partial_selected_frames_passed**,
fără vizionare integrală. Listening: **not_listened**; editorial: **not_reviewed**;
precizia ancorelor CTC manuale rămâne nemăsurată și 170 scoruri reduse nerevizuite.

Migrarea metadatelor este complete în `metadata-migration/journal.json`, cu copii
înainte/după, verificarea ancorelor Unicode în textul fiecărui derivat și hash-uri
MP4 neschimbate. Fixture-ul de migrare din sesiunea precedentă a verificat două
aplicări idempotente (`metadata-migration-fixture.stdout`, returncode 0).
Noua verificare reală `existing-subtitles-validated.json` confirmă **8/8** exporturi
existente identice cu conținutul așteptat din aliniere/stil/font, fără suprascriere.
Workerul normal folosește această verificare la relansare după migrarea ancorelor.
`adoption-idempotence-20261017.json`: rerularea helperului privat de adoptare
păstrează hash/mtime pentru **73 fișiere scene existente**, fără randare. Ramura
copiilor noi cu fsync nu este prezentată ca test de întrerupere a alimentării.

Comenzi efectiv folosite pentru încheiere și control, din rădăcina proiectului:

```bash
python3 work/media/production-20261016/recovery-scenes/continue-production.py
python3 work/media/production-20261016/recovery-scenes/repair-empty-adoption-20261017.py
python3 work/media/production-20261016/recovery-scenes/resume-last-profile-20261017.py
python3 work/media/production-20261016/recovery-scenes/finish-audit-20261017.py
python3 work/media/production-20261016/recovery-scenes/validate-existing-subtitles.py
```

Prima comandă este relansarea generală documentată în README; scripturile de
reparare/ultim profil sunt operații punctuale cu precondiții și nu se reexecută
pe producția completă. Workerii au fost lansați prin setsid pe gazdă, cu loguri,
lock unic și diagnostic. Auditul final execută migrarea, DSP/cadre, acceptanța și
centralizarea fără a porni render. Cauza terminalului istoric rămâne nedeterminată;
exitul CLI din această recuperare este localizat și rezolvat, nu ascuns.

## Continuare asset discovery/library/scenes — 2026-10-18 UTC

Versiune media 0.1.0, material schema 1/asset_schema=1, pipeline scene-assets-v1.
Audit: `work/media/asset-discovery-20261018/`. Starea găsită: baseline 8/8 MP4
tehnic PASSED păstrat; implementarea assets și probele din 17 octombrie existau,
README/notices actualizate, dar planul avea stări inițiale și lipsea centralizarea
acceptanței. Run-ul assets `3643b8e1d9e74ccf881468175ede943f` rămăsese running,
cu `.part.mkv` de ~608 MiB, fără scene complete/receipts sau MP4. Nu este proces
activ: procesele gazdei au fost inspectate separat de sandbox; niciun FFmpeg/worker
media activ. Lockurile media/audio au fost dobândite nonblocking și păstrate.
Nu se atribuie retrospectiv un returncode întreruperii din 17 octombrie.

Planul canonic a fost completat înaintea codului. Cod nou peste implementarea
existentă: preview video cu trei cadre 10/50/90% și cache pe hash; refuz checksum
incompatibil la import înainte de publicare; dimensions măsurate în bibliotecă;
candidați cu status/proprietăți normalizate și ranking structurat. Nicio modificare
în generatorul de scene, identitatea pipeline-ului, motorul TTS sau modelul CTC.

### Probe automate și istoric de erori

Regresia largă păstrată din 17 octombrie: **104 passed, 1 skipped**, 127,83 s,
`work/media/asset-discovery-20261017/regression-final.xml`; nu a fost repetată
costisitor. Testele assets noi s-au rulat în copie `/tmp`, prin driverul existent,
cu codul/testele/configurațiile copiate și PYTHONDONTWRITEBYTECODE=1. Prima probă:
27 passed/1 failed în 63,08 s, `assets-20261018.xml`; testul preview nou omitea
media.json din fixture-ul izolat. Corecția completează fixture-ul. Rerulare:
**28 passed în 49,45 s**, `assets-20261018-fixed.xml` și `.log`, rădăcina copiei
în `assets-20261018-fixed-root.txt` (în directorul de audit 20261017).

```bash
ASSET_TEST_LABEL=assets-20261018-fixed python3 work/media/asset-discovery-20261017/run-tests.py
```

Acoperire: provideri/mock/search/parsing/URL/DNS/redirecturi/MIME/executabile,
checksum/publicare atomică/dedup/cache/corupție/întrerupere/Range/429,
unknown license/provenance/credits/select/replace/undo/profile overrides,
video trim/muted/loop/freeze/sequence, split/merge, fallback/thumbnail/review,
partial rerender offline. Noul test video compară cadre distincte și hash/mtime
identice la reutilizarea preview-ului. Unit tests nu cer internet.

### Retrieval și bibliotecă reală

Căutările/downloadurile valide Commons/Openverse din 17 octombrie au fost păstrate.
La 18 octombrie sandbox-ul a refuzat DNS; aceleași operații online au fost cerute
explicit pe gazdă. Prima căutare `Romania flag -Wikipedia` a oferit rezultate
nepotrivite și nu a selectat automat nimic. Query-uri mai precise:
`intitle:Bucharest -Wikipedia`, `intitle:Iași -Wikipedia`. Fără scraping/rețea în render.
`discovery-summary.json` păstrează propunerile RO/EN/alternative, entitățile,
istoricul query-urilor reale și toate metadatele.

| Scenă integrală | Candidați păstrați | Descărcați | Surse locale comparabile |
|---|---:|---:|---|
| scene-001 | 24 | 3 | Commons 46ea9b461631a96c653e479d, Openverse 6499800dbdbc7373d1b9db4b, Commons 211d35f0fd4711a332ad2e2c |
| scene-002 | 12 | 3 | Commons 357ced8f81a5c31dd30506ff / ceede0a4adb614f6d6e83257 / f8102cadf67c613017ba986d |
| scene-003 | 7 | 3 | Commons 809800f52447143c0ce61e7d / 83edb41295b87ee3d709e996 / 49be4fe1b37de6718d3c8616 |

Biblioteca are **9 înregistrări/9 blobs distincte**, SHA256 și SQLite, plus usage și
încercări incomplete păstrate. Clipuri reale noi: Joe Mabel, București seara,
53,561 s/854×480/CC BY-SA 4.0; Eugen14Simion, iarna București 2012,
14,030 s/CC BY-SA 3.0; Drone in air, Biblioteca Centrală Universitară Iași,
72,247 s/CC BY 3.0. `video-*-download.json` păstrează surse/creator/licență/URL/
attribution/checksum/data. Protestul lung refuzat anterior (>256 MiB) nu a fost
forțat și nu a fost indexat incomplet. Pexels mock trecut, live BLOCKED fără key.

### Export real scurt, apoi replace pe o scenă

Material `assets-accept-20261018`, derivat prin split extract + merge din cel real.
`extract-plan.json`: [40627,127063], [5146958,5234276], [10115235,10202112],
la 22050 Hz: **260.631 eșantioane / 11,820 s**. Sunt extrase tehnice la limite
aliniate, fără validare auditivă/editorială a tăieturilor. Textul și timpii provin
din sursa cunoscută; fără ASR, TTS sau inferență CTC nouă. Derivatele păstrează
provenance/overrides. Scena întâi: imagine Argenna CC BY 3.0 landscape și altă
imagine Argenna CC BY-SA 3.0 portrait. Scena a doua: Joe Mabel, interval 2–10 s,
audio extern mut, imagine ilustrativă etichetată. Scena a treia: AUR/CC0 înainte,
înlocuită cu Focus Creștin/CC BY 3.0. Nu reprezintă review editorial uman.

Run **efe6b66a60a44bcfad061f4300e9f32d**. Comenzi efectiv executate (cu căi absolute
în receipts `first-command.json` / `replaced-command.json`):

```bash
unshare -Urn ./media render assets-accept-20261018 --profiles landscape,portrait --subtitles classic --output-root output/media/assets-accept-20261018-first
./media scenes assets-accept-20261018 --scene assets-accept-cut-20261018-003-scene-003 --select edbec9508a5d072a2d309b72 --approve
unshare -Urn ./media render assets-accept-20261018 --profiles landscape,portrait --subtitles classic --resume-run efe6b66a60a44bcfad061f4300e9f32d --rerender-changed --output-root output/media/assets-accept-20261018-replaced
```

**4/4 MP4 PASSED**, H.264/yuv420p, AAC mono 22050 Hz, 30 fps,
1920×1080/1080×1920. Video 11,833333 s; audio decodat 11,842177 s;
A/V **8,844 ms**, toate returncode 0 și decodare completă înainte de publicare.
Receipts finale/comenzi/stderr rămân în run; versiunile scenei a treia sunt
arhivate în revisions. Exporturile anterioare și baseline-ul nu sunt suprascrise.

`replace-proof.json` și snapshoturile înainte/după confirmă: numai scene-00002
și receipt-ul ei schimbate pe fiecare profil; **4 MKV + 4 receipts hash/mtime
identice**; master.wav/master-receipt identice; alignment și timeline identice.
MP4-urile finale au hash-uri diferite, deci reasamblate. `audio-proof.json`
reconstruiește independent PCM din intervalele sursei: egalitate exactă cu master,
corelație PCM↔AAC **0,9999666966** pe toate patru exporturile; același hash al
audio-ului AAC decodat. `protected-after.json`, 17:39:58 UTC: **581/581 fișiere
protejate identice**, inclusiv surse/modele/cache/exporturi baseline/materiale prod.

### Review, offline și limite

`review/scene-review.md`: proba scurtă; `review-full/scene-review.md`: materialul
integral cu câte trei candidați locali. Ambele au contact sheets și provenance;
clipurile au preview în trei cadre. Două thumbnail-uri independente sunt în
`output/media/assets-accept-20261018-thumbnails/`, cu credits/provenance. Toate
exporturile au credits.json/CREDITS.md. `selected-frames.jpg` conține câte trei
cadre ale exporturilor înlocuite. Au fost văzute efectiv: portrait folosește alt
asset la prima scenă, video și noua imagine apar. Status vizual **PARTIAL**:
eticheta ilustrativă se suprapune cu subtitrarea în scena video; necesită ajustare
de layout înainte de publicare. Landscape cover taie partea superioară a persoanei
în cadrul inspectat; încadrarea editorială necesită revizuire. Nu se pretinde
vizionare integrală; listening **not_listened**, editorial **not_reviewed**.

Render/review/thumbnail/audit-extra au rulat în namespace fără rețea (`unshare -Urn`).
Split/merge folosesc numai surse locale; offline pe mock este și în regresie.
Internet numai search/download. Commons/Openverse fără key, Pexels opțional cu
PEXELS_API_KEY. AI greu BLOCKED: audit WSL nou ~3,82 GiB, 4 CPU logice, fără
/dev/dxg/dri/nvidia-smi/nvcc; audit Windows din 17 octombrie păstrat separat:
Intel UHD, ~16,9 GB RAM, fără dovadă CUDA/DirectML utilizabilă. Fără instalări.
Exportul integral assets este TODO; cel întrerupt se păstrează. Toate restanțele
CTC/ASS/highlight/scroll/mix extern/animație/avatar/logo/review din plan rămân.

### Corecția compoziției și acceptanța actuală — 17:44 UTC, 2026-10-18

Problemele vizuale de mai sus aparțin versiunii `replaced`, păstrată intactă.
Prin CLI-ul existent s-a setat `visual.subtitle_placement=top` pe scena video și
`profile_overrides.landscape.visual.fit=contain` pe scena a treia. Run identic,
output-root nou `output/media/assets-accept-20261018-layout`. Comandă/returncode 0
în `layout-command.json`, verificări în `layout-state.json` și `layout-proof.json`.

**6/6 MP4 PASSED** pentru first/replaced/layout, două profile HD pe fiecare.
Ultima corecție a schimbat numai scene-00001 în ambele profile și scene-00002
landscape; **3 MKV + 3 receipts** au hash/mtime identice. Masterul și receipt-ul,
alinierea și cronologia rămân identice; audio-ul decodat are același SHA256 cu
exporturile măsurate anterior. Nu s-a refăcut nicio scenă cu setări neschimbate.

`layout-selected-frames.jpg` a fost văzut efectiv: subtitrarea este sus în scena
video, separată de etichetă, iar landscape contain arată persoana complet.
Status vizual **partial_selected_frames_passed** pentru aceste cadre corectate,
fără vizionare integrală. Listening/editorial rămân not_listened/not_reviewed.
`review-layout/scene-review.md` descrie selecția curentă, overrides și provenance;
`review-full` a fost regenerat cu numerotarea candidaților. Preview-urile video
existente s-au refolosit prin hash. Test separat după numerotare:
**1 passed, 27 deselected în 3,26 s**, `assets-review-numbered-20261018.xml` din
auditul 20261017; nu este un total suplimentar față de cele 28 de cazuri assets.

CLI efectiv pentru ajustări (JSON-uri echivalente `scenes --set`):
`{"visual":{"subtitle_placement":"top"}}` pe scena a doua;
`{"visual":{"fit":"contain"}}` cu `--profile landscape` pe scena a treia.
Scriptul privat reluabil `correct-layout.py` păstrează snapshoturi înainte/după.
Nu s-a modificat generatorul pentru aceste ajustări. AI/Pexels fără backend/key
și aprobarea umană sunt limitele reale rămase; integrala assets este încă TODO.

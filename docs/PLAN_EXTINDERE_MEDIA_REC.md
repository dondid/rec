# REC — Plan consolidat pentru extinderea media

Destinație: `/home/daniel/projects/rec`, Debian/WSL. Data specificației: **16 octombrie 2026**. Versiune: **1.0**. Acesta este singurul exemplar canonic. Fișierul omonim de la rădăcină nu exista la audit; sursa integrării este planul integral furnizat de utilizator. Cerințele de mai jos rămân criterii de implementare, nu declarații că toate funcțiile sunt deja instalate/testate.

Principiu: fluxul audio existent este păstrat, iar funcțiile media sunt independente și combinabile. Fragmentele și compilațiile sunt materiale obișnuite, nu produse ale unor renderere separate. Istoricul audio rămâne în [TEST_RESULTS.md](../TEST_RESULTS.md), utilizarea curentă în [README.md](../README.md).

## Starea curentă pe funcții — actualizare 2026-10-16 UTC

Planul inițial este păstrat, inclusiv cerințele normative dezvoltate în anexa A1–A20. Tabelele istorice nu sunt reinterpretate ca teste noi. Stările românești cerute se aplică mai jos: **implementată** fără probă suficientă, **verificată** cu dovadă specifică, **parțială** cu restanță, **neimplementată**, **blocată** cu impediment concret. `optional_not_installed` precizează o extensie opțională neinstalată; nu înseamnă imposibilitate hardware.

| Funcție | Stare curentă | Dovadă sau restanță concretă |
|---|---|---|
| Protecție ./tts, originale, cache | verificată | 38 regresii audio fără sinteză nouă; snapshot înainte/după în `work/media/real-alignment-audit/`; cele 44 de integrare rămân istorice. |
| Git/surse/documente | verificată | Regula `/*` a părintelui ignora întregul rec; adăugat numai `!/rec/`, cu permisiune. Excluderile locale pentru date private, modele, medii și rezultate rămân. Fără staging/commit/push. |
| Import real text/MP3 | verificată | `real-ro-20261016`; raport/manifest/hash-uri concordante; PCM exact 15.188.520 eșantioane. |
| Landscape/portrait/custom | verificată tehnic | Probe HD istorice și renderer comun; rezultatele noi per profil sunt enumerate separat în TEST_RESULTS. |
| Imagine fixă/contain/cover/focală | verificată | Probe media existente; copertă geometrică reală, fără pretenție semantică AI. |
| Aliniere română automată CPU | parțială | Backend CTC real, 30 ferestre/1.824 unități; 170 scoruri reduse și 17 normalizări, precizie auditivă/ancore ±200 ms nemăsurate. |
| Dependențe/model aliniere | verificată local | `.venv-align`, torch 2.8.0+cpu/transformers 4.56.2; model safetensors la revizia 79cf603aac59501d02bfeb37f615efc3ac4ce1b3; lock/hash-uri/licențe. Instalare curată secundară neefectuată. |
| Ferestre pentru audio lung TTS | verificată | Eșantioane reale și pauze din manifest; integral 688,822 s PCM. Fără estimare din caractere. |
| Audio lung fără ancore TTS | parțială | Cere `--windows` cu intervale/text cunoscute, maximum 40 s/fereastră; segmentarea/alocarea automată a textului fără ancore nu există. |
| Afișat/rostit/numere/sigle | parțială | Țintă CTC explicită, afișare originală păstrată pe materialul real; display_group manual testat. Maparea editorială complexă nu este dedusă automat. `‘89` nu devine implicit 1989. |
| Import manual timpi | verificată | Contractul `--words --provenance` păstrat, cu validarea textului/intervalelor. |
| SRT/ASS/classic | verificată tehnic | Exporturi și video reale; încadrare măsurată per profil. Sincronizarea auditivă rămâne nerevizuită. |
| Highlight/scroll | parțială | Render verificat pe fixture; fără validare auditivă pe material real. Scroll este fereastră discretă, nu deplasare continuă în pixeli. |
| Fonturi/diacritice | verificată punctual | DejaVu Sans, măsurare PIL, cadre selectate; nu vizionare integrală. |
| Scene imagini/clipuri | verificată pe fixture | Acoperire/ancore/assets verificate; asociere semantică/recunoaștere vizuală neimplementată. |
| Zoom/pan/crossfade/apariție titlu | verificată pe fixture | Nu scene AI noi; continuitatea fazei de mișcare la split rămâne neimplementată. |
| Avatar/logo/lip-sync | neimplementată | Asset opțional în plan; fără integrare actuală. Lip-sync realist/clonare nu sunt implicit în scop. |
| Titluri extractive/manuale/selectare | verificată tehnic | Candidați din fiecare material, selecție și blocare; relevanța editorială rămâne nerevizuită. |
| Thumbnail imagine/scenă/grafic PNG/JPEG | verificată tehnic | Compoziții adaptate pe profil, font minim/casete și JSON; fără evaluare semantică automată. |
| Split audio partition/extract | verificată pe voce reală | Două părți, limită de propoziție la eșantionul 7.682.042; text/scene/timpi rebazați. |
| Split text înainte de TTS | neimplementată | Restanță A10 tip A; CLI-ul temporal nu o finalizează. |
| Split capitole/semantic/maxim strict | parțială | Intervale, N părți și țintă există; capitole/semantică/maxim strict cu conflicte explicite nu sunt implementate. |
| Merge intern | verificată pe voce reală | Compilație din cele două părți; SHA PCM identic, 1.824 unități păstrate. |
| Merge extern/mix rate/fps/texte | parțială | Import separat și aceeași rată; conversii automate/resampling/re-narare neimplementate. |
| Pauze/intro/normalizare compilație | neimplementată | Merge fără efecte și fără voce suprapusă; configurarea acestor efecte rămâne cerință. |
| Renderer comun pe derivate | verificată | Același cod pentru integral/probă/fragmente/compilație; listele artefactelor în TEST_RESULTS. |
| Batch | parțială | Numai titles/thumbnail/subtitles/render; import/split/merge în afara batch. Eșecuri individuale și checkpointuri. |
| Cache/reluare aliniere | parțială; checkpointuri verificate pe voce reală | Întrerupere după prima fereastră, reluare cu hash/mtime păstrate; corupție JSON recuperată. Pregătirea WAV inițială și corupția copiei de analiză nu au recuperare automată validată. |
| Cache/reluare video | verificată la nivel profil | Probe de întrerupere; fără reluare per cadru/scenă. Imaginea fixă unică evită intermediarul FFV1 integral. |
| Offline aliniere + video real | verificată | `offline-real-current-result.json`: cache gol, unshare -Urn, rute goale; sandbox-ul blochează suplimentar socketurile. |
| Precizie manuală cuvinte/ascultare | neimplementată ca verificare | `not_listened`, `manual_anchor_accuracy: not_measured`; duratele A/V nu sunt precizie de aliniere. |
| Vizionare/editorial integral | neimplementată ca verificare | Cadre inspectate punctual; global not_reviewed. |
| LLM Qwen/llama.cpp, semantică, imagini/clipuri AI | neimplementată; optional_not_installed | Fără instalare în această etapă; necesită selecție, resurse, licențe și probe explicite. GPU absent nu blochează funcțiile CPU. |

### Decizii ale etapei reale și compatibilitate

Se păstrează schema material 1, cu metadate aditive în alignment.json: backend, model, setări, țintă acustică, confidence, normalizări și scoruri reduse. Importurile manuale existente rămân compatibile. Piper și configurația audio sunt nemodificate. CLI-ul nou este `align --backend ctc-ro`; `--words` rămâne alternativă exclusivă. Modelul propus în plan este folosit direct prin Transformers și Viterbi CTC, fără întregul WhisperX/ASR/diarizare sau model n-gram. Aceasta este o decizie de integrare explicită, nu declararea WhisperX ca instalat.

La textul actual, afișarea și rostirea au aceeași secvență de tokenuri. Numerele se expandează numai în ținta acustică, păstrată în manifest; siglele rămân avertizate. O cale CTC completă nu este dovadă de pronunție/sincronizare corectă. Niciun an prescurtat nu este reinterpretat implicit ca 1989 și nicio regulă experimentală nu este introdusă în dicționar.

Ultimul exit 1 al predării anterioare a fost reprodus separat: `git diff --no-index --check` pe documente diferite returnează 1 fără diagnostic de spațiere. Nu era un test audio/media eșuat. Proba nouă a consemnat și remediat două probleme distincte: testul offline folosea lock-ul global (acum izolat), iar publicarea alinierii importa inutil Pillow în worker (importurile grafice sunt acum locale funcțiilor). Rezultatele inițial eșuate se păstrează în audit, urmate de rerulări reale; nu sunt șterse din istoric.

## Istoricul primei implementări și diferențele asumate (înaintea alinierii reale)

Statusuri permise: `planned`, `implemented_not_tested`, `tested`, `blocked`, `optional_not_installed`. `tested` înseamnă numai capabilitatea efectiv acoperită de dovada citată, nu aprobare vizuală/editorială/auditivă. Orice limitare parțială se consemnează separat.

| Etapă/capabilitate | Stare la integrare | Dovadă/limită |
|---|---|---|
| F0 audit și protecție audio | tested, 2026-10-16 UTC | `work/media/audit/audio-regression.xml`: 44 teste rerulate în copie izolată; hash-uri în `protected-before.json`; capabilități în `capabilities.json`. |
| F1 materiale/profile/video | tested, 2026-10-16 UTC | `audio-demo` în 1920×1080 și 1080×1920; `scene-demo` și custom 640×360; rapoarte în `output/media/`. Fără sinteză nouă. |
| F2 import de timpi furnizați și SRT/ASS | tested, 2026-10-16 UTC | 16 teste media și fixture `scene-demo`: classic/highlight/scroll și mapare număr afișat/rostit. Teste de randare, nu validare a alinierii vorbirii. F2 automat rămâne nefinalizat. |
| F2 WhisperX + model românesc | optional_not_installed | Fără instalare/descărcare grea implicită; nu există comandă de aliniere automată declarată utilizabilă. |
| F3 funcții CPU de bază | tested, 2026-10-16 UTC | Imagini/clip, zoom/pan/crossfade/titlu; titluri extractive/manuale și thumbnail PNG/JPEG; cadre inspectate punctual. Avatar/logo și validare editorială rămân planned. |
| F4 derivare/loturi de bază | tested, 2026-10-16 UTC | Split→merge PCM identic; același renderer pe doi copii/compilație; lot 6/6 și relansare 6/6. Nu include încă toate cazurile text/mix extern/maxim strict. |
| F5 LLM/Wan/assets AI | optional_not_installed | Niciun backend/model mare instalat sau declarat verificat. |

Decizie de dependențe: Python-ul Debian are deja Pillow 11.1.0. `media` folosește `/usr/bin/python3`, separat de `.venv` audio, fără instalări pip/system. `requirements-media.lock` fixează versiunea observată, **nu** este un wheel lock cu hash-uri; o instalare media reproductibilă curată rămâne de validat. FFmpeg media folosește explicit build-ul local existent, fără schimbarea PATH-ului audio. Un build media nou, dacă devine necesar, va fi instalat separat și explicit.

## 1. Obiectivul final

Din text românesc și/sau materiale locale: MP3 prin fluxul existent; video cu imagine fixă cu/fără subtitrări; scene ilustrate cu imagini/clipuri; animații grafice; profile orizontale/verticale/custom; titluri și thumbnail-uri; împărțire în materiale independente; reunire în ordine aleasă; combinații și loturi.

Funcțiile de bază rulează local în CLI fără cont, abonament, trial, credite, watermark impus sau API plătit. Internetul este permis numai pentru instalări/descărcări explicite. Nu se construiesc interfață web, server HTTP permanent, bază de date sau publicare pe platforme. Imaginile/clipurile AI sunt extensii opționale; montajul, subtitrările cu timpi furnizați, titlurile extractive, compoziția locală, împărțirea și reunirea nu depind de ele sau de GPU.

## 2. Baza existentă și protecții obligatorii

Există `tts`, Piper Mihai, `rec.json`, dicționar, cache, FFmpeg local și documentația audio. Comanda rămâne compatibilă:

```bash
cd /home/daniel/projects/rec &&
./tts render input/text.txt -o output/text.mp3 --force &&
./tts verify output/text.mp3
```

Referința anterioară, nu un test nou al extensiei: `work/runs/20261016T090507-5f8a96d4/manifest.json`, 30/30 segmente, 0 cache hits, 688.875102 s MP3, 57.56760829999985 s total, MP3 mono 128 kbps 22050 Hz, `technical_status: passed`, `full_decode: true`, `listening_status: not_listened`. Manifestul confirmă segmente/cache; durata/formatul/timpul total provin din raportul asociat. Cele 44 de teste vechi nu devin rezultate noi decât după rerulare consemnată.

Înainte de modificări se inspectează AGENTS.md, documentația, codul și Git. Modificările utilizatorului se păstrează. Nu se reinstalează/actualizează preventiv `.venv`, Piper, ONNX, vocea sau FFmpeg audio. Nu se modifică inputuri, dicționarul, MP3-uri sau cache pentru demonstrații. Se folosesc directoare noi pentru media/teste/output și o configurație media separată, fără schimbări în `rec.json`. Se păstrează hash-uri/versiuni înainte/după; textul privat nu intră în Git. Fără commit/push, curățare, resetări sau modificări de sistem necerute. Schimbările indispensabile în cod comun trebuie minimale, justificate și retestate; motorul audio nu este rescris.

## 3. Arhitectura: un material, mai multe produse

Un material reunește text, audio, cronologie, aliniere, scene, titluri, thumbnail-uri și exporturi. Importul, alinierea, scenele, titlurile, thumbnail-urile, rendererul, derivarea și loturile au funcții mici, reutilizate identic de integral/fragment/compilație. CLI separat `./media`; fără platformă generică de pluginuri/cozi/servicii externe.

### 3.1 Manifestele și timpul

`material.json` are `schema_version`, ID stabil, părinți, căi și SHA-256 de surse; text original/afișat/rostit distinct; audio, rată și intervale în eșantioane; aliniere, scene, pronunții; setări și compoziție per profil; titluri candidate/selectate/aprobate și text thumbnail separat; proveniență/licență vizualuri când este cunoscută; exporturi/hash-uri/rapoarte/statusuri; reguli și istoric split/merge.

Căile relative se rezolvă față de documentul care le conține, niciodată față de shell. Vocea, subtitrările și scenele au o cronologie comună în indici de eșantioane sau fracții raționale. Rotunjirea în milisecunde/cadre se face numai la export. Schema 1 este prima schemă media, fără migrarea fișierelor audio existente; o versiune necunoscută se refuză.

## 4. Profile și compoziție

Profile obligatorii `landscape` 1920×1080, `portrait` 1080×1920 și `custom` cu dimensiuni explicite; opțional `square` 1080×1080. Un material poate selecta mai multe profile în aceeași comandă, fără resinteză/aliniere nouă pentru rezoluție. Numai combinațiile cerute sunt randate.

Implicit `contain`, fără deformare; `cover` numai ales explicit, cu focală configurabilă per scenă/profil. Textul, subtitrările, avatarul și logo-ul se reașază independent pe profil; nu se scalează mecanic întreaga compoziție. Margini de siguranță configurabile, fără pretenția de reguli universale de platformă. Dimensiuni pare pentru H.264/yuv420p, test real de encodare, MP4 H.264/AAC 30 fps constant ca alegere inițială. Calitatea/fps/încadrarea validate; thumbnail-ul poate avea alte dimensiuni. Nu se impun limite de durată ale platformelor. Disponibilitatea filtrelor se verifică în build-ul local [S1].

## 5. Imagine fixă și audio

Intrări locale JPEG/PNG + audio; imagine pe întreaga narațiune. Imaginea, titlul, logo-ul, subtitrările și mișcarea sunt opțiuni independente; thumbnail-ul nu devine implicit primul cadru. Nu se taie ultimul cuvânt și nu se adaugă ecran negru final. Se verifică duratele după decodare, toleranța de cadre și întârzierea codec-ului.

MP3-ul original se păstrează. Montajul preferă PCM/WAV/FLAC verificat când există; dacă intrarea este MP3, se decodează într-un intermediar local o dată la import. Nu se pretinde recuperarea informației pierdute. Se evită recodările intermediare cu pierderi și materialele lungi în array-uri de cadre în RAM.

## 6. Aliniere și subtitrări

Moduri independente: `off`; `classic` implicit la cerere (1–2 linii); `highlight` (fraza vizibilă, cuvânt evidențiat); `scroll` (fereastră după progres). Highlight/scroll cer timpi reali, nu estimare uniformă după lungimea textului.

### 6.1 Aliniere

Textul cunoscut efectiv rostit este sursa, nu o transcriere ASR substituită automat. Limitele segmentelor audio nu sunt limite de cuvinte. Candidat local: WhisperX + `gigant/romanian-wav2vec2`, asociat limbii `ro`, model cu intrare 16 kHz și licență declarată Apache-2.0 [S3,S4]. Aceste informații sunt o bază de evaluare, nu test local de precizie. Copia resamplată pentru analiză nu schimbă sursa. Nu se instalează diarizare/modele cu cont nenecesare și nu se cere obligatoriu transcriere completă pentru text cunoscut. Toate resursele auxiliare se descarcă explicit pentru procesare offline.

Textele lungi cer ferestre ancorate cu suprapunere controlată și frontiere rezolvate. Nu se presupune eficiența unui apel pe zeci de minute. Maparea afișare/rostire este explicită: de exemplu `2026` versus mai multe cuvinte rostite. Nealinierile rămân marcate; nu se inventează timpi exacți. Highlight produce eroare la acoperire insuficientă, sau fallback clasic numai ales explicit și raportat.

### 6.2 Export/aspect

Fișiere separate `subtitles.srt`, `subtitles.ass`, `alignment.json`. Stilizarea ASS randată în pixeli se distinge de aspectul într-un player arbitrar. Se verifică diacritice, punctuație, linii, intervale pozitive/ordonate, spații și încadrare. Fonturi locale cu proveniență. Culoarea, fontul, conturul/fundalul și poziția nu cer realiniere. Audio-ul, viteza și pauzele schimbate invalidează timpii afectați. O copie a alinierii include amprenta cronologiei audio, nu doar calea inputului.

## 7. Scene și animații

### 7.1 Plan editabil

`scenes.json`: ID, pasaj ancoră, interval audio, asset, focală, mișcare, tranziție, ajustări per profil. Acceptă imagine pe întregul material, imagini pe scene, imagini/clipuri mixte și opțional avatar grafic. Prioritate asset-urilor utilizatorului. Asocierea automată bazată pe nume/metadate nu este prezentată ca recunoaștere vizuală. Planul rămâne inspectabil; acoperire integrală fără goluri accidentale. Asset lipsă/rezoluție mică/clip prea scurt se raportează, fără umplere cu vizualuri irelevante.

### 7.2 Animații CPU

Deplasare lentă, zoom in/out, tranziții discrete, apariție de text/elemente. FFmpeg zoompan/xfade sunt opțiuni [S1]. Mișcare legată de scenă; subtitrări stabile după mișcare, cu viteză/intensitate/tranziții configurabile. Mișcarea camerei pe o fotografie nu este acțiune AI nouă. Avatarul simplu este opțional; lip-sync realist/clonare nu sunt incluse implicit.

### 7.3 Assets AI opționale

Generarea asset-ului este separată de randare. Modelul produce fișier local aprobat, tratat ulterior ca asset obișnuit. Înainte de alegere: CPU/RAM/GPU/VRAM/spațiu, licență, acces fără cont și test real. Fără drivere Windows/CUDA sau descărcări mari automate. Wan2.1, cod Apache-2.0 [S8], este candidat nevalidat, nu motor de producție promis. Când resursele nu sunt potrivite, funcțiile CPU continuă; AI se marchează neinstalat/blocat, fără serviciu plătit înlocuitor. Textul se desenează prin renderer, nu prin litere generate în fundal AI. Proveniență: prompt/model/revizie/seed/parametri/aprobare. Ieșirea unui model nu se execută drept cod.

## 8. Titluri

Funcție separată, înainte/după montaj, fără resinteză. Până la 3–5 variante distincte dacă sursa permite; întregul conținut, numai al fragmentului pentru fragmente, conținut reunit pentru compilații. Nume/ani/afirmații susținute de sursă, fără clickbait sau concluzii inventate. Titlu manual, selecție și blocare aprobată; text thumbnail separat. Titlurile părintelui nu se copiază automat în toate fragmentele.

### 8.1 Backend-uri

Bază CPU deterministă: extragere de capitole/propoziții-cheie/sintagme, clasare simplă, deduplicare, limite configurabile. Nu simplă redenumire sau „Partea 1”; lipsa candidaților buni cere editare și nu pretinde creativitate. Se păstrează `candidate_id`, titlu, text thumbnail, pasaje sursă, backend/versiune și `suggested/selected/approved`.

LLM opțional: Qwen3-4B-GGUF + llama.cpp CLI [S6,S7], revizii fixate, local, CPU posibil; fără server sau descărcări la render. Necesită instalare explicită, limite memorie/timp și probe românești. Fără fallback tăcut la backend diferit. Pentru texte lungi: selecție/ierarhie cu referințe, fără trunchiere la început și pretenție că s-a analizat tot.

## 9. Thumbnail-uri

Imagine separată asociată materialului, nu primul cadru obligatoriu. Legătura cu narațiunea prin text rostit/scene/intervale; fără ASR suplimentar pentru text cunoscut și fără analiză de emoție vocală pretinsă.

### 9.1 Moduri

Imagine utilizator + text; scenă/cadru reprezentativ ales cu pasaj (nu implicit primul cadru); copertă grafică din culori/forme, explicit ne-AI. Fundal AI eventual prin modul opțional. Variante de compoziție reale (de exemplu panou jos/text sus), vizual/focală/text editabile, specifice fiecărei părți.

### 9.2 Export

PNG/JPEG, dimensiuni independente; 16:9/9:16 adaptate fără crop orb. Stil coerent și conținut specific, diacritice, contrast, margini, măsurare reală a textului cu Pillow [S5]. Font minim și eroare/editare la depășire, fără ascundere/micșorare nelimitată. JSON alături: sursă vizuală, interval, text, profil, setări. Thumbnail independent de encodarea întregului video. Nu se descarcă imagini implicit și nu se șterg watermark-uri.

## 10. Împărțire

### 10.1 Intrări

A: text înainte de TTS, pe capitole/paragrafe/limite explicite, fiecare parte prin fluxul audio; durata pre-TTS este estimare. B: audio/video cu text+aliniere, extracție de intervale, fără resinteză. C: audio/video fără text, tăiere temporală; semantică numai cu transcript sau ASR local explicit, fără text inventat.

### 10.2 Metode și plan

Capitole/paragrafe, N părți echilibrate, durată-țintă ajustată la limite sigure, intervale manuale, propuneri semantice distincte prin backend testat sau plan manual aprobat. Structura de capitole nu este înțelegere AI. `partition` acoperă totul fără gol/suprapunere; `extract` consemnează omisiuni/repetiții intenționate. Ținta de 60 s nu este durată garantată; un maxim strict cere limite sigure, altfel conflict explicit, nu tăiere tăcută a cuvântului.

### 10.3 Materiale complete

Fiecare parte: ID/părinte/interval, text propriu când este cunoscut, audio derivat/referit, aliniere rebazată la zero, scene, titluri/thumbnail și exporturi. Aceleași opțiuni F1–F3, moștenire și suprascrieri per parte. Întâi `split-plan.json` inspectabil, aplicare explicită sau batch documentat fără întrebare obligatorie.

Nu se dublează/tai cuvinte, pauze sau scene la frontiere. Subtitrările se regrupează din cuvintele copilului, fără cuvinte nerostite în cue; scenele active/mișcarea se ajustează la cronologia nouă, maparea părintelui se păstrează. Dacă timpii lipsesc, tăierea temporală nu inventează textul fragmentului.

## 11. Reunire

Ordinea materialelor/textelor/audio/video este explicită, fără wildcard/sortare lexicografică implicită.

### 11.1 Internă

Cronologie nouă din surse/intervale păstrate; reutilizează audio/scene/assets, rebasează subtitrări/capitole. Randare din surse curate, nu obligatoriu din MP4-uri comprimate. Vocile rămân; re-nararea necesită opțiune separată, text și avertizare, niciodată implicită. Compilația are titlu/thumbnail proprii; titlurile părților pot fi metadate, nu intro-uri rostite automate.

### 11.2 Fișiere externe

Inspectează codec/dimensiuni/fps/orientare/audio/durată; conversii în intermediari separați la profil final. `-c copy` numai dacă compatibilitatea și rezultatul sunt verificate [S2]; tăieri precise țin cont de cadre/keyframes. Subtitrările arse nu devin editabile; repoziționarea curată cere surse curate/reconstrucție, iar limita se raportează.

### 11.3 Tranziții/sunet

Implicit fără suprapunerea vocilor. Tranziții vizuale pot folosi cadre menținute/suplimentare fără scurtarea narațiunii. Pauzele/intro-urile/effectele temporale intră în cronologia comună; offseturi din montaj real, nu suma aproximativă a duratelor containerelor. Fără crossfade automat peste cuvinte sau normalizări repetate; normalizarea compilației configurabilă și măsurată.

### 11.4 Inversabilitate

Split→merge păstrează ordinea/conținutul dacă nu sunt părți eliminate/modificate sau efecte temporale noi. Pe PCM fără resampling/efecte, eșantioane identice. MP3/MP4 reencodate: fără promisiune de identitate binară; verifică acoperire și întârziere codec.

## 12. Combinare și loturi

Prioritate: implicite → proiect media → material → fragment/scenă → CLI. Loturile pot combina integral în două profile cu subtitrări+thumbnail, părți cu vizualuri diferite și titluri proprii, compilație din părți selectate, regenerare numai de titlu/stil/thumbnail. Funcțiile trebuie independente și combinabile. Incompatibilitățile se validează înainte de randare, fără produs cartezian de exporturi necerute. Backend cerut dar absent produce eroare explicită, nu succes global.

## 13. Dependențe, offline și eficiență

### 13.1 Izolare

Audio rămâne în `.venv`; orchestrarea media și alinierea grea sunt izolate efectiv (numele `.venv-media`/`.venv-align` sunt propuneri, nu obligație dacă există structură compatibilă). Lockfile-uri separate. `media doctor` verifică CPU/RAM/disc, uneltele efective, H.264/AAC/filtre/fonturi/modele și GPU dacă este vizibil. GPU absent nu este eroare CPU. FFmpeg media nou, când este necesar, se instalează explicit separat de audio. Modelele păstrează revizie/sursă/hash/dimensiuni/licențe distincte pentru cod/greutăți/date.

### 13.2 Invalidare/cache

Alt thumbnail: reutilizează audio/aliniere/video. Alt font: audio/aliniere. Altă rezoluție: audio/aliniere/structură scene. Altă imagine: audio/aliniere/rest assets. Alt titlu: audio/aliniere, video doar dacă titlul nu era în pixeli. Altă ordine: assets/alinieri locale, offseturi noi. Alt text/viteză: refacere audio+aliniere afectate. Altă pauză: audio de bază, cronologie/exporturi noi. Imaginea schimbată poate cere reencodare finală; nu se promite cache pe fiecare cadru.

Prioritate audio/aliniere/titluri/assets; cache video numai corect și măsurabil. Chei din conținut/versiuni/model/font/parametri/profile, nu numai căi/mtime. Scriere atomică/temporare distincte/stare/relansare, `.part` invalid, export vechi valid păstrat la eșec. Flux de pe disc și paralelism limitat, fără toate cadrele în RAM sau toate modelele grele simultan.

### 13.3 Integritate

Argumente subprocess separate; fără shell construit din text, metadate sau ieșire LLM. Escapare controlată pentru filtre, căi dificile. Procesare fără rețea/fallback cloud. Cererile neexecutate/eșecurile se raportează individual, iar lotul incomplet nu are succes total.

## 14. CLI: specificație versus interfață reală

Interfața dorită include `doctor`, `init`, `align`, `subtitles`, `scenes`, `titles`, `thumbnail`, `split`, `merge`, `render`, `batch`, `verify`. `--help`, rapoarte JSON, logare, `--force` explicit, planificare și reluare documentate. Nu se impun pași interactivi în lot; modele prin instalare/descărcare separate.

**Exemplele de intenție din plan nu sunt contract CLI implementat.** Sintaxa testată se publică în README după probe; în special `align --words` este import de timpi furnizați, nu WhisperX; `titles` este extractiv/manual și nu acceptă un backend LLM neinstalat. Un material se poate furniza prin ID sau calea absolută/relativă către `material.json`. Profilele se selectează în cererile de export, nu prin resinteză.

## 15. Structură

Noi fișiere: `media`, `media.json`, `src/rec_media/`, `requirements-media.in/.lock`, `assets/`, `materials/<id>/material.json` și metadate scene/titluri/aliniere, `output/media/<id>/<profil>/video.mp4` + rapoarte/thumbnail/subtitles, `work/media/{cache,runs,plans,batches,audit}/`, `tests/media/`, acest plan canonic, instrucțiuni AGENTS.md și documentele existente actualizate. Lock de aliniere numai după alegerea/instalarea backend-ului, fără fișier care ar pretinde că instalarea s-a făcut. Nu se mută directoare audio. Se inspectează orice destinație existentă. Manifestele cu text privat/assets personale/rezultate se exclud implicit din Git; numai exemple sintetice în teste.

## 16. Etape și criterii

- **F0:** inventar/Git/hash-uri/comenzi/regresii izolate/capabilități, fără reinstalare.
- **F1:** materiale, import, profile, video fix, verificare, aceeași voce fără sinteză nouă.
- **F2:** model local izolat și testat pe română, SRT/ASS/clasic/highlight, scroll testat separat; importul manual nu echivalează cu finalizarea alinierii automate.
- **F3:** scene, animații CPU, titluri extractive/manuale, thumbnail; funcții și separat. LLM numai instalat/testat explicit.
- **F4:** fragmente normale, planuri, offseturi, compilații, profile și split→merge; toate funcțiile disponibile la integral aplicabile derivatelor.
- **F5:** după audit/resurse/instalări explicite: LLM/semantică/assets AI, status/test separat. Nu blochează F1–F4.

După fiecare etapă se rulează teste noi și regresia relevantă, se actualizează documentația și matricea. Un flag sau stub nu finalizează o etapă.

## 17. Acceptare

| Caz | Criteriu |
|---|---|
| Audio | Comenzi/regresii funcționale, hash-uri originale neschimbate. |
| Imagine/audio/profile | MP4 integral, fără final tăiat/negru accidental, dimensiuni exacte, custom validat, fără deformare. |
| Fonturi | Ș/Ț/Ă/Â/Î și minuscule, încadrare și caractere fără lipsuri. |
| Subtitrări | Ordine/durate/acoperire/pauze și probe început/mijloc/final; mapare afișat/rostit; highlight/scroll numai pe aliniere. |
| Scene | Acoperire/ancore, lipsuri raportate. |
| Thumbnail/titluri | Dimensiuni/text în casetă/compoziție pe profil și fragment, context propriu, selecție manuală păstrată. |
| Partition/extract | Fără goluri/suprapuneri la partition; omisiuni/repetiții explicite la extract; contabilizare text/timp. |
| Split→merge | Eșantioane PCM identice fără efecte/resampling. |
| Merge/mixte | Ordine/offseturi corecte, fără voce dublată; formate diferite tratate explicit. |
| Cache/întrerupere | Font/imagine fără resinteză; reluare fără pierderea rezultatelor valide. |
| Offline/export | Izolare reală când permite mediul; ffprobe și decodare A/V completă, fluxuri/durate conforme. |
| Căi/lot | Spații/apostrofuri/diacritice fără shell/filtergraph defect; eșecuri nominalizate fără succes total. |

Toleranță A/V inițială maximum **100 ms după decodare**, cu explicația cadrării și întârzierii codec-ului; nu este precizia subtitrării. Precizia subtitrării cere probă românească cu ancore manuale: țintă propusă maximum 200 ms la limitele inspectate, fără garanție pentru toate cuvintele. Se extrag cadre început/mijloc/final/tranziții/text lung pentru inspecție. Tehnicul nu validează relevanța titlului/imaginii sau voce naturală.

Statusuri distincte: `technical_status`, `alignment_status`, `visual_review_status`, `listening_status`, `editorial_review_status`. Fără vedere/ascultare reală rămân `not_reviewed`/`not_listened`, nu `passed`.

## 18. Documentare și predare

README principal: funcții curente/instalare reală/exemple testate/diagnostic/linkuri. Acest plan: cerințe/decizii/status/diferențe/restanțe. TEST_RESULTS: date/versiuni/run-id/comenzi/artefacte/eșecuri/omisiuni, istoric păstrat. THIRD_PARTY_NOTICES: cod/modele/assets/fonturi cu proveniență/licențe distincte. CHANGELOG doar dacă devine util; AGENTS cu regulă scurtă. La schimbare CLI/config/schema/dependențe/model/comportament se actualizează toate explicațiile afectate, matricea, testele și compatibilitatea/migrarea, fără copii contradictorii.

Datele tehnice folosesc UTC explicit; Europe/Bucharest poate fi afișat separat. Textul privat nu este copiat în README/Git. Predarea include implementat/opțional, păstrat/modificat, comenzi exact testate, artefacte/rapoarte, limite/blocaje/verificări nefăcute și Markdown actualizat. Sudo fără acces: comandă și motiv, niciodată parolă cerută sau execuție pretinsă.

## 19. Proveniență și surse

Baza audio din relatări: PLAN_IMPLEMENTARE_REC.md și două texte Pasted text(20261016-074030)/(20261016-080637), plus raportul ulterior al rulării de referință. Aceste fișiere nu sunt presupuse prezente; relatările sunt confruntate cu artefactele reale. Un plan vechi nu suprascrie comportamentul verificat fără decizie explicită.

Sursele primare furnizate în specificație (nu probe locale de performanță/licențiere completă):

- [S1 FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html): scale/pad/crop/subtitles/trim/setpts/concat/zoompan/xfade.
- [S2 FFmpeg concat](https://ffmpeg.org/ffmpeg-formats.html#concat): compatibilitate/temporizare.
- [S3 WhisperX alignment](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py) și [proiect](https://github.com/m-bain/whisperX).
- [S4 Romanian Wav2Vec2](https://huggingface.co/gigant/romanian-wav2vec2).
- [S5 Pillow ImageDraw](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html).
- [S6 Qwen3-4B-GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF) și [licență](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/main/LICENSE).
- [S7 llama.cpp](https://github.com/ggml-org/llama.cpp).
- [S8 Wan2.1](https://github.com/Wan-Video/Wan2.1).

Nu se descarcă implicit main/master în producție. După selecție/test se fixează versiuni/revizii/hash-uri/surse. Licența codului nu dovedește licența tuturor greutăților/date.

## 20. Checklist și restanțe

Finalizarea consolidată cere toate criteriile: audio protejat/retestat; profile și imagine fixă; subtitrări cu timpi reali și fișiere separate; scene/animații pe cronologia comună; titluri editabile proprii; thumbnail fără API și video obligatoriu; aceleași funcții pe fragmente; merge cu offseturi corecte; loturi/cache/relansare testate; AI opțional cu statut real; exemple README verificate; plan/rezultate/licențe/AGENTS actualizate.

**Restanțe consemnate la implementarea inițială (istoric; matricea curentă de mai jos precizează ce s-a rezolvat):** instalare și precizie WhisperX pe română; ferestre de aliniere lungă; ancore auditive manuale; split text înainte de TTS și semantică; maxime stricte de durată; resampling/mix extern complet; pauze/intro/normalizare configurabile la merge; continuitate de fază a animației între fragmente; avatar/logo; parametrizare completă a stilului ASS (culoare highlight/poziție liberă); aprobare editorială/vizuală; modele generative F5; reproductibilitate media într-un mediu curat. Probe și priorități ulterioare trebuie să actualizeze această listă, nu să declare întregul plan finalizat.


### Dovezi ale implementării inițiale și compatibilitate

Cod media 0.1.0, schema material 1. Rezultatele sunt în [TEST_RESULTS.md](../TEST_RESULTS.md), `work/media/audit/audio-regression.xml`, `work/media/media-tests.xml`, `work/media/demo/pcm-roundtrip.json` și rapoartele MP4. Importul aliniamentelor validează textul și timpii, dar rămâne `imported_not_reviewed`. Importul eșuat nu are încă reluare automată de director parțial. Randarea reia la nivel de profil, nu dintr-un cadru intermediar. Nu există cache video pe fiecare scenă; scenele incomplete se pot reface din surse fără pierderi.

Batch-ul curent acceptă numai render/thumbnail/subtitles/titles; importul și split/merge se fac înainte de lot. Căile din manifestele media se rezolvă relativ la document; listele `args` ale loturilor păstrează semantica CLI a căilor din shell (se recomandă absolute). Aceste restrângeri sunt explicite, nu funcții declarate finalizate. Moștenirea compoziției este implementată; mixul cu stiluri/rate diferite cere încă decizie/conversie explicită. Pauzele/normalizarea suplimentară la merge nu sunt oferite implicit.

La etapa inițială doar cadre selectate au fost inspectate; rapoartele de export păstrează `visual_review_status: not_reviewed` pentru vizionarea integrală și `listening_status: not_listened`. Precizia aliniamentelor pe voce românească și ancorele ±200 ms nu au fost măsurate. F0–F4 au subseturi testate; **întregul checklist consolidat nu este declarat finalizat**.

## Anexă normativă — cerințele consolidate originale, dezvoltate integral

Această anexă face parte din același document canonic. Păstrează cerințele de produs ale versiunii 1.0 furnizate în conversație; deciziile și probele de mai sus se citesc separat de aceste cerințe. Nu există un al doilea exemplar la rădăcina proiectului. Descrierile unei funcții dorite nu îi schimbă statutul de implementare.

### A1. Obiectivul final și limite

Dintr-un text românesc și/sau din materialele locale existente, utilizatorul trebuie să poată produce audio MP3 prin fluxul actual, video cu imagine fixă cu sau fără subtitrări, video cu imagini sau clipuri care urmăresc ideile narațiunii, mișcări grafice și animații aplicate scenelor, exporturi orizontale/verticale/personalizate, titluri și thumbnail-uri relevante, mai multe materiale independente dintr-un material mare, un material unic din mai multe materiale în ordinea aleasă și combinații ale acestor funcții, inclusiv în lot.

Toate funcțiile de bază trebuie să funcționeze local din CLI, fără cont, abonament, trial, credite, watermark impus sau API plătit. Internetul este permis pentru instalări și descărcări explicite, nu pentru procesarea obișnuită. Nu se construiesc interfață web, serviciu HTTP permanent, bază de date sau sistem de publicare pe platforme. Generarea AI de imagini/clipuri este opțională, dependentă de modele și resurse validate; nu condiționează montajul, subtitrările, titlurile extractive, thumbnail-urile compuse local, împărțirea sau reunirea.

### A2. Baza existentă și protecția ei

Baza raportată este `./tts`, Piper `ro_RO-mihai-medium`, `rec.json`, dicționarul, cache-ul segmentelor și FFmpeg local; documentele includ README, TEST_RESULTS și THIRD_PARTY_NOTICES. Comanda audio din secțiunea 2 trebuie să rămână valabilă. Rularea de referință este `20261016T090507-5f8a96d4`: 30/30 segmente, zero cache hits, 688.875102 s MP3, 57.56760829999985 s total, mono/128 kbps/22050 Hz, passed/full_decode true/not_listened. Aceasta este o relatare confruntată cu fișierele, nu o execuție făcută la redactarea specificației. Numărul inițial de 44 teste nu trebuie prezentat ca test nou fără rerulare.

Protecții obligatorii, fiecare aplicabilă separat:

- Citește AGENTS, documentația și codul; inspectează Git înainte de modificări și păstrează modificările utilizatorului.
- Nu reinstala și nu actualiza preventiv `.venv`, Piper, ONNX, vocea sau FFmpeg-ul audio.
- Nu modifica originalele din `input/`, dicționarul, MP3-urile existente sau cache-ul audio pentru demonstrații.
- Folosește directoare noi pentru media, teste și rezultate; fără suprascriere implicită.
- Nu schimba `rec.json` pentru video; configurația media este separată.
- Înregistrează versiuni și hash-uri relevante înainte/după; nu include textele private în Git.
- Fără commit, push, curățare cache, modificări de sistem sau resetări Git necerute.
- Orice modificare indispensabilă în cod comun este minimă, justificată și acoperită de regresie; motorul audio nu se rescrie.

### A3. Un material, mai multe produse

Textul, audio-ul, legăturile temporale, scenele, titlurile, thumbnail-urile și exporturile aparțin unui material. Fiecare fragment și fiecare compilație este tot un material. Același renderer și aceleași funcții se aplică tuturor; nu se construiesc fluxuri incompatibile.

| Componentă | Intrări | Rezultate cerute |
|---|---|---|
| Audio existent | Text și opțiuni TTS | MP3 și rapoartele actuale |
| Import și cronologie | Text/audio/video/manifest | Material și referințe la surse |
| Aliniere | Audio și text efectiv rostit | Timpi ai cuvintelor/propozițiilor |
| Scene | Pasaje, imagini, clipuri | Plan editabil |
| Titluri | Conținutul materialului | Variante și selecție |
| Thumbnail | Titlu scurt și vizual relevant | PNG/JPEG și metadate |
| Montaj video | Cronologie, vizualuri, audio, subtitrări | MP4 și raport |
| Împărțire/reunire | Materiale și reguli de montaj | Materiale derivate |
| Loturi | Materiale și profile | Exporturi independente, reluabile |

CLI separat, de exemplu `./media`, fără schimbarea `./tts`; adaptoare mici, fără platformă generică de pluginuri, cozi externe sau servicii distribuite.

Fiecare material are `material.json`, versionat prin `schema_version`, cu ID stabil și sursa/părintele; căi și hash-uri pentru surse; text original, afișat și pregătit pentru rostire distincte; surse audio, sample rate și intervale în eșantioane; aliniere, scene și reguli de pronunție; profile și compoziție pe profil; titluri candidate/selectate și text thumbnail; proveniența și licența cunoscută a vizualurilor; exporturi/hash-uri/rapoarte/statusuri; reguli și istoric split/merge. Căile relative se rezolvă față de documentul care le conține, independent de shell. Vocea, subtitrările și scenele folosesc o singură cronologie în eșantioane sau fracții raționale; conversia la ms/cadre se face numai la export, fără rotunjiri repetate.

### A4. Formatele videoclipurilor

| Profil obligatoriu | Dimensiuni | Raport |
|---|---|---|
| landscape | 1920 × 1080 | 16:9 |
| portrait | 1080 × 1920 | 9:16 |
| custom | Lățime și înălțime explicite | Calculat și validat |

Pătratul 1080 × 1080 poate fi preset suplimentar; nu este necesară o listă mare. Un material poate fi exportat în mai multe profile în aceeași comandă, fără regenerarea vocii/alinierii pentru rezoluție. Nu întinde imaginea. Oferă contain cu margini și cover cu decupare; focală configurabilă, inclusiv pe scenă/profil. Contain este implicit, iar crop-ul nu trebuie să taie subiectul fără alegere explicită. Subtitrările, titlurile, avatarul și logo-ul se reașază pe profil, nu se scalează mecanic întregul cadru. Margini de siguranță configurabile, fără pretenția unor reguli universale de platformă.

Pentru H.264/yuv420p sunt necesare dimensiuni pare și un test de encodare. MP4/H.264/AAC/30 fps constant sunt alegeri inițiale, nu cerințe universale de publicare. Calitatea, fps și încadrarea sunt configurabile și validate. Thumbnail-ul își alege separat dimensiunile. Nu introduce limite de durată sau cerințe de rețele sociale fără cerere și verificare actuală. Disponibilitatea filtrelor scale/pad/crop/subtitles/tranziții se verifică în build-ul FFmpeg local [S1].

### A5. Imagine fixă

Acceptă audio local și JPEG/PNG local. Imaginea acoperă durata completă a narațiunii. Imaginea, titlul pe ecran, logo-ul, subtitrările și mișcarea sunt independente; thumbnail-ul nu este introdus automat ca primul cadru. Nu întrerupe ultimul cuvânt pentru egalizarea duratelor și nu lăsa ecran negru accidental la final. Diferența A/V se verifică după decodare, cu toleranță documentată pentru cadre și întârziere codec.

Păstrează MP3-ul original. Preferă master PCM/WAV/FLAC verificat când există. Dacă există numai MP3, decodează-l o dată în intermediar local; nu pretinde recuperarea informației pierdute, dar evită recodările intermediare succesive.

### A6. Subtitrări și aliniere

| Mod | Comportament cerut |
|---|---|
| off | Fără subtitrări |
| classic | Una/două linii în unități lizibile; implicit la cererea subtitrărilor |
| highlight | Fraza rămâne vizibilă, cuvântul rostit este evidențiat |
| scroll | Fereastra textului urmărește progresul vorbirii |

Highlight și scroll folosesc timpi reali, nu ritm uniform din lungimea textului. Textul cunoscut efectiv rostit este sursa; nu îl înlocui automat cu transcriere ASR. Timpii manifestului audio se refolosesc numai cu semnificația necesară verificată; segmentele nu sunt cuvinte.

Candidatul specificației: WhisperX și `gigant/romanian-wav2vec2`, asociat limbii ro, model declarat Apache-2.0 cu intrare 16 kHz [S3,S4]. Acestea justifică evaluarea; integrarea și precizia se testează local. Folosește copie resamplată pentru analiză, fără modificarea sursei. Nu instala diarizare/modele cu cont nenecesare; textul cunoscut nu cere obligatoriu transcriere completă. Descarcă explicit toate resursele, inclusiv auxiliare text, pentru a evita descărcări surpriză la prima procesare offline.

Pe texte lungi aliniază pe ferestre/propoziții ancorate, cu suprapunere controlată și rezolvarea frontierelor; nu presupune eficiența/stabilitatea unui singur apel pe zeci de minute. Păstrează explicit diferența dintre rostire și afișare: `2026` poate fi afișat astfel, în timp ce audio spune „două mii douăzeci și șase”. Cuvintele nealiniate/acoperirea insuficientă rămân marcate. Nu inventa timpi exacți. La highlight, pasajul nealiniat produce eroare clară sau fallback clasic numai cu politică aleasă explicit și raportată.

Produce separat SRT, ASS și alignment.json. SRT este text temporizat simplu; stilizarea/evidențierea sunt ASS și randare configurată. Verifică diacritice, punctuație, lungimea liniilor, intervale pozitive/ordonate, spații și încadrare. Fonturi locale, proveniență cunoscută. Culoarea, mărimea, conturul/fundalul și poziția se schimbă fără realiniere. ASS avansat nu are aspect garantat identic în orice player; subtitrarea arsă este rezultat distinct. Audio/viteză/pauze schimbate invalidează timpii afectați; rezoluția/fontul/culoarea nu invalidează alinierea.

### A7. Scene, mișcare și assets AI

Scena este asociată pasajului și intervalului audio, nu doar unei durate arbitrare. `scenes.json` păstrează ID, pasaje ancoră, interval, vizual, focală, mișcare, tranziție și ajustări pe profile. Acceptă imagine integrală, imagini pe scene, imagini și clipuri combinate, opțional povestitor/avatar grafic. Imaginile utilizatorului sunt prima sursă. Asocierea poate fi explicită sau propusă din text/metadate; citirea numelor fișierelor nu este recunoaștere vizuală. Planurile automate sunt inspectabile/editabile. Verifică acoperirea întregii narațiuni și lipsa golurilor neintenționate. Avertizează pentru imagini lipsă, rezoluție mică și clip insuficient; fără umplere discretă cu imagini irelevante.

Animația locală obligatorie include deplasare lentă, apropiere/depărtare, tranziții discrete și apariție de text/elemente grafice; poate folosi FFmpeg zoompan/xfade [S1]. Mișcarea urmează scena; subtitrările rămân stabile/lizibile. Viteză, intensitate și tranziții configurabile. Mișcarea unei camere pe o imagine nu este scenă AI cu acțiune nouă. Avatarul simplu poate fi asset opțional; lip-sync realist și clonare de identitate nu sunt implicit incluse.

Generarea AI este separată de randare: modelul produce un fișier local aprobat, tratat apoi ca orice asset. Înainte de backend verifică CPU/RAM, GPU/VRAM vizibile WSL, disc, licențe, acces public fără cont și test real pe hardware. Nu instala drivere Windows/CUDA și nu descărca modele mari automat. Wan2.1 [S8] este candidat, nu alegere de producție validată; Apache-2.0 publicat nu transformă cerințele/benchmark-urile externe în măsurători locale. Dacă hardware-ul nu permite generare utilă, restul funcționează complet; AI este neinstalat/blocat, fără înlocuitor plătit. Textul din thumbnail/video se desenează cu renderer, nu prin litere generate de model. Păstrează prompt, model/revizie, seed dacă există, parametri și aprobare. Nu executa comenzi/cod propuse de model.

### A8. Titluri

Funcția rulează separat înainte/după montaj, fără voce nouă. Pentru fiecare material generează până la 3–5 variante relevante dacă sursa permite variante distincte. Folosește întregul material; pentru fragment numai fragmentul. Păstrează numele, anii și afirmațiile susținute, fără promisiuni, concluzii sau senzaționalism absent din sursă. Permite manual, selecție și blocare aprobată; titlul video și textul scurt thumbnail sunt separate. Titlurile părintelui nu se copiază automat tuturor fragmentelor; compilația are titlu bazat pe conținutul reunit.

Baza CPU fără model selectează extractiv din capitole, propoziții-cheie și sintagme, cu clasare simplă deterministă, deduplicare și limite configurabile. Nu se reduce la redenumirea fișierului sau „Partea 1”. Dacă nu sunt propuneri bune, marchează editarea necesară; fără pretenție de creativitate lingvistică. Datele includ candidate_id, title, thumbnail_text, pasaje sursă, backend, versiune și suggested/selected/approved.

LLM local opțional: Qwen3-4B-GGUF și llama.cpp CLI cu revizii fixate și fișiere locale [S6,S7]. Apache-2.0 pentru model și posibilitatea CPU justifică evaluarea, nu garantează româna sau timpul local. Instalare/descărcare explicită, limite memorie/timp, probe românești. Fără server/descărcare la render/fallback tăcut când backend-ul cerut lipsește. Pentru texte lungi, selecție sau analiză ierarhică cu referințe; nu trunchia la primele paragrafe pretinzând analiză integrală.

### A9. Thumbnail-uri

Sunt prezentări separate asociate materialului, nu obligatoriu primul cadru. Legătura cu vocea se face prin textul rostit și scene/intervale. Pentru audio cu text cunoscut nu este necesară transcriere suplimentară. Nu declara analiză de emoții fără funcție testată.

Moduri obligatorii: imagine aleasă + text/stil local; scenă/cadru reprezentativ asociat pasajului, nu primul cadru implicit; copertă grafică din culori/forme când nu există imagine potrivită, explicit ne-AI. Fundal AI eventual prin extensia opțională. Oferă câteva variante reale de compoziție, nu schimbări arbitrare de culoare. Fiecare are vizual/focală/text scurt asociat titlului, editabil.

Export PNG/JPEG cu dimensiuni independente/configurabile. Compoziție 16:9 și 9:16 fără crop orb. Stil constant în serie, conținut specific părții. Diacritice, contrast/contur/fundal, margini, măsurare reală a textului. Font minim și control overflow; cere editare/altă variantă, fără ascundere sau micșorare nelimitată. JSON alături cu sursă vizuală, interval, text, profil, setări. Thumbnail independent de encodarea întregului video. Fără imagini descărcate automat și fără ștergere de watermark-uri terțe. Pillow/ImageDraw este baza verificabilă propusă [S5].

### A10. Împărțire

Intrări distincte:

- A, text înainte de sinteză: capitole/paragrafe/limite explicite; fiecare parte folosește TTS actual; durata pre-sinteză este estimare.
- B, audio/video cu text și aliniere: extrage intervale existente, fără resinteză numai pentru split.
- C, audio/video fără text: permite temporal; semantică numai cu transcript furnizat sau ASR local explicit, fără text inventat.

| Metodă | Regulă |
|---|---|
| Capitole/paragrafe | Limite explicite/structură |
| Număr părți | Echilibrare fără ruperea inutilă a ideilor |
| Durată-țintă | Aproximativ X secunde/minute, ajustat la limită sigură |
| Manuală | Intervalele utilizatorului |
| Semantică | Propuneri după idei, pentru revizuire |

Capitolele/paragrafele nu sunt înțelegere AI. Semantica este distinctă, cere backend testat sau plan manual aprobat. Separă partition, integral fără goluri/suprapuneri, de extract, selecție cu omisiuni/repetări intenționate raportate. Pentru țintă preferă final de propoziție/pauză verificată. 60 s nu înseamnă 60.000 s garantat. La maxim strict respectă-l numai cu limite sigure; altfel conflict explicit, fără tăiere discretă de cuvinte/text.

Fiecare parte are ID stabil, sursă/interval, text propriu, referință/audio derivat, aliniere rebazată la zero, scene adaptate, titlu, thumbnail și exporturi. Toate opțiunile anterioare se pot activa independent: imagine, scene, clipuri, animații, subtitrări, profile și voce asociată. Setări comune moștenite și suprascrieri per parte. Întâi split-plan.json inspectabil cu limite/durate/pasaje/avertismente; aplicare explicită sau batch documentat, fără întrebare interactivă obligatorie.

La frontiere păstrează eșantioanele și vorbirea integrală; nu dubla cuvinte/pauze/scene; regrupează subtitrările din cuvintele părții; nu lăsa într-un cue cuvinte care nu mai sunt rostite; adaptează scene/mișcare și păstrează maparea către părinte.

### A11. Reunire

Acceptă materiale interne, texte, audio și video local, în ordine explicită, nu ordinea unui wildcard sau sortare lexicografică a numerelor.

Varianta internă preferată construiește cronologie nouă din surse/intervale păstrate, reutilizează audio/scene/assets și recalculează offseturi subtitrări/capitole. Nu lipește obligatoriu MP4 comprimate când există surse curate. Păstrează vocile; uniformizarea prin re-narare cere opțiune separată, text și avertizare, nu este implicită. Compilația are titlu/thumbnail proprii; titlurile părților pot rămâne metadate/capitole, fără intro-uri rostite automate.

La externe inspectează codec, dimensiuni, fps, orientare, audio și durată. Convertește doar în intermediari separați la profil final. Concat direct are restricții [S2]; nu folosi `-c copy` pentru orice listă MP4. Copiere numai după compatibilitate și rezultat verificate; pentru tăieturi precise tratează cadre/keyframe-uri. Subtitrările arse nu devin editabile; repoziționarea curată cere surse curate/reconstrucție; limitele se raportează.

Implicit fără suprapunerea vocilor. Tranzițiile vizuale pot ține/adăuga cadre fără scurtarea narațiunii. Pauze/intro/tranziții care schimbă durata intră în cronologia comună; offseturi din montaj real, nu durate de containere aproximative. Fără crossfade automat peste cuvinte sau normalizare repetată; normalizarea compilației configurabilă, măsurată final.

Split→merge trebuie să reconstruiască ordinea/conținutul dacă nu sunt părți eliminate/modificate sau efecte temporale noi. Pe sursă PCM, fără resampling/efecte, păstrează exact eșantioanele. Pe MP3/MP4 reencodate nu promite identitate binară; verifică intervale, conținut temporal și întârzieri codec.

### A12. Combinare și loturi

Ordine de rezolvare: implicite → proiect media → material → fragment/scenă → CLI. Batch permite integral cu ambele profile/subtitrare/thumbnail; split cu titluri/coperți proprii; părți unele fixe, altele scene/animații; compilație din părți selectate apoi export vertical/orizontal; regenerare exclusivă de titluri/subtitrări stilizate/thumbnail-uri. Funcțiile rulează separat și combinat. Incompatibilitățile reale se validează înainte de randare, cu lipsuri precise. Nu produce combinații carteziene necerute; numai variante/profile selectate.

### A13. Dependențe, eficiență și siguranță

Izolare propusă: `.venv` audio, `.venv-media` orchestration/compoziție/teste, `.venv-align` pentru aliniere, modele/executabile AI separate. Numele nu sunt obligatorii dacă separarea efectivă există; lockfile-uri separate. Doctor verifică CPU/RAM/disc, FFmpeg/ffprobe efective, H.264/AAC/filtre/fonturi/modele și GPU vizibil. Lipsa GPU nu este eroare pentru CPU. Dacă audio FFmpeg nu are libass sau altă facilitate, instalează explicit build media separat; nu înlocui `.tools/ffmpeg` și nu schimba PATH audio automat. Pentru modele păstrează proveniență/revizie/dimensiuni/hash/licență; codul nu acoperă automat toate greutățile/datele.

| Modificare | Reutilizare urmărită |
|---|---|
| Thumbnail | Audio, aliniere, video existent |
| Font subtitrare | Audio și aliniere |
| Rezoluție | Audio, aliniere, structura scenelor |
| Imagine scenă | Audio, aliniere, alte assets |
| Titlu | Audio și aliniere; video dacă titlul nu era desenat |
| Ordine părți | Assets și alinieri locale; offseturi noi |
| Text/viteză | Refacere audio și alinieri afectate |
| Pauză între părți | Audio de bază; cronologie/exporturi noi |

Imaginea schimbată poate cere reencodare MP4; obiectivul este evitarea recalculării elementelor neafectate. Prioritizează cache audio/aliniere/titluri/assets. Cache secvențe video doar dacă este corect și măsurabil. Cheile includ conținut, versiuni, model, fonturi, parametri/profile, nu doar căi/mtime. Scriere atomică/temporare distincte/manifest actualizat/reluare; .part nu este rezultat valid. Eșecul nu șterge exportul valid anterior. Flux de pe disc și paralelism limitat, fără film integral în RAM sau toate modelele grele simultan.

Validează date/căi, fără text interpolat în shell. Argumente subprocess separate și escapare FFmpeg corectă. Nu executa instrucțiuni din transcript/metadate/ieșiri LLM. Offline fără rețea/fallback cloud. Orice funcție cerută dar neexecutată este raportată; lot incomplet nu înseamnă succes total.

### A14. CLI propus, nu contract implementat automat

| Comandă dorită | Rol |
|---|---|
| ./media doctor | Diagnostic fără descărcări |
| ./media init | Import material |
| ./media align | Aliniere text/audio |
| ./media subtitles | Export/stil |
| ./media scenes | Import/propunere scene |
| ./media titles | Variante/selecție |
| ./media thumbnail | Numai thumbnail |
| ./media split | Plan/aplicare split |
| ./media merge | Plan/aplicare reunire |
| ./media render | Profile selectate |
| ./media batch | Lot |
| ./media verify | Export și consistență |

Exemple de experiență dorită în specificație, care cer verificarea sintaxei reale înainte de utilizare:

```text
./media init --id material-001 --text input/text.txt --audio output/text.mp3
./media render material-001 --image assets/imagini/coperta.jpg --profiles landscape,portrait --subtitles classic
./media titles material-001 --backend extractive --candidates 5
./media thumbnail material-001 --profiles landscape,portrait
./media split material-001 --target-seconds 90 --plan-only
./media merge --id compilatie --materials part-001,part-002 --plan-only
```

Acest bloc este specificație istorică, **nu comenzi testate**: de exemplu CLI actual nu cere/acceptă `titles --backend extractive`, split planifică implicit și merge primește ID-uri ca argumente separate. README publică interfața efectiv verificată. Cerințe transversale: help, logare lizibilă, raport JSON, force explicit, planificare fără randare, reluare documentată; modele prin comenzi separate; fără interactivitate obligatorie în batch, selecții prin plan/config.

### A15. Structura propusă

```text
rec/
  tts
  media
  media.json
  src/rec_media/
  requirements-media.in
  requirements-media.lock
  requirements-align.lock
  assets/imagini/
  assets/clipuri/
  assets/stiluri/
  materials/material-001/material.json
  materials/material-001/scenes.json
  materials/material-001/titles.json
  materials/material-001/alignment.json
  output/media/material-001/landscape/video.mp4
  output/media/material-001/portrait/video.mp4
  output/media/material-001/thumbnails/
  output/media/material-001/subtitles/
  output/media/material-001/report.json
  work/media/cache/
  work/media/runs/
  work/media/plans/
  tests/media/
  docs/PLAN_EXTINDERE_MEDIA_REC.md
  README.md
  TEST_RESULTS.md
  THIRD_PARTY_NOTICES.md
```

Integrează în structura reală, fără mutarea directoarelor audio; inspectează numele deja existente. Manifestele private, assets personale și rezultate nu intră implicit în Git; exemplele sunt sintetice. Un lock de aliniere există numai după alegerea/instalarea backend-ului. Amplasarea rapoartelor reale poate fi per export, documentată separat.

### A16. Etape și criterii de trecere

F0: inventar/Git/hash/comenzi/regresii în directoare izolate, capabilități hardware/FFmpeg, fără reinstalare preventivă.

F1: manifest minim, import text/audio/imagine, imagine fixă, landscape/portrait/custom, export și verificare; aceeași voce fără sinteză nouă.

F2: model local izolat, probe românești, SRT/ASS/clasic/highlight; scroll în aceeași arhitectură, marcat separat până la test real.

F3: scene/schimbare imagini/animații deterministe/titluri extractive și manuale/copertă locală, funcții separat; LLM doar instalat explicit și testat.

F4: fragmente materiale complete, planuri/offseturi/compilații/profile/probe split→merge; toate funcțiile F1–F3 și pe derivate.

F5: după hardware/resurse aprobate, AI opțional pentru LLM/semantică/imagini/clipuri; fiecare backend cu test și statut separat. Nu blochează F1–F4.

După fiecare etapă: teste noi/regresii relevante/documentație; un CLI sau stub nu înseamnă etapă implementată.

### A17. Acceptare și statusuri

| Test | Criteriu verificabil |
|---|---|
| Regresie audio | Comenzi/teste funcționale; originale cu hash neschimbat |
| Imagine/audio | MP4 complet, ultimul cuvânt păstrat, fără final negru accidental |
| Profile | 1920×1080/1080×1920 exacte, custom validat, fără deformare |
| Diacritice | Ș/Ț/Ă/Â/Î și lowercase vizibile, fără lipsuri |
| Subtitrări | Ordine/durate/limite/acoperire; început/mijloc/final/pauze |
| Afișat/rostit | Numere/sigle mapate fără pierderi |
| Highlight/scroll | Aliniere reală; fără timpi inventați pentru nealinieri |
| Scene | Acoperire/ancore/lipsuri raportate |
| Thumbnail | Dimensiuni/casete/compoziție pe profil și parte |
| Titluri | Context propriu, selecție păstrată, surse |
| Partition | Fără goluri/suprapuneri, tot textul/intervalele contabilizate |
| Extract | Omisiuni/repetări intenționate consemnate |
| Split→merge PCM | Eșantioane identice fără efecte/resampling |
| Merge | Ordine/offseturi, fără voce dublată la tranziții |
| Surse mixte | Formate/fps/audio explicite, fără compatibilitate presupusă |
| Cache | Font/imagine fără resinteză |
| Întrerupere | Reluare fără pierderea rezultatelor valide |
| Offline | Modele locale și rețea blocată când mediul permite |
| Export | ffprobe și decodare A/V completă, fluxuri/durate conforme |
| Căi dificile | Spații/apostrof/diacritice fără shell/filtergraph defect |
| Lot incomplet | Eșecuri nominalizate, fără succes global fals |

Toleranța tehnică A/V inițială este maximum 100 ms după decodare și contabilizarea întârzierilor cunoscute; documentează măsurătoarea, fără confundare cu precizia cuvintelor. Pentru subtitrări pregătește probă românească cu ancore manuale și raportează diferențe; ținta propusă pentru classic este maximum 200 ms la limitele inspectate, fără garanție pe toate cuvintele. Extrage cadre început/mijloc/final/tranziții/text lung. Tehnicul nu confirmă titlu bun, imagine relevantă sau voce naturală.

Statusuri separate: technical_status, alignment_status, visual_review_status, listening_status, editorial_review_status. Fără ascultare/vedere reală păstrează not_reviewed/not_listened, nu passed.

### A18. Documentație și predare

README este intrarea principală: ce funcționează acum, instalare reală, audio/media, comenzi testate, diagnostic/linkuri. Planul canonic conține cerințe/decizii/stări/diferențe/restanțe. TEST_RESULTS păstrează date, versiuni/commit dacă există, comenzi, artefacte, eșecuri și verificări omise. THIRD_PARTY_NOTICES separă cod/modele/assets/fonturi/proveniență/licențe. CHANGELOG numai dacă există/devine util. AGENTS are regula scurtă de întreținere. Completează echivalentele existente, fără duplicate contradictorii.

Orice schimbare CLI/config/schema/dependențe/model/comportament cere exemple și explicații actualizate, matrice actualizată, verificări relevante cu rezultate efective, migrare/compatibilitate unde schema se schimbă și păstrarea istoricului. Matricea folosește planned, implemented_not_tested, tested, blocked, optional_not_installed cu dată/dovadă pentru tested; în evidența curentă se oferă și etichetele românești implementată/verificată/parțială/neimplementată/blocată. Date tehnice UTC cu fus explicit; Europe/Bucharest poate fi afișat separat, fără interpretarea run_id UTC ca oră locală. Nu copia text privat în README/Git.

Predare: implementat/opțional, schimbat/intact, comenzi exacte testate per funcție, artefacte/rapoarte, limite/blocaje/comenzi numai utilizator, Markdown/secțiuni afectate. Dacă sudo nu este disponibil, oferă comanda și motivul; nu cere parole și nu pretinde execuție.

### A19. Surse și delimitare

Profilele, pragurile și arhitectura sunt cerințe de produs, nu rezultate de benchmark. Baza audio provine din PLAN_IMPLEMENTARE_REC.md, relatările Pasted text(20261016-074030).txt și Pasted text(20261016-080637).txt și raportul ulterior al rulării 20261016T090507-5f8a96d4. Aceste relatări trebuie confruntate cu fișierele reale; planul vechi nu are prioritate asupra comportamentului verificat fără decizie explicită.

Sursele publice S1–S8, enumerate cu legături în secțiunea 19, fundamentează doar capabilități externe: FFmpeg filters/concat, WhisperX alignment, Romanian Wav2Vec2, Pillow ImageDraw, Qwen3-4B-GGUF/licență, llama.cpp și Wan2.1. Nu dovedesc instalarea locală. Nu descărca implicit main/master în producție; după selecție/test fixează versiuni/revizii/hash-uri/surse. Licența codului nu dovedește licența tuturor greutăților/datelor.

### A20. Checklist final

Audio protejat și retestat; profile landscape/portrait/custom; video fix independent; subtitrări reale și exporturi separate; scene/animații pe cronologia comună; titluri relevante/editabile/corecte per material; thumbnail fără API sau video obligatoriu; aceleași funcții pe fiecare fragment; reunire care păstrează conținut și temporizări; loturi/cache/reluare testate; AI opțional cu cerințe/stare reale; comenzi README verificate; plan/rezultate/licențe/AGENTS actualizate. Nicio bifă globală nu se deduce doar dintr-o demonstrație.

### Închiderea etapei pe materialul real — 2026-10-16 UTC

Dovezi finale: `work/media/real-alignment-audit/acceptance.json`, `media-tests-verified.xml` (27), `audio-unit-regression.xml` (38), `batch-final-result.json` (11/11), `batch-final-resume.json` (11/11 refolosite), `offline-real-current-result.json`, `recovery-real-result.json`. Nouă MP4-uri, nouă SRT/ASS/alinieri și nouă thumbnail-uri; maximum 24,082 ms A/V, toate decodate complet. Acoperire SRT exactă, PCM split→merge identic, 441/441 originale neschimbate. `not_listened`, precizie manuală nemăsurată, vizual numai cadre selectate; F2 rămâne parțial din aceste motive. Restanța de recuperare în etapa inițială a WAV-ului analizei rămâne explicită. Matricea și cerințele A1–A20 nu sunt înlocuite de acest rezultat.

### Etapa producție, split text — 2026-10-16 UTC

Implementat `split-text` (N, durată estimată, capitole/delimitator, intervale manuale,
propunere lexicală pe paragrafe) și `merge-text` fără pierderea octeților.
Maparea păstrează offseturi Unicode/octet și hash-uri; nu este aliniere acustică.
Status provizoriu: implemented + not fully verified, până la probele etapei producție.

### Etapa producție, review/recovery — 2026-10-16 UTC

Implementate raportul CTC grupat și deciziile accepted/rejected/corrected cu cheie
pe revizia exactă, plus `align --segments`. Scorurile originale rămân vizibile.
Identitatea inferenței CTC este păstrată: refactorizarea recuperării nu invalidează
cele 30 checkpointuri deja verificate. Pregătirea atomică WAV are receipt hash și
încercări distincte; statutul rămâne implemented + not fully verified până la
întreruperea reală consemnată în rezultatele acestei etape.

### Etapa producție, scene/titluri/preseturi — 2026-10-16 UTC

Extensii aditive: `scene-plan` cu assets explicite/folder, intervale aliniate și
mapping text; descriere și approval_status în importul existent; rejected blochează
render. Titlurile lungi pot oferi extrase contigue cu sursă, iar regenerarea
propunerilor păstrează selecția aprobată. Aliasurile youtube-landscape și
shorts-portrait reutilizează profilele existente. Probele etapei sunt consemnate
mai jos; nu se atribuie semantică AI imaginilor manuale.

### Etapa producție, orchestrare — 2026-10-16 UTC

Workflow aditiv peste CLI, cu etape activate/dezactivate, dependențe, only/rerun,
checkpointuri hash și loguri. Acceptă toate etapele locale media și procesarea
TTS existentă; fără instalări implicite sau recursie workflow/batch. Invalidarea
externă este explicită prin inputs/outputs în plan, nu o presupusă dependență
ascunsă. `synthesize-parts` planifică implicit și aplică explicit numai părțile noi.
Fluxurile existente rămân publice. Statusul testat urmează în evidența finală.

### Etapa producție, AI opțional — 2026-10-16 UTC

BLOCKED pentru test AI imagine/video în WSL curent: ~3,82 GiB RAM, GPU neexpus
prin dxg/dri. Windows are Intel UHD și ~15,73 GiB RAM; nu se afirmă absența GPU.
Backend imagine ales pentru evaluare viitoare: stable-diffusion.cpp CPU (MIT),
SD 1.5 cu licență separată OpenRAIL-M. `image-plan` este numai contract verificabil,
PARTIAL ca integrare, fără instalare/inferență. AI video/LLM rămân TODO/opționale.
Acest blocaj nu afectează montajul CPU și nici scenele furnizate manual.

## Recuperarea producției — 2026-10-16 UTC

Această matrice actualizează statusurile curente; tabelele de mai sus păstrează
istoricul etapelor. DONE se referă strict la proba citată, nu la ascultare sau
aprobare editorială. Incidentul și checkpointurile sunt în
`work/media/production-20261016/incident-recovery.json`.

| Funcție / verificare | Status curent | Dovadă / limită |
|---|---|---|
| Protecție audio/surse/modele/cache | DONE | 553 hash-uri neschimbate la recuperare; verificare finală separată. |
| Import/material/cronologie comună | DONE | Materialele reale și exporturile istorice păstrate, fără reconstruire. |
| Imagine fixă și profile landscape/portrait/custom | DONE | Acceptanța reală anterioară; nu rerandată preventiv. |
| Split text N/durată/capitole/delimitator/manual/lexical | DONE | Teste producție și split text real; duratele sunt estimări, nu timpi acustici. |
| Merge text exact Unicode/octet | DONE | Originalul și text-reunited.txt sunt identice octet cu octet. |
| Sinteză separată de părți | PARTIAL | Planificare și --apply implementate; sinteza reală pe părțile private nu a fost necesară/testată aici. |
| Aliniere CTC română offline | PARTIAL | Backend real verificat; 170 scoruri reduse și precizie manuală nemăsurată. |
| Review CTC accepted/rejected/corrected | DONE | Teste cu fixture și raport real de 170; nicio decizie editorială automată. |
| Rerulare CTC --segments | DONE | selective-alignment-result.json: segment 1 recalculat, segment 0 cu hash/mtime identice, apoi cache_hit. |
| Recovery scriere PCM/WAV inițială și corupție analiză | DONE | recovery-real-result.json istoric passed; receipt real reutilizat în sesiunea nouă. |
| SRT/ASS/classic și diacritice | DONE tehnic | Exporturi reale istorice, verificare nouă pe producție separată. Sincronizare auditivă nerevizuită. |
| Highlight/scroll continuu | PARTIAL | Moduri verificate tehnic pe fixture; scroll discret, fără ascultare integrală. |
| Scene manuale / plan / descrieri / aprobări | DONE | Contract și scene de producție; asocierea semantică nu este inferată. |
| Montaj integral cu scene și ambele profile | DONE tehnic | 2026-10-17 UTC: ambele MP4 complete, scene originale reutilizate; final-acceptance.json. Review integral separat. |
| Zoom/pan/crossfade/titlu | DONE pe fixture | Randare și probe tehnice existente; montajul lung verificat separat. |
| Titluri extractive/manuale și selecție aprobată | DONE tehnic | Teste; selecția aprobată este păstrată, relevanța editorială nerevizuită. |
| Thumbnail scenă/imagine/grafic PNG/JPEG | DONE tehnic | Layout/dimensiuni/hash-uri; nu aprobare editorială. |
| Două fragmente + compilație cu scene/profile | DONE tehnic | 2026-10-17 UTC: 6 MP4 derivate, SRT/ASS/thumbnail per profil; PCM split→merge identic. |
| Split temporal și merge intern PCM exact | DONE | Dovada reală istorică; proba noii compilații verificată separat. |
| Continuitate fază mișcare după split | TODO | Mișcarea se reia local; limită vizibilă în history. |
| Maxim strict temporal / conflicte de limite | DONE tehnic | --max-seconds în eșantioane, fără limite inventate în cuvinte; teste și strict-max-real-plan.json. Durata textului înainte de TTS rămâne estimată. |
| Merge extern cu resampling/mix fps | PARTIAL | Rate identice acceptate; conversiile trebuie pregătite explicit. |
| Pauze/intro/normalizare compilație | TODO | Merge actual fără efecte și fără suprapunerea vocii. |
| Batch titles/thumbnail/subtitles/render | DONE pentru subset | Loturi istorice complete și reluare verificată. |
| Orchestrare import/split/merge/align/TTS | DONE pentru CLI local | Teste workflow; inputs/outputs explicite, fără instalări. |
| Selecție workflow și păstrare succes anterior la retry eșuat | DONE | regression-recovered.xml; --only raportează partial/incomplete; previous_success rămâne istoric. |
| Resume video | DONE pe regresie și producție | 2026-10-17 UTC: 8/8 MP4, scene originale hash/mtime identice; publicare atomică și part-uri istorice păstrate. Perechea goală de adoptare reparată explicit, fără rerandare. |
| Avatar/logo configurabil | TODO | Nu există integrare în renderer. |
| Stil ASS complet configurabil | PARTIAL | Setările publice existente sunt validate; nu toate cerințele planului. |
| Instalare media secundară curată cu hash-uri | TODO | Lock media observat local, fără instalare nouă preventivă. |
| image-plan / identitate / lipsă execuție implicită | DONE pentru contract | Test cu fișiere sintetice și hash schimbat, fără model AI. |
| Backend imagine AI executabil integrat | PARTIAL | Numai contract; fără runner/inferență validată. |
| Test imagine/video AI pe hardware WSL actual | BLOCKED | Resursele WSL/Windows documentate separat; fără instalări grele. |
| Backend LLM și video AI | TODO, opțional | Neinstalate; nu blochează baza CPU. |
| Vizionare integrală / ascultare / ancore manuale | TODO ca review | Nu sunt deduse din decodarea completă. |

Reluarea a păstrat run-ul și fișierele trunchiate. Niciun job vechi nu mai exista
pe gazdă după noul boot WSL. Sesiunea precedentă nu are un diagnostic final care
să lege mesajul terminalului exit 1 de render. Există un exit 1 auxiliar anterior
la citirea unui fișier cgroup inexistent; asocierea lui cu închiderea terminalului
nu este demonstrată. Nu se declară nici eroare globală, nici cauză exactă inventată.

Incident suplimentar în recuperare: continuarea temporară a primit SIGTERM/143,
cu landscape complet valid și portrait nepublicat. Expeditorul nu este dovedit.
Continuarea durabilă, detașată și cu lock propriu, este documentată în README și
TEST_RESULTS; nu echivalează cu reluare per scenă. Rootul audio și originalele
rămân protejate. Extensia maximului strict temporal a trecut regresia de 74 teste;
planul real este numai o probă de planificare, fără aplicare pe sursele private.

Corecție F3 la 20:46 UTC: tpad după zoompan/trim/setpts necesita FPS explicit.
Proba 90+6 emitea 91 cadre; acum emite 96, cu amestec gradual al pixelilor
verificat prin test. Global A/V passed nu demonstra paddingul crossfade corect.
`render --output-root` scrie variantele corectate în `output/media/scenes-v2/`,
fără suprascrierea exporturilor precedente. Workerul vechi a fost oprit explicit,
lockurile confirmate libere, apoi s-a pornit unul singur, PID 7833. Regresie:
75 passed; statusul randării lungi rămâne separat până la acceptanță.


### Recuperare per scenă, run 9f8ed5ce64054935b51da76f4d686db7 — 2026-10-16 UTC

Implementat `render --resume-run` cu receipts pentru scene și master PCM,
validarea configurației efective, hash/profil/fps/cadre și decodare integrală.
Scenele FFV1 complete sunt reutilizate; MP4 se finalizează într-un temporar nou,
se verifică și se publică atomic. Temporarele vechi rămân dovezi private.
Diagnostic final persistent: comandă/cwd/PID/stderr/returncode/RSS observat.
Decodarea fiecărui input final are fire limitate explicit.

Regresia întrerupe finalizarea după scene complete, lasă .part de 48 bytes,
reia fără rerandare (hash/mtime identice), verifică publicarea atomică și decodează
MP4 final. Teste izolate: `recovery-scenes/all-regression.xml`.
Scenele reale validate: 6.950, 6.765, 6.962 cadre, FFV1 HD 30 fps; toate reutilizabile.
Migrarea legacy este o operație de audit explicită, nu fallback automat.
Prima încercare a migrării a refuzat configurația incompletă fără compoziția
moștenită; receipts corectate, fără regenerare. Incidentul istoric de terminal
nu are returncode/stderr final păstrat: cauza exactă rămâne nedeterminată;
bootul WSL nou este confirmat. Nu se atribuie OOM pe baza probelor artificiale.

Ordinea acceptării: integral landscape PASSED înainte de portrait, apoi două
fragmente și compilația pe ambele profile. Statusul rezultatelor reale rămâne
separat de regresie până la acceptanța din TEST_RESULTS. Reluare privată:
`python3 work/media/production-20261016/recovery-scenes/continue-production.py`.
Review auditiv/editorial și cele 170 scoruri reduse rămân nerevizuite.


### Acceptanță producție și recuperare închisă — 2026-10-17 UTC

Dovadă: `work/media/production-20261016/recovery-scenes/final-acceptance.json`,
**05:58:06 UTC**, media 0.1.0: **8/8 MP4 PASSED tehnic**, 8 exporturi SRT/ASS/
aliniere și 8 thumbnail-uri. Toate cele 553 fișiere protejate sunt neschimbate.
893 + 931 = 1.824 unități și 79 + 91 = 170 scoruri reduse sunt păstrate;
split→merge păstrează exact 15.188.520 eșantioane PCM. Max A/V 17,642 ms.

Cele trei scene originale landscape sunt reutilizate, cu hash/mtime identice și
6.950 / 6.765 / 6.962 cadre decodate integral. La începutul acestei reluări erau
cinci exporturi publicate; au fost reverificate, apoi s-au finalizat fragmentul 2
portrait și cele două profile ale compilației. Nu s-a regenerat nicio scenă
validă în această reluare. Cele șapte variante intermediare generate în sesiunea
precedentă sunt enumerate separat în raport; nu sunt randări noi din 17 octombrie.

Exit 1 observat și localizat în recuperare: citire Python a unui receipt gol,
pereche cu un MKV de 0 bytes din adoptarea întreruptă a compilației portrait.
Perechea a fost păstrată și înlocuită numai după audit, prin copierea unei scene
valide cu contract identic; nu prin generarea pixelilor. Helperul privat de
adoptare refuză acum existența goală/incompatibilă și publică noile copii numai
după fsync/hash. Fișierele istorice `.part.mp4` de 48 și 1.048.624 bytes rămân
invalide și păstrate. Cauza închiderii terminalului precedent rămâne nedeterminată:
ultima comandă seed nu are rezultat terminal salvat, iar oprirea Windows este
ulterioară. Diagnosticele și cronologia sunt în TEST_RESULTS și incident-20261017.json.

Regresia existentă a fost întărită cu antetul real de 48 bytes și păstrarea
hash-ului part-ului: 3 teste recovery trecute din nou în copie izolată. Totalul
larg de 79 este probă istorică separată, nu rerulare nouă. Review-ul vizual este
limitat la cadre selectate; ascultarea și aprobarea editorială rămân neefectuate.

Restanță închisă suplimentar: ancorele și intervalele Unicode ale scenelor
fragmentelor/compilației au fost rebazate pe propriul text cunoscut, fără schimbări
în audio, aliniere, pixeli sau durate. Migrarea are jurnal reluabil și copii
înainte/după în `metadata-migration/`; fixture-ul a verificat două aplicări
idempotente cu MP4 și hash/mtime MKV identice. Pentru relansare, workerul verifică
subtitrările existente prin conținutul așteptat din aliniere/stil/font, păstrând
fișierele; modificarea exclusivă a metadatelor scenei nu justifică suprascrierea lor.

Comanda normală de continuare rămâne cea din README. `runner-state.json` și
`completion.json` sunt complete; vechiul workflow și semnăturile lui rămân
istoric, fără declararea retroactivă a executării etapelor sale. Matricea curentă
păstrează PARTIAL pentru CTC/review, sinteza părților, highlight/scroll, mix extern,
stil ASS și integrarea AI; TODO pentru continuitatea mișcării, pauze/intro/
normalizare, avatar/logo, instalare media curată și review integral; BLOCKED
pentru probele AI grele conform auditului de resurse anterior. Nu s-au instalat
modele sau dependențe și nu s-a resintetizat audio-ul privat.

## ASSET DISCOVERY, MEDIA LIBRARY ȘI SCENE EDITING

Etapă adăugată la 2026-10-17 UTC, peste baza verificată de 8/8 MP4. Acesta este
planul canonic al etapei; nu înlocuiește matricea și restanțele precedente.
Stări: TODO, IN_PROGRESS, DONE (numai cu probă), PARTIAL, BLOCKED.
Recovery-ul închis nu se reexecută preventiv; regresia se verifică numai unde
noua integrare atinge rendererul/cache-ul. Audio-ul, textul sursă, Piper și
alinierea existente rămân protejate. Probele reale folosesc exporturi noi.

### Contract și arhitectură

Providerii de discovery sunt separați de renderer: Wikimedia Commons, Openverse,
Pexels opțional după verificarea termenilor/API. Rețeaua se folosește numai în
search/download explicit; nu scraping Google/Bing/YouTube și nu cloud implicit.
Biblioteca este un index local cu identități stabile, obiecte adresate prin SHA-256,
metadate de căutare/provenance și istoric de utilizare. Mod implicit ASSISTED;
MANUAL selectează explicit, AUTO clasează și explică alegerea, păstrând alternative.
Query-urile RO/EN provin din contextul scenei, cu persoane/locuri/evenimente/
perioade/organizații/obiecte/teme propuse, fără pretenție de înțelegere perfectă.
Minimum trei candidați unde sursele oferă; lipsurile se raportează, nu se inventează.

Schema rămâne compatibilă cu scenele existente. Extensia aditivă include scene_id,
text/context, start/end în eșantioane, selected_asset (type, local_path, provider,
source_url, creator, license, license_url, attribution, checksum, downloaded_at),
video (source_start/source_end în secunde, audio_enabled=false), visual (fit,
focal_point, crop, zoom, pan, motion, transition, overlay), status
proposed/approved/rejected, alternatives și profile_overrides landscape/portrait/
custom. previous_selection/current_selection permit undo fără redownload.
Aliasurile legacy id/anchor/asset/kind/focal/profiles rămân lizibile; nu se migrează
în masă materialele validate. Câmpurile editoriale nu invalidează singure pixelii.

Asset-urile online cer provenance completă. Licența nedeterminabilă este
LICENSE_UNKNOWN: exclusă din AUTO, fără aprobare implicită/publicare sigură;
selecția cere aprobare explicită. credits.json și CREDITS.md enumeră scenele,
asset-urile și attribution, inclusiv overrides și thumbnail. Split/merge păstrează
numai sursele relevante, provenance și attribution, fără audio nou.

Video folosește interval explicit source_start/source_end și audio extern mut.
Un clip prea scurt cere politică explicită: loop, freeze, asset alternativ,
secvență/combinare ori fallback imagine; nu loop universal implicit. Editarea
independentă acoperă asset/crop/fit/focal/zoom/pan/motion/transition/overlay,
poziționare subtitrări, durată vizuală și titlu. Schimbarea duratei vizuale nu
schimbă durata audio; cronologia trebuie să rămână acoperită fără goluri.

Rerandarea parțială extinde recovery-ul existent: amprente pe contractul real de
pixeli/timestampuri (asset hash, profil, crop/focal/motion/tranziție/padding,
overlay, subtitrări relevante, versiune/configurație relevantă). Scenele neafectate
cu receipts/hash/decodare valide sunt reutilizate; numai scena incompatibilă se
randează într-un temporar nou, păstrând intermediarul vechi, apoi se reasamblează,
verifică și publică MP4 atomic. Paddingul depinde de tranziția următoare și trebuie
invalidat explicit unde aceasta schimbă cadrele. Legacy scene_key rămâne valabil
pentru contractele legacy neschimbate; generatorul schimbat primește identitate nouă.

Download: URL/scheme/redirecturi verificate, limite de mărime/durată/rezoluție,
Content-Type și format real, decodare completă, fără nume externe ca destinație,
fără executabile/path traversal. Temporare unice, hash, fsync și publicare atomică;
incompletele nu intră în index. Dedup înainte de transfer când identitatea/hash-ul
sunt cunoscute; verificare checksum la reutilizare. Reluare HTTP numai dacă Range/
validatorii și mărimea totală permit verificare sigură; altfel încercare nouă,
păstrând diagnosticul. Ranking separat de retrieval: text, rezoluție, orientare,
aspect ratio, licență, durată, calitate, utilizări și preferințe explicite.
Evită repetarea vecină unde există alternative; override manual permis și jurnalizat.

### Matricea de implementare și acceptare a etapei

| ID | Cerință / probă | Stare inițială | Criteriu |
|---|---|---|---|
| AD00 | Plan canonic înainte de cod | DONE | Această secțiune; documentele obligatorii citite integral. |
| AD01 | Schema aditivă, manual/local/library/fallback | IN_PROGRESS | Compatibilitate legacy, validare și istoric selecție. |
| AD02 | Wikimedia Commons | TODO | Adapter/teste mock și căutare reală cu provenance. |
| AD03 | Openverse | TODO | Adapter/teste mock și probă reală; erori nominalizate. |
| AD04 | Pexels opțional | TODO | Termeni/API verificați; key numai prin mediu, fără secret în rapoarte. |
| AD05 | Query-uri RO/EN și entități/context | TODO | Propuneri inspectabile/editabile, fără traduceri inventate ca fapt. |
| AD06 | MANUAL/ASSISTED/AUTO și ranking | TODO | ASSISTED implicit; fără primul rezultat ales tacit. |
| AD07 | Candidați stabili/contact sheets/video previews | TODO | Minimum 3 unde există, licență/provider/dimensiuni/durată vizibile. |
| AD08 | Bibliotecă indexată/dedup/cache/usage | TODO | keywords/persons/places/events/period/tags/type/provider/license/orientation/width/height/duration/checksum. |
| AD09 | Provenance/unknown license/credits | TODO | Necunoscutele cer aprobare explicită, export credits JSON/Markdown. |
| AD10 | Video trim/muted/politici clip scurt | TODO | Probe loop/freeze/alternativă/secvență/fallback; vocea rămâne principală. |
| AD11 | Scene editing CLI/undo/overrides | TODO | List/inspect/alternatives/select/replace/remove/restore/interval/focal/motion/transition și controalele vizuale. |
| AD12 | Partial rerender peste recovery | TODO | Replace pe o scenă: celelalte hash/mtime/checkpoint identice; verify final. |
| AD13 | Landscape/portrait/custom independente | TODO | Asset/focal/crop diferite pe profil, fără crop central obligatoriu. |
| AD14 | Thumbnail din scene aprobate/provenance | TODO | Layout per profil și sursă/licență păstrate. |
| AD15 | Split/merge cu provenance/overrides | TODO | Attribution și selecții păstrate, numai scene relevante. |
| AD16 | Download safety/atomic/recovery | TODO | Corupție/MIME/URL/întrerupere/checksum/duplicat testate fără internet. |
| AD17 | Offline | TODO | Render/verify/split/merge/subtitles fără socket; alinierea locală existentă păstrată. |
| AD18 | AI local opțional | TODO | Audit CPU/RAM/GPU/VRAM WSL și Windows, dxg/nvidia/CUDA/DirectML reale; fără instalare grea implicită. |
| AD19 | Teste automate | TODO | Provider/parsing/search/download/selection/undo/provenance/trim/mute/overrides/partial/cache/offline. |
| AD20 | Probă reală minimum 3 scene | TODO | Query-uri/candidați/download/preview/select; ≥2 imagini diferite și video dacă utilizabil/licențiat. |
| AD21 | Export real landscape/portrait + replace | TODO | Destinație nouă, audio/aliniere neschimbate, verify și probe hash/mtime. |
| AD22 | scene-review.md | TODO | Timestamp/context/asset/preview/alternative/provider/source/creator/license/status; selecție prin ID. |
| AD23 | Documentație/predare | TODO | README/TEST_RESULTS/plan/AGENTS/THIRD_PARTY_NOTICES, comenzi reale, statusuri și git status. |

### Restanțe protejate

Review CTC și cele 170 scoruri reduse, highlight/scroll, stil ASS complet, mix
extern, listening/editorial review integral, continuitatea animației, avatar/logo,
pauze/intro/normalizare, instalare curată secundară și toate celelalte TODO/PARTIAL/
BLOCKED din matricea anterioară rămân active. Această etapă nu le declară rezolvate.
Rezultatele tehnice, vizuale, auditive și editoriale vor fi documentate separat,
cu UTC/run-id/hash-uri. Nu se face staging/commit/push/reset/clean sau curățare.


### Reluare efectivă — 2026-10-18 UTC — IN_PROGRESS

Auditul găsește providerii, biblioteca și CLI-ul deja implementate, cu regresie
istorică 104 passed/1 skipped. Matricea inițială de mai sus rămâne istoric;
acceptanța curentă se va centraliza după probe. Proba assets din 17 octombrie
s-a întrerupt înaintea primului MP4: run 3643b8e1d9e74ccf881468175ede943f,
numai .part MKV, fără receipt de scenă. Acesta se păstrează separat de producția
stabilă 8/8 și nu se adoptă automat.

Lucru autorizat: completarea preview-ului video cu mai multe cadre, validarea
checksumului la import și a metadatelor candidaților, apoi proba reală pe trei
extrase scurte din scenele existente (fără resinteză/aliniere nouă), exporturi HD
landscape/portrait în destinații noi și replace cu reuse verificat. Se reutilizează
căutările/downloadurile valide; video online se reîncearcă numai prin API și în
limitele furnizorului. Pexels live rămâne BLOCKED fără cheie, AI greu rămâne
BLOCKED pe hardware-ul auditat. Toate restanțele anterioare se păstrează.

### Matrice curentă assets — 2026-10-18 UTC

Această matrice actualizează AD00–AD23; stările inițiale rămân istoric.
Probe în `work/media/asset-discovery-20261018/`, media 0.1.0, asset_schema=1,
pipeline vizual `scene-assets-v1` păstrat. Nu s-a schimbat scene_key pentru preview.

| ID | Status curent | Dovadă / restanță |
|---|---|---|
| AD00 | DONE | Secțiunea canonică exista înaintea codului, reluarea documentată înaintea completărilor. |
| AD01 | DONE | Extensie aditivă și compatibilitate legacy; import/local/library/fallback în testele assets. |
| AD02 | DONE | Commons live, trei clipuri validate, provenance pe fiecare asset. |
| AD03 | DONE | Openverse live păstrat din 17 octombrie, imagine Argenna descărcată și override portrait verificat. |
| AD04 | PARTIAL | Pexels mock trecut; endpoint oficial reverificat; live BLOCKED fără PEXELS_API_KEY. |
| AD05 | PARTIAL | RO/EN/alternative/entități inspectabile; lexical/glosar, fără NER/traducere semantică validată. |
| AD06 | DONE | MANUAL/ASSISTED/AUTO, ranking explicabil și alternative; AUTO rămâne euristic, fără review uman implicit. |
| AD07 | DONE | 24/12/7 candidați în materialul integral, câte 3 locali; contact sheets și preview video în trei cadre. |
| AD08 | DONE | 9 înregistrări/9 blobs SHA256, index SQLite și usage; dedup/cache testate. |
| AD09 | DONE | Provenance/unknown license/credits verificate; drepturile nu sunt aprobate juridic automat. |
| AD10 | DONE | Clip real 53,561 s cu interval 2–10 s și audio extern omis; loop/freeze/sequence testate. |
| AD11 | DONE | CLI select/replace/restore/remove/settings și limite comune testate. |
| AD12 | DONE | replace-proof.json: numai scena a treia ×2 schimbată; patru MKV și receipts hash/mtime identice. |
| AD13 | DONE | HD 1920×1080 și 1080×1920; scena întâi are alt asset portrait; custom verificat pe fixture. |
| AD14 | DONE | Două thumbnail-uri, provenance și credits per profil, fără render suplimentar. |
| AD15 | DONE | Trei extrase reale + merge, referințe/provenance/override păstrate; teste split video portrait. |
| AD16 | DONE | Checksum/MIME/URL/corupție/întrerupere/Range/429/dedup; importul refuză checksum diferit. |
| AD17 | DONE | Render/review/thumbnail/audit executate cu unshare -Urn; split/merge fără acces HTTP; aliniere existentă reutilizată. |
| AD18 | BLOCKED | WSL ~3,82 GiB, GPU neexpus, backend neinstalat; Windows Intel UHD/~16,9 GB raportate separat în auditul păstrat. Fără instalări AI. |
| AD19 | DONE | 28 passed în 49,45 s în copie izolată; regresia largă 104 passed/1 skipped rămâne probă istorică. |
| AD20 | DONE tehnic | Trei scene reale, câte trei asset-uri locale; minimum două imagini diferite și un video selectat. Review editorial separat. |
| AD21 | DONE pentru proba scurtă | Patru MP4 PASSED, 11,820 s PCM, run efe6b66a60a44bcfad061f4300e9f32d; integral assets încă TODO. |
| AD22 | DONE | review/scene-review.md pentru extrase și review-full/scene-review.md cu 3 candidați locali/scenă. |
| AD23 | DONE | README/TEST_RESULTS/plan/AGENTS/notices și raport privat, Git inspectat fără scrieri. |

Status vizual PARTIAL: șase cadre selectate văzute; contain/portrait independent
confirmate. În scena video eticheta ilustrativă și subtitrarea se suprapun în
cadrele inspectate; layout-ul necesită ajustare editorială înainte de publicare.
Nu se declară vizionare integrală, ascultare sau aprobare editorială. Review uman
rămâne TODO. Proba scurtă este extract, nu export integral și nu garantează
continuitate editorială între extrase. Cele 581 fișiere protejate sunt identice;
PCM-ul extras este exact, alinierea numai rebazată, fără inferență nouă.
Restanțele protejate de mai sus rămân active integral.

### Ajustare vizuală după cadrele inspectate — IN_PROGRESS, 2026-10-18 UTC

Eticheta ilustrativă rămâne vizibilă, subtitrarea scenei video se mută sus;
imaginea persoanei primește contain numai în landscape. Se folosesc controalele
CLI existente și o a treia destinație. Sunt scene cu setări vizuale schimbate;
scenele neafectate se reutilizează. Proba replace-ului unic rămâne istoric distinct.
Fără schimbarea generatorului, audio-ului sau alinierii și fără rerandarea baseline-ului.

### Corecție vizuală încheiată — DONE pentru probele inspectate

2026-10-18, 17:44 UTC: a treia versiune `assets-accept-20261018-layout`, ambele
profile PASSED. Total tehnic 6/6 MP4 noi în trei destinații distincte. Schimbări
vizuale explicite pe scena video (subtitrare sus) și persoană landscape (contain);
3 variante afectate recalculat, 3 variante MKV/receipts reutilizate cu hash/mtime
identice. PCM/master/aliniere/timeline identice. Dovezi: layout-proof.json,
layout-state.json, layout-selected-frames.jpg în auditul 20261018.

Cele șase cadre noi au fost văzute și corecțiile confirmate. Status curent vizual:
PARTIAL, `partial_selected_frames_passed`, fără vizionare integrală; suprapunerea
și tăierea observate mai sus sunt rezolvate în versiunea layout. Celelalte versiuni
rămân istoric. Listening/editorial TODO, AI greu BLOCKED, Pexels live BLOCKED fără
key, query semantic și restanțele vechi PARTIAL/TODO păstrate. Export integral
assets TODO, proba tehnică scurtă DONE. AD23 este complet prin cele cinci documente
actualizate și final-acceptance.json; fără operații Git de scriere.

## Aplicare assets pe materialul integral — 2026-10-18 UTC

IN_PROGRESS. Baza assets și proba scurtă rămân păstrate. Copie de lucru integrală
`assets-integral-20261018`, din manifestul existent, cu audio/alignment/timeline
identice. Aproximativ 19 scene tematice la limite observate de propoziții, durate
vizuale rezonabile; fără split audio, resinteză sau inferență CTC. ASSISTED,
library-first, Commons/Openverse numai când biblioteca nu oferă candidați suficienți,
Pexels BLOCKED_OPTIONAL fără key, fără modele AI noi.

| ID | Lucrare | Status |
|---|---|---|
| AI01 | Audit/protecție și grupare scene integrale | IN_PROGRESS |
| AI02 | Query/retrieval library-first, ranking/alternative și download limitat | TODO |
| AI03 | Review complet JSON/Markdown/contact sheets și statusuri editoriale explicite | TODO |
| AI04 | Selecții propuse/fallback și configurații landscape/portrait | TODO |
| AI05 | Credits numai din selecțiile efective ale profilului exportat | TODO |
| AI06 | Render integral HD offline, verify și cadre inspectate | TODO |
| AI07 | Replace unic la scară integrală, hash/mtime/audio/alignment/library proof | TODO |
| AI08 | Titluri păstrate și thumbnail-uri cu provenance | TODO |
| AI09 | Probe focalizate pentru modificările necesare, documentație/predare | TODO |

Statusurile de review sunt APPROVED/PROPOSED/NEEDS_REVIEW/FALLBACK/
LICENSE_UNKNOWN/REJECTED, distincte de aprobarea tehnică a scenei și de faptul
că fișierul se poate decoda. Selecția făcută de agent nu este aprobare editorială
umană. LICENSE_UNKNOWN nu intră în exporturile acestei etape. Nu se reexecută
preventiv cele 28 teste assets sau exporturile deja validate. Toate restanțele
vechi (CTC, highlight/scroll, ASS, mix, listening, continuitate, avatar/logo, AI)
rămân active. Exporturi noi și receipts/checkpointuri pentru reluare.

## Matrice curentă consolidată după recovery — 2026-10-19 UTC

Această secțiune actualizează statusurile curente; tabelele anterioare rămân
istoric. Probe: `work/media/assets-integral-20261018/recovery-20261019/`,
run `5ba454a524f74ffc8991987e14b12cf1`, media 0.1.0, fără modificarea codului produsului.

| Funcție / etapă | Status | Limită / dovadă curentă |
|---|---|---|
| AI01 audit/protecție, 19 scene | DONE | Gazdă/sandbox distincte, snapshot, originale păstrate. |
| AI02 retrieval library-first | DONE pentru workflow lexical | 59 assets păstrate; fără search/download nou. Semantica AD05 rămâne PARTIAL. |
| AI03 review/index/contact sheets | DONE tehnic | Markdown/JSON/HTML, profile și candidați numerotați; lipsurile explicite, review uman separat. |
| AI04 selecții/overrides/fallback | DONE tehnic | 9 fotografii + 2 video + 8 fallback; 11 NEEDS_REVIEW și 8 FALLBACK. |
| AI05 provenance/credits per profil | DONE tehnic | 19 rânduri per profil; 0 LICENSE_UNKNOWN selectate. |
| AI06 integral HD offline/verify | DONE tehnic; PARTIAL vizual | Landscape păstrat, portrait recuperat 11 reuse/8 generate; full decode, PCM exact; numai cadre selectate. |
| AI07 schimbare unică la scară integrală | DONE tehnic | scene-016 portrait candidate 3; 18 reuse/1 rerender, baseline intact, proof hash/mtime/audio/library. |
| AI08 titluri/thumbnails | DONE tehnic | Titlu păstrat; două thumbnails HD cu hash/provenance/credits. |
| AI09 probe/documentație/predare | DONE pentru etapa tehnică | Receipts și rapoarte UTC; fără repetarea regresiei istorice. |
| CTC review accepted/rejected/corrected și rerun selectiv | DONE ca instrument; PARTIAL ca acceptanță | Cele 170 unități cu scor redus nu sunt aprobate; precizie auditivă nemăsurată. |
| Classic subtitles, SRT/ASS, diacritice | DONE tehnic | Baseline-uri integrale și varianta portrait verificate; audiția rămâne restantă. |
| Word highlight | PARTIAL | Fixture verificat; lipsesc ascultarea/acceptanța pe voce reală. |
| Scrolling subtitles | PARTIAL | Fereastră discretă, nu scroll continuu; audiție lipsă. |
| Stil ASS complet | PARTIAL | Culoare highlight/poziție liberă și restul stilului avansat încă restante. |
| Split text înainte de TTS + merge Unicode/octet | DONE | Implementare/probe existente; durata rămâne estimată. |
| Synthesize-parts --apply | PARTIAL | Aplicare disponibilă; sinteza privată nu se rulează preventiv. |
| Scene editing / profile overrides / restore | DONE tehnic | CLI existent + AI07 integral; nu aprobare editorială umană. |
| Asset discovery/library/dedup/provenance/offline | DONE tehnic pentru Commons/Openverse/local | Pexels mock verificat; live BLOCKED_OPTIONAL fără key. AD05 query semantic PARTIAL. |
| Full integral asset export | DONE tehnic | Landscape/portrait HD plus variantă portrait; 19 scene, 8 fallback păstrate deliberat. |
| Partial rerender / recovery | DONE tehnic | Numai scena schimbată rerandată; restul cu hash/mtime identice. |
| Mix extern / resampling / rate/fps diferite | PARTIAL | Rate egale existente; conversii/mix explicit încă restante. |
| Animation continuity după split | TODO | Faza se reia local; fără corecție nouă. |
| Pauze/intro/normalizare compilație | TODO | Fără efecte configurabile suplimentare. |
| Avatar/logo configurabil | TODO | Neintegrat. |
| Instalare media secundară curată cu hash-uri | TODO | Fără instalări preventive. |
| AI image backend | PARTIAL / BLOCKED pentru inferență locală | image-plan este contract; hardware/backend validate insuficient, fără instalare nouă. |
| AI video / LLM backend | TODO opțional; probă grea BLOCKED | Nu blochează workflow-ul CPU. |
| Listening/editorial review integral și ancore manuale | TODO / necesită reviewer uman | not_listened/not_reviewed; cadrele selectate nu sunt vizionare integrală. |

Continuarea după recovery a fost AI07, apoi completarea UX de review pentru
decizii pe scenă/profil. Următoarea poartă pentru acceptanța editorială este
review-ul uman (170 unități CTC, cele 19 scene și cele 8 fallback-uri), fără
aprobare automată. Backlogul tehnic rămâne ordonat: PARTIAL aproape terminate
(ASS, highlight/scroll), workflow/review, apoi mix extern, avatar/logo; AI la final.
Cele 41 assets graphic sunt locale; nu se declară 59 fotografii online.
Tranzițiile integrale sunt cut; un zoom_in landscape, portrait static.
Workflow-ul anterior întrerupt și receipts running sunt păstrate ca istoric;
acceptanța recovery-ului este separată, fără returncode inventat.

## Matrice curentă după CTC tooling / subtitrări — 2026-10-19 UTC

Aceasta este matricea curentă; secțiunile precedente rămân istoric.
Media 0.1.0, sample run `3879e965ddf84444a8dbbef6bfff34be`, dovezi în
`work/media/subtitles-20261019/` și TEST_RESULTS.md. Recovery-ul integral
era încheiat la pornire; nicio regresie nouă, nicio reluare sau rerandare integrală.

| Funcție / etapă | Status curent | Dovadă și limită |
|---|---|---|
| Audit / baseline / AI01–AI09 | DONE tehnic | 19 scene, 3 MP4-uri validate anterior păstrate hash+mtime; 720 fișiere protejate identice. |
| CTC tooling: review/export/validate/apply | DONE tehnic | Șase acțiuni, trei identități verificate, reviewer/timestamp, copii exacte, jurnal reluabil și before/after. Apply testat numai pe fixture. |
| Acceptanță CTC umană | PARTIAL / necesită reviewer | 170 low-confidence neschimbate; nicio decizie reală aplicată, precizie semantică neacceptată. |
| Browser scene/CTC review | DONE tehnic | Chromium 149 real, playback, candidați/profile/export/validări; zero erori JS, fără instalare nouă. |
| Classic subtitles / Unicode / SRT | DONE tehnic | Compatibil; classic implicit pentru subtitles; default render off păstrat. |
| Word/unit highlight | DONE tehnic | Interval existent exact, context neutru în pauze, șase sample-uri comune; dovadă raster/pixeli în ambele profile. Review auditiv separat. |
| Scrolling subtitles | DONE tehnic | Scroll continuu determinist la schimbare de linie, safe area, cadre intermediare demonstrate. Nu mai este numai fereastră discretă. |
| Stilizare ASS solicitată | DONE tehnic | Font/mărime/outline/shadow/margini/alignment/line spacing/highlight/safe area, preseturi și profile overrides validate. |
| Fallback safe margins | DONE tehnic pe sample | Regula sistemică 14% landscape/10% portrait și rezervare overlays; exporturile integrale istorice rămân intacte. |
| Cache subtitrări / invalidare minimă | DONE tehnic | Schimbările captions afectează finalul; highlight/scroll 6 reuse/0 generate, style/margini/preset 3 reuse/0. Cele 38 scene keys integrale păstrate. |
| Scene editing / profile overrides / restore | DONE tehnic | Proba integrală anterioară 18 reuse/1 rerender și browser review curent. |
| Asset discovery/library/dedup/provenance/offline | DONE tehnic pentru Commons/Openverse/local | 59 assets păstrate, render sample fără rețea; AD05 semantic PARTIAL, Pexels live BLOCKED_OPTIONAL fără key. |
| Full integral assets / thumbnails / title / credits | DONE tehnic | Baseline precedent păstrat: 9 foto+2 video+8 fallback; review editorial integral restant. |
| Partial rerender / recovery | DONE tehnic | Mecanism păstrat; nu s-a modificat recovery-ul și nu s-a repetat exportul integral. |
| Split text înainte de TTS / merge Unicode/octet | DONE | CLI existent și probe istorice; duratele split-text rămân estimate. |
| Synthesize-parts --apply | PARTIAL | Sinteza privată nu este rulată preventiv. |
| Mix extern / resampling / rate/fps diferite | PARTIAL | Etapa următoare pregătită mai jos; fără mix nou în această etapă. |
| Continuitate animație după split | TODO | Faza locală existentă nu este corectată aici. |
| Pauze/intro/normalizare compilații | TODO | Efecte suplimentare neimplementate. |
| Avatar/logo configurabil | TODO | Amânat conform priorității. |
| Instalare media secundară curată | TODO | Fără instalări preventive. |
| AI image backend | PARTIAL / inferență BLOCKED | image-plan este contract; backend/hardware insuficient validate, nicio instalare. |
| AI video / LLM backend | TODO opțional / probă grea BLOCKED | Nu blochează workflow-ul CPU. |
| Listening/editorial/CTC human review | TODO pentru acceptanță integrală | not_listened/not_reviewed/pending; agentul a inspectat numai cadre și screenshots. |

Porțile tehnice CTC tooling, highlight, scroll și ASS sunt închise pentru
cerințele acestei etape. Cuantizarea ASS la centisecunde/cadre și scorurile CTC
reduse rămân vizibile; full decode și diferența A/V nu măsoară precizia semantică.
Nu există highlight+scroll combinat: cele trei moduri sunt suficiente aici.
Sample-ul folosește exclusiv audio existent; singurul freeze explicit este
rotunjirea sub un cadru a clipului video din copia sample, documentată separat.

## Următoarea etapă pregătită: EXTERNAL AUDIO MIX

Nu se începe mixarea în această etapă. Contractul propus pentru implementare:

1. Intrări explicite: master narativ existent, fișier extern cu hash/provenance,
   sample rate/canale/durată; nicio resinteză sau realiniere a narațiunii.
2. Configurație de mix separată: offset, gain, trim/loop explicit, fades,
   ducking și țintă loudness opționale. Definirea regulilor de resampling și
   plafonare este necesară înainte de a declara suportul ratelor diferite.
3. Master original și alignment originale imuabile; master de mix/receipt nou,
   cache separat pentru audio mix/final composition, scene reutilizabile.
4. Proba inițială numai sample: semnal extern fixture izolat, clipping/peak,
   A/V/full decode, rate/canale, determinism și dovada că masterul narativ nu
   s-a schimbat. Fișierul privat pentru producție și nivelurile editoriale cer
   selecție explicită; nu sunt inventate de agent.
5. Acceptanță tehnică separată de audiția umană a inteligibilității/echilibrului.
   Export integral nou numai după stabilizarea probei scurte și alegerea sursei.

Nicio dependență sau licență nouă în etapa CTC/subtitrări; THIRD_PARTY_NOTICES.md
nu necesită schimbare. Review-ul uman rămâne poarta externă a acceptanței,
fără a bloca pregătirea următoarei etape tehnice.

## Matrice curentă după EXTERNAL AUDIO MIX — 2026-10-19 UTC

Aceasta actualizează matricea curentă; secțiunile precedente sunt istoric.
Implementarea continuă contractul pregătit mai sus: master narativ imuabil,
mix derivat/cache separat, configurare explicită, probe scurte și acceptanță
auditivă separată. Media 0.1.0; dovezi `work/media/audio-mix-20261019/`.

| Funcție / etapă | Status curent | Limită / probă |
|---|---|---|
| EXTERNAL AUDIO MIX | DONE tehnic | Narration + music/sfx/ambience, gain/trim/fades/loop, ducking și normalizare finală, CLI local. |
| Resampling extern / mono-stereo | DONE tehnic | Surse 44100 stereo și 48000 stereo/mono spre 22050 mono PCM s32, durată în eșantioane exactă; downmix medie explicită. |
| Ducking | DONE tehnic | RMS controlat: 11,989 dB pentru amount_db=12; anvelopă continuă cu attack/release și revenire în pauză. Nu este detector semantic de vorbire. |
| SFX timing | DONE tehnic | 7,125 s în sample real cu fixture; probă controlată 2,125 s → eșantion 46856, onset măsurat 46856. |
| Loudness / peak / atomicity | DONE tehnic | WAV -18,97 LUFS/-2,00 dBTP; AAC -19,00/-2,00; încercări incomplete păstrate și retry testat. |
| Mix split/merge și provenance | DONE tehnic | Contextul DSP original păstrat; split→merge PCM identic; configurări muzicale diferite păstrate separat. |
| Mix cache / compoziție video | DONE tehnic | Mix separat; schimbare audio reutilizează video cu streamhash identic, fără apel de subtitle generation. |
| REAL MUSIC ACCEPTANCE | PARTIAL / READY_FOR_USER_AUDIO | Nu există track de muzică aprobat pentru publicare identificat în proiect; numai fixture-uri locale tehnice. |
| Listening mix real | TODO / necesită utilizator | not_listened; metricile și tonurile nu reprezintă audiție umană. |
| Merge narațiuni cu rate diferite | PARTIAL | Regula existentă de conversie explicită rămâne; mixerul rezolvă ratele trackurilor externe, nu rescrie narațiunea. |
| Pauze/intro/normalizare globală compilații | TODO | Pauzele existente respectate; nu se inserează pauze/intro noi sau normalizare repetată la merge. |
| CTC tooling / classic / highlight / scroll / ASS | DONE tehnic | Etapa precedentă păstrată; regresie media și hash-uri de protecție verificate. |
| CTC human review | PARTIAL | 170 unități încă pending; alinierea originală nemodificată. |
| Browser scene/CTC review | DONE tehnic | Chromium PASSED din etapa precedentă; nu s-a repetat fără schimbări UI. |
| Integrale / scene editing / thumbnails / credits / partial rerender | DONE tehnic | Baseline-uri și scene keys păstrate; niciun integral rerandat. |
| Assets/library/offline | DONE tehnic pentru Commons/Openverse/local | Library intactă; întregul mix/testele rulează fără rețea. AD05 semantic rămâne PARTIAL. |
| Pexels live | BLOCKED_OPTIONAL | Cheie absentă; nu blochează mixul local. |
| Split text înainte de TTS / merge text | DONE | Fără schimbări. Synthesize-parts privat rămâne PARTIAL, fără sinteză preventivă. |
| Animation continuity | TODO | Continuitatea fazei mișcării vizuale după split nu este rezolvată prin mixul audio. |
| Avatar/logo / instalare media secundară curată | TODO | Neîncepute aici. |
| AI image backend | PARTIAL / inferență BLOCKED | Contract existent, fără instalare/inferență nouă. |
| AI video / LLM | TODO opțional / probă grea BLOCKED | Nu blochează workflow-ul CPU. |
| Listening/editorial integral | TODO / necesită reviewer uman | Nicio aprobare umană inventată. |

Contract implementat: rețetă `material.audio_mix`, schema aditivă 1, tracks locale
hash-bound, timpi externi în secunde și interni în eșantioane. Narration obligatorie
implicit; sursa audio a unui asset video nu intră automat în mix. Fragmentul
reține o fereastră din contextul părintelui și procesează acel context înainte de
decupare: aceeași anvelopă, fază loop, fades și normalizare, inclusiv după merge.
Merge nu unește euristic muzica și nu normalizează din nou compilația.

Cli: `audio-mix --inspect/--validate/--set/--disable/--render/--verify`;
`--render --mux-video ... --output ...` pentru copiere video existentă.
Render obișnuit consumă mixul activ și reutilizează compoziții compatibile prin
picture_request. Baseline-urile istorice fără acest receipt se pot remuxa explicit,
fără adoptare bazată numai pe dimensiune/mtime. Nicio invalidare TTS/CTC/assets;
workflow-urile declarate cu întreg manifestul input își păstrează hash-ul declarat.

Următoarea poartă pentru mix real: utilizatorul furnizează/alege un fișier local
aprobat și metadatele de drepturi, configurează nivelurile, apoi ascultă A/B.
Nu se descarcă și nu se selectează automat muzică. Etapa tehnică nu mai este
blocată; acceptanța reală este READY_FOR_USER_AUDIO. Backlogul independent
rămâne în tabel; nu a fost început avatar/AI sau redesign.


## LOCAL GUI / PRODUCTION STUDIO — 2026-10-20 UTC

Status etapă: IN_PROGRESS. CLI-urile rămân disponibile independent. Arhitectură:
servicii Python comune, server HTTP local implicit 127.0.0.1:8765, UI HTML/CSS/JS
locală fără CDN, fără build și fără dependențe suplimentare. Biblioteca standard
reduce instalările și păstrează mediile Piper/CTC existente. Joburile folosesc
procese Python cu servicii importate direct, nu subprocess ./media sau ./tts.
Manifestele sunt source-of-truth; joburile au receipts separate.

| Etapă | Ecrane / workflow / contract | Status |
|---|---|---|
| A | Audit CLI exact, materiale/work/output read-only, protecție baseline | IN_PROGRESS |
| B | rec_media.services / rec_tts.services, aceeași validare/lock/dispatch | TODO |
| C | Server local, host/port/no-browser, API, CSRF/origin/paths/picker | TODO |
| D–E | Shell compact, Dashboard, Materials, creare/duplicare sigură, metadata/timeline | TODO |
| F | Scene list/filter, preview, properties, crop/focal/profile, motion/transition, undo | TODO |
| G | Assets/library/search/download/import, alternative grid/contact sheets/provenance | TODO |
| H | Alignment/status și CTC integrat, playback/decizii explicite/validate/apply | TODO |
| I | Subtitles classic/highlight/scroll, preset/stil/profile, preview backend real | TODO |
| J | Audio Mix tracks/gain/timing/trim/loop/fades/ducking, waveform/verify | TODO |
| K | Render/plan/invalidation, job queue/progress/log/cancel/resume/restart | TODO |
| L | Verify/statusuri umane distincte, Outputs/player/folder/rapoarte/hash | TODO |
| M | Settings/hardware/AI read-only, text editor/diff/save, TTS, split-text, split/merge/compilation, title/thumbnail | TODO |
| N | API/service/CLI parity, securitate/recovery/offline și browser existent; sample izolat real | TODO |
| O | README/TEST_RESULTS/plan/AGENTS/notices, limitări și Git read-only | TODO |

Nu se oferă controale pentru backend-uri inexistente. Delete nu este implementat
în backend și nu se activează implicit. Intro/outro/pauze suplimentare rămân TODO
conform contractului existent. Estimările nu devin măsurători; ETA necunoscut nu
este inventat. Review browser/tehnic/vizual/auditiv/editorial/CTC uman rămân
separate. Testele automate nu aplică decizii materialelor reale.

### Audit CLI exact pentru Studio

Inventar derivat din argparse, înainte și după extragerea serviciilor.
`gui` este singura subcomandă nouă; comenzile și opțiunile istorice rămân.
Opțiuni globale: media `--config/--report`; tts `--config`.

| CLI / comandă | Opțiuni / poziționale specifice |
|---|---|
| `./tts fetch-model` |  |
| `./tts doctor` |  |
| `./tts verify` | `audio` |
| `./tts prepare` | `input`, `--pronunciations`, `--verbose`, `--output-dir` |
| `./tts preview` | `input`, `--pronunciations`, `--verbose`, `-o/--output`, `--speed`, `--keep-wav`, `--force`, `--words` |
| `./tts render` | `input`, `--pronunciations`, `--verbose`, `-o/--output`, `--speed`, `--keep-wav`, `--force` |
| `./media doctor` |  |
| `./media gui` | `--host`, `--port`, `--no-browser` |
| `./media audio-mix` | `material`, `--output-dir`, `--output`, `--mux-video`, `--inspect`, `--validate`, `--set`, `--disable`, `--render`, `--verify` |
| `./media image-plan` | `request`, `--output` |
| `./media workflow` | `plan`, `--only`, `--disable`, `--rerun` |
| `./media synthesize-parts` | `manifest`, `--output-dir`, `--apply` |
| `./media split-text` | `text`, `--output-dir`, `--parts`, `--target-duration`, `--chapters`, `--delimiter`, `--manual-ranges`, `--semantic`, `--words-per-minute` |
| `./media merge-text` | `manifest`, `--output` |
| `./media init` | `--id`, `--audio`, `--text`, `--image`, `--tts-report`, `--sample-rate` |
| `./media convert-narration` | `material`, `--id`, `--sample-rate` |
| `./media compile` | `--id`, `--materials`, `--composition`, `--plan-only` |
| `./media compile-video` | `material`, `--videos`, `--output`, `--profiles` |
| `./media align` | `material`, `--words`, `--backend`, `--provenance`, `--model`, `--windows`, `--max-windows`, `--segments` |
| `./media alignment-review` | `material`, `--output`, `--apply`, `--validate`, `--media` |
| `./media scene-plan` | `material`, `--output`, `--folder`, `--images`, `--intervals` |
| `./media scenes` | `material`, `--scene`, `--profile`, `--library-root`, `--plan`, `--inspect`, `--alternatives`, `--select`, `--replace`, `--remove`, `--restore`, `--set`, `--auto`, `--sequence`, `--approve`, `--allow-unknown-license` |
| `./media assets search` | `--library-root`, `material`, `--scene`, `--provider`, `--query`, `--type`, `--limit`, `--mode` |
| `./media assets queries` | `--library-root`, `material`, `--scene` |
| `./media assets list` | `--library-root`, `--query`, `--type`, `--filters` |
| `./media assets import` | `--library-root`, `path`, `--metadata` |
| `./media assets download` | `--library-root`, `material`, `--scene`, `--candidate`, `--all`, `--rendition` |
| `./media assets review` | `--library-root`, `material`, `--output-dir` |
| `./media assets credits` | `--library-root`, `material`, `--output-dir`, `--profiles` |
| `./media titles` | `material`, `--manual`, `--select`, `--approve`, `--unlock`, `--candidates` |
| `./media subtitles` | `material`, `--profiles`, `--width`, `--height`, `--mode`, `--output-dir`, `--ass-preset` |
| `./media thumbnail` | `material`, `--profiles`, `--width`, `--height`, `--text`, `--image`, `--scene`, `--variant`, `--format`, `--output-dir` |
| `./media render` | `material`, `--profiles`, `--width`, `--height`, `--image`, `--subtitles`, `--title`, `--force`, `--plan-only`, `--ass-preset`, `--rerender-changed`, `--resume-run`, `--output-root` |
| `./media split` | `material`, `--mode`, `--intervals`, `--parts`, `--target-seconds`, `--max-seconds`, `--prefix`, `--apply` |
| `./media merge` | `--id`, `--materials`, `--plan-only`, `--composition` |
| `./media batch` | `file` |
| `./media verify` | `video` |

Audit: 27 materiale, library 59 intrări în starea inițială, scene integrale 19,
170 unități CTC low-confidence. 822 fișiere de input/material/output/model/library/
cache inventariate hash+mtime înaintea probei; scanarea inițială nu scrie în SQLite.
Pipeline-urile scene/CTC/Piper nu sunt modificate; serviciile sunt extrase din
CLI. Regresia a identificat separat o limită a normalizării dinamice a compilațiilor;
corecția limitată și probele sunt consemnate în TEST_RESULTS. Codul existent compilation.create/convert_material/video oferă deja contract
intro/outro/pause înainte/între/după; UI îl expune prin compile și JSON, fără a
interpreta vechile statusuri TODO ca dovadă că funcția lipsește din cod.

### Matrice de implementare LOCAL GUI / PRODUCTION STUDIO

Starea anterioară A–O rămâne istoric al începerii. Probe private:
`work/studio/acceptance/`, Studio 1.0.0 / media 0.1.0.

| Etapă / contract | Status | Dovadă / limită |
|---|---|---|
| A audit + inventar CLI + baseline | DONE | Catalog argparse, 27 materiale; snapshot hash/mtime. |
| B servicii comune | DONE | CLI și GUI importă aceleași dispatch/validări/lock; paritate scene/TTS prepare testată. |
| C server/API/security | DONE | gui host/port/no-browser, loopback, CSRF/origin/Host, paths/symlinks, range, upload staging, fără shell. |
| D–E shell/Dashboard/Materials | DONE tehnic | Pagini reale Chromium, full material inspectat read-only, creare/duplicare sigură, metadata/timeline. Delete refuzat implicit. |
| F Scene Editor / list / filters / profiles | DONE pentru controalele existente | Select/replace/remove/undo, candidate IDs, crop/focal/fit/motion/transition/video/mute/review și advanced JSON; invalidare prin scene_key. |
| F preview editor avansat | PARTIAL | Focal click și profile separate; crop preview orientativ; fără drag crop/trim handles sau transition preview dedicat. Proba exactă prin render sample derivat. |
| G Assets/Library/contact alternatives | DONE pentru backend imagine/video | Grid local, query/search/download explicit, provenance/credits/import/export Markdown. Library audio separată TODO; trackurile audio se importă prin mixer. |
| H Alignment/CTC review | DONE tehnic | Identități/scoruri, navigare/playback/waveform la cerere, șase acțiuni/export/validate/apply existent; browser validează numai decizii fixture, fără apply real. |
| H acceptanță CTC umană | PARTIAL | Cele 170 unități reale rămân pending. Playback global compus/waveform cere export audio separat. |
| I Subtitles | DONE tehnic | Stil/preset/profile/undo, SRT/ASS, preview raster prin layout real și preflight înainte de render. Preview neutru, nu compoziție live completă. |
| J Audio Mix / verify / waveform | DONE pentru contract existent | Track forms/gain/timing/trim/loop/fades/ducking/norm/validate/save/undo/render/mux; waveform simplu în browser pentru sursă simplă sub 80 MB. |
| J muzică reală / listening | PARTIAL | READY_FOR_USER_AUDIO / not_listened; proba folosește fixture tehnic, fără aprobare de muzică. |
| K Render/Jobs/Logs/progress | DONE tehnic | Procese separate, coadă JSON persistentă, progres pe run propriu/scene/phase/remux, fără ETA inventat; stdout/stderr/command/result. |
| K cancel/resume/restart | DONE tehnic | SIGINT activ, checkpoint înainte/după identic, .part nepublicat, job original păstrat, resume și restart server cu worker activ. |
| K Workflow/batch/synthesize-parts | DONE adaptor validat | Pași/căi normalizate, fără recursivitate/instalări/online ascuns; apply sinteză explicit. Orchestratorul istoric încă folosește intern CLI wrappers; eliminarea acestor subprocess-uri este TODO separat. |
| L Verify/Outputs/human statuses | DONE tehnic | Hash/surse/provenance/intervale, verify audio/video/ASS, playere/range/hash/folder; statusurile umane nu devin PASSED. |
| M Settings/hardware/AI | DONE read-only + preferințe UI | CPU/RAM/GPU nevalidat, toolchain/model/config, Pexels bool fără key, AI unavailable/blocked explicat. Toolchain settings editabile și Windows opener rămân PARTIAL/nevalidate. |
| M text/TTS/split-text/title/thumbnail/split/merge | DONE controale backend | Draft/diff/hash, same TTS service, estimated offsets, titlu locked, thumbnails/provenance, ordine explicită și contract compilation existent. |
| N tests/browser/sample/offline | DONE tehnic | 31 unit, 38 TTS izolat, 81 audio/compilation/Studio; Chromium 31 checks offline; active cancel/restart/resume și 822 hash+mtime/38 scene keys. Istoricul 180 passed/1 failed este păstrat și corecția focalizată documentată. |
| O documentație/predare/Git | DONE | README/TEST_RESULTS/plan/AGENTS/notices actualizate; git status/diff read-only. Fără staging/commit/push. |

Status general până la închiderea verificărilor: IN_PROGRESS. DONE tehnic se
referă la criteriile minime de acceptanță GUI, nu la review uman integral sau
la controalele opționale avansate. Restanțele media/AI istorice sunt păstrate.

### Închidere LOCAL GUI / PRODUCTION STUDIO — 2026-10-20 UTC

**DONE tehnic pentru criteriile principale de acceptanță**, cu limitele PARTIAL/
TODO din matrice păstrate. `work/studio/acceptance/final-acceptance.json`,
`browser-final-v6/result.json`, `recovery-final/result.json`, TEST_RESULTS.
Serverul final este pornit explicit cu `./media gui --no-browser`,
http://127.0.0.1:8765. CLI-urile sunt independente și păstrate.

Baseline 822/822 hash+mtime și 38/38 scene keys identice. Snapshotul istoric
720 are 718 identice și două diferențe autorizate CLI TTS/bytecode; motorul,
config/dicționar/model/audio/cache sunt neschimbate. Normalizarea mixului are
retry limitat din suma originală pentru limita găsită în regresie, fără
relaxarea acceptanței și fără rerandarea baseline-urilor. Raportul comun inițial
180 passed/1 failed și corecțiile/probele ulterioare rămân istoric distinct.

Nu se declară audiție, review editorial integral sau aprobare CTC umană.
AI greu și muzica reală păstrează statusurile anterioare; Windows opener/GPU
Windows rămân nevalidate. Funcțiile opționale UI restante nu sunt redenumite DONE.


## GUI HARDENING + UX COMPLETION — 2026-10-20 UTC

Status DONE tehnic, cu GH06 PARTIAL pentru confirmarea vizuală Explorer. Extensie a Studio existent, fără schimbarea arhitecturii,
CLI-urilor, motorului TTS, CTC sau pipeline-ului de pixeli al scenelor. Probe numai
în copie izolată/sample; fără export integral. Cache preview separat în
work/studio/previews, bibliotecă audio aditivă în același SQLite/blobs.

| ID | Contract | Status |
|---|---|---|
| GH01 | Audit/baseline, CLI și scene keys păstrate | DONE |
| GH02 | Crop/focal drag+click, landscape/portrait prin renderer real, cache verificat | DONE |
| GH03 | Video trim/scrub/frame, durată/mute/short-policy reale | DONE |
| GH04 | Cut/crossfade preview scurt prin renderer existent, cache atomic | DONE |
| GH05 | Audio library/index/metadate/tags/provenance/play/reuse Audio Mix | DONE |
| GH06 | Windows-path presentation/Open folder și probă browser Windows separată | PARTIAL |
| GH07 | Loading/empty/error/disabled/cost confirmation pe toate paginile | DONE |
| GH08 | Progres run propriu/reused/rendered/frame/log/cancel/resume | DONE |
| GH09 | Scene navigation/next pending/save indicator/unsaved/undo | DONE |
| GH10 | Full-screen Review mode, profile/candidate/decizii explicite/shortcuts | DONE |
| GH11 | Outputs player/badge/size/hash/date/path/copy/folder | DONE |
| GH12 | Settings toolchain validation și secrete mascate; security păstrată | DONE |
| GH13 | Teste servicii/browser/offline/sample/cancel/recovery și regresii focalizate | DONE |
| GH14 | README/TEST_RESULTS/plan/AGENTS, Git read-only | DONE |

Preview-urile nu sunt aprobare editorială/auditivă. Cadrele de crop/trim sunt
mostre de scenă înainte de subtitles/final assembly; tranzițiile folosesc un
material temporar scurt și rendererul real, fără resinteza narațiunii. Durata
ferestrei preview și eventualele limite trebuie afișate, fără a promite un export
integral. Timestampurile/audio-ul/alinierea sursei și scene_key rămân imuabile
pentru cererile exclusiv de preview. Windows/WSL au probe/statusuri distincte.

### Probe și limite la închidere — Studio 1.1.0, 2026-10-20 UTC

- GH02–04: cadre crop/focal prin asset_render.generate + validate_scene, trim/scrub
  cu timestamp cerut/efectiv, clipuri cut/crossfade prin video.render pe snapshot
  temporar. Cache content-addressed, hash/decodare/cadre exacte, fără scriere sursă.
- GH05: studio_audio aditiv în indexul existent, tags/provenance/full decode,
  play și reutilizare în mixer; corecție formular pentru loop_fade_ms numeric și
  păstrarea source/checksum când se adaugă/elimină alt track. Niciun DSP schimbat.
- GH07–11: 21 pagini, loading/empty/error/retry și formulare disabled; confirmări,
  save/dirty/undo, navigare/shortcut-uri, fullscreen/profile/candidate review,
  playere Outputs/hash/date/Windows path. Jobul selectat are footer și log proprii,
  frame-uri reale și contoare rendered/reused, separate de asamblarea finală.
- GH06: Edge Windows a încărcat efectiv Dashboard localhost:8765; CDP raportează
  title=REC Studio, dashboard=true, ready=true, hasMaterials=true. HTTP Windows
  200 și UNC output Test-Path=true. Open folder lansează opener-ul, dar returncode
  Explorer nu dovedește o fereastră vizibilă; confirmarea vizuală rămâne PARTIAL.
  Erorile vsock din încercările inițiale și cele de harness sunt păstrate.
- GH12: toolchain fix verificat fără model loading/instalări; cheia Pexels mascată
  și absentă din receipts/logs. Host/Origin/CSRF/scoped paths/no shell păstrate.
- GH13: 55 teste Studio + 38 TTS izolat; Chromium 149, 46 checks offline, fără
  erori JS/conexiuni externe. Browser Cancel/Resume + restart real: 1 checkpoint
  reutilizat, 2 scene randate numai pe sample 16.46 s, hash+mtime păstrate;
  HTTP Range passed. CLI scenes --inspect identic cu serviciul comun.
- Protecție: 833/833 SHA256+mtime identice; 38 scene keys recalculabile identic
  din intrări/pipeline nemodificate. Fără resinteză, CTC nou sau export integral.
- Dovezi: work/studio/hardening-20261020/{services-final-v2.xml,tts-regression.xml,
  browser-final/result.json,recovery-final/result.json,windows-browser-v4.json,
  windows-folder.json,runtime-final.json,protection-final.json,cli-final.json,
  final-acceptance.json,git-status-final.txt}. Date private ignorate.

Nu există trim handles, animație completă la scrub sau configurare arbitrară de
executabile. Preview maximum 960 px, fără subtitrări finale; motion la începutul
ferestrei. Settings toolchain read-only. Review vizual selectiv de agent este
separat de browser_review=passed, listening_review=not_listened,
editorial_review=not_reviewed, ctc_human_review=pending. Nu există dependențe noi,
Electron, cloud sau build/frontend nou; CLI-urile și rendererul sunt neschimbate.
README/TEST_RESULTS/AGENTS actualizate; THIRD_PARTY nu cere alte notificări în
această etapă. Git numai status/diff, fără staging/commit/push.

# Proveniență și licențe

Motorul instalat este **piper-tts 1.8.0**, GPL-3.0-or-later. Textul licenței distribuit în wheel este păstrat în `licenses/Piper-GPL-3.0.txt`. Sursa: https://github.com/OHF-Voice/piper1-gpl și https://pypi.org/project/piper-tts/1.8.0/ . Licențele componentelor incluse în wheel rămân în `.venv/lib/python3.13/site-packages/piper_tts-1.8.0.dist-info/licenses/`.

Vocea fixă **ro_RO-mihai-medium** provine din depozitul oficial https://huggingface.co/rhasspy/piper-voices . `fetch-model` fixează revizia și păstrează fișa MODEL_CARD, metadatele depozitului și URL-urile exacte în `models/piper/`. Fișa declară dataset CC0 și antrenare pornind de la vocea lessac. Metadatele depozitului declară MIT. Licența datasetului nu echivalează cu o garanție asupra tuturor drepturilor modelului; păstrăm separat aceste afirmații ale furnizorului. SHA-256 calculat local identifică fișierele, fără a fi o semnătură independentă.

Dependențe: ONNX Runtime (MIT), NumPy (BSD-3-Clause și notificările bibliotecilor incluse), SoundFile (BSD-3-Clause), libsndfile (LGPL), CFFI (MIT), protobuf (BSD-3-Clause), flatbuffers (Apache-2.0), pathvalidate (MIT), packaging (Apache-2.0/BSD), typing-extensions (PSF), pycparser (BSD). Notificările versiunilor efectiv instalate se găsesc în directoarele `*.dist-info` ale mediului virtual. Lista exactă este în lockfile.

FFmpeg și libmp3lame se instalează ca pachete Debian, separat de Python. În mediul de implementare sudo a cerut parolă; s-a folosit build-ul static GPLv3 FFmpeg 7.0.2 de la https://johnvansickle.com/ffmpeg/ . Arhiva, hash-urile, URL-ul, readme-ul și licența sunt păstrate în `.tools/`; instalarea explicită reproductibilă este `scripts/install-local-ffmpeg.sh`. Build-ul local este un fallback fixat și testat, fără a fi declarat cea mai nouă versiune. Configurația și licența build-ului local se văd din rădăcina proiectului cu `.tools/ffmpeg/ffmpeg -version` și `.tools/ffmpeg/ffmpeg -L`; executabilele locale nu sunt adăugate permanent în PATH-ul terminalului. Lock-ul de proveniență este `.tools/ffmpeg.lock.json`, iar textul licenței este `.tools/ffmpeg/GPLv3.txt`; documentație: https://ffmpeg.org/ffmpeg-codecs.html#libmp3lame și https://ffmpeg.org/ffmpeg-filters.html#loudnorm . Executabilele descărcate local sunt excluse din Git.

Fluxul audio nu include Supertonic, servicii cloud sau CUDA. Modelul suplimentar de aliniere media este documentat separat mai jos.

Pentru utilizare și instalare numai la nevoie, vezi [README.md](README.md); pentru mediul și rulările efectiv verificate, vezi [TEST_RESULTS.md](TEST_RESULTS.md). Această actualizare de documentație nu reprezintă un nou audit juridic sau o reverificare externă a tuturor licențelor tranzitive.


## Extensia media 0.1.0 — 16 octombrie 2026

Media reutilizează **Pillow 11.1.0 deja instalat în Debian** (`/usr/lib/python3/dist-packages/PIL`), fără instalări în mediul Piper. Notificările și licența distribuției sunt în `/usr/share/doc/python3-pil/copyright` (Pillow/HPND și notificările componentelor incluse); pinul de versiune locală este `requirements-media.lock`, fără hash-uri de wheel. Acesta nu este un audit juridic nou al tuturor componentelor sistemului.

Fontul demonstrativ este **DejaVu Sans**, `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`; proveniența/licențele Bitstream Vera/DejaVu sunt păstrate de Debian în `/usr/share/doc/fonts-dejavu-core/copyright`. Exporturile de subtitrări păstrează o copie a fontului folosit și hash-ul acestuia; pentru un font furnizat separat de utilizator trebuie verificată licența sa. Nu presupunem că toate fonturile instalate au aceeași licență.

Build-ul FFmpeg local existent furnizează libx264, AAC, libass și filtrele media verificate prin `media doctor` și probe de encodare. Licența GPLv3 a build-ului și notificările lui rămân cele descrise mai sus; nu a fost înlocuit executabilul audio.

Imaginile și tonurile din `work/media/demo/` sunt fixture-uri sintetice compuse local din forme/text și semnale, fără imagini de pe internet sau model generativ. Vocea din `audio-demo` provine din proba Piper sintetică existentă, cu proveniența modelului descrisă separat mai sus. Pentru assets ale utilizatorului, câmpurile `license`/`provenance` rămân `unknown`/furnizate explicit când drepturile nu sunt cunoscute; nu atribuim automat CC0 tuturor imaginilor ori modelelor.

La etapa inițială, WhisperX/Wav2Vec2, Qwen/llama.cpp și Wan2.1 erau numai candidați. Actualizarea de mai jos instalează explicit numai modelul românesc pentru aliniere. WhisperX complet, Qwen/llama.cpp și Wan2.1 rămân neinstalate.

## Aliniere românească CPU — 16 octombrie 2026 UTC

Adaptorul REC `ctc-ro` utilizează direct **gigant/romanian-wav2vec2**, revizia `79cf603aac59501d02bfeb37f615efc3ac4ce1b3`, prin Transformers/PyTorch CPU și Viterbi CTC. [Fișa oficială a modelului](https://huggingface.co/gigant/romanian-wav2vec2/blob/79cf603aac59501d02bfeb37f615efc3ac4ce1b3/README.md) declară Apache-2.0 și descrie derivarea din XLS-R-300m, Common Voice 8 Romanian și Romanian Speech Synthesis. Licența declarată a modelului nu este o garanție independentă asupra tuturor datelor/drepturilor. Fișa, configurațiile, vocabularul, safetensors, revizia, sursele și hash-urile locale rămân în `models/alignment/romanian-wav2vec2/`, excluse din Git. Nu s-au descărcat `pytorch_model.bin`, language_model/5gram.bin, resurse de diarizare sau ASR Whisper.

Dependențele sunt izolate în `.venv-align`, cu versiuni în `requirements-align.lock`. Copiile notificărilor efectiv distribuite sunt în [licenses/alignment/provenance.json](licenses/alignment/provenance.json):

| Componentă | Versiune | Licență/proveniență |
|---|---|---|
| PyTorch CPU | 2.8.0+cpu | BSD-3-Clause și NOTICE ale distribuției; [sursa oficială](https://github.com/pytorch/pytorch/tree/v2.8.0). Fără CUDA. |
| Transformers | 4.56.2 | Apache-2.0; [sursa oficială](https://github.com/huggingface/transformers/tree/v4.56.2). |
| num2words | 0.5.14 | LGPL-2.1, textul COPYING distribuit; [proiect](https://github.com/savoirfairelinux/num2words). Folosit numai pentru ținta acustică, fără rescrierea sursei. |
| SoundFile | 0.13.1 | BSD-3-Clause; libsndfile inclus are licență separată LGPL. |
| safetensors | 0.8.0 | Apache-2.0 conform LICENSE distribuit. |
| huggingface-hub | 0.36.2 | Apache-2.0 conform LICENSE distribuit; încărcarea la procesare este exclusiv locală. |

Licențele tranzitivelor și bibliotecilor incluse rămân și în `*.dist-info` din mediul izolat; lista versiunilor este completă în lock, fără pretenția unui audit juridic al tuturor componentelor. Coperțile reale media sunt forme geometrice Pillow cu text extras din material; nu sunt imagini AI sau imagini preluate de pe internet. Textul personal și fișierele media nu se distribuie implicit prin Git.

## Etapa producție — 2026-10-16 UTC

Nu s-au instalat pachete sau modele suplimentare. Noile module folosesc biblioteca
standard Python și Pillow/FFmpeg/fonturile existente. Grafica de acceptanță din
`work/media/production-20261016/assets/` este compusă din forme și etichete locale,
fără imagini externe sau generare AI; nu se declară asociere semantică automată.

Backend opțional ales pentru evaluare pe alt hardware: **stable-diffusion.cpp**,
[cod cu licență MIT](https://github.com/leejet/stable-diffusion.cpp/blob/master/LICENSE),
[documentație CLI oficială](https://github.com/leejet/stable-diffusion.cpp/blob/master/examples/cli/README.md).
Greutățile propuse SD 1.5 au o licență separată **CreativeML OpenRAIL-M**, cu
restricții de utilizare; nu le numim software OSI fără restricții. Vezi
[fișa oficială SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/blob/main/README.md).
Aceste pagini au fost consultate la această etapă; nu dovedesc instalare locală.
Nicio greutate sau binar nu a fost descărcat. Interfața `image-plan` păstrează
promptul, seed-ul, dimensiunile, reviziile/hash-urile/licențele când sunt furnizate.
Nu execută un backend neverificat și nu folosește cloud. Orice conversie/quantizare
viitoare trebuie să păstreze sursa, licența greutăților și hash-urile rezultatului.

## Recuperarea producției — 2026-10-16 UTC

Nu s-au instalat sau actualizat dependențe, modele, fonturi ori executabile.
Recuperarea reutilizează FFmpeg/Pillow, Piper și CTC românesc deja documentate.
Modificările orchestratorului folosesc biblioteca standard Python. Proba
`image-plan` folosește un fișier sintetic de identitate, fără greutăți AI și fără
executarea vreunui backend. Status: DONE pentru contractul testat;
PARTIAL pentru integrarea generării; BLOCKED pentru proba de inferență pe
resursele WSL documentate; TODO pentru backend-uri LLM/video opționale.
Grafica de producție rămâne fixture geometric local, fără imagini externe noi.

Plafonul temporal strict folosește numai math și cronologia locală existentă;
nu adaugă dependențe, modele sau generare audio.

Corecția crossfade restabilește FPS prin filtrul FFmpeg existent înainte de
`tpad`; proba roșu/albastru este creată local. `render --output-root` folosește
Path din biblioteca standard. Nu s-a schimbat build-ul FFmpeg sau proveniența sa.

## Discovery și asset-uri online — 2026-10-17 UTC

Implementarea folosește urllib/sqlite3/hashlib din Python, plus Pillow și FFmpeg
existente; nu instalează biblioteci, modele sau motor TTS. Datele externe și
rezultatele rămân în directoarele ignorate de Git.

- Wikimedia Commons: [API Imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo),
  [TimedMediaHandler/videoinfo](https://www.mediawiki.org/wiki/Extension:TimedMediaHandler/API),
  [dimensiuni standard thumbnails](https://www.mediawiki.org/wiki/Common_thumbnail_sizes).
  Fiecare fișier are licență proprie; autorul, pagina originală, licența/URL și
  attribution se păstrează din extmetadata. Originalul și rendition-ul descărcat
  sunt identificate separat; SHA1 original nu este aplicat transcodării/thumbnail-ului.
- Openverse: [API și proprietăți media](https://docs.openverse.org/meta/media_properties/api.html),
  [API](https://api.openverse.org/v1/). Indexul nu acordă o licență nouă; sursa,
  autorul și licența fiecărui rezultat sunt păstrate. Adapterul actual caută imagini.
- Pexels: [API oficial](https://www.pexels.com/api/documentation/),
  [licență](https://www.pexels.com/license/). Integrare opțională cu cheie prin mediu,
  credit furnizor/fotograf și link original; biblioteca este locală pentru montaj,
  nu republicare ca serviciu de stock concurent. Proba live rămâne BLOCKED fără cheie.

Licențele CC BY/CC BY-SA/CC0 din proba reală sunt păstrate pe fiecare asset în
bibliotecă și în credits JSON/Markdown; CC BY-SA are obligații distincte de CC BY.
Provenance completă și succesul tehnic nu constituie aprobarea juridică/editorială
a unui material. Nu se publică automat LICENSE_UNKNOWN; aprobarea explicită este
jurnalizată. Nu au fost descărcate modele AI și nu se folosește cloud implicit.

### Completare probe assets — 2026-10-18 UTC

Fără dependențe/model/font/executabil nou. Preview-ul în trei cadre folosește
Pillow și FFmpeg deja documentate; importul/checksumul folosesc biblioteca standard.
Clipul Wikimedia selectat este „Bucharest - evening on Lacul Lebedelor, with crows”,
Joe Mabel, [pagina fișierului](https://commons.wikimedia.org/wiki/File:Bucharest_-_evening_on_Lacul_Lebedelor,_with_crows.webm),
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0).
Originalul/rendition-ul, checksumul și data descărcării sunt păstrate separat
în biblioteca privată și credits. Clipul are audio în sursă; rendererul îl omite.
Utilizarea în probă este ilustrativă și etichetată, fără a pretinde că arată
un eveniment din narațiune. Celelalte imagini păstrează propriile CC BY 3.0,
CC BY-SA 3.0/3.0 RO sau CC0; nu sunt relicențiate uniform.
Documentația oficială [Pexels API](https://www.pexels.com/api/documentation/)
a fost reverificată la această reluare pentru endpointul `/v1/videos/search`;
proba live rămâne BLOCKED fără `PEXELS_API_KEY`. Fără publicare externă.

Alternativele video locale din aceeași probă păstrează licențe proprii:
„Winter in Bucharest February 2012”, Eugen14Simion, CC BY-SA 3.0;
„Filmare cu drona la Biblioteca Centrală Universitară din Iasi”, Drone in air,
CC BY 3.0. Paginile originale/URL-urile licențelor și atribuirea integrală sunt în
`work/media/asset-discovery-20261018/discovery-summary.json`, biblioteca locală și
review-full. Corecțiile ulterioare de layout nu schimbă proveniența asset-urilor.


## REC Studio local — 2026-10-20 UTC

Interfața Studio folosește numai biblioteca standard Python (HTTP server,
threading/subprocess, JSON/hashlib/fcntl) și HTML/CSS/JavaScript scrise în proiect.
Nu adaugă framework-uri, npm packages, CDN, Electron, fonturi, modele sau servicii
cloud. Preview-urile ASS reutilizează Pillow, FFmpeg/libass și fonturile deja
documentate; narațiunea Piper și alinierea românească își păstrează proveniența.
Waveform-ul opțional utilizează Web Audio disponibil în browser, fără bibliotecă
externă. Playwright/Chromium 149.0.7827.55 existente sunt folosite numai la teste;
nu se distribuie și nu se instalează un browser nou. Asset-urile personale,
licențele/provenance și fixture-urile tehnice din probe rămân private/ignorate Git.

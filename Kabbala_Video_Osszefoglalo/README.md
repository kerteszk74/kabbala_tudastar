# YouTube-videók magyar összefoglalása

A program egy YouTube-videó, csatorna vagy lejátszási lista hangjából magyar
YouTube-leírást készít. A teljes hangot elemzi, nem a címből vagy feliratból
következtet. A leírás rövid összefoglalót, hang alapján becsült időbélyeges
tartalomjegyzéket, fogalommagyarázatokat, 3–4 témához illő hashtaget és
lehetőség szerint kapcsolódó Zohár-témákat tartalmaz. Az időpontokat és a szöveg pontosságát közzététel
előtt érdemes meghallgatással ellenőrizni.

## Előkészületek

Python 3.10 vagy újabb, az `ffmpeg`, internetelérés, valamint Google Cloud
hitelesítés és a Vertex AI használatához szükséges jogosultság és számlázás
szükséges. A videó letöltéséhez a hozzáférésre és felhasználásra vonatkozó
szabályokat tartsd be.

PowerShellben, a projekt mappájából:

```powershell
py -3 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
gcloud auth application-default login
```

Ha a `venv` már létezik, az első parancs kihagyható. Az ADC beállításához
Google Cloud CLI is szükséges; más, szabványos ADC-forrás is használható.
API-kulcsot a program nem használ. A projekt
`graphic-pathway-499620-n2`, a régió alapértéke `global`, a modellé
`gemini-3.8-flash`. A modellhez hozzáférés és megfelelő kvóta szükséges;
a Vertex AI-hívások költséggel járhatnak.

Az `ffmpeg` legyen a PATH-ban. Telepítés után új terminál nyitása helyett
az aktuális PowerShellben frissíthető a gépi és felhasználói PATH:

```powershell
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:Path
ffmpeg -version
```

A YouTube JavaScript-feladatainak megoldásához a yt-dlp a PATH-ban található
Deno futtatókörnyezetet használja. Ha a folyamat PATH-jában nincs Deno,
a program a Windows gépi és felhasználói PATH-beállításaiban is megkeresi.
A yt-dlp szükség esetén letölti
az EJS összetevőit a GitHubról. Deno vagy GitHub-hozzáférés hiányában továbbra
is jelentkezhetnek figyelmeztetések, illetve hiányozhatnak formátumok.
A yt-dlp három újrapróbálkozást használ a letöltésekre és a töredékekre,
letöltés előtt 2–5 másodpercet vár, és a `web`, `mweb`, valamint a yt-dlp
alapértelmezett YouTube-klienseit próbálja. A `bestaudio/best` beállítás
külön hangsáv hiányában hangot is tartalmazó videót tölt le, amelyből az
`FFmpegExtractAudio` kompakt MP3-at készít. Ezek a beállítások nem
garantálják a 403-as hibák megszűnését.

## Használat

```powershell
.\venv\Scripts\python.exe .\summarize_youtube.py --help
.\venv\Scripts\python.exe .\summarize_youtube.py --url "https://www.youtube.com/watch?v=VIDEOAZONOSITO"
.\venv\Scripts\python.exe .\summarize_youtube.py --url "https://www.youtube.com/@csatorna" --limit 3
.\venv\Scripts\python.exe .\summarize_youtube.py --url "https://www.youtube.com/playlist?list=LISTAAZONOSITO" --limit 3 --out ".\leirasok"
.\venv\Scripts\python.exe .\summarize_youtube.py --url "https://www.youtube.com/watch?v=VIDEOAZONOSITO" --force
.\venv\Scripts\python.exe .\summarize_youtube.py --index-only
```

A `--limit` alapértéke 1. Csatornánál a legutóbbi feltöltéseket, lejátszási
listánál a lista videóinak feltöltési dátum szerinti legújabb elemeit választja
ki; utóbbihoz a teljes lista metaadatainak lekérése szükséges lehet. A limit a
kiválasztott videók számára vonatkozik: az átugrottak is beleszámítanak, és
helyettük a program nem keres további videókat. A modell
és a régió opcionálisan `--model`, illetve `--location` argumentummal
módosítható.

A program a feldolgozandó videók között három másodpercet vár. Egy videó
metaadat- vagy feldolgozási hibáját naplózza, majd folytatja a következővel;
a végén felsorolja a hibákat, és hiba esetén 1-es kilépési kódot ad. A teljes
lista lekérésének vagy a közös inicializálásnak a hibája továbbra is leállítja
a futást. Lejátszási lista hibás metaadatú elemeinél a valóban legújabb
videók kiválasztása nem garantálható; a program a sikeresen beolvasott elemek
közül választ, és minden metaadathibát jelent, akár a limiten kívülit is.

A kimenet alapértelmezésben az `output` mappába kerül, videónként azonos
tartalmú `.txt` és `.md` fájlként. Ha a kimeneti mappában már van
`*_<videóazonosító>.txt` fájl, a program címváltozás esetén is átugorja a
videót, hangletöltés és modellhívás nélkül. A `--force` kapcsolóval újra
feldolgozza és az aktuális cím szerinti azonos nevű fájlokat felülírja;
eltérő régi című fájlokat nem töröl. Az ideiglenes hangfájlokat a program feldolgozás
után törli. A 8 óránál hosszabb videókat, a 200 MB-nál nagyobb tömörített
hangfájlokat és az élő vagy még el nem indult adásokat nem dolgozza fel.

A program a modell hashtagjeiből eltávolítja a szóközöket és a betűn vagy
számon kívüli karaktereket a kezdő `#` után. A duplikátumokat kis- és
nagybetűtől függetlenül szűri, és szükség esetén a `#Kabbala`, `#Zohár`,
`#BneiBaruch` címkékkel egészíti ki a listát legalább három elemre.

A futás végén a projekt gyökerében frissül az [INDEX.md](./INDEX.md).
A kiválasztott kimeneti mappa (alapból `output`, vagy a `--out` értéke)
összes mentett összefoglalóját videóazonosító szerint csoportosítja. A
táblázat a meglévő fájlokra és a YouTube-videókra mutató linkeket, a
kulcsfogalmakat és az első bekezdést tartalmazza. A `--index-only`
csak az indexet frissíti, URL, internetkapcsolat és ADC-hitelesítés nélkül.

## Tudástár és adatkezelés

A program helyben beolvassa a
`C:\Users\xzy\GemiKert_AI_agent\zohar_summaries.json` fájl hierarchikus
csomópontjait, és BM25 szövegkereséssel legfeljebb három kapcsolódó témát
választ ki a videó címe és a generált összefoglaló alapján. A témalista után
egyszer szerepel a Tudástár kezdőlapjára mutató hivatkozás; az oldal nem támogat
közvetlen csomópont-hivatkozást. A találatok relevanciáját ellenőrizni kell.
Hiányzó vagy hibás JSON esetén a program figyelmeztet, és tudástári
kapcsolatok nélkül folytatja; találat hiányakor szintén figyelmeztet.

A hangot és a videó címét a program elküldi a Vertex AI-nak feldolgozásra.
A helyi Tudástár JSON-t nem tölti fel. A generált tartalom és időbélyegek
nem garantáltan pontosak; hibás modellválasz esetén a program egyszer újra
próbálkozik, majd hibaüzenettel leáll.

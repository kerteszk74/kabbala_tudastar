# Zohár – Interaktív Gondolattérkép és Fogalomtár

A Zohár helyi dokumentumának első 200 bekezdése alapján készített magyar
hierarchikus teszt-gondolattérkép. A témákra kattintva a jobb oldali panel
rövid fogalommagyarázatot jelenít meg. A minta nem a teljes mű feldolgozása.

## Élő elérés

GitHub Pages: `https://<felhasznalo>.github.io/<repo-nev>/`

A hivatkozás helykitöltő: a közzététel után cseréld a tényleges címre.
A térkép Markmap-függőségei külső CDN-ről töltődnek be, ezért internetkapcsolat
szükséges.

## Google Sites beágyazás

Az új Google Webhelyek szerkesztőjében válaszd a **Beszúrás → Beágyazás →
Beágyazási kód** lehetőséget, és használd a tényleges Pages-címet:

```html
<iframe src="https://<felhasznalo>.github.io/<repo-nev>/" width="100%" height="750px" frameborder="0"></iframe>
```

Kattints a **Tovább**, majd a **Beszúrás** gombra, méretezd a keretet, és
tedd közzé a Google Webhelyet. A beágyazás tényleges működését a közzétett
oldalon külön ellenőrizni kell.

## GitHub Pages beállítása

A tároló **Settings → Pages → Build and deployment** részén válaszd a
**Deploy from a branch** módot, a `main` ágat és a `/docs` mappát, majd
mentsd a beállítást. A GitHub az oldal elkészülése után megjeleníti a valódi
URL-t. A konfigurációhoz és az oldal élesítéséhez megfelelő jogosultság kell.

## Fájlok

- `docs/index.html` – a térkép és az oldalsáv.
- `docs/zohar_summaries.json` – a panel által relatív URL-ről betöltött adatok.
- `input/zohar_summaries.json` – az összefoglalók szerkeszthető forrása.
- `output/mindmap_zohar_teszt.md` – a térkép Markdown-forrása.
- `scripts/generate_mindmap.py`, `scripts/mindmap_viewer.html` és
  `scripts/build_zohar_publication.py` – a megjelenítő és a csomag generálása.

A publikációs mappa helyi ellenőrzéséhez indíts HTTP-kiszolgálót:

```powershell
py -3 -m http.server 8000 --directory docs
```

Nyisd meg a `http://localhost:8000/` címet. A böngészők biztonsági szabályai
miatt a JSON betöltése közvetlen `file://` megnyitásnál nem garantált.
Az újragenerálás előtt a korábbi `docs/index.html` és
`docs/zohar_summaries.json` fájlokat kézzel át kell nevezni vagy eltávolítani;
az építő nem írja felül őket:

```powershell
py -3 scripts\build_zohar_publication.py
```

# Zohár – hibrid gondolattérkép és teljes forráskereső

A 779 csomópontos magyar tematikus gondolattérkép eredeti felépítése és
magyarázatai megmaradnak. Négy történeti témacsoportja **nem** a teljes könyv
kötetszámozása. A jobb oldali ajánlások, a forrásböngésző és a tematikus kereső
már az egységes, kizárólag helyi Zohár-könyvből
(`forrasok/zohar/zohar_teljes_konyv.md`) épülnek:

- **13 kötet, 2165 fejezet, 23 555 számozott szöveghely**;
- az eredeti 23 484-es számláláshoz képest 71 további pontot azonosítunk a
  számok előtti láthatatlan írásirány-jelek eltávolításával;
- három, arab számjegyes pontokra nem tagolt forrásszakasz is kereshető;
- az eredeti pontszámok nem változnak; ismétlődő szám esetén az előfordulás
  sorszáma is megkülönbözteti a helyeket;
- magyar–angol kabbalisztikai szinonimák, 13 kötetes szűrő, kiemelt találatok
  és hivatalos olvasólinkek; teljes pontszöveg csak helyi előnézetben.

Minden forráslink felirata:
`Zohár mindenkinek - Rashbi | [eredeti fejezetcím]`.
A link az eredeti Kabbalah Media-fejezetre mutat, a pontos pontszám mellette
látható. Nem képzünk nem létező webes pont-horgonyokat. A csomópontok
forrásajánlásai reprodukálható kulcsszavas rangsorolások, **nem ellenőrzött
értelmezések**. A régi, fel nem oldható belső idézetazonosítókat eltávolítjuk,
a magyar magyarázatokat nem generáljuk újra AI-val.

## Újraépítés

```powershell
python .\build_zohar_tudastar.py
```

Az építés csak a helyi könyvet és a meglévő magyar magyarázatokat olvassa;
nincs hálózati vagy modellhívás. Mindhárom korrigált darabszámot ellenőrzi.
A `scripts\export_web_rag.py` és a `scripts\build_zohar_publication.py`
parancs ugyanennek az építőnek a kompatibilitási belépési pontja.

Fontos fájlok:

- [build_zohar_tudastar.py](build_zohar_tudastar.py): könyvparszolás, indexek,
  csomópont-ajánlások és szöveg nélküli statikus publikáció.
- [index.html](index.html), [assets/](assets/): a honlap szerkeszthető forrása.
- [zohar_summaries.json](zohar_summaries.json): a megőrzött magyar magyarázatok.
- `data/zohar_chapters_index.json`: teljes fejezetjegyzék és ponttartományok.
- `data/zohar_search_index.json`: tömör fordított keresőindex az összes ponthoz,
  pontszámokkal és legfeljebb nyolc rendezett témakulcsszóval; szöveget,
  mondatokat, idézeteket vagy szósorrendet nem tartalmaz. Az oldal indulásakor
  **nem** töltődik be.
- `data/zohar_node_references.json`: pontos ponthivatkozások és kulcsszavak
  a 779 térképtémához.
- `data/zohar_points_index.json`: teljes, helyi pontszöveg-index a
  leckefeldolgozóhoz; Gitből kizárva.
- `data/chapters/`: a 2165 teljes szövegű, **kizárólag helyi**, Gitből kizárt
  JSON-előnézet. A `docs/data/chapters/` útvonal is kizárt.
- [docs/](docs/): kész statikus honlap a szükséges könnyített indexekkel és
  metaadatokkal. Sem nyers könyvet, sem teljes pontindexet, sem teljes szövegű
  előnézeteket nem másolunk ide. A korábbi generált előnézetmásolatokat az építő
  csak akkor távolítja el innen, ha bájtra egyeznek a megőrzött helyi példánnyal.
- [web_assets_manifest.json](web_assets_manifest.json): az összes
  futáskor használt webes fájl relatív útvonala, bájtmérete és SHA-256 lenyomata.
  Az építő minden ilyen fájlnál 15 MB alatti méretet követel meg; ugyanaz a jegyzék
  és ugyanazok a futásidejű fájlok a `docs` tükörcsomagban is rendelkezésre állnak.
  A `.gitattributes` és az építő LF sorvégekkel tartja egyezőnek a helyi,
  Gitben tárolt és kiszolgált fájlok bájtjait, Windowson is.

A nyilvános böngésző induláskor csak a térképet, fejezet-metaadatokat és
kulcsszavas ponthivatkozásokat kéri le. A teljes szövegekhez nem indít kérést.
A keresőindex csak kereséskor vagy egy fejezet pontjegyzékének megnyitásakor
töltődik be. A találat pontszámot, kiemelt kulcsszavakat és hivatalos olvasólinket
mutat; nem állítja, hogy a kulcsszólista idézet lenne.

Teljes szövegű előnézetet kizárólag a `localhost`, `127.0.0.1` és `[::1]`
kiszolgálókról próbálunk betölteni. A hiányzó helyi fájl (HTTP 404) esetén is a
metaadat és a hivatalos olvasólink jelenik meg; más letöltési/adathibákat kijelzünk.
A nyilvános séma 3-as verziójú; a leckefeldolgozó helyi teljes pontindexe továbbra
is 2-es verziójú.

Az eredeti könyv, minden teljes szövegű JSON és a letöltési gyorsítótár helyben
marad, Git-kizárással. Nyilvános feltöltésre nincs teljes könyvszöveg-terjesztési
engedély, ezért ezeket nem publikáljuk. A szövegek jogai a forrás jogosultjainál
maradnak. Hivatalos feltételek: https://www.kabbalah.info/en/terms-of-use/

## Helyi indítás és tesztek

```powershell
python -m http.server 8000 --bind 127.0.0.1
# Böngésző: http://127.0.0.1:8000/
python -m unittest discover -s tests -p test_zohar_tudastar.py
node --test .\tests\test_zohar_search.cjs
```

A JSON-betöltéshez HTTP-kiszolgáló szükséges; a közvetlen `file://` megnyitás
nem támogatott. A Markmap és D3 külső CDN-ről érkezik.
Az opcionális AI-válasz csak külön megadott kulccsal és felhasználói
kérdésküldéssel indul; az építés és a tesztek nem hívnak fizetős AI-t.

## Leckefeldolgozó-integráció

A szomszédos `Kabbala_Video_Osszefoglalo` projekt `enrich_zohar_source.py`
szkriptje alapértelmezésben a helyi teljes pontindexet használja.
A `--exclude-lesson 1` az első lecke már felhasznált, pontos új
forráshelyeit zárja ki. A régi, pontazonosító nélküli lecke-hivatkozásokat
előbb frissíteni kell; automatikus, pontatlan megfeleltetés nem történik.

A helyi Chroma/Ollama segédeszköz is az egységes könyvből építkezik;
a régi négy dokumentumos adatbázist a `scripts\zohar_rag.py --index`
paranccsal kell újraépíteni, mielőtt újra használható.

## GitHub Pages és Google Sites

A statikus publikáció helye: a tároló **Settings → Pages** beállításában
**Deploy from a branch → main → / (root)**. Az élesítéshez a `main` ágra
kell feltölteni a gyökérben lévő honlapot és webes adatait. A gyökérpublikálás
megmarad, így a tároló korábbi videó-összefoglalóinak útvonalai sem változnak.
Az oldal címe: `https://kerteszk74.github.io/kabbala_tudastar/`.
A `.nojekyll` jelzővel a fájlokat Jekyll-átalakítás nélkül szolgáljuk ki;
a `docs` mappában önálló, kizárólag metaadatokat tartalmazó tükörcsomag is készül.
Minden helyi szkript- és adatútvonal relatív, így a projekt alútvonala is működik.
A D3/Markmap CDN-címek és az opcionális Gemini API szándékosan külső HTTPS-címek.

Google Sites esetén **Beszúrás → Beágyazás → Beágyazási kód**:

```html
<iframe src="https://kerteszk74.github.io/kabbala_tudastar/" width="100%" height="750px" frameborder="0"></iframe>
```

Az élesítés és a beágyazás működését közzététel után külön kell ellenőrizni.

#!/usr/bin/env python3
"""
MonEsti44 : préparation des ventes DVF de Loire-Atlantique pour le site.

- Télécharge les fichiers « DVF géolocalisées » (data.gouv.fr) du département 44.
- Ne garde que des VENTES signées de maisons et d'appartements (prix net vendeur :
  le prix déclaré à l'acte, hors honoraires d'agence à la charge de l'acquéreur
  et hors frais de notaire). Aucune annonce, aucun prix FAI.
- Écrit deux jeux de tuiles :
    data/recent/<tuile>.json  -> ventes des 24 derniers mois disponibles
    data/y2018/<tuile>.json   -> ventes de l'année 2018 (utilisées seulement
                                 quand il n'y a pas assez de ventes récentes)
- Écrit data/meta.json (période couverte, nombre de ventes, date de mise à jour).

Usage : python scripts/build_dvf.py [--source-dir dossier_de_csv_locaux]
Les fichiers locaux éventuels doivent s'appeler <année>-44.csv ou <année>-44.csv.gz.
"""
import csv, gzip, io, json, math, os, re, sys, argparse, datetime, urllib.request, collections

DEP = "44"
BASE = "https://files.data.gouv.fr/geo-dvf"
OUT = os.environ.get("MONESTI_OUT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
TILE = 50  # 1/50e de degré, environ 2,2 km x 1,5 km
MONTHS_RECENT = 24


def tile_key(lat, lon):
    return f"{math.floor(lat * TILE)}_{math.floor(lon * TILE)}"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "monesti44-build"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def open_year(year, source_dir):
    """Renvoie un lecteur CSV pour l'année demandée, ou None."""
    if source_dir:
        for name in (f"{year}-{DEP}.csv.gz", f"{year}-{DEP}.csv"):
            p = os.path.join(source_dir, name)
            if os.path.exists(p):
                raw = open(p, "rb").read()
                return csv.DictReader(io.StringIO(gunzip(raw).decode("utf-8")))
    urls = [f"{BASE}/latest/csv/{year}/departements/{DEP}.csv.gz"]
    if year <= 2019:
        # Les années anciennes sortent du jeu « latest » : on cherche dans les versions archivées.
        try:
            listing = fetch(BASE + "/").decode("utf-8", "ignore")
            releases = sorted(set(re.findall(r'href="(\d{4}-\d{2}(?:-\d{2})?)/?"', listing)), reverse=True)
            urls += [f"{BASE}/{r}/csv/{year}/departements/{DEP}.csv.gz" for r in releases]
        except Exception as e:
            print("  liste des versions indisponible :", e)
    for u in urls:
        try:
            raw = fetch(u)
            print(f"  {year} : {u} ({len(raw)//1024} Ko)")
            return csv.DictReader(io.StringIO(gunzip(raw).decode("utf-8")))
        except Exception:
            continue
    print(f"  {year} : introuvable")
    return None


def gunzip(raw):
    return gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw


def num(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def sales_from(reader):
    """Regroupe les lignes par mutation et ne garde que les ventes d'UN seul logement."""
    muts = collections.defaultdict(lambda: {"locaux": {}, "row": None, "terrain": 0.0})
    for r in reader:
        if r.get("nature_mutation") != "Vente":
            continue
        m = muts[r["id_mutation"]]
        m["row"] = m["row"] or r
        st = num(r.get("surface_terrain")) or 0
        m["terrain"] = max(m["terrain"], st)
        t = r.get("type_local")
        if t in ("Maison", "Appartement"):
            key = (t, r.get("surface_reelle_bati"), r.get("lot1_numero"), r.get("nombre_pieces_principales"))
            m["locaux"][key] = r
        elif t == "Local industriel. commercial ou assimilé":
            m["locaux"][("pro", r.get("id_parcelle"))] = None  # vente mixte : exclue
    out = []
    for mid, m in muts.items():
        loc = list(m["locaux"].values())
        if len(loc) != 1 or loc[0] is None:
            continue
        r = loc[0]
        prix, surf = num(r.get("valeur_fonciere")), num(r.get("surface_reelle_bati"))
        lat, lon = num(r.get("latitude")), num(r.get("longitude"))
        if not prix or not surf or lat is None or lon is None:
            continue
        if surf < 9 or prix < 15000:
            continue
        pm2 = prix / surf
        if pm2 < 400 or pm2 > 15000:
            continue
        date = r["date_mutation"]
        out.append({
            "d": date,
            "t": 0 if r["type_local"] == "Maison" else 1,
            "p": int(round(prix)),
            "s": int(round(surf)),
            "n": int(num(r.get("nombre_pieces_principales")) or 0),
            "la": round(lat, 5),
            "lo": round(lon, 5),
            "v": (r.get("adresse_nom_voie") or "").title()[:40],
            "c": r.get("nom_commune") or "",
            "te": int(m["terrain"]) if r["type_local"] == "Maison" else 0,
        })
    return out


def write_tiles(sales, folder):
    path = os.path.join(OUT, folder)
    os.makedirs(path, exist_ok=True)
    for f in os.listdir(path):
        if f.endswith(".json"):
            os.remove(os.path.join(path, f))
    tiles = collections.defaultdict(list)
    for s in sales:
        # format compact : [date, type, prix, surface, pièces, lat, lon, voie, commune, terrain]
        tiles[tile_key(s["la"], s["lo"])].append([s["d"], s["t"], s["p"], s["s"], s["n"], s["la"], s["lo"], s["v"], s["c"], s["te"]])
    for k, rows in tiles.items():
        with open(os.path.join(path, k + ".json"), "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))
    return len(tiles)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir")
    a = ap.parse_args()
    this_year = datetime.date.today().year
    print("Ventes récentes :")
    recent = []
    for y in range(this_year, this_year - 4, -1):
        rd = open_year(y, a.source_dir)
        if rd:
            recent += sales_from(rd)
    if not recent:
        sys.exit("Aucune donnée récente : arrêt sans rien modifier.")
    dmax = max(s["d"] for s in recent)
    dm = datetime.date.fromisoformat(dmax)
    dmin = datetime.date(dm.year - MONTHS_RECENT // 12, dm.month, min(dm.day, 28))
    recent = [s for s in recent if s["d"] > dmin.isoformat()]
    nt = write_tiles(recent, "recent")
    print(f"  {len(recent)} ventes du {dmin} au {dmax}, {nt} tuiles")

    print("Année 2018 :")
    meta_old = {}
    mp = os.path.join(OUT, "meta.json")
    if os.path.exists(mp):
        meta_old = json.load(open(mp, encoding="utf-8"))
    rd = open_year(2018, a.source_dir)
    n2018 = meta_old.get("ventes_2018", 0)
    if rd:
        s18 = [s for s in sales_from(rd) if s["d"].startswith("2018")]
        write_tiles(s18, "y2018")
        n2018 = len(s18)
        print(f"  {n2018} ventes 2018")
    else:
        print("  2018 non téléchargée : les tuiles 2018 existantes sont conservées.")

    meta = {
        "departement": DEP,
        "periode_debut": dmin.isoformat(),
        "periode_fin": dmax,
        "ventes_recentes": len(recent),
        "maisons": sum(1 for s in recent if s["t"] == 0),
        "appartements": sum(1 for s in recent if s["t"] == 1),
        "ventes_2018": n2018,
        "tuile": TILE,
        "mise_a_jour": datetime.date.today().isoformat(),
        "source": "DVF géolocalisées, data.gouv.fr (DGFiP / Etalab)",
    }
    json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("meta.json écrit.")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Scrape 3GWIN (Journal des ventes mix du jour) et écrit meilleure_vente.json :
LA meilleure VENTE = la FACTURE du jour qui totalise le plus de marge,
avec le vendeur, l'agence, le total et le détail des articles (sans nom client).
L'URL 3GWIN (avec token) est lue depuis la variable d'environnement GWIN_VENTES_URL
(secret GitHub) — jamais en clair dans ce code (repo public).
"""
import os, re, json, datetime, urllib.request
from html.parser import HTMLParser

URL = os.environ.get("GWIN_VENTES_URL", "").strip()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "meilleure_vente.json")

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.tables=[]; self.cur=None; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag=="table": self.cur=[]; self.tables.append(self.cur)
        elif tag=="tr" and self.cur is not None: self.row=[]; self.cur.append(self.row)
        elif tag in ("td","th") and self.row is not None: self.cell=[]
    def handle_endtag(self, tag):
        if tag in ("td","th") and self.cell is not None:
            self.row.append(re.sub(r"\s+"," ","".join(self.cell)).strip()); self.cell=None
        elif tag=="tr": self.row=None
        elif tag=="table": self.cur=None
    def handle_data(self, d):
        if self.cell is not None: self.cell.append(d)

def numf(x):
    x=re.sub(r"[^0-9,\-\.]","",str(x)).replace(",",".")
    try: return float(x)
    except: return 0.0

def main():
    if not URL:
        raise SystemExit("GWIN_VENTES_URL manquant (secret GitHub non défini).")
    html = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent":"Mozilla/5.0"}), timeout=40).read().decode("utf-8","replace")
    p=TableParser(); p.feed(html)
    if not p.tables: raise SystemExit("Aucun tableau dans la réponse 3GWIN (token expiré ?).")
    grid=max(p.tables, key=len)
    hdr=next((r for r in grid[:6] if "Vendeur" in r and "Marge" in r), grid[0])
    ci={c.strip():i for i,c in enumerate(hdr)}
    iDate,iAg,iV,iFac,iD,iFam,iActe,iM = (ci.get("Date"),ci.get("Ag."),ci.get("Vendeur"),
        ci.get("N° Fac."),ci.get("Désignation"),ci.get("FAMILLE"),ci.get("Type Acte"),ci.get("Marge"))
    today=datetime.date.today().strftime("%Y%m%d")
    fac={}
    for r in grid:
        if iM is None or len(r)<=iM: continue
        v=(r[iV] if iV is not None else "").strip()
        if not v or v=="Vendeur": continue
        if iDate is not None and r[iDate].strip()!=today: continue
        f=(r[iFac] if iFac is not None else "").strip()
        if not f: continue
        o=fac.setdefault(f, {"fac":f,"vendeur":v,"agence":(r[iAg].strip() if iAg is not None else ""),
                             "articles":[], "total":0.0})
        label=(r[iD].strip() if iD is not None else "") or (r[iActe].strip() if iActe is not None else "") or (r[iFam].strip() if iFam is not None else "") or "Article"
        m=numf(r[iM]); o["articles"].append({"desig":label, "marge":round(m,2)}); o["total"]+=m
    top=sorted(fac.values(), key=lambda x:-x["total"])
    for o in top: o["total"]=round(o["total"],2)
    best = top[0] if top else None
    data={
      "maj": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
      "date": today,
      "nb_factures": len(fac),
      "meilleure_vente": best,                      # vendeur, agence, total, articles[]
      "top": [{"vendeur":o["vendeur"],"agence":o["agence"],"total":o["total"],"nb":len(o["articles"])} for o in top[:5]],
    }
    json.dump(data, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print("OK meilleure_vente.json :", (best["vendeur"]+" "+str(best["total"])+" EUR") if best else "aucune vente du jour")

if __name__=="__main__":
    main()

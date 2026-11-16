#!/usr/bin/env python3
"""Range dans le carnet une fiche par session passée avec Claude Code : ce qui a été construit.

Pour chaque conversation enregistrée par Claude Code (~/.claude/projects/*/*.jsonl), le
programme écrit une fiche dans <carnet>/sessions/ : la demande de départ (coupée et nettoyée),
les fichiers écrits, les titres des commits, et un statut. Le statut « construit-non-livre »
signale ce qui a été construit sans jamais être mis en service : c'est la matière du résumé
« ce qui dort » de la relecture de nuit.

Vie privée : la fiche reste au niveau des métadonnées. Jamais le contenu des échanges ni des
commandes ; tout ce qui ressemble à une clé, un jeton ou un mot de passe est remplacé par
« (masqué) ».

Les sessions sans intérêt (tâches automatiques, simple exploration, une ou deux retouches)
vont dans <carnet>/.sessions/, un dossier caché qu'Obsidian n'affiche pas.

Une fiche déjà écrite est gardée même quand Claude Code a effacé sa conversation.

Où le mettre : dans <carnet>/_systeme/. Le carnet est le dossier parent.

Réglages, par variable d'environnement :
  SESSIONS_CLAUDE  le dossier des conversations (défaut : ~/.claude/projects)
  MEMOIRE_CLAUDE   le dossier de la mémoire, pour repérer ce qui a été livré plus tard
                   (même défaut que miroir.py)
  CACHE_SESSIONS   le fichier de cache (défaut : ~/.cache/relecture-de-nuit/sessions.json)
"""
import json
import os
import pathlib
import re

CARNET = pathlib.Path(__file__).resolve().parent.parent
MAISON = pathlib.Path.home()
SESSIONS_CLAUDE = pathlib.Path(os.environ.get("SESSIONS_CLAUDE", MAISON / ".claude/projects"))
MEMOIRE_CLAUDE = pathlib.Path(os.environ.get(
    "MEMOIRE_CLAUDE", MAISON / ".claude/projects" / str(MAISON).replace("/", "-") / "memory"))
CACHE = pathlib.Path(os.environ.get("CACHE_SESSIONS", MAISON / ".cache/relecture-de-nuit/sessions.json"))
FICHES = CARNET / "sessions"
ARCHIVE = CARNET / ".sessions"
STATUTS_ARCHIVES = {"automatique", "notes", "exploration", "petit"}

SECRET = re.compile(r"(sk-[A-Za-z0-9_\-]{12,}|api[_-]?key\S*|token\S*|bearer\s+\S+|passw\S*|"
                    r"mot de passe\s*\S*|-----BEGIN|[A-Fa-f0-9]{32,})", re.I)
COMMIT = re.compile(r'git commit[^\n]*?-m\s+["\']([^"\']{3,120})["\']')
LIVRE = re.compile(r"\b(git commit|git push|scp |rsync |deploy|npm publish|gh release)\b")
OUTILS_ECRITURE = {"Write", "Edit", "NotebookEdit"}
NOTE_MEMOIRE = re.compile(r"/memory/[^/]+\.md$")
MARQUE_LIVRE = re.compile(r"(livré|en service|en ligne|déployé|shipped|deployed|\blive\b|commit\s+[0-9a-f]{6,})", re.I)
NOM_DE_FICHIER = re.compile(r"[\w\-]+\.(?:php|py|js|json|sh|sql|md)\b")


def masquer(s):
    return SECRET.sub("(masqué)", s or "")


def nom_du_projet(dossier):
    """Pour Alice, « -Users-alice-Documents-mon-projet » devient « mon-projet »."""
    prefixe = str(MAISON).replace("/", "-")
    if dossier.startswith(prefixe):
        dossier = dossier[len(prefixe):]
    morceaux = [m for m in dossier.strip("-").split("-") if m]
    if morceaux and morceaux[0] == "Documents":
        morceaux.pop(0)
    return "-".join(morceaux) or "maison"


def demande_de_depart(texte):
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", (texte or "").strip(), flags=re.S)
    return masquer(re.sub(r"\s+", " ", t).strip())[:400]


def lire_session(chemin):
    n_demandes = 0
    demande, debut, fin, branche = "", None, None, ""
    ecrits, commits, livre = set(), [], False
    for ligne in open(chemin, encoding="utf-8", errors="ignore"):
        try:
            d = json.loads(ligne)
        except Exception:
            continue
        ts = d.get("timestamp")
        if ts:
            debut, fin = debut or ts, ts
        branche = d.get("gitBranch") or branche
        message = d.get("message") or {}
        contenu = message.get("content", d.get("content"))
        if d.get("type") == "user":
            n_demandes += 1
            if not demande and isinstance(contenu, str) and len(demande_de_depart(contenu)) > 15:
                demande = demande_de_depart(contenu)
        elif d.get("type") == "assistant" and isinstance(contenu, list):
            for item in contenu:
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                entree = item.get("input") or {}
                fichier = entree.get("file_path") or entree.get("notebook_path")
                if item.get("name") in OUTILS_ECRITURE and fichier:
                    ecrits.add(fichier)
                elif item.get("name") == "Bash":
                    commande = entree.get("command") or ""
                    livre = livre or bool(LIVRE.search(commande))
                    commits += [masquer(m.group(1)) for m in COMMIT.finditer(commande)]
    return dict(n_demandes=n_demandes, demande=demande, debut=debut, fin=fin, branche=branche,
                ecrits=sorted(ecrits), commits=commits[:8], livre=livre)


def fichiers_livres_selon_la_memoire():
    """Les noms de fichiers cités dans une note de mémoire qui parle de travail livré."""
    noms = set()
    for p in MEMOIRE_CLAUDE.glob("*.md") if MEMOIRE_CLAUDE.is_dir() else []:
        t = p.read_text(encoding="utf-8", errors="ignore")
        if MARQUE_LIVRE.search(t):
            noms |= {m.group(0).lower() for m in NOM_DE_FICHIER.finditer(t)}
    return noms


LIVRES_PLUS_TARD = fichiers_livres_selon_la_memoire()


def statut(s):
    demande = (s.get("demande") or "").lstrip()
    if demande.startswith(("<scheduled-task", "<command-")):
        return "automatique"
    hors_memoire = [p for p in s["ecrits"] if not NOTE_MEMOIRE.search(p)]
    if s["ecrits"] and not hors_memoire:
        return "notes"
    if s["livre"]:
        return "livre"
    if len(hors_memoire) >= 3:
        # Un dossier qui a déjà sa conclusion ou son mode d'emploi a abouti dans une autre session.
        for p in hors_memoire:
            d = pathlib.Path(p).expanduser().parent
            if (d / "conclusion.txt").exists() or (d / "README.md").exists():
                return "conclu-ailleurs"
        noms = [os.path.basename(p).lower() for p in hors_memoire]
        if LIVRES_PLUS_TARD and sum(n in LIVRES_PLUS_TARD for n in noms) / len(noms) >= 0.5:
            return "livre-ailleurs"
        return "construit-non-livre"
    return "petit" if hors_memoire else "exploration"


def fiche(projet, sid, s, st):
    jour = (s["debut"] or "")[:10]
    lignes = ["---", f'aliases: ["session-{sid[:8]}"]',
              f"tags: [session, session/{st}, projet/{projet}]",
              f"projet: {projet}", f"date: {jour}", f"statut: {st}", "---", "",
              f"# {projet} : session {sid[:8]} ({jour})", "",
              f"Statut : `{st}`, {s['n_demandes']} demandes, {len(s['ecrits'])} fichiers écrits, "
              f"branche `{s['branche'] or 'aucune'}`", ""]
    if s["demande"]:
        lignes += ["Demande de départ :", f"> {s['demande']}", ""]
    if s["commits"]:
        lignes += ["Commits :"] + [f"- {c}" for c in s["commits"]] + [""]
    if s["ecrits"]:
        lignes += ["Fichiers écrits :"] + [f"- `{p.replace(str(MAISON), '~')}`" for p in s["ecrits"][:20]] + [""]
    if st == "construit-non-livre":
        lignes += ["> Des fichiers ont été écrits sans commit ni mise en ligne pendant la session : "
                   "à vérifier, c'est peut-être un projet qui dort.", ""]
    return "\n".join(lignes) + "\n"


def lire_cache():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def ecrire_si_change(chemin, texte):
    if not chemin.exists() or chemin.read_text(encoding="utf-8") != texte:
        chemin.write_text(texte, encoding="utf-8")


def main():
    for d in (FICHES, ARCHIVE):
        d.mkdir(parents=True, exist_ok=True)
    ancien_cache, cache, ecrites = lire_cache(), {}, set()
    compte = {}
    for dossier in sorted(p for p in SESSIONS_CLAUDE.glob("*") if p.is_dir()):
        projet = nom_du_projet(dossier.name)
        for jf in sorted(dossier.glob("*.jsonl")):
            st_fichier = jf.stat()
            cle = [st_fichier.st_mtime_ns, st_fichier.st_size]
            connu = ancien_cache.get(str(jf))
            s = connu["s"] if connu and connu["cle"] == cle else lire_session(jf)
            cache[str(jf)] = {"cle": cle, "s": s}
            if s["n_demandes"] == 0:
                continue
            st = statut(s)
            compte[st] = compte.get(st, 0) + 1
            dest = ARCHIVE if st in STATUTS_ARCHIVES else FICHES
            chemin = dest / f"{projet}__{jf.stem[:8]}.md"
            ecrire_si_change(chemin, fiche(projet, jf.stem, s, st))
            ecrites.add(chemin)
    # Une fiche qui a changé de dossier (archive ou non) ne doit pas rester en double.
    noms = {c.name for c in ecrites}
    for d in (FICHES, ARCHIVE):
        for f in d.glob("*.md"):
            if f not in ecrites and f.name in noms:
                f.unlink()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    print(f"{sum(compte.values())} sessions rangées, par statut : {compte}")


if __name__ == "__main__":
    main()

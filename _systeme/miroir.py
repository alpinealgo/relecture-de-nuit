#!/usr/bin/env python3
"""Recopie la mémoire de Claude Code dans le carnet Obsidian, puis refait sa page de sommaire.

Ce que fait le programme :
- il lit les notes de mémoire de Claude Code (un fichier .md par note) et les recopie dans
  <carnet>/memoire/<type>/, en ajoutant un alias pour que les deux formes de lien marchent
  dans Obsidian ([[project_mon_projet]] et [[mon-projet]]) ;
- il refait <carnet>/memoire/00_Sommaire.md.

Le dossier memoire/ est réécrit à chaque passage : n'y écrivez jamais à la main.

Filet de sécurité : un fichier présent dans l'ancien dossier memoire/ mais absent du nouveau
n'est pas effacé. Il est copié dans <carnet>/_secours/<horodatage>/, avec une ligne dans
<carnet>/_secours/JOURNAL.md. Une retouche faite à la main dans un fichier existant, elle,
est perdue : d'où la règle de ne jamais écrire dans memoire/.

Où le mettre : dans <carnet>/_systeme/. Le carnet est le dossier parent.

Réglage, par variable d'environnement :
  MEMOIRE_CLAUDE  le dossier de la mémoire de Claude Code. Par défaut, celui des sessions
                  lancées depuis votre dossier personnel :
                  ~/.claude/projects/<votre dossier personnel, les / remplacés par des ->/memory
"""
import datetime
import os
import pathlib
import re
import shutil
import tempfile

CARNET = pathlib.Path(__file__).resolve().parent.parent
MEMOIRE_CLAUDE = pathlib.Path(os.environ.get(
    "MEMOIRE_CLAUDE",
    pathlib.Path.home() / ".claude/projects" / str(pathlib.Path.home()).replace("/", "-") / "memory"))
MEMOIRE = CARNET / "memoire"
SECOURS = CARNET / "_secours"
HORODATAGE = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")

# Les quatre types de notes de la mémoire de Claude Code, et leur dossier dans le carnet.
DOSSIER_PAR_TYPE = {"project": "projets", "feedback": "retours", "reference": "references", "user": "profil"}
TITRE_PAR_TYPE = {"project": "Projets", "feedback": "Retours sur la façon de travailler",
                  "reference": "Références", "user": "Profil"}


def lire_entete(texte):
    """Rend (nom, description, type, position de la fin de l'en-tête ou -1)."""
    if not texte.startswith("---"):
        return None, "", "", -1
    fin = texte.find("\n---", 3)
    if fin == -1:
        return None, "", "", -1
    entete = texte[3:fin]
    nom = re.search(r"^name:\s*(.+)$", entete, re.M)
    desc = re.search(r'^description:\s*"?(.+?)"?\s*$', entete, re.M)
    typ = re.search(r"^\s*type:\s*(\w+)", entete, re.M)
    return (nom.group(1).strip() if nom else None,
            desc.group(1).strip() if desc else "",
            typ.group(1).strip() if typ else "",
            fin)


def type_de(nom_fichier, type_entete):
    for t in DOSSIER_PAR_TYPE:
        if nom_fichier.startswith(t):
            return t
    return type_entete if type_entete in DOSSIER_PAR_TYPE else "reference"


def preparer(dossier_neuf: pathlib.Path):
    """Écrit la copie de la mémoire dans dossier_neuf. Rend la liste (nom, type, description)."""
    notes = []
    for sous in DOSSIER_PAR_TYPE.values():
        (dossier_neuf / sous).mkdir(parents=True, exist_ok=True)
    sources = sorted(p for p in MEMOIRE_CLAUDE.glob("*.md") if p.name != "MEMORY.md")
    for chemin in sources:
        texte = chemin.read_text(encoding="utf-8")
        nom, desc, typ_entete, fin = lire_entete(texte)
        typ = type_de(chemin.name, typ_entete)
        ajout = f'aliases: ["{nom or chemin.stem}"]\ntags: [memoire/{typ}]\nsource: memoire-claude\n'
        if fin != -1:
            texte = texte[:fin + 1] + ajout + texte[fin + 1:]
        else:
            texte = f"---\n{ajout}---\n\n" + texte
        (dossier_neuf / DOSSIER_PAR_TYPE[typ] / chemin.name).write_text(texte, encoding="utf-8")
        notes.append((chemin.stem, typ, desc))
    if len(notes) != len(sources):
        raise RuntimeError(f"{len(sources)} notes attendues, {len(notes)} recopiées")
    sommaire = ["---", "tags: [memoire/sommaire]", "---", "", "# Sommaire de la mémoire", ""]
    for typ, titre in TITRE_PAR_TYPE.items():
        du_type = sorted((n, d) for n, t, d in notes if t == typ)
        if du_type:
            sommaire += [f"## {titre} ({len(du_type)})", ""]
            sommaire += [f"- [[{n}]] : {d}" if d else f"- [[{n}]]" for n, d in du_type]
            sommaire.append("")
    sommaire.append(f"*Recopié le {datetime.date.today().isoformat()}, {len(notes)} notes.*")
    (dossier_neuf / "00_Sommaire.md").write_text("\n".join(sommaire) + "\n", encoding="utf-8")
    return notes


def sauver_orphelins(ancien: pathlib.Path, neuf: pathlib.Path) -> list:
    """Copie dans _secours/ tout fichier de l'ancien dossier qui n'existe plus dans le neuf."""
    sauves = []
    if not ancien.exists():
        return sauves
    for p in ancien.rglob("*"):
        if not p.is_file() or p.name.startswith("."):
            continue
        rel = p.relative_to(ancien)
        if (neuf / rel).exists():
            continue
        dest = SECOURS / HORODATAGE / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        sauves.append(str(rel))
    return sauves


def noter_secours(sauves: list):
    if not sauves:
        return
    SECOURS.mkdir(parents=True, exist_ok=True)
    journal = SECOURS / "JOURNAL.md"
    neuf = not journal.exists()
    with journal.open("a", encoding="utf-8") as f:
        if neuf:
            f.write("# Fichiers mis de côté\n\nTrouvés dans memoire/ sans équivalent dans la nouvelle "
                    "copie : ils ont été copiés ici au lieu d'être effacés.\n\n")
        f.write(f"## {HORODATAGE}\n")
        f.write("".join(f"- `memoire/{r}` mis dans `_secours/{HORODATAGE}/{r}`\n" for r in sauves))
        f.write("\n")
    print(f"{len(sauves)} fichier(s) mis de côté dans {SECOURS / HORODATAGE}")


def remplacer(neuf: pathlib.Path) -> list:
    """Remplace memoire/ par la nouvelle copie, sans jamais effacer un fichier sans l'avoir sauvé."""
    sauves = []
    # Restes d'un passage précédent qui aurait planté avant la fin.
    for reste in CARNET.glob(".memoire.ancien-*"):
        sauves += sauver_orphelins(reste, MEMOIRE)
        shutil.rmtree(reste)
    ancien = CARNET / f".memoire.ancien-{os.getpid()}"
    if MEMOIRE.exists():
        MEMOIRE.rename(ancien)
    try:
        neuf.rename(MEMOIRE)
    except Exception:
        if ancien.exists() and not MEMOIRE.exists():
            ancien.rename(MEMOIRE)
        raise
    sauves += sauver_orphelins(ancien, MEMOIRE)
    if ancien.exists():
        shutil.rmtree(ancien)
    return sauves


def main():
    if not MEMOIRE_CLAUDE.is_dir():
        raise SystemExit(f"Dossier de mémoire introuvable : {MEMOIRE_CLAUDE} (réglez MEMOIRE_CLAUDE)")
    with tempfile.TemporaryDirectory(prefix="miroir-", dir=CARNET / "_systeme") as tmp:
        neuf = pathlib.Path(tmp) / "memoire"
        notes = preparer(neuf)
        sauves = remplacer(neuf)
    noter_secours(sauves)
    print(f"{len(notes)} notes recopiées dans {MEMOIRE}")


if __name__ == "__main__":
    main()

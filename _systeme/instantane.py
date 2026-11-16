#!/usr/bin/env python3
"""Prend un point de sauvegarde du carnet et de la mémoire de Claude, avec git, en local.

Si une nuit se passe mal ou qu'un fichier part au mauvais endroit, on revient en arrière
avec git. Rien n'est envoyé sur internet : les commits restent sur votre ordinateur.

Usage :
    python3 instantane.py [étiquette]

Le programme ne plante jamais la nuit : une erreur de git est affichée, pas levée.
Il ne fait rien quand rien n'a changé.

Réglage : MEMOIRE_CLAUDE, comme dans miroir.py.
"""
import datetime
import os
import pathlib
import subprocess
import sys

CARNET = pathlib.Path(__file__).resolve().parent.parent
MEMOIRE_CLAUDE = pathlib.Path(os.environ.get(
    "MEMOIRE_CLAUDE",
    pathlib.Path.home() / ".claude/projects" / str(pathlib.Path.home()).replace("/", "-") / "memory"))
IDENTITE = {"GIT_AUTHOR_NAME": "relecture-de-nuit", "GIT_AUTHOR_EMAIL": "nuit@local",
            "GIT_COMMITTER_NAME": "relecture-de-nuit", "GIT_COMMITTER_EMAIL": "nuit@local"}


def sauver(dossier: pathlib.Path, message: str):
    if not dossier.is_dir():
        print(f"Point de sauvegarde : {dossier} n'existe pas, sauté")
        return
    env = {**os.environ, **IDENTITE}
    try:
        if not (dossier / ".git").exists():
            subprocess.run(["git", "init", "-q"], cwd=dossier, env=env, check=True)
        subprocess.run(["git", "add", "-A"], cwd=dossier, env=env, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=dossier, env=env).returncode:
            subprocess.run(["git", "commit", "-q", "-m", message], cwd=dossier, env=env, check=True)
            print(f"Point de sauvegarde ({dossier.name}) : {message}")
        else:
            print(f"Point de sauvegarde ({dossier.name}) : rien de changé")
    except Exception as e:  # filet de sécurité, jamais une barrière
        print(f"Point de sauvegarde sauté pour {dossier.name} : {e}")


def main():
    etiquette = sys.argv[1] if len(sys.argv) > 1 else ""
    jour = datetime.date.today().isoformat()
    suite = f", {etiquette}" if etiquette else ""
    sauver(MEMOIRE_CLAUDE, f"mémoire au {jour}{suite}")
    sauver(CARNET, f"carnet au {jour}{suite}")


if __name__ == "__main__":
    main()

# La relecture de nuit : Claude relit vos notes pendant que vous dormez

Tôt le matin, Claude repasse sur mon carnet de notes Obsidian, relie ce qui doit l'être et me laisse deux résumés : les pistes qui tiennent ou qui sont mortes, et ce que j'ai construit sans jamais le mettre en service. Ce dépôt est tiré du vrai système qui tourne chez moi, trois matins par semaine : la consigne et ses trois petits programmes, simplifiés et nettoyés de mes chemins et de mes outils à moi.

L'histoire, avec tout ce qui a planté en route : [J'ai confié la relecture de mes notes à une IA](https://alpinealgo.ch/articles/carnet-qui-se-relit.html).

## Ce qu'il y a dedans

| Fichier | Ce qu'il fait |
|---|---|
| `consigne-de-nuit.md` | La consigne à coller dans une tâche planifiée de Claude. |
| `_systeme/miroir.py` | Recopie la mémoire de Claude Code dans le carnet et refait son sommaire. Un fichier qui disparaîtrait est mis de côté, jamais effacé. |
| `_systeme/fiches_sessions.py` | Range une fiche par conversation passée avec Claude : la demande, les fichiers écrits, les commits. Les clés et les mots de passe sont masqués. Il repère ce qui a été construit sans être livré. |
| `_systeme/instantane.py` | Prend un point de sauvegarde avec git, en local, pour revenir en arrière si une nuit tourne mal. |

Il faut Python 3 et git, rien d'autre à installer.

## L'installer en quatre étapes

1. Copiez le dossier `_systeme/` dans votre carnet Obsidian.
2. Lancez les programmes une fois à la main pour voir ce qu'ils font :
   ```bash
   python3 ~/MonCarnet/_systeme/miroir.py
   python3 ~/MonCarnet/_systeme/fiches_sessions.py
   ```
   Si votre mémoire Claude n'est pas à l'endroit habituel, donnez son dossier avec la variable `MEMOIRE_CLAUDE`.
3. Créez une tâche planifiée dans l'app Claude, une fois par jour ou moins, avec le texte de `consigne-de-nuit.md`. Chez moi, un programme planifié du Mac, hors de l'app, se faisait refuser.
4. Autorisez d'avance les quatre commandes de la consigne. Une demande d'autorisation sans personne pour répondre bloque toute la nuit : chez moi, la tâche est restée « en cours » plus de 25 heures.

## Les deux règles qui m'ont coûté le plus cher

- Ce que la machine réécrit et ce que vous écrivez vivent dans des dossiers séparés. J'ai perdu une retouche faite à la main dans un dossier que la nuit réécrit.
- Le rapport de la nuit dit toujours ce qu'il a fait, même quand il n'a rien fait. Sinon, un silence ressemble à s'y méprendre à une panne.

## Licence

MIT : vous pouvez la reprendre, la modifier et la partager, en gardant la mention de licence.

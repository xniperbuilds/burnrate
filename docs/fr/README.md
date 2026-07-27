[English](../../README.md) | [简体中文](../zh-CN/README.md) | [繁體中文](../zh-TW/README.md) | [日本語](../ja/README.md) | [한국어](../ko/README.md) | [Español](../es/README.md) | [Português (BR)](../pt-BR/README.md) | [Deutsch](../de/README.md) | **Français** | [Русский](../ru/README.md) | [Türkçe](../tr/README.md) | [Tiếng Việt](../vi/README.md) | [हिन्दी](../hi/README.md)

# burnrate

**Découvrez ce qui consomme réellement les tokens de votre agent de code — mesuré à partir de vos propres sessions, pas d'un pourcentage marketing.**

Chaque skill d'économie de tokens promet un chiffre. `économise 65%`. `facture ~31% plus basse`. Ces chiffres viennent des sessions de quelqu'un d'autre, avec ses fichiers et ses habitudes. Ce ne sont pas les vôtres, et vous ne pouvez pas les vérifier.

Alors vérifiez les vôtres. Une commande, sans installation, sans clé API, sans réseau :

```bash
python burnrate.py --all
```

---

## Ce que personne ne mesure

Voici un corpus réel de 348 sessions — 36 000 tours de modèle, 8,8 milliards de tokens :

| | tokens bruts | part | part pondérée par le coût |
|---|---:|---:|---:|
| **contexte renvoyé à chaque tour** (cache read) | 8 310 254 792 | **94,2%** | 49,6% |
| contexte écrit (cache write) | 446 493 285 | 5,1% | 33,3% |
| **sortie — ce que l'agent écrit** | 54 477 459 | **0,6%** | 16,3% |
| entrée (non mise en cache) | 13 730 167 | 0,2% | 0,8% |

**Contexte : 99,2% des tokens bruts, 82,9% pondéré par le coût. Sortie : 0,6% brut, 16,3% pondéré.**

La session médiane a renvoyé **109 fois plus de contexte qu'elle n'en a écrit**. Sur 348 sessions, seules **5** ont écrit plus qu'elles n'ont relu.

Toute skill qui économise des tokens en raccourcissant les réponses, en supprimant les articles ou en parlant comme un homme des cavernes optimise ces **0,6%**. Même en pondérant le prix plus élevé des tokens de sortie, elle vise le plus petit de quatre postes — tout en ajoutant ses propres instructions au contexte renvoyé à chaque tour, pour toujours.

C'est pour cela que les économies ne se manifestent jamais vraiment.

*(Les deux parts sont affichées parce qu'elles racontent des histoires différentes. La brute, c'est ce qui remplit votre fenêtre de contexte ; la pondérée utilise les ratios de facturation publiés — cache write 1,25×, cache read 0,10×, sortie 5× l'entrée. Ne citer que celle qui vous arrange, c'est le problème, pas la solution.)*

## Lancez-le sur vos propres chiffres

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+, bibliothèque standard uniquement — pas de `pip install`, pas de Node, pas d'installeur shell, pas de `curl | bash`. Fonctionne à l'identique sous Windows, macOS et Linux.

Il lit les transcriptions déjà présentes sur votre disque (`~/.claude/projects/**/*.jsonl`) et affiche :

- votre répartition de tokens brute et pondérée
- quels outils injectent le plus de volume dans votre contexte, et leur taille de résultat moyenne
- quels fichiers vous relisez encore et encore
- quels fichiers sont assez gros pour dominer une session à eux seuls
- les charges utiles d'images et de binaires, comptées à part et honnêtement

```
  [HIGH] 94 fichier(s) lus 5 fois ou plus
      Relire les mêmes fichiers inchangés a coûté environ 2,4 millions de
      tokens au-delà de la première lecture (approx). Le pire :
      project-notes.md (107 fois).
      -> Ils sont relus parce que leur contenu n'a pas survécu dans le contexte.

  [HIGH] Read produit 50% de tout ce qui revient dans le contexte
      3 100 appels ont renvoyé ~4,5 millions de tokens ; moyenne de 1 400
      tokens par appel, plus gros résultat ~16 800 tokens.
      -> Lisez avec offset/limit plutôt que des fichiers entiers.
```

## Ce qui est chargé avant que vous ne tapiez quoi que ce soit

```bash
python burnrate.py --startup
```

Le contexte de démarrage est payé à **chaque tour de chaque session** : c'est donc l'information au plus fort effet de levier. Sortie réelle :

```
-- MESURÉ (premier tour facturé de chaque session) --------------
  contexte de démarrage (médiane)  60 057 tokens   sur 310 sessions
  Il est renvoyé en cache_read à TOUS les tours suivants.

-- ATTRIBUÉ (analyse de votre configuration, approx) ------------
  descriptions de skills                8 185  57 skill(s)
  CLAUDE.md (utilisateur)                3 674
  index mémoire (MEMORY.md)              2 758  max 200 lignes / 25 Ko
  descriptions de sous-agents            1 258  18 agent(s)
  total attribué                        15 875

  résidu non attribué                   44 182  prompt système + schémas d'outils
  votre part                              26,4%  c'est ce que vous pouvez couper
```

Trois choses le distinguent d'un estimateur de fichiers de configuration :

- Le chiffre **mesuré** est exact — il provient du champ `usage`, pas d'un comptage de mots.
- Le **résidu** est indiqué plutôt que caché. Deux tiers de ce coût de démarrage sont le prompt système et les schémas d'outils, que vos modifications de fichiers ne changeront jamais. Vous le dire vous évite d'optimiser un nombre que vous ne pouvez pas bouger.
- Pour les skills et les agents, **seul le frontmatter est compté**. Leurs corps se chargent à la demande ; compter des fichiers de skill entiers — ce que font souvent les outils qui scannent les répertoires de configuration — surestime le coût de démarrage de plusieurs fois.

La surprise habituelle : **les skills installées mais inutilisées pèsent plus que `CLAUDE.md`.** La description de chaque skill se charge à chaque tour, que vous l'invoquiez ou non — c'est pourquoi `--startup` compte aussi les véritables appels à l'outil `Skill` sur tout votre historique et sépare *installées* et *utilisées* :

```
  Sur TOUT votre historique (416 transcriptions, pas la fenêtre --days) :
    57 installées  |  12 avec une invocation enregistrée  |  45 sans

  ~6 143 tokens par tour partent dans des skills sans invocation enregistrée.
  Sur une session de 100 tours, cela fait ~614 K.
```

Ce n'est pas une estimation du gaspillage : c'est du gaspillage nommé, classé du plus lourd au plus léger. Un outil qui se contente de scanner votre répertoire de configuration ne peut pas le savoir.

## Prouvez vos propres économies

```bash
python burnrate.py --snapshot before
#  ... changez quelque chose ...
python burnrate.py --compare before
```

`--compare` rapporte des **moyennes par tour**, pour qu'une semaine plus chargée ne se déguise pas en régression :

```
                                            avant   maintenant     écart
  cache write (nouveau contexte)              8.6K       5.9K    -31,7%
  cache read (renvoyé à chaque tour)         213.3K     219.5K      2,9%
  sortie (ce que l'agent a écrit)              1.4K       1.4K      1,3%

  pondéré par le coût, par tour               39.1K      36.4K     -6,9%

  Voici votre changement mesuré. Ce n'est pas une affirmation sur celui d'autrui.
```

## Installer en tant que skill

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Une fois installée, elle fait trois choses : mesurer avant de recommander, appliquer une discipline de contexte visant les 83–99% coûteux plutôt que les 0,6% bon marché, puis mesurer à nouveau pour que l'amélioration soit un fait. Le manuel complet des coupes — classé par impact, avec le coût de chacune — se trouve dans [`references/cuts.md`](../../plugins/burnrate/skills/burnrate/references/cuts.md).

## Ce qu'elle ne fera pas

- **Elle ne fera pas parler votre agent bizarrement.** Le style télégraphique rogne une petite part de la facture et rend les résultats plus difficiles à relire.
- **Elle ne vous donnera pas une moyenne.** Uniquement vos chiffres mesurés.
- **Elle ne cachera pas son propre coût.** Lorsqu'elle est invoquée, ce fichier entre dans le contexte. Sur de courtes sessions, ce surcoût peut dépasser ce qu'elle économise — et `--compare` vous le montrera honnêtement.
- **Elle n'échangera pas la justesse contre des tokens.** La concision s'applique à ce qui est transmis, jamais au raisonnement, aux tests, ni au texte littéral du code et des erreurs.

## Limites connues

- Les totaux de tokens proviennent du champ `usage` et sont exacts. Le volume des résultats d'outils est converti à ~4 caractères/token et signalé comme approximatif partout où il apparaît.
- Les images et les PDF sont facturés selon leurs dimensions, pas selon les caractères. Ils sont comptés à part et jamais convertis en nombre de tokens.
- La pondération par le coût utilise les ratios publiés entre classes de tokens, pas les prix par modèle — la colonne pondérée est une part, pas un montant.
- Les formules par abonnement peuvent pondérer l'usage différemment de la tarification API. C'est pourquoi les deux parts sont rapportées ; aucune n'est présentée comme une facture.
- Il ne voit que les transcriptions locales. Le travail fait sur une autre machine ou dans le navigateur n'est pas compté.
- Le corpus ci-dessus, ce sont les 348 sessions d'un utilisateur intensif. C'est une preuve, pas une loi universelle — et c'est précisément le propos. Lancez-le sur les vôtres.

## Licence

MIT

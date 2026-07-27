[English](../../README.md) | [简体中文](../zh-CN/README.md) | [繁體中文](../zh-TW/README.md) | [日本語](../ja/README.md) | [한국어](../ko/README.md) | [Español](../es/README.md) | [Português (BR)](../pt-BR/README.md) | **Deutsch** | [Français](../fr/README.md) | [Русский](../ru/README.md) | [Türkçe](../tr/README.md) | [Tiếng Việt](../vi/README.md) | [हिन्दी](../hi/README.md)

# burnrate

**Finde heraus, was die Tokens deines Coding-Agents wirklich verbrennt — gemessen an deinen eigenen Sessions, nicht an einem Marketing-Prozentsatz.**

Jede Token-Spar-Skill verspricht eine Zahl. `spart 65%`. `~31% niedrigere Rechnung`. Diese Zahlen stammen aus den Sessions von jemand anderem, mit dessen Dateien und dessen Gewohnheiten. Es sind nicht deine, und du kannst sie nicht überprüfen.

Also überprüfe deine. Ein Befehl, keine Installation, kein API-Key, kein Netzwerk:

```bash
python burnrate.py --all
```

---

## Was niemand misst

Hier ein echter Korpus aus 348 Sessions — 36.000 Modell-Turns, 8,8 Milliarden Tokens:

| | Roh-Tokens | Anteil | kostengewichteter Anteil |
|---|---:|---:|---:|
| **Kontext, der in jedem Turn erneut gesendet wird** (Cache Read) | 8.310.254.792 | **94,2%** | 49,6% |
| geschriebener Kontext (Cache Write) | 446.493.285 | 5,1% | 33,3% |
| **Ausgabe — was der Agent schreibt** | 54.477.459 | **0,6%** | 16,3% |
| Eingabe (ungecacht) | 13.730.167 | 0,2% | 0,8% |

**Kontext: 99,2% der Roh-Tokens, 82,9% kostengewichtet. Ausgabe: 0,6% roh, 16,3% gewichtet.**

Die mediane Session sendete **109-mal mehr Kontext erneut, als sie schrieb**. Von 348 Sessions schrieben nur **5** mehr, als sie erneut lasen.

Jede Skill, die Tokens spart, indem sie Antworten kürzt, Artikel weglässt oder wie ein Höhlenmensch spricht, optimiert diese **0,6%**. Selbst gewichtet nach dem höheren Preis von Ausgabe-Tokens zielt sie auf den kleinsten von vier Posten — und fügt dabei ihre eigenen Anweisungen dem Kontext hinzu, der in jedem Turn erneut gesendet wird. Für immer.

Deshalb taucht die Ersparnis nie wirklich auf.

*(Beide Anteile werden gezeigt, weil sie unterschiedliche Geschichten erzählen. Der rohe Anteil ist das, was dein Kontextfenster füllt; der gewichtete nutzt die veröffentlichten Abrechnungsverhältnisse — Cache Write 1,25×, Cache Read 0,10×, Ausgabe 5× Eingabe. Nur den schmeichelhaften zu zitieren ist das Problem, nicht die Lösung.)*

## Führe es mit deinen eigenen Zahlen aus

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+, nur Standardbibliothek — kein `pip install`, kein Node, kein Shell-Installer, kein `curl | bash`. Funktioniert unter Windows, macOS und Linux gleich.

Es liest die Transkripte, die bereits auf deiner Platte liegen (`~/.claude/projects/**/*.jsonl`), und gibt aus:

- deine rohe und gewichtete Token-Aufteilung
- welche Tools das meiste Volumen in deinen Kontext schieben, und ihre durchschnittliche Ergebnisgröße
- welche Dateien du immer wieder liest
- welche Dateien groß genug sind, um eine Session im Alleingang zu dominieren
- Bild- und Binär-Payloads, separat und ehrlich gezählt

```
  [HIGH] 94 Datei(en) 5+ mal gelesen
      Das erneute Lesen derselben unveränderten Dateien kostete rund
      2,4 Mio. Tokens über die erste Lesung hinaus (ca.). Am schlimmsten:
      project-notes.md (107×).
      -> Sie werden erneut gelesen, weil ihr Inhalt im Kontext nicht überlebt hat.

  [HIGH] Read erzeugt 50% von allem, was in den Kontext zurückfließt
      3.100 Aufrufe lieferten ~4,5 Mio. Tokens; im Schnitt 1.400 Tokens
      pro Aufruf, größtes Einzelergebnis ~16.800 Tokens.
      -> Mit offset/limit lesen statt ganzer Dateien.
```

## Was geladen wird, bevor du irgendetwas tippst

```bash
python burnrate.py --startup
```

Der Startkontext wird in **jedem Turn jeder Session** bezahlt — also ist er das Wirkungsvollste, was du wissen kannst. Echte Ausgabe:

```
-- GEMESSEN (erster abgerechneter Turn je Session) --------------
  Startkontext (Median)           60.057 Tokens   über 310 Sessions
  Er wird in JEDEM späteren Turn als Cache Read erneut gesendet.

-- ZUGEORDNET (aus deiner Konfiguration gescannt, ca.) ----------
  Skill-Beschreibungen                  12.998  105 Skill(s)
  CLAUDE.md (Benutzer)                   3.674
  Memory-Index (MEMORY.md)               2.718  max. 200 Zeilen / 25 KB
  Agent-Beschreibungen                   1.258  18 Agent(en)
  zugeordnet gesamt                     20.648

  nicht zugeordneter Rest               39.409  System-Prompt + Tool-Schemas
  dein Anteil                             34,4%  ist das, was du kürzen kannst
```

Drei Dinge unterscheiden das von einem Konfigurationsdatei-Schätzer:

- Die **gemessene** Zahl ist exakt — sie stammt aus dem `usage`-Feld, nicht aus Wortzählung.
- Der **Rest** wird ausgewiesen statt versteckt. Zwei Drittel dieser Startkosten sind System-Prompt und Tool-Schemas, die sich durch Bearbeiten deiner Dateien nicht ändern. Das zu sagen bewahrt dich davor, eine Zahl zu optimieren, die du nicht bewegen kannst.
- Bei Skills und Agents wird **nur das Frontmatter** gezählt. Ihre Rümpfe laden bei Bedarf; ganze Skill-Dateien zu zählen — wie es Tools tun, die Konfigurationsverzeichnisse scannen — überschätzt die Startkosten um ein Vielfaches.

Die übliche Überraschung: **installierte, aber ungenutzte Skills wiegen mehr als `CLAUDE.md`.** Die Beschreibung jeder Skill lädt in jedem Turn, ob du sie aufrufst oder nicht — deshalb zählt `--startup` auch die echten `Skill`-Tool-Aufrufe in deiner gesamten Historie und trennt *installiert* von *genutzt*:

```
  Über deine GESAMTE Historie (416 Transkripte, nicht das --days-Fenster):
    105 installiert  |  12 mit erfasstem Aufruf  |  93 ohne

  ~10.956 Tokens pro Turn gehen an Skills ohne erfassten Aufruf.
  In einer Session mit 100 Turns sind das ~1,1 Mio.
```

Das ist keine Schätzung von Verschwendung — es ist Verschwendung mit Namen, nach Gewicht sortiert. Ein Werkzeug, das nur dein Konfigurationsverzeichnis scannt, kann das nicht wissen.

## Weise deine eigene Ersparnis nach

```bash
python burnrate.py --snapshot before
#  ... etwas ändern ...
python burnrate.py --compare before
```

`--compare` meldet **Durchschnitte pro Turn**, damit eine geschäftigere Woche sich nicht als Rückschritt tarnt:

```
                                            vorher      jetzt   Änderung
  Cache Write (neuer Kontext)                 8.6K       5.9K    -31,7%
  Cache Read (pro Turn erneut gesendet)      213.3K     219.5K      2,9%
  Ausgabe (was der Agent schrieb)              1.4K       1.4K      1,3%

  kostengewichtet pro Turn                    39.1K      36.4K     -6,9%

  Das ist deine gemessene Veränderung. Keine Aussage über die anderer.
```

## Als Skill installieren

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Installiert tut sie drei Dinge: erst messen, dann empfehlen; Kontextdisziplin anwenden, die auf die teuren 83–99% zielt statt auf die billigen 0,6%; und erneut messen, damit die Verbesserung eine Tatsache ist. Das vollständige Kürzungs-Playbook — nach Wirkung sortiert, mit den Kosten jeder Kürzung — steht in [`references/cuts.md`](../../plugins/burnrate/skills/burnrate/references/cuts.md).

## Was sie nicht tut

- **Sie lässt deinen Agenten nicht seltsam sprechen.** Telegrammstil kürzt einen kleinen Teil der Rechnung und macht Ergebnisse schwerer prüfbar.
- **Sie nennt dir keinen Durchschnitt.** Nur deine gemessenen Zahlen.
- **Sie verbirgt ihre eigenen Kosten nicht.** Beim Aufruf landet diese Datei im Kontext. In kurzen Sessions kann dieser Overhead das Ersparte übersteigen — und `--compare` zeigt dir das ehrlich.
- **Sie tauscht Korrektheit nicht gegen Tokens.** Kürze gilt für das Übertragene, niemals für Schlussfolgerungen, Tests oder den Wortlaut von Code und Fehlern.

## Bekannte Grenzen

- Token-Summen stammen aus dem `usage`-Feld und sind exakt. Tool-Ergebnisvolumen wird mit ~4 Zeichen/Token umgerechnet und überall als Näherung gekennzeichnet.
- Bilder und PDFs werden nach Abmessungen abgerechnet, nicht nach Zeichen. Sie werden separat gezählt und nie in eine Token-Zahl umgerechnet.
- Die Kostengewichtung nutzt veröffentlichte Verhältnisse zwischen Token-Klassen, nicht Preise je Modell — die gewichtete Spalte ist ein Anteil, kein Geldbetrag.
- Abo-Tarife können Nutzung anders gewichten als die API-Preise. Deshalb werden beide Anteile ausgewiesen; keiner wird als Rechnung dargestellt.
- Es sieht nur lokale Transkripte. Arbeit auf einer anderen Maschine oder im Browser wird nicht gezählt.
- Der obige Korpus sind 348 Sessions eines Vielnutzers. Das ist Evidenz, kein Naturgesetz — und genau das ist der Punkt. Führe es mit deinen aus.

## Lizenz

MIT

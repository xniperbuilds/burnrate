[English](../../README.md) | [简体中文](../zh-CN/README.md) | [繁體中文](../zh-TW/README.md) | [日本語](../ja/README.md) | [한국어](../ko/README.md) | **Español** | [Português (BR)](../pt-BR/README.md) | [Deutsch](../de/README.md) | [Français](../fr/README.md) | [Русский](../ru/README.md) | [Türkçe](../tr/README.md) | [Tiếng Việt](../vi/README.md) | [हिन्दी](../hi/README.md)

# burnrate

**Descubre qué está quemando de verdad los tokens de tu agente de código: medido a partir de tus propias sesiones, no un porcentaje de marketing.**

Toda skill que promete ahorrar tokens te da una cifra. `ahorra un 65%`. `factura ~31% más baja`. Esas cifras salieron de las sesiones de otra persona, con sus archivos y sus hábitos. No son las tuyas, y no puedes comprobarlas.

Así que comprueba las tuyas. Un comando, sin instalación, sin API key, sin red:

```bash
python burnrate.py --all
```

---

## Lo que nadie mide

Este es un corpus real de 348 sesiones: 36.000 turnos de modelo, 8.800 millones de tokens.

| | tokens brutos | proporción | proporción ponderada por coste |
|---|---:|---:|---:|
| **contexto reenviado en cada turno** (cache read) | 8.310.254.792 | **94,2%** | 49,6% |
| contexto escrito (cache write) | 446.493.285 | 5,1% | 33,3% |
| **salida: lo que escribe el agente** | 54.477.459 | **0,6%** | 16,3% |
| entrada (sin caché) | 13.730.167 | 0,2% | 0,8% |

**Contexto: 99,2% de los tokens brutos, 82,9% ponderado por coste. Salida: 0,6% bruto, 16,3% ponderado.**

La sesión mediana reenvió **109 veces más contexto del que escribió**. De 348 sesiones, solo **5** escribieron más de lo que releyeron.

Toda skill que ahorra tokens acortando respuestas, quitando artículos o hablando como un cavernícola está optimizando ese **0,6%**. Incluso ponderando el precio más alto de los tokens de salida, va a por la más pequeña de cuatro partidas, mientras añade sus propias instrucciones al contexto que se reenvía en cada turno, para siempre.

Por eso el ahorro nunca acaba de aparecer.

*(Se muestran ambas proporciones porque cuentan historias distintas. La bruta es lo que llena tu ventana de contexto; la ponderada usa las proporciones de facturación publicadas: cache write 1,25×, cache read 0,10×, salida 5× la entrada. Citar solo la que te conviene es el problema, no la solución.)*

## Ejecútalo con tus propios números

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+, solo biblioteca estándar: sin `pip install`, sin Node, sin instalador de shell, sin `curl | bash`. Funciona igual en Windows, macOS y Linux.

Lee las transcripciones que ya tienes en disco (`~/.claude/projects/**/*.jsonl`) e imprime:

- tu reparto de tokens bruto y ponderado
- qué herramientas meten más volumen en tu contexto, y su tamaño medio de resultado
- qué archivos lees una y otra vez
- qué archivos son lo bastante grandes como para dominar una sesión por sí solos
- cargas de imágenes y binarios, contadas aparte y con honestidad

```
  [HIGH] 94 archivo(s) leídos 5+ veces
      Releer los mismos archivos sin cambios costó unos 2,4 millones de
      tokens más allá de la primera lectura (aprox). El peor:
      project-notes.md (107 veces).
      -> Se releen porque su contenido no sobrevivió en el contexto.

  [HIGH] Read produce el 50% de todo lo que vuelve al contexto
      3.100 llamadas devolvieron ~4,5 millones de tokens; media de 1.400
      tokens por llamada, resultado individual máximo ~16.800 tokens.
      -> Lee con offset/limit en vez de archivos enteros.
```

## Qué se carga antes de que escribas nada

```bash
python burnrate.py --startup
```

El contexto de arranque se paga en **cada turno de cada sesión**, así que es lo más rentable que puedes saber. Salida real:

```
-- MEDIDO (primer turno facturado de cada sesión) ---------------
  contexto de arranque (mediana)  60.057 tokens   en 310 sesiones
  Se reenvía como cache_read en TODOS los turnos posteriores.

-- ATRIBUIDO (escaneado de tu configuración, aprox) -------------
  descripciones de skills               8.185  57 skill(s)
  CLAUDE.md (usuario)                    3.674
  índice de memoria (MEMORY.md)          2.758  máx. 200 líneas / 25KB
  descripciones de subagentes            1.258  18 agente(s)
  total atribuido                       15.875

  residuo no atribuido                  44.182  prompt de sistema + esquemas
  tu parte                                26,4%  es lo que puedes recortar
```

Tres cosas lo diferencian de un estimador de archivos de configuración:

- La cifra **medida** es exacta: viene del campo `usage`, no de contar palabras.
- El **residuo** se informa en lugar de ocultarse. Dos tercios de ese coste de arranque son el prompt de sistema y los esquemas de herramientas, que no cambian por mucho que edites tus archivos. Decírtelo te ahorra optimizar un número que no puedes mover.
- Solo se cuenta el **frontmatter** de skills y agentes. Sus cuerpos se cargan bajo demanda, así que contar los archivos de skill enteros —como suelen hacer las herramientas que escanean directorios de configuración— sobrestima el arranque varias veces.

La sorpresa habitual: **las skills instaladas pero sin usar pesan más que `CLAUDE.md`.** La descripción de cada skill se carga en cada turno, la invoques o no — por eso `--startup` también cuenta las llamadas reales a la herramienta `Skill` en todo tu historial y separa *instaladas* de *usadas*:

```
  En TODO tu historial (416 transcripciones, no la ventana --days):
    57 instaladas  |  12 con invocación registrada  |  45 sin ella

  ~6.143 tokens por turno se van en skills sin invocación registrada.
  En una sesión de 100 turnos eso es ~614 K.
```

Eso no es una estimación del desperdicio: es desperdicio con nombre y apellido, ordenado de mayor a menor. Una herramienta que solo escanea tu directorio de configuración no puede saberlo.

## Demuestra tu propio ahorro

```bash
python burnrate.py --snapshot before
#  ... cambia algo ...
python burnrate.py --compare before
```

`--compare` informa de **medias por turno**, así que una semana con más trabajo no se disfraza de retroceso:

```
                                             antes      ahora     cambio
  cache write (contexto nuevo)                8.6K       5.9K    -31,7%
  cache read (reenviado cada turno)          213.3K     219.5K      2,9%
  output (lo que escribe el agente)            1.4K       1.4K      1,3%

  ponderado por coste, por turno              39.1K      36.4K     -6,9%

  Este es tu cambio medido. No es una afirmación sobre el de nadie más.
```

## Instalar como skill

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Instalada hace tres cosas: mide antes de recomendar, aplica una disciplina de contexto dirigida al 83–99% caro en vez del 0,6% barato, y vuelve a medir para que la mejora sea un hecho. El manual completo de recortes —ordenado por impacto, con el coste de cada uno— está en [`references/cuts.md`](../../plugins/burnrate/skills/burnrate/references/cuts.md).

## Lo que no hará

- **No hará que tu agente hable raro.** La salida telegráfica recorta una parte pequeña de la factura y hace más difícil revisar los resultados.
- **No te dará una media.** Solo tus números medidos.
- **No ocultará su propio coste.** Al invocarse, este archivo entra en el contexto. En sesiones cortas esa sobrecarga puede superar lo que ahorra, y `--compare` te lo mostrará con honestidad.
- **No cambiará corrección por tokens.** La concisión se aplica a lo que se transmite, nunca al razonamiento, las pruebas ni al código y los errores literales.

## Limitaciones conocidas

- Los totales de tokens vienen del campo `usage` y son exactos. El volumen de resultados de herramientas se convierte a ~4 caracteres/token y se marca como aproximado allí donde aparece.
- Las imágenes y los PDF se facturan por dimensiones, no por caracteres. Se cuentan aparte y nunca se convierten en una cifra de tokens.
- La ponderación por coste usa proporciones publicadas entre clases de tokens, no precios por modelo: la columna ponderada es una proporción, no un importe.
- Los planes de suscripción pueden ponderar el uso de forma distinta a la API. Por eso se informan ambas proporciones; ninguna se presenta como una factura.
- Solo ve transcripciones locales. El trabajo hecho en otra máquina o en el navegador no cuenta.
- El corpus anterior son las 348 sesiones de un usuario intensivo. Es evidencia, no una ley universal, y ese es precisamente el punto. Ejecútalo con las tuyas.

## Licencia

MIT

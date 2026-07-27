[English](../../README.md) | [简体中文](../zh-CN/README.md) | [繁體中文](../zh-TW/README.md) | [日本語](../ja/README.md) | [한국어](../ko/README.md) | [Español](../es/README.md) | **Português (BR)** | [Deutsch](../de/README.md) | [Français](../fr/README.md) | [Русский](../ru/README.md) | [Türkçe](../tr/README.md) | [Tiếng Việt](../vi/README.md) | [हिन्दी](../hi/README.md)

# burnrate

**Descubra o que realmente está queimando os tokens do seu agente de código — medido a partir das suas próprias sessões, não de uma porcentagem de marketing.**

Toda skill que promete economizar tokens apresenta um número. `economiza 65%`. `conta ~31% menor`. Esses números vieram das sessões de outra pessoa, com os arquivos e os hábitos dela. Não são os seus, e você não tem como conferir.

Então confira os seus. Um comando, sem instalação, sem chave de API, sem rede:

```bash
python burnrate.py --all
```

---

## O que ninguém mede

Este é um corpus real de 348 sessões: 36.000 turnos de modelo, 8,8 bilhões de tokens.

| | tokens brutos | fatia | fatia ponderada por custo |
|---|---:|---:|---:|
| **contexto reenviado a cada turno** (cache read) | 8.310.254.792 | **94,2%** | 49,6% |
| contexto gravado (cache write) | 446.493.285 | 5,1% | 33,3% |
| **saída — o que o agente escreve** | 54.477.459 | **0,6%** | 16,3% |
| entrada (sem cache) | 13.730.167 | 0,2% | 0,8% |

**Contexto: 99,2% dos tokens brutos, 82,9% ponderado por custo. Saída: 0,6% bruto, 16,3% ponderado.**

A sessão mediana reenviou **109 vezes mais contexto do que escreveu**. De 348 sessões, apenas **5** escreveram mais do que releram.

Toda skill que economiza tokens encurtando respostas, cortando artigos ou falando como homem das cavernas está otimizando esses **0,6%**. Mesmo ponderando o preço mais alto dos tokens de saída, ela mira o menor de quatro itens — enquanto adiciona as próprias instruções ao contexto que é reenviado a cada turno, para sempre.

É por isso que a economia nunca aparece de verdade.

*(As duas fatias são mostradas porque contam histórias diferentes. A bruta é o que enche sua janela de contexto; a ponderada usa as proporções de cobrança publicadas — cache write 1,25×, cache read 0,10×, saída 5× a entrada. Citar apenas a que favorece você é o problema, não a solução.)*

## Rode nos seus próprios números

```bash
git clone https://github.com/xniperbuilds/burnrate
cd burnrate/plugins/burnrate/skills/burnrate/scripts
python burnrate.py --days 30
```

Python 3.8+, apenas biblioteca padrão — sem `pip install`, sem Node, sem instalador de shell, sem `curl | bash`. Funciona igual no Windows, macOS e Linux.

Ele lê as transcrições que já estão no seu disco (`~/.claude/projects/**/*.jsonl`) e imprime:

- sua divisão de tokens bruta e ponderada
- quais ferramentas colocam mais volume no seu contexto, e o tamanho médio do resultado delas
- quais arquivos você lê várias e várias vezes
- quais arquivos são grandes o bastante para dominar uma sessão sozinhos
- cargas de imagens e binários, contadas à parte e com honestidade

```
  [HIGH] 94 arquivo(s) lidos 5+ vezes
      Reler os mesmos arquivos inalterados custou cerca de 2,4 milhões de
      tokens além da primeira leitura (aprox). O pior:
      project-notes.md (107 vezes).
      -> São relidos porque o conteúdo não sobreviveu no contexto.

  [HIGH] Read produz 50% de tudo que volta para o contexto
      3.100 chamadas retornaram ~4,5 milhões de tokens; média de 1.400
      tokens por chamada, maior resultado único ~16.800 tokens.
      -> Leia com offset/limit em vez de arquivos inteiros.
```

## O que carrega antes de você digitar qualquer coisa

```bash
python burnrate.py --startup
```

O contexto de inicialização é pago em **cada turno de cada sessão**, então é a informação de maior alavancagem. Saída real:

```
-- MEDIDO (primeiro turno faturado de cada sessão) --------------
  contexto inicial (mediana)      60.057 tokens   em 310 sessões
  É reenviado como cache_read em TODOS os turnos seguintes.

-- ATRIBUÍDO (varredura da sua config, aprox) -------------------
  descrições de skills                  12.998  105 skill(s)
  CLAUDE.md (usuário)                    3.674
  índice de memória (MEMORY.md)          2.718  limite 200 linhas / 25KB
  descrições de subagentes               1.258  18 agente(s)
  total atribuído                       20.648

  resíduo não atribuído                 39.409  prompt de sistema + schemas
  a sua parte                             34,4%  é o que dá para cortar
```

Três coisas o diferenciam de um estimador de arquivos de configuração:

- O número **medido** é exato — vem do campo `usage`, não de contagem de palavras.
- O **resíduo** é informado em vez de escondido. Dois terços desse custo inicial são o prompt de sistema e os schemas das ferramentas, que não mudam por mais que você edite seus arquivos. Dizer isso evita que você otimize um número que não consegue mover.
- Apenas o **frontmatter** de skills e agentes é contado. Os corpos carregam sob demanda, então contar arquivos de skill inteiros — como costumam fazer as ferramentas que varrem diretórios de configuração — superestima o custo inicial em várias vezes.

A surpresa de sempre: **skills instaladas e não usadas pesam mais que o `CLAUDE.md`.** A descrição de cada skill carrega a cada turno, você a invoque ou não — por isso o `--startup` também conta as chamadas reais à ferramenta `Skill` em todo o seu histórico e separa *instaladas* de *usadas*:

```
  Em TODO o seu histórico (416 transcrições, não a janela --days):
    105 instaladas  |  12 com invocação registrada  |  93 sem

  ~10.956 tokens por turno vão para skills sem invocação registrada.
  Numa sessão de 100 turnos isso dá ~1,1 mi.
```

Isso não é uma estimativa de desperdício — é desperdício com nome, listado do mais pesado para o mais leve. Uma ferramenta que só varre o diretório de configuração não tem como saber disso.

## Prove a sua própria economia

```bash
python burnrate.py --snapshot before
#  ... mude alguma coisa ...
python burnrate.py --compare before
```

O `--compare` informa **médias por turno**, então uma semana mais movimentada não se disfarça de regressão:

```
                                             antes      agora    variação
  cache write (contexto novo)                 8.6K       5.9K    -31,7%
  cache read (reenviado a cada turno)        213.3K     219.5K      2,9%
  output (o que o agente escreveu)             1.4K       1.4K      1,3%

  ponderado por custo, por turno              39.1K      36.4K     -6,9%

  Esta é a sua mudança medida. Não é uma afirmação sobre a de mais ninguém.
```

## Instalar como skill

```
/plugin marketplace add xniperbuilds/burnrate
/plugin install burnrate@xniperbuilds
```

Instalada, ela faz três coisas: mede antes de recomendar, aplica uma disciplina de contexto voltada aos 83–99% caros em vez dos 0,6% baratos, e mede de novo para que a melhoria seja um fato. O manual completo de cortes — ordenado por impacto, com o custo de cada um — está em [`references/cuts.md`](../../plugins/burnrate/skills/burnrate/references/cuts.md).

## O que ela não faz

- **Não faz seu agente falar de um jeito estranho.** Saída telegráfica corta uma fatia pequena da conta e torna os resultados mais difíceis de revisar.
- **Não te dá uma média.** Só os seus números medidos.
- **Não esconde o próprio custo.** Ao ser invocada, este arquivo entra no contexto. Em sessões curtas esse overhead pode superar o que ela economiza — e o `--compare` vai te mostrar isso honestamente.
- **Não troca correção por tokens.** A concisão vale para o que é transmitido, nunca para o raciocínio, os testes ou o texto literal de código e erros.

## Limitações conhecidas

- Os totais de tokens vêm do campo `usage` e são exatos. O volume de resultados de ferramentas é convertido a ~4 caracteres/token e marcado como aproximado onde quer que apareça.
- Imagens e PDFs são cobrados por dimensões, não por caracteres. São contados à parte e nunca convertidos em número de tokens.
- A ponderação por custo usa proporções publicadas entre classes de tokens, não preços por modelo — a coluna ponderada é uma fatia, não um valor em dinheiro.
- Planos de assinatura podem ponderar o uso de forma diferente da API. Por isso ambas as fatias são reportadas; nenhuma é apresentada como uma fatura.
- Só enxerga transcrições locais. Trabalho feito em outra máquina ou no navegador não é contado.
- O corpus acima são as 348 sessões de um usuário intenso. É evidência, não lei universal — e esse é justamente o ponto. Rode nos seus dados.

## Licença

MIT

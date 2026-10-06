# Simulador de Redes de Filas (T1)

Simulador orientado a eventos para redes de filas G/G/c/K, desenvolvido em Python.
O modelo (filas, roteamento, semente, quantidade de aleatórios e primeira chegada)
é carregado de um arquivo `.yml`.

## Arquivos

| Arquivo | Descrição |
|---|---|
| `simulador.py` | Código-fonte do simulador |
| `modelo.yml` | Descrição do modelo simulado (3 filas) |
| `requirements.txt` | Dependências do Python |
| `resultado.txt` | Saída da simulação (gerada automaticamente) |

## Requisitos

- Python 3.8 ou superior
- Biblioteca `pyyaml`

## Instalação

```bash
pip install -r requirements.txt
```

## Como executar

```bash
python simulador.py modelo.yml
```

O relatório é mostrado na tela e salvo em `resultado.txt`.
Para salvar com outro nome:

```bash
python simulador.py modelo.yml saida.txt
```

## Saída

Para cada fila, o relatório mostra:

- o tipo da fila (notação de Kendall: G/G/servidores/capacidade);
- o número de clientes perdidos;
- a tabela de estados com o **tempo acumulado** e a **probabilidade** de cada estado;
- a soma das probabilidades (deve ser 1).

Ao final, mostra o **tempo total da simulação** e a quantidade de números aleatórios utilizados.

## Formato do arquivo `.yml`

```yaml
semente: 123456789          # semente do gerador congruente linear
aleatorios: 100000          # a simulação encerra ao consumir este total
primeira_chegada:
  fila: Fila1               # fila que recebe a primeira chegada
  tempo: 2.0                # instante da primeira chegada

filas:
  Fila1:
    servidores: 1
    capacidade: null        # null = capacidade infinita
    chegada: [2, 4]         # intervalo entre chegadas externas [min, max]
    atendimento: [1, 2]     # tempo de atendimento [min, max]
    roteamento:             # para onde o cliente vai após o atendimento
      - {destino: Fila2, probabilidade: 0.8}
      - {destino: Fila3, probabilidade: 0.2}

  Fila2:
    servidores: 2
    capacidade: 5
    atendimento: [4, 6]
```

Regras do modelo:

- Chegadas externas só ocorrem em filas que possuem o campo `chegada`.
- Se a fila não tiver `roteamento`, o cliente sai do sistema após o atendimento.
- Se a soma das probabilidades de roteamento for menor que 1, o restante sai do sistema.
- Tempos de chegada e atendimento seguem distribuição uniforme no intervalo `[min, max]`.
- Se a fila destino estiver cheia, o cliente é perdido e contado nas perdas dessa fila.

## Detalhes da simulação

- Gerador de números pseudoaleatórios: congruente linear (LCG) com
  `a = 1664525`, `c = 1013904223`, `m = 2^32`.
- Estado inicial: todas as filas vazias.
- Término: quando o último número aleatório (o 100.000º) é consumido.
- O tempo acumulado de cada estado é calculado a cada evento, somando o intervalo
  desde o evento anterior ao estado atual de cada fila.
- A probabilidade de cada estado é `tempo acumulado do estado / tempo total da simulação`.

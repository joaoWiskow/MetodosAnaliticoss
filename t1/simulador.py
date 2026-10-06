#!/usr/bin/env python3
"""
Simulador de redes de filas G/G/c/K (orientado a eventos).

Uso:
    python simulador.py modelo.yml [saida.txt]

O relatorio e mostrado na tela e tambem salvo em arquivo
(por padrao, resultado.txt).

O arquivo .yml descreve as filas, o roteamento, a semente, a quantidade de
numeros aleatorios e o instante da primeira chegada.
A simulacao termina quando o ultimo numero aleatorio e consumido.
"""
import heapq
import itertools
import sys

import yaml


class GeradorAleatorio:
    """Gerador congruente linear (LCG) com limite de aleatorios."""

    def __init__(self, seed, limite):
        self.a = 1664525
        self.c = 1013904223
        self.m = 2 ** 32
        self.x = seed
        self.contador = 0
        self.limite = limite

    def next_random(self):
        if self.contador >= self.limite:
            raise StopIteration
        self.x = (self.a * self.x + self.c) % self.m
        self.contador += 1
        return self.x / self.m


class Fila:
    def __init__(self, nome, cfg):
        self.nome = nome
        self.servidores = int(cfg.get("servidores", 1))
        cap = cfg.get("capacidade")
        self.capacidade = float("inf") if cap is None else int(cap)
        self.chegada = cfg.get("chegada")          # [min, max] ou None
        self.atendimento = cfg["atendimento"]      # [min, max]
        self.roteamento = [(r["destino"], float(r["probabilidade"]))
                           for r in cfg.get("roteamento", [])]
        self.clientes = 0
        self.ocupados = 0
        self.perdas = 0
        self.tempo_estado = [0.0]  # cresce dinamicamente (suporta capacidade infinita)

    def acumula(self, delta):
        while len(self.tempo_estado) <= self.clientes:
            self.tempo_estado.append(0.0)
        self.tempo_estado[self.clientes] += delta

    def tipo_kendall(self):
        cap = "inf" if self.capacidade == float("inf") else int(self.capacidade)
        return f"G/G/{self.servidores}/{cap}"


def uniforme(intervalo, r):
    return intervalo[0] + (intervalo[1] - intervalo[0]) * r


def carregar_modelo(caminho):
    with open(caminho, "r", encoding="utf-8") as f:
        dados = yaml.safe_load(f)
    filas = {nome: Fila(nome, cfg) for nome, cfg in dados["filas"].items()}
    for fila in filas.values():
        for destino, _ in fila.roteamento:
            if destino not in filas:
                raise ValueError(f"Roteamento de {fila.nome} aponta para fila inexistente: {destino}")
        if sum(p for _, p in fila.roteamento) > 1.0 + 1e-9:
            raise ValueError(f"Probabilidades de roteamento de {fila.nome} somam mais que 1")
    return dados, filas


def simular(dados, filas):
    gerador = GeradorAleatorio(int(dados.get("semente", 123456789)),
                               int(dados.get("aleatorios", 100000)))
    primeira = dados["primeira_chegada"]
    contador = itertools.count()  # desempate estavel na heap
    eventos = []

    def agenda(tempo, tipo, fila):
        heapq.heappush(eventos, (tempo, next(contador), tipo, fila))

    def inicia_atendimento(fila, agora):
        fila.ocupados += 1
        d = uniforme(fila.atendimento, gerador.next_random())
        agenda(agora + d, "saida", fila)

    def entra_cliente(fila, agora):
        if fila.clientes < fila.capacidade:
            fila.clientes += 1
            if fila.ocupados < fila.servidores:
                inicia_atendimento(fila, agora)
        else:
            fila.perdas += 1

    agenda(float(primeira["tempo"]), "chegada", filas[primeira["fila"]])
    tempo = ultimo = 0.0

    try:
        while eventos:
            t, _, tipo, fila = heapq.heappop(eventos)
            delta = t - ultimo
            for f in filas.values():
                f.acumula(delta)
            tempo = ultimo = t

            if tipo == "chegada":
                entra_cliente(fila, tempo)
                if fila.chegada:  # chegadas externas so se a fila tem fluxo externo
                    intervalo = uniforme(fila.chegada, gerador.next_random())
                    agenda(tempo + intervalo, "chegada", fila)

            else:  # saida
                fila.clientes -= 1
                fila.ocupados -= 1
                if fila.clientes > fila.ocupados:
                    inicia_atendimento(fila, tempo)

                if fila.roteamento:
                    if len(fila.roteamento) == 1 and fila.roteamento[0][1] >= 1.0:
                        destino = fila.roteamento[0][0]
                    else:
                        r = gerador.next_random()
                        acumulada, destino = 0.0, None
                        for nome, p in fila.roteamento:
                            acumulada += p
                            if r <= acumulada:
                                destino = nome
                                break
                    if destino is not None:  # senao o cliente sai do sistema
                        entra_cliente(filas[destino], tempo)
    except StopIteration:
        pass

    return tempo, gerador.contador


def gerar_relatorio(filas, tempo_global, usados):
    linhas = [f"Tempo global da simulacao: {tempo_global:.4f}",
              f"Numeros aleatorios utilizados: {usados}", ""]
    for i, fila in enumerate(filas.values(), start=1):
        linhas.append(f"Fila {i} ({fila.nome}) - {fila.tipo_kendall()}")
        linhas.append(f"Clientes perdidos: {fila.perdas}")
        linhas.append("Estado | Tempo acumulado | Probabilidade")
        total = 0.0
        for estado, t in enumerate(fila.tempo_estado):
            p = t / tempo_global if tempo_global > 0 else 0.0
            total += p
            linhas.append(f"{estado:6d} | {t:15.4f} | {p:12.6f}")
        linhas.append(f"Soma das probabilidades: {total:.6f}")
        linhas.append("")
    linhas.append(f"Tempo total de simulacao: {tempo_global:.4f}")
    return "\n".join(linhas)


def main():
    if len(sys.argv) not in (2, 3):
        print("Uso: python simulador.py modelo.yml [saida.txt]")
        sys.exit(1)
    saida = sys.argv[2] if len(sys.argv) == 3 else "resultado.txt"
    dados, filas = carregar_modelo(sys.argv[1])
    tempo_global, usados = simular(dados, filas)
    relatorio = gerar_relatorio(filas, tempo_global, usados)
    print(relatorio)
    with open(saida, "w", encoding="utf-8") as f:
        f.write(relatorio + "\n")
    print(f"Resultado salvo em {saida}")


if __name__ == "__main__":
    main()
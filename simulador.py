"""
Simulador de fila por eventos discretos (G/G/c/K).
Gerador pseudoaleatorio: Metodo Congruente Linear (MCL).
Criterio de parada: consumo de N numeros pseudoaleatorios.
"""

# ---------------- Gerador Congruente Linear ----------------
# Xn+1 = (a * Xn + c) mod M
a = 1103515245
c = 12345
M = 2147483648      # 2^31
seed = 7

_estado = seed
_restantes = 0      # contador de aleatorios ainda disponiveis

def NextRandom():
    """Retorna um pseudoaleatorio normalizado em [0,1) e consome 1 do orcamento."""
    global _estado, _restantes
    _estado = (a * _estado + c) % M
    _restantes -= 1
    return _estado / M


# ---------------- Simulador ----------------
def simular(servidores, capacidade,
            chegada_min, chegada_max,
            atend_min, atend_max,
            n_aleatorios, primeira_chegada=3.0):
    global _restantes
    _restantes = n_aleatorios

    tempo = 0.0
    fila = 0                         # clientes no sistema (fila + em atendimento)
    perdas = 0
    tempos = [0.0] * (capacidade + 1)  # tempo acumulado em cada estado 0..K

    # escalonador: lista de (tempo_evento, tipo)  tipo: 'C' chegada, 'S' saida
    escalonador = [(primeira_chegada, 'C')]

    def agenda(t, tipo):
        escalonador.append((t, tipo))

    def U(lo, hi):
        return lo + (hi - lo) * NextRandom()

    while _restantes > 0 and escalonador:
        # proximo evento = menor tempo agendado
        escalonador.sort()
        t_evento, tipo = escalonador.pop(0)

        # acumula tempo no estado atual
        tempos[fila] += t_evento - tempo
        tempo = t_evento

        if tipo == 'C':
            # agenda proxima chegada (consome 1 aleatorio)
            if _restantes > 0:
                agenda(tempo + U(chegada_min, chegada_max), 'C')
            # tenta entrar
            if fila < capacidade:
                fila += 1
                # se ha servidor livre, agenda saida (consome 1 aleatorio)
                if fila <= servidores and _restantes > 0:
                    agenda(tempo + U(atend_min, atend_max), 'S')
            else:
                perdas += 1
        else:  # 'S' saida
            fila -= 1
            # se ainda ha clientes esperando alem dos em atendimento, agenda nova saida
            if fila >= servidores and _restantes > 0:
                agenda(tempo + U(atend_min, atend_max), 'S')

    return tempos, tempo, perdas


def relatorio(titulo, servidores, capacidade, cmin, cmax, amin, amax, n):
    tempos, tglobal, perdas = simular(servidores, capacidade,
                                       cmin, cmax, amin, amax, n)
    print("=" * 60)
    print(titulo)
    print("=" * 60)
    print(f"Distribuicao de probabilidade dos estados:")
    print(f"{'Estado':>6} {'Tempo acumulado':>18} {'Probabilidade':>15}")
    for estado in range(capacidade + 1):
        prob = tempos[estado] / tglobal if tglobal else 0
        print(f"{estado:>6} {tempos[estado]:>18.4f} {prob*100:>13.4f}%")
    print(f"\nTempo global da simulacao: {tglobal:.4f}")
    print(f"Perda de clientes: {perdas}")
    print()


if __name__ == "__main__":
    N = 100000
    # Valores do enunciado principal (M4): chegadas 3..5, atendimento 4..5
    relatorio("G/G/1/5  chegadas [3,5]  atendimento [4,5]",
              1, 5, 3, 5, 4, 5, N)
    relatorio("G/G/2/5  chegadas [3,5]  atendimento [4,5]",
              2, 5, 3, 5, 4, 5, N)

"""
Simulador de rede de filas por eventos discretos (filas em tandem / rede generica).
Extensao do simulador de fila unica (M4) para o M6.

Gerador pseudoaleatorio: Metodo Congruente Linear (MCL) - mesmo do M4,
com orcamento (budget) global de aleatorios compartilhado entre TODAS as filas
da rede (o criterio de parada e' o consumo de N aleatorios no total).
"""

# ---------------- Gerador Congruente Linear ----------------
# Xn+1 = (a * Xn + c) mod M
a = 1103515245
c = 12345
M = 2147483648  # 2^31
seed = 7
_estado = seed
_restantes = 0  # contador de aleatorios ainda disponiveis (orcamento global da rede)


def NextRandom():
    """Retorna um pseudoaleatorio normalizado em [0,1) e consome 1 do orcamento."""
    global _estado, _restantes
    _estado = (a * _estado + c) % M
    _restantes -= 1
    return _estado / M


def U(lo, hi):
    return lo + (hi - lo) * NextRandom()


# ---------------- Estrutura de uma Fila da rede ----------------
class Fila:
    def __init__(self, nome, servidores, capacidade,
                 chegada_min=None, chegada_max=None,
                 atend_min=None, atend_max=None):
        self.nome = nome
        self.servidores = servidores
        self.capacidade = capacidade
        self.chegada_min = chegada_min
        self.chegada_max = chegada_max
        self.atend_min = atend_min
        self.atend_max = atend_max
        self.tem_chegada_externa = chegada_min is not None and chegada_max is not None

        self.n = 0            # clientes no sistema (fila + em atendimento)
        self.perdas = 0
        self.tempos = [0.0] * (capacidade + 1)  # tempo acumulado em cada estado 0..K


# ---------------- Rede de Filas (topologia generica) ----------------
class RedeFilas:
    def __init__(self):
        self.filas = {}        # nome -> Fila
        self.roteamento = {}   # nome_origem -> [(nome_destino, probabilidade), ...]

    def add_fila(self, fila):
        self.filas[fila.nome] = fila
        return fila

    def set_roteamento(self, origem, destinos):
        """destinos: lista de tuplas (nome_destino, probabilidade).
        A soma das probabilidades pode ser < 1: o restante (1 - soma)
        e' a probabilidade do cliente sair do sistema apos o atendimento em 'origem'.
        Se 'origem' nao tiver entrada aqui, 100% dos clientes saem do sistema
        ao concluir o atendimento."""
        self.roteamento[origem] = destinos

    def _rotear(self, origem):
        """Decide para onde vai o cliente que concluiu o atendimento em 'origem'.
        So consome um aleatorio quando ha' de fato uma decisao probabilistica a
        ser tomada (mais de um destino possivel, ou probabilidade de saida > 0).
        Quando o roteamento e' deterministico (um unico destino com prob. 1.0),
        nenhum aleatorio e' consumido."""
        destinos = self.roteamento.get(origem, [])
        if not destinos:
            return None  # sai do sistema (sem roteamento definido)
        if len(destinos) == 1 and destinos[0][1] >= 1.0:
            return destinos[0][0]  # roteamento deterministico

        r = NextRandom()
        acumulado = 0.0
        for destino, prob in destinos:
            acumulado += prob
            if r < acumulado:
                return destino
        return None  # sai do sistema

    def _tenta_entrar(self, fila, tempo):
        """Tenta inserir um cliente na fila; se nao houver capacidade, conta perda.
        Se houver servidor livre, agenda o fim do atendimento (consome 1 aleatorio)."""
        if fila.n < fila.capacidade:
            fila.n += 1
            if fila.n <= fila.servidores and _restantes > 0:
                self._agenda(tempo + U(fila.atend_min, fila.atend_max), 'S', fila.nome)
        else:
            fila.perdas += 1

    def _agenda(self, t, tipo, nome):
        self.escalonador.append((t, tipo, nome))

    def simular(self, n_aleatorios, primeira_chegada=2.5):
        global _restantes
        _restantes = n_aleatorios
        tempo = 0.0
        self.escalonador = []  # (tempo_evento, tipo, fila_nome) ; tipo: 'C' chegada externa, 'S' saida

        # zera estado de todas as filas (permite rodar simular() mais de uma vez)
        for f in self.filas.values():
            f.n = 0
            f.perdas = 0
            f.tempos = [0.0] * (f.capacidade + 1)

        # agenda a primeira chegada externa de cada fila que recebe clientes de fora
        for nome, fila in self.filas.items():
            if fila.tem_chegada_externa:
                self._agenda(primeira_chegada, 'C', nome)

        while _restantes > 0 and self.escalonador:
            self.escalonador.sort(key=lambda e: e[0])
            t_evento, tipo, nome = self.escalonador.pop(0)
            fila = self.filas[nome]

            # acumula o tempo decorrido no estado atual de TODAS as filas da rede
            for f in self.filas.values():
                f.tempos[f.n] += t_evento - tempo
            tempo = t_evento

            if tipo == 'C':
                # agenda a proxima chegada externa desta fila
                if _restantes > 0:
                    self._agenda(tempo + U(fila.chegada_min, fila.chegada_max), 'C', nome)
                self._tenta_entrar(fila, tempo)

            else:  # 'S' -> fim de atendimento
                fila.n -= 1
                # se ainda houver clientes aguardando alem dos em atendimento, agenda a proxima saida
                if fila.n >= fila.servidores and _restantes > 0:
                    self._agenda(tempo + U(fila.atend_min, fila.atend_max), 'S', nome)

                # roteia o cliente que acabou de ser atendido para a proxima fila (ou saida do sistema)
                destino = self._rotear(nome)
                if destino is not None:
                    self._tenta_entrar(self.filas[destino], tempo)

        return tempo

    def relatorio(self, titulo, tglobal):
        linhas = []
        linhas.append("=" * 70)
        linhas.append(titulo)
        linhas.append("=" * 70)
        for nome, fila in self.filas.items():
            linhas.append(f"\n-- {nome} --")
            linhas.append(f"{'Estado':>6} {'Tempo acumulado':>18} {'Probabilidade':>15}")
            for estado in range(fila.capacidade + 1):
                prob = fila.tempos[estado] / tglobal if tglobal else 0
                linhas.append(f"{estado:>6} {fila.tempos[estado]:>18.4f} {prob*100:>13.4f}%")
            linhas.append(f"Perda de clientes ({nome}): {fila.perdas}")
        linhas.append(f"\nTempo global da simulacao: {tglobal:.4f}")
        texto = "\n".join(linhas)
        print(texto)
        return texto


if __name__ == "__main__":
    N = 100000

    rede = RedeFilas()
    # Fila 1: G/G/2/3, chegadas externas entre 1..5, atendimento entre 4..5
    fila1 = rede.add_fila(Fila("Fila 1", servidores=2, capacidade=3,
                                chegada_min=1, chegada_max=5,
                                atend_min=4, atend_max=5))
    # Fila 2: G/G/1/5, SEM chegada externa (so recebe da Fila 1), atendimento entre 1..3
    fila2 = rede.add_fila(Fila("Fila 2", servidores=1, capacidade=5,
                                chegada_min=None, chegada_max=None,
                                atend_min=1, atend_max=3))

    # Topologia: Fila 1 -> Fila 2 (100% dos atendidos na Fila 1 vao para a Fila 2)
    rede.set_roteamento("Fila 1", [("Fila 2", 1.0)])
    # Fila 2 nao tem roteamento definido -> 100% dos atendidos saem do sistema

    tglobal = rede.simular(N, primeira_chegada=2.5)
    rede.relatorio("Rede em tandem: Fila 1 -> Fila 2", tglobal)

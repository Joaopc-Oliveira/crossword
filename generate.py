import sys
import copy
from collections import deque
from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Cria um novo gerador de CSP para crosswords.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Retorna uma matriz 2D representando uma determinada atribuição.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Imprime a atribuição do crossword no terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Salva a atribuição do crossword em um arquivo de imagem.
        """
        from PIL import Image, ImageDraw, ImageFont

        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Cria uma tela em branco
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        try:
            font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        except IOError:
            font = ImageFont.load_default()
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        # Centraliza o texto na célula
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Aplica consistência de nó e arco, e então resolve o CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Atualiza `self.domains` de forma que cada variável seja consistente com o nó.
        Remove quaisquer palavras que não correspondam ao comprimento da variável.
        """
        for var in self.crossword.variables:
            words_to_remove = set()
            for word in self.domains[var]:
                if len(word) != var.length:
                    words_to_remove.add(word)
            if words_to_remove:
                self.domains[var] -= words_to_remove

    def revise(self, x, y):
        """
        Torna a variável x consistente com a variável y.
        Retorna True se alguma revisão foi feita na domínio de x; False caso contrário.
        """
        revised = False
        overlap = self.crossword.overlaps.get((x, y))

        if overlap is None:
            return False  # Nenhuma sobreposição, nenhuma revisão necessária

        xi, yi = overlap
        words_to_remove = set()

        for word_x in self.domains[x]:
            # Verifica se existe pelo menos uma palavra em y que seja compatível
            match_found = False
            for word_y in self.domains[y]:
                if word_x[xi] == word_y[yi]:
                    match_found = True
                    break
            if not match_found:
                words_to_remove.add(word_x)
                revised = True

        if revised:
            self.domains[x] -= words_to_remove

        return revised

    def ac3(self, arcs=None):
        """
        Aplica o algoritmo AC3 para impor consistência de arco.
        Retorna True se a consistência for alcançada sem domínios vazios; False caso contrário.
        """
        queue = deque()

        if arcs is None:
            # Inicializa a fila com todos os arcos
            for var in self.crossword.variables:
                for neighbor in self.crossword.neighbors(var):
                    queue.append((var, neighbor))
        else:
            for arc in arcs:
                queue.append(arc)

        while queue:
            (x, y) = queue.popleft()
            if self.revise(x, y):
                if not self.domains[x]:
                    return False  # Domínio eliminado
                for neighbor in self.crossword.neighbors(x):
                    if neighbor != y:
                        queue.append((neighbor, x))
        return True

    def assignment_complete(self, assignment):
        """
        Verifica se a atribuição está completa.
        """
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment):
        """
        Verifica se a atribuição é consistente.
        """
        assigned_words = set()
        for var, word in assignment.items():
            # Verifica unicidade das palavras
            if word in assigned_words:
                return False
            assigned_words.add(word)
            # Verifica consistência do comprimento
            if len(word) != var.length:
                return False
            # Verifica sobreposições com vizinhos
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    overlap = self.crossword.overlaps.get((var, neighbor))
                    if overlap:
                        xi, yi = overlap
                        if word[xi] != assignment[neighbor][yi]:
                            return False
        return True

    def order_domain_values(self, var, assignment):
        """
        Retorna uma lista de valores no domínio de var, ordenados pela heurística do menor conflito.
        """
        def count_conflicts(value):
            count = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor in assignment:
                    continue
                overlap = self.crossword.overlaps.get((var, neighbor))
                if overlap:
                    xi, yi = overlap
                    for neighbor_word in self.domains[neighbor]:
                        if value[xi] != neighbor_word[yi]:
                            count += 1
            return count

        # Ordena os valores pelo número de conflitos (ascendente)
        return sorted(self.domains[var], key=count_conflicts)

    def select_unassigned_variable(self, assignment):
        """
        Seleciona uma variável não atribuída usando as heurísticas MRV e de Grau.
        """
        unassigned_vars = [v for v in self.crossword.variables if v not in assignment]
        # Heurística MRV: menor número de valores no domínio
        min_domain_size = min(len(self.domains[var]) for var in unassigned_vars)
        mrv_vars = [var for var in unassigned_vars if len(self.domains[var]) == min_domain_size]
        if len(mrv_vars) == 1:
            return mrv_vars[0]
        # Heurística de Grau: maior número de vizinhos
        max_degree = -1
        selected_var = None
        for var in mrv_vars:
            degree = len(self.crossword.neighbors(var))
            if degree > max_degree:
                max_degree = degree
                selected_var = var
        return selected_var

    def backtrack(self, assignment):
        """
        Realiza uma busca de backtracking para encontrar uma atribuição completa e consistente.
        """
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            # Cria uma nova atribuição incluindo var=value
            local_assignment = assignment.copy()
            local_assignment[var] = value
            if self.consistent(local_assignment):
                # Inference: faz uma cópia dos domínios
                saved_domains = copy.deepcopy(self.domains)
                self.domains[var] = {value}
                # Impõe consistência de arco após a atribuição
                if self.ac3([(neighbor, var) for neighbor in self.crossword.neighbors(var)]):
                    result = self.backtrack(local_assignment)
                    if result:
                        return result
                # Restaura os domínios
                self.domains = saved_domains
        return None


def main():
    if len(sys.argv) not in [3, 4]:
        sys.exit("Uso: python generate.py estrutura.txt palavras.txt [output.png]")

    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()
    if assignment is None:
        print("Nenhuma solução encontrada.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()

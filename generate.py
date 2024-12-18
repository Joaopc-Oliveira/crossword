import sys
from crossword import Crossword, Variable
import copy
from collections import deque

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generator.
        """
        self.crossword = crossword
        # Domains is a dictionary mapping each variable to a set of possible words
        self.domains = {
            var: copy.deepcopy(crossword.words)
            for var in crossword.variables
        }

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP using backtracking.
        Returns a complete assignment if possible, else None.
        """
        self.enforce_node_consistency()
        if not self.ac3():
            return None
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        Remove any words that don't match the variable's length.
        """
        for var in self.crossword.variables:
            # Create a copy to avoid modifying the set during iteration
            words_to_remove = set()
            for word in self.domains[var]:
                if len(word) != var.length:
                    words_to_remove.add(word)
            self.domains[var] -= words_to_remove

    def revise(self, x, y):
        """
        Make variable x arc consistent with variable y.
        Returns True if a revision was made to the domain of x; False otherwise.
        """
        revised = False
        overlap = self.crossword.overlaps.get((x, y))
        if overlap is None:
            return False  # No overlap, no revision needed

        xi, yi = overlap
        words_to_remove = set()

        for word_x in self.domains[x]:
            # Check if there exists at least one word in y's domain that matches at the overlap
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
        Enforce arc consistency using the AC3 algorithm.
        Returns True if arc consistency is enforced without empty domains; False otherwise.
        """
        queue = deque()
        if arcs is None:
            # Initialize queue with all arcs
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
                    return False  # Domain wiped out
                for neighbor in self.crossword.neighbors(x):
                    if neighbor != y:
                        queue.append((neighbor, x))
        return True

    def assignment_complete(self, assignment):
        """
        Check if the assignment is complete.
        """
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment):
        """
        Check if the assignment is consistent.
        """
        assigned_words = set()
        for var, word in assignment.items():
            # Check word uniqueness
            if word in assigned_words:
                return False
            assigned_words.add(word)
            # Check length consistency
            if len(word) != var.length:
                return False
            # Check overlaps
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
        Return a list of values in the domain of var, ordered by the least-constraining value heuristic.
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

        # Sort the domain values by the number of conflicts they impose on neighbors (ascending)
        return sorted(self.domains[var], key=count_conflicts)

    def select_unassigned_variable(self, assignment):
        """
        Select an unassigned variable using the Minimum Remaining Values (MRV) and Degree heuristics.
        """
        unassigned_vars = [v for v in self.crossword.variables if v not in assignment]
        # MRV: minimum remaining values
        min_domain_size = min(len(self.domains[var]) for var in unassigned_vars)
        mrv_vars = [var for var in unassigned_vars if len(self.domains[var]) == min_domain_size]
        if len(mrv_vars) == 1:
            return mrv_vars[0]
        # Degree heuristic: variable with the most neighbors
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
        Perform backtracking search to find a complete and consistent assignment.
        """
        if self.assignment_complete(assignment):
            return assignment

        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            # Create a new assignment including var=value
            local_assignment = assignment.copy()
            local_assignment[var] = value
            if self.consistent(local_assignment):
                # Inference: make a copy of domains
                saved_domains = copy.deepcopy(self.domains)
                self.domains[var] = {value}
                # Enforce arc consistency after assignment
                if self.ac3([(neighbor, var) for neighbor in self.crossword.neighbors(var)]):
                    result = self.backtrack(local_assignment)
                    if result:
                        return result
                # Restore domains
                self.domains = saved_domains
        return None

    def print(self, assignment):
        """
        Print the crossword assignment to the terminal.
        """
        # Implementation provided in the project
        pass

    def save(self, assignment, filename):
        """
        Save the crossword assignment as an image file.
        """
        # Implementation provided in the project
        pass

def main():
    import sys

    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure.txt words.txt [output.png]")

    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)

if __name__ == "__main__":
    main()

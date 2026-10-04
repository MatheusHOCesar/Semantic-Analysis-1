# semantic.py
from ast_nodes import Program
from name_resolver import NameResolver
from type_checker import TypeChecker

class SemanticAnalyzer:
    def analyze(self, program: Program) -> Program:
        """
        Executa as duas passagens da análise semântica.
        """
        # Passagem 1: Nomes e Escopos
        resolver = NameResolver()
        program = resolver.resolve(program)
        
        # Passagem 2: Verificacao de Tipos
        # (Se a passagem 1 lancar SemanticError, a execucao nem chega aqui)
        checker = TypeChecker()
        program = checker.check(program)
        
        return program
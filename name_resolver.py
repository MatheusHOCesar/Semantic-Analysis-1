from ast_nodes import (
    Program, FunctionDecl, Parameter, Block, Stmt, Expr,
    VarDecl, IfStmt, WhileStmt, ReturnStmt, PrintStmt,
    Assignment, CallStmt, TypeName,
    IdentifierExpr, CallExpr, BinaryExpr, UnaryExpr
)
from symbols import Symbol, FunctionSymbol, SymbolKind, Scope
from semantic_errors import SemanticDiagnostic, SemanticErrorKind, SemanticError

class NameResolver:
    def __init__(self):
        self.diagnostics: list[SemanticDiagnostic] = []
        self.global_functions: dict[str, FunctionSymbol] = {}
        self.current_scope: Scope | None = None

    def report(self, kind: SemanticErrorKind, message: str, span):
        self.diagnostics.append(SemanticDiagnostic(kind, message, span))

    def _set_metadata(self, node, key, value):
        if not hasattr(node, 'metadata'): node.metadata = {}
        node.metadata[key] = value

    def resolve(self, program: Program) -> Program:
        for func in program.functions:
            if func.name in self.global_functions:
                self.report(SemanticErrorKind.DUPLICATE_FUNCTION, f"função '{func.name}' já declarada", func.span)
                continue
            
            param_types = tuple(p.type for p in func.parameters)
            func_sym = FunctionSymbol(name=func.name, kind=SymbolKind.FUNCTION, type=func.return_type, declaration=func, parameter_types=param_types)
            self.global_functions[func.name] = func_sym
            self._set_metadata(func, 'symbol', func_sym)

        main_sym = self.global_functions.get("main")
        if not main_sym or main_sym.type != TypeName.INT or len(main_sym.parameter_types) > 0:
            self.report(SemanticErrorKind.INVALID_MAIN, "ausência de main ou assinatura diferente", program.span)

        for func in program.functions:
            self.visit_function(func)

        if self.diagnostics:
            raise SemanticError(self.diagnostics)
        return program

    def visit_function(self, func: FunctionDecl):
        scope = Scope(parent=None)
        self.current_scope = scope
        self._set_metadata(func.body, 'scope', scope)

        for param in func.parameters:
            if param.name in scope.symbols:
                self.report(SemanticErrorKind.DUPLICATE_DECLARATION, f"parâmetro '{param.name}' repetido", param.span)
            else:
                sym = Symbol(param.name, SymbolKind.PARAMETER, param.type, param)
                scope.symbols[param.name] = sym
                self._set_metadata(param, 'symbol', sym)

        for stmt in func.body.statements:
            self.visit_statement(stmt)
        self.current_scope = None

    def visit_block(self, block: Block):
        prev_scope = self.current_scope
        scope = Scope(parent=prev_scope)
        self.current_scope = scope
        self._set_metadata(block, 'scope', scope)

        for stmt in block.statements:
            self.visit_statement(stmt)
        self.current_scope = prev_scope

    def visit_statement(self, stmt: Stmt):
        if isinstance(stmt, VarDecl):
            if stmt.name in self.current_scope.symbols:
                self.report(SemanticErrorKind.DUPLICATE_DECLARATION, f"variável '{stmt.name}' já declarada", stmt.span)
            else:
                sym = Symbol(stmt.name, SymbolKind.VARIABLE, getattr(stmt, 'type', stmt.var_type), stmt)
                self.current_scope.symbols[stmt.name] = sym
                self._set_metadata(stmt, 'symbol', sym)
            
            if getattr(stmt, 'initializer', None):
                self.visit_expression(stmt.initializer)
        elif isinstance(stmt, Block):
            self.visit_block(stmt)
        elif isinstance(stmt, IfStmt):
            self.visit_expression(stmt.cond)
            self.visit_block(stmt.then_b)
            if getattr(stmt, 'else_b', None): self.visit_block(stmt.else_b)
        elif isinstance(stmt, WhileStmt):
            self.visit_expression(stmt.cond)
            self.visit_block(stmt.body)
        elif isinstance(stmt, Assignment):
            self.visit_expression(stmt.target)
            self.visit_expression(stmt.value)
        elif isinstance(stmt, CallStmt):
            self.visit_expression(stmt.call)
        elif isinstance(stmt, ReturnStmt):
            if getattr(stmt, 'value', None): self.visit_expression(stmt.value)
        elif isinstance(stmt, PrintStmt):
            for item in stmt.items:
                if isinstance(item, Expr): self.visit_expression(item)

    def visit_expression(self, expr: Expr):
        if isinstance(expr, IdentifierExpr):
            sym = self.lookup_variable(expr.name)
            if not sym:
                self.report(SemanticErrorKind.UNDECLARED_VARIABLE, f"variável '{expr.name}' sem declaração visível", expr.span)
            else:
                self._set_metadata(expr, 'symbol', sym)
        elif isinstance(expr, CallExpr):
            name = getattr(expr, 'name', None) or getattr(expr, 'ident', expr.__dict__.get('name'))
            sym = self.global_functions.get(name)
            if not sym:
                self.report(SemanticErrorKind.UNDECLARED_FUNCTION, f"função inexistente '{name}'", expr.span)
            else:
                self._set_metadata(expr, 'symbol', sym)
            for arg in expr.args:
                self.visit_expression(arg)
        elif isinstance(expr, BinaryExpr):
            self.visit_expression(expr.left)
            self.visit_expression(expr.right)
        elif isinstance(expr, UnaryExpr):
            self.visit_expression(expr.operand)

    def lookup_variable(self, name: str) -> Symbol | None:
        scope = self.current_scope
        while scope is not None:
            if name in scope.symbols: return scope.symbols[name]
            scope = scope.parent
        return None
# type_checker.py
from ast_nodes import (
    Program, FunctionDecl, Block, Stmt, Expr,
    VarDecl, IfStmt, WhileStmt, ReturnStmt, PrintStmt,
    Assignment, CallStmt, TypeName
)
from semantic_errors import SemanticDiagnostic, SemanticErrorKind, SemanticError

INT_MAX = 2**63 - 1

class TypeChecker:
    def __init__(self):
        self.diagnostics: list[SemanticDiagnostic] = []
        self.current_func_return_type: TypeName | None = None

    def report(self, kind: SemanticErrorKind, message: str, span):
        self.diagnostics.append(SemanticDiagnostic(kind, message, span))

    def _set_metadata(self, node, key, value):
        if not hasattr(node, 'metadata'): node.metadata = {}
        node.metadata[key] = value

    def check(self, program: Program) -> Program:
        for func in program.functions:
            self.visit_function(func)
        if self.diagnostics:
            raise SemanticError(self.diagnostics)
        return program

    def visit_function(self, func: FunctionDecl):
        self.current_func_return_type = func.return_type
        for param in func.parameters:
            if param.type == TypeName.VOID:
                self.report(SemanticErrorKind.VOID_PARAMETER, "parâmetro não pode ser void", param.span)
        self.visit_block(func.body)
        self.current_func_return_type = None

    def visit_block(self, block: Block):
        for stmt in block.statements:
            self.visit_statement(stmt)

    def visit_statement(self, stmt: Stmt):
        if isinstance(stmt, VarDecl):
            var_type = getattr(stmt, 'type', stmt.var_type)
            if var_type == TypeName.VOID:
                self.report(SemanticErrorKind.VOID_VARIABLE, "variável não pode ser void", stmt.span)
            init_expr = getattr(stmt, 'initializer', None)
            if init_expr:
                init_type = self.visit_expression(init_expr)
                if init_type and init_type != var_type:
                    self.report(SemanticErrorKind.INITIALIZER_TYPE_MISMATCH, "tipo incompatível no inicializador", init_expr.span)

        elif isinstance(stmt, Block):
            self.visit_block(stmt)
        elif isinstance(stmt, IfStmt):
            cond_type = self.visit_expression(stmt.cond)
            if cond_type and cond_type != TypeName.BOOL:
                self.report(SemanticErrorKind.CONDITION_TYPE_MISMATCH, "if exige bool", stmt.cond.span)
            self.visit_block(stmt.then_b)
            if getattr(stmt, 'else_b', None): self.visit_block(stmt.else_b)
        elif isinstance(stmt, WhileStmt):
            cond_type = self.visit_expression(stmt.cond)
            if cond_type and cond_type != TypeName.BOOL:
                self.report(SemanticErrorKind.CONDITION_TYPE_MISMATCH, "while exige bool", stmt.cond.span)
            self.visit_block(stmt.body)
        elif isinstance(stmt, Assignment):
            t_type = self.visit_expression(stmt.target)
            v_type = self.visit_expression(stmt.value)
            if t_type and v_type and t_type != v_type:
                self.report(SemanticErrorKind.ASSIGNMENT_TYPE_MISMATCH, "atribuição incompatível", stmt.value.span)
        elif isinstance(stmt, CallStmt):
            self.visit_expression(stmt.call)
        elif isinstance(stmt, ReturnStmt):
            val_expr = getattr(stmt, 'value', None)
            if self.current_func_return_type == TypeName.VOID:
                if val_expr: self.report(SemanticErrorKind.RETURN_MISMATCH, "função void não retorna valor", stmt.span)
            else:
                if not val_expr: self.report(SemanticErrorKind.RETURN_MISMATCH, "falta expressão no return", stmt.span)
                else:
                    ret_type = self.visit_expression(val_expr)
                    if ret_type and ret_type != self.current_func_return_type:
                        self.report(SemanticErrorKind.RETURN_MISMATCH, "tipo de retorno incompatível", val_expr.span)
        elif isinstance(stmt, PrintStmt):
            for item in stmt.items:
                if isinstance(item, Expr):
                    it_type = self.visit_expression(item)
                    if it_type and it_type not in (TypeName.INT, TypeName.BOOL):
                        self.report(SemanticErrorKind.ARGUMENT_TYPE_MISMATCH, "print aceita int/bool/string", item.span)

    # Stub para não quebrar a compilação, o Kafer vai preencher isso no commit dele
    def visit_expression(self, expr: Expr) -> TypeName | None:
        pass
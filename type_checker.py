# type_checker.py
from ast_nodes import (
    Program, FunctionDecl, Block, Stmt, Expr, VarDecl, IfStmt, WhileStmt, ReturnStmt, PrintStmt, Assignment, CallStmt, TypeName, IdentifierExpr, CallExpr, BinaryExpr, UnaryExpr, IntLiteral, BoolLiteral, StringLiteral, BinaryOperator, UnaryOperator)
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

    def visit_expression(self, expr: Expr) -> TypeName | None:
        expr_type = None

        if isinstance(expr, IntLiteral):
            if 0 <= expr.value <= INT_MAX:
                expr_type = TypeName.INT
            else:
                self.report(SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE, "literal fora do limite", expr.span)
        elif isinstance(expr, BoolLiteral):
            expr_type = TypeName.BOOL
        elif isinstance(expr, StringLiteral):
            pass 
        elif isinstance(expr, IdentifierExpr):
            sym = expr.metadata.get('symbol')
            if sym: expr_type = sym.type
        elif isinstance(expr, UnaryExpr):
            op_type = self.visit_expression(expr.operand)
            if op_type:
                if expr.operator == UnaryOperator.NOT and op_type != TypeName.BOOL:
                    self.report(SemanticErrorKind.INVALID_UNARY_OPERAND, "! exige bool", expr.span)
                elif expr.operator == UnaryOperator.NEGATE and op_type != TypeName.INT:
                    self.report(SemanticErrorKind.INVALID_UNARY_OPERAND, "- unário exige int", expr.span)
                expr_type = op_type
        elif isinstance(expr, BinaryExpr):
            left_type = self.visit_expression(expr.left)
            right_type = self.visit_expression(expr.right)
            
            if left_type and right_type:
                is_arithmetic = expr.operator in (BinaryOperator.ADD, BinaryOperator.SUBTRACT, BinaryOperator.MULTIPLY, BinaryOperator.DIVIDE, BinaryOperator.REMAINDER)
                is_relational = expr.operator in (BinaryOperator.LESS, BinaryOperator.LESS_EQUAL, BinaryOperator.GREATER, BinaryOperator.GREATER_EQUAL)
                is_equality = expr.operator in (BinaryOperator.EQUAL, BinaryOperator.NOT_EQUAL)
                is_logical = expr.operator in (BinaryOperator.LOGICAL_AND, BinaryOperator.LOGICAL_OR)

                if is_arithmetic or is_relational:
                    if left_type != TypeName.INT or right_type != TypeName.INT:
                        self.report(SemanticErrorKind.INVALID_BINARY_OPERANDS, "exige ints", expr.span)
                    expr_type = TypeName.INT if is_arithmetic else TypeName.BOOL
                elif is_logical:
                    if left_type != TypeName.BOOL or right_type != TypeName.BOOL:
                        self.report(SemanticErrorKind.INVALID_BINARY_OPERANDS, "exige bools", expr.span)
                    expr_type = TypeName.BOOL
                elif is_equality:
                    if left_type != right_type:
                        self.report(SemanticErrorKind.INVALID_BINARY_OPERANDS, "exige tipos iguais", expr.span)
                    expr_type = TypeName.BOOL
        elif isinstance(expr, CallExpr):
            sym = expr.metadata.get('symbol')
            if sym:
                if len(expr.args) != len(sym.parameter_types):
                    self.report(SemanticErrorKind.ARITY_MISMATCH, "aridade incorreta", expr.span)
                else:
                    for arg, param_type in zip(expr.args, sym.parameter_types):
                        arg_type = self.visit_expression(arg)
                        if arg_type and arg_type != param_type:
                            self.report(SemanticErrorKind.ARGUMENT_TYPE_MISMATCH, "tipo incorreto", arg.span)
                expr_type = sym.type

        if expr_type and not isinstance(expr, StringLiteral):
            self._set_metadata(expr, 'type', expr_type)
            
        return expr_type
        pass
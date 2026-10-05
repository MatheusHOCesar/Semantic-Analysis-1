# type_checker.py
from ast_nodes import (
    Program, FunctionDecl, Block, Stmt, Expr,
    VarDecl, IfStmt, WhileStmt, ReturnStmt, PrintStmt,
    Assignment, CallStmt, TypeName,
    IdentifierExpr, CallExpr, BinaryExpr, UnaryExpr,
    IntLiteral, BoolLiteral, StringLiteral, BinaryOperator, UnaryOperator
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
            if stmt.type == TypeName.VOID:
                self.report(SemanticErrorKind.VOID_VARIABLE, "variável não pode ser void", stmt.span)
            if stmt.initializer:
                init_type = self.visit_expression(stmt.initializer)
                # O "and stmt.type != TypeName.VOID" evita erro em cascata quando a variável já era inválida
                if init_type and stmt.type != TypeName.VOID and init_type != stmt.type:
                    self.report(SemanticErrorKind.INITIALIZER_TYPE_MISMATCH, "tipo incompatível no inicializador", stmt.initializer.span)
        elif isinstance(stmt, Block):
            self.visit_block(stmt)
        elif isinstance(stmt, IfStmt):
            cond_type = self.visit_expression(stmt.condition)
            if cond_type and cond_type != TypeName.BOOL:
                self.report(SemanticErrorKind.CONDITION_TYPE_MISMATCH, "if exige bool", stmt.condition.span)
            self.visit_block(stmt.then_block)
            if stmt.else_block: self.visit_block(stmt.else_block)
        elif isinstance(stmt, WhileStmt):
            cond_type = self.visit_expression(stmt.condition)
            if cond_type and cond_type != TypeName.BOOL:
                self.report(SemanticErrorKind.CONDITION_TYPE_MISMATCH, "while exige bool", stmt.condition.span)
            self.visit_block(stmt.body)
        elif isinstance(stmt, Assignment):
            t_type = self.visit_expression(stmt.target)
            v_type = self.visit_expression(stmt.value)
            if t_type and v_type and t_type != v_type:
                self.report(SemanticErrorKind.ASSIGNMENT_TYPE_MISMATCH, "atribuição incompatível", stmt.value.span)
        elif isinstance(stmt, CallStmt):
            # is_stmt=True avisa que essa chamada não está sendo usada como valor matemático
            self.visit_expression(stmt.call, is_stmt=True)
        elif isinstance(stmt, ReturnStmt):
            if self.current_func_return_type == TypeName.VOID:
                if stmt.value: self.report(SemanticErrorKind.RETURN_MISMATCH, "função void não retorna valor", stmt.span)
            else:
                if not stmt.value: self.report(SemanticErrorKind.RETURN_MISMATCH, "falta expressão no return", stmt.span)
                else:
                    ret_type = self.visit_expression(stmt.value)
                    if ret_type and ret_type != self.current_func_return_type:
                        self.report(SemanticErrorKind.RETURN_MISMATCH, "tipo de retorno incompatível", stmt.value.span)
        elif isinstance(stmt, PrintStmt):
            for item in stmt.items:
                if isinstance(item, Expr):
                    it_type = self.visit_expression(item)
                    if it_type and it_type not in (TypeName.INT, TypeName.BOOL):
                        self.report(SemanticErrorKind.ARGUMENT_TYPE_MISMATCH, "print aceita int/bool/string", item.span)

    # Note o is_stmt=False
    def visit_expression(self, expr: Expr, is_stmt: bool = False) -> TypeName | None:
        expr_type = None

        if isinstance(expr, IntLiteral):
            if 0 <= expr.value <= INT_MAX:
                expr_type = TypeName.INT
            else:
                self.report(SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE, "literal fora do limite", expr.span)
                expr_type = None # Transforma em tipo desconhecido para não gerar efeito cascata
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
                    expr_type = None
                elif expr.operator == UnaryOperator.NEGATE and op_type != TypeName.INT:
                    self.report(SemanticErrorKind.INVALID_UNARY_OPERAND, "- unário exige int", expr.span)
                    expr_type = None
                else:
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
                        expr_type = None
                    else:
                        expr_type = TypeName.INT if is_arithmetic else TypeName.BOOL
                elif is_logical:
                    if left_type != TypeName.BOOL or right_type != TypeName.BOOL:
                        self.report(SemanticErrorKind.INVALID_BINARY_OPERANDS, "exige bools", expr.span)
                        expr_type = None
                    else:
                        expr_type = TypeName.BOOL
                elif is_equality:
                    if left_type != right_type:
                        self.report(SemanticErrorKind.INVALID_BINARY_OPERANDS, "exige tipos iguais", expr.span)
                        expr_type = None
                    else:
                        expr_type = TypeName.BOOL
        elif isinstance(expr, CallExpr):
            sym = expr.metadata.get('symbol')
            if sym:
                has_error = False
                if len(expr.arguments) != len(sym.parameter_types):
                    self.report(SemanticErrorKind.ARITY_MISMATCH, "aridade incorreta", expr.span)
                    has_error = True
                
                for i, arg in enumerate(expr.arguments):
                    arg_type = self.visit_expression(arg)
                    if i < len(sym.parameter_types):
                        param_type = sym.parameter_types[i]
                        if arg_type and arg_type != param_type:
                            self.report(SemanticErrorKind.ARGUMENT_TYPE_MISMATCH, "tipo de argumento incorreto", arg.span)
                            has_error = True
                
                if sym.type == TypeName.VOID and not is_stmt:
                    self.report(SemanticErrorKind.VOID_VALUE_USED, "void usado como valor", expr.span)
                    has_error = True
                    
                expr_type = None if has_error else sym.type

        if expr_type and not isinstance(expr, StringLiteral):
            self._set_metadata(expr, 'type', expr_type)
            
        return expr_type
# this clean the formulas that we get from the KB
import re

from src.app.models import exceptions
from src.app.services.knowledge_base import get_closest_kpi_formula, get_kpi_formula


def clean_placeholders(formulas: dict[str, str]):
    """
    Cleans the formula from the placeholders used in the KB. The placeholders are as °T°m°o, ...
    When it encounters operations such as idle, working, offline, it saves them in a list.

    :param formulas: The formulas dictionary to clean
    :return The cleaned formulas dictionary and the operations list
    """
    cleaned_formulas = {}
    operations = []

    for key, formula in formulas.items():

        # Search and remove specific placeholders
        placeholders = {
            "°T°m°idle°": "idle",
            "°T°m°working°": "working",
            "°T°m°offline°": "offline",
            "°T°M°idle°": "idle",
            "°T°M°working°": "working",
            "°T°M°offline°": "offline",
        }

        for placeholder, operation in placeholders.items():
            if placeholder in formula:
                operations.append(operation)
                formula = formula.replace(placeholder, "")

        # Remove other placeholders
        formula = re.sub(r"°t°m°o°", "", formula)
        formula = re.sub(r"°T°m°o°", "", formula)

        # Save the cleaned formula with no wrapping spaces
        cleaned_formulas[key] = formula.strip()

    return cleaned_formulas, operations


def remove_aggregations(result: dict[str, str]) -> dict[str, str]:
    """
    Removes the A° aggregations from the formula and saves the outermost one.
    If there are binary operations, it transforms them into a numexpr-parsable formula.

    :param result: The result dictionary containing the formula to clean
    :return The cleaned result dictionary with all infos to compute the formula
    """

    formula = result["formula"]

    formula = re.sub(r"°t", "", formula)
    formula = re.sub(r"°mo", "", formula)
    # replace with capital M to avoid matching max. min, ...
    formula = re.sub(r"A°m", "A°M", formula)
    #
    formula = re.sub(r"°m", "", formula)

    index = float("inf")

    agg_functions = ["A°sum[", "A°Mean[", "A°max[", "A°Min[", "A°var[", "A°std["]

    first_aggregation = None

    # until there are aggregations in the formula
    while any(agg_func in formula for agg_func in agg_functions):
        # do it for every possible aggregation sice we don't know the outermost one
        start_index = -1
        for agg_func in agg_functions:
            start_index = formula.find(agg_func)
            # if we find the aggregation in the formula
            if start_index != -1:
                # if the first aggregation has not been found, or if the current one is before the first one
                if first_aggregation is None or start_index < index:
                    index = start_index
                    # first aggregation is the first match
                    first_aggregation = agg_func.strip("A°[").lower()
                break

        # We interrupt immediately if we don't find anything
        if start_index == -1:
            break

        # we initialize a counter for the [ and ] in particular we increase if we find a [ and decrease if ] so we
        # delete the aggregation and the corresponding []
        depth = 1
        end_index = start_index + len(agg_func)

        # Here the implementation of the logic explained before
        for i, char in enumerate(formula[end_index:]):
            match char:
                case "[":
                    depth += 1
                case "]":
                    depth -= 1

            if depth == 0:
                end_index += i
                break

        # here we check if the ] is the last char of the formula then we return a new expression that starts from
        #  the next char after A°aggr[ and end at the last char before the ] and we have two cases :
        # the first if the ] is at the end of the expression
        # the second if th ] is in the middle of the expression
        if (len(formula) - 1) == end_index:
            formula = (
                formula[:start_index] + formula[start_index + len(agg_func) : end_index]
            )
        else:
            formula = (
                formula[:start_index]
                + formula[start_index + len(agg_func) : end_index]
                + formula[end_index + 1 :]
            )

        # remove external spaces
        formula = "".join(formula.split())

    result["formula"] = formula
    result["agg"] = first_aggregation
    return result


def to_evaluable(formula: str):
    """
    Transforms the expression in a parsable form for the numexpr library.
    It transforms the binary operations in a parsable form for the numexpr library.

    :param formula: The expression to transform
    :return The transformed expression
    """
    # Map of the possible operator that we can find
    operator_map = ["S°/", "S°*", "S°+", "S°-", "S°**"]

    # we check for the possible S° operator, and we start from the outer one

    while any(op in formula for op in operator_map):
        start_index = -1
        for op in operator_map:
            start_index = formula.find(op + "[")
            print(start_index)
            if start_index != -1:
                break

        # if we don't find an operator
        if start_index == -1:
            break

        # we initialize a counter for the  [] parenthesis in increase the counter by one if we find [ and decrease
        # by one if we find a ] so when we find a ; and counter ==1 we substitute it with the operator, and then
        # we put () instead []
        depth = 1
        end_index = start_index + len(op) + 1
        semicolon_index = None

        for i, char in enumerate(
            formula[start_index + len(op) + 1 :], start=start_index + len(op) + 1
        ):
            match char:
                case "[":
                    depth += 1
                case "]":
                    depth -= 1
                case ";" if depth == 1:
                    semicolon_index = i

            if depth == 0:
                end_index = i
                break

        # substitute the most internal block with the operator
        if semicolon_index is not None:
            # substitute the semicolon with the operator
            formula = (
                formula[:start_index]
                + "("
                + formula[start_index + len(op) + 1 : semicolon_index]
                + f" {op[2]} "
                + formula[semicolon_index + 1 : end_index]
                + ")"
                + formula[end_index + 1 :]
            )

    # if we find a constant, remove C°[number]° with the number
    formula = re.sub(r"C°(\d+)°", r"\1", formula)
    return formula.strip()


def extract_names(expression: str) -> list[str]:
    """
    Extracts the names from an expression.

    :param expression: The expression to extract the names from
    :return The list of names extracted from the expression, avoiding pure numbers
    """
    # Pattern to find valid names: letters, numbers and underscore
    pattern = re.compile(r"\b[a-zA-Z_]\w*\b")  # we don't mach pure numbers
    names = pattern.findall(expression)

    # we exclude the 100 value
    filtered_names = [name for name in names if not name.isdigit()]
    return filtered_names


def prepare_for_real_time(kpi_name: str) -> (list[str], dict[str, str]):
    """
    Gets the references from the KB for a given KPI name. Then it cleans the formulas and transforms them in a parsable
    form for the numexpr library.

    :param kpi_name: The KPI name to get the references for
    :return The list of involved KPIs in the formula and the evaluable formula inside a dictionary
    """
    try:
        response = get_kpi_formula(kpi_name)
        if response is None:
            # get the reference from the KB with the other method
            response = get_closest_kpi_formula(kpi_name)
            response = response["formulas"]

        cleaned_formulas, operations = clean_placeholders(response)
        most_general_formula_key = next(iter(cleaned_formulas))
        formula = cleaned_formulas[most_general_formula_key]  # most general formula
        evaluable_formula = transform_formula(formula, cleaned_formulas, operations)
        involved_kpis = extract_names(evaluable_formula["formula"])

    except exceptions.KPIFormulaNotFoundException() as e:
        print(f"Error getting KPI database references: {e}")
        return [], None

    return involved_kpis, evaluable_formula


def transform_formula(
    formula: str, formulas: dict[str, str], operation_IWO: list[str]
) -> dict[str, str]:
    """
    Takes a formula and its sub formulas and transforms it in a parsable form for the numexpr library.

    :param formula: The formula to transform
    :param formulas: The formulas dictionary
    :param operation_IWO: The operations idle, working, offline
    :return The transformed formula in a dict in which 'formula' is the key
    """
    result = {}

    # substitution of the R° references with their formula in the formulas dict
    formula = re.sub(r"R°(\w+)", lambda match: f"{formulas[match.group(1)]}", formula)
    # remove the D° from the formula
    formula = re.sub(r"D°(\w+)", r"\1", formula)

    # remove the spaces
    formula = "".join(formula.split())
    result["formula"] = formula
    # save in the result the operations idle working offline, if present
    result["operations_f"] = operation_IWO
    # remove the inner aggregations after saving the outermost one
    result = remove_aggregations(result)

    # then if in the formula there are pairwise operation then transform in a parsable formula
    result["formula"] = to_evaluable(result["formula"])
    return result

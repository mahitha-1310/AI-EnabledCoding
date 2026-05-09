def _test_comp(json: dict):
    # Did `bear -- make` succeed?
    if not json.get("make_output", {}).get("success"):
        return False

    # Was an executable produced?
    if not json.get("executable_path"):
        return False

    # Success!
    return True

def _test_stan(json: dict):
    # Was static analysis considered successful across all analyzers?
    if not json["overall_success"]:
        return False

    # Did every file pass for every analyzer?
    for key, value in json.items():
        if key == "overall_success":
            continue
        for file_output in value["file_outputs"].values():
            if not file_output["success"]:
                return False

    # Success!
    return True

def _test_dyan(json: dict):
    # Was dynamic analysis considered successful in general?
    return json["overall_success"]

def _test_frmt(json: dict):
    # Was formatting considered successful in general?
    if not json["overall_success"]:
        return False

    # Did every c file compile?
    for file_output in json["results"]:
        if not file_output["success"]:
            return False

    # Success!
    return True

def _test_unit(json: dict):
    return json.get("passed", False)

def _res_fail(msg: str | None):
    if msg:
        print(msg)
    return False

def _res_warn(msg: str | None):
    if msg:
        print(msg)
    return True

ANALYSIS = {
    "compilation": {
        "function": _test_comp,
        "fail_case": _res_fail
    },
    "static_analysis": {
        "function": _test_stan,
        "fail_case": _res_fail
    },
    "dynamic_analysis": {
        "function": _test_dyan,
        "fail_case": _res_fail
    },
    "formatting": {
        "function": _test_frmt,
        "fail_case": _res_warn,
        "message": "[WARNING] Formatting does not meet standards. You may determine is the generated code is acceptable."
    },
    "unit_testing": {
        "function": _test_unit,
        "fail_case": _res_warn,
        "message": "[WARNING] One or more unit tests failed. Review the test results before accepting the generated code."
    }
}
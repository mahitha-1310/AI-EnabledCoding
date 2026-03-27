def _test_comp(json: dict):
    # Is there an executable path?
    if not json["executable_path"]:
        return False
    
    # Was linking successful?
    elif not json["link_output"]["success"]:
        return False
    
    # Did every c file compile?
    for file_output in json["file_outputs"].items():
        if not file_output["success"]:
            return False
    
    # Success!
    return True

def _test_stan(json: dict):
    # Was static analysis considered successful in general?
    if not json["overall_success"]:
        return False
    
    # Did every c file compile?
    for file_output in json["file_outputs"].items():
        if not file_output["success"]:
            return False
    
    # Success!
    return True

def _test_dyan(json: dict):
    # Was dynamic analysis considered successful in general?
    return json["success"]

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
    }
}
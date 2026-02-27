
def grade_comp(json: dict):
    try:
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
    
    except Exception as e:
        print(f"{type(e)}: {e.with_traceback()}")
    return False

def grade_stan(json: dict):
    try:
        # Was static analysis considered successful in general?
        if not json["overall_success"]:
            return False
        
        # Did every c file compile?
        for file_output in json["file_outputs"].items():
            if not file_output["success"]:
                return False
        
        # Success!
        return True
    
    except Exception as e:
        print(f"{type(e)}: {e.with_traceback()}")
    return False

def grade_dyan(json: dict):
    try:
        # Was dynamic analysis considered successful in general?
        return json["success"]
    except Exception as e:
        print(f"{type(e)}: {e.with_traceback()}")
    return False

def grade_frmt(json: dict):
    try:
        # Was formatting considered successful in general?
        if not json["overall_success"]:
            return False
        
        # Did every c file compile?
        for file_output in json["results"]:
            if not file_output["success"]:
                return False
        
        # Success!
        return True
    
    except Exception as e:
        print(f"{type(e)}: {e.with_traceback()}")
    return False

ANALYSIS_MAP = {
    "compilation": grade_comp,
    "static_analysis": grade_stan,
    "dynamic_analysis": grade_dyan,
    "formatting": grade_frmt
}
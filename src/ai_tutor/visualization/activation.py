def activation_series(result):
    history=result.debug_info.get("activation_history",[])
    return [{"iteration":i,"concept":c,"activation":v} for i,row in enumerate(history) for c,v in row.items() if v>0]


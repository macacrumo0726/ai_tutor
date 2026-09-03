def normalize_metadata(value:dict)->dict:
    return {str(k):v for k,v in value.items() if v is not None}

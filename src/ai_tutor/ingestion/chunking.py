def chunk_words(text:str,size:int=350,overlap:int=50):
    words=text.split(); step=max(1,size-overlap)
    return [" ".join(words[i:i+size]) for i in range(0,len(words),step) if words[i:i+size]]


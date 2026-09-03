from ai_tutor.embeddings.encoder import HashingEncoder
from ai_tutor.indexing.faiss_index import DenseIndex
from ai_tutor.indexing.bm25_index import BM25Index

def test_dense_and_sparse_indexes_return_ids():
    texts=["función racional dominio","ecuación cuadrática"] ; enc=HashingEncoder(32)
    assert DenseIndex(enc.encode(texts),["a","b"]).search(enc.encode([texts[0]])[0],1)[0][0]=="a"
    assert BM25Index(texts,["a","b"]).search("cuadrática",1)[0][0]=="b"


from vector_store import get_collection

col = get_collection()

col.delete(where={})

print("Collection cleared")
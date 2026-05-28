from app.constants.paths import PROJECT_ROOT


CHROMA_DIR = PROJECT_ROOT / "data" / "chroma" / "virtual_twin"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "virtual_twin_documents"
HF_TOKEN_ENV = "HF_TOKEN"
EMBEDDING_DEVICE = "cpu"
NORMALIZE_EMBEDDINGS = True

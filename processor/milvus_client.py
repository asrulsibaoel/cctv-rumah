from datetime import datetime
from typing import Tuple, Optional, List
import numpy as np
from pymilvus import \
    CollectionSchema, DataType, FieldSchema, MilvusClient
from pymilvus.milvus_client.index import IndexParams
from settings import MILVUS_URI, MILVUS_TOKEN, MILVUS_COLLECTION

client = MilvusClient(uri=MILVUS_URI, token=MILVUS_TOKEN)

if not client.has_collection(collection_name=MILVUS_COLLECTION):
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR,
                    is_primary=True, auto_id=False, max_length=64),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=512),
        FieldSchema(name="timestamp", dtype=DataType.VARCHAR,
                    max_length=32),  # ✅ Add this
    ]
    # Create schema (✅ correct way)
    schema = CollectionSchema(fields=fields, description="Embedding storage")
    # Create collection
    # collection = Collection(name=MILVUS_COLLECTION, schema=schema)
    client.create_collection(
        collection_name=MILVUS_COLLECTION,
        dimension=512,
        index_type="AUTOINDEX",
        metric_type="COSINE",
        schema=schema,
        consistency_level="Strong"
    )
    index_params = IndexParams()
    index_params.add_index(field_name="embedding",
                           index_type="AUTOINDEX", metric_type="COSINE",
                           params={"nlist": 128})
    client.create_index(
        collection_name=MILVUS_COLLECTION,
        index_params=index_params
    )
client.load_collection(collection_name=MILVUS_COLLECTION)


def is_new_person(embedding: List[float], threshold=0.9) -> Tuple[bool, Optional[str]]:
    try:
        # Ensure compatibility with Milvus schema
        embedding = [float(x) for x in embedding]
        results = client.search(
            collection_name=MILVUS_COLLECTION,
            data=[embedding],
            anns_field="embedding",
            limit=1,
            output_fields=["id"],
            search_params={"metric_type": "COSINE", "params": {"nprobe": 10}}
        )
        if not results or not results[0]:
            return True, None
        top = results[0][0]
        print(f"Distance: {top['distance']}")

        return (top["distance"] >= threshold), top["id"]
    except Exception as e:
        print(f"[ERROR] Milvus search failed: {e}")
        return True, None


def store_embedding(embedding: List[float], person_id: str):
    person_id = str(person_id)

    # Convert embedding to list if it's a NumPy array
    if isinstance(embedding, np.ndarray):
        embedding = embedding.tolist()

    # ✅ Strong validation
    if not isinstance(person_id, str):
        raise ValueError("person_id must be a string")

    if not isinstance(embedding, list):
        raise ValueError("embedding must be a list")

    if len(embedding) != 512:
        raise ValueError(
            f"embedding must be 512-dimensional, got {len(embedding)}")

    if not all(isinstance(x, float) for x in embedding):
        raise ValueError("all elements in embedding must be float")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = [
        {
            "id": person_id,
            "embedding": embedding,
            "timestamp": timestamp,
        }
    ]

    try:
        print("[DEBUG] Data being inserted:")
        print("  ID:", person_id)
        print("  Embedding shape:", (len(embedding),))
        print("  Timestamp:", timestamp)

        # 🚀 Insert to Milvus
        client.insert(collection_name=MILVUS_COLLECTION, data=data)
        client.flush(MILVUS_COLLECTION)
        print(f"[INFO] Inserted {person_id} into Milvus.")

    except Exception as e:
        print(f"[ERROR] Failed to insert to Milvus: {type(e).__name__}: {e}")

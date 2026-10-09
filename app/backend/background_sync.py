import threading
import time
import hashlib
from pathlib import Path
from app.backend.db import get_connection

def hash_file(path: Path) -> str:
    hasher = hashlib.blake2b()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
    except OSError:
        return ""
    return hasher.hexdigest()

def background_hashing_worker():
    while True:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Find documents that need hashing
            cursor.execute("""
                SELECT d.id, d.rel_path, r.path as root_path
                FROM documents d
                JOIN roots r ON d.root_id = r.id
                WHERE d.content_hash IS NULL
                LIMIT 50
            """)
            docs = cursor.fetchall()
            
            for doc in docs:
                doc_id = doc["id"]
                full_path = Path(doc["root_path"]) / doc["rel_path"]
                
                new_hash = hash_file(full_path)
                
                # Check if we had a previous hash for this path before to see if it actually changed
                # (Since we set content_hash = NULL on update, we lost the old hash, but we can assume
                # if we are hashing it now, any old artifacts tied to the old file state might be invalid)
                # For now, let's just clear artifacts associated with this document if it was updated.
                # Actually, clearing artifacts on update is safer.
                cursor.execute("DELETE FROM artifacts WHERE document_id = ?", (doc_id,))
                
                # Save the new hash
                cursor.execute("UPDATE documents SET content_hash = ? WHERE id = ?", (new_hash, doc_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Background hashing error: {e}")
            
        # Sleep before next batch
        time.sleep(5)

def start_background_sync():
    thread = threading.Thread(target=background_hashing_worker, daemon=True)
    thread.start()

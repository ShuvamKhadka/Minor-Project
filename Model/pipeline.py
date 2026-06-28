import io
import re
import os
import numpy as np # type: ignore
import PyPDF2 # type: ignore
import docx as python_docx # type: ignore
from sentence_transformers import SentenceTransformer # type: ignore
from sklearn.neighbors import NearestNeighbors # type: ignore

# 1. INITIALIZE FINE-TUNED MODEL

MODEL_PATH = "/Users/prabinrimal/Desktop/THIS is FINAL ig/FINAL COMPLETE/resume_ranking/model/recruit_finetuned_minilm"

print(f"Loading local fine-tuned model from: {MODEL_PATH}...")
model = SentenceTransformer(MODEL_PATH, trust_remote_code=True)
PHI = 0.15

# 2. TEXT EXTRACTION ENGINE

def extract_text_from_bytes(data: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    try:
        if ext == "pdf":
            r = PyPDF2.PdfReader(io.BytesIO(data))
            return "\n".join(p.extract_text() or "" for p in r.pages).strip()
        elif ext == "docx":
            return "\n".join(p.text for p in python_docx.Document(io.BytesIO(data)).paragraphs).strip()
        elif ext == "txt":
            for enc in ("utf-8", "latin-1"):
                try: return data.decode(enc).strip()
                except: pass
    except Exception as e:
        print(f"[WARN] Extraction failed for {filename}: {e}")
    return ""

# 3. ADVANCED TEXT PREPROCESSING & PARSING

def clean_whitespace(text: str) -> str:
    if not text: return ""
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def standard_normalize(text: str) -> str:
    if not text: return ""
    text = text.replace('\xa0', ' ').replace('\x00', '')
    bullet_artifacts = ['•', '▪', '■', '◦', '○', '♦', '▶', '', '✅']
    for bullet in bullet_artifacts:
        text = text.replace(bullet, ' ')
    return text.lower()

def clean_text(text: str) -> str:
    return clean_whitespace(standard_normalize(text))

def extract_email(text: str) -> str:
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return email_match.group(0) if email_match else "Not Provided"

# 4. SLIDING WINDOW CHUNKING ENGINE 

def chunk_text(text: str, max_words: int = 150, overlap: int = 30) -> list:
    words = text.split()
    chunks = []
    if not words: return chunks
    for i in range(0, len(words), max_words - overlap):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
        if i + max_words >= len(words): break
    return chunks

def get_document_embedding(text: str) -> np.ndarray:
    chunks = chunk_text(text)
    if not chunks:
        return np.zeros(model.get_sentence_embedding_dimension(), dtype=np.float32)
    chunk_embeddings = model.encode(chunks, normalize_embeddings=False)
    doc_embedding = np.mean(chunk_embeddings, axis=0)
    return doc_embedding.astype(np.float32)


# 5. PURE SEMANTIC KNN RANKING ENGINE

def process_and_rank(jd_data: dict, resumes_list: list, top_k: int = 5) -> list:
    jd_raw = jd_data.get('text', '')
    jd_clean = clean_text(jd_raw)
    
    if not resumes_list or not jd_clean:
        return []
        
    parsed_resumes = []
    resume_vectors = []
    
    for res in resumes_list:
        raw_text = extract_text_from_bytes(res['bytes'], res['filename'])
        cleaned = clean_text(raw_text)
        
        if cleaned:
            doc_vector = get_document_embedding(cleaned)
            resume_vectors.append(doc_vector)
            
            email = extract_email(raw_text)
            name = os.path.splitext(res['filename'])[0].replace('_', ' ').title()
            preview_snippet = raw_text[:400] + "..." if len(raw_text) > 400 else raw_text
            
            parsed_resumes.append({
                "filename": res['filename'],
                "name": name,
                "email": email,
                "clean_text": cleaned,
                "preview": preview_snippet
            })
            
    if not resume_vectors:
        return []
        
    resume_vectors = np.array(resume_vectors, dtype=np.float32)
    jd_vector = get_document_embedding(jd_clean).reshape(1, -1)
    
    k_neighbors = min(top_k, len(parsed_resumes))
    knn = NearestNeighbors(n_neighbors=k_neighbors, metric='cosine')
    knn.fit(resume_vectors)
    
    distances, indices = knn.kneighbors(jd_vector)
    
    final_rankings = []
    for order, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        matched_resume = parsed_resumes[idx]
        
        # Convert the cosine distance directly into the final percentage score
        semantic_score = max(0.0, min(100.0, (1.0 - float(dist)) * 100))
        overall_score = round(semantic_score, 1)
        
        if overall_score >= 75: label = "Excellent"
        elif overall_score >= 55: label = "Good"
        elif overall_score >= 35: label = "Potential"
        else: label = "Low"
            
        final_rankings.append({
            "rank": order + 1,
            "name": matched_resume["name"],
            "email": matched_resume["email"],
            "filename": matched_resume["filename"],
            "score": overall_score,
            "label": label,
            "preview": matched_resume["preview"]
        })
        
    return final_rankings
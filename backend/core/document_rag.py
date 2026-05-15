"""
AIRIS Document RAG System
Self-learning knowledge base from uploaded documents
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from datetime import datetime
import json
import os
import hashlib
import PyPDF2
from docx import Document as DocxDocument

class DocumentRAG:
    """
    Document learning system for AIRIS
    Stores and retrieves knowledge from uploaded documents
    """
    
    def __init__(self, persist_directory="./data/documents"):
        """Initialize document RAG system"""
        print("📚 Initializing Document RAG System...")
        
        os.makedirs(persist_directory, exist_ok=True)
        os.makedirs("./data/weekly_learnings", exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Load embedding model (same as vector memory)
        print("📦 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Embedding model loaded")
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name="airis_documents")
            print(f"✓ Loaded document collection ({self.collection.count()} chunks)")
        except:
            self.collection = self.client.create_collection(
                name="airis_documents",
                metadata={"description": "AIRIS document knowledge base"}
            )
            print("✓ Created new document collection")
        
        print("📚 Document RAG ready!\n")
    
    def _generate_embedding(self, text):
        """Generate embedding for text"""
        return self.embedding_model.encode(text).tolist()
    
    def _extract_text_from_pdf(self, file_path):
        """Extract text from PDF"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    text += f"\n[Page {page_num + 1}]\n{page_text}"
                return text
        except Exception as e:
            print(f"❌ PDF extraction error: {e}")
            return None
    
    def _extract_text_from_docx(self, file_path):
        """Extract text from DOCX"""
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            print(f"❌ DOCX extraction error: {e}")
            return None
    
    def _extract_text_from_txt(self, file_path):
        """Extract text from TXT/MD"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"❌ TXT extraction error: {e}")
            return None
    
    def _chunk_text(self, text, chunk_size=500, overlap=50):
        """
        Split text into overlapping chunks for better context
        
        Args:
            text: Full document text
            chunk_size: Characters per chunk
            overlap: Characters to overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > chunk_size * 0.5:  # At least 50% through
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - overlap
        
        return chunks
    
    def ingest_document(self, file_path, filename, doc_type="unknown"):
        """
        Ingest a document into the knowledge base
        
        Args:
            file_path: Path to the document
            filename: Original filename
            doc_type: Type of document (proposal, report, etc.)
            
        Returns:
            Dict with ingestion results
        """
        print(f"📄 Ingesting: {filename}")
        
        # Extract text based on file type
        ext = filename.lower().split('.')[-1]
        
        if ext == 'pdf':
            text = self._extract_text_from_pdf(file_path)
        elif ext == 'docx':
            text = self._extract_text_from_docx(file_path)
        elif ext in ['txt', 'md']:
            text = self._extract_text_from_txt(file_path)
        else:
            return {"error": f"Unsupported file type: {ext}"}
        
        if not text:
            return {"error": "Failed to extract text"}
        
        print(f"✓ Extracted {len(text)} characters")
        
        # Chunk the text
        chunks = self._chunk_text(text)
        print(f"✓ Created {len(chunks)} chunks")
        
        # Generate embeddings and store
        timestamp = datetime.now().isoformat()
        doc_id = hashlib.md5(f"{filename}_{timestamp}".encode()).hexdigest()
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            embedding = self._generate_embedding(chunk)
            
            metadata = {
                "filename": filename,
                "doc_id": doc_id,
                "doc_type": doc_type,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "timestamp": timestamp,
                "char_count": len(chunk)
            }
            
            self.collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[metadata]
            )
        
        print(f"💾 Stored {len(chunks)} chunks for {filename}")
        
        return {
            "status": "ok",
            "filename": filename,
            "chunks_created": len(chunks),
            "doc_id": doc_id,
            "char_count": len(text)
        }
    
    def search_documents(self, query, n_results=5, doc_type_filter=None):
        """
        Search for relevant document chunks
        
        Args:
            query: Search query
            n_results: Number of results
            doc_type_filter: Filter by document type
            
        Returns:
            List of relevant chunks with citations
        """
        query_embedding = self._generate_embedding(query)
        
        where_filter = None
        if doc_type_filter:
            where_filter = {"doc_type": doc_type_filter}
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter
        )
        
        chunks = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                chunks.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        print(f"🔍 Found {len(chunks)} relevant chunks")
        return chunks
    
    def get_context_for_query(self, query, max_chunks=5):
        """
        Get relevant context from documents for a query
        
        Args:
            query: User query
            max_chunks: Max chunks to retrieve
            
        Returns:
            Formatted context string with citations
        """
        chunks = self.search_documents(query, n_results=max_chunks)
        
        if not chunks:
            return ""
        
        context_parts = []
        seen_docs = set()
        
        for chunk in chunks:
            filename = chunk['metadata']['filename']
            chunk_idx = chunk['metadata']['chunk_index']
            text = chunk['text']
            
            # Add document header if first time seeing this doc
            if filename not in seen_docs:
                context_parts.append(f"\n=== From: {filename} ===")
                seen_docs.add(filename)
            
            context_parts.append(f"[Chunk {chunk_idx}] {text[:500]}...")
        
        return "\n\n".join(context_parts)
    
    def get_all_documents(self):
        """Get list of all ingested documents"""
        all_data = self.collection.get()
        
        if not all_data['metadatas']:
            return []
        
        # Group by doc_id
        docs = {}
        for meta in all_data['metadatas']:
            doc_id = meta['doc_id']
            if doc_id not in docs:
                docs[doc_id] = {
                    'filename': meta['filename'],
                    'doc_id': doc_id,
                    'doc_type': meta.get('doc_type', 'unknown'),
                    'timestamp': meta['timestamp'],
                    'chunk_count': meta['total_chunks']
                }
        
        return list(docs.values())
    
    def delete_document(self, doc_id):
        """Delete a document and all its chunks"""
        # Get all chunk IDs for this document
        all_data = self.collection.get()
        chunk_ids = [
            all_data['ids'][i] 
            for i, meta in enumerate(all_data['metadatas']) 
            if meta['doc_id'] == doc_id
        ]
        
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)
            print(f"🗑️ Deleted {len(chunk_ids)} chunks for doc {doc_id}")
            return True
        return False
    
    def generate_weekly_learning_report(self):
        """
        Generate weekly learning insights (runs every Friday)
        
        Returns:
            Learning report dict
        """
        print("🧠 Generating weekly learning report...")
        
        # Get all documents
        docs = self.get_all_documents()
        
        # Get this week's documents
        from datetime import timedelta
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        this_week_docs = [
            doc for doc in docs 
            if doc['timestamp'] >= week_ago
        ]
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_documents": len(docs),
            "new_this_week": len(this_week_docs),
            "documents_this_week": [d['filename'] for d in this_week_docs],
            "total_knowledge_chunks": self.collection.count(),
            "insights": []
        }
        
        # Save report
        report_file = f"./data/weekly_learnings/{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Weekly report saved: {report_file}")
        return report
    
    def get_stats(self):
        """Get document knowledge base statistics"""
        docs = self.get_all_documents()
        
        return {
            "total_documents": len(docs),
            "total_chunks": self.collection.count(),
            "documents": docs
        }
    
    def health_check(self):
        """Check if document RAG is working"""
        try:
            count = self.collection.count()
            docs = len(self.get_all_documents())
            return True, f"✓ Document RAG ready ({docs} documents, {count} chunks)"
        except Exception as e:
            return False, f"✗ Document RAG error: {str(e)}"
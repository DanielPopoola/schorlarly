from abc import ABC, abstractmethod
from google.genai import types

class EmbeddingProvider(ABC):
    
    @abstractmethod
    def encode(self, text: str) -> list[float]:
        pass
    
    @abstractmethod
    def dimension(self) -> int:
        pass


class OpenAIEmbeddings(EmbeddingProvider):
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def encode(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def dimension(self) -> int:
        return 1536


class SentenceTransformerEmbeddings(EmbeddingProvider): 
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer # type: ignore
        self.model = SentenceTransformer(model_name)
    
    def encode(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()
    
    def dimension(self) -> int:
        return 384


class HuggingFaceEmbeddings(EmbeddingProvider):
    
    def __init__(self, api_token: str, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.api_token = api_token
        self.model = model
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"
    
    def encode(self, text: str) -> list[float]:
        import requests
        headers = {"Authorization": f"Bearer {self.api_token}"}
        response = requests.post(self.api_url, headers=headers, json={"inputs": text})
        return response.json()
    
    def dimension(self) -> int:
        return 384

class GeminiEmbeddings(EmbeddingProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001"):
        from google import genai
       
        self.model_name=model_name
        self.client = genai.Client(api_key=api_key)

    def encode(self, text: str) -> list[float]:
        result = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )

        if result.embeddings:
            [embedding_obj] = result.embeddings
            if embedding_obj.values:
                return embedding_obj.values
            
        return [0.0]
    
    def dimension(self) -> int:
        return 768
from pathlib import Path
from fastapi import APIRouter, Depends

from app.intelligence.service import SafetyIntelligenceService, provider_from_environment
from app.rag.retriever import Retriever
from app.rag.vector_store import JsonVectorStore
from app.rag.embedder import DeterministicEmbedder
from app.schemas import RiskEngineInput, SafetyIntelligenceResponse

router = APIRouter(
    prefix="/intelligence",
    tags=["Safety Intelligence"]
)

ROOT = Path(__file__).resolve().parents[3]
STORE_PATH = ROOT / "backend/data/knowledge/vector_store/chunks.json"

def get_intelligence_service() -> SafetyIntelligenceService:
    store = JsonVectorStore(STORE_PATH)
    embedder = DeterministicEmbedder()
    retriever = Retriever(store, embedder)
    provider = provider_from_environment()
    return SafetyIntelligenceService(retriever, provider)

@router.post("/generate", response_model=SafetyIntelligenceResponse)
def generate_intelligence(
    risk: RiskEngineInput,
    service: SafetyIntelligenceService = Depends(get_intelligence_service)
) -> SafetyIntelligenceResponse:
    """
    Generate an advisory safety intelligence response for a given risk engine input.
    """
    return service.generate(risk)

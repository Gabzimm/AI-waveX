from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import logging
from datetime import datetime
import uvicorn
from typing import Optional, Dict, List
import asyncio

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa o app FastAPI
app = FastAPI(
    title="Minha API de IA",
    description="API personalizada para interagir com modelos de linguagem",
    version="1.0.0"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class ChatRequest(BaseModel):
    mensagem: str
    session_id: Optional[str] = None
    temperatura: Optional[float] = 0.7
    max_tokens: Optional[int] = 500

class ChatResponse(BaseModel):
    resposta: str
    session_id: str
    tokens_used: Optional[int] = None
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    python_version: str

# Configuração da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY não configurada")
else:
    openai.api_key = OPENAI_API_KEY

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))

# Histórico de conversas (em produção, use Redis)
conversas: Dict[str, List[Dict]] = {}

@app.get("/", response_model=dict)
async def root():
    """Endpoint raiz"""
    return {
        "message": "🚀 API de IA funcionando!",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check detalhado"""
    import sys
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("RENDER_SERVICE_NAME", "local"),
        python_version=sys.version
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para conversar com a IA
    
    - **mensagem**: Sua pergunta para a IA
    - **session_id**: ID para manter contexto (opcional)
    - **temperatura**: Criatividade (0.0 a 1.0, padrão 0.7)
    - **max_tokens**: Máximo de tokens na resposta
    """
    try:
        # Validação da API key
        if not OPENAI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="API key não configurada. Configure OPENAI_API_KEY no ambiente."
            )
        
        # Validação da mensagem
        if not request.mensagem or len(request.mensagem.strip()) == 0:
            raise HTTPException(
                status_code=400,
                detail="Mensagem não pode estar vazia"
            )
        
        # Gerencia session_id
        session_id = request.session_id or f"session_{int(datetime.utcnow().timestamp())}"
        
        # Inicializa histórico se necessário
        if session_id not in conversas:
            conversas[session_id] = [
                {"role": "system", "content": "Você é um assistente útil, amigável e conciso."}
            ]
        
        # Adiciona mensagem do usuário
        conversas[session_id].append({"role": "user", "content": request.mensagem})
        
        logger.info(f"Processando requisição - Session: {session_id}")
        
        # Chama OpenAI com timeout
        try:
            response = await asyncio.wait_for(
                openai.ChatCompletion.acreate(
                    model=MODEL_NAME,
                    messages=conversas[session_id][-MAX_HISTORY:],
                    temperature=max(0.0, min(1.0, request.temperatura)),
                    max_tokens=min(500, request.max_tokens)
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Timeout na chamada da OpenAI")
        
        # Processa resposta
        resposta_ia = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Adiciona resposta ao histórico
        conversas[session_id].append({"role": "assistant", "content": resposta_ia})
        
        # Limita tamanho do histórico
        if len(conversas[session_id]) > MAX_HISTORY:
            # Mantém a mensagem do sistema + últimas N-1
            conversas[session_id] = (
                [conversas[session_id][0]] + 
                conversas[session_id][-(MAX_HISTORY-1):]
            )
        
        logger.info(f"Resposta gerada - Tokens: {tokens_used}")
        
        return ChatResponse(
            resposta=resposta_ia,
            session_id=session_id,
            tokens_used=tokens_used,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except openai.error.RateLimitError:
        logger.error("Rate limit excedido")
        raise HTTPException(status_code=429, detail="Limite de requisições excedido")
    
    except openai.error.AuthenticationError:
        logger.error("Erro de autenticação")
        raise HTTPException(status_code=401, detail="Erro de autenticação na OpenAI")
    
    except openai.error.APIError as e:
        logger.error(f"Erro na API OpenAI: {str(e)}")
        raise HTTPException(status_code=502, detail="Erro no serviço da OpenAI")
    
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.delete("/conversa/{session_id}")
async def limpar_conversa(session_id: str):
    """Limpa histórico de uma conversa"""
    if session_id in conversas:
        del conversas[session_id]
        return {"message": f"✅ Conversa {session_id} removida"}
    return {"message": f"❌ Conversa {session_id} não encontrada"}

@app.get("/conversas")
async def listar_conversas():
    """Lista todas as conversas ativas"""
    return {
        "total": len(conversas),
        "sessions": list(conversas.keys())
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )

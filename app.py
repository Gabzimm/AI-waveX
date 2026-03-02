from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import logging
from datetime import datetime
import uvicorn
from typing import Optional, List

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializa o app FastAPI
app = FastAPI(
    title="Minha API de IA",
    description="API personalizada para interagir com modelos de linguagem",
    version="1.0.0"
)

# Configura CORS para permitir requisições de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para validação de dados
class ChatRequest(BaseModel):
    mensagem: str
    session_id: Optional[str] = None
    temperatura: Optional[float] = 0.7

class ChatResponse(BaseModel):
    resposta: str
    session_id: str
    tokens_used: Optional[int] = None
    timestamp: str

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str

# Configuração da OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY não configurada. A API não funcionará corretamente.")
else:
    openai.api_key = OPENAI_API_KEY

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

# Dicionário simples para armazenar histórico de conversas (em produção, use Redis/PostgreSQL)
conversas = {}

@app.get("/")
async def root():
    """Endpoint raiz para verificar se a API está funcionando"""
    return {
        "message": "Bem-vindo à sua API de IA!",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Endpoint de health check para o Render"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        environment=os.getenv("RENDER_SERVICE_NAME", "local")
    )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para conversar com a IA
    
    - **mensagem**: Sua pergunta ou comando para a IA
    - **session_id**: ID para manter contexto da conversa (opcional)
    - **temperatura**: Controle de criatividade (0.0 a 1.0)
    """
    try:
        # Verifica se a API key está configurada
        if not OPENAI_API_KEY:
            raise HTTPException(
                status_code=500, 
                detail="API key não configurada. Configure OPENAI_API_KEY no Render."
            )
        
        # Usa ou cria um session_id
        session_id = request.session_id or f"session_{datetime.utcnow().timestamp()}"
        
        # Recupera histórico da conversa ou cria novo
        if session_id not in conversas:
            conversas[session_id] = [
                {"role": "system", "content": "Você é um assistente útil e amigável."}
            ]
        
        # Adiciona a mensagem do usuário ao histórico
        conversas[session_id].append({"role": "user", "content": request.mensagem})
        
        # Chama a API da OpenAI
        logger.info(f"Processando requisição para session_id: {session_id}")
        
        response = openai.ChatCompletion.create(
            model=MODEL_NAME,
            messages=conversas[session_id][-10:],  # Mantém apenas últimas 10 mensagens
            temperature=request.temperatura,
            max_tokens=500
        )
        
        # Extrai a resposta
        resposta_ia = response.choices[0].message.content
        tokens_used = response.usage.total_tokens
        
        # Adiciona a resposta ao histórico
        conversas[session_id].append({"role": "assistant", "content": resposta_ia})
        
        # Limita o tamanho do histórico para não crescer infinitamente
        if len(conversas[session_id]) > 20:
            conversas[session_id] = conversas[session_id][-20:]
        
        logger.info(f"Resposta gerada com sucesso. Tokens: {tokens_used}")
        
        return ChatResponse(
            resposta=resposta_ia,
            session_id=session_id,
            tokens_used=tokens_used,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except openai.error.RateLimitError:
        logger.error("Rate limit excedido")
        raise HTTPException(status_code=429, detail="Limite de requisições excedido. Tente novamente mais tarde.")
    
    except openai.error.AuthenticationError:
        logger.error("Erro de autenticação na OpenAI")
        raise HTTPException(status_code=401, detail="Erro de autenticação. Verifique sua API key.")
    
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.delete("/conversa/{session_id}")
async def limpar_conversa(session_id: str):
    """Limpa o histórico de uma conversa específica"""
    if session_id in conversas:
        del conversas[session_id]
        return {"message": f"Conversa {session_id} removida com sucesso"}
    return {"message": f"Conversa {session_id} não encontrada"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

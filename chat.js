// chat.js - Integração com a API AI WaveX

// Configuração - COLOQUE SUA URL DO RENDER AQUI
const API_URL = 'https://api-ai-3v4b.onrender.com'; // Mude para sua URL real
let sessionId = localStorage.getItem('wavex_session') || 'wavex_' + Date.now();
let conversationHistory = [];

// Salva sessionId
localStorage.setItem('wavex_session', sessionId);

// Elementos do DOM
const messagesContainer = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const typingIndicator = document.getElementById('typing-indicator');
const clearButton = document.getElementById('clear-chat');
const tokenCount = document.getElementById('token-count');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    loadConversation();
    updateTokenCount(0);
    
    // Foca no input
    userInput.focus();
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    if (clearButton) {
        clearButton.addEventListener('click', clearConversation);
    }
});

// Carrega conversa do localStorage
function loadConversation() {
    const saved = localStorage.getItem(`wavex_${sessionId}`);
    if (saved) {
        conversationHistory = JSON.parse(saved);
        conversationHistory.forEach(msg => {
            addMessageToUI(msg.text, msg.type, false);
        });
    }
}

// Salva conversa no localStorage
function saveConversation() {
    localStorage.setItem(`wavex_${sessionId}`, JSON.stringify(conversationHistory));
}

// Envia mensagem para a IA
async function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Limpa input
    userInput.value = '';
    
    // Adiciona mensagem do usuário ao chat
    addMessageToUI(message, 'user');
    
    // Mostra indicador de digitação
    showTypingIndicator(true);
    
    // Desabilita input
    toggleInput(false);
    
    try {
        // Verifica se API_URL foi configurada
        if (API_URL === 'https://seu-app-name.onrender.com') {
            throw new Error('Configure a URL da API no arquivo chat.js');
        }
        
        // Envia requisição para sua API
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                mensagem: message,
                session_id: sessionId,
                temperatura: 0.7
            })
        });
        
        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`Erro ${response.status}: ${errorData}`);
        }
        
        const data = await response.json();
        
        // Esconde indicador de digitação
        showTypingIndicator(false);
        
        // Adiciona resposta da IA ao chat
        addMessageToUI(data.resposta, 'ai');
        
        // Atualiza contador de tokens
        if (data.tokens_used) {
            updateTokenCount(data.tokens_used);
        }
        
    } catch (error) {
        console.error('Erro:', error);
        
        // Esconde indicador de digitação
        showTypingIndicator(false);
        
        // Mostra mensagem de erro
        let errorMessage = '❌ Erro ao conectar com a IA. ';
        
        if (error.message.includes('Configure a URL')) {
            errorMessage += 'Por favor, configure a URL da API no arquivo chat.js';
        } else if (error.message.includes('Failed to fetch')) {
            errorMessage += 'Não foi possível conectar ao servidor. Verifique se a API está no ar.';
        } else {
            errorMessage += error.message;
        }
        
        addMessageToUI(errorMessage, 'error');
        
    } finally {
        // Reabilita input
        toggleInput(true);
        userInput.focus();
    }
}

// Adiciona mensagem à interface
function addMessageToUI(text, type, save = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    if (type === 'ai') {
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        avatar.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    } else if (type === 'user') {
        avatar.innerHTML = '<i class="fas fa-user"></i>';
        avatar.style.background = '#00b894';
    } else {
        avatar.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        avatar.style.background = '#e17055';
    }
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    
    // Formata o texto (suporta markdown básico)
    const formattedText = formatMessage(text);
    bubble.innerHTML = formattedText;
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = new Date().toLocaleTimeString();
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(bubble);
    messageDiv.appendChild(time);
    
    messagesContainer.appendChild(messageDiv);
    
    // Scroll para o final
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Salva no histórico se necessário
    if (save && type !== 'error') {
        conversationHistory.push({ text, type, timestamp: Date.now() });
        saveConversation();
    }
}

// Formata a mensagem (links, negrito, etc)
function formatMessage(text) {
    if (!text) return '';
    
    // Escapa HTML
    text = text.replace(/&/g, '&amp;')
               .replace(/</g, '&lt;')
               .replace(/>/g, '&gt;')
               .replace(/"/g, '&quot;')
               .replace(/'/g, '&#039;');
    
    // Links
    text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Negrito (markdown)
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Itálico
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Código inline
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Quebras de linha
    text = text.replace(/\n/g, '<br>');
    
    return text;
}

// Mostra/Esconde indicador de digitação
function showTypingIndicator(show) {
    if (!typingIndicator) return;
    
    if (show) {
        typingIndicator.style.display = 'flex';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } else {
        typingIndicator.style.display = 'none';
    }
}

// Habilita/Desabilita input
function toggleInput(enabled) {
    userInput.disabled = !enabled;
    sendButton.disabled = !enabled;
    
    if (enabled) {
        sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
        sendButton.style.opacity = '1';
    } else {
        sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        sendButton.style.opacity = '0.7';
    }
}

// Limpa conversa atual
function clearConversation() {
    if (confirm('Tem certeza que deseja limpar todo o histórico da conversa?')) {
        conversationHistory = [];
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <i class="fas fa-robot"></i>
                <h3>Bem-vindo à AI WaveX!</h3>
                <p>Comece a conversar digitando sua mensagem abaixo.</p>
            </div>
        `;
        localStorage.removeItem(`wavex_${sessionId}`);
        updateTokenCount(0);
    }
}

// Atualiza contador de tokens
function updateTokenCount(tokens) {
    if (tokenCount) {
        tokenCount.textContent = `Tokens usados: ${tokens}`;
    }
}

// Exporta conversa
function exportConversation() {
    const conversation = conversationHistory.map(msg => {
        const prefix = msg.type === 'user' ? '👤 Você' : '🤖 WaveX';
        return `${prefix}: ${msg.text}`;
    }).join('\n\n');
    
    const blob = new Blob([conversation], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `wavex-conversa-${new Date().toISOString().slice(0,10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// Função para testar conexão com a API
async function testConnection() {
    try {
        const response = await fetch(`${API_URL}/health`);
        if (response.ok) {
            const data = await response.json();
            console.log('✅ API conectada:', data);
            return true;
        }
    } catch (error) {
        console.error('❌ Erro de conexão:', error);
        return false;
    }
}

// Testa conexão ao carregar
testConnection().then(connected => {
    if (!connected && API_URL !== 'https://seu-app-name.onrender.com') {
        addMessageToUI('⚠️ Não foi possível conectar à API. Verifique se o servidor está rodando.', 'error');
    }
});

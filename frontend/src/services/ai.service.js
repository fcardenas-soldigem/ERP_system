import { api } from '../lib/api';

class AIService {
    async createThread() {
        console.log('🔧 aiService.createThread llamado');
        const response = await api.post('/api/ai/threads/');
        console.log('🔧 createThread response:', response.data);
        return response.data;
    }

    async sendMessage(threadId, content) {
        console.log('🔧 aiService.sendMessage llamado', { threadId, content });
        const response = await api.post(`/api/ai/threads/${threadId}/messages/`, {
            content
        });
        console.log('🔧 sendMessage response:', response.data);
        return response.data;
    }

    async getMessages(threadId) {
        const response = await api.get(`/api/ai/threads/${threadId}/messages/`);
        return response.data;
    }

    async createThreadWithTools() {
        console.log('🛠️ aiService.createThreadWithTools llamado');
        const response = await api.post('/api/ai/threads-tools/');
        console.log('🛠️ createThreadWithTools response:', response.data);
        return response.data;
    }

    async sendMessageWithTools(threadId, content) {
        console.log('🛠️ aiService.sendMessageWithTools llamado', { threadId, content });
        const response = await api.post(`/api/ai/threads-tools/${threadId}/messages/`, {
            content
        });
        console.log('🛠️ sendMessageWithTools response:', response.data);
        return response.data;
    }

    async getMessagesWithTools(threadId) {
        console.log('🛠️ aiService.getMessagesWithTools llamado:', threadId);
        const response = await api.get(`/api/ai/threads-tools/${threadId}/messages/`);
        console.log('🛠️ getMessagesWithTools response:', response.data);
        return response.data;
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await api.post('/api/ai/files/upload/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    }

    async getConversations() {
        console.log('🔧 aiService.getConversations llamado');
        const response = await api.get('/api/ai/conversations/');
        console.log('🔧 getConversations response:', response.data);
        return response.data;
    }

    async createConversation() {
        const response = await api.post('/api/ai/conversations/');
        return response.data;
    }

    async getLatestConversation() {
        try {
            console.log('🔧 aiService.getLatestConversation llamado');
            const conversations = await this.getConversations();
            console.log('📝 Conversaciones encontradas:', conversations);
            
            if (conversations && conversations.results && conversations.results.length > 0) {
                const latest = conversations.results[0]; // Ya están ordenadas por fecha
                console.log('✅ Conversación más reciente:', latest);
                return latest;
            }
            return null;
        } catch (error) {
            console.error('❌ Error obteniendo conversación reciente:', error);
            return null;
        }
    }

    async loadConversationMessages(conversationId) {
        try {
            console.log('🔧 aiService.loadConversationMessages llamado:', conversationId);
            const response = await api.get(`/api/ai/conversations/${conversationId}/messages/`);
            console.log('📨 Mensajes cargados:', response.data);
            return response.data;
        } catch (error) {
            console.error('❌ Error cargando mensajes:', error);
            return [];
        }
    }

    async getOrCreateActiveConversationWithTools() {
        try {
            console.log('🛠️ aiService.getOrCreateActiveConversationWithTools llamado');
            
            // Buscar conversación específica de Jorge (analista)
            const jorgeConversation = await this.getJorgeConversation();
            
            if (jorgeConversation && jorgeConversation.thread_id) {
                console.log('✅ Usando conversación existente de Jorge:', jorgeConversation.id);
                const messages = await this.getMessagesWithTools(jorgeConversation.thread_id);
                return {
                    conversation: jorgeConversation,
                    messages: messages.messages || [],
                    isExisting: true
                };
            } else {
                console.log('🆕 Creando nueva conversación con Jorge...');
                const newThread = await this.createThreadWithTools();
                return {
                    conversation: { 
                        id: newThread.conversation_id, 
                        thread_id: newThread.thread_id,
                        title: "Conversación con Jorge"
                    },
                    messages: [{ role: 'assistant', content: newThread.message }],
                    isExisting: false
                };
            }
        } catch (error) {
            console.error('❌ Error en getOrCreateActiveConversationWithTools:', error);
            throw error;
        }
    }

    async getJorgeConversation() {
        try {
            console.log('🔍 Buscando conversación específica de Jorge...');
            const conversations = await this.getConversations();
            
            if (conversations && conversations.results && conversations.results.length > 0) {
                // Buscar conversación que contenga "Jorge" en el título
                const jorgeConv = conversations.results.find(conv => 
                    conv.title && conv.title.toLowerCase().includes('jorge')
                );
                
                if (jorgeConv) {
                    console.log('✅ Conversación de Jorge encontrada:', jorgeConv);
                    return jorgeConv;
                }
                
                console.log('⚠️ No se encontró conversación específica de Jorge');
            }
            return null;
        } catch (error) {
            console.error('❌ Error buscando conversación de Jorge:', error);
            return null;
        }
    }

    async getOrCreateActiveConversation() {
        try {
            console.log('🔧 aiService.getOrCreateActiveConversation llamado');
            
            const latestConversation = await this.getLatestConversation();
            
            if (latestConversation && latestConversation.thread_id) {
                console.log('✅ Usando conversación existente con thread_id:', latestConversation.id);
                return {
                    conversation: latestConversation,
                    messages: await this.loadConversationMessages(latestConversation.id),
                    isExisting: true
                };
            } else {
                console.log('🆕 Creando nueva conversación...');
                const newThread = await this.createThread();
                return {
                    conversation: { 
                        id: newThread.conversation_id, 
                        thread_id: newThread.thread_id,
                        title: "Nueva Conversación"
                    },
                    messages: [{ role: 'assistant', content: newThread.message }],
                    isExisting: false
                };
            }
        } catch (error) {
            console.error('❌ Error en getOrCreateActiveConversation:', error);
            throw error;
        }
    }

    async createNewConversationWithTools() {
        console.log('🛠️ Creando nueva conversación con tools...');
        return await this.createThreadWithTools();
    }

    async createNewConversation() {
        console.log('🆕 Creando nueva conversación...');
        return await this.createThread();
    }
}

export const aiService = new AIService(); 
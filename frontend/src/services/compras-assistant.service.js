import { api } from '../api';

class ComprasAssistantService {
    
    /**
     * Crear un nuevo thread para el asistente de compras
     */
    async createThread() {
        console.log('📦 ComprasAssistant.createThread llamado');
        const response = await api.post('/api/ai/compras-assistant/');
        console.log('📦 createThread response:', response.data);
        return response.data;
    }

    /**
     * Enviar mensaje al asistente de compras
     */
    async sendMessage(threadId, message) {
        console.log('📦 ComprasAssistant.sendMessage llamado', { threadId, message });
        const response = await api.post(`/api/ai/compras-assistant/${threadId}/messages/`, {
            message
        });
        console.log('📦 sendMessage response:', response.data);
        return response.data;
    }

    /**
     * Obtener mensajes del thread de compras
     */
    async getMessages(threadId) {
        console.log('📦 ComprasAssistant.getMessages llamado:', threadId);
        const response = await api.get(`/api/ai/compras-assistant/${threadId}/messages/`);
        console.log('📦 getMessages response:', response.data);
        return response.data;
    }

    /**
     * Obtener conversación activa de compras o crear una nueva
     */
    async getOrCreateActiveConversation() {
        try {
            console.log('📦 ComprasAssistant.getOrCreateActiveConversation llamado');
            
            const response = await api.get('/api/ai/compras-assistant/conversation/');
            console.log('📦 Conversación de compras obtenida:', response.data);
            
            if (response.data.thread_id) {
                // Cargar mensajes existentes
                const messages = await this.getMessages(response.data.thread_id);
                return {
                    conversation: {
                        id: response.data.conversation_id,
                        thread_id: response.data.thread_id,
                        title: "Chat de Compras",
                        assistant: response.data.assistant
                    },
                    messages: messages.messages || [],
                    isExisting: true
                };
            } else {
                // Crear nueva conversación
                const newThread = await this.createThread();
                return {
                    conversation: {
                        id: newThread.conversation_id,
                        thread_id: newThread.thread_id,
                        title: "Chat de Compras",
                        assistant: newThread.assistant
                    },
                    messages: [], // Los mensajes de bienvenida se cargarán después
                    isExisting: false
                };
            }
        } catch (error) {
            console.error('❌ Error en ComprasAssistant.getOrCreateActiveConversation:', error);
            throw error;
        }
    }

    /**
     * Crear una nueva conversación de compras
     */
    async createNewConversation() {
        console.log('📦 Creando nueva conversación de compras...');
        return await this.createThread();
    }

    /**
     * Buscar productos (para autocompletado)
     */
    async buscarProductos(query) {
        try {
            console.log('🔍 Buscando productos para compra:', query);
            const response = await api.get(`/api/inventario/productos/buscar/?q=${encodeURIComponent(query)}`);
            return response.data;
        } catch (error) {
            console.error('❌ Error buscando productos:', error);
            return [];
        }
    }

    /**
     * Buscar proveedores (para autocompletado)  
     */
    async buscarProveedores(query) {
        try {
            console.log('🔍 Buscando proveedores:', query);
            const response = await api.get(`/api/compras/proveedores/buscar/?q=${encodeURIComponent(query)}`);
            return response.data;
        } catch (error) {
            console.error('❌ Error buscando proveedores:', error);
            return [];
        }
    }
}

export const comprasAssistantService = new ComprasAssistantService(); 
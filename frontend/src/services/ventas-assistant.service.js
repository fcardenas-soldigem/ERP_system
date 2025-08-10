import { api } from '../api';

class VentasAssistantService {
    
    /**
     * Crear un nuevo thread para el asistente de ventas
     */
    async createThread() {
        console.log('🛒 VentasAssistant.createThread llamado');
        const response = await api.post('/api/ai/ventas-assistant/');
        console.log('🛒 createThread response:', response.data);
        return response.data;
    }

    /**
     * Enviar mensaje al asistente de ventas
     */
    async sendMessage(threadId, message) {
        console.log('🛒 VentasAssistant.sendMessage llamado', { threadId, message });
        const response = await api.post(`/api/ai/ventas-assistant/${threadId}/messages/`, {
            message
        });
        console.log('🛒 sendMessage response:', response.data);
        return response.data;
    }

    /**
     * Obtener mensajes del thread de ventas
     */
    async getMessages(threadId) {
        console.log('🛒 VentasAssistant.getMessages llamado:', threadId);
        const response = await api.get(`/api/ai/ventas-assistant/${threadId}/messages/`);
        console.log('🛒 getMessages response:', response.data);
        return response.data;
    }

    /**
     * Obtener conversación activa de ventas o crear una nueva
     */
    async getOrCreateActiveConversation() {
        try {
            console.log('🛒 VentasAssistant.getOrCreateActiveConversation llamado');
            
            const response = await api.get('/api/ai/ventas-assistant/conversation/');
            console.log('🛒 Conversación de ventas obtenida:', response.data);
            
            if (response.data.thread_id) {
                // Cargar mensajes existentes
                const messages = await this.getMessages(response.data.thread_id);
                return {
                    conversation: {
                        id: response.data.conversation_id,
                        thread_id: response.data.thread_id,
                        title: "Chat de Ventas",
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
                        title: "Chat de Ventas",
                        assistant: newThread.assistant
                    },
                    messages: [], // Los mensajes de bienvenida se cargarán después
                    isExisting: false
                };
            }
        } catch (error) {
            console.error('❌ Error en VentasAssistant.getOrCreateActiveConversation:', error);
            throw error;
        }
    }

    /**
     * Crear una nueva conversación de ventas
     */
    async createNewConversation() {
        console.log('🛒 Creando nueva conversación de ventas...');
        return await this.createThread();
    }

    /**
     * Buscar productos (para autocompletado)
     */
    async buscarProductos(query) {
        try {
            console.log('🔍 Buscando productos:', query);
            const response = await api.get(`/api/inventario/productos/buscar/?q=${encodeURIComponent(query)}`);
            return response.data;
        } catch (error) {
            console.error('❌ Error buscando productos:', error);
            return [];
        }
    }

    /**
     * Buscar clientes (para autocompletado)  
     */
    async buscarClientes(query) {
        try {
            console.log('🔍 Buscando clientes:', query);
            const response = await api.get(`/api/ventas/clientes/buscar/?q=${encodeURIComponent(query)}`);
            return response.data;
        } catch (error) {
            console.error('❌ Error buscando clientes:', error);
            return [];
        }
    }
}

export const ventasAssistantService = new VentasAssistantService(); 
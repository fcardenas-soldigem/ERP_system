import { useState, useEffect, useCallback } from 'react';
import { clientesService } from '../services/clientes.service';
import useConsultaDocumentos from './useConsultaDocumentos';

/**
 * Encapsulates all client search and selection state for sale forms.
 *
 * Replaces 8 useState calls in NuevaVenta:
 *   clienteSearch, showClienteDropdown, filteredClientes, selectedClienteIndex,
 *   documentoSearch, tipoDocumento, consultandoDocumento, modoConsultaDocumento
 *
 * @param {Array}    clientes      - list from useQuery(['clientes'])
 * @param {Function} toast         - Chakra useToast()
 * @param {Object}   queryClient   - from useQueryClient()
 * @param {Function} onSelect      - callback(clienteId) when a client is chosen
 */
export const useClienteSelector = (clientes = [], toast, queryClient, onSelect) => {
  // Search by name
  const [clienteSearch, setClienteSearch]           = useState('');
  const [showClienteDropdown, setDropdown]          = useState(false);
  const [filteredClientes, setFiltered]             = useState([]);
  const [selectedIndex, setSelectedIndex]           = useState(-1);

  // Search / create by document
  const [documentoSearch, setDocumentoSearch]       = useState('');
  const [tipoDocumento, setTipoDocumento]           = useState('dni');
  const [consultando, setConsultando]               = useState(false);
  const [modoDocumento, setModoDocumento]           = useState(false);

  const { consultarDocumento, validarDocumento, limpiarError } = useConsultaDocumentos();

  // ── Filter by name ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!clienteSearch) { setFiltered([]); setDropdown(false); return; }
    const q = clienteSearch.toLowerCase();
    const matches = clientes.filter(c =>
      c.nombre.toLowerCase().includes(q) || c.documento.includes(clienteSearch)
    );
    setFiltered(matches);
    setDropdown(matches.length > 0);
  }, [clienteSearch, clientes]);

  // ── Select by name dropdown ───────────────────────────────────────────────
  const selectCliente = useCallback((cliente) => {
    setClienteSearch(cliente.nombre);
    setDropdown(false);
    setSelectedIndex(-1);
    onSelect(cliente.id);
  }, [onSelect]);

  const handleSearchChange = useCallback((e) => {
    const v = e.target.value;
    setClienteSearch(v);
    setSelectedIndex(-1);
    if (!v) onSelect('');
  }, [onSelect]);

  // ── Keyboard navigation ───────────────────────────────────────────────────
  const handleSearchKeyDown = useCallback((e) => {
    if (!showClienteDropdown || !filteredClientes.length) return;
    if (e.key === 'ArrowDown') {
      setSelectedIndex(i => Math.min(i + 1, filteredClientes.length - 1));
    } else if (e.key === 'ArrowUp') {
      setSelectedIndex(i => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      selectCliente(filteredClientes[selectedIndex]);
    } else if (e.key === 'Escape') {
      setDropdown(false);
    }
  }, [showClienteDropdown, filteredClientes, selectedIndex, selectCliente]);

  // ── Toggle between search modes ───────────────────────────────────────────
  const toggleModo = useCallback(() => {
    setModoDocumento(m => !m);
    setClienteSearch('');
    setDocumentoSearch('');
    setDropdown(false);
    onSelect('');
    limpiarError();
  }, [onSelect, limpiarError]);

  // ── Create or find by document ────────────────────────────────────────────
  const buscarOCrearPorDocumento = useCallback(async () => {
    if (!validarDocumento(documentoSearch, tipoDocumento)) {
      toast({
        title: 'Documento inválido',
        description: `El ${tipoDocumento.toUpperCase()} debe tener ${tipoDocumento === 'dni' ? '8' : '11'} dígitos`,
        status: 'error', duration: 3000, isClosable: true,
      });
      return;
    }

    setConsultando(true);
    try {
      const existente = clientes.find(c => c.documento === documentoSearch);
      if (existente) {
        selectCliente(existente);
        setModoDocumento(false);
        setDocumentoSearch('');
        toast({ title: 'Cliente encontrado', status: 'success', duration: 2000 });
        return;
      }

      const datos = await consultarDocumento(documentoSearch, tipoDocumento);
      if (!datos) {
        toast({ title: 'No se encontraron datos', status: 'error', duration: 3000 });
        return;
      }

      const nombre = tipoDocumento === 'dni'
        ? (datos.nombre_completo || `${datos.nombres || ''} ${datos.apellido_paterno || ''} ${datos.apellido_materno || ''}`.trim())
        : (datos.razon_social || datos.nombre_comercial || '');

      if (!nombre) {
        toast({ title: 'Datos incompletos del documento', status: 'error', duration: 3000 });
        return;
      }

      const nuevo = await clientesService.createCliente({
        nombre,
        documento: documentoSearch,
        tipo_documento: tipoDocumento,
        direccion: tipoDocumento === 'ruc' ? (datos.direccion || '') : '',
        telefono: '',
        email: '',
      });

      queryClient.invalidateQueries(['clientes']);
      selectCliente(nuevo);
      setModoDocumento(false);
      setDocumentoSearch('');
      toast({ title: `Cliente "${nombre}" creado`, status: 'success', duration: 3000 });

    } catch (err) {
      toast({ title: 'Error al procesar cliente', status: 'error', duration: 3000 });
    } finally {
      setConsultando(false);
    }
  }, [documentoSearch, tipoDocumento, clientes, consultarDocumento, validarDocumento, selectCliente, queryClient, toast]);

  return {
    // Name search
    clienteSearch,
    showClienteDropdown,
    filteredClientes,
    selectedIndex,
    handleSearchChange,
    handleSearchKeyDown,
    selectCliente,
    closeDropdown: () => setDropdown(false),

    // Document search
    documentoSearch,
    setDocumentoSearch,
    tipoDocumento,
    setTipoDocumento,
    consultando,
    modoDocumento,
    toggleModo,
    buscarOCrearPorDocumento,
  };
};

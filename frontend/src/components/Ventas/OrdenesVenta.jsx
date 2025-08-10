import React, { useEffect, useState } from 'react';
import api from '../../api.jsx';
import { Table, Button, Modal, Form, Row, Col } from 'react-bootstrap';

const OrdenesVenta = () => {
  const [ordenesVenta, setOrdenesVenta] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [productos, setProductos] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [nuevaOrden, setNuevaOrden] = useState({
    cliente: '',
    fecha: '',
    estado: 'pendiente',
    productos: []
  });

  useEffect(() => {
    fetchOrdenesVenta();
    fetchClientes();
    fetchProductos();
  }, []);

  const fetchOrdenesVenta = async () => {
    try {
      const response = await api.get('ventas/ordenes/');
      setOrdenesVenta(response.data);
    } catch (error) {
      console.error('Error al obtener órdenes de venta:', error);
    }
  };

  const fetchClientes = async () => {
    try {
      const response = await api.get('ventas/clientes/');
      setClientes(response.data);
    } catch (error) {
      console.error('Error al obtener clientes:', error);
    }
  };

  const fetchProductos = async () => {
    try {
      const response = await api.get('inventario/productos/');
      setProductos(response.data);
    } catch (error) {
      console.error('Error al obtener productos:', error);
    }
  };

  const handleInputChange = (e) => {
    setNuevaOrden({
      ...nuevaOrden,
      [e.target.name]: e.target.value
    });
  };

  const handleProductoChange = (index, field, value) => {
    const nuevosProductos = [...nuevaOrden.productos];
    nuevosProductos[index][field] = value;
    setNuevaOrden({
      ...nuevaOrden,
      productos: nuevosProductos
    });
  };

  const agregarProducto = () => {
    setNuevaOrden({
      ...nuevaOrden,
      productos: [...nuevaOrden.productos, { producto: '', cantidad: 1, precio: 0 }]
    });
  };

  const eliminarProducto = (index) => {
    const nuevosProductos = [...nuevaOrden.productos];
    nuevosProductos.splice(index, 1);
    setNuevaOrden({
      ...nuevaOrden,
      productos: nuevosProductos
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('ventas/ordenes/', nuevaOrden);
      fetchOrdenesVenta();
      setShowModal(false);
      setNuevaOrden({ cliente: '', fecha: '', estado: 'pendiente', productos: [] });
    } catch (error) {
      console.error('Error al crear orden de venta:', error);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`ventas/ordenes/${id}/`);
      fetchOrdenesVenta();
    } catch (error) {
      console.error('Error al eliminar orden de venta:', error);
    }
  };

  return (
    <div className="mt-5">
      <h4>Órdenes de Venta</h4>
      <Button variant="primary" onClick={() => setShowModal(true)}>
        Crear Orden de Venta
      </Button>

      <Table striped bordered hover className="mt-3">
        <thead>
          <tr>
            <th>ID Orden</th>
            <th>Cliente</th>
            <th>Fecha</th>
            <th>Estado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {ordenesVenta.map((orden) => (
            <tr key={orden.id}>
              <td>{orden.id}</td>
              <td>{orden.cliente.nombre}</td>
              <td>{orden.fecha}</td>
              <td>{orden.estado}</td>
              <td>
                <Button variant="danger" size="sm" onClick={() => handleDelete(orden.id)}>
                  Eliminar
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {/* Modal para Crear Orden de Venta */}
      <Modal show={showModal} onHide={() => setShowModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Crear Orden de Venta</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form onSubmit={handleSubmit}>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Cliente</Form.Label>
                  <Form.Control
                    as="select"
                    name="cliente"
                    value={nuevaOrden.cliente}
                    onChange={handleInputChange}
                    required
                  >
                    <option value="">Selecciona un cliente</option>
                    {clientes.map((cliente) => (
                      <option key={cliente.id} value={cliente.id}>{cliente.nombre}</option>
                    ))}
                  </Form.Control>
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Fecha</Form.Label>
                  <Form.Control
                    type="date"
                    name="fecha"
                    value={nuevaOrden.fecha}
                    onChange={handleInputChange}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={3}>
                <Form.Group className="mb-3">
                  <Form.Label>Estado</Form.Label>
                  <Form.Control
                    as="select"
                    name="estado"
                    value={nuevaOrden.estado}
                    onChange={handleInputChange}
                    required
                  >
                    <option value="pendiente">Pendiente</option>
                    <option value="completada">Completada</option>
                    <option value="cancelada">Cancelada</option>
                  </Form.Control>
                </Form.Group>
              </Col>
            </Row>

            <h5>Productos</h5>
            {nuevaOrden.productos.map((prod, index) => (
              <Row key={index} className="mb-3 border p-3">
                <Col md={5}>
                  <Form.Group>
                    <Form.Label>Producto</Form.Label>
                    <Form.Control
                      as="select"
                      value={prod.producto}
                      onChange={(e) => handleProductoChange(index, 'producto', e.target.value)}
                      required
                    >
                      <option value="">Selecciona un producto</option>
                      {productos.map((producto) => (
                        <option key={producto.id} value={producto.id}>{producto.nombre}</option>
                      ))}
                    </Form.Control>
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>Cantidad</Form.Label>
                    <Form.Control
                      type="number"
                      min="1"
                      value={prod.cantidad}
                      onChange={(e) => handleProductoChange(index, 'cantidad', e.target.value)}
                      required
                    />
                  </Form.Group>
                </Col>
                <Col md={3}>
                  <Form.Group>
                    <Form.Label>Precio</Form.Label>
                    <Form.Control
                      type="number"
                      min="0"
                      value={prod.precio}
                      onChange={(e) => handleProductoChange(index, 'precio', e.target.value)}
                      required
                    />
                  </Form.Group>
                </Col>
                <Col md={1} className="d-flex align-items-end">
                  <Button variant="danger" onClick={() => eliminarProducto(index)}>
                    X
                  </Button>
                </Col>
              </Row>
            ))}
            <Button variant="secondary" onClick={agregarProducto}>
              Agregar Producto
            </Button>
            <br /><br />
            <Button variant="primary" type="submit">
              Crear Orden
            </Button>
          </Form>
        </Modal.Body>
      </Modal>
    </div>
  );
};

export default OrdenesVenta; 
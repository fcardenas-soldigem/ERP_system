import React from 'react';
import { Button } from '@chakra-ui/react';

const Factura = ({ orden }) => {
  const generarPDF = async () => {
    try {
      const jsPDF = (await import('jspdf')).default;
      const html2canvas = (await import('html2canvas')).default;
      const input = document.getElementById('factura');
      if (!input) return;
      input.style.display = 'block';
      const canvas = await html2canvas(input);
      input.style.display = 'none';
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const imgProps = pdf.getImageProperties(imgData);
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`Factura_${orden.id}.pdf`);
    } catch (error) {
      console.error('Error al generar PDF:', error);
    }
  };

  return (
    <div>
      <Button colorScheme="green" onClick={generarPDF}>Generar Factura PDF</Button>

      <div id="factura" style={{ display: 'none' }}>
        <h1>Factura</h1>
        <p>ID Orden: {orden.id}</p>
        <p>Cliente: {orden.cliente.nombre}</p>
        <p>Fecha: {orden.fecha}</p>
        <p>Estado: {orden.estado}</p>
        <h3>Productos</h3>
        <table>
          <thead><tr><th>Producto</th><th>Cantidad</th><th>Precio Unitario</th><th>Total</th></tr></thead>
          <tbody>
            {orden.productos.map((prod, index) => (
              <tr key={index}>
                <td>{prod.nombre}</td>
                <td>{prod.cantidad}</td>
                <td>${prod.precio}</td>
                <td>${prod.cantidad * prod.precio}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>Total a Pagar: ${orden.productos.reduce((acc, prod) => acc + (prod.cantidad * prod.precio), 0)}</h3>
      </div>
    </div>
  );
};

export default Factura;

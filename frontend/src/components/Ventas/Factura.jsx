import React from 'react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import { Button } from 'react-bootstrap';

const Factura = ({ orden }) => {
  const generarPDF = () => {
    const input = document.getElementById('factura');
    html2canvas(input)
      .then((canvas) => {
        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF('p', 'mm', 'a4');
        const imgProps= pdf.getImageProperties(imgData);
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
        pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
        pdf.save(`Factura_${orden.id}.pdf`);
      })
      .catch((error) => console.error('Error al generar PDF:', error));
  };

  return (
    <div>
      <Button variant="success" onClick={generarPDF}>Generar Factura PDF</Button>

      {/* Este div contiene la estructura de la factura, ocultado en la interfaz */}
      <div id="factura" style={{ display: 'none' }}>
        <h1>Factura</h1>
        <p>ID Orden: {orden.id}</p>
        <p>Cliente: {orden.cliente.nombre}</p>
        <p>Fecha: {orden.fecha}</p>
        <p>Estado: {orden.estado}</p>
        <h3>Productos</h3>
        <table>
          <thead>
            <tr>
              <th>Producto</th>
              <th>Cantidad</th>
              <th>Precio Unitario</th>
              <th>Total</th>
            </tr>
          </thead>
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
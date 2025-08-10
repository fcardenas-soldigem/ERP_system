import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Login from './Login';
import { AuthContext } from '../context/AuthContext';
import { BrowserRouter as Router } from 'react-router-dom';

test('renders formulario de inicio de sesión', () => {
  render(
    <AuthContext.Provider value={{ login: jest.fn() }}>
      <Router>
        <Login />
      </Router>
    </AuthContext.Provider>
  );

  expect(screen.getByText(/Iniciar Sesión/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Usuario:/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Contraseña:/i)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /Entrar/i })).toBeInTheDocument();
});

test('permite al usuario ingresar credenciales', () => {
  const mockLogin = jest.fn();
  
  render(
    <AuthContext.Provider value={{ login: mockLogin }}>
      <Router>
        <Login />
      </Router>
    </AuthContext.Provider>
  );

  fireEvent.change(screen.getByLabelText(/Usuario:/i), { target: { value: 'testuser' } });
  fireEvent.change(screen.getByLabelText(/Contraseña:/i), { target: { value: 'testpass' } });
  fireEvent.click(screen.getByRole('button', { name: /Entrar/i }));

  expect(mockLogin).toHaveBeenCalledWith('testuser', 'testpass');
}); 
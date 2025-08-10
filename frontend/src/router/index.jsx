import { createBrowserRouter } from 'react-router-dom';
import PrivateRoute from './PrivateRoute';
import Chat from '../components/AIAssistant/Chat';

const router = createBrowserRouter([
    {
        path: '/chat',
        element: <PrivateRoute><Chat /></PrivateRoute>
    },
]);

export default router; 
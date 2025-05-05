import { Navigate, useLocation } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const location = useLocation();
  const token = localStorage.getItem('token');
  
  console.log('ProtectedRoute - Current location:', location.pathname);
  console.log('ProtectedRoute - Token exists:', !!token);

  if (!token) {
    console.log('ProtectedRoute - No token, redirecting to signin');
    // Redirect to login page but save the attempted url
    return <Navigate to="/signin" state={{ from: location }} replace />;
  }

  console.log('ProtectedRoute - Token found, rendering children');
  return <>{children}</>;
};

export default ProtectedRoute; 
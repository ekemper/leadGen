import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const isDashboardActive = location.pathname === '/dashboard';
  const isCampaignsActive = location.pathname === '/campaigns';

  return (
    <aside style={{
      position: 'fixed',
      left: '0',
      top: '0',
      height: '100vh',
      width: '250px',
      backgroundColor: '#252526',
      borderRight: '1px solid #333333'
    }}>
      <div style={{ padding: '1rem' }}>
        <h2 style={{ color: '#d4d4d4', fontSize: '1.25rem', fontWeight: '600' }}>LeadGen</h2>
      </div>
      <nav style={{ marginTop: '1rem' }}>
        <ul style={{ 
          padding: '0 1rem',
          listStyle: 'none',
          margin: '0'
        }}>
          <li>
            <Link 
              to="/dashboard" 
              style={{
                display: 'block',
                color: '#d4d4d4',
                padding: '0.5rem',
                textDecoration: 'none',
                backgroundColor: isDashboardActive ? '#2d2d2d' : 'transparent'
              }}
            >
              Dashboard
            </Link>
          </li>
          <li>
            <Link 
              to="/campaigns" 
              style={{
                display: 'block',
                color: '#d4d4d4',
                padding: '0.5rem',
                textDecoration: 'none',
                backgroundColor: isCampaignsActive ? '#2d2d2d' : 'transparent'
              }}
            >
              Campaigns
            </Link>
          </li>
          <li>
            <a href="#" style={{
              display: 'block',
              color: '#d4d4d4',
              padding: '0.5rem',
              textDecoration: 'none'
            }}>
              todo-placeholder
            </a>
          </li>
        </ul>
      </nav>
    </aside>
  );
};

export default Sidebar; 
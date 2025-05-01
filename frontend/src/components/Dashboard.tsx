import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div>
      {/* Sidebar */}
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
              <a href="#" style={{
                display: 'block',
                color: '#d4d4d4',
                padding: '0.5rem',
                textDecoration: 'none'
              }}>
                Campaigns
              </a>
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

      {/* Main Content */}
      <main style={{
        marginLeft: '250px',
        padding: '2rem'
      }}>
        <h1 style={{ color: '#d4d4d4', fontSize: '1.5rem' }}>Dashboard</h1>
      </main>
    </div>
  );
};

export default Dashboard; 
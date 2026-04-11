import React, { useState } from 'react';
import NotificationContainer from '../components/Alerts/NotificationContainer';
import '../components/Alerts/NotificationCard.css';
import '../components/Alerts/NotificationContainer.css';

const TestNotifications = () => {
  const [notifications, setNotifications] = useState([]);

  const showNotification = (type, title, message) => {
    const id = Date.now() + Math.random();
    console.log('Adding notification:', { id, type, title, message });
    setNotifications(prev => [...prev, { id, type, title, message, duration: 5000 }]);
  };

  const handleClose = (id) => {
    console.log('Closing notification:', id);
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  return (
    <div style={{ padding: '50px' }}>
      <h1>Notification Test Page</h1>
      <p>Click the buttons below to test notifications:</p>
      
      <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
        <button 
          onClick={() => showNotification('success', 'Success!', 'This is a success notification')}
          style={{ padding: '10px 20px', background: '#10b981', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
        >
          Show Success
        </button>
        
        <button 
          onClick={() => showNotification('error', 'Error!', 'This is an error notification')}
          style={{ padding: '10px 20px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
        >
          Show Error
        </button>
        
        <button 
          onClick={() => showNotification('warning', 'Warning!', 'This is a warning notification')}
          style={{ padding: '10px 20px', background: '#f59e0b', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
        >
          Show Warning
        </button>
        
        <button 
          onClick={() => showNotification('info', 'Info!', 'This is an info notification')}
          style={{ padding: '10px 20px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '5px', cursor: 'pointer' }}
        >
          Show Info
        </button>
      </div>

      <div style={{ marginTop: '20px' }}>
        <h3>Current Notifications: {notifications.length}</h3>
        <pre>{JSON.stringify(notifications, null, 2)}</pre>
      </div>

      <NotificationContainer 
        notifications={notifications} 
        onClose={handleClose}
      />
    </div>
  );
};

export default TestNotifications;

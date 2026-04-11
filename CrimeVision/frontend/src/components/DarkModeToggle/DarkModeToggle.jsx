// src/components/DarkModeToggle/DarkModeToggle.js
import React from 'react';
import './DarkModeToggle.css';

const DarkModeToggle = ({ darkMode, toggleDarkMode }) => {
  return (
    <button className="dark-mode-toggle" onClick={toggleDarkMode}>
      <i className={darkMode ? 'fas fa-sun' : 'fas fa-moon'}></i>
    </button>
  );
};

export default DarkModeToggle;

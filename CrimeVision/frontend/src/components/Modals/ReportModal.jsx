// src/components/Modals/ReportModal.js
import React from 'react';
import './ReportModal.css';

const ReportModal = ({ isOpen, closeModal }) => {
  if (!isOpen) return null;

  return (
    <div id="reportModal" className="modal">
      <div className="modal-content">
        <span className="close" onClick={closeModal}>&times;</span>
        <h3 className="modal-title">Report a Crime</h3>
        <form className="modal-form">
          <div className="form-group">
            <label htmlFor="crime-location">Location</label>
            <input type="text" id="crime-location" placeholder="Enter crime location" />
          </div>
          <div className="form-group">
            <label htmlFor="crime-type">Crime Type</label>
            <select id="crime-type">
              <option value="">Select crime type</option>
              <option value="theft">Theft</option>
              <option value="robbery">Robbery</option>
              <option value="assault">Assault</option>
              <option value="burglary">Burglary</option>
              <option value="snatching">Snatching</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="crime-date">Date & Time</label>
            <input type="datetime-local" id="crime-date" />
          </div>
          <div className="form-group">
            <label htmlFor="crime-description">Description</label>
            <textarea id="crime-description" rows="3" placeholder="Describe the incident"></textarea>
          </div>
          <button type="button" className="btn btn-primary">Submit Report</button>
        </form>
      </div>
    </div>
  );
};

export default ReportModal;
import React, { useState, useEffect } from 'react';
import './TestModelModal.css';

const TestModelModal = ({ isOpen, closeModal }) => {
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [areas, setAreas] = useState([]);
  const [formData, setFormData] = useState({
    crime_type: '',
    area: '',
    date: '',
    latitude: '',
    longitude: '',
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Fetch crime types and areas
      fetch('/api/crime-types')
        .then(res => res.json())
        .then(data => setCrimeTypes(data.crime_types || []))
        .catch(() => setCrimeTypes([]));

      fetch('/api/areas')
        .then(res => res.json())
        .then(data => setAreas(data.areas || []))
        .catch(() => setAreas([]));

      // Reset form and result
      setFormData({
        crime_type: '',
        area: '',
        date: '',
        latitude: '',
        longitude: '',
      });
      setResult(null);
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    // Basic validation
    if (!formData.crime_type || !formData.area || !formData.date || !formData.latitude || !formData.longitude) {
      setError('Please fill in all fields.');
      setSubmitting(false);
      return;
    }

    // Prepare payload
    const payload = {
      crime_type: formData.crime_type,
      area: formData.area,
      date: formData.date,
      latitude: parseFloat(formData.latitude),
      longitude: parseFloat(formData.longitude),
    };

    try {
      const response = await fetch('/api/crimes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to submit');
      }
      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div id="testModelModal" className="modal">
      <div className="modal-content">
        <span className="close" onClick={closeModal}>&times;</span>
        <h3 className="modal-title">Test Crime Risk Model</h3>
        <form className="modal-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="crime_type">Crime Type</label>
            <input type="text" name="crime_type" id="crime_type" value={formData.crime_type} onChange={handleChange} placeholder="Enter crime type (e.g., theft, robbery)" required />
          </div>
          <div className="form-group">
            <label htmlFor="area">Area</label>
            <input type="text" name="area" id="area" value={formData.area} onChange={handleChange} placeholder="Enter area (e.g., North, South)" required />
          </div>
          <div className="form-group">
            <label htmlFor="date">Date</label>
            <input type="date" name="date" id="date" value={formData.date} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label htmlFor="latitude">Latitude</label>
            <input type="number" step="any" name="latitude" id="latitude" value={formData.latitude} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label htmlFor="longitude">Longitude</label>
            <input type="number" step="any" name="longitude" id="longitude" value={formData.longitude} onChange={handleChange} required />
          </div>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit'}
          </button>
        </form>
        {error && <div className="error-message">{error}</div>}
        {result && (
          <div className="result-message">
            <p>Crime ID: {result.id}</p>
            <p>Predicted Risk Level: <strong>{result.risk_level}</strong></p>
            <p>Message: {result.message}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TestModelModal;

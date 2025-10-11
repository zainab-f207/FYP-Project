import React, { useState } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
import apiService from '../../services/apiService_updated';

const ForgotPasswordModal = ({ show, onHide }) => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await apiService.forgotPassword(email);
      setMessage(response.message || 'Password reset email sent successfully!');
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Failed to send password reset email');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setEmail('');
    setError('');
    setMessage('');
    setSuccess(false);
    onHide();
  };

  return (
    <Modal show={show} onHide={handleClose} centered>
      <Modal.Header closeButton>
        <Modal.Title>Forgot Password</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {success ? (
          <Alert variant="success">
            <h5>Check Your Email</h5>
            <p>{message}</p>
            <p className="mb-0">If you don't see the email, check your spam folder.</p>
          </Alert>
        ) : (
          <>
            <p>Enter your email address and we'll send you a link to reset your password.</p>
            {error && <Alert variant="danger">{error}</Alert>}
            {message && <Alert variant="info">{message}</Alert>}
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label>Email Address</Form.Label>
                <Form.Control
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                />
              </Form.Group>
              <div className="d-grid">
                <Button
                  variant="primary"
                  type="submit"
                  disabled={loading || !email.trim()}
                >
                  {loading ? (
                    <>
                      <Spinner animation="border" size="sm" className="me-2" />
                      Sending...
                    </>
                  ) : (
                    'Send Reset Link'
                  )}
                </Button>
              </div>
            </Form>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={handleClose}>
          {success ? 'Close' : 'Cancel'}
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default ForgotPasswordModal;

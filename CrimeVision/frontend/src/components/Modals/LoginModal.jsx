import React, { useState } from "react";
import { useAuth } from "../../contexts/AuthContext";
import "./LoginModal.css";

const LoginModal = ({ isOpen, closeModal }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: "",
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    confirmPassword: "",
    homeArea: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [generatedUsername, setGeneratedUsername] = useState("");

  const { login, register } = useAuth();

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError(""); // Clear error when user starts typing

    // Auto-generate username when first name or last name changes
    if (
      !isLogin &&
      (e.target.name === "firstName" || e.target.name === "lastName")
    ) {
      if (formData.firstName && formData.lastName) {
        const generated = `${formData.firstName.toLowerCase()}.${formData.lastName.toLowerCase()}`;
        setGeneratedUsername(generated);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (isLogin) {
        // Login
        const result = await login(formData.username, formData.password);
        if (result.success) {
          closeModal();
        } else {
          setError(result.error);
        }
      } else {
        // Register
        if (formData.password !== formData.confirmPassword) {
          setError("Passwords do not match");
          setLoading(false);
          return;
        }

        if (formData.password.length < 6) {
          setError("Password must be at least 6 characters long");
          setLoading(false);
          return;
        }

        const result = await register(
          formData.firstName,
          formData.lastName,
          formData.email,
          formData.password,
          formData.homeArea 
        );
        if (result.success) {
          // Show success message with generated username
          alert(
            `Registration successful! Your username is: ${result.username}\n\n${result.message}`
          );
          closeModal();
        } else {
          setError(result.error);
        }
      }
    } catch (error) {
      setError("An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setFormData({
      username: "",
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      confirmPassword: "",
      homeArea: ""
    });
    setError("");
    setGeneratedUsername("");
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={closeModal}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{isLogin ? "Login" : "Register"}</h2>
          <button className="close-button" onClick={closeModal}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {isLogin ? (
            // Login Form
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                required
                disabled={loading}
              />
            </div>
          ) : (
            // Registration Form
            <>
              <div className="form-group">
                <label htmlFor="firstName">First Name</label>
                <input
                  type="text"
                  id="firstName"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleInputChange}
                  required
                  disabled={loading}
                  placeholder="Enter your first name"
                />
              </div>

              <div className="form-group">
                <label htmlFor="lastName">Last Name</label>
                <input
                  type="text"
                  id="lastName"
                  name="lastName"
                  value={formData.lastName}
                  onChange={handleInputChange}
                  required
                  disabled={loading}
                  placeholder="Enter your last name"
                />
              </div>

              {generatedUsername && (
                <div className="form-group">
                  <label>Generated Username</label>
                  <div className="username-display">
                    <strong>{generatedUsername}</strong>
                    <small>(This will be your username)</small>
                  </div>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  disabled={loading}
                  placeholder="Enter your email address"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              disabled={loading}
              placeholder="Enter your password"
            />
          </div>

          {!isLogin && (
            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                required
                disabled={loading}
                placeholder="Confirm your password"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="homeArea">Home Area (Optional)</label>
            <input
              type="text"
              id="homeArea"
              name="homeArea"
              value={formData.homeArea}
              onChange={handleInputChange}
              disabled={loading}
              placeholder="Enter your home area (e.g., Gulberg, DHA)"
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? "Loading..." : isLogin ? "Login" : "Register"}
          </button>
        </form>

        <div className="auth-toggle">
          <p>
            {isLogin ? "Don't have an account?" : "Already have an account?"}
            <button
              type="button"
              className="toggle-button"
              onClick={toggleMode}
              disabled={loading}
            >
              {isLogin ? "Register" : "Login"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginModal;

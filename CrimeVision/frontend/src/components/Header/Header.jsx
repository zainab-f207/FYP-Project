// src/components/Header/Header.js
import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import './Header2.css';
import apiService from '../../services/apiService';
import SafeVisionLogo from '../common/SafeVisionLogo';

const Header = ({ toggleSidebar, showLoginModal, showReportModal, onAreaSelect, onCrimeSelect }) => {
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [areas, setAreas] = useState(['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan', 'Peshawar', 'Quetta', 'Sialkot', 'Gujranwala']);
  const [crimeTypes, setCrimeTypes] = useState(['Murder', 'Theft', 'Robbery', 'Burglary', 'Assault', 'Kidnapping', 'Fraud', 'Drug Trafficking', 'Terrorism', 'Cyber Crime']);
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeNav, setActiveNav] = useState('home');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isLogoPopupOpen, setIsLogoPopupOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  const searchInputRef = useRef(null);
  const searchDropdownRef = useRef(null);
  const navbarRef = useRef(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Predefined search data
  const pages = [
    { id: 'home', title: 'Home', route: '/', category: 'Pages' },
    { id: 'map', title: 'Crime Map', route: '/crime-map', category: 'Pages' },
    { id: 'risk', title: 'Risk Prediction', route: '/risk-prediction', category: 'Pages' },
    { id: 'emergency', title: 'Emergency Contacts', route: '/emergency', category: 'Pages' },
    { id: 'about', title: 'About Project', route: '/about-project', category: 'Pages' }
  ];

  const features = [
    { id: 'heatmap', title: 'Crime Heatmap', route: '/crime-map', category: 'Features' },
    { id: 'prediction', title: 'AI Risk Prediction', route: '/risk-prediction', category: 'Features' },
    { id: 'police', title: 'Nearby Police Stations', route: '/emergency', category: 'Features' },
    { id: 'hospitals', title: 'Emergency Hospitals', route: '/emergency', category: 'Features' },
    { id: 'report', title: 'Report Incident', route: '/emergency', category: 'Features' },
    { id: 'alerts', title: 'Safety Alerts', route: '/risk-prediction', category: 'Features' }
  ];

  // Project-focused statistics
  const projectStats = {
    incidentsAnalyzed: "1K+",
    spatialCoverage: "5+ Areas",
    dataYears: "2024-2025",
    predictionAccuracy: "90%"
  };

  // Enhanced theme toggle with smooth transition
  const toggleTheme = () => {
    setIsDarkTheme(!isDarkTheme);
    document.body.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
    document.body.setAttribute('data-theme', isDarkTheme ? 'light' : 'dark');
  };

  // Generate particles for background
  const generateParticles = () => {
    const particles = [];
    for (let i = 0; i < 15; i++) {
      particles.push(
        <div
          key={i}
          className="particle"
          style={{
            left: `${Math.random() * 100}%`,
            animationDelay: `${Math.random() * 15}s`,
            animationDuration: `${15 + Math.random() * 10}s`
          }}
        />
      );
    }
    return particles;
  };

  // Fallback local search function
  const performSearch = (query) => {
    const results = [];
    const lowercaseQuery = query.toLowerCase();

    // Search Areas
    areas.forEach(area => {
      if (area.toLowerCase().includes(lowercaseQuery)) {
        results.push({ type: 'area', value: area, display: area, category: 'Areas', route: '/crime-map' });
      }
    });

    // Search Crime Types
    crimeTypes.forEach(crime => {
      if (crime.toLowerCase().includes(lowercaseQuery)) {
        results.push({ type: 'crime', value: crime, display: crime, category: 'Crime Types', route: '/risk-prediction' });
      }
    });

    // Search Pages
    pages.forEach(page => {
      if (page.title.toLowerCase().includes(lowercaseQuery)) {
        results.push({ type: 'page', value: page.id, display: page.title, category: 'Pages', route: page.route });
      }
    });

    // Search Features
    features.forEach(feature => {
      if (feature.title.toLowerCase().includes(lowercaseQuery)) {
        results.push({ type: 'feature', value: feature.id, display: feature.title, category: 'Features', route: feature.route });
      }
    });

    return results.slice(0, 10);
  };

  // Instant search input handler
  const handleSearchInput = (e) => {
    const query = e.target.value;
    setSearchQuery(query);

    if (query.length >= 1) {
      const results = performSearch(query);
      setSearchResults(results);
      setShowSearchDropdown(true);
    } else {
      setShowSearchDropdown(false);
    }
  };

  // Scroll effects
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Update active nav based on current route
  useEffect(() => {
    const path = location.pathname;
    if (path === '/') setActiveNav('home');
    else if (path === '/crime-map') setActiveNav('map');
    else if (path === '/risk-prediction') setActiveNav('analytics');
    else if (path === '/emergency') setActiveNav('resources');
    else if (path === '/about-project') setActiveNav('video');
  }, [location]);

  // Enhanced navigation with proper routes
  const navItems = [
    { id: 'home', label: 'Home', icon: 'fas fa-home', route: '/' },
    { id: 'map', label: 'Incident Map', icon: 'fas fa-map', route: '/crime-map' },
    // { id: 'analytics', label: 'Risk Prediction', icon: 'fas fa-chart-bar', route: '/risk-prediction' },
    { id: 'resources', label: 'Emergency Contacts', icon: 'fas fa-shield-alt', route: '/emergency' },
    { id: 'video', label: 'Project Video', icon: 'fas fa-video', route: '/about-project' }
  ];

  const handleNavClick = (item, e) => {
    e.preventDefault();
    setActiveNav(item.id);
    navigate(item.route);
    setIsMobileMenuOpen(false);
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen((prev) => !prev);
  };

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Lock body scroll when mobile menu or logo popup open
  useEffect(() => {
    if (isMobileMenuOpen || isLogoPopupOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isMobileMenuOpen, isLogoPopupOpen]);

  const toggleSearch = () => {
    setIsSearchOpen(!isSearchOpen);
    if (!isSearchOpen) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 400);
    } else {
      setSearchQuery('');
      setShowSearchDropdown(false);
    }
  };

  const handleSearchResultSelect = (result) => {
    navigate(result.route);
    
    if (result.type === 'area') {
      setTimeout(() => {
        onAreaSelect?.(result.value.toLowerCase().replace(/\s+/g, '-'));
      }, 100);
    } else if (result.type === 'crime') {
      setTimeout(() => {
        onCrimeSelect?.(result.value.toLowerCase());
      }, 100);
    }

    setSearchQuery('');
    setShowSearchDropdown(false);
    setIsSearchOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchDropdownRef.current && !searchDropdownRef.current.contains(event.target) &&
          searchInputRef.current && !searchInputRef.current.contains(event.target)) {
        setShowSearchDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <>
      <header
        className={`header ${isScrolled ? 'scrolled' : ''} ${isSearchOpen ? 'search-open' : ''}`}
        ref={navbarRef}
      >
        <div className="nav-container">
          {/* Enhanced Logo Section — icon click opens popup, text navigates home */}
          <div className="logo-section">
            <button
              type="button"
              className="logo-brand logo-brand-button"
              onClick={() => setIsLogoPopupOpen(true)}
              aria-label="View SafeVision logo"
            >
              <SafeVisionLogo size={42} className="logo-svg" />
            </button>
            <Link to="/" className="logo-text">
              <span className="logo-main">SafeVision</span>
              <span className="logo-sub">Spatial Analysis & Visualization</span>
            </Link>
          </div>

          {/* Desktop-only navigation rail */}
          <nav className="main-nav">
            <div className="nav-rail">
              {navItems.map((item) => (
                <Link
                  key={item.id}
                  to={item.route}
                  className={`nav-item ${activeNav === item.id ? 'active' : ''}`}
                  onClick={(e) => handleNavClick(item, e)}
                >
                  <div className="nav-orb">
                    <i className={item.icon}></i>
                  </div>
                  <span className="nav-label">{item.label}</span>
                </Link>
              ))}
            </div>
          </nav>

          {/* Enhanced Action Section */}
          <div className="action-section">
            <div className="live-status-pill" title="Live monitoring active">
              <span className="live-status-dot"></span>
              <span className="live-status-text">LIVE</span>
            </div>

            <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
              <i className={isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'}></i>
            </button>

            <button className="login-btn" onClick={showLoginModal}>
              <i className="fas fa-user"></i>
              <span className="login-text">Login</span>
            </button>

            <button
              className={`mobile-trigger ${isMobileMenuOpen ? 'active' : ''}`}
              onClick={toggleMobileMenu}
              aria-label="Toggle navigation menu"
              aria-expanded={isMobileMenuOpen}
            >
              <i className={`fas ${isMobileMenuOpen ? 'fa-times' : 'fa-bars'}`}></i>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer — rendered OUTSIDE <header> so it escapes the header's
          backdrop-filter containing block (which would otherwise trap position:fixed) */}
      {isMobileMenuOpen && (
        <div
          className="mobile-nav-overlay"
          onClick={() => setIsMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`mobile-drawer ${isMobileMenuOpen ? 'mobile-open' : ''}`}
        aria-hidden={!isMobileMenuOpen}
      >
        <div className="mobile-drawer-header">
          <div className="mobile-drawer-brand">
            <div className="mobile-drawer-logo">
              <SafeVisionLogo size={42} />
            </div>
            <div>
              <div className="mobile-drawer-title">SafeVision</div>
              <div className="mobile-drawer-subtitle">Spatial Visualytics</div>
            </div>
          </div>
          <button
            className="mobile-drawer-close"
            onClick={() => setIsMobileMenuOpen(false)}
            aria-label="Close menu"
          >
            <i className="fas fa-times"></i>
          </button>
        </div>

        <div className="mobile-drawer-nav">
          {navItems.map((item) => (
            <Link
              key={item.id}
              to={item.route}
              className={`mobile-drawer-item ${activeNav === item.id ? 'active' : ''}`}
              onClick={(e) => handleNavClick(item, e)}
            >
              <span className="mobile-drawer-icon">
                <i className={item.icon}></i>
              </span>
              <span className="mobile-drawer-label">{item.label}</span>
              <i className="fas fa-chevron-right mobile-drawer-chevron"></i>
            </Link>
          ))}

        </div>

        <div className="mobile-drawer-footer">
          <button
            className="mobile-drawer-action mobile-drawer-action--primary"
            onClick={() => { setIsMobileMenuOpen(false); showLoginModal && showLoginModal(); }}
          >
            <i className="fas fa-user"></i>
            <span>Login / Sign In</span>
          </button>
          <button
            className="mobile-drawer-action mobile-drawer-action--secondary"
            onClick={toggleTheme}
          >
            <i className={isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'}></i>
            <span>{isDarkTheme ? 'Light Theme' : 'Dark Theme'}</span>
          </button>
        </div>
      </aside>
      {/* Ultra Modern Hero Section - Only show on home page */}
      {location.pathname === '/' && (
        <section className="hero" id="home">
          <div className="hero-bg">
            <div className="hero-gradient"></div>
            <div className="hero-particles">
              {generateParticles()}
            </div>
          </div>

          <div className="hero-container">
            <div className="hero-content">
              <div className="hero-badge">
                <i className="fas fa-shield-alt"></i>
                <span>SafeVision Platform</span>
              </div>

              <h1 className="hero-title">
                <span className="title-line">Spatial Visualytics</span>
              </h1>

              <div className="hero-subtitle">
                Reported Incidents in Lahore
              </div>

              <div className="hero-urdu">
                <span>سیف ویژن — لاہور میں رپورٹ شدہ واقعات کا تجزیاتی نقشہ اور بصری نمائش</span>
              </div>

              <p className="hero-description">
                Advanced spatial analysis platform visualizing crime patterns, predicting risks, 
                and enhancing urban safety through data-driven intelligence.
              </p>

              <div className="hero-actions">
                <Link to="/crime-map" className="cta-primary">
                  <i className="fas fa-map-marked-alt"></i>
                  <span>Explore Crime Map</span>
                </Link>
                <Link to="/risk-prediction" className="cta-secondary">
                  <i className="fas fa-chart-network"></i>
                  <span>View AI Analytics</span>
                </Link>
              </div>

              <div className="hero-stats">
                <div className="stat">
                  <span className="stat-number">{projectStats.incidentsAnalyzed}</span>
                  <span className="stat-label">Incidents Analyzed</span>
                </div>
                <div className="stat">
                  <span className="stat-number">{projectStats.spatialCoverage}</span>
                  <span className="stat-label">Spatial Coverage</span>
                </div>
                <div className="stat">
                  <span className="stat-number">{projectStats.dataYears}</span>
                  <span className="stat-label">Data Years</span>
                </div>
                <div className="stat">
                  <span className="stat-number">{projectStats.predictionAccuracy}</span>
                  <span className="stat-label">Prediction Accuracy</span>
                </div>
              </div>
            </div>

            <div className="hero-visual">
              <div className="visual-container">
                <div className="earth-sphere">
                  <div className="map-grid"></div>
                  <div className="scanning-line"></div>
                  
                  {/* Floating Cards */}
                  <div className="floating-card card-1">
                    <div className="card-icon"><i className="fas fa-shield-check"></i></div>
                    <div className="card-content">
                      <h3>Safe Zone</h3>
                      <p>Model Town</p>
                    </div>
                  </div>

                  <div className="floating-card card-2">
                    <div className="card-icon"><i className="fas fa-brain"></i></div>
                    <div className="card-content">
                      <h3>AI Analysis</h3>
                      <p>Risk Level: Low</p>
                    </div>
                  </div>

                  <div className="floating-card card-3">
                    <div className="card-icon"><i className="fas fa-map-marker-alt"></i></div>
                    <div className="card-content">
                      <h3>Live Tracking</h3>
                      <p>Active Monitoring</p>
                    </div>
                  </div>

                  <div className="floating-card card-4">
                    <div className="card-icon"><i className="fas fa-bolt"></i></div>
                    <div className="card-content">
                      <h3>Real-time</h3>
                      <p>Updates: Live</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Logo Popup — clickable logo opens a big preview */}
      {isLogoPopupOpen && (
        <div
          className="logo-popup-overlay"
          onClick={() => setIsLogoPopupOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-label="SafeVision brand"
        >
          <button
            className="logo-popup-close"
            onClick={() => setIsLogoPopupOpen(false)}
            aria-label="Close"
          >
            <i className="fas fa-times"></i>
          </button>
          <div className="logo-popup-content" onClick={(e) => e.stopPropagation()}>
            <div className="logo-popup-frame">
              <SafeVisionLogo size={280} />
            </div>
            <h2 className="logo-popup-title">SafeVision</h2>
            <p className="logo-popup-tagline">Spatial Analysis &amp; Visualization</p>
            <p className="logo-popup-desc">
              AI-powered crime intelligence platform delivering real-time risk insights,
              hotspot prediction, and community safety analytics across Lahore.
            </p>
          </div>
        </div>
      )}
    </>
  );
};

export default Header;

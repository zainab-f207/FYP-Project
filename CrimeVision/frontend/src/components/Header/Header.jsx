// src/components/Header/Header.js
import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import './Header2.css';
import apiService from '../../services/apiService_updated';
import SafeVisionLogo from '../../../../../branding/safevision/concept4.svg';

const Header = ({ toggleSidebar, showLoginModal, showReportModal, onAreaSelect, onCrimeSelect }) => {
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [areas, setAreas] = useState(['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi', 'Faisalabad', 'Multan', 'Peshawar', 'Quetta', 'Sialkot', 'Gujranwala']);
  const [crimeTypes, setCrimeTypes] = useState(['Murder', 'Theft', 'Robbery', 'Burglary', 'Assault', 'Kidnapping', 'Fraud', 'Drug Trafficking', 'Terrorism', 'Cyber Crime']);
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeNav, setActiveNav] = useState('home');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
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
  };

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
          {/* Enhanced Logo Section */}
          <Link to="/" className="logo-section">
            <div className="logo-orbital">
              <div className="logo-core">
                <img src={SafeVisionLogo} alt="SafeVision" className="logo-img" />
              </div>
            </div>
            <div className="logo-text">
              <span className="logo-main">SafeVision</span>
              <span className="logo-sub">Spatial Analysis & Visualization</span>
            </div>
          </Link>

          {/* Enhanced Navigation */}
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
            <button className="theme-toggle" onClick={toggleTheme}>
              <i className={isDarkTheme ? 'fas fa-sun' : 'fas fa-moon'}></i>
            </button>

            <button
              className={`search-btn ${isSearchOpen ? 'active' : ''}`}
              onClick={toggleSearch}
            >
              <i className="fas fa-search"></i>
            </button>

            <button className="login-btn" onClick={showLoginModal}>
              <i className="fas fa-user"></i>
              <span className="login-text">Login</span>
            </button>

            <button className="mobile-trigger" onClick={toggleSidebar}>
              <div className="hamburger">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </button>
          </div>
        </div>
        {/* Add Search Panel - placed inside header so it opens directly under the nav */}
        <div className={`search-panel ${isSearchOpen ? 'open' : ''}`}>
            <div className="search-container">
              <div className="search-field-container">
                <div className="search-field">
                  <i className="fas fa-search search-icon"></i>
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search areas, crime types, incidents..."
                    ref={searchInputRef}
                    value={searchQuery}
                    onChange={handleSearchInput}
                    onFocus={() => searchQuery.length >= 1 && setShowSearchDropdown(true)}
                  />
                  <button className="search-close" onClick={() => {
                    setIsSearchOpen(false);
                    setSearchQuery('');
                    setShowSearchDropdown(false);
                  }}>
                    <i className="fas fa-times"></i>
                  </button>
                </div>

                {/* Search Results Dropdown */}
                {showSearchDropdown && (
                  <div className="search-dropdown" ref={searchDropdownRef}>
                    <div className="dropdown-content">
                      {searchResults.length > 0 ? (
                        <>
                          {Object.entries(
                            searchResults.reduce((groups, result) => {
                              if (!groups[result.category]) groups[result.category] = [];
                              groups[result.category].push(result);
                              return groups;
                            }, {})
                          ).map(([category, items]) => (
                            <div key={category} className="result-category">
                              <div className="category-header">
                                <i className={`fas fa-${category === 'Areas' ? 'map-marker-alt' : category === 'Crime Types' ? 'exclamation-triangle' : category === 'Pages' ? 'file-alt' : 'star'}`}></i>
                                {category}
                              </div>
                              <div className="category-items">
                                {items.map((item, index) => (
                                  <div
                                    key={index}
                                    className="result-item"
                                    onClick={() => handleSearchResultSelect(item)}
                                  >
                                    <i className={`fas fa-${item.type === 'area' ? 'location-arrow' : item.type === 'crime' ? 'exclamation-circle' : item.type === 'page' ? 'link' : 'bolt'}`}></i>
                                    <span>{item.display}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </>
                      ) : searchQuery.length >= 1 && (
                        <div className="no-results">
                          <i className="fas fa-search"></i>
                          <span>No results found for "{searchQuery}"</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Access Section */}
              <div className="quick-access">
                <div className="quick-header">Quick Access</div>
                <div className="quick-grid">
                  <Link to="/crime-map" className="quick-item" onClick={() => setIsSearchOpen(false)}>
                    <i className="fas fa-map-marked-alt"></i>
                    <span>Interactive Maps</span>
                  </Link>
                  <Link to="/risk-prediction" className="quick-item" onClick={() => setIsSearchOpen(false)}>
                    <i className="fas fa-chart-network"></i>
                    <span>AI Analytics</span>
                  </Link>
                  <Link to="/emergency" className="quick-item" onClick={() => setIsSearchOpen(false)}>
                    <i className="fas fa-shield-alt"></i>
                    <span>Safety Resources</span>
                  </Link>
                  <Link to="/about-project" className="quick-item" onClick={() => setIsSearchOpen(false)}>
                    <i className="fas fa-video"></i>
                    <span>Project Video</span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
      </header>
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
    </>
  );
};

export default Header;

// src/components/Sidebar/Sidebar.js
import React, { useState, useRef, useEffect } from 'react';
import './Sidebar.css';
import apiService from '../../services/api';

const Sidebar = ({ isOpen, closeSidebar, showLoginModal, showReportModal, onAreaSelect, onCrimeSelect }) => {
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [areas, setAreas] = useState([]);
  const [crimeTypes, setCrimeTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const searchInputRef = useRef(null);
  const searchDropdownRef = useRef(null);

  // Search data - will be populated from API
  const searchData = {
    areas: areas,
    crimes: crimeTypes,
    tips: [
      'Night Safety', 'Emergency Contacts', 'Home Security',
      'Vehicle Safety', 'Financial Safety', 'Community Awareness'
    ]
  };

  // Fetch areas and crime types on component mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [areasData, crimeTypesData] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes()
        ]);
        setAreas(areasData);
        setCrimeTypes(crimeTypesData);
      } catch (error) {
        console.error('Error fetching search data:', error);
        // Fallback to empty arrays if API fails
        setAreas([]);
        setCrimeTypes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Toggle dropdown
  const toggleDropdown = (dropdownName) => {
    setActiveDropdown(activeDropdown === dropdownName ? null : dropdownName);
  };

  // Perform search
  const performSearch = (query) => {
    if (!query || query.length < 1) {
      return [];
    }
    
    const results = [];
    const lowercaseQuery = query.toLowerCase();
    
    // Search areas
    searchData.areas.forEach(area => {
      if (area.toLowerCase().includes(lowercaseQuery)) {
        results.push({
          type: 'area',
          value: area,
          display: area,
          category: 'Areas'
        });
      }
    });
    
    // Search crimes
    searchData.crimes.forEach(crime => {
      if (crime.toLowerCase().includes(lowercaseQuery)) {
        results.push({
          type: 'crime',
          value: crime,
          display: crime,
          category: 'Crime Types'
        });
      }
    });
    
    // Search tips
    searchData.tips.forEach(tip => {
      if (tip.toLowerCase().includes(lowercaseQuery)) {
        results.push({
          type: 'tip',
          value: tip.toLowerCase().replace(' ', '-'),
          display: tip,
          category: 'Safety Tips'
        });
      }
    });
    
    return results;
  };

  // Handle search input
  const handleSearchInput = (e) => {
    const query = e.target.value.trim();
    const results = performSearch(query);
    
    setSearchResults(results);
    setShowSearchDropdown(results.length > 0);
  };

  // Handle search result selection
  const handleSearchResultSelect = (result) => {
    if (result.type === 'area') {
      // Scroll to prediction section
      document.getElementById('prediction')?.scrollIntoView({ behavior: 'smooth' });
      // Auto-select area in prediction tool
      if (onAreaSelect) {
        onAreaSelect(result.value.toLowerCase().replace(/\s+/g, '-'));
      }
    } else if (result.type === 'crime') {
      // Scroll to prediction section
      document.getElementById('prediction')?.scrollIntoView({ behavior: 'smooth' });
      // Auto-select crime type in prediction tool
      if (onCrimeSelect) {
        onCrimeSelect(result.value.toLowerCase());
      }
    }

    // Clear search input
    if (searchInputRef.current) {
      searchInputRef.current.value = '';
    }
    setShowSearchDropdown(false);
    // Do not close sidebar on search selection to keep dropdown visible
    // closeSidebar();
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
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Scroll to tip function
  const scrollToTip = (tipId) => {
    const tipElement = document.getElementById(tipId);
    if (tipElement) {
      tipElement.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });

      // Add highlight effect
      tipElement.style.boxShadow = '0 0 0 3px var(--accent-blue)';
      setTimeout(() => {
        tipElement.style.boxShadow = '';
      }, 2000);
    }
    closeSidebar();
  };

  return (
    <div className={`sidebar ${isOpen ? 'active' : ''}`} id="sidebar">
      <button className="sidebar-close" onClick={closeSidebar}>
        <i className="fas fa-times"></i>
      </button>
      
      {/* Mobile Search Bar in Sidebar */}
      <div className="sidebar-search-container">
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            id="sidebarSearchInput"
            placeholder="Search areas or crimes..."
            ref={searchInputRef}
            onChange={handleSearchInput}
          />
          <i className="fas fa-search"></i>
          <button className="mobile-voice-search" id="sidebarVoiceSearch">
            <i className="fas fa-microphone"></i>
          </button>
        </div>
      </div>

      {/* Search Dropdown - positioned outside sidebar to avoid overflow clipping */}
      {showSearchDropdown && (
        <div id="sidebarSearchDropdown" className={`search-dropdown ${showSearchDropdown ? 'show' : ''}`} ref={searchDropdownRef}>
          {searchResults.length > 0 ? (
            <>
              {Object.entries(
                searchResults.reduce((groups, result) => {
                  if (!groups[result.category]) groups[result.category] = [];
                  groups[result.category].push(result);
                  return groups;
                }, {})
              ).map(([category, items]) => (
                <div key={category}>
                  <div className="search-header">{category}</div>
                  {items.map((item, index) => (
                    <div
                      key={index}
                      className="search-item"
                      onClick={() => handleSearchResultSelect(item)}
                    >
                      {item.display}
                    </div>
                  ))}
                </div>
              ))}
            </>
          ) : (
            <div className="search-item">No results found</div>
          )}
        </div>
      )}

      <div className="sidebar-links">
        <a href="#home" onClick={closeSidebar}>
          <i className="fas fa-home"></i>
          <span>Home</span>
        </a>

        {/* Features Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'features' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('features')}>
            <i className="fas fa-star"></i>
            <span>Features</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#features" onClick={closeSidebar}>All Features</a>
            <a href="#features" onClick={closeSidebar}>Crime Maps</a>
            <a href="#features" onClick={closeSidebar}>Risk Prediction</a>
            <a href="#features" onClick={closeSidebar}>Smart Alerts</a>
          </div>
        </div>

        {/* Safety Tips Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'safety-tips' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('safety-tips')}>
            <i className="fas fa-shield-alt"></i>
            <span>Safety Tips</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#safety-tips" onClick={closeSidebar}>All Tips</a>
            <a href="#safety-tips" onClick={() => scrollToTip('night')}>Night Safety</a>
            <a href="#safety-tips" onClick={() => scrollToTip('emergency')}>Emergency Contacts</a>
            <a href="#safety-tips" onClick={() => scrollToTip('home')}>Home Security</a>
            <a href="#safety-tips" onClick={() => scrollToTip('vehicle')}>Vehicle Safety</a>
            <a href="#safety-tips" onClick={() => scrollToTip('financial')}>Financial Safety</a>
            <a href="#safety-tips" onClick={() => scrollToTip('community')}>Community Awareness</a>
          </div>
        </div>

        {/* News Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'news' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('news')}>
            <i className="fas fa-newspaper"></i>
            <span>News</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#news" onClick={closeSidebar}>All News</a>
            <a href="#news" onClick={closeSidebar}>Recent Updates</a>
            <a href="#news" onClick={closeSidebar}>Crime Prevention</a>
            <a href="#news" onClick={closeSidebar}>Community Programs</a>
            <a href="#news" onClick={closeSidebar}>Police Initiatives</a>
          </div>
        </div>

        {/* Risk Check Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'risk-check' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('risk-check')}>
            <i className="fas fa-chart-line"></i>
            <span>Risk Check</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#prediction" onClick={closeSidebar}>Area Safety</a>
            <a href="#prediction" onClick={closeSidebar}>Personal Assessment</a>
            <a href="#prediction" onClick={closeSidebar}>Route Planning</a>
          </div>
        </div>

        {/* Crime Map Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'crime-map' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('crime-map')}>
            <i className="fas fa-map"></i>
            <span>Crime Map</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#map" onClick={closeSidebar}>Map View</a>
            <a href="#map" onClick={closeSidebar}>Heatmap</a>
            <a href="#map" onClick={closeSidebar}>Risk Zones</a>
            <a href="#map" onClick={closeSidebar}>Safe Areas</a>
          </div>
        </div>

        {/* Statistics Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'statistics' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('statistics')}>
            <i className="fas fa-chart-pie"></i>
            <span>Statistics</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#stats" onClick={closeSidebar}>Overview</a>
            <a href="#stats" onClick={closeSidebar}>Monthly Trends</a>
            <a href="#stats" onClick={closeSidebar}>Crime Types</a>
            <a href="#stats" onClick={closeSidebar}>Area Comparison</a>
            <a href="#stats" onClick={closeSidebar}>Yearly Reports</a>
          </div>
        </div>

        {/* Testimonials Dropdown */}
        <div className={`sidebar-dropdown ${activeDropdown === 'testimonials' ? 'active' : ''}`}>
          <button className="sidebar-dropdown-toggle" onClick={() => toggleDropdown('testimonials')}>
            <i className="fas fa-comments"></i>
            <span>Reviews</span>
            <i className="fas fa-chevron-down dropdown-arrow"></i>
          </button>
          <div className="sidebar-dropdown-content">
            <a href="#testimonials" onClick={closeSidebar}>All Reviews</a>
            <a href="#testimonials" onClick={closeSidebar}>User Testimonials</a>
            <a href="#testimonials" onClick={closeSidebar}>Community Feedback</a>
          </div>
        </div>

        <a href="#" onClick={showReportModal}>
          <i className="fas fa-plus"></i>
          <span>Report Crime</span>
        </a>
        <a href="#" onClick={showLoginModal}>
          <i className="fas fa-user"></i>
          <span>Login</span>
        </a>
      </div>
    </div>
  );
};

export default Sidebar;
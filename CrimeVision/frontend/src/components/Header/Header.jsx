// src/components/Header/Header.js
import React, { useState, useRef, useEffect } from 'react';
import './Header.css';
import apiService from '../../services/api';

const Header = ({ toggleSidebar, showLoginModal, showReportModal, onAreaSelect, onCrimeSelect }) => {
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
        console.log('Starting to fetch data for header...');
        const [areasResponse, crimeTypesResponse] = await Promise.all([
          apiService.getAreas(),
          apiService.getCrimeTypes()
        ]);
        
        console.log('Raw areas response:', areasResponse);
        console.log('Raw crime types response:', crimeTypesResponse);
        
        // Extract the arrays from the response objects
        const areasData = areasResponse.areas || [];
        const crimeTypesData = crimeTypesResponse.crime_types || [];
        
        console.log('Processed areas data:', areasData);
        console.log('Processed crime types data:', crimeTypesData);
        
        setAreas(areasData);
        setCrimeTypes(crimeTypesData);
      } catch (error) {
        console.error('Error fetching search data:', error);
        setAreas([]);
        setCrimeTypes([]);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

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

  return (
    <header className="header">
      <div className="navbar">
        <div className="logo">
          <div className="logo-icon">
            <i className="fas fa-shield-alt"></i>
          </div>
          <span>CrimeVision Pakistan</span>
        </div>

        <div className="desktop-nav">
          <div className="nav-item">
            <a href="#home" className="nav-link">Home</a>
          </div>
          
          <div className="nav-item">
            <a href="#features" className="nav-link">Features <i className="fas fa-chevron-down"></i></a>
            <div className="dropdown-menu">
              <a href="#features" className="dropdown-item">All Features</a>
              <a href="#" className="dropdown-item">Crime Maps</a>
              <a href="#" className="dropdown-item">Risk Prediction</a>
              <a href="#" className="dropdown-item">Smart Alerts</a>
            </div>
          </div>
          
          <div className="nav-item">
            <a href="#safety-tips" className="nav-link">Safety Tips <i className="fas fa-chevron-down"></i></a>
            <div className="dropdown-menu">
              <a href="#safety-tips" className="dropdown-item">All Tips</a>
              <a href="#safety-tips" className="dropdown-item">Night Safety</a>
              <a href="#safety-tips" className="dropdown-item">Emergency Contacts</a>
              <a href="#safety-tips" className="dropdown-item">Home Security</a>
              <a href="#safety-tips" className="dropdown-item">Vehicle Safety</a>
              <a href="#safety-tips" className="dropdown-item">Financial Safety</a>
              <a href="#safety-tips" className="dropdown-item">Community Awareness</a>
            </div>
          </div>

          <div className="nav-item">
            <a href="#news" className="nav-link">News <i className="fas fa-chevron-down"></i></a>
            <div className="dropdown-menu">
              <a href="#news" className="dropdown-item">All News</a>
              <a href="#news" className="dropdown-item">Recent Updates</a>
              <a href="#news" className="dropdown-item">Crime Prevention</a>
              <a href="#news" className="dropdown-item">Community Programs</a>
              <a href="#news" className="dropdown-item">Police Initiatives</a>
            </div>
          </div>

          <div className="nav-item">
            <a href="#prediction" className="nav-link">Risk Check <i className="fas fa-chevron-down"></i></a>
            <div className="dropdown-menu">
              <a href="#prediction" className="dropdown-item">Area Safety</a>
              <a href="#" className="dropdown-item">Personal Assessment</a>
              <a href="#" className="dropdown-item">Route Planning</a>
            </div>
          </div>

          <div className="nav-item">
            <a href="#map" className="nav-link">Crime Map <i className="fas fa-chevron-down"></i></a>
            <div className="dropdown-menu">
              <a href="#map" className="dropdown-item">Map View</a>
              <a href="#map" className="dropdown-item">Heatmap</a>
              <a href="#map" className="dropdown-item">Risk Zones</a>
              <a href="#map" className="dropdown-item">Safe Areas</a>
            </div>
          </div>

          <div className="nav-item">
            <a href="#stats" className="nav-link">Statistics <i className="fas fa-chevron-down"></i></a>
            <div className="dropdown-menu">
              <a href="#stats" className="dropdown-item">Overview</a>
              <a href="#stats" className="dropdown-item">Monthly Trends</a>
              <a href="#stats" className="dropdown-item">Crime Types</a>
              <a href="#stats" className="dropdown-item">Area Comparison</a>
              <a href="#stats" className="dropdown-item">Yearly Reports</a>
            </div>
          </div>

          <div className="search-container">
            <i className="fas fa-search search-icon"></i>
            <input 
              type="text" 
              className="search-input" 
              id="mainSearchInput" 
              placeholder="Search areas or crimes..."
              ref={searchInputRef}
              onChange={handleSearchInput}
            />
            <button className="voice-search-btn" id="voiceSearchBtn">
              <i className="fas fa-microphone"></i>
            </button>
            <i className="fas fa-circle recording-indicator" id="recordingIndicator"></i>
            
            {showSearchDropdown && (
              <div className="search-dropdown show" ref={searchDropdownRef}>
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
          </div>
        </div>

        <div className="nav-actions">
          <a href="#" className="btn-report" onClick={showReportModal}>
            <i className="fas fa-plus"></i> Report Crime
          </a>
          {/* Removed Test Model button as per user request */}
          {/* <a href="#" className="btn-test" onClick={showTestModelModal}>
            <i className="fas fa-flask"></i> Test Model
          </a> */}
          <a href="#" className="btn-login" onClick={showLoginModal}>Login</a>
        </div>

        <button className="mobile-menu-btn" id="mobileMenuBtn" onClick={toggleSidebar}>
          <i className="fas fa-bars"></i>
        </button>
      </div>
    </header>
  );
};

export default Header;
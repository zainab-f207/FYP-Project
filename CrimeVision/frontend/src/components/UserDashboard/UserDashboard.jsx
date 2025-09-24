import styles from './UserDashboard.module.css';
import './UserDropdown.css';
import CrimeMap from '../CrimeMap/CrimeMap_updated';
import ProfileModal from './ProfileModal';
import PredictionSection from './PredictionSection';
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext_updated';

const UserDashboard = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [selectedArea, setSelectedArea] = useState('');
  const [selectedCrimeType, setSelectedCrimeType] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [showMap, setShowMap] = useState(false);
  const { user, logout } = useAuth();

  useEffect(() => {
    const fadeElements = document.querySelectorAll(`.${styles.fadeIn}`);

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add(styles.visible);
        }
      });
    }, { threshold: 0.1 });

    fadeElements.forEach(element => {
      observer.observe(element);
    });

    return () => {
      fadeElements.forEach(element => {
        observer.unobserve(element);
      });
    };
  }, []);

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const toggleMobileSidebar = () => {
    setMobileSidebarOpen(!mobileSidebarOpen);
  };

  const closeMobileSidebar = () => {
    setMobileSidebarOpen(false);
  };

  const toggleDropdown = () => {
    setDropdownOpen(!dropdownOpen);
  };

  const openProfileModal = () => {
    setProfileModalOpen(true);
    setDropdownOpen(false);
  };

  const closeProfileModal = () => {
    setProfileModalOpen(false);
  };

  const handlePredictionComplete = (prediction) => {
    console.log('Prediction completed:', prediction);
    setPredictionResult(prediction);
    setSelectedArea(prediction.area);
    setSelectedCrimeType(prediction.crimeType);
    setSelectedDate(prediction.date);
    setShowMap(false);
  };

  const handleViewOnMap = () => {
    setShowMap(!showMap);
  };

  const formatAreaName = (name) => {
    return name.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className={styles.appContainer}>
      <button className={styles.mobileToggle} onClick={toggleMobileSidebar}>
        <i className="fas fa-bars"></i>
      </button>

      <div className={`${styles.sidebar} ${sidebarCollapsed ? styles.sidebarCollapsed : ''} ${mobileSidebarOpen ? styles.sidebarMobileOpen : ''}`}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logo}>
            <i className="fas fa-shield-alt"></i>
          </div>
          <h3>CrimeVision</h3>
        </div>

        <div className={styles.userProfileSidebar}>
          <img src={user?.profile_picture || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-1.2.1&auto=format&fit=crop&w=200&q=80"} alt="User" />
          <div className={styles.userInfoSidebar}>
            <h4>{user?.username || 'User Name'}</h4>
            <p>{user?.home_area ? `${user.home_area}, Pakistan` : 'Location not set'}</p>
          </div>
        </div>

        <ul className={styles.sidebarMenu}>
          <li>
            <a href="#" className={styles.active} onClick={closeMobileSidebar}>
              <i className="fas fa-home"></i>
              <span>Dashboard</span>
            </a>
          </li>
          <li>
            <a href="#risk-prediction" onClick={closeMobileSidebar}>
              <i className="fas fa-robot"></i>
              <span>Risk Prediction</span>
            </a>
          </li>
          <li>
            <a href="#alerts" onClick={closeMobileSidebar}>
              <i className="fas fa-bell"></i>
              <span>Alerts & Notifications</span>
            </a>
          </li>
          <li>
            <a href="#reports" onClick={closeMobileSidebar}>
              <i className="fas fa-clipboard-list"></i>
              <span>Crime Reports</span>
            </a>
          </li>
          <li>
            <a href="#history" onClick={closeMobileSidebar}>
              <i className="fas fa-history"></i>
              <span>History</span>
            </a>
          </li>
          <li>
            <a href="#settings" onClick={closeMobileSidebar}>
              <i className="fas fa-cog"></i>
              <span>Settings</span>
            </a>
          </li>
        </ul>

        <div className={styles.sidebarFooter}>
          <a href="#" onClick={logout} style={{color: 'white', textDecoration: 'none', display: 'block', marginBottom: '15px'}}>
            <i className="fas fa-sign-out-alt"></i>
            <span>Logout</span>
          </a>
          <button className={styles.toggleBtn} onClick={toggleSidebar}>
            <i className={`fas fa-chevron-${sidebarCollapsed ? 'right' : 'left'}`}></i>
          </button>
        </div>
      </div>

      <div className={`${styles.mainContent} ${sidebarCollapsed ? styles.mainContentExpanded : ''}`}>
        <div className={styles.navbar}>
          <div className={styles.searchBar}>
            <i className="fas fa-search"></i>
            <input type="text" placeholder="Search for locations or crimes..." />
          </div>
          <div className={styles.navbarActions}>
            <div className={styles.notificationBtn}>
              <i className="fas fa-bell"></i>
              <span className={styles.notificationBadge}>3</span>
            </div>
            <div className="user-profile" onClick={toggleDropdown} tabIndex={0} onBlur={() => setDropdownOpen(false)} style={{position: 'relative', zIndex: 10000}}>
              <div className={styles.userProfile}>
                <img src={user?.profile_picture || "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?ixlib=rb-1.2.1&auto=format&fit=crop&w=200&q=80"} alt="User" />
                <div className={styles.userInfo}>
                  <div>{user?.username || 'User Name'}</div>
                  <small className={styles.role}>{user?.home_area ? `${user.home_area}, Pakistan` : 'Location not set'}</small>
                </div>
                <span className="dropdown-arrow">▼</span>
              </div>
              {dropdownOpen && (
                <div className="user-dropdown">
                  <div className="dropdown-item" onClick={openProfileModal}>
                    <i className="fas fa-user"></i> Profile
                  </div>
                  <div className="dropdown-item" onClick={logout}>
                    <i className="fas fa-sign-out-alt"></i> Logout
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Risk Prediction Tool */}
        <div id="risk-prediction">
          <PredictionSection onPredictionComplete={handlePredictionComplete} />
        </div>

        {predictionResult && (
          <>
            <div className={`${styles.predictionResultCard} ${styles.fadeIn}`}>
              <div className={styles.predictionResultHeader}>
                <h3>Prediction Results</h3>
                <button className={styles.viewOnMapBtn} onClick={handleViewOnMap}>
                  <i className="fas fa-map-marker-alt"></i> {showMap ? 'Hide Map' : 'View on Map'}
                </button>
              </div>
              
              <div className={styles.predictionDetails}>
                <div className={styles.riskScoreDisplay}>
                  <div className={styles.riskMeter}>
                    <svg width="120" height="120" viewBox="0 0 120 120">
                      <circle cx="60" cy="60" r="54" fill="none" stroke="#eee" strokeWidth="8" />
                      <circle 
                        cx="60" cy="60" r="54" fill="none" 
                        stroke={predictionResult.riskLevel === 'High' ? '#dc2626' : predictionResult.riskLevel === 'Medium' ? '#f59e0b' : '#22c55e'}
                        strokeWidth="8"
                        strokeDasharray="339.3"
                        strokeDashoffset={339.3 - (predictionResult.riskPercentage / 100) * 339.3}
                        transform="rotate(-90 60 60)"
                      />
                      <text x="60" y="65" textAnchor="middle" fontSize="14" fill="var(--text-dark)" fontWeight="bold">
                        {predictionResult.riskPercentage}%
                      </text>
                    </svg>
                  </div>
                  <div className={`${styles.riskValue} ${styles[predictionResult.riskLevel.toLowerCase()]}`}>
                    {predictionResult.riskLevel} Risk
                  </div>
                </div>
                
                <div className={styles.predictionInfo}>
                  <div className={styles.infoItem}>
                    <span className={styles.infoLabel}>Area:</span>
                    <span className={styles.infoValue}>{formatAreaName(predictionResult.area)}</span>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.infoLabel}>Crime Type:</span>
                    <span className={styles.infoValue}>{predictionResult.crimeType}</span>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.infoLabel}>Date:</span>
                    <span className={styles.infoValue}>{new Date(predictionResult.date).toLocaleDateString()}</span>
                  </div>
                  <div className={styles.infoItem}>
                    <span className={styles.infoLabel}>Confidence:</span>
                    <span className={styles.infoValue}>{Math.round((predictionResult.confidence || 0.8) * 100)}%</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Map Section - Only shown when user clicks "View on Map" */}
            {showMap && (
              <div className={`${styles.mapContainer} ${styles.fadeIn}`}>
                <div className={styles.mapHeader}>
                  <h3 className={styles.mapTitle}>Crime Risk Visualization</h3>
                  <div className={styles.mapControls}>
                    <div className={styles.predictionFilter}>
                      <span className={styles.filterLabel}>Showing prediction for:</span>
                      <span className={styles.filterValue}>
                        {formatAreaName(selectedArea)} • {selectedCrimeType} • {new Date(selectedDate).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className={styles.crimeMapWrapper}>
                  <CrimeMap 
                    isAuthenticated={true} 
                    showLoginModal={() => alert('Please login to access advanced features')}
                    predictionData={predictionResult}
                    hideControls={true}
                  />
                </div>
              </div>
            )}
          </>
        )}

        <DashboardCards styles={styles} />
        <AlertSection styles={styles} />
        <RecentReports styles={styles} />
      </div>
      <ProfileModal isOpen={profileModalOpen} user={user} onClose={closeProfileModal} />
    </div>
  );
};

// Sub-components (DashboardCards, AlertSection, RecentReports)
const DashboardCards = ({ styles }) => (
  <div className={styles.dashboardCards}>
    <div className={`${styles.card} ${styles.fadeIn}`}>
      <div className={styles.cardHeader}>
        <h4 className={styles.cardTitle}>Safety Score</h4>
        <i className="fas fa-shield-alt"></i>
      </div>
      <div className={styles.cardValue}>82%</div>
      <div className={`${styles.cardChange} ${styles.positive}`}>
        <i className="fas fa-arrow-up"></i> 5% improvement from last week
      </div>
    </div>
    <div className={`${styles.card} ${styles.fadeIn}`}>
      <div className={styles.cardHeader}>
        <h4 className={styles.cardTitle}>Alerts This Week</h4>
        <i className="fas fa-bell"></i>
      </div>
      <div className={styles.cardValue}>3</div>
      <div className={`${styles.cardChange} ${styles.negative}`}>
        <i className="fas fa-exclamation-circle"></i> 1 new high-risk alert
      </div>
    </div>
    <div className={`${styles.card} ${styles.fadeIn}`}>
      <div className={styles.cardHeader}>
        <h4 className={styles.cardTitle}>Safe Routes Planned</h4>
        <i className="fas fa-route"></i>
      </div>
      <div className={styles.cardValue}>12</div>
      <div className={`${styles.cardChange} ${styles.positive}`}>
        <i className="fas fa-check-circle"></i> All routes were safe
      </div>
    </div>
    <div className={`${styles.card} ${styles.fadeIn}`}>
      <div className={styles.cardHeader}>
        <h4 className={styles.cardTitle}>Nearest Safe Zone</h4>
        <i className="fas fa-map-marker-alt"></i>
      </div>
      <div className={styles.cardValue}>0.8 km</div>
      <div className={styles.cardChange}>
        <i className="fas fa-info-circle"></i> Liberty Market Police Station
      </div>
    </div>
  </div>
);

const AlertSection = ({ styles }) => (
  <div className={`${styles.alertSection} ${styles.fadeIn}`}>
    <div className={styles.alertHeader}>
      <h3 className={styles.alertTitle}>Recent Alerts</h3>
      <a href="#" className={styles.viewAll}>View All <i className="fas fa-chevron-right"></i></a>
    </div>

    <div className={styles.alertItem}>
      <div className={styles.alertIcon}>
        <i className="fas fa-exclamation-triangle"></i>
      </div>
      <div className={styles.alertContent}>
        <h4>High Risk Alert - Gulberg</h4>
        <p>Multiple theft incidents reported in the last 2 hours. Avoid the area if possible.</p>
      </div>
      <div className={styles.alertTime}>30 min ago</div>
    </div>

    <div className={styles.alertItem}>
      <div className={styles.alertIcon} style={{background: '#f9a826'}}>
        <i className="fas fa-info-circle"></i>
      </div>
      <div className={styles.alertContent}>
        <h4>Medium Risk - Model Town</h4>
        <p>Increased street crime activity detected. Stay alert in this area.</p>
      </div>
      <div className={styles.alertTime}>2 hours ago</div>
    </div>

    <div className={styles.alertItem}>
      <div className={styles.alertIcon} style={{background: '#1dd1a1'}}>
        <i className="fas fa-check-circle"></i>
      </div>
      <div className={styles.alertContent}>
        <h4>Safety Update - DHA Phase 5</h4>
        <p>Previous high-risk alert has been cleared. Area is now safe.</p>
      </div>
      <div className={styles.alertTime}>5 hours ago</div>
    </div>
  </div>
);

const RecentReports = ({ styles }) => (
  <div className={`${styles.recentReports} ${styles.fadeIn}`}>
    <div className={styles.sectionHeader}>
      <h3 className={styles.sectionTitle}>Recent Crime Reports Near You</h3>
      <a href="#" className={styles.viewAll}>View All <i className="fas fa-chevron-right"></i></a>
    </div>
    <ul className={styles.reportList}>
      <li className={styles.reportItem}>
        <div className={styles.reportInfo}>
          <div className={`${styles.reportIcon} ${styles.theft}`}>
            <i className="fas fa-gem"></i>
          </div>
          <div className={styles.reportDetails}>
            <h4>Car Theft</h4>
            <p>Gulberg III, Lahore • 2 hours ago</p>
          </div>
        </div>
        <div className={`${styles.reportStatus} ${styles.statusHigh}`}>
          HIGH RISK
        </div>
      </li>
      <li className={styles.reportItem}>
        <div className={styles.reportInfo}>
          <div className={`${styles.reportIcon} ${styles.assault}`}>
            <i className="fas fa-fist-raised"></i>
          </div>
          <div className={styles.reportDetails}>
            <h4>Street Fight</h4>
            <p>Main Boulevard, Lahore • 5 hours ago</p>
          </div>
        </div>
        <div className={`${styles.reportStatus} ${styles.statusMedium}`}>
          MEDIUM RISK
        </div>
      </li>
      <li className={styles.reportItem}>
        <div className={styles.reportInfo}>
          <div className={`${styles.reportIcon} ${styles.burglary}`}>
            <i className="fas fa-house-damage"></i>
          </div>
          <div className={styles.reportDetails}>
            <h4>House Break-in</h4>
            <p>Model Town, Lahore • 12 hours ago</p>
          </div>
        </div>
        <div className={`${styles.reportStatus} ${styles.statusHigh}`}>
          HIGH RISK
        </div>
      </li>
      <li className={styles.reportItem}>
        <div className={styles.reportInfo}>
          <div className={`${styles.reportIcon} ${styles.theft}`}>
            <i className="fas fa-mobile-alt"></i>
          </div>
          <div className={styles.reportDetails}>
            <h4>Phone Snatching</h4>
            <p>Liberty Market, Lahore • 1 day ago</p>
          </div>
        </div>
        <div className={`${styles.reportStatus} ${styles.statusMedium}`}>
          MEDIUM RISK
        </div>
      </li>
    </ul>
  </div>
);

export default UserDashboard;
import { useNavigate, useLocation } from 'react-router-dom';
import Header from '../Header/Header';
import Footer from '../Footer/Footer';
import CrimeMapInterface from '../CrimeMapInterface/CrimeMapInterface_real_insights';
import styles from './CrimeMapPage.module.css';

const CrimeMapPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Extract area from query parameters
  const queryParams = new URLSearchParams(location.search);
  const areaName = queryParams.get('area');
  const predictionData = areaName ? {
    area: areaName.replace(/-/g, ' '),
    crimeType: 'all',
    riskLevel: 'High',
    date: new Date().toISOString()
  } : null;

  return (
    <>
      <Header 
        toggleSidebar={() => {}}
        showLoginModal={() => navigate('/login')}
        showReportModal={() => {}}
        onAreaSelect={() => {}}
        onCrimeSelect={() => {}}
      />
      
      <div className={styles.pageContainer}>
      {/* Animated Background */}
      <div className={styles.animatedBackground}>
        <svg className={styles.backgroundSvg} viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="mapGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{ stopColor: '#8b5cf6', stopOpacity: 0.3 }} />
              <stop offset="100%" style={{ stopColor: '#06b6d4', stopOpacity: 0.3 }} />
            </linearGradient>
          </defs>
          
          {/* Animated map markers */}
          <g className={styles.mapMarker}>
            <circle cx="300" cy="200" r="8" fill="#8b5cf6" opacity="0.6">
              <animate attributeName="r" values="8;12;8" dur="2s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />
            </circle>
            <circle cx="300" cy="200" r="20" fill="none" stroke="#8b5cf6" strokeWidth="2" opacity="0.4">
              <animate attributeName="r" values="20;30;20" dur="2s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" />
            </circle>
          </g>
          
          <g className={styles.mapMarker}>
            <circle cx="800" cy="300" r="8" fill="#06b6d4" opacity="0.6">
              <animate attributeName="r" values="8;12;8" dur="2.5s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite" />
            </circle>
            <circle cx="800" cy="300" r="20" fill="none" stroke="#06b6d4" strokeWidth="2" opacity="0.4">
              <animate attributeName="r" values="20;30;20" dur="2.5s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.4;0;0.4" dur="2.5s" repeatCount="indefinite" />
            </circle>
          </g>
          
          <g className={styles.mapMarker}>
            <circle cx="600" cy="500" r="8" fill="#10b981" opacity="0.6">
              <animate attributeName="r" values="8;12;8" dur="3s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.6;1;0.6" dur="3s" repeatCount="indefinite" />
            </circle>
            <circle cx="600" cy="500" r="20" fill="none" stroke="#10b981" strokeWidth="2" opacity="0.4">
              <animate attributeName="r" values="20;30;20" dur="3s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.4;0;0.4" dur="3s" repeatCount="indefinite" />
            </circle>
          </g>
        </svg>
      </div>

      {/* Header Section */}
      <div className={styles.pageHeader}>
        <div className={styles.headerContent}>
          <div className={styles.iconContainer}>
            <svg className={styles.headerIcon} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="mapIconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style={{ stopColor: '#8b5cf6' }} />
                  <stop offset="100%" style={{ stopColor: '#06b6d4' }} />
                </linearGradient>
              </defs>
              
              {/* Map icon */}
              <rect x="20" y="30" width="60" height="40" rx="5" fill="none" stroke="url(#mapIconGrad)" strokeWidth="3">
                <animate attributeName="stroke-dasharray" values="0 200;200 0" dur="3s" repeatCount="indefinite" />
              </rect>
              
              {/* Location pin */}
              <path d="M50 20 C45 20 40 25 40 30 C40 37 50 50 50 50 C50 50 60 37 60 30 C60 25 55 20 50 20 Z" 
                    fill="url(#mapIconGrad)">
                <animateTransform attributeName="transform" type="translate" values="0,0;0,-5;0,0" dur="2s" repeatCount="indefinite" />
              </path>
              <circle cx="50" cy="30" r="3" fill="white" />
              
              {/* Heatmap dots */}
              <circle cx="30" cy="50" r="3" fill="#8b5cf6" opacity="0.6">
                <animate attributeName="opacity" values="0.6;1;0.6" dur="1.5s" repeatCount="indefinite" />
              </circle>
              <circle cx="50" cy="55" r="3" fill="#06b6d4" opacity="0.6">
                <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />
              </circle>
              <circle cx="70" cy="50" r="3" fill="#10b981" opacity="0.6">
                <animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite" />
              </circle>
            </svg>
          </div>
          <h1 className={styles.pageTitle}>Interactive Incident Map & Heatmap</h1>
          <p className={styles.pageSubtitle}>
            Explore real-time Incident data visualization across Lahore. Our interactive map displays FIR incidents,
            density heatmaps, and geographical patterns to help you understand safety trends in different areas.
          </p>
        </div>

        {/* Feature Cards */}
        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <i className="fas fa-fire"></i>
            </div>
            <h3>Incident Heatmap</h3>
            <p>Visualize Incident density with color-coded heat zones</p>
          </div>
          
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <i className="fas fa-map-marked-alt"></i>
            </div>
            <h3>Incident Markers</h3>
            <p>View individual FIR incidents with detailed information</p>
          </div>
          
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <i className="fas fa-filter"></i>
            </div>
            <h3>Smart Filters</h3>
            <p>Filter by crime type, date range, and area</p>
          </div>
          
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}>
              <i className="fas fa-chart-area"></i>
            </div>
            <h3>Trend Analysis</h3>
            <p>Analyze Incident patterns and temporal trends</p>
          </div>
        </div>
      </div>

      {/* Info Section */}
      <div className={styles.infoSection}>
        <div className={styles.infoCard}>
          <div className={styles.infoIcon}>
            <i className="fas fa-info-circle"></i>
          </div>
          <div className={styles.infoContent}>
            <h3>Understanding the Incident Map</h3>
            <p>
              The Incident map uses advanced visualization techniques to display Incident data across Lahore.
              Red zones indicate high Incident density, while green zones represent safer areas. Click on
              individual markers to view detailed incident information including type, date, and location.
            </p>
          </div>
        </div>

        <div className={styles.legendCard}>
          <h3>
            <i className="fas fa-palette"></i>
            Heat Map Legend
          </h3>
          <div className={styles.legendItems}>
            <div className={styles.legendItem}>
              <div className={styles.legendColor} style={{ background: '#ef4444' }}></div>
              <span>High Risk - Critical attention needed</span>
            </div>
            <div className={styles.legendItem}>
              <div className={styles.legendColor} style={{ background: '#f59e0b' }}></div>
              <span>Medium Risk - Stay cautious</span>
            </div>
            <div className={styles.legendItem}>
              <div className={styles.legendColor} style={{ background: '#10b981' }}></div>
              <span>Low Risk - Relatively safe</span>
            </div>
          </div>
        </div>
      </div>

      {/* Map Container */}
      <div className={styles.mapSection}>
        <div className={styles.mapHeader}>
          <h2>
            <i className="fas fa-globe-asia"></i>
            Live Incident Map - Lahore
          </h2>
          <div className={styles.mapBadges}>
            <span className={styles.liveBadge}>
              <span className={styles.pulsingDot}></span>
              Live Data
            </span>
            <span className={styles.updateBadge}>
              <i className="fas fa-sync-alt"></i>
              Updated Daily
            </span>
          </div>
        </div>
        
        <div className={styles.mapWrapper}>
          <CrimeMapInterface 
            predictionData={predictionData} 
            showAdditionalSections={false} 
          />
        </div>
      </div>

      {/* Statistics Section */}
      <div className={styles.statsSection}>
        <h2>Incident Statistics Overview</h2>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <div className={styles.statValue}>15,234</div>
            <div className={styles.statLabel}>Total Incidents Mapped</div>
            <div className={styles.statTrend}>
              <i className="fas fa-arrow-down"></i>
              <span>12% decrease from last month</span>
            </div>
          </div>
          
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-map-marker-alt"></i>
            </div>
            <div className={styles.statValue}>120+</div>
            <div className={styles.statLabel}>Areas Covered</div>
            <div className={styles.statTrend}>
              <i className="fas fa-check"></i>
              <span>Complete city coverage</span>
            </div>
          </div>
          
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-clock"></i>
            </div>
            <div className={styles.statValue}>Real-time</div>
            <div className={styles.statLabel}>Data Updates</div>
            <div className={styles.statTrend}>
              <i className="fas fa-sync"></i>
              <span>Synced with police database</span>
            </div>
          </div>
          
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-shield-alt"></i>
            </div>
            <div className={styles.statValue}>85%</div>
            <div className={styles.statLabel}>Data Accuracy</div>
            <div className={styles.statTrend}>
              <i className="fas fa-check-circle"></i>
              <span>Verified by authorities</span>
            </div>
          </div>
        </div>
      </div>

      {/* How to Use Section */}
      <div className={styles.howToUseSection}>
        <h2>How to Use the Incident Map</h2>
        <div className={styles.instructionsGrid}>
          <div className={styles.instructionCard}>
            <div className={styles.instructionNumber}>1</div>
            <div className={styles.instructionIcon}>
              <i className="fas fa-mouse-pointer"></i>
            </div>
            <h3>Navigate the Map</h3>
            <p>Use your mouse to pan and zoom. Click and drag to move around Lahore's different areas.</p>
          </div>
          
          <div className={styles.instructionCard}>
            <div className={styles.instructionNumber}>2</div>
            <div className={styles.instructionIcon}>
              <i className="fas fa-search-location"></i>
            </div>
            <h3>Search Locations</h3>
            <p>Use the search bar to quickly find specific areas or neighborhoods you're interested in.</p>
          </div>
          
          <div className={styles.instructionCard}>
            <div className={styles.instructionNumber}>3</div>
            <div className={styles.instructionIcon}>
              <i className="fas fa-sliders-h"></i>
            </div>
            <h3>Apply Filters</h3>
            <p>Filter crime data by type, date range, and area to focus on specific information.</p>
          </div>
          
          <div className={styles.instructionCard}>
            <div className={styles.instructionNumber}>4</div>
            <div className={styles.instructionIcon}>
              <i className="fas fa-info"></i>
            </div>
            <h3>View Details</h3>
            <p>Click on markers to see detailed information about specific FIR incidents.</p>
          </div>
        </div>
      </div>
      </div>
      
      <Footer />
    </>
  );
};

export default CrimeMapPage;

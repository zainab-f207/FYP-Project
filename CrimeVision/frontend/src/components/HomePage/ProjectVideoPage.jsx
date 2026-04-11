import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../Header/Header';
import Footer from '../Footer/Footer';
import styles from './ProjectVideoPage.module.css';

const ProjectVideoPage = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const navigate = useNavigate();

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
            <linearGradient id="videoGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{ stopColor: '#06b6d4', stopOpacity: 0.3 }} />
              <stop offset="100%" style={{ stopColor: '#8b5cf6', stopOpacity: 0.3 }} />
            </linearGradient>
          </defs>
          
          {/* Animated play button */}
          <g className={styles.playIcon}>
            <circle cx="300" cy="200" r="50" fill="url(#videoGrad1)" opacity="0.4">
              <animate attributeName="r" values="50;60;50" dur="3s" repeatCount="indefinite" />
            </circle>
            <polygon points="290,185 290,215 315,200" fill="#06b6d4" opacity="0.6">
              <animate attributeName="opacity" values="0.6;1;0.6" dur="2s" repeatCount="indefinite" />
            </polygon>
          </g>
          
          <g className={styles.playIcon}>
            <circle cx="900" cy="400" r="40" fill="url(#videoGrad1)" opacity="0.4">
              <animate attributeName="r" values="40;50;40" dur="4s" repeatCount="indefinite" />
            </circle>
            <polygon points="890,390 890,410 910,400" fill="#8b5cf6" opacity="0.6">
              <animate attributeName="opacity" values="0.6;1;0.6" dur="2.5s" repeatCount="indefinite" />
            </polygon>
          </g>
        </svg>
      </div>

      {/* Header Section */}
      <div className={styles.pageHeader}>
        <div className={styles.headerContent}>
          <div className={styles.iconContainer}>
            <svg className={styles.headerIcon} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="videoIconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style={{ stopColor: '#06b6d4' }} />
                  <stop offset="100%" style={{ stopColor: '#8b5cf6' }} />
                </linearGradient>
              </defs>
              
              {/* Video camera icon */}
              <rect x="20" y="35" width="50" height="30" rx="5" fill="url(#videoIconGrad)">
                <animate attributeName="opacity" values="1;0.7;1" dur="3s" repeatCount="indefinite" />
              </rect>
              <polygon points="70,40 85,35 85,65 70,60" fill="url(#videoIconGrad)">
                <animate attributeName="opacity" values="1;0.7;1" dur="3s" repeatCount="indefinite" />
              </polygon>
              
              {/* Recording dot */}
              <circle cx="30" cy="45" r="4" fill="#ef4444">
                <animate attributeName="opacity" values="1;0;1" dur="1.5s" repeatCount="indefinite" />
              </circle>
            </svg>
          </div>
          <h1 className={styles.pageTitle}>About SafeVision Project</h1>
          <p className={styles.pageSubtitle}>
            Discover how SafeVision is revolutionizing public safety through AI-powered crime prediction
            and real-time monitoring. Watch our comprehensive project overview and learn about the
            technology, features, and impact of our innovative safety platform.
          </p>
        </div>
      </div>

      {/* Video Section */}
      <div className={styles.videoSection}>
        <div className={styles.videoContainer}>
          <div className={styles.videoWrapper}>
            {/* Placeholder for video - replace with actual video */}
            <div className={styles.videoPlaceholder}>
              <div className={styles.playButton}>
                <i className="fas fa-play"></i>
              </div>
              <p>Project Demo Video</p>
              <span>Click to watch our comprehensive project overview</span>
            </div>
            {/* Uncomment when you have actual video */}
            {/* <iframe
              width="100%"
              height="100%"
              src="YOUR_VIDEO_URL"
              title="SafeVision Project Demo"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
            ></iframe> */}
          </div>
          
          <div className={styles.videoInfo}>
            <div className={styles.videoBadges}>
              <span className={styles.badge}>
                <i className="fas fa-clock"></i>
                8:45 Duration
              </span>
              <span className={styles.badge}>
                <i className="fas fa-eye"></i>
                1080p HD
              </span>
              <span className={styles.badge}>
                <i className="fas fa-closed-captioning"></i>
                Subtitles Available
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Section */}
      <div className={styles.tabsSection}>
        <div className={styles.tabsHeader}>
          <button 
            className={`${styles.tab} ${activeTab === 'overview' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <i className="fas fa-info-circle"></i>
            Overview
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'features' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('features')}
          >
            <i className="fas fa-star"></i>
            Key Features
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'technology' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('technology')}
          >
            <i className="fas fa-cogs"></i>
            Technology
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'impact' ? styles.activeTab : ''}`}
            onClick={() => setActiveTab('impact')}
          >
            <i className="fas fa-chart-line"></i>
            Impact
          </button>
        </div>

        <div className={styles.tabContent}>
          {activeTab === 'overview' && (
            <div className={styles.contentPanel}>
              <h2>Project Overview</h2>
              <p className={styles.leadText}>
                SafeVision is an advanced AI-powered crime prediction and monitoring system designed to enhance
                public safety in Lahore, Pakistan. Our platform combines cutting-edge machine learning algorithms
                with real-time data analysis to provide accurate crime risk predictions and safety insights.
              </p>
              
              <div className={styles.highlightsGrid}>
                <div className={styles.highlightCard}>
                  <div className={styles.highlightIcon}>
                    <i className="fas fa-bullseye"></i>
                  </div>
                  <h3>Mission</h3>
                  <p>To create safer communities through predictive analytics and real-time crime monitoring</p>
                </div>
                
                <div className={styles.highlightCard}>
                  <div className={styles.highlightIcon}>
                    <i className="fas fa-eye"></i>
                  </div>
                  <h3>Vision</h3>
                  <p>A future where technology empowers citizens with safety information and crime prevention tools</p>
                </div>
                
                <div className={styles.highlightCard}>
                  <div className={styles.highlightIcon}>
                    <i className="fas fa-users"></i>
                  </div>
                  <h3>Target Users</h3>
                  <p>Citizens, law enforcement agencies, and community safety organizations</p>
                </div>
              </div>

              <div className={styles.problemSolution}>
                <div className={styles.problemCard}>
                  <h3><i className="fas fa-exclamation-triangle"></i> The Problem</h3>
                  <ul>
                    <li>Rising crime rates in urban areas</li>
                    <li>Lack of real-time crime information for citizens</li>
                    <li>Reactive rather than proactive policing</li>
                    <li>Limited public awareness of high-risk areas</li>
                  </ul>
                </div>
                
                <div className={styles.solutionCard}>
                  <h3><i className="fas fa-lightbulb"></i> Our Solution</h3>
                  <ul>
                    <li>AI-powered crime risk prediction</li>
                    <li>Real-time crime mapping and alerts</li>
                    <li>Data-driven insights for law enforcement</li>
                    <li>Community-wide safety awareness platform</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'features' && (
            <div className={styles.contentPanel}>
              <h2>Key Features</h2>
              <p className={styles.leadText}>
                SafeVision offers a comprehensive suite of features designed to enhance public safety
                and empower users with actionable crime intelligence.
              </p>
              
              <div className={styles.featuresGrid}>
                <div className={styles.featureCard}>
                  <div className={styles.featureNumber}>1</div>
                  <div className={styles.featureIcon}>
                    <i className="fas fa-brain"></i>
                  </div>
                  <h3>AI Crime Prediction</h3>
                  <p>Advanced machine learning models predict crime risk levels for specific areas and times with 95% accuracy</p>
                  <div className={styles.featureTags}>
                    <span>Machine Learning</span>
                    <span>Predictive Analytics</span>
                  </div>
                </div>
                
                <div className={styles.featureCard}>
                  <div className={styles.featureNumber}>2</div>
                  <div className={styles.featureIcon}>
                    <i className="fas fa-map-marked-alt"></i>
                  </div>
                  <h3>Interactive Crime Map</h3>
                  <p>Real-time visualization of crime incidents with heatmap overlays and detailed incident information</p>
                  <div className={styles.featureTags}>
                    <span>Geospatial Analysis</span>
                    <span>Real-time Data</span>
                  </div>
                </div>
                
                <div className={styles.featureCard}>
                  <div className={styles.featureNumber}>3</div>
                  <div className={styles.featureIcon}>
                    <i className="fas fa-bell"></i>
                  </div>
                  <h3>Smart Alerts</h3>
                  <p>Personalized safety alerts based on user location and crime patterns in their area</p>
                  <div className={styles.featureTags}>
                    <span>Push Notifications</span>
                    <span>Location-based</span>
                  </div>
                </div>
                
                <div className={styles.featureCard}>
                  <div className={styles.featureNumber}>4</div>
                  <div className={styles.featureIcon}>
                    <i className="fas fa-route"></i>
                  </div>
                  <h3>Safe Navigation</h3>
                  <p>Route planning that avoids high-risk areas and provides real-time safety updates during travel</p>
                  <div className={styles.featureTags}>
                    <span>Route Optimization</span>
                    <span>Safety First</span>
                  </div>
                </div>
                
                <div className={styles.featureCard}>
                  <div className={styles.featureNumber}>5</div>
                  <div className={styles.featureIcon}>
                    <i className="fas fa-chart-bar"></i>
                  </div>
                  <h3>Analytics Dashboard</h3>
                  <p>Comprehensive crime statistics and trend analysis for informed decision-making</p>
                  <div className={styles.featureTags}>
                    <span>Data Visualization</span>
                    <span>Insights</span>
                  </div>
                </div>
                
                <div className={styles.featureCard}>
                  <div className={styles.featureNumber}>6</div>
                  <div className={styles.featureIcon}>
                    <i className="fas fa-phone-alt"></i>
                  </div>
                  <h3>Emergency Resources</h3>
                  <p>Quick access to emergency contacts, hospitals, and police stations with one-tap calling</p>
                  <div className={styles.featureTags}>
                    <span>Emergency Response</span>
                    <span>Quick Access</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'technology' && (
            <div className={styles.contentPanel}>
              <h2>Technology Stack</h2>
              <p className={styles.leadText}>
                SafeVision is built using modern, scalable technologies to ensure high performance,
                reliability, and security.
              </p>
              
              <div className={styles.techStack}>
                <div className={styles.techCategory}>
                  <h3><i className="fas fa-laptop-code"></i> Frontend</h3>
                  <div className={styles.techItems}>
                    <div className={styles.techItem}>
                      <i className="fab fa-react"></i>
                      <span>React.js</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-code"></i>
                      <span>JavaScript ES6+</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fab fa-css3-alt"></i>
                      <span>CSS Modules</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-map"></i>
                      <span>Leaflet.js</span>
                    </div>
                  </div>
                </div>
                
                <div className={styles.techCategory}>
                  <h3><i className="fas fa-server"></i> Backend</h3>
                  <div className={styles.techItems}>
                    <div className={styles.techItem}>
                      <i className="fab fa-python"></i>
                      <span>Python</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-flask"></i>
                      <span>Flask</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-database"></i>
                      <span>PostgreSQL</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-shield-alt"></i>
                      <span>JWT Auth</span>
                    </div>
                  </div>
                </div>
                
                <div className={styles.techCategory}>
                  <h3><i className="fas fa-brain"></i> AI & ML</h3>
                  <div className={styles.techItems}>
                    <div className={styles.techItem}>
                      <i className="fas fa-robot"></i>
                      <span>TensorFlow</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-chart-line"></i>
                      <span>Scikit-learn</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-project-diagram"></i>
                      <span>Neural Networks</span>
                    </div>
                    <div className={styles.techItem}>
                      <i className="fas fa-analytics"></i>
                      <span>Pandas & NumPy</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className={styles.architectureDiagram}>
                <h3>System Architecture</h3>
                <div className={styles.diagramContainer}>
                  <svg viewBox="0 0 800 400" className={styles.diagram}>
                    <defs>
                      <linearGradient id="archGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style={{ stopColor: '#06b6d4' }} />
                        <stop offset="100%" style={{ stopColor: '#8b5cf6' }} />
                      </linearGradient>
                    </defs>
                    
                    {/* Frontend Layer */}
                    <rect x="50" y="50" width="150" height="80" rx="10" fill="url(#archGrad)" opacity="0.8"/>
                    <text x="125" y="95" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">Frontend</text>
                    <text x="125" y="115" textAnchor="middle" fill="white" fontSize="12">React.js</text>
                    
                    {/* Backend Layer */}
                    <rect x="325" y="50" width="150" height="80" rx="10" fill="url(#archGrad)" opacity="0.8"/>
                    <text x="400" y="95" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">Backend</text>
                    <text x="400" y="115" textAnchor="middle" fill="white" fontSize="12">Flask API</text>
                    
                    {/* Database Layer */}
                    <rect x="600" y="50" width="150" height="80" rx="10" fill="url(#archGrad)" opacity="0.8"/>
                    <text x="675" y="95" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">Database</text>
                    <text x="675" y="115" textAnchor="middle" fill="white" fontSize="12">PostgreSQL</text>
                    
                    {/* AI Layer */}
                    <rect x="325" y="270" width="150" height="80" rx="10" fill="url(#archGrad)" opacity="0.8"/>
                    <text x="400" y="315" textAnchor="middle" fill="white" fontSize="16" fontWeight="bold">AI Engine</text>
                    <text x="400" y="335" textAnchor="middle" fill="white" fontSize="12">ML Models</text>
                    
                    {/* Arrows */}
                    <line x1="200" y1="90" x2="325" y2="90" stroke="#06b6d4" strokeWidth="3" markerEnd="url(#arrowhead)"/>
                    <line x1="475" y1="90" x2="600" y2="90" stroke="#06b6d4" strokeWidth="3" markerEnd="url(#arrowhead)"/>
                    <line x1="400" y1="130" x2="400" y2="270" stroke="#06b6d4" strokeWidth="3" markerEnd="url(#arrowhead)"/>
                    
                    <defs>
                      <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                        <polygon points="0 0, 10 3, 0 6" fill="#06b6d4" />
                      </marker>
                    </defs>
                  </svg>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'impact' && (
            <div className={styles.contentPanel}>
              <h2>Project Impact</h2>
              <p className={styles.leadText}>
                SafeVision is making a real difference in community safety and crime prevention.
                Here's how our platform is creating positive change.
              </p>
              
              <div className={styles.impactStats}>
                <div className={styles.impactCard}>
                  <div className={styles.impactValue}>10,000+</div>
                  <div className={styles.impactLabel}>Active Users</div>
                  <div className={styles.impactDescription}>
                    Citizens using SafeVision daily for safety information
                  </div>
                </div>
                
                <div className={styles.impactCard}>
                  <div className={styles.impactValue}>95%</div>
                  <div className={styles.impactLabel}>Prediction Accuracy</div>
                  <div className={styles.impactDescription}>
                    Highly accurate crime risk predictions
                  </div>
                </div>
                
                <div className={styles.impactCard}>
                  <div className={styles.impactValue}>50K+</div>
                  <div className={styles.impactLabel}>Crime Records</div>
                  <div className={styles.impactDescription}>
                    Historical data analyzed for patterns
                  </div>
                </div>
                
                <div className={styles.impactCard}>
                  <div className={styles.impactValue}>24/7</div>
                  <div className={styles.impactLabel}>Real-time Monitoring</div>
                  <div className={styles.impactDescription}>
                    Continuous crime data updates and alerts
                  </div>
                </div>
              </div>

              <div className={styles.benefitsSection}>
                <h3>Key Benefits</h3>
                <div className={styles.benefitsGrid}>
                  <div className={styles.benefitCard}>
                    <i className="fas fa-shield-alt"></i>
                    <h4>Enhanced Public Safety</h4>
                    <p>Empowering citizens with real-time safety information and crime awareness</p>
                  </div>
                  
                  <div className={styles.benefitCard}>
                    <i className="fas fa-chart-line"></i>
                    <h4>Data-Driven Policing</h4>
                    <p>Helping law enforcement allocate resources more effectively</p>
                  </div>
                  
                  <div className={styles.benefitCard}>
                    <i className="fas fa-users"></i>
                    <h4>Community Awareness</h4>
                    <p>Building safer communities through shared safety intelligence</p>
                  </div>
                  
                  <div className={styles.benefitCard}>
                    <i className="fas fa-clock"></i>
                    <h4>Proactive Prevention</h4>
                    <p>Shifting from reactive to proactive crime prevention strategies</p>
                  </div>
                </div>
              </div>

              <div className={styles.futureGoals}>
                <h3><i className="fas fa-rocket"></i> Future Goals</h3>
                <div className={styles.goalsList}>
                  <div className={styles.goalItem}>
                    <div className={styles.goalIcon}>
                      <i className="fas fa-map"></i>
                    </div>
                    <div className={styles.goalContent}>
                      <h4>Expand Coverage</h4>
                      <p>Extend SafeVision to other major cities across Pakistan</p>
                    </div>
                  </div>
                  
                  <div className={styles.goalItem}>
                    <div className={styles.goalIcon}>
                      <i className="fas fa-mobile-alt"></i>
                    </div>
                    <div className={styles.goalContent}>
                      <h4>Mobile App</h4>
                      <p>Launch native iOS and Android applications for better accessibility</p>
                    </div>
                  </div>
                  
                  <div className={styles.goalItem}>
                    <div className={styles.goalIcon}>
                      <i className="fas fa-brain"></i>
                    </div>
                    <div className={styles.goalContent}>
                      <h4>Advanced AI</h4>
                      <p>Implement deep learning models for even more accurate predictions</p>
                    </div>
                  </div>
                  
                  <div className={styles.goalItem}>
                    <div className={styles.goalIcon}>
                      <i className="fas fa-handshake"></i>
                    </div>
                    <div className={styles.goalContent}>
                      <h4>Government Partnership</h4>
                      <p>Collaborate with law enforcement for official data integration</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      </div>
      
      <Footer />
    </>
  );
};

export default ProjectVideoPage;

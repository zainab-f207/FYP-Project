import React from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../Header/Header';
import Footer from '../Footer/Footer';
import EmergencyContacts from '../CrimeMapInterface/components/EmergencyContacts';
import styles from './EmergencyPage.module.css';

const EmergencyPage = () => {
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
            <linearGradient id="emergencyGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{ stopColor: '#ef4444', stopOpacity: 0.3 }} />
              <stop offset="100%" style={{ stopColor: '#dc2626', stopOpacity: 0.3 }} />
            </linearGradient>
          </defs>
          
          {/* Pulsing emergency circles */}
          <circle cx="200" cy="200" r="50" fill="url(#emergencyGrad1)" opacity="0.3">
            <animate attributeName="r" values="50;70;50" dur="3s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0.6;0.3" dur="3s" repeatCount="indefinite" />
          </circle>
          
          <circle cx="900" cy="300" r="60" fill="url(#emergencyGrad1)" opacity="0.3">
            <animate attributeName="r" values="60;80;60" dur="4s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0.6;0.3" dur="4s" repeatCount="indefinite" />
          </circle>
          
          <circle cx="600" cy="600" r="70" fill="url(#emergencyGrad1)" opacity="0.3">
            <animate attributeName="r" values="70;90;70" dur="5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.3;0.6;0.3" dur="5s" repeatCount="indefinite" />
          </circle>
        </svg>
      </div>

      {/* Header Section */}
      <div className={styles.pageHeader}>
        <div className={styles.headerContent}>
          <div className={styles.iconContainer}>
            <svg className={styles.headerIcon} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient id="emergencyIconGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" style={{ stopColor: '#ef4444' }} />
                  <stop offset="100%" style={{ stopColor: '#dc2626' }} />
                </linearGradient>
              </defs>
              
              {/* Emergency cross */}
              <rect x="42" y="20" width="16" height="60" rx="3" fill="url(#emergencyIconGrad)">
                <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
              </rect>
              <rect x="20" y="42" width="60" height="16" rx="3" fill="url(#emergencyIconGrad)">
                <animate attributeName="opacity" values="1;0.5;1" dur="2s" repeatCount="indefinite" />
              </rect>
              
              {/* Pulsing circle */}
              <circle cx="50" cy="50" r="40" fill="none" stroke="url(#emergencyIconGrad)" strokeWidth="2" opacity="0.5">
                <animate attributeName="r" values="40;45;40" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.5;0;0.5" dur="2s" repeatCount="indefinite" />
              </circle>
            </svg>
          </div>
          <h1 className={styles.pageTitle}>Emergency Resources & Contacts</h1>
          <p className={styles.pageSubtitle}>
            Quick access to emergency services, helplines, and support resources. In case of emergency,
            every second counts. Find the help you need instantly with our comprehensive directory of
            emergency contacts across Lahore.
          </p>
        </div>

        {/* Emergency Alert Banner */}
        <div className={styles.emergencyBanner}>
          <div className={styles.bannerIcon}>
            <i className="fas fa-exclamation-triangle"></i>
          </div>
          <div className={styles.bannerContent}>
            <h3>In Case of Immediate Danger</h3>
            <p>Call <strong>15</strong> (Police Emergency) or <strong>1122</strong> (Rescue Services) immediately</p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-phone-alt"></i>
            </div>
            <div className={styles.statValue}>24/7</div>
            <div className={styles.statLabel}>Emergency Hotlines</div>
          </div>
          
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-hospital"></i>
            </div>
            <div className={styles.statValue}>50+</div>
            <div className={styles.statLabel}>Hospitals & Clinics</div>
          </div>
          
          <div className={styles.statCard}>
            <div className={styles.statIcon}>
              <i className="fas fa-shield-alt"></i>
            </div>
            <div className={styles.statValue}>100+</div>
            <div className={styles.statLabel}>Police Stations</div>
          </div>
        </div>
      </div>

      {/* Important Numbers Section */}
      <div className={styles.importantNumbersSection}>
        <h2>
          <i className="fas fa-star"></i>
          Most Important Numbers
        </h2>
        <div className={styles.numbersGrid}>
          <div className={styles.numberCard}>
            <div className={styles.numberIcon} style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)' }}>
              <i className="fas fa-phone-volume"></i>
            </div>
            <h3>Police Emergency</h3>
            <div className={styles.phoneNumber}>15</div>
            <p>For immediate police assistance</p>
          </div>
          
          <div className={styles.numberCard}>
            <div className={styles.numberIcon} style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
              <i className="fas fa-ambulance"></i>
            </div>
            <h3>Rescue Services</h3>
            <div className={styles.phoneNumber}>1122</div>
            <p>Medical emergencies & rescue</p>
          </div>
          
          <div className={styles.numberCard}>
            <div className={styles.numberIcon} style={{ background: 'linear-gradient(135deg, #10b981, #059669)' }}>
              <i className="fas fa-fire-extinguisher"></i>
            </div>
            <h3>Fire Brigade</h3>
            <div className={styles.phoneNumber}>16</div>
            <p>Fire emergencies & rescue</p>
          </div>
          
          <div className={styles.numberCard}>
            <div className={styles.numberIcon} style={{ background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)' }}>
              <i className="fas fa-user-shield"></i>
            </div>
            <h3>Women Helpline</h3>
            <div className={styles.phoneNumber}>1043</div>
            <p>Support for women in distress</p>
          </div>
        </div>
      </div>

      {/* Emergency Contacts Component */}
      <div className={styles.contactsSection}>
        <div className={styles.sectionHeader}>
          <h2>
            <i className="fas fa-address-book"></i>
            Complete Emergency Directory
          </h2>
          <p>Browse all emergency contacts by category</p>
        </div>
        <div className={styles.contactsWrapper}>
          <EmergencyContacts />
        </div>
      </div>

      {/* Safety Tips Section */}
      <div className={styles.safetyTipsSection}>
        <h2>
          <i className="fas fa-lightbulb"></i>
          Emergency Safety Tips
        </h2>
        <div className={styles.tipsGrid}>
          <div className={styles.tipCard}>
            <div className={styles.tipNumber}>1</div>
            <div className={styles.tipIcon}>
              <i className="fas fa-mobile-alt"></i>
            </div>
            <h3>Keep Phone Charged</h3>
            <p>Always maintain your phone battery above 20% and keep emergency numbers saved</p>
          </div>
          
          <div className={styles.tipCard}>
            <div className={styles.tipNumber}>2</div>
            <div className={styles.tipIcon}>
              <i className="fas fa-map-marker-alt"></i>
            </div>
            <h3>Know Your Location</h3>
            <p>Be aware of your current location and nearby landmarks for accurate emergency reporting</p>
          </div>
          
          <div className={styles.tipCard}>
            <div className={styles.tipNumber}>3</div>
            <div className={styles.tipIcon}>
              <i className="fas fa-users"></i>
            </div>
            <h3>Share Location</h3>
            <p>Share your live location with trusted contacts when traveling alone</p>
          </div>
          
          <div className={styles.tipCard}>
            <div className={styles.tipNumber}>4</div>
            <div className={styles.tipIcon}>
              <i className="fas fa-first-aid"></i>
            </div>
            <h3>Basic First Aid</h3>
            <p>Learn basic first aid and CPR to help yourself and others in emergencies</p>
          </div>
          
          <div className={styles.tipCard}>
            <div className={styles.tipNumber}>5</div>
            <div className={styles.tipIcon}>
              <i className="fas fa-exclamation-circle"></i>
            </div>
            <h3>Stay Calm</h3>
            <p>In emergencies, stay calm and speak clearly when calling for help</p>
          </div>
          
          <div className={styles.tipCard}>
            <div className={styles.tipNumber}>6</div>
            <div className={styles.tipIcon}>
              <i className="fas fa-file-medical"></i>
            </div>
            <h3>Medical Information</h3>
            <p>Keep important medical information and allergies documented and accessible</p>
          </div>
        </div>
      </div>

      {/* What to Do Section */}
      <div className={styles.whatToDoSection}>
        <h2>What to Do in an Emergency</h2>
        <div className={styles.scenariosGrid}>
          <div className={styles.scenarioCard}>
            <div className={styles.scenarioIcon} style={{ background: '#ef4444' }}>
              <i className="fas fa-user-injured"></i>
            </div>
            <h3>Medical Emergency</h3>
            <ul>
              <li><i className="fas fa-check"></i> Call 1122 immediately</li>
              <li><i className="fas fa-check"></i> Provide exact location</li>
              <li><i className="fas fa-check"></i> Describe the condition clearly</li>
              <li><i className="fas fa-check"></i> Stay with the patient</li>
            </ul>
          </div>
          
          <div className={styles.scenarioCard}>
            <div className={styles.scenarioIcon} style={{ background: '#f59e0b' }}>
              <i className="fas fa-fire"></i>
            </div>
            <h3>Fire Emergency</h3>
            <ul>
              <li><i className="fas fa-check"></i> Call 16 for fire brigade</li>
              <li><i className="fas fa-check"></i> Evacuate immediately</li>
              <li><i className="fas fa-check"></i> Don't use elevators</li>
              <li><i className="fas fa-check"></i> Alert others nearby</li>
            </ul>
          </div>
          
          <div className={styles.scenarioCard}>
            <div className={styles.scenarioIcon} style={{ background: '#8b5cf6' }}>
              <i className="fas fa-exclamation-triangle"></i>
            </div>
            <h3>Crime/Threat</h3>
            <ul>
              <li><i className="fas fa-check"></i> Call 15 for police</li>
              <li><i className="fas fa-check"></i> Move to safe location</li>
              <li><i className="fas fa-check"></i> Note suspect details</li>
              <li><i className="fas fa-check"></i> Preserve evidence</li>
            </ul>
          </div>
        </div>
      </div>
      </div>
      
      <Footer />
    </>
  );
};

export default EmergencyPage;

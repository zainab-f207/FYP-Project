// src/components/SuperAdminDashboard/SVGComponents.jsx
import React from 'react';

// Advanced Analytics Dashboard Background SVG
export const AnalyticsBgSVG = () => (
  <svg className="analytics-bg-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800">
    <defs>
      <linearGradient id="analyticsGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor:'#1a3a5f', stopOpacity:0.1}} />
        <stop offset="50%" style={{stopColor:'#00a6a6', stopOpacity:0.08}} />
        <stop offset="100%" style={{stopColor:'#ffc107', stopOpacity:0.05}} />
      </linearGradient>
      <pattern id="networkPattern" x="0" y="0" width="60" height="60" patternUnits="userSpaceOnUse">
        <circle cx="30" cy="30" r="2" fill="#00a6a6" opacity="0.3"/>
        <circle cx="0" cy="0" r="1" fill="#00a6a6" opacity="0.2"/>
        <circle cx="60" cy="60" r="1" fill="#00a6a6" opacity="0.2"/>
        <line x1="30" y1="30" x2="0" y2="0" stroke="#00a6a6" strokeWidth="0.5" opacity="0.2"/>
        <line x1="30" y1="30" x2="60" y2="60" stroke="#00a6a6" strokeWidth="0.5" opacity="0.2"/>
      </pattern>
      <filter id="glow">
        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
        <feMerge> 
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>
    
    {/* Background */}
    <rect width="100%" height="100%" fill="url(#analyticsGrad1)"/>
    <rect width="100%" height="100%" fill="url(#networkPattern)"/>
    
    {/* Animated Geometric Shapes */}
    <g className="floating-shapes">
      <circle cx="200" cy="150" r="40" fill="#00a6a6" opacity="0.1" filter="url(#glow)">
        <animateTransform
          attributeName="transform"
          attributeType="XML"
          type="translate"
          values="0,0; 20,10; 0,0"
          dur="6s"
          repeatCount="indefinite"
        />
      </circle>
      
      <polygon points="800,100 850,50 900,100 850,150" fill="#1a3a5f" opacity="0.15">
        <animateTransform
          attributeName="transform"
          attributeType="XML"
          type="rotate"
          values="0 850 100; 360 850 100"
          dur="20s"
          repeatCount="indefinite"
        />
      </polygon>
      
      <rect x="1000" y="200" width="60" height="60" rx="10" fill="#ffc107" opacity="0.1">
        <animateTransform
          attributeName="transform"
          attributeType="XML"
          type="scale"
          values="1; 1.2; 1"
          dur="4s"
          repeatCount="indefinite"
        />
      </rect>
    </g>
    
    {/* Data Flow Lines */}
    <g className="data-flow-lines" stroke="#00a6a6" strokeWidth="2" opacity="0.3" fill="none">
      <path d="M100,400 Q300,300 500,400 T900,400">
        <animate
          attributeName="stroke-dasharray"
          values="0,1000; 50,950; 100,900; 0,1000"
          dur="8s"
          repeatCount="indefinite"
        />
      </path>
      <path d="M150,500 Q400,400 650,500 T1100,500">
        <animate
          attributeName="stroke-dasharray"
          values="0,1000; 50,950; 100,900; 0,1000"
          dur="10s"
          repeatCount="indefinite"
        />
      </path>
    </g>
  </svg>
);

// Enhanced System Monitoring SVG Icon
export const SystemMonitorSVG = ({ className, color = "#00a6a6" }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <defs>
      <linearGradient id="monitorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style={{stopColor: color, stopOpacity: 1}} />
        <stop offset="100%" style={{stopColor: '#1a3a5f', stopOpacity: 0.8}} />
      </linearGradient>
      <filter id="innerShadow">
        <feOffset dx="0" dy="0"/>
        <feGaussianBlur stdDeviation="2" result="offset-blur"/>
        <feFlood floodColor="#000000" floodOpacity="0.3"/>
        <feComposite in2="offset-blur" operator="in"/>
      </filter>
    </defs>
    
    {/* Monitor Screen */}
    <rect x="15" y="20" width="70" height="50" rx="5" fill="url(#monitorGrad)" filter="url(#innerShadow)"/>
    <rect x="20" y="25" width="60" height="40" rx="2" fill="#001122" opacity="0.8"/>
    
    {/* Screen Content - Charts */}
    <g stroke={color} strokeWidth="1.5" fill="none" opacity="0.9">
      <path d="M25,45 L35,40 L45,50 L55,35 L65,45 L75,40">
        <animate
          attributeName="d"
          values="M25,45 L35,40 L45,50 L55,35 L65,45 L75,40; M25,50 L35,35 L45,45 L55,30 L65,40 L75,35; M25,45 L35,40 L45,50 L55,35 L65,45 L75,40"
          dur="3s"
          repeatCount="indefinite"
        />
      </path>
      <circle cx="45" cy="45" r="8" opacity="0.3">
        <animate attributeName="r" values="8; 12; 8" dur="2s" repeatCount="indefinite"/>
      </circle>
    </g>
    
    {/* Monitor Stand */}
    <rect x="45" y="70" width="10" height="10" fill="url(#monitorGrad)"/>
    <rect x="35" y="80" width="30" height="5" rx="2" fill="url(#monitorGrad)"/>
    
    {/* Status Indicators */}
    <circle cx="80" cy="30" r="3" fill="#22c55e">
      <animate attributeName="opacity" values="0.5; 1; 0.5" dur="2s" repeatCount="indefinite"/>
    </circle>
    <circle cx="80" cy="40" r="3" fill="#ffc107">
      <animate attributeName="opacity" values="0.3; 0.8; 0.3" dur="3s" repeatCount="indefinite"/>
    </circle>
    <circle cx="80" cy="50" r="3" fill="#dc2626" opacity="0.3"/>
  </svg>
);

// Advanced Security Shield SVG
export const SecurityShieldSVG = ({ className, color = "#00a6a6" }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <defs>
      <radialGradient id="shieldGrad" cx="50%" cy="50%">
        <stop offset="0%" style={{stopColor: color, stopOpacity: 1}} />
        <stop offset="70%" style={{stopColor: '#1a3a5f', stopOpacity: 0.8}} />
        <stop offset="100%" style={{stopColor: '#000', stopOpacity: 0.3}} />
      </radialGradient>
      <pattern id="circuitPattern" x="0" y="0" width="8" height="8" patternUnits="userSpaceOnUse">
        <circle cx="4" cy="4" r="0.5" fill={color} opacity="0.3"/>
        <line x1="0" y1="4" x2="8" y2="4" stroke={color} strokeWidth="0.2" opacity="0.2"/>
        <line x1="4" y1="0" x2="4" y2="8" stroke={color} strokeWidth="0.2" opacity="0.2"/>
      </pattern>
    </defs>
    
    {/* Shield Base */}
    <path d="M50 10 L20 25 L20 55 Q20 80 50 90 Q80 80 80 55 L80 25 Z" 
          fill="url(#shieldGrad)" stroke={color} strokeWidth="2"/>
    
    {/* Circuit Pattern Overlay */}
    <path d="M50 15 L25 28 L25 55 Q25 75 50 85 Q75 75 75 55 L75 28 Z" 
          fill="url(#circuitPattern)" opacity="0.6"/>
    
    {/* Central Security Symbol */}
    <g transform="translate(50,50)">
      <circle r="15" fill="none" stroke={color} strokeWidth="2" opacity="0.8">
        <animate attributeName="r" values="15; 18; 15" dur="3s" repeatCount="indefinite"/>
      </circle>
      <path d="M-8,-2 L-3,3 L8,-8" fill="none" stroke="#22c55e" strokeWidth="3" strokeLinecap="round">
        <animate attributeName="stroke-dasharray" values="0,20; 20,0; 0,20" dur="2s" repeatCount="indefinite"/>
      </path>
    </g>
    
    {/* Scanning Lines */}
    <g stroke={color} strokeWidth="1" opacity="0.4">
      <line x1="30" y1="35" x2="70" y2="35">
        <animate attributeName="opacity" values="0; 1; 0" dur="2s" repeatCount="indefinite"/>
      </line>
      <line x1="30" y1="45" x2="70" y2="45">
        <animate attributeName="opacity" values="0; 1; 0" dur="2s" begin="0.5s" repeatCount="indefinite"/>
      </line>
      <line x1="30" y1="55" x2="70" y2="55">
        <animate attributeName="opacity" values="0; 1; 0" dur="2s" begin="1s" repeatCount="indefinite"/>
      </line>
    </g>
    
    {/* Security Level Indicators */}
    <g transform="translate(50,75)">
      <rect x="-2" y="-2" width="4" height="4" fill="#22c55e" opacity="0.8"/>
      <rect x="-8" y="-2" width="4" height="4" fill="#ffc107" opacity="0.6"/>
      <rect x="4" y="-2" width="4" height="4" fill="#22c55e" opacity="0.9"/>
    </g>
  </svg>
);

// Network Topology SVG
export const NetworkTopologySVG = ({ className, color = "#00a6a6" }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <defs>
      <radialGradient id="nodeGrad" cx="50%" cy="50%">
        <stop offset="0%" style={{stopColor: color, stopOpacity: 1}} />
        <stop offset="100%" style={{stopColor: '#1a3a5f', stopOpacity: 0.6}} />
      </radialGradient>
    </defs>
    
    {/* Network Connections */}
    <g stroke={color} strokeWidth="1.5" opacity="0.6" fill="none">
      <path d="M50,20 L20,40 M50,20 L80,40 M20,40 L80,40 M20,40 L50,70 M80,40 L50,70 M50,70 L30,85 M50,70 L70,85">
        <animate
          attributeName="stroke-dasharray"
          values="0,200; 10,190; 0,200"
          dur="5s"
          repeatCount="indefinite"
        />
      </path>
    </g>
    
    {/* Network Nodes */}
    <g>
      {/* Central Hub */}
      <circle cx="50" cy="20" r="6" fill="url(#nodeGrad)" stroke={color} strokeWidth="2">
        <animate attributeName="r" values="6; 8; 6" dur="3s" repeatCount="indefinite"/>
      </circle>
      
      {/* Secondary Nodes */}
      <circle cx="20" cy="40" r="4" fill="url(#nodeGrad)" stroke={color} strokeWidth="1.5">
        <animate attributeName="r" values="4; 5; 4" dur="2s" begin="0.5s" repeatCount="indefinite"/>
      </circle>
      <circle cx="80" cy="40" r="4" fill="url(#nodeGrad)" stroke={color} strokeWidth="1.5">
        <animate attributeName="r" values="4; 5; 4" dur="2s" begin="1s" repeatCount="indefinite"/>
      </circle>
      
      {/* Processing Node */}
      <circle cx="50" cy="70" r="5" fill="url(#nodeGrad)" stroke={color} strokeWidth="2">
        <animate attributeName="r" values="5; 7; 5" dur="2.5s" begin="0.3s" repeatCount="indefinite"/>
      </circle>
      
      {/* Terminal Nodes */}
      <circle cx="30" cy="85" r="3" fill="url(#nodeGrad)" stroke={color} strokeWidth="1"/>
      <circle cx="70" cy="85" r="3" fill="url(#nodeGrad)" stroke={color} strokeWidth="1"/>
    </g>
    
    {/* Data Flow Indicators */}
    <g fill={color} opacity="0.8">
      <circle cx="35" cy="30" r="1.5">
        <animateMotion dur="4s" repeatCount="indefinite">
          <mpath href="#path1"/>
        </animateMotion>
      </circle>
      <circle cx="65" cy="30" r="1.5">
        <animateMotion dur="3s" repeatCount="indefinite">
          <mpath href="#path2"/>
        </animateMotion>
      </circle>
    </g>
    
    <defs>
      <path id="path1" d="M50,20 L20,40 L50,70"/>
      <path id="path2" d="M50,20 L80,40 L50,70"/>
    </defs>
  </svg>
);

// Crime Analytics Visualization SVG
export const CrimeAnalyticsSVG = ({ className, color = "#00a6a6" }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <defs>
      <linearGradient id="chartGrad" x1="0%" y1="100%" x2="0%" y2="0%">
        <stop offset="0%" style={{stopColor: color, stopOpacity: 0.8}} />
        <stop offset="100%" style={{stopColor: '#ffc107', stopOpacity: 0.3}} />
      </linearGradient>
    </defs>
    
    {/* Chart Background */}
    <rect x="15" y="15" width="70" height="55" fill="none" stroke={color} strokeWidth="1" opacity="0.3"/>
    
    {/* Chart Bars */}
    <g fill="url(#chartGrad)">
      <rect x="20" y="50" width="8" height="15">
        <animate attributeName="height" values="15; 25; 15" dur="3s" repeatCount="indefinite"/>
        <animate attributeName="y" values="50; 40; 50" dur="3s" repeatCount="indefinite"/>
      </rect>
      <rect x="32" y="45" width="8" height="20">
        <animate attributeName="height" values="20; 30; 20" dur="2.5s" repeatCount="indefinite"/>
        <animate attributeName="y" values="45; 35; 45" dur="2.5s" repeatCount="indefinite"/>
      </rect>
      <rect x="44" y="35" width="8" height="30">
        <animate attributeName="height" values="30; 35; 30" dur="3.5s" repeatCount="indefinite"/>
        <animate attributeName="y" values="35; 30; 35" dur="3.5s" repeatCount="indefinite"/>
      </rect>
      <rect x="56" y="40" width="8" height="25">
        <animate attributeName="height" values="25; 35; 25" dur="2.8s" repeatCount="indefinite"/>
        <animate attributeName="y" values="40; 30; 40" dur="2.8s" repeatCount="indefinite"/>
      </rect>
      <rect x="68" y="55" width="8" height="10">
        <animate attributeName="height" values="10; 20; 10" dur="3.2s" repeatCount="indefinite"/>
        <animate attributeName="y" values="55; 45; 55" dur="3.2s" repeatCount="indefinite"/>
      </rect>
    </g>
    
    {/* Trend Line */}
    <path d="M24,58 L36,52 L48,42 L60,47 L72,60" 
          fill="none" 
          stroke="#22c55e" 
          strokeWidth="2" 
          strokeDasharray="3,2"
          opacity="0.8">
      <animate
        attributeName="stroke-dasharray"
        values="3,2; 6,4; 3,2"
        dur="2s"
        repeatCount="indefinite"
      />
    </path>
    
    {/* Risk Indicators */}
    <g transform="translate(50,80)">
      <circle r="3" fill="#dc2626" opacity="0.7">
        <animate attributeName="opacity" values="0.7; 1; 0.7" dur="1.5s" repeatCount="indefinite"/>
      </circle>
      <circle r="3" transform="translate(-15,0)" fill="#ffc107" opacity="0.5">
        <animate attributeName="opacity" values="0.5; 0.9; 0.5" dur="2s" repeatCount="indefinite"/>
      </circle>
      <circle r="3" transform="translate(15,0)" fill="#22c55e" opacity="0.8"/>
    </g>
  </svg>
);

// Advanced Database SVG Icon
export const DatabaseSVG = ({ className, color = "#00a6a6" }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
    <defs>
      <linearGradient id="dbGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style={{stopColor: color, stopOpacity: 1}} />
        <stop offset="50%" style={{stopColor: '#1a3a5f', stopOpacity: 0.8}} />
        <stop offset="100%" style={{stopColor: color, stopOpacity: 0.6}} />
      </linearGradient>
    </defs>
    
    {/* Database Cylinders */}
    <g fill="url(#dbGrad)" stroke={color} strokeWidth="1">
      {/* Top Cylinder */}
      <ellipse cx="50" cy="20" rx="25" ry="8"/>
      <rect x="25" y="20" width="50" height="20"/>
      <ellipse cx="50" cy="40" rx="25" ry="8"/>
      
      {/* Middle Cylinder */}
      <ellipse cx="50" cy="45" rx="25" ry="8"/>
      <rect x="25" y="45" width="50" height="20"/>
      <ellipse cx="50" cy="65" rx="25" ry="8"/>
      
      {/* Bottom Cylinder */}
      <ellipse cx="50" cy="70" rx="25" ry="8"/>
      <rect x="25" y="70" width="50" height="15"/>
      <ellipse cx="50" cy="85" rx="25" ry="8"/>
    </g>
    
    {/* Data Flow Animation */}
    <g stroke={color} strokeWidth="2" fill="none" opacity="0.7">
      <line x1="30" y1="30" x2="70" y2="30">
        <animate
          attributeName="stroke-dasharray"
          values="0,40; 20,20; 0,40"
          dur="2s"
          repeatCount="indefinite"
        />
      </line>
      <line x1="30" y1="55" x2="70" y2="55">
        <animate
          attributeName="stroke-dasharray"
          values="0,40; 20,20; 0,40"
          dur="2s"
          begin="0.5s"
          repeatCount="indefinite"
        />
      </line>
      <line x1="30" y1="77" x2="70" y2="77">
        <animate
          attributeName="stroke-dasharray"
          values="0,40; 20,20; 0,40"
          dur="2s"
          begin="1s"
          repeatCount="indefinite"
        />
      </line>
    </g>
    
    {/* Status Lights */}
    <circle cx="80" cy="30" r="2" fill="#22c55e">
      <animate attributeName="opacity" values="0.3; 1; 0.3" dur="2s" repeatCount="indefinite"/>
    </circle>
    <circle cx="80" cy="55" r="2" fill="#22c55e">
      <animate attributeName="opacity" values="0.3; 1; 0.3" dur="2s" begin="0.7s" repeatCount="indefinite"/>
    </circle>
    <circle cx="80" cy="77" r="2" fill="#22c55e">
      <animate attributeName="opacity" values="0.3; 1; 0.3" dur="2s" begin="1.3s" repeatCount="indefinite"/>
    </circle>
  </svg>
);

export default {
  AnalyticsBgSVG,
  SystemMonitorSVG,
  SecurityShieldSVG,
  NetworkTopologySVG,
  CrimeAnalyticsSVG,
  DatabaseSVG
};

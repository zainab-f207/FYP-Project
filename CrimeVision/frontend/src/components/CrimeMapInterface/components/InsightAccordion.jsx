import React, { useState } from 'react';

const InsightAccordion = ({ insights }) => {
  const [expandedItems, setExpandedItems] = useState(new Set());

  const toggleItem = (index) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedItems(newExpanded);
  };

  if (!insights || insights.length === 0) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#6b7280' }}>
        No insights available
      </div>
    );
  }

  return (
    <div className="insight-accordion">
      {insights.map((insight, index) => (
        <div key={index} className="accordion-item">
          <button
            className="accordion-header"
            onClick={() => toggleItem(index)}
          >
            <div className="accordion-title">
              <i className={insight.icon} style={{ marginRight: '8px', color: insight.color }}></i>
              {insight.title}
            </div>
            <i className={`fas fa-chevron-${expandedItems.has(index) ? 'up' : 'down'}`}></i>
          </button>
          {expandedItems.has(index) && (
            <div className="accordion-content">
              <p>{insight.description}</p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default InsightAccordion;

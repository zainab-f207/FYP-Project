import React, { useMemo } from 'react';
import PropTypes from 'prop-types';
import { Checkbox, Col, Row, Space, Tag, Tooltip, Typography } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import { PERMISSION_CATEGORIES } from './constants/adminPermissions';

const { Text } = Typography;

/**
 * Reusable card-grid permission picker.
 * Controlled component: parent owns the `value` array (string[]) and reacts via `onChange`.
 *
 * Props:
 *  - value: string[]                – currently selected permission keys
 *  - onChange: (next: string[]) => void
 *  - recommendedPerms?: string[]    – keys to highlight with a "Recommended" tag (informational only)
 *  - compact?: boolean              – tighter spacing for use inside modals
 */
const PermissionMatrix = ({ value = [], onChange, recommendedPerms = [], compact = false }) => {
  const recommendedSet = useMemo(() => new Set(recommendedPerms), [recommendedPerms]);
  const selectedSet = useMemo(() => new Set(value), [value]);

  const togglePermission = (permValue, checked) => {
    const next = new Set(selectedSet);
    if (checked) next.add(permValue);
    else next.delete(permValue);
    onChange?.(Array.from(next));
  };

  const toggleCategory = (categoryPerms, checked) => {
    const next = new Set(selectedSet);
    categoryPerms.forEach((p) => {
      if (checked) next.add(p.value);
      else next.delete(p.value);
    });
    onChange?.(Array.from(next));
  };

  const cardPad = compact ? '14px 16px' : '18px 20px';
  const headerMb = compact ? 10 : 14;

  return (
    <Row gutter={[compact ? 14 : 20, compact ? 14 : 20]}>
      {PERMISSION_CATEGORIES.map((cat) => {
        const catValues = cat.permissions.map((p) => p.value);
        const checkedCount = catValues.filter((v) => selectedSet.has(v)).length;
        const allChecked = checkedCount === catValues.length;
        const someChecked = checkedCount > 0 && !allChecked;

        return (
          <Col xs={24} lg={12} key={cat.category}>
            <div
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 16,
                padding: cardPad,
                height: '100%',
                transition: 'all 0.3s ease',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: headerMb,
                  paddingBottom: 10,
                  borderBottom: '1px solid rgba(255,255,255,0.06)',
                  flexWrap: 'wrap',
                  gap: 8,
                }}
              >
                <Space size={8} wrap>
                  <i className={cat.iconClass} style={{ color: cat.color, fontSize: 16 }} />
                  <Text strong style={{ color: '#e0e0e0', fontSize: compact ? 14 : 15 }}>
                    {cat.category}
                  </Text>
                  <Tag color={cat.color} style={{ borderRadius: 10, fontSize: 11 }}>
                    {checkedCount}/{catValues.length}
                  </Tag>
                </Space>
                <Checkbox
                  checked={allChecked}
                  indeterminate={someChecked}
                  onChange={(e) => toggleCategory(cat.permissions, e.target.checked)}
                  style={{ marginRight: 0 }}
                >
                  <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: 12 }}>All</Text>
                </Checkbox>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? 6 : 8 }}>
                {cat.permissions.map((perm) => (
                  <div
                    key={perm.value}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <Checkbox
                      checked={selectedSet.has(perm.value)}
                      onChange={(e) => togglePermission(perm.value, e.target.checked)}
                    >
                      <span style={{ color: '#d0d0d0' }}>{perm.label}</span>
                      {recommendedSet.has(perm.value) && (
                        <Tag
                          color="gold"
                          style={{ marginLeft: 6, fontSize: 10, borderRadius: 8, lineHeight: '16px', padding: '0 5px' }}
                        >
                          Recommended
                        </Tag>
                      )}
                    </Checkbox>
                    <Tooltip title={perm.desc} placement="left">
                      <InfoCircleOutlined style={{ color: 'rgba(255,255,255,0.3)', cursor: 'pointer' }} />
                    </Tooltip>
                  </div>
                ))}
              </div>
            </div>
          </Col>
        );
      })}
    </Row>
  );
};

PermissionMatrix.propTypes = {
  value: PropTypes.arrayOf(PropTypes.string),
  onChange: PropTypes.func,
  recommendedPerms: PropTypes.arrayOf(PropTypes.string),
  compact: PropTypes.bool,
};

export default PermissionMatrix;

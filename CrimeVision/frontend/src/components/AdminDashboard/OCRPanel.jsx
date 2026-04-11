import React, { useState, useCallback, useRef, useEffect } from 'react';
import styles from './OCRPanel.module.css';
import { apiService } from '../../services/apiService_updated';
import { useAuth } from '../../contexts/AuthContext_updated';

// OCR backend URL - uses main backend (same origin, port 8000)
const OCR_API_URL = 'http://localhost:8000';

const OCRPanel = ({ token }) => {
  const { refreshAuthToken, token: liveToken } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [confidence, setConfidence] = useState(null);
  const [extractedFields, setExtractedFields] = useState(null);
  const [extractedSections, setExtractedSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const [nearestAreaEnglish, setNearestAreaEnglish] = useState(null);
  const [newSectionInput, setNewSectionInput] = useState('');
  const [addingSection, setAddingSection] = useState(false);

  // Resolve English area name from geocoded coordinates
  useEffect(() => {
    const lat = extractedFields?.location?.latitude;
    const lon = extractedFields?.location?.longitude;
    if (!lat || !lon) { setNearestAreaEnglish(null); return; }
    fetch(`${OCR_API_URL}/api/crimes/nearest-area?lat=${lat}&lon=${lon}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.area_name) setNearestAreaEnglish(data.area_name); })
      .catch(() => {});
  }, [extractedFields?.location?.latitude, extractedFields?.location?.longitude]);

  // Compress image if needed (client-side)
  const compressImage = async (file, maxSizeMB = 50) => {
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB <= maxSizeMB) return file;

    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const scale = Math.sqrt(maxSizeMB / sizeMB);
          const width = Math.floor(img.width * scale);
          const height = Math.floor(img.height * scale);
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);
          canvas.toBlob(
            (blob) => {
              const compressedFile = new File([blob], file.name, {
                type: 'image/jpeg',
                lastModified: Date.now(),
              });
              resolve(compressedFile);
            },
            'image/jpeg',
            0.85
          );
        };
        img.src = e.target.result;
      };
      reader.readAsDataURL(file);
    });
  };

  // Handle file selection
  const handleFileSelect = useCallback(async (file) => {
    if (!file) return;
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      setError('Please upload a PNG or JPEG image');
      return;
    }
    const sizeMB = file.size / (1024 * 1024);
    let processedFile = file;
    if (sizeMB > 50) {
      processedFile = await compressImage(file, 50);
    }
    setSelectedFile(processedFile);
    setError(null);
    setExtractedText('');
    setExtractedFields(null);
    setConfidence(null);
    const reader = new FileReader();
    reader.onloadend = () => setPreviewUrl(reader.result);
    reader.readAsDataURL(processedFile);
  }, []);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    handleFileSelect(file);
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  // Extract text from image via OCR API
  const handleExtractText = async () => {
    if (!selectedFile) { setError('Please select an image first'); return; }
    setLoading(true);
    setError(null);
    setExtractedFields(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      const response = await fetch(`${OCR_API_URL}/api/ocr/extract`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || errData.error || `OCR extraction failed (${response.status})`);
      }
      const result = await response.json();
      setExtractedText(result.text || '');
      setConfidence(result.confidence ?? null);
      if (result.fields) setExtractedFields(result.fields);
      if (result.sections) setExtractedSections(result.sections);
      setNewSectionInput('');
    } catch (err) {
      setError(err.message || 'OCR extraction failed');
      setExtractedText('');
      setConfidence(null);
    } finally {
      setLoading(false);
    }
  };

  // Compress image to a small thumbnail for storing in the approval request.
  // Compress for storage while keeping enough resolution for the lightbox viewer.
  // Target: longest edge ≤ 1080px at quality 0.88 — ~300-500 KB base64, well
  // within MySQL max_allowed_packet (default 4 MB).
  const compressForApproval = (dataUrl) =>
    new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const MAX = 1080;
        const scale = Math.min(1, MAX / Math.max(img.width, img.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL('image/jpeg', 0.88));
      };
      img.onerror = () => resolve(null); // skip image on error
      img.src = dataUrl;
    });

  // Remove a single section (and its crime entry) from the extraction results
  const handleRemoveSection = useCallback((sectionToRemove) => {
    setExtractedSections(prev => prev.filter(s => s !== sectionToRemove));
    setExtractedFields(prev => {
      if (!prev) return prev;
      const newSectionCrimes = (prev.section_crimes || []).filter(sc => sc.section !== sectionToRemove);
      const newCrimeType = newSectionCrimes.length
        ? 'Sections: ' + newSectionCrimes.map(sc => sc.section).join(', ')
        : 'Not found';
      return { ...prev, section_crimes: newSectionCrimes, crime_type: newCrimeType };
    });
  }, []);

  const handleFieldEdit = (field, value) => {
    setExtractedFields(prev => ({ ...(prev || {}), [field]: value }));
  };

  const handleLocationEdit = (key, value) => {
    setExtractedFields(prev => ({
      ...(prev || {}),
      location: {
        ...(prev?.location || {}),
        [key]: value,
      },
    }));
  };

  const addSectionWithMeaning = async () => {
    const raw = String(newSectionInput || '').trim();
    if (!raw) return;
    const normalized = raw.toUpperCase().replace(/\s+/g, '');
    if (extractedSections.includes(normalized)) {
      setNewSectionInput('');
      return;
    }

    setAddingSection(true);
    try {
      let lawType = 'PPC';
      let sectionNumber = normalized;
      if (normalized.includes('-')) {
        const [maybeLaw, maybeSection] = normalized.split('-', 2);
        if (maybeLaw && maybeSection && ['PPC', 'ATA', 'CNSA', 'CRPC'].includes(maybeLaw)) {
          lawType = maybeLaw;
          sectionNumber = maybeSection;
        }
      }

      let crimeName = `Section ${sectionNumber}`;
      try {
        const lookup = await apiService.lookupLawSection(sectionNumber, lawType);
        if (lookup?.found && lookup?.section?.english_title) {
          crimeName = lookup.section.english_title;
          lawType = lookup.section.law_type || lawType;
          sectionNumber = lookup.section.section_number || sectionNumber;
        } else if (lookup?.crime_name) {
          crimeName = lookup.crime_name;
          lawType = lookup.law_type || lawType;
        }
      } catch {
        // Keep fallback title if lookup fails
      }

      const finalSection = lawType === 'PPC' ? sectionNumber : `${lawType}-${sectionNumber}`;

      setExtractedSections(prev => [...prev, finalSection]);
      setExtractedFields(prev => {
        const p = prev || {};
        const sectionCrimes = [...(p.section_crimes || []), {
          section: finalSection,
          law_type: lawType,
          crime_name: crimeName,
        }];
        return {
          ...p,
          section_crimes: sectionCrimes,
          crime_type: sectionCrimes.length
            ? 'Sections: ' + sectionCrimes.map(sc => sc.section).join(', ')
            : 'Not found',
        };
      });
      setNewSectionInput('');
    } finally {
      setAddingSection(false);
    }
  };

  // Submit extracted FIR data for SuperAdmin approval
  const handleSubmitForApproval = async () => {
    if (!extractedFields || !previewUrl) return;
    setSubmitting(true);
    setError(null);

    const doSubmit = async (tok) => {
      const thumbnailBase64 = await compressForApproval(previewUrl);
      await apiService.submitApprovalRequest(
        tok,
        'fir_ocr_submission',
        'crime',
        null,
        {
          fir_image_base64: thumbnailBase64,
          extracted_fields: extractedFields,
          extracted_sections: extractedSections,
          confidence: confidence,
          file_name: selectedFile?.name || 'fir_image.jpg',
        }
      );
    };

    try {
      // Use the live token from AuthContext (may have been refreshed)
      const currentToken = liveToken || token;
      await doSubmit(currentToken);
      setSubmitSuccess(true);
    } catch (err) {
      if (err.message === 'SESSION_EXPIRED') {
        // Try to refresh token once and retry
        const refreshed = await refreshAuthToken();
        if (refreshed) {
          try {
            const newToken = liveToken || token;
            await doSubmit(newToken);
            setSubmitSuccess(true);
            return;
          } catch (retryErr) {
            setError('Submission failed after session refresh. Please try again.');
          }
        } else {
          setError('Your session has expired. Please save your work and log in again.');
        }
      } else {
        setError(err.message || 'Failed to submit for approval');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setExtractedText('');
    setExtractedFields(null);
    setExtractedSections([]);
    setConfidence(null);
    setError(null);
    setSubmitSuccess(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const confClass = confidence > 80 ? styles.confidenceHigh : confidence > 60 ? styles.confidenceMedium : styles.confidenceLow;

  return (
    <div className={styles.ocrPanel}>
      {/* ===== PANEL HEADER ===== */}
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><i className="fas fa-file-image"></i></div>
          <div>
            <h3>FIR Document OCR</h3>
            <p className={styles.headerSub}>Upload FIR images to extract crime data using AI-powered OCR</p>
          </div>
        </div>
        <div className={styles.headerControls}>
          {(selectedFile || extractedText) && (
            <button className={styles.clearBtn} onClick={handleClear}>
              <i className="fas fa-redo-alt"></i> Reset
            </button>
          )}
        </div>
      </div>
      {/* ===== CONTENT AREA ===== */}
      <div className={styles.contentArea}>
        {/* Upload Section */}
        <div className={styles.uploadSection}>
          <div className={styles.uploadLabel}><i className="fas fa-upload"></i> Upload FIR Document</div>
          <div
            className={`${styles.dropzone} ${isDragging ? styles.dropzoneDragging : ''} ${previewUrl ? styles.dropzoneHasFile : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {previewUrl ? (
              <div className={styles.previewContainer}>
                <img src={previewUrl} alt="FIR Preview" className={styles.previewImage} />
                <button className={styles.removeImageBtn} onClick={handleClear} title="Remove image">
                  <i className="fas fa-times"></i>
                </button>
              </div>
            ) : (
              <>
                <div className={styles.dropzoneIcon}><i className="fas fa-cloud-upload-alt"></i></div>
                <p className={styles.dropzoneText}>Drag & drop your FIR image here</p>
                <p className={styles.dropzoneSubtext}>or</p>
                <label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/jpg"
                    onChange={handleFileChange}
                    className={styles.fileInput}
                  />
                  <span className={styles.browseBtn}><i className="fas fa-folder-open"></i> Browse Files</span>
                </label>
                <p className={styles.fileFormats}>Supported: PNG, JPG — any size (auto-compressed if needed)</p>
              </>
            )}
          </div>

          {/* File details */}
          {selectedFile && (
            <div className={styles.fileDetails}>
              <div className={styles.fileDetailItem}>
                <span className={styles.fileDetailLabel}>File:</span>
                <span className={styles.fileDetailValue}>{selectedFile.name}</span>
              </div>
              <div className={styles.fileDetailItem}>
                <span className={styles.fileDetailLabel}>Size:</span>
                <span className={styles.fileDetailValue}>{(selectedFile.size / 1024).toFixed(1)} KB</span>
              </div>
              <div className={styles.fileDetailItem}>
                <span className={styles.fileDetailLabel}>Type:</span>
                <span className={styles.fileDetailValue}>{selectedFile.type}</span>
              </div>
            </div>
          )}

          {/* Extract button */}
          <button className={styles.extractBtn} onClick={handleExtractText} disabled={!selectedFile || loading}>
            {loading ? (
              <><i className={`fas fa-spinner ${styles.spin}`}></i> Processing FIR...</>
            ) : (
              <><i className="fas fa-magic"></i> Extract Data from FIR</>
            )}
          </button>

          {/* Error message */}
          {error && (
            <div className={styles.errorMsg}>
              <i className="fas fa-exclamation-circle"></i> {error}
            </div>
          )}
        </div>
      </div>

      {/* ===== RESULTS SECTION ===== */}
      {(extractedText || loading) && (
        <div className={styles.resultsSection}>
          {loading ? (
            <div className={styles.processingState}>
              <div className={styles.processingSpinner}></div>
              <p className={styles.processingText}>Extracting data using AI OCR engine...</p>
              <p className={styles.processingSubtext}>This may take a moment for high-resolution images</p>
            </div>
          ) : (
            <>
              {/* Results Header */}
              <div className={styles.resultsHeader}>
                <h4 className={styles.resultsTitle}><i className="fas fa-check-circle"></i> Extraction Results</h4>
                {confidence !== null && (
                  <span className={`${styles.confidenceBadge} ${confClass}`}>
                    <i className="fas fa-chart-line"></i> {confidence}% Confidence
                  </span>
                )}
              </div>

              {/* Extracted Fields Grid */}
              {extractedFields && (
                <div className={styles.fieldsGrid}>
                  <div className={styles.fieldCard}>
                    <div className={styles.fieldLabel}><i className="fas fa-calendar-alt"></i> Crime Date</div>
                    <input
                      type="date"
                      className={styles.fieldValue}
                      value={extractedFields.crime_date || ''}
                      onChange={(e) => handleFieldEdit('crime_date', e.target.value)}
                    />
                  </div>
                  <div className={styles.fieldCard}>
                    <div className={styles.fieldLabel}><i className="fas fa-clock"></i> Crime Time</div>
                    <input
                      type="text"
                      className={styles.fieldValue}
                      placeholder="e.g. 07:53 AM"
                      value={extractedFields.crime_time || ''}
                      onChange={(e) => handleFieldEdit('crime_time', e.target.value)}
                    />
                  </div>
                  <div className={styles.fieldCard}>
                    <div className={styles.fieldLabel}><i className="fas fa-gavel"></i> Crime Type / Sections</div>
                    <div className={styles.fieldValue}>
                      {extractedFields.crime_type || 'Not found'}
                    </div>
                    {extractedFields.section_crimes && extractedFields.section_crimes.length > 0 && (
                      <div className={styles.sectionCrimesList}>
                        {extractedFields.section_crimes.map((sc, idx) => (
                          <div key={idx} className={styles.sectionCrimeItem}>
                            <span className={`${styles.sectionBadge} ${sc.law_type === 'ATA' ? styles.sectionBadgeAta : sc.law_type !== 'PPC' ? styles.sectionBadgeOther : ''}`}>
                              {sc.section} {sc.law_type || 'PPC'}
                            </span>
                            <span className={styles.crimeName}>{sc.crime_name}</span>
                            <button
                              className={styles.sectionRemoveBtn}
                              title="Remove this section"
                              onClick={() => handleRemoveSection(sc.section)}
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                      <input
                        type="text"
                        className={styles.fieldValue}
                        placeholder="Add section (e.g. 109 or ATA-7)"
                        value={newSectionInput}
                        onChange={(e) => setNewSectionInput(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSectionWithMeaning(); } }}
                        style={{ flex: 1 }}
                      />
                      <button
                        type="button"
                        className={styles.submitApprovalBtn}
                        onClick={addSectionWithMeaning}
                        disabled={addingSection || !newSectionInput.trim()}
                        style={{ padding: '8px 12px' }}
                      >
                        {addingSection ? <i className={`fas fa-spinner ${styles.spin}`}></i> : <i className="fas fa-plus"></i>}
                      </button>
                    </div>
                  </div>
                  <div className={styles.fieldCard}>
                    <div className={styles.fieldLabel}><i className="fas fa-map-marker-alt"></i> Crime Area (Thana)</div>
                    <input
                      type="text"
                      className={styles.fieldValue}
                      value={extractedFields.crime_area || ''}
                      onChange={(e) => handleFieldEdit('crime_area', e.target.value)}
                      style={{ fontFamily: "'Noto Nastaliq Urdu', serif" }}
                    />
                    {nearestAreaEnglish && (
                      <div className={styles.fieldValueSub}>
                        <i className="fas fa-language" style={{ marginRight: 4, color: '#3b82f6' }}></i>
                        {nearestAreaEnglish}
                      </div>
                    )}
                  </div>
                  {extractedFields.location && extractedFields.location.latitude && (
                    <div className={`${styles.fieldCard} ${styles.fieldCardFull}`}>
                      <div className={styles.fieldLabel}><i className="fas fa-map-pin"></i> Geocoded Location</div>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                        <input
                          type="number"
                          step="0.000001"
                          className={styles.fieldValue}
                          value={extractedFields.location.latitude ?? ''}
                          onChange={(e) => handleLocationEdit('latitude', e.target.value)}
                        />
                        <input
                          type="number"
                          step="0.000001"
                          className={styles.fieldValue}
                          value={extractedFields.location.longitude ?? ''}
                          onChange={(e) => handleLocationEdit('longitude', e.target.value)}
                        />
                      </div>
                      {extractedFields.location.display_name && (
                        <input
                          type="text"
                          className={styles.fieldValueSub}
                          value={extractedFields.location.display_name}
                          onChange={(e) => handleLocationEdit('display_name', e.target.value)}
                        />
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Submit for Approval */}
              <div className={styles.submitSection}>
                {submitSuccess ? (
                  <div className={styles.submitSuccessMsg}>
                    <i className="fas fa-check-circle"></i>
                    <span>FIR data submitted for SuperAdmin approval successfully!</span>
                  </div>
                ) : (
                  <button
                    className={styles.submitApprovalBtn}
                    onClick={handleSubmitForApproval}
                    disabled={submitting || !extractedFields}
                  >
                    {submitting ? (
                      <><i className={`fas fa-spinner ${styles.spin}`}></i> Submitting...</>
                    ) : (
                      <><i className="fas fa-paper-plane"></i> Submit for SuperAdmin Approval</>
                    )}
                  </button>
                )}
                <p className={styles.submitHint}>
                  <i className="fas fa-info-circle"></i> Extracted data will be reviewed by a SuperAdmin before being saved as a crime record.
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default OCRPanel;


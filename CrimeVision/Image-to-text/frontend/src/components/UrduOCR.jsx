import { useState, useCallback } from 'react';
import { ocrService } from '../services/api';
import './UrduOCR.css';

const UrduOCR = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [extractedText, setExtractedText] = useState('');
  const [confidence, setConfidence] = useState(null);
  const [extractedFields, setExtractedFields] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  // Compress image if needed (client-side)
  const compressImage = async (file, maxSizeMB = 50) => {
    const sizeMB = file.size / (1024 * 1024);

    // If file is already small enough, return as is
    if (sizeMB <= maxSizeMB) {
      return file;
    }

    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          let width = img.width;
          let height = img.height;

          // Calculate scale to reduce file size
          const scale = Math.sqrt(maxSizeMB / sizeMB);
          width = Math.floor(width * scale);
          height = Math.floor(height * scale);

          canvas.width = width;
          canvas.height = height;

          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);

          // Convert to blob with quality adjustment
          canvas.toBlob(
            (blob) => {
              const compressedFile = new File([blob], file.name, {
                type: 'image/jpeg',
                lastModified: Date.now(),
              });
              console.log(`Compressed from ${sizeMB.toFixed(2)}MB to ${(compressedFile.size / (1024 * 1024)).toFixed(2)}MB`);
              resolve(compressedFile);
            },
            'image/jpeg',
            0.85 // Quality
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

    // Validate file type
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      setError('Please upload a PNG or JPEG image');
      return;
    }

    // No file size limit - we'll compress on client side if needed
    const sizeMB = file.size / (1024 * 1024);
    console.log(`Original file size: ${sizeMB.toFixed(2)}MB`);

    // Compress if larger than 50MB
    let processedFile = file;
    if (sizeMB > 50) {
      setError(null);
      console.log('Compressing large image...');
      processedFile = await compressImage(file, 50);
    }

    setSelectedFile(processedFile);
    setError(null);
    setExtractedText('');
    setExtractedFields(null);
    setConfidence(null);

    // Create preview
    const reader = new FileReader();
    reader.onloadend = () => {
      setPreviewUrl(reader.result);
    };
    reader.readAsDataURL(processedFile);
  }, []);

  // Handle file input change
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    handleFileSelect(file);
  };

  // Handle drag and drop
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileSelect(file);
  };

  // Extract text from image
  const handleExtractText = async () => {
    if (!selectedFile) {
      setError('Please select an image first');
      return;
    }

    setLoading(true);
    setError(null);
    setExtractedFields(null);

    try {
      const result = await ocrService.extractText(selectedFile);
      setExtractedText(result.text);
      setConfidence(result.confidence);
      if (result.fields) {
        setExtractedFields(result.fields);
      }
    } catch (err) {
      setError(err.message);
      setExtractedText('');
      setConfidence(null);
    } finally {
      setLoading(false);
    }
  };

  // Copy text to clipboard
  const handleCopyText = () => {
    if (extractedText) {
      navigator.clipboard.writeText(extractedText);
      // You could add a toast notification here
    }
  };

  // Clear all
  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setExtractedText('');
    setExtractedFields(null);
    setConfidence(null);
    setError(null);
  };

  return (
    <div className="urdu-ocr-container">
      {/* Header */}
      <header className="ocr-header fade-in">
        <div className="header-content">
          <h1 className="gradient-text">Urdu OCR</h1>
          <p className="header-subtitle">Convert Urdu Images to Editable Text</p>
        </div>
        <div className="header-decoration">
          <div className="decoration-circle"></div>
          <div className="decoration-circle"></div>
          <div className="decoration-circle"></div>
        </div>
      </header>

      <div className="container">
        <div className="ocr-content">
          {/* Upload Section */}
          <section className="upload-section glass-effect fade-in">
            <h2 className="section-title">Upload Image</h2>
            
            <div
              className={`dropzone ${isDragging ? 'dragging' : ''} ${previewUrl ? 'has-image' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {previewUrl ? (
                <div className="preview-container">
                  <img src={previewUrl} alt="Preview" className="preview-image" />
                  <button className="clear-btn" onClick={handleClear}>
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                      <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </button>
                </div>
              ) : (
                <div className="dropzone-content">
                  <div className="upload-icon">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
                      <path d="M12 15V3M12 3L8 7M12 3L16 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M2 17L2 19C2 20.1046 2.89543 21 4 21L20 21C21.1046 21 22 20.1046 22 19V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                  </div>
                  <p className="dropzone-text">Drag & drop your image here</p>
                  <p className="dropzone-subtext">or</p>
                  <label className="file-input-label">
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/jpg"
                      onChange={handleFileChange}
                      className="file-input"
                    />
                    <span className="btn btn-primary">Browse Files</span>
                  </label>
                  <p className="file-info">PNG, JPG (any size - auto-compressed if needed)</p>
                </div>
              )}
            </div>

            {selectedFile && (
              <div className="file-details">
                <div className="file-info-item">
                  <span className="file-info-label">File:</span>
                  <span className="file-info-value">{selectedFile.name}</span>
                </div>
                <div className="file-info-item">
                  <span className="file-info-label">Size:</span>
                  <span className="file-info-value">
                    {(selectedFile.size / 1024).toFixed(2)} KB
                  </span>
                </div>
              </div>
            )}

            <button
              className="btn btn-extract"
              onClick={handleExtractText}
              disabled={!selectedFile || loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Processing...
                </>
              ) : (
                <>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  Extract Text
                </>
              )}
            </button>

            {error && (
              <div className="error-message slide-in">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                {error}
              </div>
            )}
          </section>

          {/* Results Section */}
          {(extractedText || loading) && (
            <section className="results-section glass-effect fade-in">
              <div className="results-header">
                <h2 className="section-title">Extracted Text</h2>
                {confidence !== null && (
                  <div className="confidence-badge">
                    <span className="confidence-label">Confidence:</span>
                    <span className={`confidence-value ${confidence > 80 ? 'high' : confidence > 60 ? 'medium' : 'low'}`}>
                      {confidence}%
                    </span>
                  </div>
                )}
              </div>

              <div className="text-output-container">
                {loading ? (
                  <div className="loading-state">
                    <div className="loading-spinner"></div>
                    <p>Extracting text using AI engine (this may take a moment)...</p>
                  </div>
                ) : (
                  <>
                    {/* Extracted Fields Display */}
                    {extractedFields && (
                      <div className="extracted-fields-grid">
                        <div className="field-card">
                          <span className="field-label">Crime Date</span>
                          <span className="field-value">{extractedFields.crime_date}</span>
                        </div>
                        <div className="field-card">
                          <span className="field-label">Crime Type</span>
                          <span className="field-value urdu-text-small">{extractedFields.crime_type}</span>
                        </div>
                        <div className="field-card">
                          <span className="field-label">Crime Area</span>
                          <span className="field-value urdu-text-small">{extractedFields.crime_area}</span>
                        </div>
                        {extractedFields.location && extractedFields.location.latitude && (
                          <div className="field-card" style={{gridColumn: '1 / -1'}}>
                            <span className="field-label">📍 Coordinates</span>
                            <span className="field-value" style={{fontSize: '0.85rem'}}>
                              {Number(extractedFields.location.latitude).toFixed(6)}, {Number(extractedFields.location.longitude).toFixed(6)}
                            </span>
                            {extractedFields.location.display_name && (
                              <span className="field-value" style={{fontSize: '0.75rem', color: '#666', marginTop: '4px', display: 'block'}}>
                                {extractedFields.location.display_name}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    
                    <textarea
                      className="text-output urdu-text"
                      value={extractedText}
                      onChange={(e) => setExtractedText(e.target.value)}
                      placeholder="Extracted text will appear here..."
                      rows={15}
                    />
                    <button className="copy-btn" onClick={handleCopyText} title="Copy to clipboard">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                        <path d="M8 4V16C8 17.1046 8.89543 18 10 18H18C19.1046 18 20 17.1046 20 16V7.24162C20 6.7034 19.7831 6.18789 19.3982 5.81161L16.6569 3.11612C16.2811 2.74855 15.7722 2.53906 15.2426 2.53906H10C8.89543 2.53906 8 3.43449 8 4.53906V4Z" stroke="currentColor" strokeWidth="2"/>
                        <path d="M16 18V20C16 21.1046 15.1046 22 14 22H6C4.89543 22 4 21.1046 4 20V9C4 7.89543 4.89543 7 6 7H8" stroke="currentColor" strokeWidth="2"/>
                      </svg>
                      Copy
                    </button>
                  </>
                )}
              </div>
            </section>
          )}
        </div>

        {/* Features */}
        <section className="features-section fade-in">
          <div className="feature-card glass-effect">
            <div className="feature-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <path d="M13 2L3 14H12L11 22L21 10H12L13 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h3>Fast Processing</h3>
            <p>Advanced OCR engine for quick text extraction</p>
          </div>

          <div className="feature-card glass-effect">
            <div className="feature-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h3>High Accuracy</h3>
            <p>Optimized for Urdu text recognition</p>
          </div>

          <div className="feature-card glass-effect">
            <div className="feature-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <path d="M12 15V3M12 3L8 7M12 3L16 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 17L2 19C2 20.1046 2.89543 21 4 21L20 21C21.1046 21 22 20.1046 22 19V17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h3>Easy to Use</h3>
            <p>Simple drag & drop interface</p>
          </div>
        </section>
      </div>
    </div>
  );
};

export default UrduOCR;

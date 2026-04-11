# Run FIR OCR System
# This script helps you run different modes of the FIR OCR system

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("web", "batch", "test", "help")]
    [string]$Mode = "help",
    
    [Parameter(Mandatory=$false)]
    [string]$InputFolder = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "fir_results.csv",
    
    [Parameter(Mandatory=$false)]
    [string]$TestImage = ""
)

function Show-Help {
    Write-Host "=" -ForegroundColor Cyan
    Write-Host "FIR OCR System - Usage Guide" -ForegroundColor Cyan
    Write-Host "=============================================================================`n" -ForegroundColor Cyan
    
    Write-Host "MODES:" -ForegroundColor Yellow
    Write-Host "  web       - Start web interface for single image processing"
    Write-Host "  batch     - Batch process multiple images (3000+)"
    Write-Host "  test      - Test on a single image"
    Write-Host "  help      - Show this help message`n"
    
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host "  1. Start web interface:"
    Write-Host "     .\run-fir-ocr.ps1 -Mode web`n" -ForegroundColor Green
    
    Write-Host "  2. Batch process all images in folder:"
    Write-Host "     .\run-fir-ocr.ps1 -Mode batch -InputFolder 'F:\FIR_Images' -OutputFile 'results.csv'`n" -ForegroundColor Green
    
    Write-Host "  3. Test on single image:"
    Write-Host "     .\run-fir-ocr.ps1 -Mode test -TestImage 'sample_fir.jpg'`n" -ForegroundColor Green
    
    Write-Host "=============================================================================`n" -ForegroundColor Cyan
}

function Start-WebInterface {
    Write-Host "Starting FIR OCR Web Interface..." -ForegroundColor Cyan
    Write-Host "=" -ForegroundColor Cyan
    
    # Start backend
    Write-Host "`nStarting backend server..." -ForegroundColor Yellow
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:PSScriptRoot
        cd backend
        python main.py
    }
    
    Start-Sleep -Seconds 5
    
    # Check if backend started successfully
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -UseBasicParsing
        Write-Host "✓ Backend running on http://localhost:8000" -ForegroundColor Green
    } catch {
        Write-Host "✗ Failed to start backend!" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Stop-Job $backendJob
        Remove-Job $backendJob
        exit 1
    }
    
    # Start frontend
    Write-Host "`nStarting frontend..." -ForegroundColor Yellow
    $frontendJob = Start-Job -ScriptBlock {
        Set-Location $using:PSScriptRoot
        cd frontend
        npm run dev
    }
    
    Start-Sleep -Seconds 3
    
    Write-Host "`n=============================================================================`n" -ForegroundColor Cyan
    Write-Host "✓ FIR OCR System is running!" -ForegroundColor Green
    Write-Host "`nBackend:  http://localhost:8000" -ForegroundColor Cyan
    Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
    Write-Host "`nOpen your browser and go to: http://localhost:5173" -ForegroundColor Yellow
    Write-Host "`nPress Ctrl+C to stop both servers`n" -ForegroundColor Gray
    Write-Host "=============================================================================`n" -ForegroundColor Cyan
    
    # Wait for user to stop
    try {
        Wait-Job $backendJob, $frontendJob
    } finally {
        Write-Host "`nStopping servers..." -ForegroundColor Yellow
        Stop-Job $backendJob, $frontendJob
        Remove-Job $backendJob, $frontendJob
        Write-Host "✓ Servers stopped" -ForegroundColor Green
    }
}

function Start-BatchProcessing {
    param(
        [string]$Folder,
        [string]$Output
    )
    
    if ([string]::IsNullOrEmpty($Folder)) {
        Write-Host "Error: Input folder not specified!" -ForegroundColor Red
        Write-Host "Usage: .\run-fir-ocr.ps1 -Mode batch -InputFolder 'F:\FIR_Images' -OutputFile 'results.csv'" -ForegroundColor Yellow
        exit 1
    }
    
    if (-not (Test-Path $Folder)) {
        Write-Host "Error: Input folder not found: $Folder" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "=============================================================================`n" -ForegroundColor Cyan
    Write-Host "FIR Batch Processing" -ForegroundColor Cyan
    Write-Host "=============================================================================`n" -ForegroundColor Cyan
    Write-Host "Input Folder: $Folder" -ForegroundColor Yellow
    Write-Host "Output File:  $Output`n" -ForegroundColor Yellow
    
    # Count images
    $imageCount = (Get-ChildItem -Path $Folder -Include *.jpg,*.jpeg,*.png,*.webp -Recurse).Count
    Write-Host "Found $imageCount images to process`n" -ForegroundColor Green
    
    if ($imageCount -eq 0) {
        Write-Host "No images found in folder!" -ForegroundColor Red
        exit 1
    }
    
    # Confirm with user
    $confirm = Read-Host "Continue? (Y/N)"
    if ($confirm -ne "Y" -and $confirm -ne "y") {
        Write-Host "Cancelled by user" -ForegroundColor Yellow
        exit 0
    }
    
    Write-Host "`nStarting batch processing..." -ForegroundColor Cyan
    Write-Host "This may take several hours for 3000+ images`n" -ForegroundColor Yellow
    
    # Run batch processor
    python batch_process_fir.py "$Folder" --output "$Output"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n=============================================================================`n" -ForegroundColor Cyan
        Write-Host "✓ Batch processing completed successfully!" -ForegroundColor Green
        Write-Host "`nResults saved to: $Output" -ForegroundColor Cyan
        Write-Host "=============================================================================`n" -ForegroundColor Cyan
    } else {
        Write-Host "`n✗ Batch processing failed!" -ForegroundColor Red
        exit 1
    }
}

function Start-Test {
    param(
        [string]$Image
    )
    
    if ([string]::IsNullOrEmpty($Image)) {
        Write-Host "Error: Test image not specified!" -ForegroundColor Red
        Write-Host "Usage: .\run-fir-ocr.ps1 -Mode test -TestImage 'sample_fir.jpg'" -ForegroundColor Yellow
        exit 1
    }
    
    if (-not (Test-Path $Image)) {
        Write-Host "Error: Test image not found: $Image" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Testing FIR OCR on: $Image`n" -ForegroundColor Cyan
    
    # Run test
    python test_fir_ocr.py "$Image"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✓ Test completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "`n✗ Test failed!" -ForegroundColor Red
        exit 1
    }
}

# Main execution
switch ($Mode) {
    "web" {
        Start-WebInterface
    }
    "batch" {
        Start-BatchProcessing -Folder $InputFolder -Output $OutputFile
    }
    "test" {
        Start-Test -Image $TestImage
    }
    "help" {
        Show-Help
    }
    default {
        Show-Help
    }
}

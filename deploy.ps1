# Kevin Smart Grant Finder - Production Deployment Script
# This script automates the deployment process for both frontend and backend

Write-Host "🚀 Starting Kevin Smart Grant Finder Deployment Process..." -ForegroundColor Green

# Step 1: Check if all required tools are available
Write-Host "`n📋 Pre-deployment checks..." -ForegroundColor Yellow

# Check if git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if npm is available
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "❌ npm is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# Check if heroku CLI is available
if (-not (Get-Command heroku -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Heroku CLI is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ All required tools are available" -ForegroundColor Green

# Step 2: Ensure we're on the latest code
Write-Host "`n📦 Checking git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️  You have uncommitted changes:" -ForegroundColor Yellow
    git status --short
    $response = Read-Host "Do you want to continue with deployment? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Deployment cancelled by user" -ForegroundColor Yellow
        exit 0
    }
}

# Step 3: Install frontend dependencies and build
Write-Host "`n🔧 Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install frontend dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "`n🏗️  Building frontend for production..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend build failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Frontend build successful" -ForegroundColor Green

# Return to root directory
Set-Location ..

# Step 4: Run backend tests
Write-Host "`n🧪 Running backend tests..." -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Some tests failed. Do you want to continue? (y/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Deployment cancelled due to test failures" -ForegroundColor Yellow
        exit 1
    }
}

# Step 5: Deploy backend to Heroku
Write-Host "`n🚀 Deploying backend to Heroku..." -ForegroundColor Yellow
git add .
git commit -m "Deploy: Feature curation implementation with bulk operations, export, and filtering" -m "- Added bulk grant selection and operations
- Implemented CSV, PDF, and ICS export functionality  
- Added 'Hide Expired' toggle across all pages
- Enhanced UI/UX with modern Material UI components
- Added success notifications and error handling
- Modularized export utilities and bulk actions toolbar"

git push heroku main
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend deployment to Heroku failed" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Backend deployed to Heroku successfully" -ForegroundColor Green

# Step 6: Deploy frontend to Vercel
Write-Host "`n🌐 Deploying frontend to Vercel..." -ForegroundColor Yellow
Set-Location frontend

# Check if Vercel CLI is available
if (Get-Command vercel -ErrorAction SilentlyContinue) {
    vercel --prod
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Frontend deployment to Vercel failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Frontend deployed to Vercel successfully" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Vercel CLI not found. Please deploy frontend manually:" -ForegroundColor Yellow
    Write-Host "1. Install Vercel CLI: npm i -g vercel" -ForegroundColor Cyan
    Write-Host "2. Run: vercel --prod" -ForegroundColor Cyan
    Write-Host "3. Or push to your connected Git repository for auto-deployment" -ForegroundColor Cyan
}

Set-Location ..

# Step 7: Health checks
Write-Host "`n🏥 Running post-deployment health checks..." -ForegroundColor Yellow

Write-Host "Checking backend health..." -ForegroundColor Gray
try {
    $healthCheck = Invoke-RestMethod -Uri "https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health" -Method Get
    Write-Host "✅ Backend health check passed" -ForegroundColor Green
    Write-Host "   Status: $($healthCheck.status)" -ForegroundColor Gray
    Write-Host "   Response time: $($healthCheck.response_time)" -ForegroundColor Gray
}
catch {
    Write-Host "⚠️  Backend health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Step 8: Summary
Write-Host "`n🎉 Deployment Process Complete!" -ForegroundColor Green
Write-Host "`n📋 Deployment Summary:" -ForegroundColor Cyan
Write-Host "✅ Frontend built successfully" -ForegroundColor Green
Write-Host "✅ Backend deployed to Heroku" -ForegroundColor Green
Write-Host "✅ New features deployed:" -ForegroundColor Green
Write-Host "   • Bulk operations (select, save, export)" -ForegroundColor Gray
Write-Host "   • Multi-format export (CSV, PDF, ICS)" -ForegroundColor Gray
Write-Host "   • Hide expired grants filter" -ForegroundColor Gray
Write-Host "   • Enhanced UI/UX with notifications" -ForegroundColor Gray

Write-Host "`n🔗 URLs:" -ForegroundColor Cyan
Write-Host "Backend API: https://smartgrantfinder-a4e2fa159e79.herokuapp.com" -ForegroundColor Blue
Write-Host "Health Check: https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health" -ForegroundColor Blue
Write-Host "Frontend: (Your Vercel deployment URL)" -ForegroundColor Blue

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Test all new features in production" -ForegroundColor Gray
Write-Host "2. Verify bulk operations functionality" -ForegroundColor Gray
Write-Host "3. Test export features across browsers" -ForegroundColor Gray
Write-Host "4. Confirm 'Hide Expired' filter works correctly" -ForegroundColor Gray
Write-Host "5. Monitor logs for any errors" -ForegroundColor Gray

Write-Host "`n🚀 Deployment completed successfully!" -ForegroundColor Green

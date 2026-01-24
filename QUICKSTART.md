# Quick Start Guide - FermentIQ Dashboard

## Step 1: Start the Backend

Open a terminal and run:
```bash
cd Backend
uvicorn main:app --reload --port 8000
```

## Step 2: Open the Dashboard

Simply double-click on `Frontend/index.html` or open it in your browser:
```
file:///c:/Users/krishna raj/Desktop/FermentIQ/Frontend/index.html
```

## What You'll See

The dashboard will display 4 fermentation batches:

### Batch 1 (Green) - Acceptable
- 90% match with golden standard
- Degrades slightly after 48 hours

### Batch 2 (Blue) - Perfect  
- 100% match with golden standard
- Perfect fermentation throughout

### Batch 3 (Red) - Failed
- <75% match with golden standard
- Significant deviations

### Batch 4 (Orange) - Concerning
- 85% match with golden standard
- Moderate deviations

## Features

- **Real-Time Graphs**: 3 charts per batch (pH, Temperature, CO2)
- **Live Updates**: Auto-refreshes every 5 seconds
- **Comparison Metrics**: Shows actual vs ideal readings
- **Color-Coded Alerts**: Visual indicators for deviations
- **Responsive Design**: Works on all screen sizes

## Troubleshooting

If you see connection errors:
1. Make sure the backend is running on port 8000
2. Check that CORS is enabled in the backend
3. Refresh the page

Enjoy monitoring your fermentation batches! 🧪

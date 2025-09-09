# Google OAuth Setup Instructions

To enable direct Google authentication and eliminate the two-step login process, you need to set up a Google OAuth Client ID.

## Steps to Configure Google OAuth:

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the Google Identity API

### 2. Create OAuth 2.0 Credentials
1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Set the following:
   - **Name**: Crypto PnL Tracker
   - **Authorized JavaScript origins**: 
     - `https://pnldashboard.preview.emergentagent.com`
     - `http://localhost:3000` (for development)
   - **Authorized redirect URIs**: 
     - `https://pnldashboard.preview.emergentagent.com`
     - `http://localhost:3000` (for development)

### 3. Update Environment Variables
1. Copy your Google Client ID from the credentials page
2. Update both environment files:

**Frontend (.env):**
```bash
REACT_APP_GOOGLE_CLIENT_ID="your-actual-google-client-id.apps.googleusercontent.com"
```

**Backend (.env):**
```bash
GOOGLE_CLIENT_ID="your-actual-google-client-id.apps.googleusercontent.com"
```

### 4. Restart Services
```bash
sudo supervisorctl restart all
```

## Benefits After Setup:
- ✅ **One-Click Login** - Direct Google authentication
- ✅ **No More Two-Step Process** - Eliminates the intermediate auth page
- ✅ **Faster Login** - Immediate authentication
- ✅ **Better User Experience** - Seamless Google OAuth flow

## Current Status:
- ⚠️ **Placeholder Client ID** - Currently using placeholder values
- ⚠️ **Fallback Available** - The old two-step process still works as backup
- ✅ **Code Ready** - All authentication code is implemented and ready

## Security Notes:
- Client ID is safe to expose (it's public by design)
- Never expose Client Secret (not needed for frontend OAuth)
- Ensure authorized origins match your domain exactly
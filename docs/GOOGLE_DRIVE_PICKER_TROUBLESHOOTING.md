# Google Drive Folder Picker - Troubleshooting Guide

**Error:** "Google Picker API is unavailable"

---

## ✅ Quick Fix Checklist

### 1. Check Environment Variables
```bash
# In frontend/.env.local
cat frontend/.env.local | grep GOOGLE
```

**Required variables:**
```bash
NEXT_PUBLIC_GOOGLE_CLIENT_ID=438983238371-svvk701gqvjql8jsj5gr1lqmtqun9snl.apps.googleusercontent.com
NEXT_PUBLIC_GOOGLE_API_KEY=AIzaSyD2CqZQcV7d0o9Yc_Elv2SDxaKU_B1w-Xw
```

### 2. Restart Development Server
```bash
cd frontend
npm run dev
```

### 3. Hard Refresh Browser
- **Windows/Linux:** Ctrl + Shift + R
- **Mac:** Cmd + Shift + R

### 4. Check Browser Console
Open DevTools (F12) and look for:
```
[DriveFolderPicker] Picker API not available: {gapiExists: true, pickerExists: false}
```

**What this means:**
- `gapiExists: true, pickerExists: true` → ✅ API loaded correctly
- `gapiExists: true, pickerExists: false` → ⏳ Still loading, wait 2-3 seconds
- `gapiExists: false` → ❌ Script failed to load, check network tab

---

## 🔧 Advanced Troubleshooting

### Issue: API Key Invalid
**Symptom:** Picker shows "API key not valid" error

**Fix:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Find your API Key
3. Click "Edit"
4. Under "API restrictions" → "Restrict key"
5. Add these APIs:
   - ✅ Google Picker API
   - ✅ Google Drive API
6. Save and wait 2-5 minutes for propagation
7. Update `.env.local` with the new key

### Issue: Client ID Mismatch
**Symptom:** OAuth error "redirect_uri_mismatch"

**Fix:**
1. Go to [OAuth Credentials](https://console.cloud.google.com/apis/credentials)
2. Click your OAuth 2.0 Client ID
3. Add authorized JavaScript origins:
   - `http://localhost:3000`
   - `https://yourdomain.com`
4. Add authorized redirect URIs:
   - `http://localhost:3000`
   - `https://yourdomain.com`
5. Save and wait 5 minutes

### Issue: Picker API Not Enabled
**Symptom:** Console error "Google Picker API has not been used in project..."

**Fix:**
1. Go to [API Library](https://console.cloud.google.com/apis/library)
2. Search for "Google Picker API"
3. Click and press "Enable"
4. Wait 1-2 minutes
5. Try again

---

## 🐛 Debug Mode

Add this to your browser console to see detailed logs:

```javascript
// Enable debug logging
localStorage.setItem('DEBUG', 'DriveFolderPicker');

// Check if APIs are loaded
console.log('window.gapi:', window.gapi);
console.log('window.gapi.picker:', window.gapi?.picker);
console.log('window.google:', window.google);

// Manually trigger load
if (window.gapi) {
  window.gapi.load('picker', () => {
    console.log('Picker loaded!', window.gapi.picker);
  });
}
```

---

## 📊 Common Error Codes

| Error | Cause | Fix |
|-------|-------|-----|
| `Google Picker API is unavailable` | Picker not loaded yet | Wait 2-3 seconds, try again |
| `API key not valid` | Wrong API key or restrictions | Update API key in Cloud Console |
| `idpiframe_initialization_failed` | Cookie/CORS issue | Clear cookies, check CORS settings |
| `popup_closed_by_user` | User closed picker | Normal behavior, no fix needed |
| `access_denied` | User declined OAuth | Normal behavior, no fix needed |

---

## 🔍 Network Issues

### Check API Endpoints

Open Network tab (F12 → Network) and look for these requests:

1. ✅ `https://apis.google.com/js/api.js` → Status 200
2. ✅ `https://accounts.google.com/gsi/client` → Status 200
3. ❌ NO request to `content.googleapis.com/discovery/...` (we removed this)

**If you see 502 errors:**
- Old code is still cached
- Hard refresh (Ctrl+Shift+R)
- Clear browser cache
- Restart dev server

---

## 💡 Testing the Fix

Run this in browser console when on the export page:

```javascript
// Test 1: Check environment variables
console.log('CLIENT_ID:', process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.slice(0, 20) + '...');
console.log('API_KEY:', process.env.NEXT_PUBLIC_GOOGLE_API_KEY?.slice(0, 20) + '...');

// Test 2: Check API loading
setTimeout(() => {
  console.log('GAPI loaded:', !!window.gapi);
  console.log('Picker loaded:', !!window.gapi?.picker);
  console.log('Google Identity loaded:', !!window.google?.accounts?.oauth2);
}, 3000);

// Test 3: Try to create picker manually
if (window.gapi?.picker) {
  const view = new window.gapi.picker.View(window.gapi.picker.ViewId.FOLDERS);
  console.log('✅ Picker View created successfully!');
} else {
  console.log('❌ Picker not available yet');
}
```

**Expected output:**
```
CLIENT_ID: 438983238371-svvk701...
API_KEY: AIzaSyD2CqZQcV7d0o9...
GAPI loaded: true
Picker loaded: true
Google Identity loaded: true
✅ Picker View created successfully!
```

---

## 🚀 Production Deployment

Before deploying to production:

1. **Update Vercel Environment Variables:**
   ```bash
   vercel env add NEXT_PUBLIC_GOOGLE_CLIENT_ID production
   vercel env add NEXT_PUBLIC_GOOGLE_API_KEY production
   ```

2. **Update OAuth Authorized Domains:**
   - Add `https://yourapp.vercel.app`
   - Add `https://yourdomain.com`

3. **Test on staging first:**
   ```bash
   vercel --prod --env-file .env.production
   ```

4. **Monitor for errors:**
   - Check Vercel logs
   - Check browser console on production URL
   - Test folder selection end-to-end

---

## 📞 Still Having Issues?

If none of the above works:

1. **Share console logs:**
   - Open browser console (F12)
   - Click "Select Folder"
   - Copy all errors (right-click → Save as...)

2. **Share network logs:**
   - Open Network tab
   - Filter by "gapi" or "picker"
   - Look for failed requests (red)

3. **Check Google Cloud Console:**
   - Go to [Quotas](https://console.cloud.google.com/iam-admin/quotas)
   - Make sure Picker API quota not exceeded

4. **Try incognito mode:**
   - Rules out browser extension conflicts
   - Rules out cookie/cache issues

---

**Last Updated:** October 4, 2025  
**Status:** ✅ Fixed and tested

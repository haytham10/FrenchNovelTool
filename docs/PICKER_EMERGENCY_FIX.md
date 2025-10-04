# 🚨 IMMEDIATE FIX - Google Picker "Failed to open folder picker"

**Current Error:** "Failed to open folder picker. Please refresh and try again."

---

## 🔍 Step 1: Check What's Failing

Open your browser console (F12) and look for these new debug messages:

```
[DriveFolderPicker] Select Folder clicked {missingCredentials: false, gapiLoaded: true, ...}
[DriveFolderPicker] Requesting access token...
[DriveFolderPicker] Access token received, creating picker...
[DriveFolderPicker] Picker API not available: {gapiExists: true, pickerExists: false, ...}
```

**Key indicators:**
- ✅ `gapiLoaded: true` → Scripts loaded
- ❌ `pickerExists: false` → **THIS IS THE PROBLEM**

---

## 🔧 Quick Fix Options

### Fix #1: Enable Google Picker API in Cloud Console (Most Common)

1. Go to: https://console.cloud.google.com/apis/library/picker.googleapis.com
2. Select your project
3. Click **"Enable"** button
4. Wait 2-3 minutes for propagation
5. Refresh your app

### Fix #2: Verify API Key Restrictions

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click your API Key (the one in `.env.local`)
3. Scroll to **"API restrictions"**
4. Select **"Restrict key"**
5. Add these APIs:
   - ✅ Google Picker API
   - ✅ Google Drive API
6. Click **Save**
7. Wait 5 minutes

### Fix #3: Use Unrestricted API Key (Temporary Testing)

1. Go to credentials page
2. Create a **NEW API Key**
3. Don't add any restrictions
4. Copy the new key
5. Update `.env.local`:
   ```bash
   NEXT_PUBLIC_GOOGLE_API_KEY=your-new-unrestricted-key
   ```
6. Restart dev server:
   ```bash
   cd frontend
   npm run dev
   ```

---

## 🧪 Use Debug Component

I've created a debug tool. Add it to your page temporarily:

**Edit `frontend/src/app/page.tsx`:**

```typescript
import GooglePickerDebug from '@/components/GooglePickerDebug';

// Inside your component JSX, add:
<GooglePickerDebug />
```

Then:
1. Reload page
2. Click buttons in order: 1 → 2 → wait 3 seconds → 3 → 4
3. Check the console output

---

## 📋 Manual Browser Test

Paste this in browser console (F12):

```javascript
// Step 1: Check if scripts loaded
console.log('GAPI loaded:', !!window.gapi);
console.log('Picker loaded:', !!window.gapi?.picker);
console.log('Google Identity loaded:', !!window.google?.accounts?.oauth2);

// Step 2: If GAPI exists but Picker doesn't, manually load it
if (window.gapi && !window.gapi.picker) {
  console.log('Loading Picker manually...');
  window.gapi.load('picker', () => {
    console.log('Picker loaded!', !!window.gapi.picker);
  });
}

// Step 3: After 5 seconds, check again
setTimeout(() => {
  console.log('After 5s - Picker loaded:', !!window.gapi?.picker);
  
  if (window.gapi?.picker) {
    console.log('✅ SUCCESS! Picker is now available');
    console.log('ViewId.FOLDERS:', window.gapi.picker.ViewId.FOLDERS);
  } else {
    console.log('❌ FAILED - Picker still not available');
    console.log('This means Google Picker API is disabled in Cloud Console');
  }
}, 5000);
```

---

## 🎯 Expected Results

### ✅ Working State
```
[DriveFolderPicker] Loading Picker API...
[DriveFolderPicker] Picker API loaded successfully
[DriveFolderPicker] window.gapi.picker: {View: ƒ, ViewId: {…}, Action: {…}, ...}
[DriveFolderPicker] Select Folder clicked {gapiLoaded: true, pickerExists: true}
[DriveFolderPicker] Requesting access token...
[DriveFolderPicker] Access token received, creating picker...
→ Picker dialog opens ✅
```

### ❌ Broken State (What you're seeing)
```
[DriveFolderPicker] Loading Picker API...
[DriveFolderPicker] Picker API loaded successfully
[DriveFolderPicker] window.gapi.picker: undefined  ← PROBLEM HERE
[DriveFolderPicker] Select Folder clicked {gapiLoaded: true, pickerExists: false}
[DriveFolderPicker] Picker API not available: {gapiExists: true, pickerExists: false}
→ Error: "Failed to open folder picker"
```

---

## 🔥 Nuclear Option (If Nothing Works)

Create a completely new Google Cloud Project:

1. Go to: https://console.cloud.google.com/
2. Create **New Project**
3. Enable these APIs:
   - Google Picker API
   - Google Drive API
   - Google Sheets API
4. Create **OAuth 2.0 Client ID**:
   - Application type: Web application
   - Authorized JavaScript origins: `http://localhost:3000`
5. Create **API Key**:
   - No restrictions for testing
6. Update `.env.local` with new credentials
7. Restart everything

---

## 📞 Tell Me What You See

After running the manual browser test above, tell me:

1. **Does `window.gapi.picker` exist?** (true/false)
2. **What does the 5-second check say?** (✅ SUCCESS or ❌ FAILED)
3. **Any errors in Network tab?** (filter by "picker" or "gapi")

This will tell us exactly what's wrong! 🔍

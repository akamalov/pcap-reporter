# Upload Debugging Guide - PCAP Reporter

## 🔍 **Issue Status**

**Problem**: File selection works (telnet-raw.pcap shows as selected), but upload process doesn't start afterward.

**Investigation**: Added comprehensive debugging to trace the exact issue.

## 🧪 **How to Debug the Upload Issue**

### **Step 1: Open Browser Console**
1. Navigate to http://localhost:3000/upload
2. Press F12 to open Developer Tools
3. Go to the "Console" tab
4. Clear any existing messages

### **Step 2: Test File Selection**
1. Click the blue file input button
2. Select a .pcap file (like telnet-raw.pcap)
3. Watch the console for these debug messages:

**Expected Console Output:**
```
File input onChange triggered
Event target: <input type="file" accept=".pcap,.pcapng,.cap" ...>
Files: FileList { 0: File, length: 1 }
Selected file: File { name: "telnet-raw.pcap", size: 1234, type: "" }
Calling handleUpload with file: telnet-raw.pcap
handleUpload called with file: File { name: "telnet-raw.pcap", ... }
File name: telnet-raw.pcap
File size: 1234
File type: 
File extension: .pcap
Allowed types: [".pcap", ".pcapng", ".cap"]
About to call ApiService.submitAnalysis
```

### **Step 3: Identify the Issue**

**If you see NO console messages:**
- The file input onChange handler isn't being called
- This suggests a JavaScript error or the function isn't bound properly

**If you see file selection messages but no handleUpload:**
- The file variable is undefined or the condition isn't met
- Check if the file object is properly passed

**If you see handleUpload messages but stops at validation:**
- File extension or size validation is failing
- Check the console for validation error messages

**If you see "About to call ApiService.submitAnalysis" but no result:**
- The API call is failing
- Check the Network tab for HTTP requests and errors

**If you see API errors:**
- Backend communication issue
- Check backend logs or API endpoint availability

## 🔧 **Debugging Features Added**

### **File Input Handler**
```typescript
onChange={(e) => {
  console.log('File input onChange triggered')
  console.log('Event target:', e.target)
  console.log('Files:', e.target.files)
  const file = e.target.files?.[0]
  console.log('Selected file:', file)
  if (file) {
    console.log('Calling handleUpload with file:', file.name)
    handleUpload(file)
  } else {
    console.log('No file selected')
  }
}}
```

### **Upload Function**
```typescript
const handleUpload = useCallback(async (file: File): Promise<boolean> => {
  console.log('handleUpload called with file:', file)
  console.log('File name:', file.name)
  console.log('File size:', file.size)
  console.log('File type:', file.type)
  
  // File validation with logging
  const allowedTypes = ['.pcap', '.pcapng', '.cap']
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
  console.log('File extension:', fileExtension)
  console.log('Allowed types:', allowedTypes)
  
  // API call with logging
  console.log('About to call ApiService.submitAnalysis')
  const result = await ApiService.submitAnalysis(file, 'comprehensive', 'normal')
  console.log('ApiService.submitAnalysis result:', result)
  
  // Error handling with detailed logging
  console.error('Upload error:', error)
  console.error('Error details:', error.message, error.stack)
  
  // Cleanup logging
  console.log('Upload finally block - cleaning up')
})
```

## 📋 **Common Issues and Solutions**

### **1. File Input Not Triggering**
**Symptoms**: No console messages at all
**Cause**: JavaScript error preventing event binding
**Solution**: Check for errors in console, verify React component is rendering

### **2. File Object Undefined**
**Symptoms**: "Selected file: undefined" in console
**Cause**: File input not properly returning file object
**Solution**: Verify file input accepts the file type and has proper attributes

### **3. File Validation Failing**
**Symptoms**: Validation error messages in console
**Cause**: File extension or size doesn't meet requirements
**Solution**: Check file extension is .pcap, .pcapng, or .cap and size < 100MB

### **4. API Call Failing**
**Symptoms**: Network errors or no API response
**Cause**: Backend communication issue
**Solution**: Check backend status, API endpoint availability, CORS settings

### **5. Upload Progress Not Showing**
**Symptoms**: No visual progress indicator
**Cause**: State updates not triggering UI changes
**Solution**: Check React state management and component re-rendering

## 🌐 **Network Debugging**

### **Check API Endpoint**
1. Open Network tab in DevTools
2. Select file and watch for HTTP requests
3. Look for POST request to `/api/v1/analysis/submit`
4. Check request headers, body, and response

### **Expected Network Activity**
```
POST /api/v1/analysis/submit
Content-Type: multipart/form-data
Body: FormData with file, analysis_type, priority

Response: 200 OK
{
  "job_id": "some-uuid",
  "filename": "telnet-raw.pcap",
  "status": "processing",
  "file_size": 1234,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## 🔍 **Backend Verification**

### **Check Backend Status**
```bash
# Health check
curl http://localhost:8000/health

# API documentation
curl http://localhost:8000/docs
```

### **Test API Endpoint Directly**
```bash
# Test upload endpoint
curl -X POST "http://localhost:8000/api/v1/analysis/submit" \
  -F "file=@test.pcap" \
  -F "analysis_type=comprehensive" \
  -F "priority=normal"
```

## 📊 **Current Status**

### **Debugging Implementation**
- ✅ **File Input**: Console logging for onChange events
- ✅ **File Validation**: Detailed validation logging
- ✅ **API Calls**: Request and response logging
- ✅ **Error Handling**: Comprehensive error logging
- ✅ **State Management**: Upload progress and cleanup logging

### **Backend Integration**
- ✅ **Backend Running**: http://localhost:8000/health shows healthy
- ✅ **API Endpoint**: /api/v1/analysis/submit available
- ✅ **API Client**: Configured with proper headers and timeout

### **Next Steps**
1. **Test with browser console open** to see exact failure point
2. **Check Network tab** for HTTP request details
3. **Verify file type and size** meet requirements
4. **Test API endpoint directly** if needed

## 🎯 **Testing Instructions**

1. **Open http://localhost:3000/upload**
2. **Open Browser Console (F12)**
3. **Click file input and select telnet-raw.pcap**
4. **Watch console for debug messages**
5. **Check Network tab for HTTP requests**
6. **Report exact console output and error messages**

The comprehensive debugging will pinpoint exactly where the upload process is failing and provide actionable information to fix the issue.
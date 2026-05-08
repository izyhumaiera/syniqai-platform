# SyniqAI Bronze Layer - CustomTkinter GUI

## 🎨 Modern GUI Upgrade

This document describes the new **CustomTkinter** version of the SyniqAI Bronze Layer GUI.

---

## ✨ What Changed?

### **Visual Improvements**
✅ **Modern, rounded widgets** - Smoother, more professional appearance  
✅ **Enhanced dark theme** - Better contrast and readability  
✅ **Improved button styling** - More intuitive hover effects  
✅ **Cleaner scrolling** - Built-in smooth scrollbars  
✅ **Better spacing and padding** - More polished layout  

### **New Features**
✅ **☁️ Cloud Multi-Tenant Tab** - Dedicated section for MariaDB Cloud operations  
  - Import credentials from `readonly_users_list.json`
  - Test all users in batch
  - Extract data for all tenants
  - View results summary

### **Layout Preservation**
✅ **Exact same structure** - All original tabs and sections maintained  
✅ **Same functionality** - No features removed or modified  
✅ **Familiar workflow** - Same user experience, better visuals  

---

## 📁 Files

| File | Purpose |
|------|---------|
| `gui_ctk.py` | **New CustomTkinter GUI** (recommended) |
| `gui.py` | Original tkinter GUI (still functional) |

**Both GUIs work identically** - choose based on preference!

---

## 🚀 How to Run

### **Option 1: CustomTkinter GUI (Recommended)**
```powershell
python gui_ctk.py
```

### **Option 2: Original GUI**
```powershell
python gui.py
```

---

## 📊 Tab Overview

### **1. 🔌 Connection Tab**
Connect to PostgreSQL, MariaDB, or MariaDB Cloud (SkySQL)

**Fields:**
- Database Type (radio buttons)
- Host Address
- Port
- Database Name
- Username
- Password (with show/hide toggle)
- SSL Certificate (for Cloud)

**Actions:**
- 🔌 Connect to Database
- ✅ Test Connection
- 🔌 Disconnect

---

### **2. 📊 Extraction Tab**
Configure and execute single-table extraction

**Configuration:**
- 📋 Table Configuration
  - Table Name
  - Partition Column

- ⚡ Performance Configuration
  - 🤖 Auto-Optimize toggle
  - Chunk Size (with ➕➖ controls)
  - Workers (with ➕➖ controls)
  - 🔄 Reset button

- 🔄 Extraction Mode
  - Full Load
  - Incremental (with watermark settings)

- Output Directory

**Actions:**
- 🧮 Analyze Table (calculates optimal parameters)
- 🚀 Start Extraction
- ⏹ Stop

---

### **3. 📈 Monitoring Tab**
Real-time extraction statistics

**Metrics:**
- Total Rows
- Chunks Processed
- Elapsed Time
- Extraction Speed (rows/s)

---

### **4. ☁️ Cloud Multi-Tenant Tab** *(NEW!)*
Manage multiple MariaDB Cloud read-only users

**Workflow:**

#### **Step 1: Import Credentials**
1. Click **📁 Browse** to select `readonly_users_list.json`
2. Click **📥 Load Credentials**
3. View loaded users in the display area

**Expected JSON format:**
```json
[
  {
    "username": "analyst_readonly",
    "password": "secure_password",
    "host": "serverless-us-west-2.sysp0000.db1.skysql.com",
    "port": 4020,
    "database": "idp_ingestion_db",
    "ssl_ca": "C:/path/to/globalsignrootca.pem",
    "description": "Data analyst"
  }
]
```

#### **Step 2: Test All Users**
- Click **✅ Test All Users**
- GUI will test connection + security for each user
- Check logs for detailed results
- Final summary shows pass/fail count

#### **Step 3: Extract All Tenants**
- Enter table name in **Extraction tab**
- Return to **Cloud Multi-Tenant tab**
- Click **📦 Extract All Tenants**
- Confirm extraction
- Data saved to: `bronze_data_multi_tenant/{username}/`

#### **Step 4: View Results**
- Click **📊 View Results**
- Shows summary of all tenant data folders

---

## 🎯 Key Improvements Over Original GUI

| Feature | Original GUI | CustomTkinter GUI |
|---------|--------------|-------------------|
| Visual Style | Basic tkinter | Modern, rounded |
| Dark Theme | Manual styling | Built-in dark mode |
| Scrolling | Custom canvas | Native CTkScrollableFrame |
| Button Hover | Basic | Smooth animations |
| Multi-Tenant | None | Dedicated tab |
| Loading State | Text-based | Visual progress indicators |

---

## 🔧 Technical Details

### **Dependencies**
```python
customtkinter==5.2.0  # Modern UI framework
tkinter               # Built-in (for ScrolledText)
```

### **Color Scheme**
- **Appearance Mode:** Dark
- **Theme:** Blue
- **Accent Color:** #007acc (SyniqAI blue)
- **Background:** #1e1e1e (VS Code dark)

### **Widget Mapping**

| Original | CustomTkinter | Notes |
|----------|---------------|-------|
| `tk.Tk()` | `ctk.CTk()` | Root window |
| `ttk.Frame()` | `ctk.CTkFrame()` | Containers |
| `ttk.Label()` | `ctk.CTkLabel()` | Text labels |
| `ttk.Entry()` | `ctk.CTkEntry()` | Input fields |
| `ttk.Button()` | `ctk.CTkButton()` | Buttons |
| `ttk.Radiobutton()` | `ctk.CTkRadioButton()` | Radio buttons |
| `ttk.Checkbutton()` | `ctk.CTkCheckBox()` | Checkboxes |
| `ttk.Notebook()` | `ctk.CTkTabview()` | Tabs |
| `ttk.Progressbar()` | `ctk.CTkProgressBar()` | Progress bar |
| `scrolledtext.ScrolledText()` | `scrolledtext.ScrolledText()` | Console (unchanged) |

---

## 🧪 Testing Checklist

### **Connection Tab**
- [ ] Select PostgreSQL → fields update
- [ ] Select MariaDB → fields update
- [ ] Select MariaDB Cloud → SSL field required
- [ ] Connect → status badge turns green
- [ ] Test Connection → success message
- [ ] Disconnect → status badge turns red

### **Extraction Tab**
- [ ] Enter table name
- [ ] Toggle Auto-Optimize → chunk entry becomes readonly
- [ ] Click Analyze → optimal parameters calculated
- [ ] Adjust chunk size manually (disable auto first)
- [ ] Adjust workers manually
- [ ] Start extraction → progress bar animates

### **Monitoring Tab**
- [ ] Statistics update during extraction
- [ ] All 4 metric cards display correctly

### **Cloud Multi-Tenant Tab**
- [ ] Browse for JSON file → path displayed
- [ ] Load credentials → users displayed
- [ ] Test All Users → logs show results
- [ ] Extract All Tenants → folders created
- [ ] View Results → summary displayed

### **Menu Bar**
- [ ] File → Load Configuration
- [ ] File → Save Configuration
- [ ] File → Reset to Defaults
- [ ] Tools → Clear Logs
- [ ] Help → Documentation
- [ ] Help → Quick Start Guide
- [ ] Help → About

---

## 🎨 Customization

### **Change Theme**
Edit `gui_ctk.py` line 36-37:
```python
ctk.set_appearance_mode("dark")  # "dark", "light", or "system"
ctk.set_default_color_theme("blue")  # "blue", "green", or "dark-blue"
```

### **Adjust Window Size**
Edit line 42:
```python
self.root.geometry("1200x900")  # width x height
```

### **Modify Colors**
CustomTkinter uses semantic colors that adapt to theme:
- `fg_color` - Foreground/fill color
- `text_color` - Text color
- `hover_color` - Hover state color

---

## 🐛 Troubleshooting

### **Issue: GUI doesn't start**
**Solution:** Ensure CustomTkinter is installed:
```powershell
pip install customtkinter
```

### **Issue: Widgets look broken**
**Solution:** Update CustomTkinter to latest version:
```powershell
pip install --upgrade customtkinter
```

### **Issue: Console text not visible**
**Solution:** Check `ScrolledText` background/foreground colors (lines 177-178)

### **Issue: SSL certificate error (Cloud)**
**Solution:** Verify SSL certificate path is correct (no spaces, use forward slashes)

---

## 📚 Resources

- **CustomTkinter Documentation:** https://github.com/TomSchimansky/CustomTkinter
- **Original GUI:** `gui.py` (still functional)
- **Cloud Setup Guide:** `README_MARIADB_CLOUD.md`
- **Optimization Guide:** `OPTIMIZATION_SUMMARY.md`

---

## 🆚 Comparison: GUI vs CLI Scripts

| Task | GUI (gui_ctk.py) | CLI Scripts |
|------|------------------|-------------|
| **Single User Extraction** | ✅ Extraction Tab | `laptopB_idp_ingestion.py` |
| **Multi-User Testing** | ✅ Cloud Tab → Test All | `test_all_readonly_users.py` |
| **Multi-Tenant Extraction** | ✅ Cloud Tab → Extract All | `multi_tenant_ingestion.py` |
| **User Creation** | ❌ Not supported | `laptopA_create_readonly.py` |

**Recommendation:** Use GUI for extraction/testing, use CLI scripts for user creation.

---

## 🎯 Next Steps

1. **Test the GUI:**
   ```powershell
   python gui_ctk.py
   ```

2. **Load your credentials:**
   - Go to **☁️ Cloud Multi-Tenant tab**
   - Browse for `readonly_users_list.json`
   - Load credentials

3. **Test all users:**
   - Click **✅ Test All Users**
   - Verify all 3 users pass

4. **Extract data:**
   - Go to **📊 Extraction tab**
   - Enter table name: `user_credit_card_transaction`
   - Return to **☁️ Cloud Multi-Tenant tab**
   - Click **📦 Extract All Tenants**

5. **View results:**
   - Click **📊 View Results**
   - Check `bronze_data_multi_tenant/` folder

---

## 💡 Pro Tips

1. **Auto-Optimize**: Leave it ON for best performance (calculates optimal chunk size + workers)

2. **Analyze First**: Click **🧮 Analyze Table** before extraction to preview optimization

3. **Console Logs**: All operations log to the console at the bottom (with color coding)

4. **Save Config**: Use **File → Save Configuration** to save connection settings

5. **Multi-Tenant**: Import credentials once, then reuse for all operations

---

## 📝 Summary

**New GUI: `gui_ctk.py`**
- ✅ Modern CustomTkinter styling
- ✅ Exact same layout as original
- ✅ New Cloud Multi-Tenant tab
- ✅ All original features preserved
- ✅ Better visuals and UX

**Complement Approach:**
- GUI + CLI scripts both exist
- Use GUI for interactive testing/extraction
- Use CLI scripts for automation/scheduling
- Final results: Summary at end + logs during execution

**You can now manage all MariaDB Cloud operations from the GUI!** 🎉

# Reset PostgreSQL Password on Windows

## Steps to Reset Password:

### 1. Find and Edit pg_hba.conf
Open File Explorer and navigate to:
```
C:\Program Files\PostgreSQL\18\data\pg_hba.conf
```

### 2. Backup the File First
Right-click `pg_hba.conf` → Copy → Paste (creates "pg_hba - Copy.conf")

### 3. Edit with Administrator Rights
Right-click `pg_hba.conf` → Open with → Notepad (Run as Administrator)

### 4. Find These Lines (near the bottom):
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256
# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
```

### 5. Change "scram-sha-256" to "trust" temporarily:
```
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
```

### 6. Save the File

### 7. Restart PostgreSQL Service
Open PowerShell as Administrator and run:
```powershell
Restart-Service postgresql-x64-18
```

### 8. Connect Without Password
Now in pgAdmin, connect to PostgreSQL 18 - it won't ask for password!

### 9. Reset the Password
In pgAdmin:
- Right-click "Login/Group Roles" → "postgres"
- Go to "Definition" tab
- Enter new password: **postgres**
- Click Save

OR run this SQL:
```sql
ALTER USER postgres WITH PASSWORD 'postgres';
```

### 10. Restore pg_hba.conf Security
- Edit pg_hba.conf again
- Change "trust" back to "scram-sha-256"
- Save the file
- Restart PostgreSQL service again:
```powershell
Restart-Service postgresql-x64-18
```

### 11. Done!
Now you can connect with:
- Username: postgres
- Password: postgres

---

## Then Run Setup for SyniqAI:

After resetting the postgres password, run in pgAdmin SQL tool:
```sql
CREATE DATABASE syniqai_metadata;
CREATE USER syniqai_user WITH PASSWORD 'syniqai_password';
GRANT ALL PRIVILEGES ON DATABASE syniqai_metadata TO syniqai_user;
```

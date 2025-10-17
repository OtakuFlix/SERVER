"""
Database Inspector for Master Group ID Issues
==============================================
Run this script to diagnose master_group_id inconsistencies
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import hashlib
import re
from typing import Dict, List
from datetime import datetime

# ===== CONFIGURATION =====
MONGODB_URI = "mongodb+srv://mhsm:mhsm@cluster0.j9figvh.mongodb.net/?retryWrites=true&w=majority"  # Update with your MongoDB URI
MONGODB_DB = "to"  # Update with your database name

# ===== UTILITY FUNCTIONS =====
def generate_master_group_id(folder_id: str, name: str) -> str:
    """Generate master group ID (same logic as your utils)"""
    clean_name = name
    if '.' in name:
        parts = name.rsplit('.', 1)
        if len(parts) == 2 and parts[1].lower() in ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mp3', 'm4v']:
            clean_name = parts[0]
    
    clean_name = re.sub(
        r'\b(4320p|2160p|1440p|1080p|720p|480p|360p|240p|4K|2K|HD|FHD|UHD|8K)\b',
        '',
        clean_name,
        flags=re.IGNORECASE
    )
    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
    
    combined = f"{folder_id}:{clean_name}"
    return hashlib.md5(combined.encode()).hexdigest()[:24]

# ===== INSPECTION FUNCTIONS =====
async def inspect_database():
    """Main inspection function"""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    
    print("=" * 80)
    print("DATABASE INSPECTION REPORT")
    print("=" * 80)
    print(f"Database: {MONGODB_DB}")
    print(f"Timestamp: {datetime.now()}\n")
    
    # 1. Check Collections
    print("\n[1] CHECKING COLLECTIONS")
    print("-" * 80)
    collections = await db.list_collection_names()
    print(f"Available collections: {collections}")
    
    # 2. Analyze Folders
    print("\n[2] ANALYZING FOLDERS")
    print("-" * 80)
    folders = await db.folders.find({}).to_list(length=None)
    print(f"Total folders: {len(folders)}")
    
    for folder in folders[:5]:  # Show first 5
        print(f"\nFolder ID: {folder.get('folderId')}")
        print(f"  Name: {folder.get('name')}")
        print(f"  Type: {'Quality Folder' if folder.get('isQualityFolder') else 'Regular Folder'}")
        print(f"  Quality: {folder.get('quality', 'N/A')}")
        print(f"  Parent: {folder.get('parentFolderId', 'N/A')}")
        print(f"  File Count: {folder.get('fileCount', 0)}")
    
    # 3. Analyze Files and Master Group IDs
    print("\n[3] ANALYZING FILES AND MASTER GROUP IDs")
    print("-" * 80)
    files = await db.files.find({}).to_list(length=None)
    print(f"Total files: {len(files)}")
    
    # Check for master group ID field existence
    files_with_master_id = [f for f in files if 'masterGroupId' in f]
    files_without_master_id = [f for f in files if 'masterGroupId' not in f]
    
    print(f"Files WITH masterGroupId field: {len(files_with_master_id)}")
    print(f"Files WITHOUT masterGroupId field: {len(files_without_master_id)}")
    
    # 4. Specific Master Group ID Check
    print("\n[4] CHECKING SPECIFIC MASTER GROUP ID: 7cf053a11b2235711a5487e6")
    print("-" * 80)
    target_master_id = "7cf053a11b2235711a5487e6"
    
    # Method 1: Direct lookup
    direct_match = await db.files.find_one({'masterGroupId': target_master_id})
    print(f"Direct masterGroupId lookup: {'FOUND' if direct_match else 'NOT FOUND'}")
    
    if direct_match:
        print(f"  File ID: {direct_match['_id']}")
        print(f"  Folder ID: {direct_match.get('folderId')}")
        print(f"  Base Name: {direct_match.get('baseName')}")
        print(f"  Quality: {direct_match.get('quality')}")
    
    # Method 2: Check parent_master_group_id field
    parent_match = await db.files.find_one({'parent_master_group_id': target_master_id})
    print(f"parent_master_group_id lookup: {'FOUND' if parent_match else 'NOT FOUND'}")
    
    if parent_match:
        print(f"  File ID: {parent_match['_id']}")
        print(f"  Folder ID: {parent_match.get('folderId')}")
        print(f"  Base Name: {parent_match.get('baseName')}")
    
    # Method 3: Reverse engineer - find file with name "07" in folder "1"
    print("\n  Reverse engineering (looking for baseName='07' in folderId=1):")
    reverse_matches = await db.files.find({
        'folderId': 1,
        'baseName': '07'
    }).to_list(length=None)
    
    print(f"  Found {len(reverse_matches)} files matching criteria")
    for match in reverse_matches:
        computed_id = generate_master_group_id(str(match['folderId']), match['baseName'])
        print(f"\n  File: {match['_id']}")
        print(f"    Folder ID: {match['folderId']}")
        print(f"    Base Name: {match['baseName']}")
        print(f"    File Name: {match.get('fileName')}")
        print(f"    Quality: {match.get('quality')}")
        print(f"    Stored masterGroupId: {match.get('masterGroupId', 'MISSING')}")
        print(f"    Computed masterGroupId: {computed_id}")
        print(f"    Match with target: {computed_id == target_master_id}")
    
    # 5. Sample Files Analysis
    print("\n[5] SAMPLE FILES ANALYSIS (First 10 files)")
    print("-" * 80)
    for i, file in enumerate(files[:10], 1):
        print(f"\nFile #{i}: {file['_id']}")
        print(f"  Folder ID: {file.get('folderId')}")
        print(f"  File Name: {file.get('fileName')}")
        print(f"  Base Name: {file.get('baseName')}")
        print(f"  Quality: {file.get('quality')}")
        
        # Check if masterGroupId exists
        if 'masterGroupId' in file:
            print(f"  Stored masterGroupId: {file['masterGroupId']}")
        else:
            print(f"  Stored masterGroupId: MISSING")
        
        # Compute what it should be
        if file.get('folderId') and file.get('baseName'):
            computed = generate_master_group_id(str(file['folderId']), file['baseName'])
            print(f"  Computed masterGroupId: {computed}")
            
            if 'masterGroupId' in file:
                if file['masterGroupId'] == computed:
                    print(f"  Status: ✓ CORRECT")
                else:
                    print(f"  Status: ✗ MISMATCH")
            else:
                print(f"  Status: ⚠ MISSING FIELD")
    
    # 6. Field Existence Check
    print("\n[6] FIELD EXISTENCE ANALYSIS")
    print("-" * 80)
    
    all_fields = set()
    for file in files:
        all_fields.update(file.keys())
    
    print("Fields found in files collection:")
    for field in sorted(all_fields):
        count = sum(1 for f in files if field in f)
        print(f"  {field}: {count}/{len(files)} files ({count/len(files)*100:.1f}%)")
    
    # 7. Master Group ID Statistics
    print("\n[7] MASTER GROUP ID STATISTICS")
    print("-" * 80)
    
    master_ids = {}
    for file in files:
        mid = file.get('masterGroupId')
        if mid:
            if mid not in master_ids:
                master_ids[mid] = []
            master_ids[mid].append(file)
    
    print(f"Unique master group IDs: {len(master_ids)}")
    print(f"Files with duplicate master IDs:")
    
    for mid, file_list in sorted(master_ids.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        if len(file_list) > 1:
            print(f"\n  Master ID: {mid}")
            print(f"  Files: {len(file_list)}")
            for f in file_list:
                print(f"    - {f.get('fileName')} (Quality: {f.get('quality')})")
    
    # 8. Folder ID Type Check
    print("\n[8] FOLDER ID TYPE CONSISTENCY CHECK")
    print("-" * 80)
    
    folder_id_types = {}
    for file in files:
        fid = file.get('folderId')
        fid_type = type(fid).__name__
        if fid_type not in folder_id_types:
            folder_id_types[fid_type] = 0
        folder_id_types[fid_type] += 1
    
    print("Folder ID types in files collection:")
    for ftype, count in folder_id_types.items():
        print(f"  {ftype}: {count} files")
    
    folder_id_types_folders = {}
    for folder in folders:
        fid = folder.get('folderId')
        fid_type = type(fid).__name__
        if fid_type not in folder_id_types_folders:
            folder_id_types_folders[fid_type] = 0
        folder_id_types_folders[fid_type] += 1
    
    print("\nFolder ID types in folders collection:")
    for ftype, count in folder_id_types_folders.items():
        print(f"  {ftype}: {count} folders")
    
    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)
    
    client.close()

# ===== RUN =====
if __name__ == "__main__":
    asyncio.run(inspect_database())
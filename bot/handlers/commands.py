from pyrogram import filters
from pyrogram.types import Message
from bot.keyboards import main_menu_kb
from database.operations import get_stats, create_folder, generate_next_folder_id
import secrets
import string

from bot.handlers.helpers import show_folders_page, show_folder_contents


def register_command_handlers(bot):

    @bot.on_message(filters.command(["start", "menu"]) & filters.private)
    async def start_command(client, message: Message):
        user = message.from_user
        
        welcome_text = f"""
╔══════════════════╗
║   🎬 Tᴇʟᴇ Sᴛᴏʀᴇ Bᴏᴛ 🎬     ║
╚══════════════════╝

👋 Wᴇʟᴄᴏᴍᴇ {user.first_name}!

🌟 Yᴏᴜʀ Pᴇʀsᴏɴᴀʟ Cʟᴏᴜᴅ Sᴛᴏʀᴀɢᴇ Sᴏʟᴜᴛɪᴏɴ

✨ Kᴇʏ Fᴇᴀᴛᴜʀᴇs:
- 📁 Oʀɢᴀɴɪᴢᴇ ғɪʟᴇs ɪɴ ғᴏʟᴅᴇʀs & sᴜʙғᴏʟᴅᴇʀs
- 🎥 Mᴜʟᴛɪ-ǫᴜᴀʟɪᴛʏ sᴜᴘᴘᴏʀᴛ (4K ᴛᴏ 360ᴘ)
- 🔗 Iɴsᴛᴀɴᴛ sᴛʀᴇᴀᴍɪɴɢ ʟɪɴᴋs
- ⬇️ Dɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ sᴜᴘᴘᴏʀᴛ
- 🌐 Eᴍʙᴇᴅᴅᴀʙʟᴇ ᴠɪᴅᴇᴏ ᴘʟᴀʏᴇʀ
- 💾 Dᴀᴛᴀʙᴀsᴇ ʙᴀᴄᴋᴜᴘ & ʀᴇsᴛᴏʀᴇ
- 📊 Dᴇᴛᴀɪʟᴇᴅ sᴛᴀᴛɪsᴛɪᴄs ᴛʀᴀᴄᴋɪɴɢ
- 📜 Aᴘɪ sᴜᴘᴘᴏʀᴛ

🚀 Qᴜɪᴄᴋ Sᴛᴀʀᴛ:
1️⃣ Cʀᴇᴀᴛᴇ ᴀ ғᴏʟᴅᴇʀ ᴡɪᴛʜ /newfolder
2️⃣ Uᴘʟᴏᴀᴅ ғɪʟᴇs ᴡɪᴛʜ ǫᴜᴀʟɪᴛʏ ᴛᴀɢs
3️⃣ Gᴇᴛ sʜᴀʀᴇᴀʙʟᴇ ʟɪɴᴋs ɪɴsᴛᴀɴᴛʟʏ

💡 Aᴜᴛᴏ Uᴘʟᴏᴀᴅ Fᴏʀᴍᴀᴛ:
`<Folder><File><Quality><Size>`

Exᴀᴍᴘʟᴇ: 
`<My Movies><Movie.mp4><1080p><2.5GB>`

Usᴇ ᴛʜᴇ ʙᴜᴛᴛᴏɴs ʙᴇʟᴏᴡ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ! 👇
"""
        
        await message.reply_photo(
            photo="https://iili.io/KvfAsPp.jpg",
            caption=welcome_text,
            reply_markup=main_menu_kb()
        )

    @bot.on_message(filters.command("api") & filters.private)
    async def api_command(client, message: Message):
        api_text = """
┏━━━━━━━━━━━┓
┃  🗂 Cᴏᴍᴘʟᴇᴛᴇ Aᴘɪ Dᴏᴄs ┃
┗━━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  GET `/api/folder_list?user_id={1740287480}&page={1}&page_size={200}`
- qᴜᴇʀʏ ᴘᴀʀᴀᴍs: user_id (int), parent_id (str, optional), page (int), page_size (int)
- sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:
```json
{
  "success": "hi",
  "folders": ["hi"],
  "page": "hi",
  "pageSize": "hi"
}```
━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣ GET `/api/file_list/{folder_id}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: folder_id (str)

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "folderId": "hi",
  "folderName": "hi",
  "files": ["hi"]
}```
━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣ GET `/api/stream/{master_group_id}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: master_group_id (str)

qᴜᴇʀʏ: quality (str, default="1080p")

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "message": "hi",
  "fileId": "hi",
  "streamUrl": "hi",
  "watchUrl": "hi",
  "downloadUrl": "hi",
  "quality": "hi",
  "fileName": "hi",
  "size": "hi"
}```
━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣ GET `/api/quality_info/{file_id}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: file_id (str)

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "master_group_id": "hi",
  "baseName": "hi",
  "qualities": ["hi"]
}```
━━━━━━━━━━━━━━━━━━━━━━━━

5️⃣ GET `/api/s_file_list/{folder_id}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: folder_id (str)

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "folderId": "hi",
  "folderName": "hi",
  "fileGroups": ["hi"]
}```
━━━━━━━━━━━━━━━━━━━━━━━━

6️⃣ GET `/api/quality_folders/{parent_folder_id}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: parent_folder_id (str)

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "parentFolderId": "hi",
  "parentFolderName": "hi",
  "qualityFolders": ["hi"]
}```
━━━━━━━━━━━━━━━━━━━━━━━━

7️⃣ GET `/api/files_by_name/{folder_id}/{base_name}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: folder_id (str), base_name (str)

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "folderId": "hi",
  "baseName": "hi",
  "master_group_id": "hi",
  "files": ["hi"]
}```
━━━━━━━━━━━━━━━━━━━━━━━━

8️⃣ GET `/api/master_info/{master_group_id}`

ᴘᴀᴛʜ ᴘᴀʀᴀᴍs: master_group_id (str)

sᴀᴍᴘʟᴇ ʀᴇsᴘᴏɴsᴇ:

```json
{
  "success": "hi",
  "master_group_id": "hi",
  "folderId": "hi",
  "baseName": "hi",
  "qualities": ["hi"],
  "totalFiles": "hi"
}```
━━━━━━━━━━━━━━━━━━━━━━━━

💬 ɴᴇᴇᴅ ʜᴇʟᴘ? ᴄᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ!
"""
        await message.reply_text(api_text)

    @bot.on_message(filters.command("help") & filters.private)
    async def help_command(client, message: Message):
        help_text = """
┏━━━━━━━━━━┓
┃  📖 Cᴏᴍᴘʟᴇᴛᴇ Gᴜɪᴅᴇ  ┃
┗━━━━━━━━━━┛

━━━━━━━━━━━━━━━━━━━━━━━━

📁 CREATING FOLDERS

Cᴏᴍᴍᴀɴᴅ: `/newfolder <name>`
Exᴀᴍᴘʟᴇ: `/newfolder My Movies`
Fᴏʟᴅᴇʀs ɢᴇᴛ ᴀᴜᴛᴏ-ɴᴜᴍʙᴇʀᴇᴅ IDs (1, 2, 3...)

━━━━━━━━━━━━━━━━━━━━━━━━

📤 UPLOADING FILES

Mᴇᴛʜᴏᴅ 1: Aᴜᴛᴏ Uᴘʟᴏᴀᴅ (Rᴇᴄᴏᴍᴍᴇɴᴅᴇᴅ)
Sᴇɴᴅ ғɪʟᴇ ᴡɪᴛʜ ᴄᴀᴘᴛɪᴏɴ ɪɴ ᴛʜɪs ғᴏʀᴍᴀᴛ:
`<Folder><Filename><Quality><Size>`

Exᴀᴍᴘʟᴇ:
`<Action Movies><Avengers.mp4><1080p><2.5GB>`

Mᴇᴛʜᴏᴅ 2: Mᴀɴᴜᴀʟ Uᴘʟᴏᴀᴅ
1. Oᴘᴇɴ ғᴏʟᴅᴇʀ ғʀᴏᴍ ᴍᴇɴᴜ
2. Cʟɪᴄᴋ "Aᴅᴅ Fɪʟᴇs"
3. Sᴇʟᴇᴄᴛ ǫᴜᴀʟɪᴛʏ (4K/1080ᴘ/720ᴘ/480ᴘ/360ᴘ)
4. Sᴇɴᴅ ʏᴏᴜʀ ғɪʟᴇs
5. Usᴇ /done ᴡʜᴇɴ ғɪɴɪsʜᴇᴅ

━━━━━━━━━━━━━━━━━━━━━━━━

🔗 GETTING LINKS

Cʟɪᴄᴋ ᴀɴʏ ғɪʟᴇ ᴛᴏ ɢᴇᴛ:
  • ▶️ Wᴀᴛᴄʜ Lɪɴᴋ (sᴛʀᴇᴀᴍɪɴɢ ᴘʟᴀʏᴇʀ)
  • ⬇️ Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋ (ᴅɪʀᴇᴄᴛ ᴅᴏᴡɴʟᴏᴀᴅ)
  • 📋 Eᴍʙᴇᴅ Lɪɴᴋ (ғᴏʀ ᴡᴇʙsɪᴛᴇs)

━━━━━━━━━━━━━━━━━━━━━━━━

📊 BULK OPERATIONS

Fʀᴏᴍ ᴀɴʏ ғᴏʟᴅᴇʀ, ɢᴇᴛ ᴀʟʟ ʟɪɴᴋs ᴀᴛ ᴏɴᴄᴇ:
- 🔗 Aʟʟ Eᴍʙᴇᴅ Lɪɴᴋs
- ⬇️ Aʟʟ Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋs
- ▶️ Aʟʟ Wᴀᴛᴄʜ Lɪɴᴋs

━━━━━━━━━━━━━━━━━━━━━━━━

💾 DATABASE MANAGEMENT

- `/vanish` - Exᴘᴏʀᴛ ғᴜʟʟ ᴅᴀᴛᴀʙᴀsᴇ ʙᴀᴄᴋᴜᴘ
- `/retrieve` - Rᴇsᴛᴏʀᴇ ғʀᴏᴍ ʙᴀᴄᴋᴜᴘ JSON

━━━━━━━━━━━━━━━━━━━━━━━━

🎥 SUPPORTED FORMATS

MP4, MKV, AVI, MOV, WMV, FLV, WEBM, ᴀɴᴅ ᴍᴏʀᴇ!

━━━━━━━━━━━━━━━━━━━━━━━━

🔧 FEATURES

- Aᴜᴛᴏ ǫᴜᴀʟɪᴛʏ ᴅᴇᴛᴇᴄᴛɪᴏɴ
- Lᴀɴɢᴜᴀɢᴇ ᴅᴇᴛᴇᴄᴛɪᴏɴ
- Mᴇᴛᴀᴅᴀᴛᴀ ᴇxᴛʀᴀᴄᴛɪᴏɴ
- Mᴀsᴛᴇʀ ɢʀᴏᴜᴘ ʟɪɴᴋɪɴɢ
- Rᴇᴀʟ-ᴛɪᴍᴇ sᴛᴀᴛɪsᴛɪᴄs
- Mᴜʟᴛɪ-ǫᴜᴀʟɪᴛʏ sᴜᴘᴘᴏʀᴛ
- Aᴘɪ sᴜᴘᴘᴏʀᴛ

━━━━━━━━━━━━━━━━━━━━━━━━

💬 Nᴇᴇᴅ ʜᴇʟᴘ? Cᴏɴᴛᴀᴄᴛ sᴜᴘᴘᴏʀᴛ!
        """
        await message.reply_text(help_text, reply_markup=main_menu_kb())

    @bot.on_message(filters.command("newfolder") & filters.private)
    async def newfolder_command(client, message: Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text(
                """
❌ Mɪssɪɴɢ ғᴏʟᴅᴇʀ ɴᴀᴍᴇ!

Usᴀɢᴇ: `/newfolder <name>`

Exᴀᴍᴘʟᴇs:
- `/newfolder My Movies`
- `/newfolder TV Shows 2024`
- `/newfolder Anime Collection`
                """
            )
            return

        folder_name = parts[1].strip()
        if len(folder_name) < 2:
            await message.reply_text("❌ Fᴏʟᴅᴇʀ ɴᴀᴍᴇ ᴍᴜsᴛ ʙᴇ ᴀᴛ ʟᴇᴀsᴛ 2 ᴄʜᴀʀᴀᴄᴛᴇʀs ʟᴏɴɢ.")
            return

        folder_id = await generate_next_folder_id()

        await create_folder(folder_id=folder_id, name=folder_name, created_by=message.from_user.id)

        await message.reply_text(
            f"""
✅ Fᴏʟᴅᴇʀ ᴄʀᴇᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!

📁 Nᴀᴍᴇ: {folder_name}
🆔 Fᴏʟᴅᴇʀ ID: `{folder_id}`
📊 Sᴛᴀᴛᴜs: Rᴇᴀᴅʏ ғᴏʀ ᴜᴘʟᴏᴀᴅs

Nᴇxᴛ Sᴛᴇᴘs:
1. Oᴘᴇɴ ғᴏʟᴅᴇʀ ғʀᴏᴍ /myfolders
2. Cʟɪᴄᴋ 'Aᴅᴅ Fɪʟᴇs'
3. Sᴇʟᴇᴄᴛ ǫᴜᴀʟɪᴛʏ ᴀɴᴅ ᴜᴘʟᴏᴀᴅ

Oʀ ᴜsᴇ ᴀᴜᴛᴏ-ᴜᴘʟᴏᴀᴅ ғᴏʀᴍᴀᴛ:
`<{folder_name}><filename><quality><size>`
            """,
            reply_markup=main_menu_kb()
        )

    @bot.on_message(filters.command("stats") & filters.private)
    async def stats_command(client, message: Message):
        stats = await get_stats(message.from_user.id)
        
        stats_text = f"""
┏━━━━━━━━━━┓
┃  📊 Yᴏᴜʀ Sᴛᴀᴛɪsᴛɪᴄs  ┃
┗━━━━━━━━━━┛

📁 Fᴏʟᴅᴇʀs: {stats['folders']}
🎬 Tᴏᴛᴀʟ Fɪʟᴇs: {stats['files']}
💾 Sᴛᴏʀᴀɢᴇ Usᴇᴅ: {stats['total_size_mb']:.2f} MB
👁️ Tᴏᴛᴀʟ Vɪᴇᴡs: {stats.get('views', 0):,}
⬇️ Tᴏᴛᴀʟ Dᴏᴡɴʟᴏᴀᴅs: {stats.get('downloads', 0):,}

━━━━━━━━━━━━━━━━━━━━━━━━

💡 Tɪᴘ: Kᴇᴇᴘ ᴜᴘʟᴏᴀᴅɪɴɢ ᴛᴏ ᴇxᴘᴀɴᴅ ʏᴏᴜʀ ʟɪʙʀᴀʀʏ!
"""
        
        await message.reply_text(
            stats_text,
            reply_markup=main_menu_kb()
        )

    @bot.on_message(filters.command("myfolders") & filters.private)
    async def myfolders_command(client, message: Message):
        await show_folders_page(message, page=1, edit=False)

    @bot.on_message(filters.command("cancel") & filters.private)
    async def cancel_command(client, message: Message):
        from bot.handlers.callbacks import user_rename_context
        
        user_id = message.from_user.id
        if user_id in user_rename_context:
            del user_rename_context[user_id]
            await message.reply_text(
                "❌ Oᴘᴇʀᴀᴛɪᴏɴ ᴄᴀɴᴄᴇʟʟᴇᴅ.",
                reply_markup=main_menu_kb()
            )
        else:
            await message.reply_text("Nᴏ ᴏᴘᴇʀᴀᴛɪᴏɴ ᴛᴏ ᴄᴀɴᴄᴇʟ.")
    @bot.on_message(filters.command("vanish") & filters.private)
    async def vanish_command(client, message: Message):
        """Handle /vanish command - Export database backup"""
        from database.backup import export_database
        from config import config
        import os
        
        user_id = message.from_user.id
        
        status_msg = await message.reply_text(
            "🔄 **Exporting database...**\n\n"
            "⏳ This may take a moment...\n"
            "📦 Packaging all your data..."
        )
        
        try:
            json_file = await export_database()
            
            if not os.path.exists(json_file):
                await status_msg.edit_text("❌ Failed to create backup file.")
                return
            
            file_size = os.path.getsize(json_file) / (1024 * 1024)
            
            await status_msg.edit_text(
                f"📤 **Uploading backup...**\n\n"
                f"💾 Size: {file_size:.2f} MB\n"
                f"📊 Processing complete..."
            )
            
            from datetime import datetime
            backup_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            
            caption = (
                f"📦 **Database Backup Export**\n\n"
                f"📅 **Date:** {backup_time}\n"
                f"💾 **Size:** {file_size:.2f} MB\n"
                f"👤 **Requested by:** {message.from_user.first_name} ({user_id})\n\n"
                f"⚠️ **Security Notice:**\n"
                f"• Keep this file in a secure location\n"
                f"• Don't share with unauthorized users\n"
                f"• Contains all your folder/file data\n\n"
                f"🔄 Use `/retrieve` to restore this backup"
            )
            
            if config.CHANNEL_ID:
                try:
                    await client.send_document(
                        chat_id=config.CHANNEL_ID,
                        document=json_file,
                        caption=caption
                    )
                except Exception as e:
                    print(f"[VANISH] Error sending to channel: {e}")
            
            await client.send_document(
                chat_id=message.chat.id,
                document=json_file,
                caption="✅ **Backup created successfully!**\n\n"
                        "📥 **Save this file safely!**\n"
                        "🔒 Keep it in a secure location\n"
                        "🔄 Use /retrieve to restore when needed\n\n"
                        "💡 Backup includes:\n"
                        "• All folders and subfolders\n"
                        "• All file metadata\n"
                        "• Quality mappings\n"
                        "• Statistics data"
            )
            
            await status_msg.delete()
            
            os.remove(json_file)
            print(f"[VANISH] Backup file deleted from server: {json_file}")
            
        except Exception as e:
            print(f"[VANISH] Error: {e}")
            await status_msg.edit_text(
                f"❌ **Error creating backup:**\n\n"
                f"```{str(e)}```\n\n"
                f"Please try again or contact support."
            )

    @bot.on_message(filters.command("retrieve") & filters.private)
    async def retrieve_command(client, message: Message):
        """Handle /retrieve command - Prompt for backup file"""
        from bot.handlers.backup_handlers import user_waiting_for_json
        
        user_id = message.from_user.id
        user_waiting_for_json[user_id] = True
        
        await message.reply_text(
            "📥 **Database Restore Mode Activated**\n\n"
            "**━━━━━━━━━━━━━━━━━━━━**\n\n"
            "Please send me the JSON backup file you want to restore.\n\n"
            "⚠️ **Important Information:**\n\n"
            "✓ Data will be imported into current database\n"
            "✓ Existing data will NOT be deleted\n"
            "✓ Duplicate entries will be skipped\n"
            "✗ This operation cannot be undone\n\n"
            "**━━━━━━━━━━━━━━━━━━━━**\n\n"
            "📎 **Send the `.json` file now**\n"
            "🚫 Or use /cancel to abort\n\n"
            "💡 Make sure it's the correct backup file!"
        )
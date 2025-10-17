from pyrogram import filters
from database.operations import get_or_create_quality_folder
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.keyboards import (
    main_menu_kb, folders_kb, folder_view_kb,
    file_actions_kb, confirm_delete_kb, quality_selection_kb,
    quality_folder_view_kb, files_by_basename_kb
)
from database.operations import (
    get_user_folders, get_folder_files, get_file_by_id,
    delete_file, delete_folder, get_folder_by_id, get_stats,
    count_user_folders, count_folder_files, get_quality_folders,
    get_simplified_file_list, get_files_by_basename, get_all_folder_files,
    update_file
)
from bot.handlers.helpers import show_folders_page, show_folder_contents, show_quality_folders, show_files_by_basename
from config import config
from database.connection import get_database
import html
import os
from urllib.parse import urlparse
import math

PAGE_SIZE = 8

user_rename_context = {}

def register_callback_handlers(bot):

    @bot.on_callback_query(filters.regex(r"^main_menu$"))
    async def main_menu_callback(bot_instance, callback: CallbackQuery):
        welcome_text = f"""
╔═══════════════════════════╗
║   🎬 Tᴇʟᴇ Sᴛᴏʀᴇ Bᴏᴛ 🎬   ║
╚═══════════════════════════╝

👋 Wᴇʟᴄᴏᴍᴇ ʙᴀᴄᴋ {callback.from_user.first_name}!

Cʜᴏᴏsᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ:
"""
        await callback.message.edit_text(
            welcome_text,
            reply_markup=main_menu_kb()
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^folders:\d+$"))
    async def folders_callback(bot_instance, callback: CallbackQuery):
        page = int(callback.data.split(":")[1])
        user_id = callback.from_user.id if callback.from_user else None
        await show_folders_page(callback.message, page, edit=True, user_id=user_id)
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^folder:[\w]+:\d+$"))
    async def folder_view_callback(bot_instance, callback: CallbackQuery):
        parts = callback.data.split(":")
        folder_id = parts[1]
        page = int(parts[2])
        
        folder = await get_folder_by_id(folder_id)
        if not folder:
            await callback.answer("❌ Fᴏʟᴅᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        quality_folders = await get_quality_folders(folder_id)
        
        if not quality_folders:
            await callback.answer("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        db = get_database()
        quality_folder_ids = [qf['folderId'] for qf in quality_folders]
        
        pipeline = [
            {'$match': {'folderId': {'$in': quality_folder_ids}}},
            {'$group': {
                '_id': '$baseName',
                'baseName': {'$first': '$baseName'},
                'parent_master_group_id': {'$first': '$parent_master_group_id'},
                'fileCount': {'$sum': 1},
                'qualities': {'$addToSet': '$quality'}
            }},
            {'$sort': {'baseName': 1}}
        ]
        
        cursor = db.files.aggregate(pipeline)
        file_groups = await cursor.to_list(length=None)
        
        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"
        
        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"
        
        text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📁 {html.escape(folder['name'])}
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📊 Tᴏᴛᴀʟ Fɪʟᴇs: {len(file_groups)}

"""
        
        buttons = []
        for idx, group in enumerate(file_groups[:10], 1):
            base_name = group['baseName']
            master_id = group.get('parent_master_group_id')
            file_count = group.get('fileCount', 0)
            qualities = sorted(group.get('qualities', []))
            quality_str = ", ".join(qualities)
            
            name_without_ext = os.path.splitext(base_name)[0]
            
            buttons.append([
                InlineKeyboardButton(
                    f"{idx}. {name_without_ext[:35]} [{quality_str}]",
                    callback_data=f"master:{master_id}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton("🔗 Aʟʟ Eᴍʙᴇᴅ Lɪɴᴋs", callback_data=f"all_embeds:{folder_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("⬇️ Aʟʟ Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋs", callback_data=f"all_downloads:{folder_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("▶️ Aʟʟ Wᴀᴛᴄʜ Lɪɴᴋs", callback_data=f"all_watch:{folder_id}"),
        ])
        buttons.append([
            InlineKeyboardButton("➕ Aᴅᴅ Fɪʟᴇs", callback_data=f"add_files:{folder_id}"),
            InlineKeyboardButton("✏️ Rᴇɴᴀᴍᴇ", callback_data=f"rename_folder:{folder_id}")
        ])
        buttons.append([
            InlineKeyboardButton("🗑 Dᴇʟᴇᴛᴇ Fᴏʟᴅᴇʀ", callback_data=f"delete_folder:{folder_id}"),
            InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data="folders:1")
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^master:[a-f0-9]{24}$"))
    async def master_group_callback(bot_instance, callback: CallbackQuery):
        master_id = callback.data.split(":")[1]
        
        db = get_database()
        matched_files = await db.files.find({
            'parent_master_group_id': master_id
        }).to_list(length=None)
        
        if not matched_files:
            await callback.answer("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        base_name = matched_files[0].get('baseName')
        folder_id = matched_files[0].get('folderId')
        
        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"
        
        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"
        
        embed_url = f"{base_url}/embed/master/{master_id}"
        watch_url = f"{base_url}/watch/master/{master_id}"
        
        text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📦 {html.escape(base_name)}
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

🔗 Mᴀsᴛᴇʀ ID: `{master_id}`

━━━━━━━━━━━━━━━━━━━━━━━━

🎥 Aᴠᴀɪʟᴀʙʟᴇ Qᴜᴀʟɪᴛɪᴇs:

"""
        
        buttons = []
        for file in matched_files:
            quality = file.get('quality', 'Unknown')
            size_mb = file.get('size', 0) / (1024 * 1024)
            file_id = str(file['_id'])
            
            text += f"  • {quality} - {size_mb:.1f} MB\n"
            
            buttons.append([
                InlineKeyboardButton(
                    f"🎬 {quality} ({size_mb:.1f} MB)",
                    callback_data=f"file:{file_id}"
                )
            ])
        
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        buttons.append([
            InlineKeyboardButton("🔗 Eᴍʙᴇᴅ Lɪɴᴋ", url=embed_url),
            InlineKeyboardButton("▶️ Wᴀᴛᴄʜ", url=watch_url)
        ])
        buttons.append([
            InlineKeyboardButton("⬇️ Dᴏᴡɴʟᴏᴀᴅ Oᴘᴛɪᴏɴs", callback_data=f"download_options:{master_id}")
        ])
        buttons.append([
            InlineKeyboardButton("✏️ Rᴇɴᴀᴍᴇ Gʀᴏᴜᴘ", callback_data=f"rename_master:{master_id}"),
            InlineKeyboardButton("🗑 Dᴇʟᴇᴛᴇ Aʟʟ", callback_data=f"delete_master:{master_id}")
        ])
        buttons.append([
            InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data=f"folder:{folder_id}:1")
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^download_options:[a-f0-9]{24}$"))
    async def download_options_callback(bot_instance, callback: CallbackQuery):
        master_id = callback.data.split(":")[1]
        
        db = get_database()
        matched_files = await db.files.find({
            'parent_master_group_id': master_id
        }).to_list(length=None)
        
        if not matched_files:
            await callback.answer("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        base_name = matched_files[0].get('baseName')
        
        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"
        
        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"
        
        text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⬇️ Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📦 {html.escape(base_name)}

━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for idx, file in enumerate(matched_files, 1):
            quality = file.get('quality', 'Unknown')
            size_mb = file.get('size', 0) / (1024 * 1024)
            file_id = str(file['_id'])
            download_url = f"{base_url}/dl/{file_id}"
            
            text += f"{idx}. {quality} ({size_mb:.1f} MB)\n"
            text += f"   `{download_url}`\n\n"
        
        buttons = [
            [InlineKeyboardButton("⬅️ Bᴀᴄᴋ", callback_data=f"master:{master_id}")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^rename_master:[a-f0-9]{24}$"))
    async def rename_master_callback(bot_instance, callback: CallbackQuery):
        master_id = callback.data.split(":")[1]
        user_id = callback.from_user.id
        
        user_rename_context[user_id] = {'type': 'master', 'id': master_id}
        
        await callback.message.edit_text(
            """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ✏️ Rᴇɴᴀᴍᴇ Fɪʟᴇ Gʀᴏᴜᴘ
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ɴᴀᴍᴇ ғᴏʀ ᴛʜɪs ғɪʟᴇ ɢʀᴏᴜᴘ.

Usᴇ /cancel ᴛᴏ ᴀʙᴏʀᴛ.
            """,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cᴀɴᴄᴇʟ", callback_data=f"master:{master_id}")
            ]])
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^delete_master:[a-f0-9]{24}$"))
    async def delete_master_callback(bot_instance, callback: CallbackQuery):
        master_id = callback.data.split(":")[1]
        
        db = get_database()
        matched_files = await db.files.find({
            'parent_master_group_id': master_id
        }).to_list(length=None)
        
        if not matched_files:
            await callback.answer("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        base_name = matched_files[0].get('baseName')
        folder_id = matched_files[0].get('folderId')
        
        text = f"""
⚠️ Dᴇʟᴇᴛᴇ Eɴᴛɪʀᴇ Gʀᴏᴜᴘ?

📦 {html.escape(base_name)}

Tʜɪs ᴡɪʟʟ ᴅᴇʟᴇᴛᴇ {len(matched_files)} ғɪʟᴇ(s) ɪɴ ᴀʟʟ ǫᴜᴀʟɪᴛɪᴇs.
Tʜɪs ᴀᴄᴛɪᴏɴ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜɴᴅᴏɴᴇ!
        """
        
        buttons = [
            [InlineKeyboardButton("✅ Yᴇs, Dᴇʟᴇᴛᴇ Aʟʟ", callback_data=f"confirm_delete_master:{master_id}")],
            [InlineKeyboardButton("❌ Cᴀɴᴄᴇʟ", callback_data=f"master:{master_id}")]
        ]
        
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^confirm_delete_master:[a-f0-9]{24}$"))
    async def confirm_delete_master_callback(bot_instance, callback: CallbackQuery):
        master_id = callback.data.split(":")[1]
        
        db = get_database()
        matched_files = await db.files.find({
            'parent_master_group_id': master_id
        }).to_list(length=None)
        
        if not matched_files:
            await callback.answer("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        folder_id = matched_files[0].get('folderId')
        
        deleted_count = 0
        for file in matched_files:
            file_id = str(file['_id'])
            success = await delete_file(file_id)
            if success:
                deleted_count += 1
        
        await callback.answer(f"✅ Dᴇʟᴇᴛᴇᴅ {deleted_count} ғɪʟᴇ(s)!", show_alert=True)
        await callback.message.edit_text(
            f"✅ Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ {deleted_count} ғɪʟᴇ(s)!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Bᴀᴄᴋ ᴛᴏ Fᴏʟᴅᴇʀ", callback_data=f"folder:{folder_id}:1")
            ]])
        )

    @bot.on_callback_query(filters.regex(r"^quality_folder:[\w]+:\d+$"))
    async def quality_folder_callback(bot_instance, callback: CallbackQuery):
        parts = callback.data.split(":")
        quality_folder_id = parts[1]
        page = int(parts[2])
        user_id = callback.from_user.id if callback.from_user else None
        await show_folder_contents(callback.message, quality_folder_id, page, edit=True, user_id=user_id)
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^basename:[\w]+:"))
    async def basename_view_callback(bot_instance, callback: CallbackQuery):
        parts = callback.data.split(":", 2)
        folder_id = parts[1]
        base_name = parts[2]
        await show_files_by_basename(callback.message, folder_id, base_name, edit=True)
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^all_embeds:[\w]+$"))
    async def all_embeds_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]

        folder = await get_folder_by_id(folder_id)
        if not folder:
            await callback.answer("❌ Fᴏʟᴅᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        await callback.answer("🔄 Gᴇɴᴇʀᴀᴛɪɴɢ ᴇᴍʙᴇᴅ ʟɪɴᴋs...", show_alert=False)

        quality_folders = await get_quality_folders(folder_id)
        all_files = []

        if not quality_folders:
            files = await get_all_folder_files(folder_id)
            all_files.extend(files)
        else:
            for qf in quality_folders:
                files = await get_all_folder_files(qf['folderId'])
                all_files.extend(files)

        if not all_files:
            await callback.message.reply_text("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ ɪɴ ᴛʜɪs ғᴏʟᴅᴇʀ!")
            return

        file_groups = {}
        for file in all_files:
            base_name = file.get("baseName")
            parent_master_group_id = file.get("parent_master_group_id")
            master_group_id = file.get("masterGroupId")
            master_id = parent_master_group_id or master_group_id

            if not base_name:
                continue

            if base_name not in file_groups:
                file_groups[base_name] = {
                    "base_name": base_name,
                    "master_group_id": master_id,
                    "files": []
                }

            file_groups[base_name]["files"].append(file)

        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"

        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"

        max_message_length = 3500
        text_chunks = []
        current_chunk = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🎬 Aʟʟ Eᴍʙᴇᴅ Lɪɴᴋs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📁 {html.escape(folder['name'])}

━━━━━━━━━━━━━━━━━━━━━━━━

"""
        btn_rows = []
        group_count = 0

        for base_name, group in sorted(file_groups.items()):
            master_group_id = group.get("master_group_id")
            if not master_group_id:
                continue

            embed_url = f"{base_url}/embed/master/{master_group_id}"
            name_without_ext = os.path.splitext(base_name)[0]
            escaped_name = html.escape(f"E{name_without_ext}")
            line = f"• {escaped_name}\n   `{embed_url}`\n"
            
            if len(current_chunk) + len(line) > max_message_length:
                text_chunks.append((current_chunk, btn_rows))
                current_chunk = ""
                btn_rows = []

            current_chunk += line
            group_count += 1

        if current_chunk:
            text_chunks.append((current_chunk, btn_rows))

        for text, rows in text_chunks:
            rows.append([InlineKeyboardButton("⬅️ Bᴀᴄᴋ ᴛᴏ Fᴏʟᴅᴇʀ", callback_data=f"folder:{folder_id}:1")])
            await callback.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(rows),
                disable_web_page_preview=True
            )

        await callback.answer(f"✅ Gᴇɴᴇʀᴀᴛᴇᴅ {group_count} ᴇᴍʙᴇᴅ ʟɪɴᴋs!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^all_downloads:[\w]+$"))
    async def all_downloads_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]
        
        folder = await get_folder_by_id(folder_id)
        if not folder:
            await callback.answer("❌ Fᴏʟᴅᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        await callback.answer("🔄 Gᴇɴᴇʀᴀᴛɪɴɢ ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋs...", show_alert=False)
        
        quality_folders = await get_quality_folders(folder_id)
        
        all_files = []
        for qf in quality_folders:
            files = await get_all_folder_files(qf['folderId'])
            all_files.extend(files)
        
        if not all_files:
            await callback.message.reply_text("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ ɪɴ ᴛʜɪs ғᴏʟᴅᴇʀ!")
            return
        
        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"
        
        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"
        
        message_text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⬇️ Aʟʟ Dᴏᴡɴʟᴏᴀᴅ Lɪɴᴋs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📁 {html.escape(folder['name'])}
📊 Tᴏᴛᴀʟ Fɪʟᴇs: {len(all_files)}

━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for idx, file in enumerate(all_files, 1):
            file_id = file['fileId']
            file_name = file.get('fileName', 'Unnamed')
            quality = file.get('quality', 'Unknown')
            size = file.get('size', 0)
            size_mb = size / (1024 * 1024) if size else 0
            download_link = f"{base_url}/dl/{file_id}"
            
            message_text += f"{idx}. {file_name} [{quality}] ({size_mb:.1f}MB)\n"
            message_text += f"   `{download_link}`\n\n"
            
            if len(message_text) > 3500:
                await callback.message.reply_text(message_text, disable_web_page_preview=True)
                message_text = ""
        
        if message_text:
            await callback.message.reply_text(message_text, disable_web_page_preview=True)
        
        await callback.message.reply_text(
            f"✅ Gᴇɴᴇʀᴀᴛᴇᴅ {len(all_files)} ᴅᴏᴡɴʟᴏᴀᴅ ʟɪɴᴋs!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Bᴀᴄᴋ ᴛᴏ Fᴏʟᴅᴇʀ", callback_data=f"folder:{folder_id}:1")
            ]])
        )

    @bot.on_callback_query(filters.regex(r"^all_watch:[\w]+$"))
    async def all_watch_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]

        folder = await get_folder_by_id(folder_id)
        if not folder:
            await callback.answer("❌ Fᴏʟᴅᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return

        await callback.answer("🔄 Gᴇɴᴇʀᴀᴛɪɴɢ ᴡᴀᴛᴄʜ ʟɪɴᴋs...", show_alert=False)

        quality_folders = await get_quality_folders(folder_id)
        all_files = []

        if not quality_folders:
            files = await get_all_folder_files(folder_id)
            all_files.extend(files)
        else:
            for qf in quality_folders:
                files = await get_all_folder_files(qf['folderId'])
                all_files.extend(files)

        if not all_files:
            await callback.message.reply_text("❌ Nᴏ ғɪʟᴇs ғᴏᴜɴᴅ ɪɴ ᴛʜɪs ғᴏʟᴅᴇʀ!")
            return

        file_groups = {}
        for file in all_files:
            base_name = file.get("baseName")
            parent_master_group_id = file.get("parent_master_group_id")
            master_group_id = file.get("masterGroupId")
            master_id = parent_master_group_id or master_group_id

            if not base_name or not master_id:
                continue

            if base_name not in file_groups:
                file_groups[base_name] = {
                    "base_name": base_name,
                    "master_group_id": master_id,
                    "files": []
                }
            file_groups[base_name]["files"].append(file)

        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"

        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"

        max_message_length = 3500
        text_chunks = []
        current_chunk = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ▶️ Aʟʟ Wᴀᴛᴄʜ Lɪɴᴋs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📁 {html.escape(folder['name'])}

━━━━━━━━━━━━━━━━━━━━━━━━

"""
        group_count = 0

        for base_name, group in sorted(file_groups.items()):
            master_group_id = group.get("master_group_id")
            if not master_group_id:
                continue

            name_without_ext = os.path.splitext(base_name)[0]
            escaped_name = html.escape(f"E{name_without_ext}")

            watch_link = f"{base_url}/watch/master/{master_group_id}"
            line = f"• {escaped_name}\n   `{watch_link}`\n"

            if len(current_chunk) + len(line) > max_message_length:
                text_chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line
            group_count += 1

        if current_chunk:
            text_chunks.append(current_chunk)

        for chunk in text_chunks:
            await callback.message.reply_text(
                chunk,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Bᴀᴄᴋ ᴛᴏ Fᴏʟᴅᴇʀ", callback_data=f"folder:{folder_id}:1")
                ]]),
                disable_web_page_preview=True
            )

        await callback.answer(f"✅ Gᴇɴᴇʀᴀᴛᴇᴅ {group_count} ᴡᴀᴛᴄʜ ʟɪɴᴋs!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^file:[a-f0-9]{24}$"))
    async def file_view_callback(bot_instance, callback: CallbackQuery):
        file_id = callback.data.split(":")[1]
        
        file_data = await get_file_by_id(file_id)
        if not file_data:
            await callback.answer("❌ Fɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        raw_base = config.BASE_APP_URL or ""
        parsed = urlparse(raw_base)
        host = parsed.hostname or ""
        scheme = parsed.scheme or "https"
        
        if (not host) or ("localhost" in host) or host.startswith("127.") or host.startswith("0."):
            base_url = "https://demo.com"
        else:
            netloc = parsed.netloc or host
            base_url = f"{scheme}://{netloc}"
        
        info = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  🎬 Fɪʟᴇ Dᴇᴛᴀɪʟs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📄 {file_data.get('fileName', 'Unnamed')}

"""
        
        if file_data.get('baseName'):
            info += f"📦 Bᴀsᴇ Nᴀᴍᴇ: {file_data['baseName']}\n"
        
        if file_data.get('masterGroupId'):
            info += f"🔗 Mᴀsᴛᴇʀ ID: `{file_data['masterGroupId']}`\n"
        
        if file_data.get('size'):
            size_mb = file_data['size'] / (1024 * 1024)
            info += f"💾 Sɪᴢᴇ: {size_mb:.2f} MB\n"
        
        if file_data.get('mimeType'):
            info += f"📋 Tʏᴘᴇ: {file_data['mimeType']}\n"
        
        if file_data.get('quality'):
            info += f"🎥 Qᴜᴀʟɪᴛʏ: {file_data['quality']}\n"
        
        if file_data.get('language'):
            info += f"🗣 Lᴀɴɢᴜᴀɢᴇ: {file_data['language']}\n"
        
        if file_data.get('duration'):
            mins = file_data['duration'] // 60
            secs = file_data['duration'] % 60
            info += f"⏱ Dᴜʀᴀᴛɪᴏɴ: {mins}ᴍ {secs}s\n"
        
        if file_data.get('caption'):
            info += f"\n📝 {file_data['caption']}\n"
        
        info += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔗 Qᴜɪᴄᴋ Lɪɴᴋs:"
        info += f"\n▶️ Wᴀᴛᴄʜ: `{base_url}/watch/{file_id}`"
        info += f"\n📥 Sᴛʀᴇᴀᴍ: `{base_url}/{file_id}`"
        info += f"\n⬇️ Dᴏᴡɴʟᴏᴀᴅ: `{base_url}/dl/{file_id}`"
        
        if file_data.get('masterGroupId'):
            info += f"\n🔗 Eᴍʙᴇᴅ: `{base_url}/embed/{file_data['masterGroupId']}`"
        
        await callback.message.edit_text(
            info,
            reply_markup=file_actions_kb(file_id, file_data['folderId'])
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^rename_file:[a-f0-9]{24}$"))
    async def rename_file_callback(bot_instance, callback: CallbackQuery):
        file_id = callback.data.split(":")[1]
        user_id = callback.from_user.id
        
        user_rename_context[user_id] = {'type': 'file', 'id': file_id}
        
        await callback.message.edit_text(
            """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ✏️ Rᴇɴᴀᴍᴇ Fɪʟᴇ
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ғɪʟᴇ ɴᴀᴍᴇ.

Usᴇ /cancel ᴛᴏ ᴀʙᴏʀᴛ.
            """,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cᴀɴᴄᴇʟ", callback_data=f"file:{file_id}")
            ]])
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^delete_file:[a-f0-9]{24}:[\w]+$"))
    async def delete_file_confirm_callback(bot_instance, callback: CallbackQuery):
        parts = callback.data.split(":")
        file_id = parts[1]
        folder_id = parts[2]
        
        await callback.message.edit_text(
            """
⚠️ Dᴇʟᴇᴛᴇ Fɪʟᴇ?

Aʀᴇ ʏᴏᴜ sᴜʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴅᴇʟᴇᴛᴇ ᴛʜɪs ғɪʟᴇ?
Tʜɪs ᴀᴄᴛɪᴏɴ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜɴᴅᴏɴᴇ.
            """,
            reply_markup=confirm_delete_kb("file", file_id, folder_id)
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^confirm_delete_file:[a-f0-9]{24}:[\w]+$"))
    async def confirm_delete_file_callback(bot_instance, callback: CallbackQuery):
        parts = callback.data.split(":")
        file_id = parts[1]
        folder_id = parts[2]
        
        success = await delete_file(file_id)
        
        if success:
            await callback.answer("✅ Fɪʟᴇ ᴅᴇʟᴇᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!", show_alert=True)
            await show_folder_contents(callback.message, folder_id, 1, edit=True)
        else:
            await callback.answer("❌ Fᴀɪʟᴇᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ғɪʟᴇ!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^rename_folder:[\w]+$"))
    async def rename_folder_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]
        user_id = callback.from_user.id
        
        user_rename_context[user_id] = {'type': 'folder', 'id': folder_id}
        
        await callback.message.edit_text(
            """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ✏️ Rᴇɴᴀᴍᴇ Fᴏʟᴅᴇʀ
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Sᴇɴᴅ ᴛʜᴇ ɴᴇᴡ ғᴏʟᴅᴇʀ ɴᴀᴍᴇ.

Usᴇ /cancel ᴛᴏ ᴀʙᴏʀᴛ.
            """,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Cᴀɴᴄᴇʟ", callback_data=f"folder:{folder_id}:1")
            ]])
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^delete_folder:[\w]+$"))
    async def delete_folder_confirm_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]
        
        folder = await get_folder_by_id(folder_id)
        if not folder:
            await callback.answer("❌ Fᴏʟᴅᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"""
⚠️ Dᴇʟᴇᴛᴇ Fᴏʟᴅᴇʀ?

📁 {folder['name']}

Tʜɪs ᴡɪʟʟ ᴅᴇʟᴇᴛᴇ ᴛʜᴇ ғᴏʟᴅᴇʀ ᴀɴᴅ ALL ғɪʟᴇs/sᴜʙғᴏʟᴅᴇʀs ɪɴsɪᴅᴇ ɪᴛ.
Tʜɪs ᴀᴄᴛɪᴏɴ ᴄᴀɴɴᴏᴛ ʙᴇ ᴜɴᴅᴏɴᴇ!
            """,
            reply_markup=confirm_delete_kb("folder", folder_id)
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^confirm_delete_folder:[\w]+$"))
    async def confirm_delete_folder_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]
        
        success = await delete_folder(folder_id, callback.from_user.id)
        
        if success:
            await callback.answer("✅ Fᴏʟᴅᴇʀ ᴅᴇʟᴇᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!", show_alert=True)
            await show_folders_page(callback.message, 1, edit=True)
        else:
            await callback.answer("❌ Fᴀɪʟᴇᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ғᴏʟᴅᴇʀ!", show_alert=True)

    @bot.on_callback_query(filters.regex(r"^stats$"))
    async def stats_callback(bot_instance, callback: CallbackQuery):
        stats = await get_stats(callback.from_user.id)
        
        stats_text = f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📊 Yᴏᴜʀ Sᴛᴀᴛɪsᴛɪᴄs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📁 Fᴏʟᴅᴇʀs: {stats['folders']}
🎬 Tᴏᴛᴀʟ Fɪʟᴇs: {stats['files']}
💾 Sᴛᴏʀᴀɢᴇ Usᴇᴅ: {stats['total_size_mb']:.2f} MB
👁️ Tᴏᴛᴀʟ Vɪᴇᴡs: {stats.get('views', 0):,}
⬇️ Tᴏᴛᴀʟ Dᴏᴡɴʟᴏᴀᴅs: {stats.get('downloads', 0):,}

━━━━━━━━━━━━━━━━━━━━━━━━

💡 Kᴇᴇᴘ ᴜᴘʟᴏᴀᴅɪɴɢ ᴛᴏ ɢʀᴏᴡ ʏᴏᴜʀ ʟɪʙʀᴀʀʏ!
"""
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=main_menu_kb()
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^help$"))
    async def help_callback(bot_instance, callback: CallbackQuery):
        help_text = """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📖 Qᴜɪᴄᴋ Gᴜɪᴅᴇ
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Aᴜᴛᴏ Uᴘʟᴏᴀᴅ Fᴏʀᴍᴀᴛ:
`<Folder><File><Quality><Size>`

Exᴀᴍᴘʟᴇ:
`<Naruto><01.mp4><1080p><234MB>`

Mᴀɴᴜᴀʟ Uᴘʟᴏᴀᴅ:
1. Cʀᴇᴀᴛᴇ ғᴏʟᴅᴇʀ → Sᴇʟᴇᴄᴛ ǫᴜᴀʟɪᴛʏ → Uᴘʟᴏᴀᴅ

Fᴇᴀᴛᴜʀᴇs:
- Mᴜʟᴛɪ-ǫᴜᴀʟɪᴛʏ sᴜᴘᴘᴏʀᴛ (4K-360ᴘ)
- Nᴇsᴛᴇᴅ ғᴏʟᴅᴇʀ sᴛʀᴜᴄᴛᴜʀᴇ
- Aᴜᴛᴏ-ᴏʀɢᴀɴɪᴢᴇ ғɪʟᴇs
- Qᴜᴀʟɪᴛʏ sᴡɪᴛᴄʜɪɴɢ ɪɴ ᴘʟᴀʏᴇʀ
- Bᴜʟᴋ ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛɪᴏɴ

Usᴇ /help ғᴏʀ ᴅᴇᴛᴀɪʟᴇᴅ ɪɴsᴛʀᴜᴄᴛɪᴏɴs.
"""
        await callback.message.edit_text(help_text, reply_markup=main_menu_kb())
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^backup_menu$"))
    async def backup_menu_callback(bot_instance, callback: CallbackQuery):
        backup_text = """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  💾 Bᴀᴄᴋᴜᴘ & Rᴇsᴛᴏʀᴇ
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Exᴘᴏʀᴛ Dᴀᴛᴀʙᴀsᴇ:
Usᴇ `/vanish` ᴛᴏ ᴄʀᴇᴀᴛᴇ ᴀ ᴄᴏᴍᴘʟᴇᴛᴇ ʙᴀᴄᴋᴜᴘ.

Rᴇsᴛᴏʀᴇ Dᴀᴛᴀʙᴀsᴇ:
Usᴇ `/retrieve` ᴛᴏ ʀᴇsᴛᴏʀᴇ ғʀᴏᴍ ᴀ ʙᴀᴄᴋᴜᴘ ғɪʟᴇ.

Wʜᴀᴛ's Iɴᴄʟᴜᴅᴇᴅ:
- Aʟʟ ғᴏʟᴅᴇʀs ᴀɴᴅ sᴜʙғᴏʟᴅᴇʀs
- Aʟʟ ғɪʟᴇ ᴍᴇᴛᴀᴅᴀᴛᴀ
- Qᴜᴀʟɪᴛʏ ᴍᴀᴘᴘɪɴɢs
- Sᴛᴀᴛɪsᴛɪᴄs ᴅᴀᴛᴀ
- Mᴀsᴛᴇʀ ɢʀᴏᴜᴘ IDs

━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Iᴍᴘᴏʀᴛᴀɴᴛ: Kᴇᴇᴘ ʙᴀᴄᴋᴜᴘ ғɪʟᴇs sᴇᴄᴜʀᴇ!
"""
        await callback.message.edit_text(backup_text, reply_markup=main_menu_kb())
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^settings$"))
    async def settings_callback(bot_instance, callback: CallbackQuery):
        settings_text = """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ⚙️ Bᴏᴛ Sᴇᴛᴛɪɴɢs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Cᴜʀʀᴇɴᴛ Cᴏɴғɪɢᴜʀᴀᴛɪᴏɴ:
- Aᴜᴛᴏ-ɴᴜᴍʙᴇʀɪɴɢ: ✅ Eɴᴀʙʟᴇᴅ
- Qᴜᴀʟɪᴛʏ Dᴇᴛᴇᴄᴛɪᴏɴ: ✅ Eɴᴀʙʟᴇᴅ
- Lᴀɴɢᴜᴀɢᴇ Dᴇᴛᴇᴄᴛɪᴏɴ: ✅ Eɴᴀʙʟᴇᴅ
- Mᴀsᴛᴇʀ Gʀᴏᴜᴘɪɴɢ: ✅ Eɴᴀʙʟᴇᴅ

Aᴠᴀɪʟᴀʙʟᴇ Cᴏᴍᴍᴀɴᴅs:
- `/newfolder` - Cʀᴇᴀᴛᴇ ɴᴇᴡ ғᴏʟᴅᴇʀ
- `/myfolders` - Vɪᴇᴡ ᴀʟʟ ғᴏʟᴅᴇʀs
- `/stats` - Vɪᴇᴡ sᴛᴀᴛɪsᴛɪᴄs
- `/vanish` - Exᴘᴏʀᴛ ᴅᴀᴛᴀʙᴀsᴇ
- `/retrieve` - Rᴇsᴛᴏʀᴇ ᴅᴀᴛᴀʙᴀsᴇ
- `/help` - Dᴇᴛᴀɪʟᴇᴅ ɢᴜɪᴅᴇ
- `/api` - Aᴘɪ Dᴏᴄᴜᴍᴇɴᴛᴀᴛɪᴏɴ
━━━━━━━━━━━━━━━━━━━━━━━━

💡 Aʟʟ ғᴇᴀᴛᴜʀᴇs ᴀʀᴇ ᴏᴘᴛɪᴍɪᴢᴇᴅ!
"""
        await callback.message.edit_text(settings_text, reply_markup=main_menu_kb())
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^new_folder$"))
    async def new_folder_callback(bot_instance, callback: CallbackQuery):
        await callback.message.edit_text(
            """
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📁 Cʀᴇᴀᴛᴇ Nᴇᴡ Fᴏʟᴅᴇʀ
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

Usᴇ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ ʙᴇʟᴏᴡ ᴛᴏ ᴄʀᴇᴀᴛᴇ ᴀ ғᴏʟᴅᴇʀ:
`/newfolder <folder name>`

Exᴀᴍᴘʟᴇs:
- `/newfolder My Movies`
- `/newfolder TV Series 2024`
- `/newfolder Anime Collection`

━━━━━━━━━━━━━━━━━━━━━━━━

💡 Fᴏʟᴅᴇʀs ɢᴇᴛ ᴀᴜᴛᴏ-ɴᴜᴍʙᴇʀᴇᴅ IDs (1, 2, 3...)
            """,
            reply_markup=main_menu_kb()
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^add_files:[\w]+$"))
    async def add_files_callback(bot_instance, callback: CallbackQuery):
        folder_id = callback.data.split(":")[1]
        folder = await get_folder_by_id(folder_id)
        
        await callback.message.edit_text(
            f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📤 Aᴅᴅ Fɪʟᴇs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📁 {folder['name']}

Sᴇʟᴇᴄᴛ Qᴜᴀʟɪᴛʏ:
            """,
            reply_markup=quality_selection_kb(folder_id)
        )
        await callback.answer()

    @bot.on_callback_query(filters.regex(r"^select_quality:[\w]+:\w+$"))
    async def select_quality_callback(bot_instance, callback: CallbackQuery):
        from bot.handlers.media import set_user_folder_context, set_user_quality_context
        
        parts = callback.data.split(":")
        parent_folder_id = parts[1]
        quality = parts[2]
        
        quality_folder_id = await get_or_create_quality_folder(
            parent_folder_id, 
            quality, 
            callback.from_user.id
        )
        
        set_user_folder_context(callback.from_user.id, quality_folder_id)
        set_user_quality_context(callback.from_user.id, quality)
        
        folder = await get_folder_by_id(parent_folder_id)
        
        await callback.message.edit_text(
            f"""
┏━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📤 Aᴅᴅɪɴɢ Fɪʟᴇs
┗━━━━━━━━━━━━━━━━━━━━━━━━┛

📁 {folder['name']}
🎥 Qᴜᴀʟɪᴛʏ: {quality}

━━━━━━━━━━━━━━━━━━━━━━━━

Sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴠɪᴅᴇᴏ ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ ғɪʟᴇs.
Tʜᴇʏ'ʟʟ ʙᴇ sᴀᴠᴇᴅ ɪɴ ᴛʜᴇ {quality} ǫᴜᴀʟɪᴛʏ ғᴏʟᴅᴇʀ.

Sᴜᴘᴘᴏʀᴛᴇᴅ ғᴏʀᴍᴀᴛs:
MP4, MKV, AVI, MOV, WMV, FLV, WEBM, ᴀɴᴅ ᴍᴏʀᴇ!

━━━━━━━━━━━━━━━━━━━━━━━━

Wʜᴇɴ ᴅᴏɴᴇ, ᴜsᴇ /done
            """,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                "⬅️ Bᴀᴄᴋ ᴛᴏ Fᴏʟᴅᴇʀ", callback_data=f"folder:{parent_folder_id}:1"
            )]])
        )
        await callback.answer(f"✅ Sᴇʟᴇᴄᴛᴇᴅ {quality} ǫᴜᴀʟɪᴛʏ")

    @bot.on_callback_query(filters.regex(r"^noop$"))
    async def noop_callback(bot_instance, callback: CallbackQuery):
        await callback.answer()

    @bot.on_message(filters.text & filters.private, group=2)
    async def handle_rename_text(client, message):
        user_id = message.from_user.id
        
        if user_id not in user_rename_context:
            return
        
        context = user_rename_context[user_id]
        rename_type = context['type']
        item_id = context['id']
        new_name = message.text.strip()
        
        if not new_name or len(new_name) < 2:
            await message.reply_text("❌ Nᴀᴍᴇ ᴍᴜsᴛ ʙᴇ ᴀᴛ ʟᴇᴀsᴛ 2 ᴄʜᴀʀᴀᴄᴛᴇʀs ʟᴏɴɢ.")
            return
        
        if rename_type == 'file':
            file_data = await get_file_by_id(item_id)
            if not file_data:
                await message.reply_text("❌ Fɪʟᴇ ɴᴏᴛ ғᴏᴜɴᴅ!")
                del user_rename_context[user_id]
                return
            
            success = await update_file(item_id, {'fileName': new_name})
            
            if success:
                await message.reply_text(
                    f"✅ Fɪʟᴇ ʀᴇɴᴀᴍᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n📄 Nᴇᴡ ɴᴀᴍᴇ: {new_name}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📄 Vɪᴇᴡ Fɪʟᴇ", callback_data=f"file:{item_id}")
                    ]])
                )
            else:
                await message.reply_text("❌ Fᴀɪʟᴇᴅ ᴛᴏ ʀᴇɴᴀᴍᴇ ғɪʟᴇ!")
            
            del user_rename_context[user_id]
        
        elif rename_type == 'folder':
            from database.operations import update_folder
            
            folder = await get_folder_by_id(item_id)
            if not folder:
                await message.reply_text("❌ Fᴏʟᴅᴇʀ ɴᴏᴛ ғᴏᴜɴᴅ!")
                del user_rename_context[user_id]
                return
            
            success = await update_folder(item_id, {'name': new_name})
            
            if success:
                await message.reply_text(
                    f"✅ Fᴏʟᴅᴇʀ ʀᴇɴᴀᴍᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n📁 Nᴇᴡ ɴᴀᴍᴇ: {new_name}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📁 Vɪᴇᴡ Fᴏʟᴅᴇʀ", callback_data=f"folder:{item_id}:1")
                    ]])
                )
            else:
                await message.reply_text("❌ Fᴀɪʟᴇᴅ ᴛᴏ ʀᴇɴᴀᴍᴇ ғᴏʟᴅᴇʀ!")
            
            del user_rename_context[user_id]
        
        elif rename_type == 'master':
            db = get_database()
            matched_files = await db.files.find({
                'parent_master_group_id': item_id
            }).to_list(length=None)
            
            if not matched_files:
                await message.reply_text("❌ Fɪʟᴇ ɢʀᴏᴜᴘ ɴᴏᴛ ғᴏᴜɴᴅ!")
                del user_rename_context[user_id]
                return
            
            updated_count = 0
            for file in matched_files:
                file_id = str(file['_id'])
                old_ext = os.path.splitext(file.get('fileName', ''))[1]
                new_filename = new_name + old_ext
                
                success = await update_file(file_id, {
                    'fileName': new_filename,
                    'baseName': new_name
                })
                if success:
                    updated_count += 1
            
            if updated_count > 0:
                await message.reply_text(
                    f"✅ Rᴇɴᴀᴍᴇᴅ {updated_count} ғɪʟᴇ(s) sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n📦 Nᴇᴡ ɴᴀᴍᴇ: {new_name}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("📦 Vɪᴇᴡ Gʀᴏᴜᴘ", callback_data=f"master:{item_id}")
                    ]])
                )
            else:
                await message.reply_text("❌ Fᴀɪʟᴇᴅ ᴛᴏ ʀᴇɴᴀᴍᴇ ғɪʟᴇs!")
            
            del user_rename_context[user_id]
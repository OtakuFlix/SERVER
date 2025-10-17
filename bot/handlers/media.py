from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.client import get_bot
from database.operations import (
    add_file_to_folder, get_folder_by_id, parse_caption_format,
    get_or_create_folder_by_name, get_or_create_quality_folder
)
from config import config
import re
from utils.master_id import get_base_name_from_filename

user_folder_context = {}
user_quality_context = {}

def set_user_folder_context(user_id: int, folder_id):
    user_folder_context[user_id] = folder_id

def set_user_quality_context(user_id: int, quality: str):
    user_quality_context[user_id] = quality

def clear_user_folder_context(user_id: int):
    user_folder_context.pop(user_id, None)
    user_quality_context.pop(user_id, None)

def get_user_folder_context(user_id: int):
    return user_folder_context.get(user_id)

def get_user_quality_context(user_id: int) -> str:
    return user_quality_context.get(user_id)

def extract_quality(filename: str) -> str:
    quality_patterns = [
        r'\b(4320p|2160p|1440p|1080p|720p|480p|360p|240p)\b',
        r'\b(4K|2K|HD|FHD|UHD|8K)\b',
    ]
    for pattern in quality_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            q = match.group(1).upper()
            if q in ['4K', '2160P', '4320P']: return '4K'
            if q in ['1080P', 'FHD']: return '1080p'
            if q in ['720P', 'HD']: return '720p'
            if q in ['480P']: return '480p'
            if q in ['360P']: return '360p'
            return q
    return 'Unknown'

def extract_language(filename: str) -> str:
    language_patterns = {
        r'\b(Hindi|Tamil|Telugu|Malayalam|Kannada|Bengali|Marathi|Gujarati|Punjabi)\b': lambda m: m.group(1),
        r'\b(English|Eng)\b': lambda m: 'English',
        r'\b(Dual Audio|Multi Audio)\b': lambda m: 'Multi Audio',
    }
    for pattern, extractor in language_patterns.items():
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            return extractor(match)
    return None

def extract_base_name(file_name: str) -> str:
    return get_base_name_from_filename(file_name)

async def handle_media(client, message: Message):
    user_id = message.from_user.id
    folder_id = get_user_folder_context(user_id)
    selected_quality = get_user_quality_context(user_id)
    
    caption = message.caption or ""
    parsed_data = parse_caption_format(caption)
    
    auto_mode = False
    if parsed_data.get('parsed'):
        auto_mode = True
        target_folder_name = parsed_data['folder_name']
        base_file_name = parsed_data['file_name']
        quality = parsed_data['quality']
        
        parent_folder_id = await get_or_create_folder_by_name(target_folder_name, user_id)
        quality_folder_id = await get_or_create_quality_folder(parent_folder_id, quality, user_id)
        folder_id = quality_folder_id
    
    elif not folder_id:
        await message.reply_text(
            "📤 **To save this file:**\n\n"
            "**Option 1: Use Caption Format**\n"
            "`<Folder_Name><File_Name><Quality><Size>`\n"
            "Example: `<Naruto><01.mp4><1080p><234MB>`\n\n"
            "**Option 2: Manual Upload**\n"
            "1. Create a folder: /newfolder <name>\n"
            "2. Open folder from /myfolders\n"
            "3. Click 'Add Files'\n"
            "4. Select quality\n"
            "5. Send your media files"
        )
        return
    
    try:
        folder = await get_folder_by_id(folder_id)
        if not folder:
            await message.reply_text("❌ Folder not found!")
            return
        
        if message.video:
            media = message.video
            file_id = media.file_id
            file_unique_id = media.file_unique_id
            file_name = media.file_name or "video.mp4"
            mime_type = media.mime_type
            file_size = media.file_size
            duration = media.duration
            width = media.width
            height = media.height
            thumbnail = media.thumbs[0].file_id if media.thumbs else None
            
        elif message.document:
            media = message.document
            file_id = media.file_id
            file_unique_id = media.file_unique_id
            file_name = media.file_name or "document"
            mime_type = media.mime_type
            file_size = media.file_size
            thumbnail = media.thumbs[0].file_id if media.thumbs else None
            duration = None
            width = None
            height = None
        else:
            await message.reply_text("❌ Unsupported file type.")
            return
        
        if auto_mode:
            quality = parsed_data['quality']
            base_name = parsed_data['file_name']
        else:
            quality = selected_quality or extract_quality(file_name)
            base_name = extract_base_name(file_name)
        
        language = extract_language(file_name)
        
        file_doc = {
            'telegramFileId': file_id,
            'telegramFileUniqueId': file_unique_id,
            'fileName': file_name,
            'baseName': base_name,
            'mimeType': mime_type,
            'size': file_size,
            'folderId': folder_id,
            'caption': message.caption,
            'quality': quality,
            'language': language,
            'duration': duration,
            'width': width,
            'height': height,
            'thumbnail': thumbnail,
            'parsedFromCaption': auto_mode
        }
        
        insert_result = await add_file_to_folder(file_doc, user_id)
        if not insert_result:
            await message.reply_text("⚠️ Failed to save file.")
            return
        
        if not insert_result.get('inserted', False):
            await message.reply_text("⚠️ This file already exists in this folder.")
            return
        
        mongo_id = insert_result.get('documentId')
        master_group_id = insert_result.get('masterGroupId')
        parent_master_group_id = insert_result.get('parent_master_group_id')
        
        if not mongo_id:
            await message.reply_text("⚠️ Failed to save file.")
            return
        
        # --- Safe URL generation ---
        base_url = config.BASE_APP_URL

        # If base_url is localhost or 127.x.x.x, replace with demo domain
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "https://demo.com"

        embed_url = f"{base_url}/embed/master/{parent_master_group_id or master_group_id}"
        watch_url = f"{base_url}/watch/{mongo_id}"
        download_url = f"{base_url}/dl/{mongo_id}"


        # Build clean caption for channel
        channel_caption = (
            f"🎬 **New File Uploaded!**\n\n"
            f"📁 **Folder:** {folder['name']}\n"
            f"🔗 **Embed Link:** {base_url}/embed/master/{parent_master_group_id or master_group_id}\n"
            f"📄 **File Name:** {file_name}\n"
        )
        if quality:
            channel_caption += f"🎥 **Quality:** {quality}\n"
        if language:
            channel_caption += f"🗣 **Language:** {language}\n"
        if file_size:
            size_mb = file_size / (1024 * 1024)
            channel_caption += f"💾 **Size:** {size_mb:.2f} MB\n"
        if duration:
            mins = duration // 60
            secs = duration % 60
            channel_caption += f"⏱ **Duration:** {mins}m {secs}s\n"

        channel_caption += f"\n👤 **Uploaded by:** {message.from_user.first_name} ({user_id})"

        # Inline buttons layout
        buttons = [
            [
                InlineKeyboardButton("📺 Embed", url=embed_url),
                InlineKeyboardButton("▶️ Watch", url=watch_url)
            ],
            [
                InlineKeyboardButton("⬇️ Download", url=download_url)
            ]
        ]

        # Forward to channel
        try:
            bot = get_bot()
            if config.CHANNEL_ID:
                await bot.copy_message(
                    chat_id=config.CHANNEL_ID,
                    from_chat_id=message.chat.id,
                    message_id=message.id,
                    caption=channel_caption,
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                print(f"[MEDIA] File forwarded to channel: {file_name}")
        except Exception as e:
            print(f"[MEDIA] Error forwarding to channel: {e}")

        # Send confirmation to user
        response = (
            f"✅ **File Added Successfully!**\n\n"
            f"📦 **Name:** {base_name}\n"
            f"🔗 **Embed Link:** {base_url}/embed/master/{parent_master_group_id or master_group_id}\n"
        )
        if quality:
            response += f"🎥 **Quality:** {quality}\n"
        if language:
            response += f"🗣 **Language:** {language}\n"
        if file_size:
            response += f"💾 **Size:** {size_mb:.2f} MB\n"
        if duration:
            mins = duration // 60
            secs = duration % 60
            response += f"⏱ **Duration:** {mins}m {secs}s\n"

        response += "\n**━━━━━━━━━━━━━━━━━━━━**\n"

        await message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        print(f"[MEDIA] Error handling media: {e}")
        await message.reply_text("❌ Failed to save file. Please try again.")

async def done_adding_files(client, message: Message):
    user_id = message.from_user.id
    folder_id = user_folder_context.pop(user_id, None)
    user_quality_context.pop(user_id, None)
    
    if folder_id:
        folder = await get_folder_by_id(folder_id)
        await message.reply_text(
            f"✅ **Upload Complete!**\n\n"
            f"📁 Finished adding files to **{folder['name']}**\n\n"
            f"**━━━━━━━━━━━━━━━━━━━━**\n\n"
            f"📊 Use /myfolders to view your folders\n"
            f"🔗 Use /stats to see your statistics"
        )
    else:
        await message.reply_text("⚠️ You weren't adding files to any folder.")

def register_media_handlers(bot):
    bot.on_message(filters.private & (filters.video | filters.document), group=0)(handle_media)
    bot.on_message(filters.private & filters.command("done"))(done_adding_files)

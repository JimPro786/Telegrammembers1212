import os
import asyncio
import sqlite3
from datetime import datetime
from telethon import TelegramClient, events
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import InputPeerUser
from telethon.sessions import StringSession

# ==================== CONFIGURATION ====================
class Config:
    OPERATOR = "𝗝𝗜𝗠𝗣𝗥𝗢"  # Big bold letters
    VERSION = "6.0"
    DB_FILE = "jimpro.db"
    SESSION_FILE = "jimpro.session"
    API_ID = 2040  # Official Telegram API
    API_HASH = "b18441a1ff607e10a989891a5462e627"  # Official Telegram API
    BOT_TOKEN = os.getenv("7871589959:AAGXJN7D88gdF9yBMQoKTBVEDFDH0gSBcQY", "")  # From environment variable
    ADMIN_ID = int(os.getenv("5287661425", 0))  # From environment variable

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(Config.DB_FILE)
        self._create_tables()
    
    def _create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY,
                    source_id INTEGER,
                    source_name TEXT,
                    target_id INTEGER,
                    target_name TEXT,
                    total_users INTEGER,
                    success INTEGER,
                    skipped INTEGER,
                    failed INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_commands (
                    id INTEGER PRIMARY KEY,
                    command TEXT,
                    source TEXT,
                    target TEXT,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

# ==================== MAIN MIGRATOR CLASS ====================
class JimProUltimateMigrator:
    def __init__(self):
        self.client = None
        self.bot = None
        self.db = Database()
        self.current_operation = None
        self.remote_control_enabled = bool(Config.BOT_TOKEN and Config.ADMIN_ID)

    async def start(self):
        print(self._get_banner())
        
        # Initialize Telegram client
        await self._initialize_client()
        
        # Start bot if token available
        if self.remote_control_enabled:
            await self._start_bot()
        
        # Main menu loop
        await self._main_loop()

    def _get_banner(self):
        return f"""
╔════════════════════════════════════════╗
║                                        ║
║            𝗝𝗜𝗠𝗣𝗥𝗢 𝗩{Config.VERSION}             ║
║                                        ║
║  ULTIMATE TELEGRAM MIGRATION SYSTEM    ║
║                                        ║
║  • One-Time Login                     ║
║  • Unlimited Runtime                  ║
║  • Full Remote Control                ║
║  • Instant Operations                 ║
║                                        ║
╚════════════════════════════════════════╝
{'='*60}
🔹 Bot Control: {'ENABLED' if self.remote_control_enabled else 'DISABLED'}
{'='*60}"""

    async def _initialize_client(self):
        """Initialize Telegram client with persistent session"""
        self.client = TelegramClient(Config.SESSION_FILE, Config.API_ID, Config.API_HASH)
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            await self._do_login()
        
        me = await self.client.get_me()
        print(f"\n✅ Logged in as: {me.first_name} (@{me.username})")

    async def _do_login(self):
        """Handle user login process"""
        phone = input("\n📱 Enter your phone number (with country code): ").strip()
        
        try:
            await self.client.send_code_request(phone)
            code = input("✉️ Enter verification code: ").strip()
            
            try:
                await self.client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                password = input("🔒 Enter your 2FA password: ")
                await self.client.sign_in(password=password)
        
        except Exception as e:
            print(f"❌ Login failed: {e}")
            exit()

    async def _start_bot(self):
        """Initialize and start the control bot"""
        try:
            self.bot = TelegramClient(StringSession(), Config.API_ID, Config.API_HASH)
            
            # ========== BOT COMMAND HANDLERS ==========
            @self.bot.on(events.NewMessage(pattern='/start'))
            async def start_handler(event):
                if event.sender_id == Config.ADMIN_ID:
                    buttons = [
                        [Button.inline("Group ➔ Channel", b"migrate_g2c")],
                        [Button.inline("Channel ➔ Group", b"migrate_c2g")],
                        [Button.inline("Multi-Source", b"migrate_multi")],
                        [Button.inline("Get Status", b"get_status")]
                    ]
                    await event.respond(f"**{Config.OPERATOR} Migration Control**", buttons=buttons)
            
            @self.bot.on(events.CallbackQuery(data=b"migrate_g2c"))
            async def migrate_g2c_handler(event):
                await event.respond("Please send source group and target channel in format:\n`/migrate @sourcegroup @targetchannel`")
            
            @self.bot.on(events.CallbackQuery(data=b"migrate_c2g"))
            async def migrate_c2g_handler(event):
                await event.respond("Please send source channel and target group in format:\n`/migrate @sourcechannel @targetgroup`")
            
            @self.bot.on(events.NewMessage(pattern='/migrate'))
            async def migrate_handler(event):
                if event.sender_id == Config.ADMIN_ID:
                    try:
                        parts = event.text.split()
                        if len(parts) == 3:
                            source = parts[1]
                            target = parts[2]
                            await self._handle_remote_migration(event, source, target)
                        else:
                            await event.respond("Invalid format. Use:\n`/migrate @source @target`")
                    except Exception as e:
                        await event.respond(f"❌ Error: {str(e)}")
            
            @self.bot.on(events.NewMessage(pattern='/status'))
            async def status_handler(event):
                if event.sender_id == Config.ADMIN_ID:
                    await self._send_status_report(event)
            
            # Start the bot
            await self.bot.start(bot_token=Config.BOT_TOKEN)
            print("\n🤖 Bot started successfully for remote control!")
            
            # Run bot in background
            asyncio.create_task(self.bot.run_until_disconnected())
            
        except Exception as e:
            print(f"\n⚠️ Bot failed to start: {e}")

    async def _handle_remote_migration(self, event, source, target):
        """Handle migration command from bot"""
        try:
            source_entity = await self.client.get_entity(source)
            target_entity = await self.client.get_entity(target)
            
            await event.respond(f"🚀 Starting migration:\nFrom: {source_entity.title}\nTo: {target_entity.title}")
            
            # Start migration
            await self._migrate_users(source_entity, target_entity, "remote_bot_migration")
            
            # Send completion report
            with sqlite3.connect(Config.DB_FILE) as conn:
                cursor = conn.execute("""
                    SELECT success, skipped, failed 
                    FROM migrations 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                if result:
                    await event.respond(
                        f"✅ Migration Complete!\n"
                        f"Success: {result[0]}\n"
                        f"Skipped: {result[1]}\n"
                        f"Failed: {result[2]}"
                    )
            
        except Exception as e:
            await event.respond(f"❌ Migration failed: {str(e)}")

    async def _main_loop(self):
        """Main operational loop"""
        while True:
            try:
                if not self.current_operation:
                    await self._show_main_menu()
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ Main loop error: {e}")
                await asyncio.sleep(5)

    async def _show_main_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print(f"🏠 {Config.OPERATOR} MAIN MENU")
        print("="*60)
        print("1. Group ➔ Channel Migration")
        print("2. Channel ➔ Group Migration")
        print("3. View Migration History")
        print("4. Remote Control Status")
        print("0. Exit")
        print("="*60)
        
        choice = input("\n🛠 Select an option (0-4): ").strip()
        
        if choice == "1":
            await self._start_migration("group_to_channel")
        elif choice == "2":
            await self._start_migration("channel_to_group")
        elif choice == "3":
            self._show_history()
        elif choice == "4":
            self._show_remote_status()
        elif choice == "0":
            await self.cleanup()
            exit()
        else:
            print("❌ Invalid choice")

    async def _start_migration(self, migration_type):
        """Start migration process"""
        try:
            source = await self._get_entity("Enter SOURCE username (e.g. @group): ")
            if not source:
                return
                
            target = await self._get_entity("Enter TARGET username (e.g. @channel): ")
            if not target:
                return
                
            print(f"\n🚀 Starting migration from {source.title} to {target.title}")
            await self._migrate_users(source, target, migration_type)
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")

    async def _migrate_users(self, source, target, migration_type):
        """Core migration logic"""
        try:
            print("\n🔍 Fetching users...")
            users = await self.client.get_participants(source, aggressive=True)
            valid_users = [u for u in users if not u.bot and not u.is_self]
            
            stats = {
                'total': len(valid_users),
                'success': 0,
                'skipped': 0,
                'failed': 0
            }
            
            print(f"\n🔹 Migrating {stats['total']} users")
            
            # Process in optimized batches
            batch_size = 15
            for i in range(0, len(valid_users), batch_size):
                batch = valid_users[i:i + batch_size]
                await self._process_batch(batch, target, stats)
                
                # Dynamic rate limiting
                wait = 2 if (i // batch_size) % 5 != 0 else 5
                await asyncio.sleep(wait)
            
            # Save results
            self.db.conn.execute("""
                INSERT INTO migrations (
                    source_id, source_name, target_id, target_name,
                    total_users, success, skipped, failed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source.id, source.title, target.id, target.title,
                stats['total'], stats['success'], stats['skipped'], stats['failed']
            ))
            self.db.conn.commit()
            
            # Show report
            print("\n" + "="*60)
            print(f"📊 MIGRATION COMPLETE")
            print("="*60)
            print(f"🔹 Total: {stats['total']}")
            print(f"✅ Success: {stats['success']}")
            print(f"⚠️ Skipped: {stats['skipped']}")
            print(f"❌ Failed: {stats['failed']}")
            print("\n🌟 Powered by " + Config.OPERATOR)
            
        except Exception as e:
            print(f"\n❌ Migration error: {e}")

    async def _process_batch(self, batch, target, stats):
        """Process a batch of users"""
        try:
            users_to_add = [
                InputPeerUser(u.id, u.access_hash) 
                for u in batch 
                if hasattr(u, 'access_hash')
            ]
            
            if users_to_add:
                await self.client(InviteToChannelRequest(target, users_to_add))
                stats['success'] += len(users_to_add)
            
            stats['skipped'] += len(batch) - len(users_to_add)
            
        except errors.UserPrivacyRestrictedError:
            stats['skipped'] += len(batch)
        except errors.FloodWaitError as e:
            print(f"⏳ Flood wait: {e.seconds} seconds")
            stats['failed'] += len(batch)
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"⚠️ Batch error: {e}")
            stats['failed'] += len(batch)

    def _show_history(self):
        """Show migration history"""
        print("\n" + "="*60)
        print(f"📜 {Config.OPERATOR} MIGRATION HISTORY")
        print("="*60)
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            cursor = conn.execute("""
                SELECT source_name, target_name, total_users, success, timestamp 
                FROM migrations 
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                print(f"\n⏰ {row[4]}")
                print(f"FROM: {row[0]}")
                print(f"TO: {row[1]}")
                print(f"USERS: {row[2]} | ✅ {row[3]}")
                print("─"*40)

    def _show_remote_status(self):
        """Show remote control status"""
        print("\n" + "="*60)
        print(f"📡 REMOTE CONTROL STATUS")
        print("="*60)
        print(f"🔹 Bot Control: {'ENABLED ✅' if self.remote_control_enabled else 'DISABLED ❌'}")
        if self.remote_control_enabled:
            print(f"🔸 Admin ID: {Config.ADMIN_ID}")
            print("\nAvailable Bot Commands:")
            print("/start - Show control panel")
            print("/migrate @source @target - Start migration")
            print("/status - Get current status")
        else:
            print("\nTo enable remote control:")
            print("1. Set TELEGRAM_BOT_TOKEN environment variable")
            print("2. Set TELEGRAM_ADMIN_ID environment variable")
            print("3. Restart the application")
        print("="*60)

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.disconnect()
        if self.bot:
            await self.bot.disconnect()

# ==================== MAIN EXECUTION ====================
if __name__ == '__main__':
    migrator = JimProUltimateMigrator()
    
    async def run():
        await migrator.start()
    
    asyncio.run(run())

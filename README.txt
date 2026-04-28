════════════════════════════════════════════════════════════════════
  ALL-IN-ONE DISCORD BOT — README
════════════════════════════════════════════════════════════════════

A feature-rich Discord bot with Music, Moderation, AI Chat,
Fun Commands, and a Ticket System — all in a single Python file.


────────────────────────────────────────────────────────────────────
  PROJECT STRUCTURE
────────────────────────────────────────────────────────────────────

  my_bot/
  ├── bot_combined.py       ← Main bot file (run this)
  ├── ffmpeg.exe            ← Required for music (Windows only)
  ├── .env                  ← Your secret tokens (never share this)
  ├── requirements.txt      ← Python dependencies
  ├── README.txt            ← This file
  └── data/                 ← Auto-created at runtime
      ├── warnings.json     ← Stores moderation warnings
      └── tickets.json      ← Stores ticket data


────────────────────────────────────────────────────────────────────
  REQUIREMENTS
────────────────────────────────────────────────────────────────────

  - Python 3.10 or higher
  - pip (Python package manager)
  - ffmpeg (see FFMPEG section below)
  - A Discord Bot Token
  - An Anthropic API Key (for AI chat features)


────────────────────────────────────────────────────────────────────
  QUICK START
────────────────────────────────────────────────────────────────────

  1. Install dependencies:
       pip install -r requirements.txt

  2. Fill in your tokens in the .env file:
       DISCORD_TOKEN=your_discord_bot_token_here
       ANTHROPIC_API_KEY=your_anthropic_api_key_here

  3. Set up ffmpeg (see FFMPEG section below)

  4. Run the bot:
       python bot_combined.py


────────────────────────────────────────────────────────────────────
  GETTING YOUR TOKENS
────────────────────────────────────────────────────────────────────

  DISCORD BOT TOKEN
  ─────────────────
  1. Go to https://discord.com/developers/applications
  2. Click "New Application" and give it a name
  3. Go to the "Bot" tab → click "Add Bot"
  4. Under "Token", click "Reset Token" and copy it
  5. Under "Privileged Gateway Intents", enable:
       - Presence Intent
       - Server Members Intent
       - Message Content Intent
  6. Go to "OAuth2" → "URL Generator"
     Scopes: bot, applications.commands
     Bot Permissions: Administrator (or select individually)
  7. Open the generated URL to invite the bot to your server

  ANTHROPIC API KEY
  ─────────────────
  1. Go to https://console.anthropic.com/
  2. Sign in or create an account
  3. Navigate to "API Keys" → "Create Key"
  4. Copy the key and paste it in your .env file


────────────────────────────────────────────────────────────────────
  FFMPEG SETUP
────────────────────────────────────────────────────────────────────

  ffmpeg is required for music playback.

  WINDOWS
  ───────
  1. Go to: https://www.gyan.dev/ffmpeg/builds/
  2. Download: ffmpeg-release-essentials.zip
  3. Extract the zip
  4. Copy bin\ffmpeg.exe into the same folder as bot_combined.py

  LINUX
  ─────
  sudo apt install ffmpeg          (Ubuntu/Debian)
  sudo dnf install ffmpeg          (Fedora)

  MACOS
  ─────
  brew install ffmpeg

  The bot automatically detects ffmpeg.exe if it's in the same
  folder, otherwise falls back to the system-installed ffmpeg.


────────────────────────────────────────────────────────────────────
  COMMANDS
────────────────────────────────────────────────────────────────────

  All commands use the ! prefix by default.

  🤖 AI CHAT
  ──────────
  !ask <question>       Ask the AI a question (keeps conversation history)
  !resetchat            Clear your AI conversation history
  @BotName <message>    Mention the bot to chat with it directly

  🎵 MUSIC
  ────────
  !play <query>         Play a song by name or YouTube URL
  !pause                Pause playback
  !resume               Resume playback
  !skip                 Skip to the next song
  !stop                 Stop playback and clear the queue
  !queue                View the current queue
  !nowplaying           Show the currently playing song
  !volume <0-100>       Set the volume
  !loop                 Toggle loop mode
  !join                 Join your voice channel
  !leave                Leave the voice channel

  🔨 MODERATION  (requires appropriate permissions)
  ──────────────
  !ban <user> [reason]          Ban a user
  !unban <user#tag or ID>       Unban a user
  !kick <user> [reason]         Kick a user
  !mute <user> [minutes]        Timeout a user (default: 10 min)
  !unmute <user>                Remove timeout from a user
  !warn <user> [reason]         Issue a warning to a user
  !warnings <user>              View a user's warnings
  !clearwarns <user>            Clear all warnings for a user
  !purge <amount>               Delete messages (max 500)
  !slowmode <seconds>           Set channel slowmode (0 = off)
  !lock                         Lock the current channel
  !unlock                       Unlock the current channel
  !role <user> <role>           Add or remove a role from a user
  !nick <user> [nickname]       Change or reset a user's nickname
  !serverinfo                   Display server information
  !userinfo [user]              Display user information

  🎫 TICKETS
  ──────────
  !ticket setup [#channel]      Send the ticket panel to a channel
  !ticket close                 Close the current ticket
  !ticket add <user>            Add a user to the current ticket
  !ticket remove <user>         Remove a user from the current ticket
  !ticket rename <name>         Rename the ticket channel
  !ticket list                  List all open tickets

  🎉 FUN
  ──────
  !8ball <question>     Ask the magic 8-ball
  !coinflip             Flip a coin
  !dice [sides]         Roll a dice (default: d6)
  !rps <choice>         Rock, paper, scissors
  !joke                 Get a random joke
  !fact                 Get a random fun fact
  !poll "Q" "A" "B"     Create a poll with reactions
  !avatar [user]        Show a user's avatar
  !choose <a> <b> ...   Choose randomly between options
  !reverse <text>       Reverse text
  !ping                 Check the bot's latency


────────────────────────────────────────────────────────────────────
  CONFIGURATION
────────────────────────────────────────────────────────────────────

  The following can be changed at the top of bot_combined.py:

  PREFIX = "!"          Change the command prefix
  MAX_HISTORY = 20      Number of AI messages retained per user


────────────────────────────────────────────────────────────────────
  TROUBLESHOOTING
────────────────────────────────────────────────────────────────────

  Bot won't start
    → Check that your .env file has valid tokens
    → Make sure Python 3.10+ is installed: python --version

  Music not working
    → Ensure ffmpeg is set up correctly (see FFMPEG section)
    → Make sure PyNaCl is installed: pip install PyNaCl

  AI commands not working
    → Verify your ANTHROPIC_API_KEY is correct in .env
    → Check you have API credits at console.anthropic.com

  Missing permissions errors
    → Re-invite the bot with Administrator permission, or
      manually grant the required permissions in server settings

  Commands not appearing as slash commands
    → Wait up to 1 hour for Discord to sync slash commands
    → Or kick and re-invite the bot to force a sync


════════════════════════════════════════════════════════════════════
"""
SKYLINE Auth - Discord Management Bot
======================================
Prefix commands for managing users via Discord.
Run standalone: python discord_bot.py

Commands (owner-only):
  !createuser <username> <password> <days>  - Create a user
  !createuser <days>                        - Create auto-keyed user for <days>
  !deleteuser <username>                    - Delete a user by key/username
  !resetuser  <username>                    - Reset HWID for a user
  !listusers                                - List recent users (up to 25)
  !help                                     - Show command list
"""

import os
import discord
import requests
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────
BOT_TOKEN       = os.environ['DISCORD_BOT_TOKEN']
OWNER_ID        = int(os.environ['DISCORD_OWNER_ID'])   # Your Discord user ID
SERVER_URL      = os.environ.get('SERVER_URL', 'http://localhost:5000')  # Flask backend URL
MGMT_SECRET     = os.environ['MGMT_SECRET']
DISCORD_APP_ID  = os.environ.get('DISCORD_APP_ID', '')
DISCORD_PACKAGE_ID = os.environ.get('DISCORD_PACKAGE_ID', '')

MGMT_BASE = f"{SERVER_URL.rstrip('/')}/mgmt"
HEADERS   = {'Authorization': f'Bearer {MGMT_SECRET}', 'Content-Type': 'application/json'}

# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


# ── Guard: owner-only ─────────────────────────────────────────────────────────
def is_owner():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send('❌ You are not authorized to use this command.')
            return False
        return True
    return commands.check(predicate)


# ── Helpers ───────────────────────────────────────────────────────────────────
def mgmt_post(path, json_data):
    try:
        r = requests.post(f"{MGMT_BASE}{path}", json=json_data, headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return {'success': False, 'message': str(e)}


def mgmt_delete(path, json_data):
    try:
        r = requests.delete(f"{MGMT_BASE}{path}", json=json_data, headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return {'success': False, 'message': str(e)}


def mgmt_get(path, params=None):
    try:
        r = requests.get(f"{MGMT_BASE}{path}", params=params, headers=HEADERS, timeout=10)
        return r.json()
    except Exception as e:
        return {'success': False, 'message': str(e)}


def build_embed(title, description, color=discord.Color.blurple()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text='SKYLINE Auth Management')
    return embed


# ── Events ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f'✅ Bot online as {bot.user} (ID: {bot.user.id})')
    print(f'   Server URL : {SERVER_URL}')
    print(f'   Owner ID   : {OWNER_ID}')


# ── Commands ──────────────────────────────────────────────────────────────────

@bot.command(name='createuser')
@is_owner()
async def createuser(ctx, *args):
    """
    !createuser <username> <password> <days>
    !createuser <days>   (auto-generates a SKYLINE-XXXX key)
    """
    if len(args) == 0:
        await ctx.send(embed=build_embed(
            '❌ Usage Error',
            '`!createuser <username> <password> <days>`\n'
            'or: `!createuser <days>` for an auto-generated key',
            discord.Color.red()
        ))
        return

    if len(args) == 1:
        # Auto-generate key
        days = int(args[0])
        username = None
        password = None
    elif len(args) >= 3:
        username = args[0]
        password = args[1]
        days = int(args[2])
    else:
        await ctx.send(embed=build_embed(
            '❌ Usage Error',
            '`!createuser <username> <password> <days>`',
            discord.Color.red()
        ))
        return

    async with ctx.typing():
        payload = {
            'app_id': DISCORD_APP_ID,
            'package_id': DISCORD_PACKAGE_ID,
            'days': days,
        }
        if username:
            payload['username'] = username
        if password:
            payload['password'] = password

        result = mgmt_post('/users/create', payload)

    if result.get('success'):
        users = result.get('users', [])
        lines = '\n'.join(
            f"**Key:** `{u['key']}`  |  **Pass:** `{u['password']}`"
            for u in users
        )
        await ctx.send(embed=build_embed(
            '✅ User Created',
            f"{lines}\n\n⏱ Expires in **{days} day(s)**",
            discord.Color.green()
        ))
    else:
        await ctx.send(embed=build_embed(
            '❌ Create Failed',
            result.get('message', 'Unknown error'),
            discord.Color.red()
        ))


@bot.command(name='deleteuser')
@is_owner()
async def deleteuser(ctx, key: str = None):
    """!deleteuser <username/key>"""
    if not key:
        await ctx.send(embed=build_embed('❌ Usage', '`!deleteuser <username>`', discord.Color.red()))
        return

    async with ctx.typing():
        result = mgmt_delete('/users/delete', {'key': key})

    if result.get('success'):
        await ctx.send(embed=build_embed(
            '✅ User Deleted',
            result.get('message', f'User `{key}` deleted.'),
            discord.Color.green()
        ))
    else:
        await ctx.send(embed=build_embed(
            '❌ Delete Failed',
            result.get('message', 'Unknown error'),
            discord.Color.red()
        ))


@bot.command(name='resetuser')
@is_owner()
async def resetuser(ctx, key: str = None):
    """!resetuser <username/key> — resets their HWID lock"""
    if not key:
        await ctx.send(embed=build_embed('❌ Usage', '`!resetuser <username>`', discord.Color.red()))
        return

    async with ctx.typing():
        result = mgmt_post('/users/reset-hwid', {'key': key})

    if result.get('success'):
        await ctx.send(embed=build_embed(
            '✅ HWID Reset',
            result.get('message', f'HWID cleared for `{key}`. They can log in on a new device.'),
            discord.Color.green()
        ))
    else:
        await ctx.send(embed=build_embed(
            '❌ Reset Failed',
            result.get('message', 'Unknown error'),
            discord.Color.red()
        ))


@bot.command(name='listusers')
@is_owner()
async def listusers(ctx):
    """!listusers — shows up to 25 recent users"""
    async with ctx.typing():
        result = mgmt_get('/users/list', params={'app_id': DISCORD_APP_ID})

    if result.get('success'):
        users = result.get('users', [])
        total = result.get('total', 0)
        if not users:
            await ctx.send(embed=build_embed('📋 Users', 'No users found.', discord.Color.blurple()))
            return

        lines = []
        for u in users:
            status = '🟢' if u.get('is_active') else '🔴'
            hwid = '🔒' if u.get('hwid_locked') else '🔓'
            lines.append(f"{status}{hwid} `{u['key']}` — expires `{u['expiry']}`")

        await ctx.send(embed=build_embed(
            f'📋 Users ({len(users)}/{total})',
            '\n'.join(lines),
            discord.Color.blurple()
        ))
    else:
        await ctx.send(embed=build_embed(
            '❌ List Failed',
            result.get('message', 'Unknown error'),
            discord.Color.red()
        ))


@bot.command(name='help')
async def help_cmd(ctx):
    """Show available commands"""
    if ctx.author.id != OWNER_ID:
        return
    desc = (
        '**User Management Commands** (owner only)\n\n'
        '`!createuser <username> <password> <days>` — Create named user\n'
        '`!createuser <days>` — Create auto-keyed user\n'
        '`!deleteuser <username>` — Delete a user\n'
        '`!resetuser <username>` — Reset HWID (allow new device)\n'
        '`!listusers` — List recent users\n'
    )
    await ctx.send(embed=build_embed('SKYLINE Auth Bot', desc, discord.Color.blurple()))


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    bot.run(BOT_TOKEN)

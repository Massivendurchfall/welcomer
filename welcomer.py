import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import asyncio
import json
import os


class WelcomeBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

        self.config_file = "guild_configs.json"
        self.guild_configs = self.load_configs()

    def load_configs(self):
        """Lädt die Konfiguration aus der JSON-Datei"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Konvertiere String-Keys zurück zu Integers
                    return {int(k): v for k, v in data.items()}
            except (json.JSONDecodeError, FileNotFoundError):
                print("⚠️ Konfigurationsdatei konnte nicht geladen werden, verwende Standard-Einstellungen")
                return {}
        return {}

    def save_configs(self):
        """Speichert die Konfiguration in die JSON-Datei"""
        try:
            # Konvertiere Integer-Keys zu Strings für JSON
            data = {str(k): v for k, v in self.guild_configs.items()}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Fehler beim Speichern der Konfiguration: {e}")

    def get_guild_config(self, guild_id):
        if guild_id not in self.guild_configs:
            self.guild_configs[guild_id] = {
                "welcome_channel": None,
                "welcome_message": "Willkommen {user} auf unserem Server! 🎉",
                "welcome_image_url": None,
                "embed_color": 0x00ff00,
                "auto_role": None,
                "dm_welcome": False,
                "dm_message": "Willkommen auf unserem Discord Server! 🎉"
            }
            self.save_configs()  # Speichere die neue Konfiguration
        return self.guild_configs[guild_id]

    def update_guild_config(self, guild_id, key, value):
        if guild_id not in self.guild_configs:
            self.get_guild_config(guild_id)
        self.guild_configs[guild_id][key] = value
        self.save_configs()  # Speichere die Änderungen sofort

    async def on_ready(self):
        print(f'✅ Bot online - {len(self.guilds)} Server')
        print(f'📁 Konfiguration geladen für {len(self.guild_configs)} Server')
        try:
            synced = await self.tree.sync()
            print(f'🔄 {len(synced)} Commands synchronisiert')
        except Exception as e:
            print(f'❌ Sync-Fehler: {e}')

    async def on_member_join(self, member):
        guild_config = self.get_guild_config(member.guild.id)

        if guild_config.get("auto_role"):
            try:
                role = member.guild.get_role(guild_config["auto_role"])
                if role:
                    await member.add_roles(role)
            except Exception:
                pass

        if guild_config.get("welcome_channel"):
            channel = self.get_channel(guild_config["welcome_channel"])
            if channel:
                await self.send_welcome_message(channel, member, guild_config)

        if guild_config.get("dm_welcome"):
            try:
                await member.send(guild_config.get("dm_message", "Willkommen auf unserem Discord Server! 🎉"))
            except Exception:
                pass

    async def send_welcome_message(self, channel, member, config):
        try:
            embed = discord.Embed(
                title="🎉 Neues Mitglied!",
                description=config.get("welcome_message", "Willkommen {user} auf unserem Server! 🎉").format(
                    user=member.mention,
                    username=member.name,
                    server=member.guild.name
                ),
                color=config.get("embed_color", 0x00ff00)
            )

            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Mitglied", value=f"#{len(member.guild.members)}", inline=True)
            embed.add_field(name="📅 Beigetreten", value=discord.utils.format_dt(member.joined_at, style='R'),
                            inline=True)
            embed.add_field(name="📊 Account erstellt", value=discord.utils.format_dt(member.created_at, style='R'),
                            inline=True)
            embed.set_footer(text=f"User ID: {member.id}")

            if config.get("welcome_image_url"):
                embed.set_image(url=config["welcome_image_url"])

            await channel.send(embed=embed)

        except Exception:
            pass


bot = WelcomeBot()


@bot.tree.command(name="setup", description="Konfiguriere den Welcome Bot")
@app_commands.describe(
    channel="Welcome Channel auswählen",
    message="Custom Welcome Message (nutze {user}, {username}, {server})",
    image_url="URL für Welcome Image",
    color="Embed Farbe (Hex ohne #, z.B. ff0000 für rot)",
    auto_role="Auto-Role für neue Mitglieder",
    dm_welcome="DM Welcome aktivieren/deaktivieren",
    dm_message="DM Welcome Message"
)
async def setup(
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        message: Optional[str] = None,
        image_url: Optional[str] = None,
        color: Optional[str] = None,
        auto_role: Optional[discord.Role] = None,
        dm_welcome: Optional[bool] = None,
        dm_message: Optional[str] = None
):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Du benötigst die 'Server verwalten' Berechtigung!", ephemeral=True)
        return

    embed = discord.Embed(
        title="🛠️ Welcome Bot Setup",
        description="Konfiguration wird aktualisiert...",
        color=0x00ff00
    )

    guild_config = bot.get_guild_config(interaction.guild.id)
    changes_made = False

    if channel:
        bot.update_guild_config(interaction.guild.id, "welcome_channel", channel.id)
        embed.add_field(name="✅ Welcome Channel", value=channel.mention, inline=False)
        changes_made = True
    else:
        current_channel = bot.get_channel(guild_config.get("welcome_channel"))
        embed.add_field(
            name="📋 Welcome Channel",
            value=current_channel.mention if current_channel else "❌ Nicht gesetzt",
            inline=False
        )

    if message:
        bot.update_guild_config(interaction.guild.id, "welcome_message", message)
        embed.add_field(name="✅ Welcome Message", value=f"```{message[:150]}{'...' if len(message) > 150 else ''}```",
                        inline=False)
        changes_made = True
    else:
        current_message = guild_config.get("welcome_message")
        embed.add_field(name="📋 Welcome Message",
                        value=f"```{current_message[:150]}{'...' if len(current_message) > 150 else ''}```",
                        inline=False)

    if image_url:
        bot.update_guild_config(interaction.guild.id, "welcome_image_url", image_url)
        embed.add_field(name="✅ Welcome Image", value="🖼️ URL gesetzt", inline=False)
        changes_made = True
    else:
        current_image = guild_config.get("welcome_image_url")
        embed.add_field(name="📋 Welcome Image", value="🖼️ Gesetzt" if current_image else "❌ Nicht gesetzt",
                        inline=False)

    if color:
        try:
            color_int = int(color.replace('#', ''), 16)
            bot.update_guild_config(interaction.guild.id, "embed_color", color_int)
            embed.add_field(name="✅ Embed Farbe", value=f"🎨 #{color}", inline=False)
            changes_made = True
        except ValueError:
            embed.add_field(name="❌ Embed Farbe", value="Ungültiges Hex-Format! Nutze z.B. 'ff0000'", inline=False)
    else:
        current_color = guild_config.get("embed_color")
        embed.add_field(name="📋 Embed Farbe", value=f"🎨 #{current_color:06x}", inline=False)

    if auto_role:
        bot.update_guild_config(interaction.guild.id, "auto_role", auto_role.id)
        embed.add_field(name="✅ Auto-Role", value=f"🔰 {auto_role.mention}", inline=False)
        changes_made = True
    else:
        current_role_id = guild_config.get("auto_role")
        current_role = interaction.guild.get_role(current_role_id) if current_role_id else None
        embed.add_field(name="📋 Auto-Role", value=f"🔰 {current_role.mention}" if current_role else "❌ Nicht gesetzt",
                        inline=False)

    if dm_welcome is not None:
        bot.update_guild_config(interaction.guild.id, "dm_welcome", dm_welcome)
        embed.add_field(name="✅ DM Welcome", value="💬 Aktiviert" if dm_welcome else "❌ Deaktiviert", inline=False)
        changes_made = True
    else:
        current_dm = guild_config.get("dm_welcome")
        embed.add_field(name="📋 DM Welcome", value="💬 Aktiviert" if current_dm else "❌ Deaktiviert", inline=False)

    if dm_message:
        bot.update_guild_config(interaction.guild.id, "dm_message", dm_message)
        embed.add_field(name="✅ DM Message", value=f"```{dm_message[:100]}{'...' if len(dm_message) > 100 else ''}```",
                        inline=False)
        changes_made = True
    else:
        current_dm_msg = guild_config.get("dm_message")
        embed.add_field(name="📋 DM Message",
                        value=f"```{current_dm_msg[:100]}{'...' if len(current_dm_msg) > 100 else ''}```", inline=False)

    if changes_made:
        embed.set_footer(text="✅ Konfiguration wurde erfolgreich aktualisiert und gespeichert!")
        embed.color = 0x00ff00
    else:
        embed.set_footer(text="📋 Aktuelle Konfiguration wird angezeigt")
        embed.color = 0x0099ff

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="test-welcome", description="Teste die Welcome-Nachricht mit dir selbst")
async def test_welcome(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Du benötigst die 'Server verwalten' Berechtigung!", ephemeral=True)
        return

    guild_config = bot.get_guild_config(interaction.guild.id)

    if not guild_config.get("welcome_channel"):
        await interaction.response.send_message(
            "❌ Kein Welcome Channel konfiguriert! Nutze `/setup channel:#kanal` zuerst.", ephemeral=True)
        return

    channel = bot.get_channel(guild_config["welcome_channel"])
    if not channel:
        await interaction.response.send_message("❌ Welcome Channel nicht gefunden!", ephemeral=True)
        return

    await bot.send_welcome_message(channel, interaction.user, guild_config)

    embed = discord.Embed(
        title="✅ Test erfolgreich!",
        description=f"Test-Welcome-Nachricht wurde in {channel.mention} gesendet!",
        color=0x00ff00
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="welcome-info", description="Zeige aktuelle Welcome-Konfiguration")
async def welcome_info(interaction: discord.Interaction):
    guild_config = bot.get_guild_config(interaction.guild.id)

    embed = discord.Embed(
        title="📋 Welcome Bot Konfiguration",
        description=f"Aktuelle Einstellungen für **{interaction.guild.name}**",
        color=guild_config.get("embed_color", 0x00ff00)
    )

    channel = bot.get_channel(guild_config.get("welcome_channel"))
    embed.add_field(name="📢 Welcome Channel", value=channel.mention if channel else "❌ Nicht gesetzt", inline=False)

    message = guild_config.get("welcome_message")
    embed.add_field(name="💬 Welcome Message", value=f"```{message[:200]}{'...' if len(message) > 200 else ''}```",
                    inline=False)

    image_url = guild_config.get("welcome_image_url")
    embed.add_field(name="🖼️ Welcome Image", value="✅ Gesetzt" if image_url else "❌ Nicht gesetzt", inline=True)

    color = guild_config.get("embed_color")
    embed.add_field(name="🎨 Embed Farbe", value=f"#{color:06x}", inline=True)

    role_id = guild_config.get("auto_role")
    role = interaction.guild.get_role(role_id) if role_id else None
    embed.add_field(name="🔰 Auto-Role", value=role.mention if role else "❌ Nicht gesetzt", inline=True)

    dm_welcome = guild_config.get("dm_welcome")
    embed.add_field(name="💬 DM Welcome", value="✅ Aktiviert" if dm_welcome else "❌ Deaktiviert", inline=True)

    dm_message = guild_config.get("dm_message")
    embed.add_field(name="💬 DM Message", value=f"```{dm_message[:100]}{'...' if len(dm_message) > 100 else ''}```",
                    inline=False)

    embed.set_footer(text="Nutze /setup um Einstellungen zu ändern")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="reset-config", description="Setzt die Welcome-Konfiguration zurück")
async def reset_config(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Du benötigst die 'Server verwalten' Berechtigung!", ephemeral=True)
        return

    if interaction.guild.id in bot.guild_configs:
        del bot.guild_configs[interaction.guild.id]
        bot.save_configs()  # Speichere die Änderungen

    embed = discord.Embed(
        title="🔄 Konfiguration zurückgesetzt",
        description="Alle Welcome-Einstellungen wurden auf Standard zurückgesetzt und gespeichert.",
        color=0xff9900
    )

    embed.add_field(name="ℹ️ Nächster Schritt", value="Nutze `/setup` um den Bot neu zu konfigurieren.", inline=False)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="backup-config", description="Erstelle ein Backup der aktuellen Konfiguration")
async def backup_config(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ Du benötigst die 'Server verwalten' Berechtigung!", ephemeral=True)
        return

    try:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"guild_configs_backup_{timestamp}.json"

        # Erstelle eine Kopie der aktuellen Konfiguration
        data = {str(k): v for k, v in bot.guild_configs.items()}
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        embed = discord.Embed(
            title="💾 Backup erstellt",
            description=f"Konfiguration wurde erfolgreich gesichert als `{backup_filename}`",
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title="❌ Backup fehlgeschlagen",
            description=f"Fehler beim Erstellen des Backups: {str(e)}",
            color=0xff0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="help", description="Zeige alle verfügbaren Befehle")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Welcome Bot Hilfe",
        description="Alle verfügbaren Befehle und Informationen:",
        color=0x00ff00
    )

    embed.add_field(
        name="🛠️ `/setup`",
        value="Konfiguriere den Welcome Bot mit verschiedenen Optionen:\n"
              "• `channel`: Welcome Channel festlegen\n"
              "• `message`: Custom Welcome Message\n"
              "• `image_url`: URL für Welcome Image\n"
              "• `color`: Embed Farbe (Hex ohne #)\n"
              "• `auto_role`: Auto-Role für neue Mitglieder\n"
              "• `dm_welcome`: DM Welcome aktivieren\n"
              "• `dm_message`: DM Welcome Message",
        inline=False
    )

    embed.add_field(
        name="🧪 `/test-welcome`",
        value="Teste die Welcome-Nachricht mit deinen aktuellen Einstellungen",
        inline=False
    )

    embed.add_field(
        name="📋 `/welcome-info`",
        value="Zeige die aktuelle Welcome-Konfiguration an",
        inline=False
    )

    embed.add_field(
        name="🔄 `/reset-config`",
        value="Setzt alle Welcome-Einstellungen zurück",
        inline=False
    )

    embed.add_field(
        name="💾 `/backup-config`",
        value="Erstelle ein Backup der aktuellen Konfiguration",
        inline=False
    )

    embed.add_field(
        name="❓ `/help`",
        value="Zeige diese Hilfe-Nachricht",
        inline=False
    )

    embed.add_field(
        name="📝 Message Variablen",
        value="Du kannst folgende Variablen in deinen Messages verwenden:\n"
              "• `{user}` - Erwähnt den User (@Username)\n"
              "• `{username}` - Username ohne Erwähnung\n"
              "• `{server}` - Name des Servers",
        inline=False
    )

    embed.add_field(
        name="🎨 Farb-Beispiele",
        value="• `ff0000` - Rot\n"
              "• `00ff00` - Grün\n"
              "• `0099ff` - Blau\n"
              "• `ff9900` - Orange\n"
              "• `9900ff` - Lila",
        inline=False
    )

    embed.add_field(
        name="💾 Persistente Speicherung",
        value="Alle Einstellungen werden automatisch in `guild_configs.json` gespeichert und bleiben nach einem Neustart erhalten!",
        inline=False
    )

    embed.set_footer(text="Benötigst du weitere Hilfe? Kontaktiere einen Administrator!")

    await interaction.response.send_message(embed=embed)


def main():
    print("🤖 Discord Welcome Bot mit persistenter Konfiguration")
    print("=" * 50)

    token = input("🔑 Bot Token: ").strip()

    if not token:
        print("❌ Kein Token!")
        return

    print("🚀 Bot wird gestartet...")
    print("💾 Konfigurationsdatei: guild_configs.json")

    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Ungültiger Token!")
    except discord.PrivilegedIntentsRequired:
        print("❌ 'Server Members Intent' fehlt!")
    except Exception as e:
        print(f"❌ Fehler: {e}")


if __name__ == "__main__":
    main()

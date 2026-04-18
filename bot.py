import discord
from discord.ext import commands, tasks
import asyncio
import json
import os
import logging
from dotenv import load_dotenv
import scrape

# ─────────────────────────────────────────────
#  LOAD TOKEN
# ─────────────────────────────────────────────
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN tidak ditemukan! Buat file .env dengan isi: DISCORD_TOKEN=token_kamu")

# ─────────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


# ─────────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    log.info(f"Bot online sebagai {bot.user} (ID: {bot.user.id})")
    update_films.start()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Tunggu {error.retry_after:.0f} detik lagi.", delete_after=5)
    else:
        log.error(f"Error command '{ctx.command}': {error}", exc_info=True)
        await ctx.send("❌ Terjadi error. Coba lagi nanti.")


# ─────────────────────────────────────────────
#  BACKGROUND TASK: AUTO UPDATE
# ─────────────────────────────────────────────
@tasks.loop(hours=3)
async def update_films():
    log.info("Auto update film dimulai...")
    try:
        success = await asyncio.get_event_loop().run_in_executor(None, scrape.scrape_films)
        if success:
            log.info("Auto update berhasil.")
        else:
            log.warning("Auto update gagal.")
    except Exception as e:
        log.error(f"Error saat auto update: {e}", exc_info=True)


@update_films.before_loop
async def before_update():
    await bot.wait_until_ready()


# ─────────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────────
@bot.command(name="films")
@commands.cooldown(1, 10, commands.BucketType.user)
async def cmd_films(ctx):
    """Tampilkan daftar film terbaru."""
    try:
        with open("movies.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        movies = data.get("movies", [])
        last_updated = data.get("last_updated", "?")
        total = data.get("total", len(movies))

        if not movies:
            await ctx.send("❌ Belum ada data film. Ketik `!update` dulu.")
            return

        embed = discord.Embed(
            title="🎥 Film Streaming Terbaru",
            color=0xe63946
        )
        embed.set_footer(text=f"Total {total} film • Update: {last_updated} • !update untuk refresh")

        preview = movies[:10]
        lines = []
        for i, m in enumerate(preview, 1):
            rating = f" ★{m['rating']}" if m.get("rating") else ""
            year = f" ({m['year']})" if m.get("year") else ""
            lines.append(f"`{i:02d}` [{m['title']}{year}{rating}]({m['player_url']})")

        embed.description = "\n".join(lines)
        embed.add_field(
            name="📋 Info",
            value=f"Menampilkan 10 dari {total} film\nKetik `!cari <judul>` untuk cari film spesifik",
            inline=False
        )

        await ctx.send(embed=embed)

    except FileNotFoundError:
        await ctx.send("❌ Belum ada data film. Ketik `!update` dulu.")
    except json.JSONDecodeError:
        await ctx.send("❌ File data rusak. Ketik `!update` untuk regenerate.")
    except Exception as e:
        log.error(f"Error cmd_films: {e}", exc_info=True)
        await ctx.send("❌ Terjadi error. Coba lagi nanti.")


@bot.command(name="update")
@commands.cooldown(1, 30, commands.BucketType.user)
async def cmd_update(ctx):
    """Update manual daftar film dari lk21."""
    msg = await ctx.send("🔄 Sedang mengambil data film dari lk21...")
    try:
        success = await asyncio.get_event_loop().run_in_executor(None, scrape.scrape_films)
        if success:
            with open("movies.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            total = data.get("total", 0)
            await msg.edit(content=f"✅ Update berhasil! **{total} film** tersedia.\nKetik `!films` untuk melihat daftar.")
        else:
            await msg.edit(content="❌ Update gagal. Coba lagi nanti.")
    except Exception as e:
        log.error(f"Error cmd_update: {e}", exc_info=True)
        await msg.edit(content="❌ Terjadi error saat update.")


@bot.command(name="cari")
@commands.cooldown(1, 5, commands.BucketType.user)
async def cmd_cari(ctx, *, keyword: str = None):
    """Cari film berdasarkan keyword. Contoh: !cari avengers"""
    if not keyword:
        await ctx.send("❌ Masukkan keyword. Contoh: `!cari avengers`")
        return

    try:
        with open("movies.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        movies = data.get("movies", [])
        results = [m for m in movies if keyword.lower() in m["title"].lower()]

        if not results:
            await ctx.send(f"🔍 Tidak ada film dengan keyword **{keyword}**.")
            return

        embed = discord.Embed(
            title=f"🔍 Hasil pencarian: {keyword}",
            color=0xe63946
        )

        lines = []
        for i, m in enumerate(results[:15], 1):
            rating = f" ★{m['rating']}" if m.get("rating") else ""
            year = f" ({m['year']})" if m.get("year") else ""
            lines.append(f"`{i:02d}` [{m['title']}{year}{rating}]({m['player_url']})")

        embed.description = "\n".join(lines)
        embed.set_footer(text=f"Ditemukan {len(results)} film • Menampilkan maks 15")

        await ctx.send(embed=embed)

    except FileNotFoundError:
        await ctx.send("❌ Belum ada data film. Ketik `!update` dulu.")
    except Exception as e:
        log.error(f"Error cmd_cari: {e}", exc_info=True)
        await ctx.send("❌ Terjadi error saat mencari.")


@bot.command(name="status")
async def cmd_status(ctx):
    """Cek status bot dan data film."""
    try:
        with open("movies.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        total = data.get("total", 0)
        last_updated = data.get("last_updated", "?")
        status_text = f"✅ {total} film tersedia\n🕐 Update: {last_updated}"
    except FileNotFoundError:
        status_text = "❌ Belum ada data film"
    except Exception:
        status_text = "⚠️ Gagal baca data"

    embed = discord.Embed(title="📊 Status Bot", color=0x2ecc71)
    embed.add_field(name="🎥 Data Film", value=status_text, inline=False)
    embed.add_field(name="⏰ Auto Update", value="Setiap 3 jam", inline=True)
    embed.add_field(name="🤖 Bot", value=f"{bot.user.name}", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="infofilm")
async def cmd_infofilm(ctx):
    """Tampilkan daftar command."""
    embed = discord.Embed(title="📖 Daftar Command", color=0xe63946)
    embed.add_field(name="`!films`", value="Lihat 10 film terbaru", inline=False)
    embed.add_field(name="`!cari <keyword>`", value="Cari film. Contoh: `!cari one piece`", inline=False)
    embed.add_field(name="`!update`", value="Update data film OwoBim", inline=False)
    embed.add_field(name="`!status`", value="Cek status bot & jumlah film", inline=False)
    embed.add_field(name="`!infofilm`", value="Tampilkan daftar command ini", inline=False)
    await ctx.send(embed=embed)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
async def main():
    async with bot:
        try:
            await bot.start(TOKEN)
        except discord.LoginFailure:
            log.critical("TOKEN tidak valid! Cek DISCORD_TOKEN di .env atau Railway Variables.")
        except discord.PrivilegedIntentsRequired:
            log.critical("Aktifkan Message Content Intent di Discord Developer Portal.")
        except KeyboardInterrupt:
            log.info("Bot dihentikan.")
        except Exception as e:
            log.critical(f"Error fatal: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

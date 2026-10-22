"""Data and icons for the site's combo web (Nikita 2026-10-22: "у комбо тоже есть иконки, и я бы
сделал паутину всяких комбо до третьего тира, наподобие Path of Exile").

Sources, all in the game project:
- recipes: docs/game-design.md, tables "II порядок" and "III порядок" (the approved rules);
- glyphs and plate colours: tools/skill_icon_map.py and tools/title_icon_map.py, the same tables
  the game's DA_IconSet_GameIcons is authored from; glyph PNGs from staging/game_icons_glyphs
  (game-icons.net, CC BY 3.0 - the site credits it);
- the tile itself is drawn the way the game draws it: a white glyph on a coloured plate in a
  dark frame; titles wear their tier colour (gold II, crimson III).

Writes site/assets/icons/<key>.webp and site/combos.js (nodes, recipes and the ring order).
"""
import json
import math
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

GAME = Path(r"C:\Projects\SkillStorm")
SITE = Path(__file__).resolve().parents[1] / "site"
sys.path.insert(0, str(GAME / "tools"))
import skill_icon_map  # noqa: E402
import title_icon_map  # noqa: E402

GLYPHS = GAME / "staging" / "game_icons_glyphs"
OUT = SITE / "assets" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

# the GDD's skill names -> the icon tables' keys
SKILLS = {
    "Multishot": "Multishot", "Rapid Fire": "RapidFire", "Piercing": "Pierce", "Power": "Power",
    "Vampirism": "Vampirism", "Rear Shot": "RearShot", "Poison": "Poison", "Ricochet": "Ricochet",
    "Blaze": "Blaze", "Freeze": "Freeze", "Crit Master": "CritMaster", "Orbit": "Orbit",
    "Long Shot": "LongShot", "Big Shots": "BigShots", "Splinter": "Split", "Diagonal Shots": "Diagonal",
    "Seeker": "Homing", "Executioner": "Executioner", "Rage": "Rage", "Run and Gun": "RunAndGun",
    "Zone Walker": "ZoneWalker", "Swift Feet": "Swift", "Bloodthirst": "Bloodthirst",
    "Vitality": "Vitality", "Carapace": "Block", "Lightning": "Lightning",
}
# what each skill does at its first level, in short English (docs/game-design.md, the skills table)
SKILL_DESC = {
    "Multishot": "+1 projectile alongside your shot",
    "Rapid Fire": "+30% attack speed",
    "Piercing": "shots pierce 2 more targets",
    "Power": "+35% damage",
    "Vampirism": "heal 15% of the damage you deal",
    "Rear Shot": "an extra shot behind you",
    "Poison": "poisons enemies for 6 s",
    "Ricochet": "shots bounce on to another enemy",
    "Blaze": "sets enemies on fire for 3 s",
    "Freeze": "slows enemies by 35% for 2 s",
    "Crit Master": "+15% crit chance, +25% crit damage",
    "Orbit": "two satellites circle you",
    "Long Shot": "+20% attack range",
    "Big Shots": "+25% projectile size",
    "Splinter": "pierces and bounces throw off extra shards",
    "Diagonal Shots": "two extra diagonal shots at half damage",
    "Seeker": "shots seek out enemies",
    "Executioner": "+50% damage to foes below 30% health",
    "Rage": "+40% damage below 35% health",
    "Run and Gun": "shoot on the move at 50% damage",
    "Zone Walker": "-40% damage from the storm",
    "Swift Feet": "+15% move speed",
    "Bloodthirst": "+10 health for every rival you kill",
    "Vitality": "+30% max health",
    "Carapace": "+20 max armor",
    "Lightning": "15% chance to shock on hit",
}
# the twists, in short English (the GDD's Russian lines, said for a player)
TWISTS = {
    "Bullet Storm": "every fifth volley fires twice",
    "Shredder": "pierced shards keep their bite",
    "Bloodbath": "overhealing turns into a shield",
    "Twin Fang": "the rear shot gets multishot too",
    "Epidemic": "poisoned kills leave a toxic cloud",
    "Wildfire": "burning foes leave a trail of fire",
    "Red Harvest": "poison ticks heal you",
    "Cold Blood": "the first hit on a frozen foe crits",
    "Thermal Shock": "burning + frozen = stunned",
    "Frost Crown": "an icy orb freezes its trail",
    "Sun Dance": "orbs spark with every shot",
    "Sniper": "crits at max range pierce through",
    "Skewer": "a shot through three foes flies forever",
    "Avalanche": "shots grow as they fly",
    "Juggernaut": "shots knock enemies back",
    "Fractal": "shards split again",
    "Buckshot": "diagonal shots split too",
    "Crossfire": "each diagonal hunts its own target",
    "Bloodhound": "seekers go for the wounded",
    "Guillotine": "executions reload your shot",
    "Berserker": "enraged, you shoot on the run at full power",
    "Blizzard": "leave an icy trail as you run",
    "Eye of the Storm": "always enraged inside the storm",
    "Stormchaser": "unseen in the storm until you shoot",
    "Headhunter": "a kill gives a burst of speed",
    "Trophy Hunter": "every kill: +1 max health",
    "Bulwark": "each enemy's first shot is blocked",
    "Riposte": "a block fires back",
    "Hurricane": "a 360° ring volley every 8 s",
    "Plaguelord": "your poison cloud heals you",
    "Absolute Zero": "stunned kills shatter into ice",
    "Darkness": "kills open vortexes that drag the crowd in",
    "Reaper": "after an execution the shot finds the next wounded",
    "Godspeed": "kills grant 4 s of full-speed running",
    "Titanheart": "a full shield bursts into a shockwave",
}


def key(name):
    # the icon tables spell names in CamelCase: "Eye of the Storm" -> EyeOfTheStorm
    return "".join(w[:1].upper() + w[1:] for w in name.split())


def gdd_titles():
    text = (GAME / "docs" / "game-design.md").read_text(encoding="utf-8")
    titles = []
    for tier, head in ((2, "### II порядок"), (3, "### III порядок")):
        part = text[text.index(head):]
        part = part[part.index("|---|"):]
        for line in part.split("\n")[1:]:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip("|").split("|")]
            name = cells[0].split(" (")[0]
            parts = [p.strip().replace(" ур.2", "") for p in cells[1].split("+")]
            titles.append({"name": name, "tier": tier, "req": parts})
    return titles


def tile(glyph, color, path, size=96):
    """The game's tile: dark frame, a coloured plate with a soft top light, a white glyph."""
    s = size * 4
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.16), fill=(52, 54, 48, 255))
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    inset = int(s * 0.07)
    plate = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    pd = ImageDraw.Draw(plate)
    for y in range(inset, s - inset):
        k = (y - inset) / (s - 2 * inset)
        f = 1.14 - 0.26 * k          # lighter at the top, deeper at the foot
        pd.line((inset, y, s - inset, y), fill=(min(255, int(r * f)), min(255, int(g * f)), min(255, int(b * f)), 255))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((inset, inset, s - inset - 1, s - inset - 1), radius=int(s * 0.1), fill=255)
    im.paste(plate, (0, 0), mask)
    gl = Image.open(GLYPHS / (glyph + ".png")).convert("RGBA")
    gs = int(s * 0.66)
    gl = gl.resize((gs, gs), Image.LANCZOS)
    shadow = Image.new("RGBA", gl.size, (0, 0, 0, 0))
    shadow.putalpha(gl.split()[3].point(lambda a: int(a * 0.35)))
    off = (s - gs) // 2
    im.alpha_composite(shadow, (off, off + int(s * 0.02)))
    im.alpha_composite(gl, (off, off))
    im.resize((size, size), Image.LANCZOS).save(path, "WEBP", quality=90)


def ring_order(skill_keys, pairs):
    """Order the skills round the ring so recipe pairs sit close: fewer, shorter crossings."""
    rnd = random.Random(5)
    order = skill_keys[:]
    n = len(order)

    def cost(o):
        pos = {k: i for i, k in enumerate(o)}
        c = 0
        for a, b in pairs:
            dd = abs(pos[a] - pos[b])
            c += min(dd, n - dd) ** 2
        return c

    best, cur = cost(order), cost(order)
    t = 30.0
    for step in range(60000):
        i, j = rnd.randrange(n), rnd.randrange(n)
        order[i], order[j] = order[j], order[i]
        c = cost(order)
        if c <= cur or rnd.random() < math.exp((cur - c) / t):
            cur = c
            best = min(best, c)
        else:
            order[i], order[j] = order[j], order[i]
        t = max(0.05, t * 0.9998)
    return order


def main():
    titles = gdd_titles()
    skills = []
    for name, k in SKILLS.items():
        tile(skill_icon_map.GLYPHS[k], skill_icon_map.COLORS[k], OUT / f"s_{k}.webp")
        skills.append({"id": "s_" + k, "name": name, "desc": SKILL_DESC[name]})
    nodes = []
    for t in titles:
        k = key(t["name"])
        tile(title_icon_map.GLYPHS[k], title_icon_map.TIER_COLORS[t["tier"]], OUT / f"t_{k}.webp")
        req = []
        for r in t["req"]:
            if r in SKILLS:
                req.append("s_" + SKILLS[r])
            else:
                req.append("t_" + key(r))
        nodes.append({"id": "t_" + k, "name": t["name"], "tier": t["tier"], "req": req, "twist": TWISTS[t["name"]]})
    pairs = [(a, b) for t in nodes if t["tier"] == 2 for a in t["req"] for b in t["req"] if a < b]
    order = ring_order([s["id"] for s in skills], pairs)
    data = {"skills": skills, "titles": nodes, "ring": order}
    js = ("/* The combo web's data, generated by tools_tripo/build_combo_web.py from the game's\n"
          "   design document and icon tables - edit there, not here. */\n"
          "export const COMBOS = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    (SITE / "combos.js").write_text(js, encoding="utf-8")
    print(len(skills), "skills,", len(nodes), "titles; ring:", " ".join(o[2:] for o in order))


if __name__ == "__main__":
    main()

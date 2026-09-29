"""Generate the repository's lightweight, privacy-safe V1 walkthrough GIF."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public" / "assets" / "caresathi-v1-walkthrough.gif"
OUT.parent.mkdir(parents=True, exist_ok=True)

W, H = 1120, 650
BG, INK, SOFT, PINE, MINT, CORAL, WHITE, LINE = "#f7faf8", "#12332e", "#65807a", "#12584d", "#def4eb", "#f2765d", "#ffffff", "#d9e8e2"
FONT = Path("C:/Windows/Fonts/segoeui.ttf")
BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def text(draw, xy, value, size, color=INK, bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=color, anchor=anchor)


def pill(draw, box, label, fill=MINT, color=PINE):
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=fill)
    text(draw, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), label, 14, color, True, "mm")


def card(draw, box, title, subtitle="", accent=MINT):
    draw.rounded_rectangle(box, radius=20, fill=WHITE, outline=LINE, width=2)
    draw.rounded_rectangle((box[0] + 18, box[1] + 18, box[0] + 58, box[1] + 58), radius=12, fill=accent)
    text(draw, (box[0] + 72, box[1] + 19), title, 18, INK, True)
    if subtitle:
        text(draw, (box[0] + 72, box[1] + 44), subtitle, 13, SOFT)


def shell(title, label, step, bounce=0):
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    draw.ellipse((-170, -210, 420, 340), fill="#e5f7f0")
    draw.ellipse((800, 390, 1280, 850), fill="#fff0e9")
    draw.rounded_rectangle((34, 28, W - 34, 94), radius=20, fill=WHITE, outline=LINE)
    draw.rounded_rectangle((55, 43, 101, 79), radius=13, fill=PINE)
    text(draw, (78, 61), "♡", 26, WHITE, True, "mm")
    text(draw, (115, 53), "Care", 24, INK, True)
    text(draw, (171, 53), "Sathi", 24, PINE, True)
    pill(draw, (785, 45, 900, 76), "V1 WALKTHROUGH", "#ecf6f2")
    text(draw, (1030, 60), f"0{step} / 04", 14, SOFT, True, "mm")
    text(draw, (60, 132), label.upper(), 14, PINE, True)
    text(draw, (60, 162), title, 35, INK, True)
    return image, draw


def landing(bounce):
    image, draw = shell("Care, when family can't be there.", "01 · discover CareSathi", 1, bounce)
    text(draw, (60, 220), "A trusted space to find non-clinical hospital", 18, SOFT)
    text(draw, (60, 247), "companionship, exactly when it is needed.", 18, SOFT)
    draw.rounded_rectangle((60, 292, 270, 350), radius=16, fill=CORAL)
    text(draw, (165, 321), "Find a CareSathi  →", 16, WHITE, True, "mm")
    draw.rounded_rectangle((625, 154 + bounce, 1015, 530 + bounce), radius=42, fill="#b8e5d6")
    draw.ellipse((700, 205 + bounce, 930, 435 + bounce), fill="#f3c8ad")
    draw.rounded_rectangle((755, 270 + bounce, 870, 440 + bounce), radius=50, fill="#244f48")
    card(draw, (580, 445 + bounce, 815, 526 + bounce), "24/7 support", "Day & night availability", "#fff0d8")
    card(draw, (855, 190 + bounce, 1055, 271 + bounce), "ID verified", "Trusted profile", "#def4eb")
    return image


def family(bounce):
    image, draw = shell("Create a care request in minutes.", "02 · family portal", 2, bounce)
    draw.rounded_rectangle((60, 225, 620, 562), radius=22, fill=WHITE, outline=LINE, width=2)
    text(draw, (86, 255), "New care request", 22, INK, True)
    fields = [("Patient", "Parent / loved one"), ("Hospital", "Hospital name and ward"), ("When", "Date, time and hours"), ("Support", "Companionship or specialist need")]
    for i, (label, value) in enumerate(fields):
        y = 305 + i * 52
        text(draw, (86, y), label, 12, SOFT, True)
        draw.rounded_rectangle((200, y - 8, 573, y + 25), radius=8, fill="#f4f8f6")
        text(draw, (215, y), value, 13, SOFT)
    draw.rounded_rectangle((86, 514, 300, 548), radius=12, fill=CORAL)
    text(draw, (193, 531), "Publish request", 14, WHITE, True, "mm")
    card(draw, (680, 235 + bounce, 1015, 338 + bounce), "Transparent pricing", "Base rate + visible night / specialist premiums", "#fff0d8")
    card(draw, (680, 364 + bounce, 1015, 467 + bounce), "Private family updates", "OTP shift start and secure live watch", "#def4eb")
    return image


def caretaker(bounce):
    image, draw = shell("The right local CareSathi can accept.", "03 · caretaker portal", 3, bounce)
    draw.rounded_rectangle((60, 230, 710, 540), radius=22, fill=WHITE, outline=LINE, width=2)
    text(draw, (88, 258), "Available near you", 21, INK, True)
    card(draw, (88, 300, 682, 408), "Care request · Pune", "Night vigil · 8 hours · ₹150 / hour", "#def4eb")
    pill(draw, (504, 424 + bounce, 662, 464 + bounce), "Accept request", CORAL, WHITE)
    text(draw, (88, 445), "✓ Skill match     ✓ Availability     ✓ Verified family", 14, PINE, True)
    card(draw, (770, 260 + bounce, 1035, 360 + bounce), "Earnings", "Track shifts, payouts and ratings", "#fff0d8")
    card(draw, (770, 388 + bounce, 1035, 488 + bounce), "Availability", "Set hours and preferred hospitals", "#def4eb")
    return image


def admin(bounce):
    image, draw = shell("Keep the marketplace safe and accountable.", "04 · admin workspace", 4, bounce)
    card(draw, (60, 230, 325, 336), "Profile moderation", "Approve verified CareSathis", "#def4eb")
    card(draw, (355, 230, 620, 336), "Marketplace health", "Requests, ratings and shift value", "#fff0d8")
    card(draw, (650, 230, 1015, 336), "Account safety", "Suspend or restore suspicious accounts", "#fde6df")
    draw.rounded_rectangle((60, 375 + bounce, 1015, 530 + bounce), radius=22, fill=PINE)
    text(draw, (90, 404 + bounce), "V1 launch controls", 22, WHITE, True)
    text(draw, (90, 439 + bounce), "Clean production database · Private admin access · No demo patient data", 16, "#c9e7df")
    pill(draw, (90, 475 + bounce, 285, 508 + bounce), "Ready for Vercel", "#d9f3e9", PINE)
    return image


builders = [landing, family, caretaker, admin]
frames = []
for builder in builders:
    for bounce in (4, 0, -3, 0):
        frames.append(builder(bounce))
frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=[440, 440, 440, 1800] * 4, loop=0, optimize=True)
print(OUT)

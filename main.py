# main.py
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import json, os, hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = 'ruhi_qnr_ultra_girly_secret_2024'

DB_FILE = 'database.json'

DEFAULT_DB = {
    "password": hashlib.sha256("admin123".encode()).hexdigest(),
    "profile": {
        "name": "RUHI",
        "subtitle": "& QNR",
        "tagline": "She's the storm they never saw coming 🌸",
        "bio": "A girl made of moonlight, roses & chaos. Too pretty to be understood, too wild to be tamed. Living in her own pink universe where rules don't exist. 💕",
        "age": "19 ✨",
        "birthday": "🎂 January 1st",
        "location": "📍 In Your Heart",
        "zodiac": "♑ Capricorn Queen",
        "hobbies": "🎨 Art, Music & Dreaming",
        "music": "🎵 Dark Pop & Lo-fi",
        "vibe": "🌙 Chaotic Soft Girl",
        "bestie": "💗 QNR is My Person",
        "quote": "She needed a hero, so she became one. 🦋",
        "avatar": "https://i.pinimg.com/736x/8b/16/7a/8b167af653c2399dd93b952a48740620.jpg",
        "avatar2": ""
    },
    "background_video": "",
    "background_music": "",
    "socials": {
        "instagram": "https://instagram.com",
        "twitter": "https://twitter.com",
        "tiktok": "https://tiktok.com",
        "youtube": "https://youtube.com",
        "snapchat": "https://snapchat.com"
    },
    "media_map": {
        "age": "", "birthday": "", "location": "",
        "zodiac": "", "hobbies": "", "music": "",
        "vibe": "", "bestie": "", "quote": ""
    },
    "intro_lines": [
        "Loading her universe... 🌸",
        "Sprinkling pink magic... ✨",
        "Waking up the butterflies... 🦋",
        "Pouring love & chaos... 💕",
        "She's almost ready... 💗",
        "Welcome to her world. 🌙"
    ]
}

def load_db():
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB); return DEFAULT_DB
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
        for k in DEFAULT_DB:
            if k not in data: data[k] = DEFAULT_DB[k]
        if 'media_map' not in data: data['media_map'] = DEFAULT_DB['media_map']
        if 'bestie' not in data.get('media_map', {}): data['media_map']['bestie'] = ''
        if 'bestie' not in data.get('profile', {}): data['profile']['bestie'] = DEFAULT_DB['profile']['bestie']
        if 'subtitle' not in data.get('profile', {}): data['profile']['subtitle'] = DEFAULT_DB['profile']['subtitle']
        if 'avatar2' not in data.get('profile', {}): data['profile']['avatar2'] = ''
        if 'background_video' not in data: data['background_video'] = ''
        return data
    except: return DEFAULT_DB

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=2)

def login_required(f):
    @wraps(f)
    def dec(*a, **k):
        if not session.get('admin'): return redirect('/admin/login')
        return f(*a, **k)
    return dec

# ══════════════════════════════════════════════
#  MAIN TEMPLATE — GOD LEVEL
# ══════════════════════════════════════════════
MAIN = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ p.name }} {{ p.subtitle }} 🌸</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,600&family=Dancing+Script:wght@400;600;700&family=Poppins:wght@200;300;400;500;600;700&family=Montserrat:wght@100;200;300;400;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
:root{
  --pk:#ff4d8d;--pk2:#ff85b3;--pk3:#ffc2d9;--pk4:#fff0f5;
  --pp:#b94fcc;--pp2:#d17fe8;--pp3:#f0c6ff;
  --rd:#e8305a;--rd2:#ff6b8a;
  --gold:#ffd700;--gold2:#ffec7a;
  --dark:#1a0020;--dark2:#2d0035;--dark3:#0d0015;
  --glass:rgba(255,255,255,0.07);
  --glass2:rgba(255,255,255,0.12);
  --border:rgba(255,130,180,0.25);
  --shadow:rgba(255,77,141,0.4);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{
  width:100%;min-height:100vh;
  background:var(--dark3);
  font-family:'Poppins',sans-serif;
  overflow-x:hidden;
  cursor:none;
}

/* ── CUSTOM CURSOR ── */
#cursor{
  position:fixed;width:12px;height:12px;
  background:var(--pk);border-radius:50%;
  pointer-events:none;z-index:99999;
  transform:translate(-50%,-50%);
  transition:width .2s,height .2s,background .2s;
  box-shadow:0 0 20px var(--pk),0 0 40px var(--pk2);
}
#cursor-ring{
  position:fixed;width:36px;height:36px;
  border:2px solid rgba(255,130,180,0.5);
  border-radius:50%;pointer-events:none;z-index:99998;
  transform:translate(-50%,-50%);
  transition:all .12s ease-out;
}
body:has(.bio-card:hover) #cursor{width:30px;height:30px;background:var(--pp);}

/* ── CURSOR TRAIL ── */
.trail{
  position:fixed;border-radius:50%;pointer-events:none;
  z-index:99990;transform:translate(-50%,-50%);
  animation:trailFade .8s forwards;
}
@keyframes trailFade{
  0%{opacity:.8;transform:translate(-50%,-50%) scale(1);}
  100%{opacity:0;transform:translate(-50%,-50%) scale(0);}
}

/* ══ LOADING SCREEN ══ */
#loader{
  position:fixed;inset:0;z-index:9000;
  background:var(--dark3);
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  gap:30px;
}
.loader-petals{
  position:relative;width:120px;height:120px;
}
.loader-petal{
  position:absolute;top:50%;left:50%;
  width:16px;height:40px;
  background:linear-gradient(to bottom,var(--pk),var(--pp));
  border-radius:50% 50% 50% 50%/60% 60% 40% 40%;
  transform-origin:8px 60px;
  animation:petalSpin 1.5s ease-in-out infinite;
  box-shadow:0 0 10px var(--pk);
}
.loader-petal:nth-child(1){transform:rotate(0deg) translateY(-60px);animation-delay:0s;}
.loader-petal:nth-child(2){transform:rotate(45deg) translateY(-60px);animation-delay:.1s;}
.loader-petal:nth-child(3){transform:rotate(90deg) translateY(-60px);animation-delay:.2s;}
.loader-petal:nth-child(4){transform:rotate(135deg) translateY(-60px);animation-delay:.3s;}
.loader-petal:nth-child(5){transform:rotate(180deg) translateY(-60px);animation-delay:.4s;}
.loader-petal:nth-child(6){transform:rotate(225deg) translateY(-60px);animation-delay:.5s;}
.loader-petal:nth-child(7){transform:rotate(270deg) translateY(-60px);animation-delay:.6s;}
.loader-petal:nth-child(8){transform:rotate(315deg) translateY(-60px);animation-delay:.7s;}
.loader-center{
  position:absolute;top:50%;left:50%;
  width:24px;height:24px;
  background:radial-gradient(circle,#fff,var(--gold));
  border-radius:50%;
  transform:translate(-50%,-50%);
  box-shadow:0 0 20px var(--gold),0 0 40px #fff;
  animation:centerPulse 1s ease-in-out infinite;
}
@keyframes petalSpin{
  0%,100%{opacity:.5;transform:rotate(var(--r,0deg)) translateY(-60px) scale(.8);}
  50%{opacity:1;transform:rotate(var(--r,0deg)) translateY(-60px) scale(1.1);}
}
@keyframes centerPulse{0%,100%{transform:translate(-50%,-50%) scale(1);}50%{transform:translate(-50%,-50%) scale(1.4);}}

.loader-text{
  font-family:'Dancing Script',cursive;
  font-size:clamp(1.2rem,3vw,1.8rem);
  color:#fff;text-align:center;
  text-shadow:0 0 20px var(--pk),0 0 40px var(--pp);
  animation:textPulse 1.5s ease-in-out infinite;
}
@keyframes textPulse{0%,100%{opacity:.6;}50%{opacity:1;}}

.loader-bar-wrap{
  width:min(300px,70vw);height:3px;
  background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden;
}
.loader-bar{
  height:100%;width:0%;
  background:linear-gradient(90deg,var(--pk),var(--pp),var(--rd),var(--pk));
  background-size:300%;
  border-radius:2px;
  animation:barGlow 1s linear infinite;
  transition:width .1s linear;
}
@keyframes barGlow{0%{background-position:0%;}100%{background-position:300%;}}

/* ══ BACKGROUND VIDEO ══ */
#bg-video-wrap{
  position:fixed;inset:0;z-index:0;overflow:hidden;
}
#bg-video{
  position:absolute;
  min-width:100%;min-height:100%;
  width:auto;height:auto;
  top:50%;left:50%;
  transform:translate(-50%,-50%);
  object-fit:cover;
}
.bg-overlay{
  position:absolute;inset:0;
  background:
    radial-gradient(ellipse at 20% 20%,rgba(185,79,204,.55) 0%,transparent 55%),
    radial-gradient(ellipse at 80% 80%,rgba(255,77,141,.55) 0%,transparent 55%),
    radial-gradient(ellipse at 50% 50%,rgba(13,0,21,.7) 0%,transparent 80%),
    linear-gradient(135deg,rgba(26,0,32,.85),rgba(13,0,21,.9));
}

/* ── fallback bg if no video ── */
.bg-fallback{
  position:fixed;inset:0;z-index:0;
  background:
    radial-gradient(ellipse at 15% 15%,rgba(185,79,204,.6),transparent 50%),
    radial-gradient(ellipse at 85% 85%,rgba(232,48,90,.5),transparent 50%),
    radial-gradient(ellipse at 50% 50%,rgba(255,77,141,.3),transparent 60%),
    linear-gradient(135deg,#1a0020 0%,#0d0015 40%,#2d0035 100%);
}

/* ══ FLOATING PARTICLES ══ */
#particles{position:fixed;inset:0;z-index:1;pointer-events:none;overflow:hidden;}
.fp{
  position:absolute;
  animation:fpRise linear infinite;
  opacity:0;
}
@keyframes fpRise{
  0%{transform:translateY(110vh) rotate(0deg) scale(0);opacity:0;}
  5%{opacity:1;}
  95%{opacity:.8;}
  100%{transform:translateY(-10vh) rotate(720deg) scale(.5);opacity:0;}
}

/* ══ MAIN SITE WRAPPER ══ */
#site{
  position:relative;z-index:10;
  min-height:100vh;
  opacity:0;
  transition:opacity 1.2s ease;
}
#site.show{opacity:1;}

/* ══ HERO SECTION ══ */
.hero{
  min-height:100vh;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  text-align:center;
  padding:60px 20px 40px;
  position:relative;
}

/* ── Crown ── */
.crown{
  font-size:clamp(2rem,5vw,3.5rem);
  animation:crownFloat 3s ease-in-out infinite;
  filter:drop-shadow(0 0 20px var(--gold));
  margin-bottom:10px;display:block;
}
@keyframes crownFloat{
  0%,100%{transform:translateY(0) rotate(-5deg);}
  50%{transform:translateY(-15px) rotate(5deg);}
}

/* ── Avatar stack ── */
.avatar-stack{
  position:relative;display:inline-flex;
  justify-content:center;align-items:center;
  margin-bottom:30px;
}
.avatar-glow-ring{
  position:absolute;
  border-radius:50%;
  animation:ringPulse 2s ease-in-out infinite;
}
.agr1{
  width:calc(var(--as) + 40px);height:calc(var(--as) + 40px);
  border:2px solid rgba(255,77,141,.6);
  --as:160px;
}
.agr2{
  width:calc(var(--as) + 70px);height:calc(var(--as) + 70px);
  border:1px solid rgba(185,79,204,.3);
  --as:160px;
}
.agr3{
  width:calc(var(--as) + 100px);height:calc(var(--as) + 100px);
  border:1px solid rgba(255,77,141,.15);
  --as:160px;
  animation-direction:reverse;
}
@keyframes ringPulse{
  0%,100%{transform:rotate(0deg) scale(1);opacity:.7;}
  50%{transform:rotate(180deg) scale(1.05);opacity:1;}
}
.avatar-img{
  width:clamp(130px,18vw,175px);height:clamp(130px,18vw,175px);
  border-radius:50%;object-fit:cover;
  border:3px solid rgba(255,130,180,.5);
  box-shadow:
    0 0 0 8px rgba(255,77,141,.08),
    0 0 40px rgba(255,77,141,.5),
    0 0 80px rgba(185,79,204,.3),
    inset 0 0 30px rgba(255,255,255,.05);
  position:relative;z-index:2;
  animation:avatarFloat 4s ease-in-out infinite;
  transition:transform .4s,box-shadow .4s;
}
.avatar-img:hover{
  transform:scale(1.08) rotate(3deg);
  box-shadow:0 0 60px rgba(255,77,141,.8),0 0 100px rgba(185,79,204,.5);
}
@keyframes avatarFloat{
  0%,100%{transform:translateY(0);}
  50%{transform:translateY(-12px);}
}

/* ── Name ── */
.hero-name{
  font-family:'Playfair Display',serif;
  font-size:clamp(3rem,9vw,7rem);
  font-weight:900;font-style:italic;
  line-height:1;margin-bottom:5px;
  background:linear-gradient(135deg,#fff 0%,var(--pk2) 30%,var(--pp2) 60%,var(--gold) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;background-size:300%;
  animation:nameShimmer 4s ease-in-out infinite;
  filter:drop-shadow(0 0 30px rgba(255,130,180,.4));
  letter-spacing:-.02em;
}
@keyframes nameShimmer{
  0%,100%{background-position:0% 50%;}
  50%{background-position:100% 50%;}
}
.hero-subtitle{
  font-family:'Dancing Script',cursive;
  font-size:clamp(1.5rem,4vw,3rem);
  font-weight:600;
  background:linear-gradient(90deg,var(--pp2),var(--pk),var(--rd2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
  display:block;margin-bottom:15px;
  animation:subtitleWave 3s ease-in-out infinite;
}
@keyframes subtitleWave{
  0%,100%{letter-spacing:.05em;}
  50%{letter-spacing:.15em;}
}
.hero-tagline{
  font-family:'Cormorant Garamond',serif;
  font-size:clamp(.9rem,2.5vw,1.3rem);
  font-style:italic;font-weight:300;
  color:rgba(255,200,220,.8);
  margin-bottom:25px;
  max-width:500px;
  line-height:1.7;
}

/* ── Heart divider ── */
.heart-divider{
  display:flex;align-items:center;gap:12px;
  margin:20px 0;justify-content:center;
}
.heart-line{
  width:80px;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,130,180,.5),transparent);
}
.heart-center-icon{
  font-size:1.2rem;color:var(--pk);
  animation:heartBeat 1s ease-in-out infinite;
  text-shadow:0 0 15px var(--pk);
}
@keyframes heartBeat{
  0%,100%{transform:scale(1);}
  15%{transform:scale(1.3);}
  30%{transform:scale(1);}
  45%{transform:scale(1.15);}
}

/* ── Social row ── */
.social-row{
  display:flex;gap:12px;justify-content:center;
  flex-wrap:wrap;margin:20px 0;
}
.soc-btn{
  display:flex;align-items:center;justify-content:center;
  width:48px;height:48px;border-radius:16px;
  background:var(--glass2);
  border:1px solid var(--border);
  color:#fff;font-size:1.1rem;
  text-decoration:none;
  transition:all .3s cubic-bezier(.34,1.56,.64,1);
  backdrop-filter:blur(12px);
  position:relative;overflow:hidden;
}
.soc-btn::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,var(--pk),var(--pp));
  opacity:0;transition:opacity .3s;
}
.soc-btn i{position:relative;z-index:1;}
.soc-btn:hover{
  transform:translateY(-8px) scale(1.15) rotate(-5deg);
  border-color:var(--pk);
  box-shadow:0 15px 40px rgba(255,77,141,.5);
}
.soc-btn:hover::before{opacity:1;}

/* ══ INTRO OVERLAY ══ */
#intro{
  position:fixed;inset:0;z-index:8000;
  background:var(--dark3);
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  gap:20px;
  transition:opacity .8s ease,transform .8s ease;
}
#intro.hide{opacity:0;transform:scale(1.05);pointer-events:none;}
.intro-flowers{
  display:flex;gap:20px;font-size:2rem;
  animation:introFlowers 2s ease-in-out infinite;
}
@keyframes introFlowers{
  0%,100%{gap:20px;}
  50%{gap:30px;}
}
.intro-typing{
  font-family:'Dancing Script',cursive;
  font-size:clamp(1.3rem,4vw,2rem);
  color:#fff;min-height:2.5em;
  text-align:center;max-width:90vw;
  text-shadow:0 0 30px var(--pk),0 0 60px var(--pp);
  line-height:1.5;
}
.typing-cursor{
  display:inline-block;
  animation:blinkC .7s step-end infinite;
  color:var(--pk);
}
@keyframes blinkC{0%,100%{opacity:1;}50%{opacity:0;}}
.intro-skip{
  font-family:'Poppins',sans-serif;font-size:.75rem;
  color:rgba(255,130,180,.5);
  border:1px solid rgba(255,130,180,.2);
  padding:8px 20px;border-radius:20px;
  background:transparent;cursor:pointer;
  transition:all .3s;margin-top:10px;
  letter-spacing:.15em;
}
.intro-skip:hover{color:var(--pk);border-color:var(--pk);background:rgba(255,77,141,.1);}

/* ══ ENTER BUTTON (full page) ══ */
#enter-screen{
  position:fixed;inset:0;z-index:7000;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  gap:30px;
  background:radial-gradient(ellipse at center,rgba(255,77,141,.15),transparent 70%),var(--dark3);
  opacity:0;pointer-events:none;
  transition:opacity .6s ease;
}
#enter-screen.show{opacity:1;pointer-events:all;}

.enter-title{
  font-family:'Playfair Display',serif;
  font-size:clamp(1.5rem,5vw,3.5rem);
  font-weight:900;font-style:italic;
  background:linear-gradient(135deg,#fff,var(--pk2),var(--gold));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;text-align:center;
  animation:enterTitlePulse 2s ease-in-out infinite;
}
@keyframes enterTitlePulse{
  0%,100%{filter:drop-shadow(0 0 20px rgba(255,130,180,.4));}
  50%{filter:drop-shadow(0 0 50px rgba(255,130,180,.9)) drop-shadow(0 0 80px rgba(185,79,204,.6));}
}
.enter-sub{
  font-family:'Dancing Script',cursive;
  font-size:clamp(1rem,3vw,1.5rem);
  color:rgba(255,180,200,.7);letter-spacing:.1em;
}

.btn-enter{
  position:relative;overflow:hidden;
  padding:18px 70px;
  font-family:'Playfair Display',serif;
  font-size:clamp(1.1rem,3vw,1.6rem);
  font-style:italic;font-weight:700;
  color:#fff;border:none;cursor:pointer;
  border-radius:60px;
  background:linear-gradient(135deg,var(--pk),var(--pp),var(--rd));
  background-size:300%;
  animation:btnGrad 3s ease infinite,btnEntPulse 2s ease-in-out infinite;
  box-shadow:0 0 40px rgba(255,77,141,.5),0 20px 60px rgba(185,79,204,.3);
  letter-spacing:.05em;
  transition:transform .2s;
}
.btn-enter:hover{transform:scale(1.08);}
.btn-enter:active{transform:scale(.96);}
.btn-enter::before{
  content:'';position:absolute;
  top:-50%;left:-50%;width:200%;height:200%;
  background:conic-gradient(transparent 0deg,rgba(255,255,255,.15) 180deg,transparent 360deg);
  animation:btnSweep 2s linear infinite;
}
@keyframes btnGrad{0%,100%{background-position:0%;}50%{background-position:100%;}}
@keyframes btnEntPulse{
  0%,100%{box-shadow:0 0 40px rgba(255,77,141,.5),0 20px 60px rgba(185,79,204,.3);}
  50%{box-shadow:0 0 80px rgba(255,77,141,.9),0 30px 80px rgba(185,79,204,.6),0 0 120px rgba(232,48,90,.4);}
}
@keyframes btnSweep{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}

/* ── Enter floating hearts ── */
.enter-hearts{
  display:flex;gap:15px;font-size:1.5rem;
  animation:enterHeartsAnim 2s ease-in-out infinite;
}
@keyframes enterHeartsAnim{
  0%,100%{transform:scale(1);gap:15px;}
  50%{transform:scale(1.1);gap:25px;}
}

/* ══ BIO CARDS SECTION ══ */
.bio-section{padding:40px 20px 80px;max-width:1000px;margin:0 auto;}

.section-heading{
  text-align:center;margin-bottom:40px;
}
.section-heading h2{
  font-family:'Playfair Display',serif;
  font-size:clamp(1.5rem,4vw,2.5rem);
  font-style:italic;font-weight:700;
  background:linear-gradient(135deg,var(--pk2),var(--pp2),var(--gold2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;margin-bottom:8px;
}
.section-heading p{
  font-family:'Cormorant Garamond',serif;
  font-style:italic;font-size:1rem;
  color:rgba(255,180,210,.6);
}

.bio-grid{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(min(200px,100%),1fr));
  gap:clamp(12px,2vw,20px);
}

.bio-card{
  position:relative;overflow:hidden;
  background:var(--glass);
  border:1px solid var(--border);
  border-radius:24px;
  padding:clamp(18px,3vw,28px);
  cursor:pointer;
  backdrop-filter:blur(20px);
  transition:all .4s cubic-bezier(.34,1.56,.64,1);
  animation:cardIn .6s both;
  -webkit-tap-highlight-color:transparent;
}
.bio-card::before{
  content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(255,77,141,.12),rgba(185,79,204,.12));
  opacity:0;transition:opacity .3s;
}
.bio-card::after{
  content:'';position:absolute;
  top:-100%;left:-100%;width:300%;height:300%;
  background:conic-gradient(
    transparent 0deg,
    rgba(255,130,180,.08) 90deg,
    transparent 180deg
  );
  animation:cardRotate 6s linear infinite;
  opacity:0;transition:opacity .3s;
}
.bio-card:hover{
  transform:translateY(-12px) scale(1.03) rotate(.5deg);
  border-color:rgba(255,77,141,.6);
  box-shadow:
    0 30px 80px rgba(255,77,141,.25),
    0 0 0 1px rgba(255,77,141,.15),
    inset 0 1px 0 rgba(255,255,255,.1);
}
.bio-card:hover::before{opacity:1;}
.bio-card:hover::after{opacity:1;}
.bio-card:active{transform:scale(.97);}

@keyframes cardIn{
  from{opacity:0;transform:translateY(40px) scale(.9);}
  to{opacity:1;transform:translateY(0) scale(1);}
}
@keyframes cardRotate{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}

.card-top{display:flex;align-items:center;gap:10px;margin-bottom:14px;}
.card-icon-wrap{
  width:clamp(38px,5vw,48px);height:clamp(38px,5vw,48px);
  border-radius:14px;
  background:linear-gradient(135deg,rgba(255,77,141,.3),rgba(185,79,204,.3));
  border:1px solid rgba(255,130,180,.25);
  display:flex;align-items:center;justify-content:center;
  font-size:clamp(1rem,2vw,1.3rem);
  flex-shrink:0;
  transition:all .3s;
  box-shadow:0 4px 15px rgba(255,77,141,.2);
}
.bio-card:hover .card-icon-wrap{
  background:linear-gradient(135deg,var(--pk),var(--pp));
  transform:rotate(10deg) scale(1.1);
  box-shadow:0 8px 25px rgba(255,77,141,.5);
}
.card-label{
  font-family:'Montserrat',sans-serif;
  font-size:clamp(.55rem,1.2vw,.68rem);
  font-weight:700;letter-spacing:.2em;
  color:rgba(255,180,210,.5);
  text-transform:uppercase;
}
.card-value{
  font-family:'Poppins',sans-serif;
  font-size:clamp(.8rem,1.8vw,.95rem);
  font-weight:500;color:rgba(255,240,248,.9);
  line-height:1.5;
}
.card-play-hint{
  position:absolute;top:12px;right:14px;
  font-size:.65rem;color:rgba(255,130,180,.4);
  transition:all .3s;
  display:flex;align-items:center;gap:4px;
}
.bio-card:hover .card-play-hint{
  color:var(--pk);
  transform:scale(1.2);
  text-shadow:0 0 10px var(--pk);
}

/* quote card */
.card-quote{grid-column:1/-1;}
.card-quote .card-value{
  font-family:'Cormorant Garamond',serif;
  font-size:clamp(1rem,2.5vw,1.25rem);
  font-style:italic;font-weight:400;
  color:rgba(255,220,235,.9);
  text-align:center;line-height:1.8;
}

/* playing state */
.bio-card.playing{
  border-color:var(--pk);
  animation:cardPlaying 1.5s ease-in-out infinite;
}
@keyframes cardPlaying{
  0%,100%{box-shadow:0 0 30px rgba(255,77,141,.4),0 0 60px rgba(185,79,204,.2);}
  50%{box-shadow:0 0 60px rgba(255,77,141,.8),0 0 100px rgba(185,79,204,.5),0 0 140px rgba(232,48,90,.3);}
}

/* ══ MEDIA POPUP ══ */
#popup{
  position:fixed;inset:0;z-index:20000;
  display:none;align-items:center;justify-content:center;
  background:rgba(10,0,20,.85);backdrop-filter:blur(20px);
}
#popup.show{display:flex;}
.popup-box{
  background:linear-gradient(135deg,rgba(45,0,53,.95),rgba(26,0,32,.95));
  border:1px solid rgba(255,130,180,.3);
  border-radius:28px;
  padding:clamp(20px,4vw,35px);
  max-width:min(520px,92vw);width:100%;
  position:relative;
  box-shadow:0 0 100px rgba(255,77,141,.3),0 0 200px rgba(185,79,204,.2);
  animation:popupIn .4s cubic-bezier(.34,1.56,.64,1);
}
@keyframes popupIn{
  from{transform:scale(.3) rotate(-10deg);opacity:0;}
  to{transform:scale(1) rotate(0deg);opacity:1;}
}
.popup-close{
  position:absolute;top:16px;right:16px;
  background:rgba(255,255,255,.08);border:1px solid rgba(255,130,180,.2);
  border-radius:50%;width:36px;height:36px;
  color:rgba(255,130,180,.7);font-size:1.1rem;
  cursor:pointer;transition:all .3s;
  display:flex;align-items:center;justify-content:center;
  line-height:1;
}
.popup-close:hover{background:rgba(255,77,141,.2);color:#fff;transform:rotate(90deg) scale(1.1);}
.popup-title{
  font-family:'Dancing Script',cursive;
  font-size:1.4rem;color:var(--pk2);
  margin-bottom:20px;letter-spacing:.05em;
  text-shadow:0 0 20px rgba(255,130,180,.5);
}
.popup-media{width:100%;}
.popup-media audio{width:100%;outline:none;border-radius:12px;}
.popup-media video{width:100%;border-radius:16px;max-height:280px;object-fit:cover;}
.popup-media iframe{width:100%;height:250px;border-radius:16px;border:none;}
.no-media{
  text-align:center;padding:30px 20px;
  font-family:'Poppins',sans-serif;font-size:.9rem;
  color:rgba(255,150,190,.5);
}
.no-media .nm-icon{font-size:2.5rem;margin-bottom:12px;display:block;animation:heartBeat 1s ease-in-out infinite;}

/* ══ MUSIC WIDGET ══ */
#music-widget{
  position:fixed;bottom:20px;left:20px;z-index:500;
  background:rgba(45,0,53,.85);backdrop-filter:blur(20px);
  border:1px solid rgba(255,130,180,.25);
  border-radius:20px;padding:10px 18px;
  display:none;align-items:center;gap:12px;
  cursor:pointer;transition:all .3s;
  box-shadow:0 8px 30px rgba(255,77,141,.2);
}
#music-widget.show{display:flex;}
#music-widget:hover{border-color:rgba(255,77,141,.5);box-shadow:0 12px 40px rgba(255,77,141,.4);}
.mw-icon{
  font-size:1.1rem;color:var(--pk);
  animation:musicSpin 2s linear infinite;
}
.mw-icon.paused{animation-play-state:paused;}
@keyframes musicSpin{from{transform:rotate(0);}to{transform:rotate(360deg);}}
.mw-bars{display:flex;gap:3px;align-items:flex-end;height:18px;}
.mw-bar{
  width:3px;border-radius:2px;
  background:linear-gradient(to top,var(--pk),var(--pp2));
  animation:barDance .6s ease-in-out infinite alternate;
}
.mw-bar:nth-child(1){height:60%;animation-delay:0s;}
.mw-bar:nth-child(2){height:100%;animation-delay:.1s;}
.mw-bar:nth-child(3){height:40%;animation-delay:.2s;}
.mw-bar:nth-child(4){height:80%;animation-delay:.15s;}
.mw-bar:nth-child(5){height:50%;animation-delay:.05s;}
@keyframes barDance{from{transform:scaleY(1);}to{transform:scaleY(.3);}}
.mw-text{
  font-family:'Poppins',sans-serif;font-size:.7rem;
  color:rgba(255,180,210,.7);letter-spacing:.1em;
}

/* ══ DECORATIVE ROSE CORNERS ══ */
.rose-corner{
  position:fixed;font-size:clamp(1.5rem,3vw,2.5rem);
  pointer-events:none;z-index:3;
  filter:drop-shadow(0 0 15px rgba(255,77,141,.5));
  animation:roseFloat 4s ease-in-out infinite;
}
.rc-tl{top:15px;left:15px;animation-delay:0s;}
.rc-tr{top:15px;right:15px;animation-delay:1s;transform:scaleX(-1);}
.rc-bl{bottom:15px;left:15px;animation-delay:2s;transform:scaleY(-1);}
.rc-br{bottom:15px;right:15px;animation-delay:3s;transform:scale(-1);}
@keyframes roseFloat{
  0%,100%{transform:translateY(0) rotate(0deg);}
  50%{transform:translateY(-8px) rotate(5deg);}
}
.rc-tr{animation-name:roseFloatMirror;}
@keyframes roseFloatMirror{
  0%,100%{transform:scaleX(-1) translateY(0);}
  50%{transform:scaleX(-1) translateY(-8px);}
}

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-track{background:rgba(255,255,255,.03);}
::-webkit-scrollbar-thumb{background:linear-gradient(var(--pk),var(--pp));border-radius:2px;}

/* ══ RIPPLE ══ */
.ripple{
  position:fixed;border-radius:50%;pointer-events:none;z-index:99997;
  transform:translate(-50%,-50%) scale(0);
  animation:rippleAnim .6s ease-out forwards;
  border:2px solid rgba(255,130,180,.6);
}
@keyframes rippleAnim{
  to{transform:translate(-50%,-50%) scale(4);opacity:0;}
}

/* ══ RESPONSIVE ══ */
@media(max-width:480px){
  .bio-grid{grid-template-columns:1fr 1fr;}
  .card-quote{grid-column:1/-1;}
}
</style>
</head>
<body>

<!-- Custom Cursor -->
<div id="cursor"></div>
<div id="cursor-ring"></div>

<!-- Rose corners -->
<div class="rose-corner rc-tl">🌹</div>
<div class="rose-corner rc-tr">🌹</div>
<div class="rose-corner rc-bl">🌸</div>
<div class="rose-corner rc-br">🌸</div>

<!-- Background -->
{% if bg_video %}
<div id="bg-video-wrap">
  <video id="bg-video" autoplay muted loop playsinline>
    <source src="{{ bg_video }}">
  </video>
  <div class="bg-overlay"></div>
</div>
{% else %}
<div class="bg-fallback"></div>
{% endif %}

<!-- Particles -->
<div id="particles"></div>

<!-- ══ LOADER ══ -->
<div id="loader">
  <div class="loader-petals">
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-petal"></div>
    <div class="loader-center"></div>
  </div>
  <div class="loader-text" id="loader-text">🌸 Loading her world...</div>
  <div class="loader-bar-wrap"><div class="loader-bar" id="loader-bar"></div></div>
</div>

<!-- ══ INTRO TYPING ══ -->
<div id="intro">
  <div class="intro-flowers">🌸 💕 🌹 💕 🌸</div>
  <div class="intro-typing" id="intro-typing"><span class="typing-cursor">|</span></div>
  <button class="intro-skip" onclick="skipIntro()">skip ✨</button>
</div>

<!-- ══ ENTER SCREEN ══ -->
<div id="enter-screen">
  <div class="enter-hearts">💗 🌸 💕 🌸 💗</div>
  <div class="enter-title">Welcome to her Universe</div>
  <div class="enter-sub">~ where pink meets purple & chaos ~</div>
  <button class="btn-enter" onclick="doEnter()">
    ✨ Enter Her World ✨
  </button>
  <div style="font-family:'Dancing Script',cursive;color:rgba(255,180,210,.4);font-size:.85rem;">
    🌹 {{ p.name }} {{ p.subtitle }} 🌹
  </div>
</div>

<!-- ══ MAIN SITE ══ -->
<div id="site">

  <!-- HERO -->
  <section class="hero">
    <span class="crown">👑</span>

    <div class="avatar-stack">
      <div class="avatar-glow-ring agr3"></div>
      <div class="avatar-glow-ring agr2"></div>
      <div class="avatar-glow-ring agr1"></div>
      <img src="{{ p.avatar }}" alt="{{ p.name }}" class="avatar-img"
           onerror="this.src='https://via.placeholder.com/175/ff85b3/ffffff?text=♡'">
    </div>

    <div class="hero-name">{{ p.name }}</div>
    <div class="hero-subtitle">{{ p.subtitle }}</div>

    <div class="hero-tagline">{{ p.tagline }}</div>

    <div class="heart-divider">
      <div class="heart-line"></div>
      <div class="heart-center-icon">♡</div>
      <div class="heart-line"></div>
    </div>

    <div class="social-row">
      {% if socials.instagram %}<a href="{{ socials.instagram }}" target="_blank" class="soc-btn" title="Instagram"><i class="fab fa-instagram"></i></a>{% endif %}
      {% if socials.twitter %}<a href="{{ socials.twitter }}" target="_blank" class="soc-btn" title="Twitter"><i class="fab fa-twitter"></i></a>{% endif %}
      {% if socials.tiktok %}<a href="{{ socials.tiktok }}" target="_blank" class="soc-btn" title="TikTok"><i class="fab fa-tiktok"></i></a>{% endif %}
      {% if socials.youtube %}<a href="{{ socials.youtube }}" target="_blank" class="soc-btn" title="YouTube"><i class="fab fa-youtube"></i></a>{% endif %}
      {% if socials.snapchat %}<a href="{{ socials.snapchat }}" target="_blank" class="soc-btn" title="Snapchat"><i class="fab fa-snapchat"></i></a>{% endif %}
    </div>

    <p style="font-family:'Cormorant Garamond',serif;font-style:italic;font-size:clamp(.85rem,2vw,1.05rem);color:rgba(255,200,220,.65);max-width:460px;line-height:1.8;margin-top:10px;">{{ p.bio }}</p>
  </section>

  <!-- BIO CARDS -->
  <div class="bio-section">
    <div class="section-heading">
      <h2>✨ Know Her Better ✨</h2>
      <p>tap a card to unveil a little secret 🌸</p>
    </div>
    <div class="bio-grid">

      <div class="bio-card" onclick="cardClick('age',this,event)" style="animation-delay:.05s">
        <div class="card-top">
          <div class="card-icon-wrap">✨</div>
          <div class="card-label">Age</div>
        </div>
        <div class="card-value">{{ p.age }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('birthday',this,event)" style="animation-delay:.1s">
        <div class="card-top">
          <div class="card-icon-wrap">🎂</div>
          <div class="card-label">Birthday</div>
        </div>
        <div class="card-value">{{ p.birthday }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('location',this,event)" style="animation-delay:.15s">
        <div class="card-top">
          <div class="card-icon-wrap">🌍</div>
          <div class="card-label">Location</div>
        </div>
        <div class="card-value">{{ p.location }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('zodiac',this,event)" style="animation-delay:.2s">
        <div class="card-top">
          <div class="card-icon-wrap">🌙</div>
          <div class="card-label">Zodiac</div>
        </div>
        <div class="card-value">{{ p.zodiac }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('hobbies',this,event)" style="animation-delay:.25s">
        <div class="card-top">
          <div class="card-icon-wrap">🎨</div>
          <div class="card-label">Hobbies</div>
        </div>
        <div class="card-value">{{ p.hobbies }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('music',this,event)" style="animation-delay:.3s">
        <div class="card-top">
          <div class="card-icon-wrap">🎵</div>
          <div class="card-label">Music</div>
        </div>
        <div class="card-value">{{ p.music }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('vibe',this,event)" style="animation-delay:.35s">
        <div class="card-top">
          <div class="card-icon-wrap">🌙</div>
          <div class="card-label">My Vibe</div>
        </div>
        <div class="card-value">{{ p.vibe }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card" onclick="cardClick('bestie',this,event)" style="animation-delay:.4s">
        <div class="card-top">
          <div class="card-icon-wrap">💗</div>
          <div class="card-label">Bestie</div>
        </div>
        <div class="card-value">{{ p.bestie }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

      <div class="bio-card card-quote" onclick="cardClick('quote',this,event)" style="animation-delay:.45s">
        <div class="card-top" style="justify-content:center;">
          <div class="card-icon-wrap">🦋</div>
          <div class="card-label">Her Quote</div>
        </div>
        <div class="card-value">{{ p.quote }}</div>
        <div class="card-play-hint"><i class="fas fa-play"></i> tap</div>
      </div>

    </div>
  </div>

  <!-- Footer -->
  <div style="text-align:center;padding:20px 20px 60px;font-family:'Dancing Script',cursive;color:rgba(255,130,180,.3);font-size:1rem;">
    made with 💗 & a little bit of magic
  </div>
</div>

<!-- ══ MEDIA POPUP ══ -->
<div id="popup">
  <div class="popup-box">
    <button class="popup-close" onclick="closePopup()">✕</button>
    <div class="popup-title" id="popup-title">💕 Playing...</div>
    <div class="popup-media" id="popup-media"></div>
  </div>
</div>

<!-- Music Widget -->
<div id="music-widget" onclick="toggleMusic()">
  <i class="fas fa-compact-disc mw-icon" id="mw-icon"></i>
  <div class="mw-bars" id="mw-bars">
    <div class="mw-bar"></div>
    <div class="mw-bar"></div>
    <div class="mw-bar"></div>
    <div class="mw-bar"></div>
    <div class="mw-bar"></div>
  </div>
  <div class="mw-text" id="mw-text">MUSIC</div>
</div>

<audio id="bg-audio" loop>
  {% if bg_music %}<source src="{{ bg_music }}">{% endif %}
</audio>

<script>
// ════════════════════════════════
// DATA
// ════════════════════════════════
const MEDIA = {{ media_map | tojson }};
const INTRO_LINES = {{ intro_lines | tojson }};
const HAS_MUSIC = {{ 'true' if bg_music else 'false' }};
const CARD_LABELS = {
  age:'✨ Age Reveal',birthday:'🎂 Birthday Surprise',
  location:'📍 Her Location',zodiac:'🌙 Zodiac Energy',
  hobbies:'🎨 Her Hobbies',music:'🎵 Music Taste',
  vibe:'🌸 Her Vibe',bestie:'💗 Bestie Love',quote:'🦋 Her Quote'
};

// ════════════════════════════════
// CURSOR
// ════════════════════════════════
const cur = document.getElementById('cursor');
const curR = document.getElementById('cursor-ring');
let mx=0,my=0,rx=0,ry=0;
document.addEventListener('mousemove',e=>{
  mx=e.clientX;my=e.clientY;
  cur.style.left=mx+'px';cur.style.top=my+'px';
  // Trail
  if(document.getElementById('site').classList.contains('show') && Math.random()>.7){
    const t=document.createElement('div');
    t.className='trail';
    const emj=['✨','💕','🌸','⭐','♡'];
    t.textContent=emj[Math.floor(Math.random()*emj.length)];
    t.style.cssText=`left:${mx}px;top:${my}px;font-size:${.6+Math.random()*.6}rem;animation-duration:${.5+Math.random()*.4}s;`;
    document.body.appendChild(t);
    setTimeout(()=>t.remove(),900);
  }
});
setInterval(()=>{
  rx+=(mx-rx)*.1;ry+=(my-ry)*.1;
  curR.style.left=rx+'px';curR.style.top=ry+'px';
},16);

// Click ripple
document.addEventListener('click',e=>{
  const r=document.createElement('div');
  r.className='ripple';
  r.style.cssText=`left:${e.clientX}px;top:${e.clientY}px;width:60px;height:60px;`;
  document.body.appendChild(r);
  setTimeout(()=>r.remove(),700);
});

// ════════════════════════════════
// PARTICLES
// ════════════════════════════════
const EMOJIS=['🌸','💕','✨','🌹','💗','⭐','🦋','💜','🌙','💖','🌺','✿','♡','💫','🎀'];
function makeParticle(){
  const p=document.createElement('div');
  p.className='fp';
  p.textContent=EMOJIS[Math.floor(Math.random()*EMOJIS.length)];
  const size=.5+Math.random()*1.2;
  const dur=8+Math.random()*15;
  p.style.cssText=`
    left:${Math.random()*100}vw;
    font-size:${size}rem;
    animation-duration:${dur}s;
    animation-delay:${Math.random()*dur}s;
    filter:drop-shadow(0 0 6px rgba(255,130,180,.6));
  `;
  document.getElementById('particles').appendChild(p);
  setTimeout(()=>p.remove(),(dur+5)*1000);
}
for(let i=0;i<30;i++) setTimeout(makeParticle,i*200);
setInterval(makeParticle,1200);

// ════════════════════════════════
// LOADER
// ════════════════════════════════
const loaderMsgs=['🌸 Loading her world...','💕 Sprinkling love...','✨ Waking up magic...','🌹 Almost ready...','💗 Here she comes!'];
let lp=0;
const lb=document.getElementById('loader-bar');
const lt=document.getElementById('loader-text');
let lw=0;
const lInt=setInterval(()=>{
  lw+=Math.random()*3+1.5;
  if(lw>100)lw=100;
  lb.style.width=lw+'%';
  const mi=Math.floor((lw/100)*loaderMsgs.length);
  lt.textContent=loaderMsgs[Math.min(mi,loaderMsgs.length-1)];
  if(lw>=100){
    clearInterval(lInt);
    setTimeout(()=>{
      document.getElementById('loader').style.transition='opacity .6s';
      document.getElementById('loader').style.opacity='0';
      setTimeout(startIntro,700);
    },400);
  }
},80);

// ════════════════════════════════
// INTRO TYPING
// ════════════════════════════════
let introSkipped=false;
function startIntro(){
  document.getElementById('loader').style.display='none';
  const intro=document.getElementById('intro');
  intro.style.display='flex';
  typeIntroLines(0);
}

async function typeIntroLines(idx){
  if(introSkipped)return;
  if(idx>=INTRO_LINES.length){
    await sleep(500);
    if(!introSkipped) showEnterScreen();
    return;
  }
  const el=document.getElementById('intro-typing');
  const line=INTRO_LINES[idx];
  el.innerHTML='<span class="typing-cursor">|</span>';
  let i=0;
  await new Promise(res=>{
    const t=setInterval(()=>{
      if(introSkipped){clearInterval(t);res();return;}
      el.innerHTML=line.slice(0,++i)+'<span class="typing-cursor">|</span>';
      if(i>=line.length){clearInterval(t);setTimeout(res,700);}
    },45);
  });
  await sleep(300);
  typeIntroLines(idx+1);
}

function skipIntro(){
  introSkipped=true;
  document.getElementById('intro').classList.add('hide');
  setTimeout(showEnterScreen,500);
}

function showEnterScreen(){
  document.getElementById('intro').classList.add('hide');
  setTimeout(()=>{
    document.getElementById('intro').style.display='none';
    document.getElementById('enter-screen').classList.add('show');
  },400);
}

// ════════════════════════════════
// ENTER
// ════════════════════════════════
function doEnter(){
  // Start music
  if(HAS_MUSIC){
    const a=document.getElementById('bg-audio');
    a.volume=.4;
    a.play().catch(()=>{});
    isMusicOn=true;
    document.getElementById('music-widget').classList.add('show');
  }
  // Animate enter screen out
  const es=document.getElementById('enter-screen');
  es.style.transition='opacity .8s ease,transform .8s ease';
  es.style.opacity='0';
  es.style.transform='scale(1.1)';
  setTimeout(()=>{
    es.style.display='none';
    revealSite();
  },800);
}

function revealSite(){
  const site=document.getElementById('site');
  site.classList.add('show');
}

// ════════════════════════════════
// BIO CARDS
// ════════════════════════════════
let activeCard=null,activeAudio=null;

function cardClick(cat,el,ev){
  // Sparkle burst at click
  burst(ev.clientX,ev.clientY);

  if(activeCard && activeCard!==el) activeCard.classList.remove('playing');

  const url=MEDIA[cat]||'';
  showPopup(cat,url,el);
}

function showPopup(cat,url,cardEl){
  const pop=document.getElementById('popup');
  const title=document.getElementById('popup-title');
  const media=document.getElementById('popup-media');

  title.textContent=CARD_LABELS[cat]||('💕 '+cat);

  if(activeAudio){activeAudio.pause();activeAudio=null;}

  if(!url){
    media.innerHTML=`
      <div class="no-media">
        <span class="nm-icon">🌸</span>
        No media assigned yet~<br>
        <small style="opacity:.5">Add one in the admin panel 💕</small>
      </div>`;
  } else if(url.includes('youtube.com')||url.includes('youtu.be')){
    const vid=ytId(url);
    media.innerHTML=`<iframe src="https://www.youtube.com/embed/${vid}?autoplay=1&rel=0" allow="autoplay;encrypted-media" allowfullscreen></iframe>`;
  } else if(/\.(mp4|webm|mov)(\?|$)/i.test(url)){
    media.innerHTML=`<video controls autoplay><source src="${url}"></video>`;
  } else {
    media.innerHTML=`
      <div style="text-align:center;padding:20px 0;">
        <div style="font-size:2.5rem;margin-bottom:14px;animation:heartBeat 1s ease-in-out infinite;">🎵</div>
        <audio controls autoplay id="popAudio"><source src="${url}"></audio>
      </div>`;
    setTimeout(()=>{const a=document.getElementById('popAudio');if(a)activeAudio=a;},100);
  }

  pop.classList.add('show');
  if(cardEl){
    if(activeCard) activeCard.classList.remove('playing');
    activeCard=cardEl;
    cardEl.classList.add('playing');
  }
}

function closePopup(){
  document.getElementById('popup').classList.remove('show');
  if(activeAudio){activeAudio.pause();activeAudio=null;}
  if(activeCard){activeCard.classList.remove('playing');activeCard=null;}
}
document.getElementById('popup').addEventListener('click',function(e){
  if(e.target===this) closePopup();
});

function ytId(url){
  const m=url.match(/(?:v=|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  return m?m[1]:'';
}

// ════════════════════════════════
// SPARKLE BURST
// ════════════════════════════════
const B_EMOJIS=['✨','💕','🌸','⭐','💗','🦋','♡'];
function burst(x,y){
  for(let i=0;i<12;i++){
    const s=document.createElement('div');
    const angle=Math.random()*360;
    const dist=40+Math.random()*80;
    const rad=angle*Math.PI/180;
    const tx=Math.cos(rad)*dist;
    const ty=Math.sin(rad)*dist;
    s.textContent=B_EMOJIS[Math.floor(Math.random()*B_EMOJIS.length)];
    s.style.cssText=`
      position:fixed;left:${x}px;top:${y}px;
      pointer-events:none;z-index:99999;
      font-size:${.7+Math.random()*.8}rem;
      transform:translate(-50%,-50%);
      animation:burstAnim .8s ease forwards;
      --tx:${tx}px;--ty:${ty}px;
    `;
    document.body.appendChild(s);
    setTimeout(()=>s.remove(),900);
  }
}

// Inject burst keyframes
const bStyle=document.createElement('style');
bStyle.textContent=`
@keyframes burstAnim{
  0%{opacity:1;transform:translate(-50%,-50%) scale(0);}
  40%{opacity:1;transform:translate(calc(-50% + var(--tx)*.4),calc(-50% + var(--ty)*.4)) scale(1.2);}
  100%{opacity:0;transform:translate(calc(-50% + var(--tx)),calc(-50% + var(--ty))) scale(0);}
}`;
document.head.appendChild(bStyle);

// ════════════════════════════════
// MUSIC WIDGET
// ════════════════════════════════
let isMusicOn=false;
function toggleMusic(){
  const a=document.getElementById('bg-audio');
  const icon=document.getElementById('mw-icon');
  const bars=document.getElementById('mw-bars');
  const txt=document.getElementById('mw-text');
  if(isMusicOn){
    a.pause();isMusicOn=false;
    icon.classList.add('paused');
    bars.style.opacity='.3';
    txt.textContent='PAUSED';
  } else {
    a.play().catch(()=>{});isMusicOn=true;
    icon.classList.remove('paused');
    bars.style.opacity='1';
    txt.textContent='MUSIC';
  }
}

// Keyboard
document.addEventListener('keydown',e=>{
  if(e.key==='Escape') closePopup();
  if(e.key.toLowerCase()==='m' && document.getElementById('site').classList.contains('show')) toggleMusic();
});

function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
</script>
</body>
</html>
"""

# ══════════════════════════════════════════════
#  ADMIN LOGIN
# ══════════════════════════════════════════════
ADMIN_LOGIN = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Login 🌸</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@1,700&family=Dancing+Script:wght@600&family=Poppins:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{
  min-height:100vh;
  background:radial-gradient(ellipse at 20% 30%,rgba(185,79,204,.3),transparent 50%),
             radial-gradient(ellipse at 80% 70%,rgba(255,77,141,.25),transparent 50%),
             linear-gradient(135deg,#0d0015,#1a0020,#0d0015);
  display:flex;align-items:center;justify-content:center;
  font-family:'Poppins',sans-serif;
  min-height:100vh;
}
.card{
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,130,180,.25);
  border-radius:28px;padding:50px 40px;
  width:min(400px,90vw);
  backdrop-filter:blur(20px);
  box-shadow:0 0 80px rgba(255,77,141,.15),0 0 150px rgba(185,79,204,.1);
  text-align:center;
}
.card-icon{font-size:3rem;margin-bottom:15px;display:block;animation:iconFloat 3s ease-in-out infinite;}
@keyframes iconFloat{0%,100%{transform:translateY(0);}50%{transform:translateY(-10px);}}
h1{
  font-family:'Playfair Display',serif;font-style:italic;
  font-size:1.8rem;font-weight:700;margin-bottom:6px;
  background:linear-gradient(135deg,#ff85b3,#d17fe8,#ffd700);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.sub{
  font-family:'Dancing Script',cursive;font-size:1rem;
  color:rgba(255,150,190,.5);margin-bottom:35px;
}
.inp-wrap{position:relative;margin-bottom:20px;}
.inp-wrap i{
  position:absolute;left:16px;top:50%;transform:translateY(-50%);
  color:rgba(255,130,180,.5);font-size:.85rem;
}
input[type=password]{
  width:100%;padding:14px 16px 14px 44px;
  background:rgba(255,255,255,.06);
  border:1px solid rgba(255,130,180,.2);border-radius:14px;
  color:#fff;font-family:'Poppins',sans-serif;font-size:.9rem;outline:none;
  transition:all .3s;
}
input[type=password]:focus{border-color:rgba(255,77,141,.6);background:rgba(255,255,255,.09);box-shadow:0 0 0 3px rgba(255,77,141,.1);}
input::placeholder{color:rgba(255,150,190,.3);}
.btn{
  width:100%;padding:14px;border:none;border-radius:14px;
  background:linear-gradient(135deg,#ff4d8d,#b94fcc,#e8305a);
  background-size:300%;animation:btnG 3s ease infinite;
  color:#fff;font-family:'Poppins',sans-serif;font-size:.95rem;font-weight:600;
  cursor:pointer;letter-spacing:.05em;
  transition:transform .2s,box-shadow .2s;
  box-shadow:0 8px 30px rgba(255,77,141,.35);
}
.btn:hover{transform:translateY(-3px);box-shadow:0 15px 40px rgba(255,77,141,.55);}
@keyframes btnG{0%,100%{background-position:0%;}50%{background-position:100%;}}
.err{
  background:rgba(255,50,80,.1);border:1px solid rgba(255,50,80,.25);
  border-radius:10px;padding:12px 16px;color:#ff7090;
  font-size:.82rem;margin-bottom:18px;
  display:flex;align-items:center;gap:8px;
}
.back{
  display:block;margin-top:20px;
  color:rgba(255,130,180,.4);font-size:.78rem;text-decoration:none;
  transition:color .3s;letter-spacing:.1em;
}
.back:hover{color:rgba(255,77,141,.8);}
</style>
</head>
<body>
<div class="card">
  <span class="card-icon">🌸</span>
  <h1>Admin Access</h1>
  <div class="sub">~ her secret garden ~</div>
  {% if error %}<div class="err"><i class="fas fa-times-circle"></i> {{ error }}</div>{% endif %}
  <form method="POST" action="/admin/login">
    <div class="inp-wrap">
      <i class="fas fa-lock"></i>
      <input type="password" name="password" placeholder="Enter the secret password..." autofocus required>
    </div>
    <button type="submit" class="btn">✨ Enter Admin Panel</button>
  </form>
  <a href="/" class="back">← return to her world</a>
</div>
</body>
</html>"""

# ══════════════════════════════════════════════
#  ADMIN DASHBOARD
# ══════════════════════════════════════════════
ADMIN_DASH = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Admin Dashboard 🌸</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@1,700&family=Dancing+Script:wght@600&family=Poppins:wght@300;400;500;600&family=Montserrat:wght@300;400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
:root{--pk:#ff4d8d;--pp:#b94fcc;--rd:#e8305a;--dark:#0d0015;--glass:rgba(255,255,255,.05);--border:rgba(255,130,180,.2);}
*{margin:0;padding:0;box-sizing:border-box;}
body{
  min-height:100vh;background:var(--dark);color:#fff;
  font-family:'Poppins',sans-serif;
  background-image:radial-gradient(ellipse at 10% 10%,rgba(185,79,204,.12),transparent 50%),
                   radial-gradient(ellipse at 90% 90%,rgba(255,77,141,.1),transparent 50%);
}
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-thumb{background:linear-gradient(var(--pk),var(--pp));border-radius:2px;}

/* Topbar */
.top{
  position:sticky;top:0;z-index:100;
  background:rgba(13,0,21,.9);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);
  padding:14px 28px;display:flex;align-items:center;justify-content:space-between;
  gap:12px;flex-wrap:wrap;
}
.top-brand{
  font-family:'Dancing Script',cursive;font-size:1.4rem;
  background:linear-gradient(135deg,#ff85b3,#d17fe8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
}
.top-btns{display:flex;gap:10px;flex-wrap:wrap;}
.tbtn{
  padding:8px 18px;border-radius:10px;font-size:.72rem;
  font-family:'Montserrat',sans-serif;letter-spacing:.1em;font-weight:600;
  cursor:pointer;border:none;text-decoration:none;
  display:inline-flex;align-items:center;gap:6px;transition:all .3s;
}
.tbtn-view{background:rgba(255,255,255,.08);border:1px solid var(--border);color:rgba(255,180,210,.7);}
.tbtn-view:hover{background:rgba(255,130,180,.15);border-color:rgba(255,77,141,.4);}
.tbtn-out{background:rgba(255,50,80,.1);border:1px solid rgba(255,50,80,.2);color:#ff7090;}
.tbtn-out:hover{background:rgba(255,50,80,.2);}

/* Alert */
.alert{
  margin:20px;padding:14px 20px;border-radius:12px;
  display:flex;align-items:center;gap:10px;font-size:.85rem;
}
.alert-ok{background:rgba(100,220,120,.08);border:1px solid rgba(100,220,120,.2);color:#7ddc9f;}
.alert-err{background:rgba(255,80,80,.08);border:1px solid rgba(255,80,80,.2);color:#ff8090;}

/* Main */
.main{padding:30px;max-width:1100px;margin:0 auto;}

/* Stats */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin-bottom:32px;}
.stat{
  background:var(--glass);border:1px solid var(--border);border-radius:16px;
  padding:18px;text-align:center;
}
.stat-v{
  font-family:'Playfair Display',serif;font-style:italic;
  font-size:1.6rem;font-weight:700;
  background:linear-gradient(135deg,#ff85b3,#d17fe8);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
  margin-bottom:4px;
}
.stat-l{font-size:.62rem;color:rgba(255,150,190,.4);letter-spacing:.15em;text-transform:uppercase;font-family:'Montserrat',sans-serif;font-weight:600;}

/* Sections */
.sec{margin-bottom:32px;}
.sec-hd{
  display:flex;align-items:center;gap:10px;
  margin-bottom:18px;padding-bottom:12px;
  border-bottom:1px solid rgba(255,130,180,.1);
}
.sec-hd-icon{color:var(--pk);font-size:.95rem;}
.sec-hd-title{font-family:'Montserrat',sans-serif;font-size:.78rem;font-weight:600;letter-spacing:.2em;color:rgba(255,150,190,.7);}

.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(260px,100%),1fr));gap:16px;}
.fg{display:flex;flex-direction:column;gap:5px;}
.fg.full{grid-column:1/-1;}
.fl{font-family:'Montserrat',sans-serif;font-size:.62rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,150,190,.45);}
.fi,.fta{
  background:rgba(255,255,255,.04);border:1px solid rgba(255,130,180,.15);
  border-radius:10px;padding:11px 14px;color:#fff;
  font-family:'Poppins',sans-serif;font-size:.85rem;outline:none;width:100%;
  transition:all .3s;
}
.fi:focus,.fta:focus{border-color:rgba(255,77,141,.5);background:rgba(255,255,255,.07);box-shadow:0 0 0 3px rgba(255,77,141,.08);}
.fi::placeholder,.fta::placeholder{color:rgba(255,150,190,.2);}
.fta{resize:vertical;min-height:70px;}

/* Media cards */
.mgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr));gap:14px;}
.mc{
  background:rgba(255,255,255,.04);border:1px solid rgba(255,130,180,.12);
  border-radius:14px;padding:16px;transition:border-color .3s;
}
.mc:hover{border-color:rgba(255,130,180,.3);}
.mc-hd{display:flex;align-items:center;gap:10px;margin-bottom:12px;}
.mc-icon{
  width:32px;height:32px;border-radius:9px;
  background:linear-gradient(135deg,rgba(255,77,141,.2),rgba(185,79,204,.2));
  display:flex;align-items:center;justify-content:center;font-size:.85rem;
}
.mc-title{font-family:'Montserrat',sans-serif;font-size:.62rem;font-weight:600;letter-spacing:.15em;color:rgba(255,150,190,.5);}
.mc-hint{font-size:.6rem;color:rgba(255,255,255,.18);margin-top:4px;font-family:'Poppins',sans-serif;}

/* Submit */
.fsub{margin-top:24px;display:flex;justify-content:flex-end;}
.btn-save{
  padding:14px 45px;border:none;border-radius:12px;
  background:linear-gradient(135deg,var(--pk),var(--pp),var(--rd));
  background-size:300%;animation:bsG 3s ease infinite;
  color:#fff;font-family:'Poppins',sans-serif;font-size:.88rem;font-weight:600;
  cursor:pointer;letter-spacing:.08em;
  box-shadow:0 8px 30px rgba(255,77,141,.35);transition:transform .2s,box-shadow .2s;
  display:flex;align-items:center;gap:8px;
}
.btn-save:hover{transform:translateY(-3px);box-shadow:0 15px 40px rgba(255,77,141,.55);}
@keyframes bsG{0%,100%{background-position:0%;}50%{background-position:100%;}}

.pw-box{
  background:rgba(255,50,80,.04);border:1px solid rgba(255,50,80,.12);
  border-radius:16px;padding:24px;
}
.btn-pw{
  padding:11px 28px;border:none;border-radius:10px;
  background:rgba(255,50,80,.15);border:1px solid rgba(255,50,80,.25);
  color:#ff7090;font-family:'Poppins',sans-serif;font-size:.78rem;font-weight:600;
  cursor:pointer;transition:all .3s;display:flex;align-items:center;gap:6px;
}
.btn-pw:hover{background:rgba(255,50,80,.25);}
</style>
</head>
<body>

<div class="top">
  <div class="top-brand">🌸 Admin Panel</div>
  <div class="top-btns">
    <a href="/" target="_blank" class="tbtn tbtn-view"><i class="fas fa-eye"></i> View Site</a>
    <a href="/admin/logout" class="tbtn tbtn-out"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</div>

{% if msg %}
<div class="alert {{ 'alert-ok' if ok else 'alert-err' }}">
  <i class="fas fa-{{ 'check-circle' if ok else 'exclamation-circle' }}"></i> {{ msg }}
</div>
{% endif %}

<div class="main">

  <!-- Stats -->
  <div class="stats">
    <div class="stat">
      <div class="stat-v">{{ db.profile.name }}</div>
      <div class="stat-l">Name</div>
    </div>
    <div class="stat">
      <div class="stat-v">{{ db.media_map.values()|list|select|list|length }}</div>
      <div class="stat-l">Media Mapped</div>
    </div>
    <div class="stat">
      <div class="stat-v">{{ db.socials.values()|list|select|list|length }}</div>
      <div class="stat-l">Socials</div>
    </div>
    <div class="stat">
      <div class="stat-v">{{ db.intro_lines|length }}</div>
      <div class="stat-l">Intro Lines</div>
    </div>
  </div>

  <form method="POST" action="/admin/save">

    <!-- Profile -->
    <div class="sec">
      <div class="sec-hd"><i class="fas fa-user sec-hd-icon"></i><div class="sec-hd-title">Profile Info</div></div>
      <div class="fgrid">
        <div class="fg"><div class="fl">Main Name</div><input class="fi" type="text" name="name" value="{{ db.profile.name }}" required></div>
        <div class="fg"><div class="fl">Subtitle (& QNR)</div><input class="fi" type="text" name="subtitle" value="{{ db.profile.subtitle }}"></div>
        <div class="fg"><div class="fl">Tagline</div><input class="fi" type="text" name="tagline" value="{{ db.profile.tagline }}"></div>
        <div class="fg"><div class="fl">Avatar URL</div><input class="fi" type="url" name="avatar" value="{{ db.profile.avatar }}" placeholder="https://..."></div>
        <div class="fg full"><div class="fl">Bio</div><textarea class="fta" name="bio">{{ db.profile.bio }}</textarea></div>
      </div>
    </div>

    <!-- Bio Cards -->
    <div class="sec">
      <div class="sec-hd"><i class="fas fa-id-card sec-hd-icon"></i><div class="sec-hd-title">Bio Card Values</div></div>
      <div class="fgrid">
        <div class="fg"><div class="fl">✨ Age</div><input class="fi" type="text" name="age" value="{{ db.profile.age }}"></div>
        <div class="fg"><div class="fl">🎂 Birthday</div><input class="fi" type="text" name="birthday" value="{{ db.profile.birthday }}"></div>
        <div class="fg"><div class="fl">🌍 Location</div><input class="fi" type="text" name="location" value="{{ db.profile.location }}"></div>
        <div class="fg"><div class="fl">🌙 Zodiac</div><input class="fi" type="text" name="zodiac" value="{{ db.profile.zodiac }}"></div>
        <div class="fg"><div class="fl">🎨 Hobbies</div><input class="fi" type="text" name="hobbies" value="{{ db.profile.hobbies }}"></div>
        <div class="fg"><div class="fl">🎵 Music</div><input class="fi" type="text" name="music" value="{{ db.profile.music }}"></div>
        <div class="fg"><div class="fl">🌸 Vibe</div><input class="fi" type="text" name="vibe" value="{{ db.profile.vibe }}"></div>
        <div class="fg"><div class="fl">💗 Bestie</div><input class="fi" type="text" name="bestie" value="{{ db.profile.bestie }}"></div>
        <div class="fg full"><div class="fl">🦋 Quote</div><input class="fi" type="text" name="quote" value="{{ db.profile.quote }}"></div>
      </div>
    </div>

    <!-- Socials -->
    <div class="sec">
      <div class="sec-hd"><i class="fas fa-share-alt sec-hd-icon"></i><div class="sec-hd-title">Social Links</div></div>
      <div class="fgrid">
        <div class="fg"><div class="fl"><i class="fab fa-instagram"></i> Instagram</div><input class="fi" type="url" name="instagram" value="{{ db.socials.instagram }}" placeholder="https://..."></div>
        <div class="fg"><div class="fl"><i class="fab fa-twitter"></i> Twitter</div><input class="fi" type="url" name="twitter" value="{{ db.socials.twitter }}" placeholder="https://..."></div>
        <div class="fg"><div class="fl"><i class="fab fa-tiktok"></i> TikTok</div><input class="fi" type="url" name="tiktok" value="{{ db.socials.tiktok }}" placeholder="https://..."></div>
        <div class="fg"><div class="fl"><i class="fab fa-youtube"></i> YouTube</div><input class="fi" type="url" name="youtube" value="{{ db.socials.youtube }}" placeholder="https://..."></div>
        <div class="fg"><div class="fl"><i class="fab fa-snapchat"></i> Snapchat</div><input class="fi" type="url" name="snapchat" value="{{ db.socials.snapchat }}" placeholder="https://..."></div>
      </div>
    </div>

    <!-- Media -->
    <div class="sec">
      <div class="sec-hd"><i class="fas fa-film sec-hd-icon"></i><div class="sec-hd-title">Background Video & Music</div></div>
      <div class="fgrid">
        <div class="fg full"><div class="fl">🎬 Background Video URL (MP4 / direct link — plays behind everything)</div><input class="fi" type="url" name="background_video" value="{{ db.background_video }}" placeholder="https://...mp4"></div>
        <div class="fg full"><div class="fl">🎵 Background Music URL (MP3)</div><input class="fi" type="url" name="background_music" value="{{ db.background_music }}" placeholder="https://...mp3"></div>
      </div>
    </div>

    <!-- Intro Lines -->
    <div class="sec">
      <div class="sec-hd"><i class="fas fa-feather sec-hd-icon"></i><div class="sec-hd-title">Intro Typing Lines</div></div>
      <div class="fg">
        <div class="fl">One line per row (shown during intro screen)</div>
        <textarea class="fta" name="intro_lines" style="min-height:150px;font-size:.8rem;">{{ db.intro_lines | join('\n') }}</textarea>
      </div>
    </div>

    <!-- Card Media -->
    <div class="sec">
      <div class="sec-hd"><i class="fas fa-play-circle sec-hd-icon"></i><div class="sec-hd-title">Card Media URLs</div></div>
      <p style="font-size:.75rem;color:rgba(255,150,190,.4);margin-bottom:16px;font-family:'Poppins',sans-serif;">Assign MP3 / MP4 / YouTube URL to each card. Plays when tapped. 💕</p>
      <div class="mgrid">
        <div class="mc"><div class="mc-hd"><div class="mc-icon">✨</div><div class="mc-title">Age Card</div></div><input class="fi" type="url" name="media_age" value="{{ db.media_map.age }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🎂</div><div class="mc-title">Birthday Card</div></div><input class="fi" type="url" name="media_birthday" value="{{ db.media_map.birthday }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🌍</div><div class="mc-title">Location Card</div></div><input class="fi" type="url" name="media_location" value="{{ db.media_map.location }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🌙</div><div class="mc-title">Zodiac Card</div></div><input class="fi" type="url" name="media_zodiac" value="{{ db.media_map.zodiac }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🎨</div><div class="mc-title">Hobbies Card</div></div><input class="fi" type="url" name="media_hobbies" value="{{ db.media_map.hobbies }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🎵</div><div class="mc-title">Music Card</div></div><input class="fi" type="url" name="media_music" value="{{ db.media_map.music }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🌸</div><div class="mc-title">Vibe Card</div></div><input class="fi" type="url" name="media_vibe" value="{{ db.media_map.vibe }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">💗</div><div class="mc-title">Bestie Card</div></div><input class="fi" type="url" name="media_bestie" value="{{ db.media_map.bestie }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
        <div class="mc"><div class="mc-hd"><div class="mc-icon">🦋</div><div class="mc-title">Quote Card</div></div><input class="fi" type="url" name="media_quote" value="{{ db.media_map.quote }}" placeholder="https://..."><div class="mc-hint">MP3 · MP4 · YouTube</div></div>
      </div>
    </div>

    <div class="fsub">
      <button type="submit" class="btn-save"><i class="fas fa-save"></i> Save All Changes</button>
    </div>
  </form>

  <!-- Password -->
  <div class="sec" style="margin-top:24px;">
    <div class="sec-hd"><i class="fas fa-lock sec-hd-icon"></i><div class="sec-hd-title">Change Password</div></div>
    <div class="pw-box">
      <form method="POST" action="/admin/change-password">
        <div class="fgrid">
          <div class="fg"><div class="fl">Current Password</div><input class="fi" type="password" name="current_password" placeholder="Current..." required></div>
          <div class="fg"><div class="fl">New Password</div><input class="fi" type="password" name="new_password" placeholder="New (min 6)..." required minlength="6"></div>
          <div class="fg"><div class="fl">Confirm New</div><input class="fi" type="password" name="confirm_password" placeholder="Confirm..." required></div>
        </div>
        <div class="fsub" style="margin-top:16px;">
          <button type="submit" class="btn-pw"><i class="fas fa-key"></i> Update Password</button>
        </div>
      </form>
    </div>
  </div>

</div>
</body>
</html>"""

# ══════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════
@app.route('/')
def index():
    db = load_db()
    return render_template_string(MAIN,
        p=db['profile'],
        socials=db['socials'],
        bg_video=db.get('background_video',''),
        bg_music=db.get('background_music',''),
        media_map=db['media_map'],
        intro_lines=db['intro_lines']
    )

@app.route('/admin')
@login_required
def admin():
    return render_template_string(ADMIN_DASH, db=load_db(), msg=None, ok=False)

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin'): return redirect('/admin')
    if request.method=='POST':
        pw = request.form.get('password','')
        db = load_db()
        if hashlib.sha256(pw.encode()).hexdigest() == db['password']:
            session['admin'] = True
            return redirect('/admin')
        return render_template_string(ADMIN_LOGIN, error='Wrong password, darling 💔')
    return render_template_string(ADMIN_LOGIN, error=None)

@app.route('/admin/logout')
def admin_logout():
    session.clear(); return redirect('/admin/login')

@app.route('/admin/save', methods=['POST'])
@login_required
def admin_save():
    db = load_db()
    f = request.form
    try:
        db['profile'].update({
            'name': f.get('name','').strip(),
            'subtitle': f.get('subtitle','').strip(),
            'tagline': f.get('tagline','').strip(),
            'bio': f.get('bio','').strip(),
            'avatar': f.get('avatar','').strip(),
            'age': f.get('age','').strip(),
            'birthday': f.get('birthday','').strip(),
            'location': f.get('location','').strip(),
            'zodiac': f.get('zodiac','').strip(),
            'hobbies': f.get('hobbies','').strip(),
            'music': f.get('music','').strip(),
            'vibe': f.get('vibe','').strip(),
            'bestie': f.get('bestie','').strip(),
            'quote': f.get('quote','').strip(),
        })
        db['socials'].update({
            'instagram': f.get('instagram','').strip(),
            'twitter': f.get('twitter','').strip(),
            'tiktok': f.get('tiktok','').strip(),
            'youtube': f.get('youtube','').strip(),
            'snapchat': f.get('snapchat','').strip(),
        })
        db['background_video'] = f.get('background_video','').strip()
        db['background_music'] = f.get('background_music','').strip()
        lines = [l.strip() for l in f.get('intro_lines','').split('\n') if l.strip()]
        if lines: db['intro_lines'] = lines
        db['media_map'].update({
            'age': f.get('media_age','').strip(),
            'birthday': f.get('media_birthday','').strip(),
            'location': f.get('media_location','').strip(),
            'zodiac': f.get('media_zodiac','').strip(),
            'hobbies': f.get('media_hobbies','').strip(),
            'music': f.get('media_music','').strip(),
            'vibe': f.get('media_vibe','').strip(),
            'bestie': f.get('media_bestie','').strip(),
            'quote': f.get('media_quote','').strip(),
        })
        save_db(db)
        return render_template_string(ADMIN_DASH, db=db, msg='✓ Saved successfully! 💕', ok=True)
    except Exception as e:
        return render_template_string(ADMIN_DASH, db=db, msg=f'Error: {e}', ok=False)

@app.route('/admin/change-password', methods=['POST'])
@login_required
def admin_change_pw():
    db = load_db()
    cur = request.form.get('current_password','')
    new = request.form.get('new_password','')
    con = request.form.get('confirm_password','')
    if hashlib.sha256(cur.encode()).hexdigest() != db['password']:
        return render_template_string(ADMIN_DASH, db=db, msg='Current password is wrong 💔', ok=False)
    if new != con:
        return render_template_string(ADMIN_DASH, db=db, msg="Passwords don't match 💔", ok=False)
    if len(new) < 6:
        return render_template_string(ADMIN_DASH, db=db, msg='Password too short (min 6) 💔', ok=False)
    db['password'] = hashlib.sha256(new.encode()).hexdigest()
    save_db(db)
    return render_template_string(ADMIN_DASH, db=db, msg='Password updated! 🌸', ok=True)

if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
        print("✓ DB created | password: admin123")
    print("\n🌸 RUHI X QNR — GIRLY BIO WEBSITE")
    print("   Site  → http://localhost:5000/")
    print("   Admin → http://localhost:5000/admin")
    print("   Pass  → admin123\n")
    app.run(debug=True, host='0.0.0.0', port=5000)

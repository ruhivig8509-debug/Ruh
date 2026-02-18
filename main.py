# main.py
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import json
import os
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = 'ruhi_qnr_secret_key_2024_ultra_secure'

# ============================================================
# DATABASE MANAGEMENT (JSON-based)
# ============================================================

DB_FILE = 'database.json'

DEFAULT_DB = {
    "password": hashlib.sha256("admin123".encode()).hexdigest(),
    "profile": {
        "name": "RUHI X QNR",
        "tagline": "Digital Ghost | Aesthetic Soul",
        "bio": "A mystery wrapped in pink code. Living between two worlds — the dark web of thoughts and the pastel dreams of reality.",
        "age": "19",
        "birthday": "January 1st",
        "location": "Lost in the Digital Void",
        "zodiac": "Capricorn ♑",
        "hobbies": "Hacking Hearts & Aesthetic Edits",
        "music": "Lo-fi & Dark Pop",
        "vibe": "Chaotic Soft Girl",
        "quote": "\"She was a glitch in the matrix, too beautiful to be an error.\"",
        "avatar": "https://i.pinimg.com/736x/8b/16/7a/8b167af653c2399dd93b952a48740620.jpg"
    },
    "socials": {
        "instagram": "https://instagram.com",
        "twitter": "https://twitter.com",
        "tiktok": "https://tiktok.com",
        "youtube": "https://youtube.com",
        "spotify": "https://spotify.com"
    },
    "background_music": "https://www.soundjay.com/misc/sounds/bell-ringing-05.mp3",
    "media_map": {
        "age": "",
        "birthday": "",
        "location": "",
        "zodiac": "",
        "hobbies": "",
        "music": "",
        "vibe": "",
        "quote": ""
    },
    "terminal_lines": [
        "Initializing secure connection...",
        "Bypassing Firewalls... [████████████] 100%",
        "Decrypting encrypted data packets...",
        "Accessing RUHI X QNR Database...",
        "Loading personality matrix...",
        "Aesthetic core: ONLINE",
        "Chaos module: ACTIVE",
        "Welcome, User. Proceed with caution. 💕"
    ]
}

def load_db():
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
        return DEFAULT_DB
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            for key in DEFAULT_DB:
                if key not in data:
                    data[key] = DEFAULT_DB[key]
            if 'media_map' not in data:
                data['media_map'] = DEFAULT_DB['media_map']
            return data
    except:
        return DEFAULT_DB

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ============================================================
# MAIN TEMPLATE
# ============================================================

MAIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ profile.name }} | Digital Identity</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Poppins:wght@300;400;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
/* ==================== RESET & BASE ==================== */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --pink-primary: #ff6eb4;
  --pink-secondary: #ff9ed2;
  --pink-light: #ffd6ec;
  --pink-dark: #c2185b;
  --purple: #9c27b0;
  --cyan: #00ffff;
  --green: #00ff41;
  --dark: #0a0a0a;
  --glass: rgba(255,255,255,0.08);
  --glass-border: rgba(255,182,193,0.3);
}

html, body {
  width: 100%; height: 100%;
  overflow: hidden;
  background: #000;
  font-family: 'Orbitron', monospace;
  cursor: crosshair;
}

/* ==================== PHASE 1: GLITCH SCREEN ==================== */
#phase-glitch {
  position: fixed; inset: 0;
  background: #000;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: glitchPhaseOut 0.5s 3s forwards;
}

.glitch-overlay {
  position: absolute; inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,255,65,0.03) 2px,
    rgba(0,255,65,0.03) 4px
  );
  animation: scanlines 0.1s linear infinite;
  pointer-events: none;
}

.glitch-bars {
  position: absolute; inset: 0;
  overflow: hidden;
}

.glitch-bar {
  position: absolute;
  left: 0; right: 0;
  background: rgba(0,255,65,0.15);
  animation: glitchBar 0.3s ease infinite;
}

.glitch-bar:nth-child(1) { top: 20%; height: 3px; animation-delay: 0s; }
.glitch-bar:nth-child(2) { top: 45%; height: 5px; animation-delay: 0.1s; }
.glitch-bar:nth-child(3) { top: 70%; height: 2px; animation-delay: 0.2s; }
.glitch-bar:nth-child(4) { top: 85%; height: 8px; animation-delay: 0.05s; }
.glitch-bar:nth-child(5) { top: 10%; height: 4px; animation-delay: 0.15s; }

.glitch-zigzag {
  position: absolute; inset: 0;
  background:
    repeating-linear-gradient(
      45deg,
      transparent 0px, transparent 10px,
      rgba(0,255,65,0.02) 10px, rgba(0,255,65,0.02) 12px
    ),
    repeating-linear-gradient(
      -45deg,
      transparent 0px, transparent 10px,
      rgba(255,0,100,0.02) 10px, rgba(255,0,100,0.02) 12px
    );
  animation: zigzagShift 0.5s linear infinite;
}

.glitch-text-center {
  position: relative;
  font-family: 'Orbitron', monospace;
  font-size: clamp(1rem, 4vw, 2.5rem);
  font-weight: 900;
  color: #00ff41;
  text-shadow: 2px 0 #ff0066, -2px 0 #00ffff;
  animation: glitchText 0.3s ease infinite;
  letter-spacing: 0.3em;
  z-index: 2;
}

.glitch-text-center::before {
  content: attr(data-text);
  position: absolute;
  left: 3px; top: 0;
  color: #ff0066;
  clip-path: polygon(0 30%, 100% 30%, 100% 50%, 0 50%);
  animation: glitchClip1 0.4s infinite;
}

.glitch-text-center::after {
  content: attr(data-text);
  position: absolute;
  left: -3px; top: 0;
  color: #00ffff;
  clip-path: polygon(0 60%, 100% 60%, 100% 80%, 0 80%);
  animation: glitchClip2 0.5s infinite;
}

.error-code {
  position: absolute;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: rgba(0,255,65,0.4);
  animation: randomPos 0.2s infinite;
}

.error-code:nth-child(1) { top: 15%; left: 5%; }
.error-code:nth-child(2) { top: 25%; right: 8%; }
.error-code:nth-child(3) { top: 55%; left: 12%; }
.error-code:nth-child(4) { top: 75%; right: 5%; }
.error-code:nth-child(5) { top: 40%; left: 40%; }
.error-code:nth-child(6) { top: 65%; left: 60%; }
.error-code:nth-child(7) { top: 5%; left: 30%; }
.error-code:nth-child(8) { top: 90%; left: 20%; }

@keyframes glitchBar {
  0%, 100% { opacity: 0; transform: translateX(0); }
  50% { opacity: 1; transform: translateX(random(20px) - 10px); }
  25% { transform: translateX(-15px); opacity: 0.8; }
  75% { transform: translateX(10px); opacity: 0.6; }
}

@keyframes glitchText {
  0%, 90%, 100% { text-shadow: 2px 0 #ff0066, -2px 0 #00ffff; transform: translate(0); }
  92% { text-shadow: -3px 0 #ff0066, 3px 0 #00ffff; transform: translate(-3px, 1px); }
  94% { text-shadow: 3px 0 #ff0066, -3px 0 #00ffff; transform: translate(3px, -1px); }
  96% { text-shadow: 0 0 #ff0066, 0 0 #00ffff; transform: translate(0); }
}

@keyframes glitchClip1 {
  0%, 100% { clip-path: polygon(0 30%, 100% 30%, 100% 50%, 0 50%); transform: translateX(3px); }
  50% { clip-path: polygon(0 15%, 100% 15%, 100% 35%, 0 35%); transform: translateX(-3px); }
}

@keyframes glitchClip2 {
  0%, 100% { clip-path: polygon(0 60%, 100% 60%, 100% 80%, 0 80%); transform: translateX(-3px); }
  50% { clip-path: polygon(0 75%, 100% 75%, 100% 90%, 0 90%); transform: translateX(3px); }
}

@keyframes scanlines {
  0% { background-position: 0 0; }
  100% { background-position: 0 4px; }
}

@keyframes zigzagShift {
  0% { transform: translateX(0); }
  100% { transform: translateX(24px); }
}

@keyframes randomPos {
  0%, 100% { opacity: 0.3; transform: translate(0,0); }
  25% { opacity: 0.8; transform: translate(2px, -1px); }
  75% { opacity: 0.1; transform: translate(-1px, 2px); }
}

@keyframes glitchPhaseOut {
  0% { opacity: 1; }
  100% { opacity: 0; pointer-events: none; }
}

/* ==================== PHASE 2: TERMINAL ==================== */
#phase-terminal {
  position: fixed; inset: 0;
  background: #0a0a0a;
  z-index: 900;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  animation: terminalFadeIn 0.8s 3.5s forwards;
}

@keyframes terminalFadeIn {
  to { opacity: 1; }
}

.terminal-window {
  width: min(700px, 90vw);
  background: rgba(0,20,0,0.95);
  border: 1px solid #00ff41;
  border-radius: 8px;
  box-shadow: 0 0 40px rgba(0,255,65,0.3), inset 0 0 40px rgba(0,10,0,0.5);
  overflow: hidden;
}

.terminal-header {
  background: #1a1a1a;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid #00ff41;
}

.terminal-dot {
  width: 12px; height: 12px;
  border-radius: 50%;
}
.terminal-dot.red { background: #ff5f56; }
.terminal-dot.yellow { background: #ffbd2e; }
.terminal-dot.green { background: #27c93f; }

.terminal-title {
  flex: 1;
  text-align: center;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  color: #00ff41;
  letter-spacing: 0.2em;
}

.terminal-body {
  padding: 20px;
  min-height: 300px;
  font-family: 'Share Tech Mono', monospace;
  font-size: clamp(0.7rem, 2vw, 0.9rem);
  color: #00ff41;
  line-height: 1.8;
}

.terminal-line {
  display: block;
  opacity: 0;
  animation: lineAppear 0.1s forwards;
}

.terminal-cursor {
  display: inline-block;
  width: 8px;
  height: 1em;
  background: #00ff41;
  animation: blink 0.7s infinite;
  vertical-align: text-bottom;
  margin-left: 2px;
}

.terminal-prompt { color: #ffbd2e; }
.terminal-success { color: #27c93f; }
.terminal-info { color: #00ffff; }
.terminal-warn { color: #ff6eb4; }

@keyframes lineAppear { to { opacity: 1; } }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* ==================== PHASE 3: ACCESS GRANTED ==================== */
#phase-access {
  position: fixed; inset: 0;
  background: #fff;
  z-index: 800;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
}

#phase-access.active {
  pointer-events: all;
}

.access-title {
  font-family: 'Orbitron', monospace;
  font-size: clamp(1.5rem, 6vw, 4rem);
  font-weight: 900;
  color: #000;
  letter-spacing: 0.15em;
  text-align: center;
  animation: accessPulse 1s ease infinite;
}

.access-sub {
  font-family: 'Share Tech Mono', monospace;
  color: #333;
  margin: 10px 0 40px;
  letter-spacing: 0.3em;
  font-size: clamp(0.6rem, 2vw, 0.9rem);
}

.enter-btn {
  font-family: 'Orbitron', monospace;
  font-size: clamp(1rem, 3vw, 1.5rem);
  font-weight: 700;
  letter-spacing: 0.3em;
  padding: 20px 60px;
  background: #000;
  color: #fff;
  border: 3px solid #000;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
  animation: enterPulse 1.5s ease infinite;
}

.enter-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(45deg, #ff6eb4, #9c27b0, #00ffff, #00ff41);
  background-size: 400%;
  opacity: 0;
  transition: opacity 0.3s;
  animation: gradientShift 3s linear infinite;
}

.enter-btn:hover::before { opacity: 1; }
.enter-btn:hover { color: #fff; border-color: transparent; transform: scale(1.05); }
.enter-btn span { position: relative; z-index: 1; }

@keyframes accessPulse {
  0%, 100% { text-shadow: 0 0 20px rgba(0,0,0,0.3); }
  50% { text-shadow: 0 0 40px rgba(255,110,180,0.8), 0 0 60px rgba(156,39,176,0.6); }
}

@keyframes enterPulse {
  0%, 100% { box-shadow: 0 0 20px rgba(0,0,0,0.3); }
  50% { box-shadow: 0 0 40px rgba(255,110,180,0.6), 0 0 80px rgba(156,39,176,0.4); }
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  100% { background-position: 400% 50%; }
}

/* ==================== LOADING BAR ==================== */
#loading-screen {
  position: fixed; inset: 0;
  background: #000;
  z-index: 700;
  display: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
}

.loading-label {
  font-family: 'Orbitron', monospace;
  color: #00ff41;
  font-size: clamp(0.7rem, 2vw, 1rem);
  letter-spacing: 0.3em;
  animation: loadingPulse 0.5s ease infinite;
}

.loading-bar-container {
  width: min(400px, 80vw);
  height: 4px;
  background: rgba(0,255,65,0.2);
  border-radius: 2px;
  overflow: hidden;
}

.loading-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #00ff41, #00ffff, #ff6eb4);
  background-size: 200%;
  width: 0%;
  border-radius: 2px;
  transition: width 0.05s linear;
  animation: loadingGlow 1s linear infinite;
}

@keyframes loadingPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes loadingGlow {
  0% { background-position: 0% 50%; box-shadow: 0 0 10px #00ff41; }
  100% { background-position: 200% 50%; box-shadow: 0 0 20px #ff6eb4; }
}

/* ==================== VORTEX ==================== */
#vortex-container {
  position: fixed; inset: 0;
  z-index: 600;
  pointer-events: none;
  display: none;
}

.vortex-active {
  animation: vortexSpin 1.5s cubic-bezier(0.55, 0, 1, 0.45) forwards !important;
}

@keyframes vortexSpin {
  0% { transform: rotate(0deg) scale(1); opacity: 1; }
  50% { transform: rotate(180deg) scale(0.5); opacity: 0.6; }
  100% { transform: rotate(360deg) scale(0) translateY(50vh); opacity: 0; }
}

/* ==================== PHASE 5: BIO PAGE ==================== */
#phase-bio {
  position: fixed; inset: 0;
  background: linear-gradient(135deg, #1a0026 0%, #2d0040 30%, #1a0033 60%, #0d001a 100%);
  z-index: 100;
  overflow-y: auto;
  opacity: 0;
  pointer-events: none;
  scroll-behavior: smooth;
}

#phase-bio.active {
  opacity: 1;
  pointer-events: all;
  transition: opacity 1s ease;
}

/* Animated background */
.bio-bg-animation {
  position: fixed; inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.bio-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  animation: orbFloat 6s ease-in-out infinite;
}

.bio-orb:nth-child(1) {
  width: 400px; height: 400px;
  background: radial-gradient(circle, #ff6eb4, transparent);
  top: -100px; left: -100px;
  animation-duration: 8s;
}

.bio-orb:nth-child(2) {
  width: 300px; height: 300px;
  background: radial-gradient(circle, #9c27b0, transparent);
  bottom: -50px; right: -50px;
  animation-duration: 10s;
  animation-delay: -3s;
}

.bio-orb:nth-child(3) {
  width: 200px; height: 200px;
  background: radial-gradient(circle, #e91e8c, transparent);
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  animation-duration: 12s;
  animation-delay: -6s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.1); }
  66% { transform: translate(-20px, 30px) scale(0.9); }
}

/* Floating particles */
.particle {
  position: fixed;
  pointer-events: none;
  font-size: clamp(0.8rem, 1.5vw, 1.2rem);
  animation: particleFloat linear infinite;
  z-index: 1;
  opacity: 0.6;
}

@keyframes particleFloat {
  0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
  10% { opacity: 0.6; }
  90% { opacity: 0.6; }
  100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
}

/* Bio content */
.bio-content {
  position: relative;
  z-index: 10;
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px 80px;
}

/* Profile header */
.bio-header {
  text-align: center;
  margin-bottom: 50px;
  animation: bioHeaderReveal 1s 0.3s both;
}

@keyframes bioHeaderReveal {
  from { transform: translateY(-30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.bio-avatar-container {
  position: relative;
  display: inline-block;
  margin-bottom: 20px;
}

.bio-avatar {
  width: clamp(120px, 20vw, 160px);
  height: clamp(120px, 20vw, 160px);
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid rgba(255,110,180,0.5);
  box-shadow: 0 0 40px rgba(255,110,180,0.4), 0 0 80px rgba(156,39,176,0.3);
  animation: avatarPulse 3s ease infinite;
}

.avatar-ring {
  position: absolute; inset: -8px;
  border-radius: 50%;
  border: 2px solid transparent;
  background: linear-gradient(#1a0026, #1a0026) padding-box,
              linear-gradient(45deg, #ff6eb4, #9c27b0, #ff6eb4) border-box;
  animation: ringRotate 4s linear infinite;
}

.avatar-ring-outer {
  position: absolute; inset: -16px;
  border-radius: 50%;
  border: 1px solid rgba(255,110,180,0.3);
  animation: ringRotate 6s linear infinite reverse;
}

@keyframes avatarPulse {
  0%, 100% { box-shadow: 0 0 40px rgba(255,110,180,0.4), 0 0 80px rgba(156,39,176,0.3); }
  50% { box-shadow: 0 0 60px rgba(255,110,180,0.7), 0 0 120px rgba(156,39,176,0.5); }
}

@keyframes ringRotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.bio-name {
  font-family: 'Orbitron', monospace;
  font-size: clamp(1.5rem, 5vw, 3rem);
  font-weight: 900;
  background: linear-gradient(135deg, #ff6eb4, #ff9ed2, #e91e8c, #9c27b0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 10px;
  letter-spacing: 0.1em;
  animation: nameShimmer 3s ease infinite;
  background-size: 200%;
}

@keyframes nameShimmer {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.bio-tagline {
  font-family: 'Poppins', sans-serif;
  color: rgba(255,182,193,0.8);
  font-size: clamp(0.8rem, 2vw, 1rem);
  font-weight: 300;
  letter-spacing: 0.2em;
  margin-bottom: 20px;
}

.bio-description {
  font-family: 'Poppins', sans-serif;
  color: rgba(255,255,255,0.7);
  font-size: clamp(0.8rem, 2vw, 0.95rem);
  line-height: 1.8;
  max-width: 500px;
  margin: 0 auto 30px;
}

/* Social links */
.social-links {
  display: flex;
  justify-content: center;
  gap: clamp(8px, 2vw, 16px);
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.social-link {
  display: flex;
  align-items: center;
  justify-content: center;
  width: clamp(36px, 5vw, 44px);
  height: clamp(36px, 5vw, 44px);
  border-radius: 50%;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,110,180,0.3);
  color: #ff9ed2;
  font-size: clamp(0.9rem, 2vw, 1.1rem);
  text-decoration: none;
  transition: all 0.3s;
  backdrop-filter: blur(10px);
}

.social-link:hover {
  background: rgba(255,110,180,0.2);
  border-color: #ff6eb4;
  color: #fff;
  transform: translateY(-3px) scale(1.1);
  box-shadow: 0 10px 30px rgba(255,110,180,0.4);
}

/* Section title */
.section-title {
  font-family: 'Orbitron', monospace;
  font-size: clamp(0.8rem, 2.5vw, 1rem);
  color: rgba(255,182,193,0.6);
  letter-spacing: 0.4em;
  text-align: center;
  margin-bottom: 30px;
  position: relative;
}

.section-title::before,
.section-title::after {
  content: '─────';
  margin: 0 10px;
  opacity: 0.4;
}

/* Bio cards grid */
.bio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr));
  gap: clamp(12px, 2vw, 20px);
  margin-bottom: 40px;
}

.bio-card {
  position: relative;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,110,180,0.2);
  border-radius: 16px;
  padding: clamp(16px, 3vw, 24px);
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  backdrop-filter: blur(10px);
  overflow: hidden;
  animation: cardReveal 0.6s both;
  -webkit-tap-highlight-color: transparent;
}

.bio-card:nth-child(1) { animation-delay: 0.1s; }
.bio-card:nth-child(2) { animation-delay: 0.15s; }
.bio-card:nth-child(3) { animation-delay: 0.2s; }
.bio-card:nth-child(4) { animation-delay: 0.25s; }
.bio-card:nth-child(5) { animation-delay: 0.3s; }
.bio-card:nth-child(6) { animation-delay: 0.35s; }
.bio-card:nth-child(7) { animation-delay: 0.4s; }
.bio-card:nth-child(8) { animation-delay: 0.45s; }

@keyframes cardReveal {
  from { transform: translateY(30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.bio-card::before {
  content: '';
  position: absolute; inset: 0;
  background: linear-gradient(135deg, rgba(255,110,180,0.1), rgba(156,39,176,0.1));
  opacity: 0;
  transition: opacity 0.3s;
}

.bio-card::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
  transition: left 0.5s;
}

.bio-card:hover {
  transform: translateY(-8px) scale(1.02);
  border-color: rgba(255,110,180,0.6);
  box-shadow: 0 20px 60px rgba(255,110,180,0.2), 0 0 0 1px rgba(255,110,180,0.1);
}

.bio-card:hover::before { opacity: 1; }
.bio-card:hover::after { left: 100%; }

.bio-card:active { transform: scale(0.97); }

.bio-card.playing {
  border-color: #ff6eb4;
  box-shadow: 0 0 30px rgba(255,110,180,0.5), 0 0 60px rgba(156,39,176,0.3);
  animation: cardPlaying 1s ease infinite;
}

@keyframes cardPlaying {
  0%, 100% { box-shadow: 0 0 30px rgba(255,110,180,0.5), 0 0 60px rgba(156,39,176,0.3); }
  50% { box-shadow: 0 0 50px rgba(255,110,180,0.8), 0 0 80px rgba(156,39,176,0.5); }
}

.card-icon {
  font-size: clamp(1.2rem, 3vw, 1.8rem);
  margin-bottom: 10px;
  background: linear-gradient(135deg, #ff6eb4, #9c27b0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.card-label {
  font-family: 'Orbitron', monospace;
  font-size: clamp(0.55rem, 1.5vw, 0.65rem);
  color: rgba(255,182,193,0.6);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.card-value {
  font-family: 'Poppins', sans-serif;
  font-size: clamp(0.75rem, 2vw, 0.95rem);
  color: rgba(255,255,255,0.9);
  font-weight: 600;
  line-height: 1.4;
}

.card-media-indicator {
  position: absolute;
  top: 10px; right: 10px;
  font-size: 0.6rem;
  color: rgba(255,110,180,0.5);
  transition: all 0.3s;
}

.bio-card:hover .card-media-indicator {
  color: #ff6eb4;
  transform: scale(1.3);
}

/* Quote card - full width */
.bio-card.quote-card {
  grid-column: 1 / -1;
  text-align: center;
  padding: clamp(20px, 4vw, 35px);
}

.quote-card .card-value {
  font-size: clamp(0.85rem, 2.5vw, 1.1rem);
  font-style: italic;
  font-weight: 300;
  color: rgba(255,182,193,0.9);
}

/* Media popup */
#media-popup {
  position: fixed; inset: 0;
  z-index: 2000;
  display: none;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(10px);
}

#media-popup.active {
  display: flex;
}

.popup-content {
  background: rgba(30,0,50,0.95);
  border: 1px solid rgba(255,110,180,0.4);
  border-radius: 20px;
  padding: 30px;
  max-width: min(500px, 90vw);
  width: 100%;
  position: relative;
  box-shadow: 0 0 80px rgba(255,110,180,0.3);
  animation: popupReveal 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes popupReveal {
  from { transform: scale(0.5) rotate(-10deg); opacity: 0; }
  to { transform: scale(1) rotate(0deg); opacity: 1; }
}

.popup-close {
  position: absolute;
  top: 15px; right: 15px;
  background: none;
  border: none;
  color: rgba(255,110,180,0.7);
  font-size: 1.5rem;
  cursor: pointer;
  transition: all 0.3s;
  line-height: 1;
}

.popup-close:hover { color: #ff6eb4; transform: rotate(90deg); }

.popup-title {
  font-family: 'Orbitron', monospace;
  font-size: 1rem;
  color: #ff9ed2;
  margin-bottom: 20px;
  letter-spacing: 0.2em;
}

.popup-media {
  width: 100%;
  border-radius: 10px;
  background: rgba(0,0,0,0.5);
}

.popup-media audio { width: 100%; }

.popup-no-media {
  font-family: 'Poppins', sans-serif;
  color: rgba(255,182,193,0.6);
  text-align: center;
  padding: 20px;
  font-size: 0.9rem;
}

/* Background music control */
.music-control {
  position: fixed;
  bottom: 20px; right: 20px;
  z-index: 500;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,110,180,0.3);
  border-radius: 50px;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
  display: none;
  color: #ff9ed2;
  font-size: 0.75rem;
  font-family: 'Orbitron', monospace;
  letter-spacing: 0.1em;
}

.music-control:hover {
  background: rgba(255,110,180,0.15);
  border-color: #ff6eb4;
}

.music-control.show { display: flex; }
.music-icon { animation: musicBounce 0.5s ease infinite alternate; }
@keyframes musicBounce {
  from { transform: scale(1); }
  to { transform: scale(1.2); }
}

/* Scrollbar */
#phase-bio::-webkit-scrollbar { width: 4px; }
#phase-bio::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
#phase-bio::-webkit-scrollbar-thumb { background: rgba(255,110,180,0.4); border-radius: 2px; }

/* Sparkle effect */
.sparkle {
  position: fixed;
  pointer-events: none;
  z-index: 999;
  font-size: 1rem;
  animation: sparkleAnim 0.8s ease forwards;
}

@keyframes sparkleAnim {
  0% { transform: translate(-50%, -50%) scale(0) rotate(0deg); opacity: 1; }
  50% { transform: translate(-50%, -50%) scale(1.5) rotate(180deg); opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(0) rotate(360deg); opacity: 0; }
}

/* Responsive */
@media (max-width: 480px) {
  .bio-grid { grid-template-columns: 1fr 1fr; }
  .bio-card.quote-card { grid-column: 1 / -1; }
}

/* ==================== HEARTS ==================== */
.floating-heart {
  position: fixed;
  pointer-events: none;
  font-size: clamp(0.8rem, 2vw, 1.2rem);
  z-index: 1;
  animation: heartFloat linear infinite;
  opacity: 0;
}

@keyframes heartFloat {
  0% { transform: translateY(100vh) rotate(0deg) scale(0); opacity: 0; }
  10% { opacity: 0.8; transform: translateY(90vh) scale(1); }
  90% { opacity: 0.8; }
  100% { transform: translateY(-20px) rotate(20deg) scale(0.5); opacity: 0; }
}

/* Utility */
.hidden { display: none !important; }

</style>
</head>
<body>

<!-- ========== PHASE 1: GLITCH ========== -->
<div id="phase-glitch">
  <div class="glitch-overlay"></div>
  <div class="glitch-zigzag"></div>
  <div class="glitch-bars">
    <div class="glitch-bar"></div>
    <div class="glitch-bar"></div>
    <div class="glitch-bar"></div>
    <div class="glitch-bar"></div>
    <div class="glitch-bar"></div>
  </div>
  <span class="glitch-text-center" data-text="SYSTEM ERROR">SYSTEM ERROR</span>
  <div class="error-code">ERR_0x4F2A::NULL_REF</div>
  <div class="error-code">SEGFAULT_0x00FF::CORE_DUMP</div>
  <div class="error-code">KERNEL_PANIC::INIT_FAILED</div>
  <div class="error-code">0xDEADBEEF::MEM_CORRUPT</div>
  <div class="error-code">FIREWALL_BREACH::LEVEL_9</div>
  <div class="error-code">AUTH_BYPASS::ATTEMPTING</div>
  <div class="error-code">NET_PKT_DROP::0x7F2B</div>
  <div class="error-code">SYS_OVERRIDE::PENDING</div>
</div>

<!-- ========== PHASE 2: TERMINAL ========== -->
<div id="phase-terminal">
  <div class="terminal-window">
    <div class="terminal-header">
      <div class="terminal-dot red"></div>
      <div class="terminal-dot yellow"></div>
      <div class="terminal-dot green"></div>
      <div class="terminal-title">RUHI_X_QNR_TERMINAL v2.4.1 — SSH ENCRYPTED</div>
    </div>
    <div class="terminal-body" id="terminal-body">
      <span class="terminal-line terminal-prompt">root@darkweb:~$ <span id="terminal-text"></span><span class="terminal-cursor" id="cursor"></span></span>
    </div>
  </div>
</div>

<!-- ========== PHASE 3: ACCESS GRANTED ========== -->
<div id="phase-access">
  <div class="access-title">⚡ SYSTEM ACCESS GRANTED ⚡</div>
  <div class="access-sub">[ IDENTITY VERIFIED | CLEARANCE LEVEL: PINK ]</div>
  <button class="enter-btn" id="enter-btn" onclick="enterPortal()">
    <span>◈ ENTER ◈</span>
  </button>
</div>

<!-- ========== LOADING SCREEN ========== -->
<div id="loading-screen">
  <div class="loading-label" id="loading-label">INITIALIZING AESTHETIC CORE...</div>
  <div class="loading-bar-container">
    <div class="loading-bar-fill" id="loading-bar"></div>
  </div>
</div>

<!-- ========== PHASE 5: BIO PAGE ========== -->
<div id="phase-bio">
  <div class="bio-bg-animation">
    <div class="bio-orb"></div>
    <div class="bio-orb"></div>
    <div class="bio-orb"></div>
  </div>

  <div class="bio-content">
    <!-- Profile Header -->
    <div class="bio-header">
      <div class="bio-avatar-container">
        <div class="avatar-ring-outer"></div>
        <div class="avatar-ring"></div>
        <img src="{{ profile.avatar }}" alt="{{ profile.name }}" class="bio-avatar" onerror="this.src='https://via.placeholder.com/160/ff6eb4/ffffff?text=♡'">
      </div>
      <div class="bio-name">{{ profile.name }}</div>
      <div class="bio-tagline">✦ {{ profile.tagline }} ✦</div>
      <div class="bio-description">{{ profile.bio }}</div>

      <!-- Social Links -->
      <div class="social-links">
        {% if socials.instagram %}
        <a href="{{ socials.instagram }}" target="_blank" class="social-link" title="Instagram">
          <i class="fab fa-instagram"></i>
        </a>
        {% endif %}
        {% if socials.twitter %}
        <a href="{{ socials.twitter }}" target="_blank" class="social-link" title="Twitter">
          <i class="fab fa-twitter"></i>
        </a>
        {% endif %}
        {% if socials.tiktok %}
        <a href="{{ socials.tiktok }}" target="_blank" class="social-link" title="TikTok">
          <i class="fab fa-tiktok"></i>
        </a>
        {% endif %}
        {% if socials.youtube %}
        <a href="{{ socials.youtube }}" target="_blank" class="social-link" title="YouTube">
          <i class="fab fa-youtube"></i>
        </a>
        {% endif %}
        {% if socials.spotify %}
        <a href="{{ socials.spotify }}" target="_blank" class="social-link" title="Spotify">
          <i class="fab fa-spotify"></i>
        </a>
        {% endif %}
      </div>
    </div>

    <!-- Bio Details -->
    <div class="section-title">✦ ABOUT ME ✦</div>
    <div class="bio-grid">
      <div class="bio-card" onclick="handleCardClick('age', this, event)" data-category="age">
        <div class="card-icon"><i class="fas fa-star-of-life"></i></div>
        <div class="card-label">Age</div>
        <div class="card-value">{{ profile.age }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card" onclick="handleCardClick('birthday', this, event)" data-category="birthday">
        <div class="card-icon"><i class="fas fa-birthday-cake"></i></div>
        <div class="card-label">Birthday</div>
        <div class="card-value">{{ profile.birthday }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card" onclick="handleCardClick('location', this, event)" data-category="location">
        <div class="card-icon"><i class="fas fa-map-pin"></i></div>
        <div class="card-label">Location</div>
        <div class="card-value">{{ profile.location }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card" onclick="handleCardClick('zodiac', this, event)" data-category="zodiac">
        <div class="card-icon"><i class="fas fa-moon"></i></div>
        <div class="card-label">Zodiac</div>
        <div class="card-value">{{ profile.zodiac }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card" onclick="handleCardClick('hobbies', this, event)" data-category="hobbies">
        <div class="card-icon"><i class="fas fa-heart"></i></div>
        <div class="card-label">Hobbies</div>
        <div class="card-value">{{ profile.hobbies }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card" onclick="handleCardClick('music', this, event)" data-category="music">
        <div class="card-icon"><i class="fas fa-music"></i></div>
        <div class="card-label">Music Taste</div>
        <div class="card-value">{{ profile.music }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card" onclick="handleCardClick('vibe', this, event)" data-category="vibe">
        <div class="card-icon"><i class="fas fa-magic"></i></div>
        <div class="card-label">My Vibe</div>
        <div class="card-value">{{ profile.vibe }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
      <div class="bio-card quote-card" onclick="handleCardClick('quote', this, event)" data-category="quote">
        <div class="card-icon"><i class="fas fa-quote-left"></i></div>
        <div class="card-label">My Quote</div>
        <div class="card-value">{{ profile.quote }}</div>
        <div class="card-media-indicator"><i class="fas fa-play-circle"></i></div>
      </div>
    </div>

    <!-- Footer -->
    <div style="text-align:center; font-family:'Poppins',sans-serif; color:rgba(255,182,193,0.4); font-size:0.75rem; letter-spacing:0.2em;">
      ✦ made with love & dark energy ✦
    </div>
  </div>
</div>

<!-- ========== MEDIA POPUP ========== -->
<div id="media-popup">
  <div class="popup-content">
    <button class="popup-close" onclick="closePopup()">×</button>
    <div class="popup-title" id="popup-title">♡ PLAYING</div>
    <div class="popup-media" id="popup-media"></div>
  </div>
</div>

<!-- Music Control -->
<div class="music-control" id="music-control" onclick="toggleBgMusic()">
  <i class="fas fa-music music-icon" id="music-icon"></i>
  <span id="music-label">PAUSE</span>
</div>

<!-- Background Audio -->
<audio id="bg-music" loop>
  <source src="{{ background_music }}" type="audio/mpeg">
</audio>

<script>
// ============================================================
// GLOBAL STATE
// ============================================================
const mediaMap = {{ media_map | tojson }};
let bgMusicPlaying = false;
let activeCardEl = null;
let currentAudioEl = null;
const terminalLines = {{ terminal_lines | tojson }};

// ============================================================
// PHASE SEQUENCER
// ============================================================
window.addEventListener('load', () => {
  // Phase 1 auto-ends at 3s (CSS animation)
  // Phase 2 begins at 3.5s
  setTimeout(startTerminal, 3600);
});

// ============================================================
// PHASE 2: TERMINAL TYPING
// ============================================================
async function startTerminal() {
  const terminalBody = document.getElementById('terminal-body');
  const firstLine = document.getElementById('terminal-text');
  const cursor = document.getElementById('cursor');

  // Type terminal lines one by one
  for (let i = 0; i < terminalLines.length; i++) {
    const line = terminalLines[i];
    let displayEl;

    if (i === 0) {
      displayEl = firstLine;
    } else {
      // Create new line
      const lineSpan = document.createElement('div');
      lineSpan.style.cssText = `
        font-family: 'Share Tech Mono', monospace;
        font-size: clamp(0.7rem, 2vw, 0.9rem);
        color: ${getLineColor(line)};
        line-height: 1.8;
        opacity: 0;
        animation: lineAppear 0.1s forwards;
      `;
      terminalBody.insertBefore(lineSpan, cursor.parentElement.nextSibling || null);
      terminalBody.appendChild(lineSpan);
      displayEl = lineSpan;
    }

    // Type character by character
    await typeText(displayEl, line, 35);

    // Pause between lines
    await sleep(200);
  }

  // Transition to Phase 3
  await sleep(500);
  transitionToAccess();
}

function getLineColor(line) {
  if (line.includes('Bypassing') || line.includes('ERROR')) return '#ff6eb4';
  if (line.includes('Welcome') || line.includes('ONLINE') || line.includes('ACTIVE')) return '#27c93f';
  if (line.includes('Accessing') || line.includes('Loading')) return '#00ffff';
  return '#00ff41';
}

function typeText(element, text, speed) {
  return new Promise(resolve => {
    let i = 0;
    element.style.opacity = '1';
    const interval = setInterval(() => {
      element.textContent += text[i];
      i++;
      // Scroll terminal to bottom
      const term = document.getElementById('phase-terminal');
      if (term) term.querySelector('.terminal-window').scrollTop = 999;
      if (i >= text.length) {
        clearInterval(interval);
        resolve();
      }
    }, speed);
  });
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================
// PHASE 3: ACCESS GRANTED
// ============================================================
function transitionToAccess() {
  const terminal = document.getElementById('phase-terminal');
  const access = document.getElementById('phase-access');

  // Flash white
  terminal.style.transition = 'opacity 0.3s';
  terminal.style.opacity = '0';

  setTimeout(() => {
    terminal.style.display = 'none';
    access.classList.add('active');
    // Animate access page in
    access.animate([
      { opacity: 0, filter: 'brightness(10)' },
      { opacity: 1, filter: 'brightness(1)' }
    ], { duration: 600, fill: 'forwards' });
  }, 300);
}

// ============================================================
// PHASE 4: ENTER / VORTEX
// ============================================================
function enterPortal() {
  const access = document.getElementById('phase-access');
  const loading = document.getElementById('loading-screen');
  const bgMusic = document.getElementById('bg-music');

  // Start background music immediately
  bgMusic.volume = 0.5;
  bgMusic.play().then(() => {
    bgMusicPlaying = true;
  }).catch(e => console.log('Audio autoplay blocked:', e));

  // Show loading screen
  access.style.transition = 'opacity 0.5s';
  access.style.opacity = '0';
  setTimeout(() => {
    access.style.display = 'none';
    loading.style.display = 'flex';
    runLoadingBar();
  }, 500);
}

const loadingMessages = [
  'INITIALIZING AESTHETIC CORE...',
  'LOADING PERSONALITY MATRIX...',
  'CALIBRATING PINK FREQUENCIES...',
  'RENDERING GLASSOMORPHISM...',
  'DEPLOYING FLOATING HEARTS...',
  'UNLOCKING IDENTITY DATABASE...',
  'AESTHETIC CORE: READY ✓',
  'WELCOME. ♡'
];

async function runLoadingBar() {
  const bar = document.getElementById('loading-bar');
  const label = document.getElementById('loading-label');
  let progress = 0;

  const interval = setInterval(async () => {
    progress += Math.random() * 4 + 1;
    if (progress > 100) progress = 100;
    bar.style.width = progress + '%';

    const msgIndex = Math.floor((progress / 100) * loadingMessages.length);
    if (msgIndex < loadingMessages.length) {
      label.textContent = loadingMessages[Math.min(msgIndex, loadingMessages.length - 1)];
    }

    if (progress >= 100) {
      clearInterval(interval);
      await sleep(800);
      startVortex();
    }
  }, 60);
}

function startVortex() {
  const loading = document.getElementById('loading-screen');

  loading.style.transition = 'opacity 0.3s';
  loading.style.opacity = '0';

  setTimeout(() => {
    loading.style.display = 'none';
    // Vortex: all content spins into center, then bio reveals
    triggerVortexAnimation();
  }, 400);
}

function triggerVortexAnimation() {
  const vortexEl = document.createElement('div');
  vortexEl.style.cssText = `
    position: fixed; inset: 0; z-index: 600;
    background: radial-gradient(circle at 50% 50%, #ff6eb4 0%, #9c27b0 30%, #000 70%);
    display: flex; align-items: center; justify-content: center;
    animation: vortexAppear 1.5s ease forwards;
  `;

  // Create spinning vortex rings
  for (let r = 0; r < 6; r++) {
    const ring = document.createElement('div');
    const size = 60 + r * 80;
    ring.style.cssText = `
      position: absolute;
      width: ${size}px; height: ${size}px;
      border: 2px solid rgba(255,110,180,${0.8 - r * 0.12});
      border-radius: 50%;
      animation: vortexRing ${0.8 + r * 0.15}s linear infinite;
      box-shadow: 0 0 ${10 + r * 5}px rgba(255,110,180,0.5);
    `;
    vortexEl.appendChild(ring);
  }

  const style = document.createElement('style');
  style.textContent = `
    @keyframes vortexAppear {
      0% { transform: scale(0); opacity: 0; }
      30% { transform: scale(1); opacity: 1; }
      70% { transform: scale(1); opacity: 1; }
      100% { transform: scale(0); opacity: 0; }
    }
    @keyframes vortexRing {
      from { transform: rotate(0deg) scale(1); opacity: 1; }
      to { transform: rotate(360deg) scale(0.1); opacity: 0; }
    }
  `;
  document.head.appendChild(style);
  document.body.appendChild(vortexEl);

  // Reveal bio after vortex
  setTimeout(() => {
    vortexEl.remove();
    revealBio();
  }, 2000);
}

// ============================================================
// PHASE 5: BIO PAGE REVEAL
// ============================================================
function revealBio() {
  const bio = document.getElementById('phase-bio');
  const musicControl = document.getElementById('music-control');

  bio.classList.add('active');
  musicControl.classList.add('show');

  // Create floating hearts
  createFloatingElements();

  // Add sparkle on cursor move
  document.addEventListener('mousemove', createSparkle);
  document.addEventListener('click', (e) => {
    if (e.target.closest('#phase-bio') && !e.target.closest('.bio-card')) {
      createSparkleAt(e.clientX, e.clientY);
    }
  });
}

// ============================================================
// FLOATING ELEMENTS
// ============================================================
const particleEmojis = ['♡', '✦', '★', '✿', '❋', '✺', '♪', '✨', '💕', '🌸'];
const heartEmojis = ['♡', '💕', '💗', '🌸', '✨'];

function createFloatingElements() {
  // Create particles
  for (let i = 0; i < 20; i++) {
    setTimeout(() => createParticle(), i * 300);
  }
  setInterval(createParticle, 1500);

  // Create hearts
  for (let i = 0; i < 10; i++) {
    setTimeout(() => createHeart(), i * 500);
  }
  setInterval(createHeart, 2000);
}

function createParticle() {
  const p = document.createElement('div');
  p.className = 'particle';
  p.textContent = particleEmojis[Math.floor(Math.random() * particleEmojis.length)];
  p.style.left = Math.random() * 100 + 'vw';
  p.style.animationDuration = (8 + Math.random() * 10) + 's';
  p.style.animationDelay = (Math.random() * 2) + 's';
  p.style.fontSize = (0.6 + Math.random() * 0.8) + 'rem';
  p.style.opacity = 0.3 + Math.random() * 0.4;
  document.getElementById('phase-bio').appendChild(p);
  setTimeout(() => p.remove(), 20000);
}

function createHeart() {
  const h = document.createElement('div');
  h.className = 'floating-heart';
  h.textContent = heartEmojis[Math.floor(Math.random() * heartEmojis.length)];
  h.style.left = (5 + Math.random() * 90) + 'vw';
  h.style.animationDuration = (6 + Math.random() * 8) + 's';
  h.style.animationDelay = '0s';
  document.getElementById('phase-bio').appendChild(h);
  setTimeout(() => h.remove(), 16000);
}

function createSparkle(e) {
  if (Math.random() > 0.92) {
    createSparkleAt(e.clientX, e.clientY);
  }
}

function createSparkleAt(x, y) {
  const sparkles = ['✨', '⭐', '💫', '✦', '★'];
  const s = document.createElement('div');
  s.className = 'sparkle';
  s.textContent = sparkles[Math.floor(Math.random() * sparkles.length)];
  s.style.left = x + 'px';
  s.style.top = y + 'px';
  document.body.appendChild(s);
  setTimeout(() => s.remove(), 800);
}

// ============================================================
// BIO CARD INTERACTIONS
// ============================================================
function handleCardClick(category, cardEl, event) {
  // Create sparkle effect at click position
  createSparkleAt(event.clientX, event.clientY);

  // Remove playing class from previous card
  if (activeCardEl && activeCardEl !== cardEl) {
    activeCardEl.classList.remove('playing');
  }

  const mediaUrl = mediaMap[category];

  if (!mediaUrl) {
    // Show no-media popup
    showPopup(category, null);
  } else {
    activeCardEl = cardEl;
    cardEl.classList.add('playing');
    showPopup(category, mediaUrl);
  }
}

function showPopup(category, mediaUrl) {
  const popup = document.getElementById('media-popup');
  const popupTitle = document.getElementById('popup-title');
  const popupMedia = document.getElementById('popup-media');

  const categoryLabels = {
    age: 'AGE REVEAL',
    birthday: 'BIRTHDAY MESSAGE',
    location: 'LOCATION VIBES',
    zodiac: 'ZODIAC ENERGY',
    hobbies: 'HOBBY SHOWCASE',
    music: 'MUSIC TASTE',
    vibe: 'MY VIBE',
    quote: 'QUOTE OF LIFE'
  };

  popupTitle.textContent = '♡ ' + (categoryLabels[category] || category.toUpperCase());

  // Stop previous media
  if (currentAudioEl) {
    currentAudioEl.pause();
    currentAudioEl = null;
  }

  if (!mediaUrl) {
    popupMedia.innerHTML = `
      <div class="popup-no-media">
        <i class="fas fa-compact-disc" style="font-size:2rem; color:rgba(255,110,180,0.4); margin-bottom:10px; display:block;"></i>
        No media assigned for this card yet.<br>
        <small style="opacity:0.5;">Configure in the admin panel ♡</small>
      </div>
    `;
  } else {
    const isVideo = /\.(mp4|webm|ogg|mov)(\?|$)/i.test(mediaUrl) || mediaUrl.includes('youtube') || mediaUrl.includes('vimeo');

    if (mediaUrl.includes('youtube')) {
      const videoId = extractYouTubeId(mediaUrl);
      popupMedia.innerHTML = `
        <iframe width="100%" height="250" 
          src="https://www.youtube.com/embed/${videoId}?autoplay=1" 
          frameborder="0" allow="autoplay; encrypted-media" allowfullscreen
          style="border-radius:10px;">
        </iframe>
      `;
    } else if (isVideo) {
      popupMedia.innerHTML = `
        <video controls autoplay class="popup-media" style="max-height:300px;">
          <source src="${mediaUrl}">
          Your browser doesn't support video.
        </video>
      `;
    } else {
      // Audio
      popupMedia.innerHTML = `
        <div style="padding:20px; text-align:center;">
          <div style="font-size:3rem; margin-bottom:15px; animation: musicBounce 0.5s ease infinite alternate;">🎵</div>
          <audio controls autoplay style="width:100%;" id="popup-audio">
            <source src="${mediaUrl}">
            Your browser doesn't support audio.
          </audio>
        </div>
      `;
      currentAudioEl = document.getElementById('popup-audio');
    }
  }

  popup.classList.add('active');
}

function closePopup() {
  const popup = document.getElementById('media-popup');
  popup.classList.remove('active');

  if (currentAudioEl) {
    currentAudioEl.pause();
    currentAudioEl = null;
  }

  if (activeCardEl) {
    activeCardEl.classList.remove('playing');
    activeCardEl = null;
  }
}

function extractYouTubeId(url) {
  const match = url.match(/(?:v=|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  return match ? match[1] : '';
}

// Close popup on outside click
document.getElementById('media-popup').addEventListener('click', function(e) {
  if (e.target === this) closePopup();
});

// ============================================================
// BACKGROUND MUSIC CONTROL
// ============================================================
function toggleBgMusic() {
  const bgMusic = document.getElementById('bg-music');
  const icon = document.getElementById('music-icon');
  const label = document.getElementById('music-label');

  if (bgMusicPlaying) {
    bgMusic.pause();
    bgMusicPlaying = false;
    icon.className = 'fas fa-volume-mute';
    label.textContent = 'PLAY';
  } else {
    bgMusic.play();
    bgMusicPlaying = true;
    icon.className = 'fas fa-music music-icon';
    label.textContent = 'PAUSE';
  }
}

// Keyboard shortcut
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closePopup();
  if (e.key === 'm' || e.key === 'M') {
    if (document.getElementById('music-control').classList.contains('show')) {
      toggleBgMusic();
    }
  }
});
</script>
</body>
</html>
"""

# ============================================================
# ADMIN TEMPLATE
# ============================================================

ADMIN_LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login | RUHI X QNR</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  min-height: 100vh;
  background: #0a0a0a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Orbitron', monospace;
  background-image:
    repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,65,0.03) 2px, rgba(0,255,65,0.03) 4px);
}
.login-card {
  background: rgba(0,20,0,0.9);
  border: 1px solid #00ff41;
  border-radius: 8px;
  padding: 40px;
  width: min(400px, 90vw);
  box-shadow: 0 0 60px rgba(0,255,65,0.2);
}
.login-title {
  font-size: 1.2rem;
  color: #00ff41;
  letter-spacing: 0.3em;
  margin-bottom: 8px;
  text-align: center;
}
.login-sub {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: rgba(0,255,65,0.5);
  text-align: center;
  letter-spacing: 0.2em;
  margin-bottom: 30px;
}
.form-group { margin-bottom: 20px; }
label {
  display: block;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  color: rgba(0,255,65,0.7);
  letter-spacing: 0.2em;
  margin-bottom: 8px;
}
input[type=password] {
  width: 100%;
  background: rgba(0,40,0,0.8);
  border: 1px solid rgba(0,255,65,0.3);
  border-radius: 4px;
  padding: 12px 16px;
  color: #00ff41;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.9rem;
  outline: none;
  transition: border-color 0.3s;
}
input[type=password]:focus { border-color: #00ff41; box-shadow: 0 0 10px rgba(0,255,65,0.2); }
.login-btn {
  width: 100%;
  padding: 14px;
  background: transparent;
  border: 1px solid #00ff41;
  color: #00ff41;
  font-family: 'Orbitron', monospace;
  font-size: 0.85rem;
  letter-spacing: 0.3em;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.3s;
}
.login-btn:hover { background: rgba(0,255,65,0.1); box-shadow: 0 0 20px rgba(0,255,65,0.3); }
.error-msg {
  background: rgba(255,0,0,0.1);
  border: 1px solid rgba(255,0,0,0.3);
  color: #ff4444;
  padding: 10px;
  border-radius: 4px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  text-align: center;
  margin-bottom: 20px;
  letter-spacing: 0.1em;
}
.back-link {
  display: block;
  text-align: center;
  margin-top: 20px;
  color: rgba(0,255,65,0.4);
  text-decoration: none;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  transition: color 0.3s;
}
.back-link:hover { color: #00ff41; }
</style>
</head>
<body>
<div class="login-card">
  <div class="login-title">⚡ ADMIN ACCESS</div>
  <div class="login-sub">RESTRICTED ZONE — AUTHORIZED PERSONNEL ONLY</div>
  {% if error %}
  <div class="error-msg">✗ {{ error }}</div>
  {% endif %}
  <form method="POST" action="/admin/login">
    <div class="form-group">
      <label>SECURITY PASSPHRASE</label>
      <input type="password" name="password" placeholder="Enter password..." autofocus required>
    </div>
    <button type="submit" class="login-btn">AUTHENTICATE →</button>
  </form>
  <a href="/" class="back-link">← RETURN TO MAIN</a>
</div>
</body>
</html>
"""

ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Dashboard | RUHI X QNR</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Poppins:wght@300;400;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  min-height: 100vh;
  background: #080010;
  color: #fff;
  font-family: 'Poppins', sans-serif;
  background-image:
    radial-gradient(ellipse at top left, rgba(255,110,180,0.08) 0%, transparent 60%),
    radial-gradient(ellipse at bottom right, rgba(156,39,176,0.08) 0%, transparent 60%);
}

/* Topbar */
.topbar {
  background: rgba(255,255,255,0.04);
  border-bottom: 1px solid rgba(255,110,180,0.2);
  padding: 16px 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky; top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}
.topbar-brand {
  font-family: 'Orbitron', monospace;
  font-size: clamp(0.8rem, 2vw, 1rem);
  font-weight: 700;
  background: linear-gradient(135deg, #ff6eb4, #9c27b0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.2em;
}
.topbar-actions { display: flex; gap: 12px; align-items: center; }
.btn-sm {
  padding: 8px 16px;
  border-radius: 6px;
  font-family: 'Orbitron', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.15em;
  cursor: pointer;
  border: none;
  transition: all 0.3s;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-primary {
  background: linear-gradient(135deg, #ff6eb4, #9c27b0);
  color: #fff;
}
.btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(255,110,180,0.4); }
.btn-danger {
  background: rgba(255,50,50,0.15);
  border: 1px solid rgba(255,50,50,0.3);
  color: #ff6666;
}
.btn-danger:hover { background: rgba(255,50,50,0.25); }
.btn-ghost {
  background: rgba(255,255,255,0.07);
  border: 1px solid rgba(255,110,180,0.2);
  color: #ff9ed2;
}
.btn-ghost:hover { background: rgba(255,110,180,0.15); border-color: rgba(255,110,180,0.4); }

/* Main container */
.main { padding: clamp(20px, 4vw, 40px); max-width: 1100px; margin: 0 auto; }

/* Alert */
.alert {
  padding: 12px 20px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 10px;
}
.alert-success {
  background: rgba(39,201,63,0.1);
  border: 1px solid rgba(39,201,63,0.3);
  color: #27c93f;
}
.alert-error {
  background: rgba(255,80,80,0.1);
  border: 1px solid rgba(255,80,80,0.3);
  color: #ff5050;
}

/* Sections */
.section { margin-bottom: 40px; }
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255,110,180,0.15);
}
.section-title-admin {
  font-family: 'Orbitron', monospace;
  font-size: clamp(0.75rem, 2vw, 0.9rem);
  letter-spacing: 0.2em;
  color: #ff9ed2;
}
.section-icon { color: #ff6eb4; font-size: 1rem; }

/* Form grid */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(280px, 100%), 1fr));
  gap: 20px;
}
.form-group-admin { display: flex; flex-direction: column; gap: 6px; }
.form-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: rgba(255,182,193,0.6);
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
.form-input, .form-textarea {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,110,180,0.2);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fff;
  font-family: 'Poppins', sans-serif;
  font-size: 0.85rem;
  outline: none;
  transition: all 0.3s;
  width: 100%;
}
.form-input:focus, .form-textarea:focus {
  border-color: rgba(255,110,180,0.6);
  background: rgba(255,255,255,0.08);
  box-shadow: 0 0 0 3px rgba(255,110,180,0.1);
}
.form-textarea { resize: vertical; min-height: 80px; }
.form-input::placeholder, .form-textarea::placeholder { color: rgba(255,255,255,0.2); }

/* Media card */
.media-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
  gap: 16px;
}
.media-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,110,180,0.15);
  border-radius: 12px;
  padding: 16px;
  transition: border-color 0.3s;
}
.media-card:hover { border-color: rgba(255,110,180,0.35); }
.media-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.media-card-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(255,110,180,0.2), rgba(156,39,176,0.2));
  display: flex; align-items: center; justify-content: center;
  color: #ff9ed2;
  font-size: 0.8rem;
}
.media-card-title {
  font-family: 'Orbitron', monospace;
  font-size: 0.65rem;
  color: #ff9ed2;
  letter-spacing: 0.15em;
}
.media-hint {
  font-size: 0.65rem;
  color: rgba(255,255,255,0.25);
  margin-top: 4px;
  font-family: 'Share Tech Mono', monospace;
}

/* Submit button */
.form-submit {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
.btn-save {
  padding: 14px 40px;
  background: linear-gradient(135deg, #ff6eb4, #9c27b0);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-family: 'Orbitron', monospace;
  font-size: 0.8rem;
  letter-spacing: 0.2em;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn-save:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(255,110,180,0.4); }

/* Password change */
.password-section {
  background: rgba(255,50,50,0.05);
  border: 1px solid rgba(255,50,50,0.15);
  border-radius: 12px;
  padding: 24px;
}

/* Stats row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(150px, 100%), 1fr));
  gap: 16px;
  margin-bottom: 30px;
}
.stat-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,110,180,0.15);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
}
.stat-value {
  font-family: 'Orbitron', monospace;
  font-size: clamp(1rem, 3vw, 1.5rem);
  font-weight: 700;
  background: linear-gradient(135deg, #ff6eb4, #9c27b0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
}
.stat-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  color: rgba(255,182,193,0.5);
  letter-spacing: 0.15em;
}

/* Full width group */
.full-width { grid-column: 1 / -1; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
::-webkit-scrollbar-thumb { background: rgba(255,110,180,0.3); border-radius: 2px; }
</style>
</head>
<body>

<!-- Topbar -->
<div class="topbar">
  <div class="topbar-brand">⚡ RUHI X QNR — ADMIN PANEL</div>
  <div class="topbar-actions">
    <a href="/" class="btn-sm btn-ghost" target="_blank"><i class="fas fa-eye"></i> VIEW SITE</a>
    <a href="/admin/logout" class="btn-sm btn-danger"><i class="fas fa-sign-out-alt"></i> LOGOUT</a>
  </div>
</div>

<div class="main">
  <!-- Alert -->
  {% if message %}
  <div class="alert alert-{{ 'success' if success else 'error' }}">
    <i class="fas fa-{{ 'check-circle' if success else 'exclamation-triangle' }}"></i>
    {{ message }}
  </div>
  {% endif %}

  <!-- Stats -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-value">{{ data.profile.name.split()[0] }}</div>
      <div class="stat-label">IDENTITY</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ data.media_map.values() | list | selectattr('__bool__') | list | length }}</div>
      <div class="stat-label">MEDIA MAPPED</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{{ data.socials.values() | list | selectattr('__bool__') | list | length }}</div>
      <div class="stat-label">SOCIAL LINKS</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">8</div>
      <div class="stat-label">BIO CARDS</div>
    </div>
  </div>

  <!-- MAIN FORM -->
  <form method="POST" action="/admin/save">

    <!-- Profile Section -->
    <div class="section">
      <div class="section-header">
        <i class="fas fa-user section-icon"></i>
        <div class="section-title-admin">PROFILE INFORMATION</div>
      </div>
      <div class="form-grid">
        <div class="form-group-admin">
          <label class="form-label">Display Name</label>
          <input type="text" name="name" class="form-input" value="{{ data.profile.name }}" placeholder="RUHI X QNR" required>
        </div>
        <div class="form-group-admin">
          <label class="form-label">Tagline</label>
          <input type="text" name="tagline" class="form-input" value="{{ data.profile.tagline }}" placeholder="Digital Ghost | Aesthetic Soul">
        </div>
        <div class="form-group-admin full-width">
          <label class="form-label">Bio / Description</label>
          <textarea name="bio" class="form-textarea">{{ data.profile.bio }}</textarea>
        </div>
        <div class="form-group-admin full-width">
          <label class="form-label">Avatar Image URL</label>
          <input type="url" name="avatar" class="form-input" value="{{ data.profile.avatar }}" placeholder="https://...">
        </div>
      </div>
    </div>

    <!-- Bio Details -->
    <div class="section">
      <div class="section-header">
        <i class="fas fa-id-card section-icon"></i>
        <div class="section-title-admin">BIO CARD DETAILS</div>
      </div>
      <div class="form-grid">
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-star-of-life"></i> Age</label>
          <input type="text" name="age" class="form-input" value="{{ data.profile.age }}" placeholder="19">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-birthday-cake"></i> Birthday</label>
          <input type="text" name="birthday" class="form-input" value="{{ data.profile.birthday }}" placeholder="January 1st">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-map-pin"></i> Location</label>
          <input type="text" name="location" class="form-input" value="{{ data.profile.location }}" placeholder="City, Country">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-moon"></i> Zodiac</label>
          <input type="text" name="zodiac" class="form-input" value="{{ data.profile.zodiac }}" placeholder="Capricorn ♑">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-heart"></i> Hobbies</label>
          <input type="text" name="hobbies" class="form-input" value="{{ data.profile.hobbies }}" placeholder="Hacking Hearts...">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-music"></i> Music Taste</label>
          <input type="text" name="music" class="form-input" value="{{ data.profile.music }}" placeholder="Lo-fi & Dark Pop">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-magic"></i> My Vibe</label>
          <input type="text" name="vibe" class="form-input" value="{{ data.profile.vibe }}" placeholder="Chaotic Soft Girl">
        </div>
        <div class="form-group-admin full-width">
          <label class="form-label"><i class="fas fa-quote-left"></i> Personal Quote</label>
          <input type="text" name="quote" class="form-input" value="{{ data.profile.quote }}" placeholder="Your iconic quote...">
        </div>
      </div>
    </div>

    <!-- Social Links -->
    <div class="section">
      <div class="section-header">
        <i class="fas fa-share-alt section-icon"></i>
        <div class="section-title-admin">SOCIAL MEDIA LINKS</div>
      </div>
      <div class="form-grid">
        <div class="form-group-admin">
          <label class="form-label"><i class="fab fa-instagram"></i> Instagram URL</label>
          <input type="url" name="instagram" class="form-input" value="{{ data.socials.instagram }}" placeholder="https://instagram.com/...">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fab fa-twitter"></i> Twitter URL</label>
          <input type="url" name="twitter" class="form-input" value="{{ data.socials.twitter }}" placeholder="https://twitter.com/...">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fab fa-tiktok"></i> TikTok URL</label>
          <input type="url" name="tiktok" class="form-input" value="{{ data.socials.tiktok }}" placeholder="https://tiktok.com/@...">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fab fa-youtube"></i> YouTube URL</label>
          <input type="url" name="youtube" class="form-input" value="{{ data.socials.youtube }}" placeholder="https://youtube.com/...">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fab fa-spotify"></i> Spotify URL</label>
          <input type="url" name="spotify" class="form-input" value="{{ data.socials.spotify }}" placeholder="https://spotify.com/...">
        </div>
        <div class="form-group-admin">
          <label class="form-label"><i class="fas fa-music"></i> Background Music URL</label>
          <input type="url" name="background_music" class="form-input" value="{{ data.background_music }}" placeholder="https://...mp3">
        </div>
      </div>
    </div>

    <!-- Terminal Lines -->
    <div class="section">
      <div class="section-header">
        <i class="fas fa-terminal section-icon"></i>
        <div class="section-title-admin">TERMINAL INTRO LINES</div>
      </div>
      <div class="form-group-admin">
        <label class="form-label">Terminal Lines (one per line)</label>
        <textarea name="terminal_lines" class="form-textarea" style="min-height:180px; font-family:'Share Tech Mono',monospace; font-size:0.8rem;">{{ data.terminal_lines | join('\n') }}</textarea>
        <div class="media-hint">Each line will be typed one by one in the terminal sequence.</div>
      </div>
    </div>

    <!-- Media Mapping -->
    <div class="section">
      <div class="section-header">
        <i class="fas fa-play-circle section-icon"></i>
        <div class="section-title-admin">MEDIA URL MAPPING — BIO CARDS</div>
      </div>
      <p style="font-size:0.8rem; color:rgba(255,182,193,0.5); margin-bottom:20px; font-family:'Share Tech Mono',monospace;">
        ♡ Assign an audio (MP3) or video (MP4/YouTube) URL to each bio card. When clicked, it will play automatically.
      </p>
      <div class="media-grid">
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-star-of-life"></i></div>
            <div class="media-card-title">AGE CARD</div>
          </div>
          <input type="url" name="media_age" class="form-input" value="{{ data.media_map.age }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-birthday-cake"></i></div>
            <div class="media-card-title">BIRTHDAY CARD</div>
          </div>
          <input type="url" name="media_birthday" class="form-input" value="{{ data.media_map.birthday }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-map-pin"></i></div>
            <div class="media-card-title">LOCATION CARD</div>
          </div>
          <input type="url" name="media_location" class="form-input" value="{{ data.media_map.location }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-moon"></i></div>
            <div class="media-card-title">ZODIAC CARD</div>
          </div>
          <input type="url" name="media_zodiac" class="form-input" value="{{ data.media_map.zodiac }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-heart"></i></div>
            <div class="media-card-title">HOBBIES CARD</div>
          </div>
          <input type="url" name="media_hobbies" class="form-input" value="{{ data.media_map.hobbies }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-music"></i></div>
            <div class="media-card-title">MUSIC CARD</div>
          </div>
          <input type="url" name="media_music" class="form-input" value="{{ data.media_map.music }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-magic"></i></div>
            <div class="media-card-title">VIBE CARD</div>
          </div>
          <input type="url" name="media_vibe" class="form-input" value="{{ data.media_map.vibe }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
        <div class="media-card">
          <div class="media-card-header">
            <div class="media-card-icon"><i class="fas fa-quote-left"></i></div>
            <div class="media-card-title">QUOTE CARD</div>
          </div>
          <input type="url" name="media_quote" class="form-input" value="{{ data.media_map.quote }}" placeholder="https://...mp3 or mp4">
          <div class="media-hint">Supports: MP3, MP4, YouTube URL</div>
        </div>
      </div>
    </div>

    <!-- Submit -->
    <div class="form-submit">
      <button type="submit" name="action" value="save_profile" class="btn-save">
        <i class="fas fa-save"></i> SAVE ALL CHANGES
      </button>
    </div>
  </form>

  <!-- Password Change -->
  <div class="section" style="margin-top:20px;">
    <div class="section-header">
      <i class="fas fa-lock section-icon"></i>
      <div class="section-title-admin">CHANGE ADMIN PASSWORD</div>
    </div>
    <div class="password-section">
      <form method="POST" action="/admin/change-password">
        <div class="form-grid">
          <div class="form-group-admin">
            <label class="form-label">Current Password</label>
            <input type="password" name="current_password" class="form-input" placeholder="Current password..." required>
          </div>
          <div class="form-group-admin">
            <label class="form-label">New Password</label>
            <input type="password" name="new_password" class="form-input" placeholder="New password (min 6 chars)..." required minlength="6">
          </div>
          <div class="form-group-admin">
            <label class="form-label">Confirm New Password</label>
            <input type="password" name="confirm_password" class="form-input" placeholder="Confirm new password..." required>
          </div>
        </div>
        <div class="form-submit" style="margin-top:16px;">
          <button type="submit" class="btn-sm btn-danger" style="padding:12px 30px; font-size:0.75rem;">
            <i class="fas fa-key"></i> UPDATE PASSWORD
          </button>
        </div>
      </form>
    </div>
  </div>

</div>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================

@app.route('/')
def index():
    db = load_db()
    return render_template_string(
        MAIN_TEMPLATE,
        profile=db['profile'],
        socials=db['socials'],
        background_music=db['background_music'],
        media_map=db['media_map'],
        terminal_lines=db['terminal_lines']
    )

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template_string(
        ADMIN_DASHBOARD_TEMPLATE,
        data=load_db(),
        message=None,
        success=False
    )

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        db = load_db()
        hashed = hashlib.sha256(password.encode()).hexdigest()

        if hashed == db['password']:
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template_string(ADMIN_LOGIN_TEMPLATE, error='Invalid password. Access denied.')

    return render_template_string(ADMIN_LOGIN_TEMPLATE, error=None)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/save', methods=['POST'])
@login_required
def admin_save():
    db = load_db()

    try:
        # Update profile
        db['profile']['name'] = request.form.get('name', db['profile']['name']).strip()
        db['profile']['tagline'] = request.form.get('tagline', db['profile']['tagline']).strip()
        db['profile']['bio'] = request.form.get('bio', db['profile']['bio']).strip()
        db['profile']['avatar'] = request.form.get('avatar', db['profile']['avatar']).strip()
        db['profile']['age'] = request.form.get('age', db['profile']['age']).strip()
        db['profile']['birthday'] = request.form.get('birthday', db['profile']['birthday']).strip()
        db['profile']['location'] = request.form.get('location', db['profile']['location']).strip()
        db['profile']['zodiac'] = request.form.get('zodiac', db['profile']['zodiac']).strip()
        db['profile']['hobbies'] = request.form.get('hobbies', db['profile']['hobbies']).strip()
        db['profile']['music'] = request.form.get('music', db['profile']['music']).strip()
        db['profile']['vibe'] = request.form.get('vibe', db['profile']['vibe']).strip()
        db['profile']['quote'] = request.form.get('quote', db['profile']['quote']).strip()

        # Update socials
        db['socials']['instagram'] = request.form.get('instagram', '').strip()
        db['socials']['twitter'] = request.form.get('twitter', '').strip()
        db['socials']['tiktok'] = request.form.get('tiktok', '').strip()
        db['socials']['youtube'] = request.form.get('youtube', '').strip()
        db['socials']['spotify'] = request.form.get('spotify', '').strip()
        db['background_music'] = request.form.get('background_music', db['background_music']).strip()

        # Update terminal lines
        terminal_text = request.form.get('terminal_lines', '')
        if terminal_text.strip():
            lines = [l.strip() for l in terminal_text.split('\n') if l.strip()]
            if lines:
                db['terminal_lines'] = lines

        # Update media map
        db['media_map']['age'] = request.form.get('media_age', '').strip()
        db['media_map']['birthday'] = request.form.get('media_birthday', '').strip()
        db['media_map']['location'] = request.form.get('media_location', '').strip()
        db['media_map']['zodiac'] = request.form.get('media_zodiac', '').strip()
        db['media_map']['hobbies'] = request.form.get('media_hobbies', '').strip()
        db['media_map']['music'] = request.form.get('media_music', '').strip()
        db['media_map']['vibe'] = request.form.get('media_vibe', '').strip()
        db['media_map']['quote'] = request.form.get('media_quote', '').strip()

        save_db(db)

        return render_template_string(
            ADMIN_DASHBOARD_TEMPLATE,
            data=db,
            message='✓ All changes saved successfully! Your bio page has been updated.',
            success=True
        )
    except Exception as e:
        return render_template_string(
            ADMIN_DASHBOARD_TEMPLATE,
            data=db,
            message=f'Error saving data: {str(e)}',
            success=False
        )

@app.route('/admin/change-password', methods=['POST'])
@login_required
def admin_change_password():
    db = load_db()

    current = request.form.get('current_password', '')
    new_pass = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    current_hash = hashlib.sha256(current.encode()).hexdigest()

    if current_hash != db['password']:
        return render_template_string(
            ADMIN_DASHBOARD_TEMPLATE,
            data=db,
            message='✗ Current password is incorrect.',
            success=False
        )

    if new_pass != confirm:
        return render_template_string(
            ADMIN_DASHBOARD_TEMPLATE,
            data=db,
            message='✗ New passwords do not match.',
            success=False
        )

    if len(new_pass) < 6:
        return render_template_string(
            ADMIN_DASHBOARD_TEMPLATE,
            data=db,
            message='✗ Password must be at least 6 characters.',
            success=False
        )

    db['password'] = hashlib.sha256(new_pass.encode()).hexdigest()
    save_db(db)

    return render_template_string(
        ADMIN_DASHBOARD_TEMPLATE,
        data=db,
        message='✓ Password updated successfully! Please use your new password next time.',
        success=True
    )

@app.route('/api/db')
@login_required
def api_get_db():
    """API endpoint to get current DB state (excluding password)"""
    db = load_db()
    safe_db = {k: v for k, v in db.items() if k != 'password'}
    return jsonify(safe_db)

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == '__main__':
    # Initialize DB on first run
    if not os.path.exists(DB_FILE):
        save_db(DEFAULT_DB)
        print("✓ Database initialized with defaults")
        print("✓ Default admin password: admin123")
        print("✓ Change it immediately at /admin")

    print("\n" + "="*50)
    print("  RUHI X QNR — BIO WEBSITE")
    print("="*50)
    print(f"  Main Site  : http://localhost:5000/")
    print(f"  Admin Panel: http://localhost:5000/admin")
    print(f"  Default PW : admin123")
    print("="*50 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)

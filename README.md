# ⚡ SEVA AI (सेवा डिजिटल सहाय्यक)
### Voice-First Autonomous Public Service Kiosk Engine for Rural India

> Built upon [SAGAR-TAMANG/friday-tony-stark-demo](https://github.com/SAGAR-TAMANG/friday-tony-stark-demo) (All-in-One FastMCP + LiveKit)  
> Designed for Gram Panchayats, Setu Kendras, and Common Service Centers.

---

## 🌟 Key Features

- **Proactive Vision Greeting:** USB webcam detects a citizen standing in front of the kiosk for 1+ seconds and speaks proactively: *"Namaste! Welcome to Gram Panchayat digital assistant. How can I help you?"*
- **GPS-Aware Regional Language:** Automatically identifies state location on boot to greet in the native language (Marathi, Gujarati, Kannada, Tamil, Hindi, etc.) with real-time switching across all 22 Indian languages.
- **Split-Screen Demonstration Mode:**
  - **Left Screen:** Dark cyberpunk voice HUD with 4-state audio ring (`STANDBY` $\to$ `LISTENING` $\to$ `THINKING` $\to$ `SPEAKING`).
  - **Right Screen:** Visible Google Chrome (`headless=False`) filling government forms and highlighting fields with glowing orange borders (`#ff5500`).
- **Multimodal Authentication:** Citizen speaks their 10-digit mobile number and SMS OTP in their native language (*"पाच दोन आठ तीन"* $\to$ `5283`). Keypad fallback and USB fingerprint scanner (Mantra/Morpho) are fully supported.
- **Mobile-Only App Automation:** Handles Android-only services (like *e-Pik Pahani* / ई-पीक पाहणी) via direct backend REST APIs or USB-connected Android phone via ADB.
- **Safety Review Gate (DPDP Act):** Verbally summarizes entered details and requires citizen confirmation before clicking final "Submit" or "Pay".
- **Dual Output Delivery:** Automatically prints a paper copy via the kiosk thermal printer and sends a digital PDF copy directly to the citizen's WhatsApp number.
- **Offline & Weak Internet Resilience:** Answers government scheme FAQs offline and queues live requests to auto-execute when internet connection restores.
- **15-Second Walk-Away Privacy Purge:** Automatically clears all sensitive personal data (Aadhaar, OTP, land records) if the citizen walks away for 15+ seconds.
- **Dual-Platform Architecture:** Runs in visible desktop demonstration mode on Windows (`HP Elite 7100`, Core i3, 3.7GB RAM) and transitions seamlessly to a screenless **Raspberry Pi** appliance.

---

## 🚀 Architecture Summary

SEVA AI combines:
1. **The Brain & Real-Time Voice:** FastMCP backend and LiveKit real-time voice pipeline powered by Google Gemini 2.5 Flash and Indic speech models.
2. **The Execution Hands:** Playwright browser automation with human typing cadence and glowing field highlights.
3. **The Mobile Bridge:** ADB connector for USB-plugged Android devices.
4. **The Kiosk HUD:** Lightweight HTML5/CSS audio-reactive interface (<25MB RAM, 0% GPU).

---

## 📖 Complete Documentation

- [`MASTER_PRD.md`](./MASTER_PRD.md): The authoritative Master Product Requirement Document.
- [`PROJECT.md`](./PROJECT.md): Technical architecture, tool contracts, and component design.
- [`AGENTS.md`](./AGENTS.md): Autonomous engine operational directives and invariant rules.
- [`GEMINI.md`](./GEMINI.md): Persistent system constraints and hardware guardrails.

# Home Assistant CallMeBot API Integration

[![GitHub Release](https://img.shields.io/github/v/release/nhatthm/home-assistant-callmebot)](https://github.com/nhatthm/home-assistant-callmebot/releases/latest)
[![GitHub Downloads](https://img.shields.io/github/downloads/nhatthm/home-assistant-callmebot/total)](https://github.com/nhatthm/home-assistant-callmebot/releases)
[![codecov](https://codecov.io/gh/nhatthm/home-assistant-callmebot/branch/master/graph/badge.svg)](https://codecov.io/gh/nhatthm/home-assistant-callmebot)
[![Unit Tests](https://github.com/nhatthm/home-assistant-callmebot/actions/workflows/test.yaml/badge.svg)](https://github.com/nhatthm/home-assistant-callmebot/actions/workflows/test.yaml)
[![Lint](https://github.com/nhatthm/home-assistant-callmebot/actions/workflows/lint.yaml/badge.svg)](https://github.com/nhatthm/home-assistant-callmebot/actions/workflows/lint.yaml)
[![HACS Default](https://img.shields.io/badge/HACS-Default-orange.svg)](https://hacs.xyz)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](http://donate.nhat.me)

<p align="center"><img src="https://raw.githubusercontent.com/nhatthm/home-assistant-callmebot/master/custom_components/callmebot/brand/logo.png" alt="CallMeBot API Logo" width="150"></p>

A modern, minimal custom integration for Home Assistant to send text messages and make voice calls via Telegram using the free [CallMeBot API](https://www.callmebot.com/).

[![HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nhatthm&repository=home-assistant-callmebot&category=integration)

## Why this integration?

You might wonder why you should use this integration instead of the official Home Assistant [Telegram Bot](https://www.home-assistant.io/integrations/telegram_bot/) integration.

Here are the key differences:

1. **No Bot Setup Required:** The official Telegram Bot integration requires you to talk to BotFather, create a bot, secure API tokens, and maintain/configure the bot settings. With this CallMeBot integration, you do **not** need to create or maintain your own bot. CallMeBot manages the gateway.
2. **Simplified Authorization:** You only need to authorize the free CallMeBot gateway bot once by sending it a message on Telegram. There are no tokens or complex access lists to configure in Home Assistant.
3. **Telegram Voice Calls (Text-to-Speech):** This integration lets you make free Telegram Voice Calls. When answered, the bot reads the message via Text-to-Speech (TTS). This is perfect for critical alerts (e.g., leak/smoke/alarm) that might be missed via text. The official `telegram_bot` only supports standard text/photo/video notifications and cannot make voice calls.

## Installation

### Method 1: One-Click (Recommended)

Click the badge below to open the HACS repository directly in your Home Assistant instance and click download:

[![HACS Repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nhatthm&repository=home-assistant-callmebot&category=integration)

### Method 2: Manual HACS Setup

1. Open **HACS** in your Home Assistant instance.
2. Click the three dots `...` in the top right corner and select **Custom repositories**.
3. Paste the repository URL: `https://github.com/nhatthm/home-assistant-callmebot`
4. Select **Integration** as the category, and click **Add**.
5. Find **CallMeBot API** in HACS and click **Download**.
6. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services** in Home Assistant.
2. Click **Add Integration** in the bottom right corner.
3. Search for and select **CallMeBot API**. _(Tip: You can also click the badge below to start the setup flow directly)_

    [![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=callmebot)

4. Follow the configuration wizard:
    - **Step 1:** Choose **Telegram** as your integration type.
    - **Step 2:** Choose the message type you want to set up: **Text Message** or **Call**.
    - **Step 3:** Enter the recipient. You can enter a Telegram Username starting with `@` (e.g., `@MyTelegramUser`) or a phone number in international format starting with `+` (e.g., `+1234567890`).
    - **Step 4: Opt-In Authorization:** Before finishing, you **must authorize CallMeBot** to contact you. For Text, authenticate via [Text Login][text-login]. For Voice, authenticate via [Voice Auth][voice-auth].
    - **Step 5: Completion:** Once authorized, submit the step. A validation message/call will be sent, and a new `notify` entity will be created: For Text: `notify.callmebot_telegram_<recipient_hash>_text`. For Calls: `notify.callmebot_telegram_<recipient_hash>_call`.

### Usage & Service Actions

Once configured, you can call the notification entity as a service action in your automations or scripts.

#### Send a Text Message

```yaml
action: notify.callmebot_telegram_xxxxxxxx_text
data:
    message: "Hello! This is a text notification from Home Assistant."
```

#### Make a Voice Call (reads out the message via TTS)

```yaml
action: notify.callmebot_telegram_xxxxxxxx_call
data:
    message: "Critical warning: Water leak detected in the basement!"
```

## Known Limitations

Even though [CallMeBot](https://www.callmebot.com/) supports multiple messaging platforms (such as WhatsApp, Facebook Messenger, Signal, etc.), **this integration currently only supports the free Telegram API (Text Messages and Calls)**. Support for other platforms is not included.

## Disclaimer & Affiliation

This project is an independent, community-driven integration. It is **not**
associated with, officially endorsed by, or affiliated with CallMeBot in any
way. We simply utilize the public CallMeBot APIs to send notifications and make
calls. We do not own, maintain, or control the CallMeBot API, service, or
server infrastructure. Please use this service responsibly and in accordance
with CallMeBot's own terms and policies.

The integration logo is adapted from the official CallMeBot assets with a Home
Assistant logo overlay generated via Generative AI. Credit for the original
logo design and assets belongs to the CallMeBot author.

## Donation

If this project help you reduce time to develop, you can give me a cup of coffee :)

### PayPal donation

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](http://donate.nhat.me)

or scan this:

<img src="https://user-images.githubusercontent.com/1154587/113494222-ad8cb200-94e6-11eb-9ef3-eb883ada222a.png" width="147px" alt="PayPal QR Code" />

[text-login]: https://api2.callmebot.com/txt/login.php
[voice-auth]: https://api2.callmebot.com/txt/auth.php
